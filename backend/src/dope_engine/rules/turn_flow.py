"""The turn/phase state machine (RULES_CANONICAL.md §B): Tip-off, Action
Phase (3 rounds), Poker, Showdown, then back to Tip-off or into End Game
Scoring.

Poker never has matches to resolve (no Gamble card can be played yet)
and Showdown never actually resolves a Raid (that is Milestone 5, §D4).
Those phases still run — the turn genuinely advances through all of
them — they just have nothing to do yet. Real handlers replace the
stubs as each milestone lands.

A Link's extra action (§A5/§B2 "può fare un'azione extra, prima o dopo
l'azione principale, spendendo un Link") gets *two* offer points per
round, both funnelled through `ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION`:
right before the round's own Grit pick (`_enter_grit_or_extra_action_offer`,
the "prima" case) and right after the round's main action resolves
(`proceed_after_main_action`, the "dopo" case) — each is a cheap,
declinable offer (PassOptionalStep) so a player with no usable Link (or
who already used their one extra action this turn) skips straight
through. `PlayerState.extra_action_from_post_main` remembers which of
the two offer points is active, so declining/finishing resumes at the
right place (back to Grit, or on to hand-discard/round-end) instead of
re-offering in a loop.
"""

from __future__ import annotations

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import (
    ChooseGritAction,
    Command,
    DiscardCards,
    PassOptionalStep,
    SpendLinkForExtraAction,
)
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActiveStep, GamePhase, GameStatus, PawnRole
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    ActionRoundEnded,
    CardsDiscarded,
    DomainEvent,
    GameFinished,
    GritActionChosen,
    LinkPawnReturnedToBase,
    LinkSpentForExtraAction,
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
    bus.register(SpendLinkForExtraAction, _handle_spend_link_for_extra_action)
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
    _enter_grit_or_extra_action_offer(state, find_player(state, state.current_player_id))


def _player_has_link_pawn(state: GameState, player: PlayerState) -> bool:
    return any(state.pawns[pawn_id].role == PawnRole.LINK for pawn_id in player.pawn_ids)


def _enter_grit_or_extra_action_offer(state: GameState, player: PlayerState) -> None:
    """The "prima" offer point for a Link's extra action (module
    docstring): a cheap pre-check (owns *any* Link pawn) avoids the
    offer round-trip in the common case of a player with no Links yet;
    legal_actions.py still re-checks real per-Contact qualification once
    inside the offer, exactly like the main action's own Phase A."""
    if not player.extra_action_used_this_turn and _player_has_link_pawn(state, player):
        player.extra_action_from_post_main = False
        state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    else:
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
        _enter_grit_or_extra_action_offer(state, find_player(state, state.current_player_id))
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
    """The "dopo" offer point for a Link's extra action (module
    docstring) — offered once, right after the round's own main action
    resolves, before hand-discard/round-end. `finish_action_or_extra`
    (called by rules/economy.py and rules/officers.py at the end of
    every main-action-or-extra-action command) is this function's
    counterpart for completing an *already spent* extra action."""
    if not player.extra_action_used_this_turn and _player_has_link_pawn(state, player):
        player.extra_action_from_post_main = True
        state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
        return
    _continue_after_main_action(state, player, events)


def _is_players_last_round(state: GameState) -> bool:
    return state.action_round_index >= state.configuration["action_rounds_per_turn"]


def _continue_after_main_action(
    state: GameState, player: PlayerState, events: list[DomainEvent]
) -> None:
    # §17.4/CLAUDE.md point 22.29 (confirmed by the game designer,
    # 2026-08-01): the 5-card limit is only enforced at the end of a
    # player's own *turn* (their last of the 3 action rounds), not after
    # every round — a hand may legitimately sit above 5 between a
    # player's own rounds.
    over_limit = len(player.hand_card_ids) > state.configuration["max_hand_size"]
    if _is_players_last_round(state) and over_limit:
        state.active_step = ActiveStep.WAITING_FOR_HAND_DISCARD
    else:
        _finish_player_round(state, player, events)


def finish_action_or_extra(
    state: GameState, player: PlayerState, events: list[DomainEvent]
) -> None:
    """Common tail call for every main-action-or-extra-action command
    handler (rules/economy.py, rules/officers.py): a normal main action
    proceeds as usual; an extra action resumes wherever it was offered
    from — back to this round's own Grit pick ("prima"), or on to
    hand-discard/round-end ("dopo"), without re-offering the extra
    action again this turn. The spent Link itself already returned to
    its owner's Covo the moment it was chosen
    (`_handle_spend_link_for_extra_action`), not here."""
    player.pending_action_type = None
    link_pawn_id = player.extra_action_link_pawn_id
    if link_pawn_id is None:
        proceed_after_main_action(state, player, events)
        return

    from_post_main = player.extra_action_from_post_main
    player.extra_action_link_pawn_id = None
    player.extra_action_contact_id = None
    player.extra_action_from_post_main = False
    player.extra_action_used_this_turn = True
    player.current_round_grit_value = None

    if from_post_main:
        _continue_after_main_action(state, player, events)
    else:
        state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION


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
    expected = {
        ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS,
        ActiveStep.WAITING_FOR_HAND_DISCARD,
        ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION,
    }
    error = _validate(state, command, expected)
    if error is not None:
        return CommandFailure(error)

    player = find_player(state, command.player_id)
    events: list[DomainEvent] = []

    if state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS:
        state.revision += 1
        _emit(state, events, MainActionPassed, player_id=command.player_id)
        proceed_after_main_action(state, player, events)
    elif state.active_step == ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION:
        state.revision += 1
        if player.extra_action_link_pawn_id is not None:
            # The Link is already spent — and already back in its
            # owner's Covo, §A5 confirmed 2026-08-01 — so declining
            # from here on can never "get the Link back"; it just means
            # the extra action accomplishes nothing (e.g. its Contact's
            # allowed action types have zero legal targets right now).
            # Symmetric with a normal main action, which can always be
            # passed too, even mid-target-selection
            # (WAITING_FOR_MAIN_ACTION_TARGETS above).
            player.pending_action_type = None
            finish_action_or_extra(state, player, events)
        else:
            from_post_main = player.extra_action_from_post_main
            player.extra_action_from_post_main = False
            if from_post_main:
                _continue_after_main_action(state, player, events)
            else:
                state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION
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


def _handle_spend_link_for_extra_action(
    state: GameState, command: SpendLinkForExtraAction
) -> CommandOutcome:
    error = _validate(state, command, {ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION})
    if error is not None:
        return CommandFailure(error)

    player = find_player(state, command.player_id)
    if player.extra_action_link_pawn_id is not None:
        return CommandFailure(
            DomainError(
                code="extra_action_already_chosen",
                message="A Link was already chosen for this extra action.",
                details={},
            )
        )
    if player.extra_action_used_this_turn:
        return CommandFailure(
            DomainError(
                code="extra_action_already_used",
                message="The extra action was already used this turn.",
                details={},
            )
        )

    pawn = state.pawns.get(command.pawn_id)
    if pawn is None or pawn.owner_player_id != command.player_id or pawn.role != PawnRole.LINK:
        return CommandFailure(
            DomainError(
                code="pawn_not_eligible",
                message=f"Pawn '{command.pawn_id}' is not one of your Links.",
                details={},
            )
        )

    contact_id = pawn.contact_id
    link_level = pawn.link_level

    state.revision += 1
    player.pending_action_type = None
    player.current_round_grit_value = link_level
    player.extra_action_link_pawn_id = command.pawn_id
    player.extra_action_contact_id = contact_id

    events: list[DomainEvent] = []
    _emit(
        state,
        events,
        LinkSpentForExtraAction,
        player_id=command.player_id,
        pawn_id=command.pawn_id,
        contact_id=contact_id,
        link_level=link_level,
    )

    # §A5 (confirmed by the game designer, 2026-08-01): the spent Link
    # returns to its owner's Covo *immediately*, before the extra action
    # itself is even chosen/executed — not after it resolves. This is
    # what makes it structurally impossible for the extra action to ever
    # arrest/affect the very Link that's powering it: by the time any
    # sub-action runs, this pawn is already a plain Covo pawn, not a
    # Link a Fed/Cop lookup could ever find.
    pawn.role = PawnRole.IN_BASE
    pawn.contact_id = None
    pawn.link_level = None
    pawn.location = PawnLocation.base()
    _emit(
        state, events, LinkPawnReturnedToBase, player_id=command.player_id, pawn_id=command.pawn_id
    )

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
