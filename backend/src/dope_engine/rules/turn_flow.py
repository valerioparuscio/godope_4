"""The turn/phase state machine (RULES_CANONICAL.md §B): Tip-off, Action
Phase (3 rounds), Poker, Showdown, then back to Tip-off or into End Game
Scoring.

Milestone 1 scope only: no economic action (Piazzare/Spostare/Acquistare/
Vendere/Corrompere/Comprare Cops-Feds, §C1-C6) exists yet, so the "main
action" step is always a no-op pass, Poker never has matches to resolve
(no Gamble card can be played yet), and Showdown never actually resolves
a Raid (that is Milestone 5, §D4). Those phases still run — the turn
genuinely advances through all of them — they just have nothing to do
yet. Real handlers replace the stubs as each milestone lands.
"""

from __future__ import annotations

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import ChooseGritAction, Command, DiscardCards, PassOptionalStep
from dope_engine.domain.enums import ActiveStep, GamePhase, GameStatus
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    ActionRoundEnded,
    CardsDiscarded,
    DomainEvent,
    GameFinished,
    GritActionChosen,
    MainActionPassed,
    PokerPhaseResolved,
    RaidRevealed,
    ShowdownPhaseResolved,
    TurnEnded,
    TurnStarted,
)
from dope_engine.domain.ids import CardId, ContactId, PlayerId
from dope_engine.domain.state import GameState, PlayerState, find_player
from dope_engine.rules.event_utils import emit as _emit


def register_handlers(bus: CommandBus, *, card_contact_by_id: dict[CardId, ContactId]) -> None:
    bus.register(ChooseGritAction, _handle_choose_grit_action)
    bus.register(PassOptionalStep, _handle_pass_optional_step)
    bus.register(
        DiscardCards,
        lambda state, command: _handle_discard_cards(state, command, card_contact_by_id),
    )


def start_tip_off(state: GameState, events: list[DomainEvent]) -> None:
    """Reveal this turn's Raid card and enter the Action Phase.

    RULES_CANONICAL.md §B1/§D4: normally the player with the highest
    Preti Link decides the first player; no Link can exist before
    Milestone 3, so `first_player_id` is left as-is, matching the
    documented fallback ("resta primo chi lo era nel turno precedente").
    """
    state.phase = GamePhase.TIP_OFF
    raid_index = state.turn_index - 1
    if raid_index < len(state.raids.selected_card_ids):
        state.raids.current_turn_card_id = state.raids.selected_card_ids[raid_index]
        _emit(
            state,
            events,
            RaidRevealed,
            turn_index=state.turn_index,
            raid_card_id=state.raids.current_turn_card_id,
        )
    _emit(
        state,
        events,
        TurnStarted,
        turn_index=state.turn_index,
        first_player_id=state.first_player_id,
    )
    _start_action_phase(state)


def _start_action_phase(state: GameState) -> None:
    state.phase = GamePhase.ACTION_PHASE
    for player in state.players:
        player.available_grit_values = list(state.configuration["grit_values"])
        player.moved_pawn_ids_this_turn = []
        player.extra_action_used_this_turn = False
    _start_new_round(state, 1)


def _start_new_round(state: GameState, round_index: int) -> None:
    state.action_round_index = round_index
    for player in state.players:
        player.gamble_cards_played_this_round = 0
        player.pending_action_type = None
        player.current_round_grit_value = None
    state.current_player_id = state.first_player_id
    state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION


def _rotation_order(state: GameState) -> list[PlayerId]:
    start = state.player_order.index(state.first_player_id)
    return state.player_order[start:] + state.player_order[:start]


def _finish_player_round(
    state: GameState, player: PlayerState, events: list[DomainEvent]
) -> None:
    _emit(
        state,
        events,
        ActionRoundEnded,
        turn_index=state.turn_index,
        action_round_index=state.action_round_index,
        player_id=player.player_id,
    )
    _advance_to_next_player_or_phase(state, events)


def _advance_to_next_player_or_phase(state: GameState, events: list[DomainEvent]) -> None:
    order = _rotation_order(state)
    position = order.index(state.current_player_id)
    if position + 1 < len(order):
        state.current_player_id = order[position + 1]
        state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION
        return

    rounds_per_turn = state.configuration["action_rounds_per_turn"]
    if state.action_round_index < rounds_per_turn:
        _start_new_round(state, state.action_round_index + 1)
        return

    _enter_poker_phase(state, events)


def _enter_poker_phase(state: GameState, events: list[DomainEvent]) -> None:
    state.phase = GamePhase.POKER_PHASE
    state.active_step = ActiveStep.NONE
    state.poker.matches_this_turn = []
    _emit(state, events, PokerPhaseResolved, turn_index=state.turn_index)
    _enter_showdown_phase(state, events)


def _enter_showdown_phase(state: GameState, events: list[DomainEvent]) -> None:
    state.phase = GamePhase.SHOWDOWN_PHASE
    _emit(state, events, ShowdownPhaseResolved, turn_index=state.turn_index)
    _end_turn(state, events)


def _end_turn(state: GameState, events: list[DomainEvent]) -> None:
    _emit(state, events, TurnEnded, turn_index=state.turn_index)
    if state.turn_index >= state.configuration["num_turns"]:
        state.phase = GamePhase.FINISHED
        state.status = GameStatus.FINISHED
        state.active_step = ActiveStep.NONE
        _emit(state, events, GameFinished, turn_index=state.turn_index)
        return

    state.turn_index += 1
    start_tip_off(state, events)


def _validate(
    state: GameState, command: Command, expected_steps: set[ActiveStep]
) -> DomainError | None:
    if state.phase != GamePhase.ACTION_PHASE:
        return wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value)
    if state.current_player_id != command.player_id:
        return wrong_player(str(state.current_player_id), str(command.player_id))
    if state.active_step not in expected_steps:
        expected = "|".join(s.value for s in expected_steps)
        return DomainError(
            code="wrong_active_step",
            message=(
                f"Expected active_step in [{expected}], "
                f"state is at '{state.active_step.value}'."
            ),
            details={"expected_steps": expected, "actual_step": state.active_step.value},
        )
    return None


def proceed_after_main_action(
    state: GameState, player: PlayerState, events: list[DomainEvent]
) -> None:
    if len(player.hand_card_ids) > state.configuration["max_hand_size"]:
        state.active_step = ActiveStep.WAITING_FOR_HAND_DISCARD
    else:
        _finish_player_round(state, player, events)


def _handle_choose_grit_action(state: GameState, command: ChooseGritAction) -> CommandOutcome:
    error = _validate(state, command, {ActiveStep.WAITING_FOR_GRIT_ACTION})
    if error is not None:
        return CommandFailure(error)

    player = find_player(state, command.player_id)
    if command.grit_value not in player.available_grit_values:
        return CommandFailure(
            DomainError(
                code="grit_value_unavailable",
                message=(
                    f"Grit value {command.grit_value} is not available "
                    f"for '{command.player_id}'."
                ),
                details={"available": list(player.available_grit_values)},
            )
        )

    state.revision += 1
    player.available_grit_values.remove(command.grit_value)
    player.current_round_grit_value = command.grit_value
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS

    events: list[DomainEvent] = []
    _emit(
        state,
        events,
        GritActionChosen,
        player_id=command.player_id,
        grit_value=command.grit_value,
    )
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _handle_pass_optional_step(state: GameState, command: PassOptionalStep) -> CommandOutcome:
    expected = {ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS, ActiveStep.WAITING_FOR_HAND_DISCARD}
    error = _validate(state, command, expected)
    if error is not None:
        return CommandFailure(error)

    player = find_player(state, command.player_id)
    events: list[DomainEvent] = []

    if state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS:
        state.revision += 1
        _emit(state, events, MainActionPassed, player_id=command.player_id)
        proceed_after_main_action(state, player, events)
    else:
        overflow = len(player.hand_card_ids) - state.configuration["max_hand_size"]
        if overflow > 0:
            return CommandFailure(
                DomainError(
                    code="must_discard",
                    message=(
                        f"Hand has {overflow} card(s) over the limit; "
                        f"must discard before passing."
                    ),
                    details={"overflow": overflow},
                )
            )
        state.revision += 1
        _finish_player_round(state, player, events)

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _handle_discard_cards(
    state: GameState, command: DiscardCards, card_contact_by_id: dict[CardId, ContactId]
) -> CommandOutcome:
    error = _validate(state, command, {ActiveStep.WAITING_FOR_HAND_DISCARD})
    if error is not None:
        return CommandFailure(error)

    player = find_player(state, command.player_id)
    overflow = len(player.hand_card_ids) - state.configuration["max_hand_size"]
    if len(command.card_ids) != overflow:
        return CommandFailure(
            DomainError(
                code="wrong_discard_count",
                message=f"Must discard exactly {overflow} card(s), got {len(command.card_ids)}.",
                details={"required": overflow, "given": len(command.card_ids)},
            )
        )
    if len(set(command.card_ids)) != len(command.card_ids) or not set(command.card_ids).issubset(
        player.hand_card_ids
    ):
        return CommandFailure(
            DomainError(
                code="invalid_discard_selection",
                message="Discard selection must be distinct cards actually in the player's hand.",
                details={"card_ids": list(command.card_ids)},
            )
        )

    state.revision += 1
    for card_id in command.card_ids:
        player.hand_card_ids.remove(card_id)
        contact_id = card_contact_by_id[card_id]
        state.decks.customer_decks_by_contact[contact_id].discard_pile_card_ids.append(card_id)

    events: list[DomainEvent] = []
    _emit(state, events, CardsDiscarded, player_id=command.player_id, card_ids=command.card_ids)
    _finish_player_round(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))
