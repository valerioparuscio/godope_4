"""Follow-ups that run once a move package is done (game designer, 2026-10-15).

- Card 26 "BADGE HUNT": every pawn that enters a Hood with Cops may move one of those Cops to
  an adjacent Hood, paying $1 (optional; one Cop per entering pawn).
- Cards 36 "AFTERSHOCK" and 37 "FOLLOW ME" (after a Rissa the winner won): corrupt the Cop that
  just entered (7$, into the Covo) / place a Criminal in the Rissa's Hood for free (draws a
  card, respects the limit of 4) — both optional, queued by `rules/brawl.py`.
- Card 32 "SEAT SWAP": a pawn that enters the Den may swap places with one opposing Gambler:
  that Gambler comes out as a Criminal into the Hood the pawn left (works with a full Den;
  then the swap is mandatory, since the Den would otherwise be over capacity).

`note_*` record what happened while the moves are applied (`rules/movement.py`);
`begin` is called from the tail of the move package (also when a Rissa interrupted it) and,
if any follow-up is still doable, opens `ActiveStep.WAITING_FOR_MOVE_FOLLOWUP`, which
`PlayerState.pending_move_followups` drives one entry at a time.
"""

from __future__ import annotations

from typing import Any

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import ResolveMoveFollowup
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, GamePhase, PawnRole
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    CriminalPlaced,
    DomainEvent,
    GamblerBecameCriminal,
    OfficerMoved,
)
from dope_engine.domain.ids import HoodId, PawnId
from dope_engine.domain.state import (
    GameState,
    PlayerState,
    find_player,
    max_pawns_per_player_per_hood,
    officer_count_in_base,
    own_pawns_in_hood,
)
from dope_engine.rules import economy, officers, skills, turn_flow
from dope_engine.rules.event_utils import emit as _emit

BADGE_HUNT_COST = 1


def note_entered_hood(state: GameState, player: PlayerState, hood_id: HoodId) -> None:
    """A pawn of `player` just entered `hood_id` (Hood move, Gambler out of the Den, Link split)."""
    boost = player.active_card_boost
    if boost is None or boost["type"] != "badge_hunt":
        return
    if state.board.hoods[hood_id].cop_ids:
        player.pending_move_followups.append({"kind": "badge_hunt", "hood_id": hood_id})


def note_den_entry(
    state: GameState, player: PlayerState, pawn_id: PawnId, from_hood_id: HoodId
) -> None:
    boost = player.active_card_boost
    if boost is None or boost["type"] != "den_seat_swap":
        return
    over_capacity = len(state.board.den_gambler_pawn_ids) > state.configuration["den_capacity"]
    player.pending_move_followups.append(
        {
            "kind": "den_swap",
            "pawn_id": pawn_id,
            "from_hood_id": from_hood_id,
            "mandatory": over_capacity,
        }
    )


def enemy_gamblers_swappable(
    state: GameState, player: PlayerState, from_hood_id: HoodId
) -> list[PawnId]:
    """Opposing Gamblers that could come out into `from_hood_id` (respecting the per-player
    Hood limit of their owner)."""
    limit = max_pawns_per_player_per_hood(state.configuration)
    return [
        pid
        for pid in state.board.den_gambler_pawn_ids
        if state.pawns[pid].owner_player_id != player.player_id
        and own_pawns_in_hood(state, state.pawns[pid].owner_player_id, from_hood_id) < limit
    ]


def options(state: GameState, player: PlayerState, entry: dict[str, Any]) -> list[dict[str, Any]]:
    """The doable choices of one follow-up entry, as option payloads."""
    if entry["kind"] == "badge_hunt":
        if player.money < BADGE_HUNT_COST:
            return []
        hood = state.board.hoods[entry["hood_id"]]
        return [
            {
                "kind": "badge_hunt",
                "officer_id": officer_id,
                "destination_hood_id": adjacent_id,
            }
            for officer_id in hood.cop_ids
            for adjacent_id in hood.adjacent_hood_ids
            if state.board.hoods[adjacent_id].revealed
        ]
    if entry["kind"] == "aftershock":
        return _aftershock_options(state, player, entry)
    if entry["kind"] == "follow_me":
        return _follow_me_options(state, player, entry)
    if entry["pawn_id"] not in state.board.den_gambler_pawn_ids:
        return []
    return [
        {"kind": "den_swap", "gambler_pawn_id": pid}
        for pid in enemy_gamblers_swappable(state, player, entry["from_hood_id"])
    ]


def _presence_pawn(state: GameState, player: PlayerState, hood_id: HoodId) -> PawnId | None:
    return next(
        (
            pid
            for pid in player.pawn_ids
            if state.pawns[pid].role in (PawnRole.CRIMINAL, PawnRole.LINK)
            and economy.has_presence_at_hood(state, state.pawns[pid], hood_id)
        ),
        None,
    )


def _aftershock_options(
    state: GameState, player: PlayerState, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    officer_id = entry["officer_id"]
    officer = state.board.officers.get(officer_id)
    hood = state.board.hoods[entry["hood_id"]]
    if officer is None or officer_id not in hood.cop_ids:
        return []
    price = skills.effective_cost(
        state, player, ActionType.CORRUPT_OFFICER, state.configuration["costs"]["corrupt_officer"]
    )
    cap = state.configuration["base_max_chips_per_category"]
    if (
        player.money < price
        or officer_count_in_base(state, player.player_id) >= cap
        or _presence_pawn(state, player, hood.hood_id) is None
    ):
        return []
    return [{"kind": "aftershock", "officer_id": officer_id}]


def _follow_me_options(
    state: GameState, player: PlayerState, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    hood = state.board.hoods[entry["hood_id"]]
    limit = state.configuration["brawl_trigger_criminal_count"] - 1
    if (
        not hood.revealed
        or len(hood.criminal_pawn_ids) >= limit
        or own_pawns_in_hood(state, player.player_id, hood.hood_id)
        >= max_pawns_per_player_per_hood(state.configuration)
        or not any(state.pawns[pid].role == PawnRole.IN_BASE for pid in player.pawn_ids)
    ):
        return []
    return [{"kind": "follow_me", "destination_hood_id": hood.hood_id}]


def can_pass(entry: dict[str, Any]) -> bool:
    return not entry.get("mandatory", False)


def _prune(state: GameState, player: PlayerState) -> None:
    """Drops entries that cannot be done (anymore); a mandatory swap with no one to swap
    with is dropped too, since then nothing could be done about the over-full Den — it is
    refused up front by the option generator instead."""
    player.pending_move_followups = [
        entry
        for entry in player.pending_move_followups
        if options(state, player, entry)
    ]


def begin(state: GameState, player: PlayerState) -> bool:
    """Opens the follow-up step when something is still doable; clears the list otherwise."""
    _prune(state, player)
    if not player.pending_move_followups:
        return False
    state.active_step = ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    return True


def _continue(state: GameState, player: PlayerState, events: list[DomainEvent]) -> None:
    _prune(state, player)
    if player.pending_move_followups:
        state.active_step = ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
        return
    player.pending_action_type = None
    turn_flow.finish_action_or_extra(state, player, events)


def pass_head(
    state: GameState, player: PlayerState, events: list[DomainEvent]
) -> DomainError | None:
    """`PassOptionalStep` at this step: declines the current follow-up."""
    entry = player.pending_move_followups[0]
    if not can_pass(entry):
        return DomainError(
            code="followup_mandatory",
            message="The Den is over capacity: you must swap with an opposing Gambler.",
            details={},
        )
    player.pending_move_followups.pop(0)
    _continue(state, player, events)
    return None


def _handle_resolve(state: GameState, command: ResolveMoveFollowup) -> CommandOutcome:
    if state.phase != GamePhase.ACTION_PHASE:
        return CommandFailure(wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(wrong_player(str(state.current_player_id), str(command.player_id)))
    if state.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message=(
                    f"Not waiting for a move follow-up (state is at '{state.active_step.value}')."
                ),
                details={"actual_step": state.active_step.value},
            )
        )
    player = find_player(state, command.player_id)
    if not player.pending_move_followups:
        return CommandFailure(
            DomainError(code="no_followup", message="No follow-up is pending.", details={})
        )
    entry = player.pending_move_followups[0]
    choice_fields: dict[str, dict[str, Any]] = {
        "badge_hunt": {
            "officer_id": command.officer_id,
            "destination_hood_id": command.destination_hood_id,
        },
        "den_swap": {"gambler_pawn_id": command.gambler_pawn_id},
        "aftershock": {"officer_id": command.officer_id},
        "follow_me": {"destination_hood_id": command.destination_hood_id},
    }
    choice = {"kind": command.kind, **choice_fields.get(command.kind, {})}
    if choice not in options(state, player, entry):
        return CommandFailure(
            DomainError(
                code="followup_choice_not_allowed",
                message="That choice is not available for this follow-up.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []
    player.pending_move_followups.pop(0)
    if entry["kind"] == "badge_hunt":
        hood = state.board.hoods[entry["hood_id"]]
        officer = state.board.officers[command.officer_id]  # type: ignore[index]
        destination = state.board.hoods[command.destination_hood_id]  # type: ignore[index]
        player.money -= BADGE_HUNT_COST
        hood.cop_ids.remove(officer.officer_id)
        officer.hood_id = destination.hood_id
        destination.cop_ids.append(officer.officer_id)
        _emit(
            state, events, OfficerMoved, officer_id=officer.officer_id, hood_id=destination.hood_id
        )
        economy.check_hood_cop_removal(state, hood, events)
    elif entry["kind"] == "aftershock":
        officer = state.board.officers[command.officer_id]  # type: ignore[index]
        pawn_id = _presence_pawn(state, player, entry["hood_id"])
        assert pawn_id is not None
        error = officers.corrupt_officer_into_base(
            state, player, state.pawns[pawn_id], officer, events
        )
        if error is not None:
            return CommandFailure(error)
    elif entry["kind"] == "follow_me":
        hood = state.board.hoods[entry["hood_id"]]
        placed_id = next(
            pid for pid in sorted(player.pawn_ids) if state.pawns[pid].role == PawnRole.IN_BASE
        )
        placed = state.pawns[placed_id]
        placed.role = PawnRole.CRIMINAL
        placed.location = PawnLocation.hood(hood.hood_id)
        hood.criminal_pawn_ids.append(placed_id)
        _emit(
            state,
            events,
            CriminalPlaced,
            player_id=player.player_id,
            pawn_id=placed_id,
            hood_id=hood.hood_id,
            cost=0,
        )
        economy.draw_card(state, hood.contact_id, events, player.player_id)
    else:
        enemy = state.pawns[command.gambler_pawn_id]  # type: ignore[index]
        from_hood = state.board.hoods[entry["from_hood_id"]]
        state.board.den_gambler_pawn_ids.remove(enemy.pawn_id)
        enemy.role = PawnRole.CRIMINAL
        enemy.location = PawnLocation.hood(from_hood.hood_id)
        from_hood.criminal_pawn_ids.append(enemy.pawn_id)
        _emit(
            state,
            events,
            GamblerBecameCriminal,
            player_id=enemy.owner_player_id,
            pawn_id=enemy.pawn_id,
            hood_id=from_hood.hood_id,
        )

    _continue(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def register_handlers(bus: CommandBus) -> None:
    bus.register(ResolveMoveFollowup, _handle_resolve)
