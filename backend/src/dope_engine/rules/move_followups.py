"""Follow-ups that run once a move package is done (game designer, 2026-10-15).

- Card 26 "BADGE HUNT": every pawn that enters a Hood with Cops may move one of those Cops to
  an adjacent Hood, paying $1 (optional; one Cop per entering pawn).
- Cards 36 "AFTERSHOCK" and 37 "FOLLOW ME" (after a Rissa the winner won): corrupt the Cop that
  just entered (7$, into the Covo) / place a Criminal in the Rissa's Hood for free (draws a
  card, respects the limit of 4) — both optional, queued by `rules/brawl.py`.
- Cards 50 "BADGE HIRE", 51/57 "EXPANSION"/"FLASH MOB" and 54 "DECOY" (after a placement):
  corrupt a Cop where a pawn was just placed (optional) / move one placed pawn to an adjacent
  Hood for free (optional) / make a Cop enter a Hood where pawns were placed (mandatory),
  queued by `rules/economy.py`.
- Cards 81 "FULL CONTROL" (with Grit 3, one free corruption of an officer maneuvered in the
  action), 85 "ESCORT" (a Criminal of yours makes the same trip as a Cop you moved) and 91
  "BACKROOM DEAL" (the pawn that maneuvered a Cop goes to the Den, automatically), queued by
  `rules/officers.py` and opened when the maneuver action ends.
- Cards 86 "VACANCY", 94 "RIOT", 89 "FIXER", 90 "CONNECTION", 92 "SAFE PASSAGE", 96 "LAST JOB"
  and 98 "COVER" (after corrupting a Cop/Fed): see `officers._note_corrupt_cards`.
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
from dope_engine.domain.entities import OfficerLocationType, PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, GamePhase, PawnRole
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    CriminalPlaced,
    DomainEvent,
    GamblerBecameCriminal,
    OfficerMoved,
)
from dope_engine.domain.ids import DEN_ID, HoodId, PawnId
from dope_engine.domain.state import (
    GameState,
    PlayerState,
    find_player,
    max_pawns_per_player_per_hood,
    officer_count_in_base,
    own_pawns_in_hood,
)
from dope_engine.rules import economy, jail, links, officers, skills, turn_flow
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
    if entry["kind"] == "badge_hire":
        return _corrupt_options(state, player, entry["hood_ids"], "badge_hire")
    if entry["kind"] == "full_control":
        return _full_control_options(state, player, entry)
    if entry["kind"] == "vacancy":
        return _vacancy_options(state, player, entry)
    if entry["kind"] == "fixer":
        pawn = state.pawns[entry["pawn_id"]]
        if pawn.role == PawnRole.LINK and (pawn.link_level or 3) < 3:
            return [{"kind": "fixer", "pawn_id": pawn.pawn_id}]
        return []
    if entry["kind"] == "connection":
        pawn = state.pawns[entry["pawn_id"]]
        if pawn.role == PawnRole.CRIMINAL and pawn.pawn_id not in player.moved_pawn_ids_this_turn:
            return [{"kind": "connection", "pawn_id": pawn.pawn_id}]
        return []
    if entry["kind"] == "last_job":
        if not jail.has_free_rat_slot(state):
            return []
        return [
            {"kind": "last_job", "pawn_id": pid}
            for pid in state.board.hoods[entry["hood_id"]].criminal_pawn_ids
        ]
    if entry["kind"] == "cover":
        return _cover_options(state, player, entry)
    if entry["kind"] == "escort":
        return _escort_options(state, player, entry)
    if entry["kind"] == "backroom":
        return _backroom_options(state, player, entry)
    if entry["kind"] == "expansion":
        return _expansion_options(state, player, entry)
    if entry["kind"] == "decoy":
        return [
            {"kind": "decoy", "destination_hood_id": hood_id}
            for hood_id in entry["hood_ids"]
            if state.board.hoods[hood_id].revealed
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


def _place_free_criminal(
    state: GameState,
    player: PlayerState,
    hood: Any,
    events: list[DomainEvent],
    cost: int,
) -> None:
    """Places a Covo pawn as a Criminal of `hood` and draws from its Contact's deck."""
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
        cost=cost,
    )
    economy.draw_card(state, hood.contact_id, events, player.player_id)


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


def _corrupt_options(
    state: GameState, player: PlayerState, hood_ids: list[HoodId], kind: str
) -> list[dict[str, Any]]:
    price = skills.effective_cost(
        state, player, ActionType.CORRUPT_OFFICER, state.configuration["costs"]["corrupt_officer"]
    )
    cap = state.configuration["base_max_chips_per_category"]
    if player.money < price or officer_count_in_base(state, player.player_id) >= cap:
        return []
    return [
        {"kind": kind, "officer_id": officer_id}
        for hood_id in hood_ids
        if _presence_pawn(state, player, hood_id) is not None
        for officer_id in state.board.hoods[hood_id].cop_ids
    ]


def _corrupting_pawn(
    state: GameState, player: PlayerState, officer: Any
) -> PawnId | None:
    """A Criminal/Link of the player with the presence needed to corrupt `officer`."""
    for pid in player.pawn_ids:
        pawn = state.pawns[pid]
        if pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK):
            continue
        if officer.hood_id is not None and officers.has_presence_at_hood(
            state, pawn, officer.hood_id
        ):
            return pid
        if officer.spot_id is not None and officers.has_presence_at_spot(
            state, pawn, officer.spot_id
        ):
            return pid
    return None


def _full_control_options(
    state: GameState, player: PlayerState, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    cap = state.configuration["base_max_chips_per_category"]
    if officer_count_in_base(state, player.player_id) >= cap:
        return []
    result = []
    for officer_id in entry["officer_ids"]:
        officer = state.board.officers.get(officer_id)
        if officer is None or officer.location_type == OfficerLocationType.BASE:
            continue
        if _corrupting_pawn(state, player, officer) is not None:
            result.append({"kind": "full_control", "officer_id": officer_id})
    return result


def _vacancy_options(
    state: GameState, player: PlayerState, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    destination = state.board.hoods[entry["hood_id"]]
    limit = max_pawns_per_player_per_hood(state.configuration)
    if (
        not destination.revealed
        or len(destination.criminal_pawn_ids) >= destination.capacity
        or own_pawns_in_hood(state, player.player_id, destination.hood_id) >= limit
    ):
        return []
    sources = [h.hood_id for h in state.board.hoods.values() if h.revealed]
    return [
        {"kind": "vacancy", "pawn_id": pid, "destination_hood_id": destination.hood_id}
        for source_id in sources
        if source_id != destination.hood_id
        for pid in state.board.hoods[source_id].criminal_pawn_ids
        if state.pawns[pid].owner_player_id == player.player_id
        and pid not in player.moved_pawn_ids_this_turn
    ]


def _cover_options(
    state: GameState, player: PlayerState, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    cost = skills.effective_cost(
        state, player, ActionType.PLACE_CRIMINAL, state.configuration["costs"]["place_criminal"]
    )
    if player.money < cost:
        return []
    return _follow_me_options(
        state, player, {"kind": "cover", "hood_id": entry["hood_id"]}, kind="cover"
    )


def _escort_options(
    state: GameState, player: PlayerState, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    destination = state.board.hoods[entry["to_hood_id"]]
    limit = max_pawns_per_player_per_hood(state.configuration)
    if (
        not destination.revealed
        or len(destination.criminal_pawn_ids) >= destination.capacity
        or own_pawns_in_hood(state, player.player_id, destination.hood_id) >= limit
    ):
        return []
    origin = state.board.hoods[entry["from_hood_id"]]
    return [
        {"kind": "escort", "pawn_id": pid, "destination_hood_id": destination.hood_id}
        for pid in origin.criminal_pawn_ids
        if state.pawns[pid].owner_player_id == player.player_id
        and pid not in player.moved_pawn_ids_this_turn
    ]


def _backroom_options(
    state: GameState, player: PlayerState, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    pawn_id = entry["pawn_id"]
    pawn = state.pawns[pawn_id]
    own_in_den = sum(
        1
        for pid in state.board.den_gambler_pawn_ids
        if state.pawns[pid].owner_player_id == player.player_id
    )
    if (
        pawn.role != PawnRole.CRIMINAL
        or pawn_id in player.moved_pawn_ids_this_turn
        or len(state.board.den_gambler_pawn_ids) >= state.configuration["den_capacity"]
        or own_in_den >= state.configuration["den_capacity_per_player"]
    ):
        return []
    return [
        {"kind": "backroom", "pawn_id": pawn_id, "deck_contact_id": contact_id}
        for contact_id in state.decks.customer_decks_by_contact
    ]


def _expansion_options(
    state: GameState, player: PlayerState, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    limit = max_pawns_per_player_per_hood(state.configuration)
    result: list[dict[str, Any]] = []
    for pawn_id in entry["pawn_ids"]:
        pawn = state.pawns[pawn_id]
        if pawn.role != PawnRole.CRIMINAL or pawn_id in player.moved_pawn_ids_this_turn:
            continue
        hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
        for adjacent_id in hood.adjacent_hood_ids:
            adjacent = state.board.hoods[adjacent_id]
            if (
                adjacent.revealed
                and len(adjacent.criminal_pawn_ids) < adjacent.capacity
                and own_pawns_in_hood(state, player.player_id, adjacent_id) < limit
            ):
                result.append(
                    {"kind": "expansion", "pawn_id": pawn_id, "destination_hood_id": adjacent_id}
                )
    return result


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
    state: GameState, player: PlayerState, entry: dict[str, Any], kind: str = "follow_me"
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
    return [{"kind": kind, "destination_hood_id": hood.hood_id}]


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
        "badge_hire": {"officer_id": command.officer_id},
        "expansion": {
            "pawn_id": command.pawn_id,
            "destination_hood_id": command.destination_hood_id,
        },
        "escort": {
            "pawn_id": command.pawn_id,
            "destination_hood_id": command.destination_hood_id,
        },
        "backroom": {"pawn_id": command.pawn_id, "deck_contact_id": command.deck_contact_id},
        "full_control": {"officer_id": command.officer_id},
        "vacancy": {
            "pawn_id": command.pawn_id,
            "destination_hood_id": command.destination_hood_id,
        },
        "fixer": {"pawn_id": command.pawn_id},
        "connection": {"pawn_id": command.pawn_id},
        "last_job": {"pawn_id": command.pawn_id},
        "cover": {"destination_hood_id": command.destination_hood_id},
        "decoy": {"destination_hood_id": command.destination_hood_id},
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
    elif entry["kind"] == "fixer":
        links.promote_link(state, command.pawn_id, events)  # type: ignore[arg-type]
    elif entry["kind"] == "connection":
        pawn = state.pawns[command.pawn_id]  # type: ignore[index]
        hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
        hood.criminal_pawn_ids.remove(pawn.pawn_id)
        links.insert_link(state, player.player_id, pawn.pawn_id, hood.contact_id, 1, events)
        economy.check_hood_cop_removal(state, hood, events)
    elif entry["kind"] == "last_job":
        hood = state.board.hoods[entry["hood_id"]]
        hood.criminal_pawn_ids.remove(command.pawn_id)  # type: ignore[arg-type]
        jail.arrest_pawn(state, command.pawn_id, events)  # type: ignore[arg-type]
        economy.check_hood_cop_removal(state, hood, events)
    elif entry["kind"] == "cover":
        cost = skills.effective_cost(
            state,
            player,
            ActionType.PLACE_CRIMINAL,
            state.configuration["costs"]["place_criminal"],
        )
        player.money -= cost
        _place_free_criminal(state, player, state.board.hoods[entry["hood_id"]], events, cost)
    elif entry["kind"] in ("expansion", "escort", "backroom", "vacancy"):
        from dope_engine.rules import movement

        move_to = DEN_ID if entry["kind"] == "backroom" else command.destination_hood_id
        return movement.process_move_queue(
            state,
            player.player_id,
            player,
            [(command.pawn_id, move_to, command.deck_contact_id, None)],  # type: ignore[list-item]
            events,
        )
    elif entry["kind"] == "full_control":
        officer = state.board.officers[command.officer_id]  # type: ignore[index]
        pawn_id = _corrupting_pawn(state, player, officer)
        assert pawn_id is not None
        error = officers.corrupt_officer_into_base(
            state, player, state.pawns[pawn_id], officer, events, free=True
        )
        if error is not None:
            return CommandFailure(error)
    elif entry["kind"] == "decoy":
        economy.spawn_cop(state, state.board.hoods[command.destination_hood_id], events)  # type: ignore[index]
    elif entry["kind"] in ("aftershock", "badge_hire"):
        officer = state.board.officers[command.officer_id]  # type: ignore[index]
        assert officer.hood_id is not None
        pawn_id = _presence_pawn(state, player, officer.hood_id)
        assert pawn_id is not None
        error = officers.corrupt_officer_into_base(
            state, player, state.pawns[pawn_id], officer, events
        )
        if error is not None:
            return CommandFailure(error)
    elif entry["kind"] == "follow_me":
        _place_free_criminal(state, player, state.board.hoods[entry["hood_id"]], events, 0)
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
