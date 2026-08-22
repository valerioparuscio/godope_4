"""The turn/phase state machine (RULES_CANONICAL.md §B): Tip-off, Action
Phase (3 rounds), Poker, Showdown, then back to Tip-off or into End Game
Scoring.

Tip-off reveals the turn's Raid card and, if any player currently holds
a Preti Link, pauses for them to choose the round's first player (§D4 —
`ChooseRaidFirstPlayer`, `WAITING_FOR_RAID_RESOLUTION`) before entering
the Action Phase; Showdown resolves that Raid (`rules/raids.py::
resolve_raid`, staining REP for the losing team) before the turn ends.
End Game Scoring is still a stub (Milestone 5, not yet implemented) —
real handlers replace it once it lands.

A round has *two* optional offer points, right before the round's own
Grit pick (`_enter_grit_or_extra_action_offer`, the "prima" case) and
right after the round's main action resolves (`proceed_after_main_action`,
the "dopo" case) — each a cheap, declinable check (PassOptionalStep) so a
player who doesn't qualify for anything skips straight through:
1. **Stain-for-cash** (§D5, Milestone 5): `WAITING_FOR_STAIN_FOR_CASH_OFFER`
   — a player with `stain_rep_for_cash.money_threshold` dollars or fewer
   and at least one clean REP token may flip one for cash
   (`StainReputationForMoney`). `PlayerState.stain_offer_from_post_main`
   tracks which offer point is active.
2. **Link extra action** (§A5/§B2 "può fare un'azione extra, prima o
   dopo l'azione principale, spendendo un Link"):
   `WAITING_FOR_LINK_EXTRA_ACTION`. `PlayerState.extra_action_from_post_main`
   tracks which offer point is active.

Declining/finishing either resumes at the right place (the next check in
the same offer point, or on to hand-discard/round-end) instead of
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
    ChooseRaidFirstPlayer,
    Command,
    DiscardCards,
    PassOptionalStep,
    SpendLinkForExtraAction,
    StainReputationForMoney,
)
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActiveStep, GamePhase, GameStatus, PawnRole
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    ActionRoundEnded,
    CardsDiscarded,
    DomainEvent,
    FinalScoreCalculated,
    GameFinished,
    GritActionChosen,
    LinkPawnReturnedToBase,
    LinkSpentForExtraAction,
    MainActionPassed,
    PokerPhaseResolved,
    RaidFirstPlayerChosen,
    RaidRevealed,
    ShowdownPhaseResolved,
    TurnEnded,
    TurnStarted,
)
from dope_engine.domain.ids import CardId, ContactId, PlayerId
from dope_engine.domain.state import GameState, PlayerState, find_player
from dope_engine.rules import links, raids, scoring, skills
from dope_engine.rules.event_utils import emit as _emit
from dope_engine.rules.event_utils import emit_skill_effects

PRETI_CONTACT_ID = ContactId("preti")


def register_handlers(bus: CommandBus, *, card_contact_by_id: dict[CardId, ContactId]) -> None:
    bus.register(ChooseGritAction, _handle_choose_grit_action)
    bus.register(PassOptionalStep, _handle_pass_optional_step)
    bus.register(SpendLinkForExtraAction, _handle_spend_link_for_extra_action)
    bus.register(ChooseRaidFirstPlayer, _handle_choose_raid_first_player)
    bus.register(StainReputationForMoney, _handle_stain_reputation_for_money)
    bus.register(
        DiscardCards,
        lambda state, command: _handle_discard_cards(state, command, card_contact_by_id),
    )


def _highest_preti_link_owner(state: GameState) -> PlayerId | None:
    preti_links = [
        pawn
        for pawn in state.pawns.values()
        if pawn.role == PawnRole.LINK and pawn.contact_id == PRETI_CONTACT_ID
    ]
    if not preti_links:
        return None
    # §A5 (corrected 2026-08-01): a Contact's Link levels are globally
    # unique (shared across players), so there is always at most one
    # pawn at the highest occupied level — no tie-break needed.
    return max(preti_links, key=lambda pawn: pawn.link_level or 0).owner_player_id


def start_tip_off(state: GameState, events: list[DomainEvent]) -> None:
    """Reveal this turn's Raid card, then either let the highest Preti
    Link's owner decide the first player (§D4 — pausing at
    `WAITING_FOR_RAID_RESOLUTION`) or, if nobody holds one, enter the
    Action Phase directly with `first_player_id` unchanged (the
    documented fallback: "resta primo chi lo era nel turno precedente").
    """
    state.phase = GamePhase.TIP_OFF
    state.active_step = ActiveStep.NONE
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

    chooser_id = _highest_preti_link_owner(state)
    if chooser_id is not None:
        state.active_step = ActiveStep.WAITING_FOR_RAID_RESOLUTION
        state.current_player_id = chooser_id
        return
    _finish_tip_off(state, events)


def _finish_tip_off(state: GameState, events: list[DomainEvent]) -> None:
    _emit(
        state,
        events,
        TurnStarted,
        turn_index=state.turn_index,
        first_player_id=state.first_player_id,
    )
    _start_action_phase(state)


def _handle_choose_raid_first_player(
    state: GameState, command: ChooseRaidFirstPlayer
) -> CommandOutcome:
    if state.phase != GamePhase.TIP_OFF:
        return CommandFailure(wrong_phase(GamePhase.TIP_OFF.value, state.phase.value))
    if state.active_step != ActiveStep.WAITING_FOR_RAID_RESOLUTION:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message=f"Not waiting for a Raid first-player choice "
                f"(state is at '{state.active_step.value}').",
                details={"actual_step": state.active_step.value},
            )
        )
    if state.current_player_id != command.player_id:
        return CommandFailure(wrong_player(str(state.current_player_id), str(command.player_id)))
    if command.chosen_first_player_id not in state.player_order:
        return CommandFailure(
            DomainError(
                code="unknown_player",
                message=f"'{command.chosen_first_player_id}' is not a player in this game.",
                details={},
            )
        )

    state.revision += 1
    state.first_player_id = command.chosen_first_player_id
    events: list[DomainEvent] = []
    _emit(
        state,
        events,
        RaidFirstPlayerChosen,
        chooser_player_id=command.player_id,
        chosen_first_player_id=command.chosen_first_player_id,
    )
    _finish_tip_off(state, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _start_action_phase(state: GameState) -> None:
    state.phase = GamePhase.ACTION_PHASE
    for player in state.players:
        player.available_grit_values = list(state.configuration["grit_values"])
        player.moved_pawn_ids_this_turn = []
        player.action_types_used_this_turn = []
    _start_new_round(state, 1)


def _start_new_round(state: GameState, round_index: int) -> None:
    state.action_round_index = round_index
    for player in state.players:
        player.gamble_cards_played_this_round = 0
        player.pending_action_type = None
        player.current_round_grit_value = None
        # §A5 (2026-08-17): the Link extra action's cap resets every
        # round now, not once per whole turn — see PlayerState.
        # extra_actions_used_this_round's own docstring.
        player.extra_actions_used_this_round = 0
    state.current_player_id = state.first_player_id
    _enter_grit_or_extra_action_offer(state, find_player(state, state.current_player_id))


def _player_has_link_pawn(state: GameState, player: PlayerState) -> bool:
    return any(state.pawns[pawn_id].role == PawnRole.LINK for pawn_id in player.pawn_ids)


def _enter_grit_or_extra_action_offer(state: GameState, player: PlayerState) -> None:
    """The "prima" offer point for a round (module docstring): first a
    voluntary stain-for-cash check (§D5, Milestone 5 — cheap and
    independent of Links), then the Link extra action, then the round's
    own Grit pick."""
    if raids.player_can_stain_for_cash(state, player.player_id):
        player.stain_offer_from_post_main = False
        state.active_step = ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER
        return
    _enter_extra_action_or_grit(state, player)


def _enter_extra_action_or_grit(state: GameState, player: PlayerState) -> None:
    """A cheap pre-check (owns *any* Link pawn) avoids the offer
    round-trip in the common case of a player with no Links yet;
    legal_actions.py still re-checks real per-Contact qualification once
    inside the offer, exactly like the main action's own Phase A."""
    if player.extra_actions_used_this_round < skills.max_link_extra_actions_per_round(
        state, player
    ) and _player_has_link_pawn(state, player):
        player.extra_action_from_post_main = False
        state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    else:
        state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION


def _rotation_order(state: GameState) -> list[PlayerId]:
    start = state.player_order.index(state.first_player_id)
    return state.player_order[start:] + state.player_order[:start]


def _finish_player_round(state: GameState, player: PlayerState, events: list[DomainEvent]) -> None:
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
    from dope_engine.rules import poker

    poker.enter_poker_phase(state, events)


def finish_poker_phase(state: GameState, events: list[DomainEvent]) -> None:
    """Called by rules/poker.py once every match launched this turn (if
    any) has been bet on, revealed and resolved."""
    state.poker.matches_this_turn = []
    _emit(state, events, PokerPhaseResolved, turn_index=state.turn_index)
    _enter_showdown_phase(state, events)


def _enter_showdown_phase(state: GameState, events: list[DomainEvent]) -> None:
    state.phase = GamePhase.SHOWDOWN_PHASE
    raids.resolve_raid(state, events)
    _emit(state, events, ShowdownPhaseResolved, turn_index=state.turn_index)
    _end_turn(state, events)


def _end_turn(state: GameState, events: list[DomainEvent]) -> None:
    _emit(state, events, TurnEnded, turn_index=state.turn_index)
    if state.turn_index >= state.configuration["num_turns"]:
        # Doesn't compute the score or mark the game FINISHED here
        # directly — `rules/jobs.py`'s post-success hook (which always
        # runs right after this command, CLAUDE.md §11.12) needs its own
        # chance to complete any Job the last turn's own Poker/Raid
        # resolution just satisfied, *before* scoring locks in. Setting
        # this marker is enough: `finalize_game_if_ready` below is called
        # from that hook unconditionally, and finalizes as soon as
        # nothing is left pending — immediately, in the common case where
        # nothing new completed here.
        state.pending_game_end = True
        return

    state.turn_index += 1
    start_tip_off(state, events)


def finalize_game_if_ready(state: GameState, events: list[DomainEvent]) -> None:
    """Computes the final score and marks the game FINISHED, but only
    once `_end_turn` has set `pending_game_end` (the last turn ended)
    *and* no Job reward is left pending — called unconditionally from
    `rules/jobs.py`'s post-success hook (which runs after every command,
    including every `ChooseJobReward` claim), so it naturally waits out
    however many completions the last turn's own Poker/Raid resolution
    triggered before actually finalizing. A no-op the vast majority of
    the time (`pending_game_end` only True right after the last turn's
    own `_end_turn` call, one command)."""
    if not state.pending_game_end or state.pending_job_reward is not None:
        return
    state.pending_game_end = False
    state.phase = GamePhase.END_GAME_SCORING
    state.active_step = ActiveStep.NONE
    state.final_score = scoring.compute_final_score(state)
    _emit(state, events, FinalScoreCalculated, winner_ids=state.final_score.winner_ids)

    state.phase = GamePhase.FINISHED
    state.status = GameStatus.FINISHED
    _emit(
        state,
        events,
        GameFinished,
        turn_index=state.turn_index,
        winner_ids=state.final_score.winner_ids,
    )


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
                f"Expected active_step in [{expected}], state is at '{state.active_step.value}'."
            ),
            details={"expected_steps": expected, "actual_step": state.active_step.value},
        )
    return None


def proceed_after_main_action(
    state: GameState, player: PlayerState, events: list[DomainEvent]
) -> None:
    """The "dopo" offer point for a round (module docstring) — a
    stain-for-cash check, then a Link's extra action, offered once each
    right after the round's own main action resolves, before
    hand-discard/round-end. `finish_action_or_extra` (called by
    rules/economy.py and rules/officers.py at the end of every
    main-action-or-extra-action command) is this function's counterpart
    for completing an *already spent* extra action."""
    if raids.player_can_stain_for_cash(state, player.player_id):
        player.stain_offer_from_post_main = True
        state.active_step = ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER
        return
    _extra_action_or_continue_after_main(state, player, events)


def _extra_action_or_continue_after_main(
    state: GameState, player: PlayerState, events: list[DomainEvent]
) -> None:
    if player.extra_actions_used_this_round < skills.max_link_extra_actions_per_round(
        state, player
    ) and _player_has_link_pawn(state, player):
        player.extra_action_from_post_main = True
        state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
        return
    _continue_after_main_action(state, player, events)


def _continue_after_main_action(
    state: GameState, player: PlayerState, events: list[DomainEvent]
) -> None:
    # RULES_PENDING.md #12/#17 REVERSED (game designer, 2026-08-15): the
    # 5-card limit is enforced at the end of *every* round now, not just
    # a player's last of the 3 per turn — superseding the 2026-08-01
    # decision this comment used to cite.
    over_limit = len(player.hand_card_ids) > state.configuration["max_hand_size"]
    if over_limit:
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
    if player.extra_actions_used_this_round >= 1:
        # §A10 Politici-3: the base cap is 1 Link extra action per round
        # (§A5), so reaching a 2nd (or later) one this round only ever
        # happens because this Skill raised the cap.
        emit_skill_effects(
            state,
            events,
            player.player_id,
            skills.matching_skill_ids(state, player, "extra_link_action_slot"),
        )
    player.extra_actions_used_this_round += 1
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
                    f"Grit value {command.grit_value} is not available for '{command.player_id}'."
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
        ActiveStep.WAITING_FOR_POKER_LAUNCH,
        ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER,
        ActiveStep.WAITING_FOR_CARD_USAGE,
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
    elif state.active_step == ActiveStep.WAITING_FOR_POKER_LAUNCH:
        state.revision += 1
        return_step = player.poker_launch_return_step
        assert return_step is not None
        player.poker_launch_return_step = None
        state.active_step = return_step
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
    elif state.active_step == ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER:
        state.revision += 1
        from_post_main = player.stain_offer_from_post_main
        player.stain_offer_from_post_main = False
        if from_post_main:
            _extra_action_or_continue_after_main(state, player, events)
        else:
            _enter_extra_action_or_grit(state, player)
    elif state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE:
        # §D3 Marketing (2026-08-17: "before" only, see
        # `rules/economy.py::_finish_buy_or_sell_package`'s docstring) —
        # declining just resumes target selection (the package's own
        # price step hasn't happened yet, so there's nothing to apply).
        # Covers both declining the "which card" sub-step (game designer,
        # 2026-08-15) and declining the Stonk-allocation step itself, so
        # the chosen-card marker is cleared here regardless of which one
        # was active.
        state.revision += 1
        player.marketing_chosen_card_id = None
        player.marketing_offer_is_pre = False
        return_step = player.marketing_pre_return_step
        assert return_step is not None
        player.marketing_pre_return_step = None
        state.active_step = return_step
    else:
        overflow = len(player.hand_card_ids) - state.configuration["max_hand_size"]
        if overflow > 0:
            return CommandFailure(
                DomainError(
                    code="must_discard",
                    message=(
                        f"Hand has {overflow} card(s) over the limit; must discard before passing."
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
    if player.extra_actions_used_this_round >= skills.max_link_extra_actions_per_round(
        state, player
    ):
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

    assert pawn.contact_id is not None  # always set for a PawnRole.LINK, just checked above
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
    links.check_spot_fed_removal_for_contact(state, contact_id, events)

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


def _handle_stain_reputation_for_money(
    state: GameState, command: StainReputationForMoney
) -> CommandOutcome:
    error = _validate(state, command, {ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER})
    if error is not None:
        return CommandFailure(error)

    player = find_player(state, command.player_id)
    if not raids.player_can_stain_for_cash(state, player.player_id):
        return CommandFailure(
            DomainError(
                code="cannot_stain_for_cash",
                message="Not eligible to stain a REP token for cash right now.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []
    raids.stain_one_clean_token(state, player.player_id, events)
    player.money += state.configuration["stain_rep_for_cash"]["cash_gained"]

    from_post_main = player.stain_offer_from_post_main
    player.stain_offer_from_post_main = False
    if from_post_main:
        _extra_action_or_continue_after_main(state, player, events)
    else:
        _enter_extra_action_or_grit(state, player)

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))
