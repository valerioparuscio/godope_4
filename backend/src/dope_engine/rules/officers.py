"""Officer maneuver and purchase (RULES_CANONICAL.md §C5-C6): the two
Politici-boosted actions.

Maneuver is the one main action that can't resolve within a single
command: a maneuvered officer performs 1 to 3 *different* follow-up
sub-actions (move/arrest/confiscate) — **decision (2026-08-15): $1 per
action, player's choice how many (1-3, no repeats) and when to stop**,
superseding the earlier flat $2 (Cop) / $3 (Fed) for exactly 2 actions.
A later action's legal targets depend on the earlier ones' effect (e.g. a
Cop that just moved can now only be told to arrest/confiscate in its
*new* Hood), so each sub-action is its own interactive decision.
`ManeuverOfficer` only starts the first officer in its package;
`ChooseManeuverAction` resolves one sub-action at a time, charging $1
each time, and auto-advances to the next queued officer once the current
one stops (voluntarily, via "skip", or forced — 3 actions taken, no
legal action remains, or the money ran out)
(GameState.pending_maneuver / ActiveStep.WAITING_FOR_MANEUVER_ACTION).
The whole package's *minimum* cost (1 action per officer targeted) is
validated upfront so a later officer in the queue can never fail on
money grounds after earlier ones already committed (unlike Buy/Sell, a
maneuver sub-flow can't be discarded and retried once underway without
losing real progress) — actual cost may end up higher once each
officer's actual action count is chosen.

Buying an officer (§C6) is a simple one-shot package like Buy/Sell Dope.
"""

from __future__ import annotations

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import ChooseManeuverAction, CorruptOfficer, ManeuverOfficer
from dope_engine.domain.entities import (
    OfficerLocationType,
    OfficerState,
    PawnLocation,
    PawnState,
)
from dope_engine.domain.enums import (
    ActionType,
    ActiveStep,
    DopeType,
    GamePhase,
    OfficerType,
    PawnRole,
)
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    CriminalPlaced,
    DomainEvent,
    ManeuverActionApplied,
    ManeuverPaidWithDope,
    OfficerCorrupted,
    OfficerManeuverResolved,
    OfficerManeuverStarted,
    OfficerMoved,
    QueuedManeuverSkipped,
)
from dope_engine.domain.ids import ContactId, HoodId, OfficerId, PawnId, PlayerId, SpotId
from dope_engine.domain.state import (
    GameState,
    ManeuverProgress,
    PlayerState,
    find_player,
    officer_count_in_base,
)
from dope_engine.rules import economy, jail, links, skills, turn_flow
from dope_engine.rules.event_utils import emit as _emit
from dope_engine.rules.event_utils import emit_skill_effects
from dope_engine.rules.prices import PriceTracks

MANEUVER_ACTIONS = ("move", "arrest", "confiscate")

# Cards 87 "FREE RIDE", 93 "PROVOCATEUR" and 88 "DISCOUNT" (game designer, 2026-10-16): every
# sub-action of that kind in the maneuver costs nothing.
FREE_ACTION_BY_BOOST = {
    "maneuver_free_move": "move",
    "maneuver_free_arrest": "arrest",
    "maneuver_free_confiscate": "confiscate",
}


def register_handlers(bus: CommandBus, *, price_tracks: PriceTracks) -> None:
    bus.register(ManeuverOfficer, lambda s, c: _handle_maneuver_officer(s, c, price_tracks))
    bus.register(
        ChooseManeuverAction, lambda s, c: _handle_choose_maneuver_action(s, c, price_tracks)
    )
    bus.register(CorruptOfficer, _handle_corrupt_officer)


# --- shared presence helpers ----------------------------------------------

# has_presence_at_hood/has_presence_at_spot now live in rules/economy.py
# (Buy/Sell Dope needs them too, and this module already depends on
# economy for other shared trade validation, e.g. validate_action_targets)
# — re-exported as module-level aliases so this file's own many call sites
# below didn't all need touching.
has_presence_at_hood = economy.has_presence_at_hood
has_presence_at_spot = economy.has_presence_at_spot


def can_maneuver_cop(state: GameState, pawn: PawnState, hood_id: HoodId) -> bool:
    # Same "never an unrevealed Hood" discipline as has_presence_at_hood's
    # own Link branch just below (2026-09-07 fix, same reported symptom:
    # "solo alcuni Cops vengono evidenziati") — a Rat's "anywhere" (§11.7)
    # bypasses that helper entirely, so it needs its own explicit guard
    # here instead (bug report, 2026-09-27: "secondo me a volte... prende
    # quelli dei quartieri nascosti (non deve)"). A covered Hood can
    # already hold a pre-placed Cop as part of its own covered-tile
    # definition, long before anyone reveals it — nothing should be able
    # to target that Cop yet, Rat included.
    if not state.board.hoods[hood_id].revealed:
        return False
    return pawn.role == PawnRole.RAT or has_presence_at_hood(state, pawn, hood_id)


def can_maneuver_fed(state: GameState, pawn: PawnState, spot_id: SpotId) -> bool:
    return has_presence_at_spot(state, pawn, spot_id)


def _lowest_level_link_at_contact(state: GameState, contact_id: ContactId) -> PawnState | None:
    candidates = [
        pawn
        for pawn in state.pawns.values()
        if pawn.role == PawnRole.LINK and pawn.contact_id == contact_id
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda pawn: pawn.link_level or 0)


def has_arrestable_link(state: GameState, contact_id: ContactId) -> bool:
    return _lowest_level_link_at_contact(state, contact_id) is not None


def has_any_maneuver_action_available(
    state: GameState, officer: OfficerState, actions_taken: list[str], player: PlayerState
) -> bool:
    """Cheap existence check mirroring
    application/legal_actions.py::_maneuver_action_candidates (which
    builds full DecisionOption objects) — kept here, not imported from
    there, so this rules-layer module doesn't depend on the application
    layer (CLAUDE.md section 3.3). Used by `_handle_choose_maneuver_action`'s
    "skip" guard so it agrees with the decision layer on when a fresh
    officer (0 actions_taken yet) genuinely has nothing left to do and
    must be passable, rather than only ever allowing skip after >=1 action."""
    if officer.officer_type == OfficerType.COP:
        hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
        if "move" not in actions_taken and hood.adjacent_hood_ids:
            return True
        if "arrest" not in actions_taken and maneuver_arrest_choices(state, officer, player):
            return True
        return (
            "confiscate" not in actions_taken
            and bool(hood.dope_stack)
            and jail.has_free_confiscation_slot(state)
        )

    spot = state.board.spots[officer.spot_id]  # type: ignore[index]
    if "move" not in actions_taken and spot.adjacent_spot_ids:
        return True
    if "arrest" not in actions_taken and maneuver_arrest_choices(state, officer, player):
        return True
    return (
        "confiscate" not in actions_taken
        and bool(spot.sold_dope_tokens)
        and jail.has_free_confiscation_slot(state)
    )


def maneuver_action_cost(state: GameState, player: PlayerState, *, is_first_action: bool) -> int:
    """$1 per maneuver sub-action (move/arrest/confiscate), same for
    Cop and Fed — decision (2026-08-15), see module docstring.
    Politici-1's own "-1$" discount (corrected 2026-09-02: previously
    applied to *every* sub-action of every maneuver, over-discounting
    — game designer: "per ogni grinta che usi, il primo comando che dai
    al cops non costa 1 dollaro come al solito", i.e. once per Grit-
    fueled maneuver, not once per sub-action) applies only to the
    very first sub-action of each maneuver started (`is_first_action`
    — every call site either already knows it's about to start/consider
    a fresh maneuver's own first action, or has `progress.
    actions_taken` in scope to check)."""
    base_cost: int = state.configuration["costs"]["maneuver_action"]
    if not is_first_action:
        return base_cost
    return skills.effective_cost(state, player, ActionType.MANEUVER_OFFICER, base_cost)


def maneuver_sub_action_cost(
    state: GameState, player: PlayerState, action: str, *, is_first_action: bool
) -> int:
    boost = player.active_card_boost
    if boost is not None and FREE_ACTION_BY_BOOST.get(boost["type"]) == action:
        return 0
    return maneuver_action_cost(state, player, is_first_action=is_first_action)


def maneuver_min_start_cost(state: GameState, player: PlayerState) -> int:
    """What starting a maneuver must at least afford (its cheapest possible first action)."""
    boost = player.active_card_boost
    if boost is not None and boost["type"] in FREE_ACTION_BY_BOOST:
        return 0
    return maneuver_action_cost(state, player, is_first_action=True)


def _rat_can_enter_hood(
    state: GameState, rat_pawn_id: PawnId, hood_id: HoodId, *, leaving_pawn_id: PawnId | None
) -> bool:
    """A Rat leaving the Jail as a Criminal into `hood_id` (cards 97/100): the Hood has room
    (never to the Rissa count through a swap) and the Rat's owner stays within the per-player
    Hood limit."""
    from dope_engine.domain.state import max_pawns_per_player_per_hood, own_pawns_in_hood

    hood = state.board.hoods[hood_id]
    owner_id = state.pawns[rat_pawn_id].owner_player_id
    own = own_pawns_in_hood(state, owner_id, hood_id)
    if leaving_pawn_id is None:
        if len(hood.criminal_pawn_ids) >= state.configuration["brawl_trigger_criminal_count"]:
            return False
    elif state.pawns[leaving_pawn_id].owner_player_id == owner_id:
        own -= 1
    return own < max_pawns_per_player_per_hood(state.configuration)


def maneuver_arrest_choices(
    state: GameState, officer: OfficerState, player: PlayerState
) -> list[tuple[str | None, str | None]]:
    """The doable "arrest" choices as (target_id, second_target_id) — shared by the option
    generator, `has_any_maneuver_action_available` and `_apply_arrest`.

    Normal: a Cop arrests a Criminal of its Hood, a Fed the lowest Link of its Contact (needs a
    free Jail slot). Card 97 "REDEEM" (Cop): instead of arresting, a Rat (anyone's) leaves the
    Jail for the Cop's Hood. Card 100 "SWEEP" (Cop): an arrested Criminal may swap places with
    a Rat, which takes its place in the Hood."""
    boost = player.active_card_boost
    boost_type = boost["type"] if boost is not None else None
    free_slot = jail.has_free_rat_slot(state)
    jail_rats = [s.rat_pawn_id for s in state.jail.slots if s.rat_pawn_id is not None]
    if officer.officer_type == OfficerType.COP:
        hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
        if boost_type == "maneuver_redeem_rat":
            return [
                (rat_id, None)
                for rat_id in jail_rats
                if _rat_can_enter_hood(state, rat_id, hood.hood_id, leaving_pawn_id=None)
            ]
        choices: list[tuple[str | None, str | None]] = []
        if free_slot:
            choices.extend((pid, None) for pid in hood.criminal_pawn_ids)
        if boost_type == "maneuver_sweep":
            choices.extend(
                (pid, rat_id)
                for pid in hood.criminal_pawn_ids
                for rat_id in jail_rats
                if _rat_can_enter_hood(state, rat_id, hood.hood_id, leaving_pawn_id=pid)
            )
        return choices
    spot = state.board.spots[officer.spot_id]  # type: ignore[index]
    if free_slot and has_arrestable_link(state, spot.contact_id):
        return [(None, None)]
    return []


def end_maneuver_action(state: GameState, player: PlayerState, events: list[DomainEvent]) -> bool:
    """The whole maneuver action is over: a Hood a Rat just filled to the Rissa count (cards
    97/100) starts its Rissa, otherwise the queued card follow-ups (cards 81/85/91) open.
    Returns whether something took over (the caller then must not finish the action)."""
    from dope_engine.rules import brawl, move_followups

    trigger = state.configuration["brawl_trigger_criminal_count"]
    full = next(
        (h for h in state.board.hoods.values() if len(h.criminal_pawn_ids) >= trigger), None
    )
    if full is not None:
        brawl.start_brawl(state, full, player.player_id, [], events)
        return True
    return move_followups.begin(state, player)


def _place_released_rat(
    state: GameState, rat_pawn_id: PawnId, hood_id: HoodId, events: list[DomainEvent]
) -> None:
    """A Rat out of the Jail becomes a Criminal of the Hood (its owner draws, as for a
    placement)."""
    pawn = state.pawns[rat_pawn_id]
    hood = state.board.hoods[hood_id]
    pawn.role = PawnRole.CRIMINAL
    pawn.location = PawnLocation.hood(hood_id)
    hood.criminal_pawn_ids.append(rat_pawn_id)
    _emit(
        state,
        events,
        CriminalPlaced,
        player_id=pawn.owner_player_id,
        pawn_id=rat_pawn_id,
        hood_id=hood_id,
        cost=0,
    )
    economy.draw_card(state, hood.contact_id, events, pawn.owner_player_id)


# --- ManeuverOfficer / ChooseManeuverAction -------------------------------


def _start_maneuver(
    state: GameState,
    player: PlayerState,
    pawn_id: PawnId,
    officer_id: OfficerId,
    events: list[DomainEvent],
) -> DomainError | None:
    pawn = state.pawns.get(pawn_id)
    if pawn is None or pawn.owner_player_id != player.player_id:
        return DomainError(
            code="pawn_not_owned", message=f"Pawn '{pawn_id}' is not yours.", details={}
        )
    if pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK, PawnRole.RAT):
        return DomainError(
            code="pawn_not_eligible",
            message=f"Pawn '{pawn_id}' cannot maneuver an officer.",
            details={},
        )

    officer = state.board.officers.get(officer_id)
    if officer is None:
        return DomainError(
            code="unknown_officer", message=f"Unknown officer '{officer_id}'.", details={}
        )

    if officer.officer_type == OfficerType.COP:
        if officer.location_type != OfficerLocationType.HOOD or officer.hood_id is None:
            return DomainError(
                code="officer_not_on_map", message="Cop is not in a Hood.", details={}
            )
        if not can_maneuver_cop(state, pawn, officer.hood_id):
            return DomainError(
                code="no_presence", message="No presence to maneuver this Cop.", details={}
            )
    else:
        if officer.location_type != OfficerLocationType.SPOT or officer.spot_id is None:
            return DomainError(
                code="officer_not_on_map", message="Fed is not in a Spot.", details={}
            )
        if not can_maneuver_fed(state, pawn, officer.spot_id):
            return DomainError(
                code="no_presence", message="No presence to maneuver this Fed.", details={}
            )

    # Cost is charged per action (see maneuver_action_cost), not
    # here — but starting a maneuver always commits to at least 1
    # action, so affordability for that minimum is checked upfront.
    # This is always that maneuver's own first action.
    action_cost = maneuver_min_start_cost(state, player)
    if player.money < action_cost:
        return DomainError(
            code="insufficient_funds",
            message=f"Maneuvering costs ${action_cost} per action.",
            details={"required": action_cost, "available": player.money},
        )

    state.pending_maneuver = ManeuverProgress(
        player_id=player.player_id, maneuverer_pawn_id=pawn_id, officer_id=officer_id
    )
    player.maneuvered_pawn_ids_this_action.append(pawn_id)
    _note_maneuver_cards(state, player, pawn, officer)
    _emit(
        state,
        events,
        OfficerManeuverStarted,
        player_id=player.player_id,
        pawn_id=pawn_id,
        officer_id=officer_id,
        officer_type=officer.officer_type,
    )
    return None


def _note_maneuver_cards(
    state: GameState, player: PlayerState, pawn: PawnState, officer: OfficerState
) -> None:
    """Queues the follow-ups of the maneuver cards that run once the action is over
    (`end_maneuver_action`): 81 "FULL CONTROL" (with Grit 3, one free corruption of an officer
    maneuvered in this action) and 91 "BACKROOM DEAL" (the pawn that maneuvered a Cop goes to
    the Den)."""
    boost = player.active_card_boost
    if boost is None:
        return
    if boost["type"] == "maneuver_free_corrupt" and player.current_round_grit_value == 3:
        entry = next(
            (e for e in player.pending_move_followups if e["kind"] == "full_control"), None
        )
        if entry is None:
            entry = {"kind": "full_control", "officer_ids": []}
            player.pending_move_followups.append(entry)
        entry["officer_ids"].append(officer.officer_id)
    elif (
        boost["type"] == "maneuver_den"
        and officer.officer_type == OfficerType.COP
        and pawn.role == PawnRole.CRIMINAL
    ):
        player.pending_move_followups.append(
            {"kind": "backroom", "pawn_id": pawn.pawn_id, "mandatory": True}
        )


def _note_corrupt_cards(
    state: GameState,
    player: PlayerState,
    pawn: PawnState,
    officer_type: OfficerType,
    hood_id: HoodId | None,
) -> None:
    """Queues the follow-ups of the Corrupt cards (game designer, 2026-10-16) about the officer
    just taken into the Covo, opened by `end_maneuver_action` when the action ends: 86
    "VACANCY" / 94 "RIOT" (move a Criminal there, free, drawing), 89 "FIXER" (the Link that
    corrupted a Fed goes up a level), 90 "CONNECTION" (the Criminal that corrupted a Cop
    becomes a Link), 92 "SAFE PASSAGE" (it goes to the Den, automatically), 96 "LAST JOB"
    (arrest a Criminal of the Cop's Hood) and 98 "COVER" (place a Criminal there, $2)."""
    boost = player.active_card_boost
    if boost is None:
        return
    kind = boost["type"]
    queue = player.pending_move_followups
    if officer_type == OfficerType.FED:
        if kind == "corrupt_link_up" and pawn.role == PawnRole.LINK:
            queue.append({"kind": "fixer", "pawn_id": pawn.pawn_id})
        return
    if hood_id is None:
        return
    criminal = pawn.role == PawnRole.CRIMINAL
    if kind == "corrupt_move_anywhere":
        queue.append({"kind": "vacancy", "hood_id": hood_id})
    elif kind == "corrupt_den" and criminal:
        queue.append({"kind": "backroom", "pawn_id": pawn.pawn_id, "mandatory": True})
    elif kind == "corrupt_to_link" and criminal:
        queue.append({"kind": "connection", "pawn_id": pawn.pawn_id})
    elif kind == "corrupt_arrest":
        queue.append({"kind": "last_job", "hood_id": hood_id})
    elif kind == "corrupt_place":
        queue.append({"kind": "cover", "hood_id": hood_id})


def _handle_maneuver_officer(
    state: GameState, command: ManeuverOfficer, price_tracks: PriceTracks
) -> CommandOutcome:
    error, player = economy.validate_action_targets(
        state, command.player_id, ActionType.MANEUVER_OFFICER, len(command.maneuvers)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    if len({pid for pid, _ in command.maneuvers}) != len(command.maneuvers):
        return CommandFailure(
            DomainError(
                code="duplicate_pawn_in_targets",
                message="Each Criminal/Link/Rat can only start one maneuver per action.",
                details={},
            )
        )
    if len({oid for _, oid in command.maneuvers}) != len(command.maneuvers):
        return CommandFailure(
            DomainError(
                code="duplicate_officer_in_targets",
                message="Each officer can only be targeted once per action.",
                details={},
            )
        )

    # This command can now be dispatched more than once per action
    # instance (2026-08-16): after an earlier officer's maneuver
    # finishes, the player can choose to spend more of the *same* Grit on
    # another one instead of committing to every officer upfront (see
    # `_finish_maneuver`) — so a pawn already used earlier in this same
    # action must be rejected here too, not just within one command's own
    # `command.maneuvers`.
    already_used = set(player.maneuvered_pawn_ids_this_action)
    if any(pawn_id in already_used for pawn_id, _ in command.maneuvers):
        return CommandFailure(
            DomainError(
                code="duplicate_pawn_in_targets",
                message="A pawn already maneuvered an officer earlier in this action.",
                details={},
            )
        )
    assert player.current_round_grit_value is not None
    max_count = skills.effective_action_count(
        state, player, ActionType.MANEUVER_OFFICER, player.current_round_grit_value
    )
    remaining_budget = max_count - len(already_used)
    if len(command.maneuvers) > remaining_budget:
        given = len(command.maneuvers)
        return CommandFailure(
            DomainError(
                code="wrong_target_count",
                message=f"Expected at most {remaining_budget} more target(s), got {given}.",
                details={"remaining_budget": remaining_budget, "given": given},
            )
        )

    for _, officer_id in command.maneuvers:
        if officer_id not in state.board.officers:
            return CommandFailure(
                DomainError(
                    code="unknown_officer",
                    message=f"Unknown officer '{officer_id}'.",
                    details={},
                )
            )
    # Actual cost depends on how many actions each officer ends up
    # getting (chosen one at a time, $1 each — see
    # maneuver_action_cost), so only the guaranteed *minimum* (1
    # action per officer targeted, each that officer's own first) is
    # checked upfront; each action's own affordability is re-checked
    # as it's taken.
    min_total_cost = maneuver_min_start_cost(state, player) * len(command.maneuvers)
    if player.money < min_total_cost:
        return CommandFailure(
            DomainError(
                code="insufficient_funds",
                message=f"Maneuvering this package costs at least ${min_total_cost}.",
                details={"required": min_total_cost, "available": player.money},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []
    base_remaining_budget = player.current_round_grit_value - len(already_used)
    if len(command.maneuvers) > base_remaining_budget:
        emit_skill_effects(
            state,
            events,
            command.player_id,
            skills.matching_skill_ids(
                state,
                player,
                "extra_grit",
                lambda e: ActionType.MANEUVER_OFFICER.value in e["action_types"],
            ),
        )
    queue = list(command.maneuvers)
    first_pawn_id, first_officer_id = queue.pop(0)

    error = _start_maneuver(state, player, first_pawn_id, first_officer_id, events)
    if error is not None:
        return CommandFailure(error)

    assert state.pending_maneuver is not None
    state.pending_maneuver.remaining_queue = queue
    state.active_step = ActiveStep.WAITING_FOR_MANEUVER_ACTION
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _handle_choose_maneuver_action(
    state: GameState, command: ChooseManeuverAction, price_tracks: PriceTracks
) -> CommandOutcome:
    if state.phase != GamePhase.ACTION_PHASE:
        return CommandFailure(wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(wrong_player(str(state.current_player_id), str(command.player_id)))
    wrong_step = state.active_step != ActiveStep.WAITING_FOR_MANEUVER_ACTION
    if wrong_step or state.pending_maneuver is None:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message="Not waiting for a maneuver action.",
                details={"actual_step": state.active_step.value},
            )
        )

    progress = state.pending_maneuver
    if command.action == "skip":
        if not progress.actions_taken:
            officer_for_skip = state.board.officers.get(progress.officer_id)
            skip_player = find_player(state, command.player_id)
            # Actions that cost more than the player has are as good as taken.
            unaffordable = [
                a
                for a in MANEUVER_ACTIONS
                if maneuver_sub_action_cost(state, skip_player, a, is_first_action=True)
                > skip_player.money
            ]
            still_has_action = officer_for_skip is not None and (
                has_any_maneuver_action_available(
                    state,
                    officer_for_skip,
                    [*progress.actions_taken, *unaffordable],
                    skip_player,
                )
            )
            if still_has_action:
                return CommandFailure(
                    DomainError(
                        code="cannot_skip_first_action",
                        message="Cannot skip before at least 1 maneuver action was taken.",
                        details={},
                    )
                )
        state.revision += 1
        skip_events: list[DomainEvent] = []
        return _finish_maneuver(state, command.player_id, progress, skip_events)

    if command.action not in MANEUVER_ACTIONS:
        return CommandFailure(
            DomainError(
                code="unknown_maneuver_action",
                message=f"'{command.action}' is not a valid maneuver action.",
                details={},
            )
        )
    if command.action in progress.actions_taken:
        return CommandFailure(
            DomainError(
                code="action_already_used",
                message=f"'{command.action}' was already used for this officer.",
                details={},
            )
        )

    officer = state.board.officers.get(progress.officer_id)
    if officer is None:
        return CommandFailure(
            DomainError(code="unknown_officer", message="Officer no longer exists.", details={})
        )

    player = find_player(state, command.player_id)
    action_cost = maneuver_sub_action_cost(
        state, player, command.action, is_first_action=not progress.actions_taken
    )
    if player.money < action_cost:
        return CommandFailure(
            DomainError(
                code="insufficient_funds",
                message=f"This maneuver action costs ${action_cost}.",
                details={"required": action_cost, "available": player.money},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    error = _apply_maneuver_action(
        state,
        progress,
        officer,
        command.action,
        command.target_id,
        price_tracks,
        player,
        events,
        command.second_target_id,
    )
    if error is not None:
        return CommandFailure(error)

    player.money -= action_cost
    progress.actions_taken.append(command.action)
    emit_skill_effects(
        state,
        events,
        command.player_id,
        skills.matching_skill_ids(
            state,
            player,
            "cost_delta",
            lambda e: ActionType.MANEUVER_OFFICER.value in e["action_types"],
        ),
    )
    _emit(
        state,
        events,
        ManeuverActionApplied,
        player_id=command.player_id,
        officer_id=progress.officer_id,
        action=command.action,
    )

    # The action just applied can itself remove the officer being
    # maneuvered (e.g. a Cop's own "confiscate" empties its Hood of both
    # Dope and Criminals, triggering the standing "no Dope/no Criminals"
    # reserve-return check — maneuver grants it no immunity from that,
    # per the confirmed "immediate re-check after every relevant event"
    # decision). With nothing left to act with, the maneuver is forced
    # to a close after just this action instead of continuing to the
    # 3-action cap. Decision (2026-08-15): the cap itself is 3 actions
    # (move/arrest/confiscate, $1 each) — the player may also stop
    # voluntarily before that via "skip" (see the branch above), so
    # reaching here just means neither a forced nor a voluntary stop has
    # happened yet.
    officer_still_exists = progress.officer_id in state.board.officers
    if len(progress.actions_taken) < 3 and officer_still_exists:
        state.event_log_cursor += len(events)
        return CommandSuccess(state=state, events=tuple(events))

    return _finish_maneuver(state, command.player_id, progress, events)


def _finish_maneuver(
    state: GameState, player_id: PlayerId, progress: ManeuverProgress, events: list[DomainEvent]
) -> CommandOutcome:
    _emit(
        state,
        events,
        OfficerManeuverResolved,
        player_id=player_id,
        officer_id=progress.officer_id,
    )
    player = find_player(state, player_id)

    # An earlier officer in the same command's own queue can, through its
    # own actions, invalidate a *later* queued (pawn, officer) pair (e.g.
    # a Fed's "arrest" happens to jail the very pawn queued as the next
    # maneuverer). Rather than failing the whole command — which would
    # roll back this already-legitimately-applied action too, unlike
    # Buy/Sell where a failed later target never committed anything —
    # the rest of that command's queue is simply dropped, but a
    # QueuedManeuverSkipped event still records *why* (game designer,
    # 2026-08-16 bug report: a dropped 2nd officer looked like nothing
    # happened at all).
    started_next = False
    if progress.remaining_queue:
        remaining_queue = progress.remaining_queue
        next_pawn_id, next_officer_id = remaining_queue.pop(0)
        error = _start_maneuver(state, player, next_pawn_id, next_officer_id, events)
        if error is None:
            assert state.pending_maneuver is not None
            state.pending_maneuver.remaining_queue = remaining_queue
            started_next = True
        else:
            _emit(
                state,
                events,
                QueuedManeuverSkipped,
                player_id=player_id,
                officer_id=next_officer_id,
                reason_code=error.code,
            )

    if not started_next:
        state.pending_maneuver = None
        # 2026-08-16 (2nd fix): a Grit-N maneuver no longer has to
        # commit to all N officers upfront in one ManeuverOfficer command —
        # once this command's own queue is empty, if Grit still allows
        # more *different* pawns to maneuver (an officer's own 1-3 actions
        # don't consume any of that budget, only *which pawn started it*
        # does — see `maneuvered_pawn_ids_this_action`), loop back to the
        # same step this action was chosen from so a fresh maneuver_officer
        # decision is offered instead of ending the action outright. If
        # nothing is actually achievable anymore (no budget, no eligible
        # officers left, no money), `_action_targets_decision`'s existing
        # "None result -> empty, declinable decision" fallback already
        # handles that gracefully — same mechanism a Poker-launch-starved
        # main action already relies on, so no new plumbing is needed.
        assert player.current_round_grit_value is not None
        max_count = skills.effective_action_count(
            state, player, ActionType.MANEUVER_OFFICER, player.current_round_grit_value
        )
        remaining_budget = max_count - len(player.maneuvered_pawn_ids_this_action)
        if remaining_budget > 0:
            state.active_step = (
                ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
                if player.extra_action_link_pawn_id is not None
                else ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
            )
        elif not end_maneuver_action(state, player, events):
            turn_flow.finish_action_or_extra(state, player, events)

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _apply_maneuver_action(
    state: GameState,
    progress: ManeuverProgress,
    officer: OfficerState,
    action: str,
    target_id: str | None,
    price_tracks: PriceTracks,
    player: PlayerState,
    events: list[DomainEvent],
    second_target_id: str | None = None,
) -> DomainError | None:
    if action == "move":
        return _apply_move(state, officer, target_id, player, events)
    if action == "arrest":
        return _apply_arrest(state, officer, target_id, player, events, second_target_id)
    return _apply_confiscate(state, officer, target_id, price_tracks, player, events)


def _apply_move(
    state: GameState,
    officer: OfficerState,
    target_id: str | None,
    player: PlayerState,
    events: list[DomainEvent],
) -> DomainError | None:
    if target_id is None:
        return DomainError(
            code="target_required", message="Move requires a destination.", details={}
        )

    if officer.officer_type == OfficerType.COP:
        current_hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
        destination = HoodId(target_id)
        dest_hood = state.board.hoods.get(destination)
        if dest_hood is None:
            return DomainError(
                code="unknown_hood", message=f"Unknown Hood '{destination}'.", details={}
            )
        if destination not in current_hood.adjacent_hood_ids:
            return DomainError(
                code="not_adjacent", message=f"'{destination}' is not adjacent.", details={}
            )
        current_hood.cop_ids.remove(officer.officer_id)
        officer.hood_id = destination
        state.board.hoods[destination].cop_ids.append(officer.officer_id)
        _emit(state, events, OfficerMoved, officer_id=officer.officer_id, hood_id=destination)
        economy.check_hood_cop_removal(state, current_hood, events)
        boost = player.active_card_boost
        if boost is not None and boost["type"] == "maneuver_escort":
            # Card 85 "ESCORT" (game designer, 2026-10-16): a Criminal of yours may make the
            # same trip, free (it counts as its move of the turn, draws, can start a Rissa) —
            # offered once the maneuver action is over.
            player.pending_move_followups.append(
                {"kind": "escort", "from_hood_id": current_hood.hood_id, "to_hood_id": destination}
            )
        return None

    current_spot = state.board.spots[officer.spot_id]  # type: ignore[index]
    destination_spot = SpotId(target_id)
    if destination_spot not in state.board.spots:
        return DomainError(
            code="unknown_spot", message=f"Unknown Spot '{destination_spot}'.", details={}
        )
    if destination_spot not in current_spot.adjacent_spot_ids:
        return DomainError(
            code="not_adjacent", message=f"'{destination_spot}' is not adjacent.", details={}
        )
    current_spot.fed_ids.remove(officer.officer_id)
    officer.spot_id = destination_spot
    state.board.spots[destination_spot].fed_ids.append(officer.officer_id)
    _emit(state, events, OfficerMoved, officer_id=officer.officer_id, spot_id=destination_spot)
    return None


def _apply_arrest(
    state: GameState,
    officer: OfficerState,
    target_id: str | None,
    player: PlayerState,
    events: list[DomainEvent],
    second_target_id: str | None = None,
) -> DomainError | None:
    boost = player.active_card_boost
    swap_boost = boost is not None and boost["type"] in ("maneuver_redeem_rat", "maneuver_sweep")
    if swap_boost and officer.officer_type == OfficerType.COP:
        # Cards 97 "REDEEM" and 100 "SWEEP" (game designer, 2026-10-16) — see
        # `maneuver_arrest_choices`.
        if (target_id, second_target_id) not in maneuver_arrest_choices(state, officer, player):
            return DomainError(
                code="invalid_arrest_target",
                message="That is not a valid choice for this arrest.",
                details={},
            )
        hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
        if boost is not None and boost["type"] == "maneuver_redeem_rat":
            rat_id = PawnId(str(target_id))
            jail.release_rat(state, rat_id, events)
            _place_released_rat(state, rat_id, hood.hood_id, events)
            return None
        if second_target_id is not None:
            arrested_id = PawnId(str(target_id))
            rat_id = PawnId(second_target_id)
            hood.criminal_pawn_ids.remove(arrested_id)
            jail.swap_arrest(state, arrested_id, rat_id, events)
            _place_released_rat(state, rat_id, hood.hood_id, events)
            return None

    if not jail.has_free_rat_slot(state):
        return DomainError(code="jail_full", message="No free Jail slot for a Rat.", details={})

    # Cards 076/077/080 "BASHER" ("se arresti, arresta due criminali"):
    # a second target chosen automatically — same "position is
    # equivalent" convention as RULES_PENDING.md #4 — rather than a
    # second player choice, best-effort (silently skipped if none
    # remain/no Jail slot is left, mirroring how the last-slot Evasion
    # check is already re-run per arrest, not just once up front).
    boost = player.active_card_boost
    arrest_extra = boost is not None and boost["type"] == "arrest_extra_target"

    if officer.officer_type == OfficerType.COP:
        if target_id is None:
            return DomainError(
                code="target_required", message="Arrest requires a target Criminal.", details={}
            )
        pawn_id = PawnId(target_id)
        pawn = state.pawns.get(pawn_id)
        hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
        if pawn is None or pawn.role != PawnRole.CRIMINAL or pawn_id not in hood.criminal_pawn_ids:
            return DomainError(
                code="invalid_arrest_target",
                message=f"'{target_id}' is not a Criminal in this Hood.",
                details={},
            )
        hood.criminal_pawn_ids.remove(pawn_id)
        jail.arrest_pawn(state, pawn_id, events)
        if arrest_extra and hood.criminal_pawn_ids and jail.has_free_rat_slot(state):
            extra_pawn_id = hood.criminal_pawn_ids[0]
            hood.criminal_pawn_ids.remove(extra_pawn_id)
            jail.arrest_pawn(state, extra_pawn_id, events)
        economy.check_hood_cop_removal(state, hood, events)
        return None

    spot = state.board.spots[officer.spot_id]  # type: ignore[index]
    target_pawn = _lowest_level_link_at_contact(state, spot.contact_id)
    if target_pawn is None:
        return DomainError(
            code="no_link_to_arrest",
            message=f"No Link at Contact '{spot.contact_id}' to arrest.",
            details={},
        )
    jail.arrest_pawn(state, target_pawn.pawn_id, events)
    if arrest_extra and jail.has_free_rat_slot(state):
        extra_link = _lowest_level_link_at_contact(state, spot.contact_id)
        if extra_link is not None:
            jail.arrest_pawn(state, extra_link.pawn_id, events)
    links.check_spot_fed_removal_for_contact(state, spot.contact_id, events)
    return None


def _confiscate_one_unit(
    state: GameState,
    price_tracks: PriceTracks,
    dope_type: DopeType,
    *,
    events: list[DomainEvent],
    slot_index: int | None = None,
) -> None:
    jail.confiscate_dope(state, dope_type, events, slot_index=slot_index)
    economy.apply_ordinary_price_step(state, price_tracks, dope_type, steps=1, events=events)


def _apply_confiscate(
    state: GameState,
    officer: OfficerState,
    target_id: str | None,
    price_tracks: PriceTracks,
    player: PlayerState,
    events: list[DomainEvent],
) -> DomainError | None:
    boost = player.active_card_boost
    # Card 83 "INSIDER" (game designer, 2026-08-31): the maneuverer names a specific *free*
    # Jail slot instead of always the first free one.
    choose_slot = boost is not None and boost["type"] == "insider_choose_jail_slot"
    slot_index: int | None = None
    if choose_slot:
        if target_id is None:
            return DomainError(
                code="target_required", message="Choose a Jail slot for the Dope.", details={}
            )
        slot_index = int(target_id)
        if not (0 <= slot_index < len(state.jail.slots)) or (
            state.jail.slots[slot_index].confiscated_dope_type is not None
        ):
            return DomainError(
                code="jail_slot_not_free",
                message=f"Jail slot {slot_index} is not free.",
                details={},
            )
    if not jail.has_free_confiscation_slot(state):
        return DomainError(
            code="jail_confiscation_full",
            message="No free Jail slot for confiscated Dope.",
            details={},
        )

    if officer.officer_type == OfficerType.COP:
        hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
        if not hood.dope_stack:
            return DomainError(
                code="hood_has_no_dope", message=f"Hood '{hood.hood_id}' has no Dope.", details={}
            )
        dope_type = hood.dope_stack.pop()
        _confiscate_one_unit(state, price_tracks, dope_type, events=events, slot_index=slot_index)
        if economy.extremes_mode(state) and not hood.dope_stack:
            # "Easy Price": a Hood emptied (here by a requisition) -> the price to its maximum.
            economy.set_price_extreme(state, dope_type, "max", events)
        economy.check_hood_cop_removal(state, hood, events)
        return None

    spot = state.board.spots[officer.spot_id]  # type: ignore[index]
    if not spot.sold_dope_tokens:
        return DomainError(
            code="spot_has_no_dope", message=f"Spot '{spot.spot_id}' has no Dope.", details={}
        )
    dope_type = spot.sold_dope_tokens.pop()
    _confiscate_one_unit(state, price_tracks, dope_type, events=events, slot_index=slot_index)
    return None


# --- CorruptOfficer -------------------------------------------------------------


def _handle_corrupt_officer(state: GameState, command: CorruptOfficer) -> CommandOutcome:
    error, player = economy.validate_action_targets(
        state, command.player_id, ActionType.CORRUPT_OFFICER, len(command.purchases)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    if len({pid for pid, _, _ in command.purchases}) != len(command.purchases):
        return CommandFailure(
            DomainError(
                code="duplicate_pawn_in_targets",
                message="Each Criminal/Link can only buy once per action.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []
    price = skills.effective_cost(
        state, player, ActionType.CORRUPT_OFFICER, state.configuration["costs"]["corrupt_officer"]
    )

    for index, (pawn_id, officer_id, destination) in enumerate(command.purchases):
        payment: DopeType | None = None
        chosen_payment = (
            command.payment_dope_types[index] if index < len(command.payment_dope_types) else None
        )
        if chosen_payment:
            boost = player.active_card_boost
            payment = DopeType(chosen_payment)
            if (
                boost is None
                or boost["type"] != "corrupt_pay_dope"
                or player.base_inventory.dope_counts.get(payment, 0) < 1
            ):
                return CommandFailure(
                    DomainError(
                        code="insufficient_dope",
                        message="You cannot pay for this officer with that Dope.",
                        details={},
                    )
                )
        if payment is None and player.money < price:
            return CommandFailure(
                DomainError(
                    code="insufficient_funds",
                    message=f"Buying an officer costs ${price}.",
                    details={"required": price, "available": player.money},
                )
            )
        pawn = state.pawns.get(pawn_id)
        if (
            pawn is None
            or pawn.owner_player_id != command.player_id
            or pawn.role
            not in (
                PawnRole.CRIMINAL,
                PawnRole.LINK,
            )
        ):
            return CommandFailure(
                DomainError(
                    code="pawn_not_eligible",
                    message=f"Pawn '{pawn_id}' cannot buy an officer.",
                    details={},
                )
            )
        officer = state.board.officers.get(officer_id)
        if officer is None:
            return CommandFailure(
                DomainError(
                    code="unknown_officer",
                    message=f"Unknown officer '{officer_id}'.",
                    details={},
                )
            )

        on_map = officer.location_type != OfficerLocationType.BASE
        officer_type, officer_hood_id = officer.officer_type, officer.hood_id
        if officer.location_type == OfficerLocationType.BASE:
            error = _corrupt_officer_onto_map(
                state, player, pawn, officer, destination, events, payment=payment
            )
        else:
            error = _corrupt_officer_into_base(
                state, player, pawn, officer, events, payment=payment
            )
        if error is not None:
            return CommandFailure(error)
        if on_map:
            _note_corrupt_cards(state, player, pawn, officer_type, officer_hood_id)
        # Job 2 / Raid 5 (RULES_CANONICAL.md §A10, reversed 2026-08-23)
        # now read live possession (`officer_count_in_base`) instead of a
        # cumulative "ever bought" counter — nothing to bump here anymore.

    player.officer_corruptor_pawn_ids_this_action.extend(pid for pid, _, _ in command.purchases)
    assert player.current_round_grit_value is not None
    remaining_budget = skills.effective_action_count(
        state, player, ActionType.CORRUPT_OFFICER, player.current_round_grit_value
    ) - len(player.officer_corruptor_pawn_ids_this_action)
    if remaining_budget > 0:
        # Grit still allows another officer (possibly the very one just
        # placed on the map): stay on the same step so a fresh corrupt_officer
        # decision is offered — `_action_targets_decision`'s empty,
        # auto-declined fallback covers "nothing buyable anymore".
        state.active_step = (
            ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
            if player.extra_action_link_pawn_id is not None
            else ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
        )
    elif not end_maneuver_action(state, player, events):
        turn_flow.finish_action_or_extra(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _pay_with_dope(
    state: GameState, player: PlayerState, dope_type: DopeType, events: list[DomainEvent]
) -> None:
    """Card 82 "PAYOFF": one Dope of the Covo goes back to the supply instead of the price."""
    player.base_inventory.dope_counts[dope_type] -= 1
    supply = state.market.supply_remaining_by_dope_type
    supply[dope_type] = supply.get(dope_type, 0) + 1
    _emit(state, events, ManeuverPaidWithDope, player_id=player.player_id, dope_type=dope_type)


def _carry_dope_to_base(
    state: GameState, player: PlayerState, officer: OfficerState, events: list[DomainEvent]
) -> None:
    """Card 84 "EVIDENCE" (game designer, 2026-10-16): the corrupted officer brings along a
    Dope of its Hood/Spot, if there is one and the Covo has room for it."""
    if officer.officer_type == OfficerType.COP:
        pile = state.board.hoods[officer.hood_id].dope_stack  # type: ignore[index]
    else:
        pile = state.board.spots[officer.spot_id].sold_dope_tokens  # type: ignore[index]
    if not pile:
        return
    dope_type = pile[-1]
    if player.base_inventory.dope_counts.get(dope_type, 0) >= 3:
        return
    pile.pop()
    jail.recover_dope(state, player.player_id, dope_type, events)
    if officer.officer_type == OfficerType.COP and not pile and economy.extremes_mode(state):
        # "Easy Price": the Hood this card emptied -> the price to its maximum.
        economy.set_price_extreme(state, dope_type, "max", events)


def _corrupt_officer_into_base(
    state: GameState,
    player: PlayerState,
    pawn: PawnState,
    officer: OfficerState,
    events: list[DomainEvent],
    *,
    payment: DopeType | None = None,
    free: bool = False,
) -> DomainError | None:
    if officer.officer_type == OfficerType.COP:
        if officer.hood_id is None or not has_presence_at_hood(state, pawn, officer.hood_id):
            return DomainError(
                code="no_presence", message="No presence to buy this Cop.", details={}
            )
    else:
        if officer.spot_id is None or not has_presence_at_spot(state, pawn, officer.spot_id):
            return DomainError(
                code="no_presence", message="No presence to buy this Fed.", details={}
            )

    officer_cap = state.configuration["base_max_chips_per_category"]
    if officer_count_in_base(state, player.player_id) >= officer_cap:
        return DomainError(
            code="base_officer_cap_reached", message="Covo already holds 3 Cops/Feds.", details={}
        )

    price = skills.effective_cost(
        state, player, ActionType.CORRUPT_OFFICER, state.configuration["costs"]["corrupt_officer"]
    )
    if free or payment is not None:
        price = 0
    if payment is not None:
        _pay_with_dope(state, player, payment, events)
    player.money -= price
    if not free and payment is None:
        emit_skill_effects(
            state,
            events,
            player.player_id,
            skills.matching_skill_ids(
                state,
                player,
                "cost_delta",
                lambda e: ActionType.CORRUPT_OFFICER.value in e["action_types"],
            ),
        )
    carries = (
        player.active_card_boost is not None
        and player.active_card_boost["type"] == "corrupt_officer_carries_dope"
    )
    if officer.officer_type == OfficerType.COP:
        state.board.hoods[officer.hood_id].cop_ids.remove(officer.officer_id)  # type: ignore[index]
    else:
        state.board.spots[officer.spot_id].fed_ids.remove(officer.officer_id)  # type: ignore[index]

    if carries:
        _carry_dope_to_base(state, player, officer, events)
    officer.location_type = OfficerLocationType.BASE
    officer.hood_id = None
    officer.spot_id = None
    officer.owner_player_id = player.player_id
    _emit(
        state,
        events,
        OfficerCorrupted,
        buyer_player_id=player.player_id,
        seller_player_id=None,
        officer_id=officer.officer_id,
        price=price,
    )
    return None


corrupt_officer_into_base = _corrupt_officer_into_base


def _corrupt_officer_onto_map(
    state: GameState,
    player: PlayerState,
    pawn: PawnState,
    officer: OfficerState,
    destination: str | None,
    events: list[DomainEvent],
    *,
    payment: DopeType | None = None,
) -> DomainError | None:
    if destination is None:
        return DomainError(
            code="destination_required",
            message="Buying an officer onto the map requires a destination.",
            details={},
        )

    if officer.officer_type == OfficerType.COP:
        hood_id = HoodId(destination)
        if hood_id not in state.board.hoods or not has_presence_at_hood(state, pawn, hood_id):
            return DomainError(code="no_presence", message="No presence at that Hood.", details={})
    else:
        spot_id = SpotId(destination)
        if spot_id not in state.board.spots or not has_presence_at_spot(state, pawn, spot_id):
            return DomainError(code="no_presence", message="No presence at that Spot.", details={})

    seller_player_id = officer.owner_player_id
    base_price = state.configuration["costs"]["corrupt_officer"]
    # PROVISIONAL (docs/rules/RULES_PENDING.md): §C6 doesn't say whether
    # Politici-1's "-1$" is a personal discount to what the buyer pays,
    # or a market-wide price cut that also reduces what the seller
    # receives. Read as a purely personal benefit (the buyer's own Skill,
    # not the transaction's) — the seller still receives the full,
    # un-discounted price regardless of the buyer's Skills.
    buyer_price = skills.effective_cost(state, player, ActionType.CORRUPT_OFFICER, base_price)
    if payment is not None:
        # PROVISIONAL (card 82 "PAYOFF"): the Dope goes back to the supply, so the seller is
        # not paid.
        buyer_price = 0
        _pay_with_dope(state, player, payment, events)
    player.money -= buyer_price
    if payment is None:
        emit_skill_effects(
            state,
            events,
            player.player_id,
            skills.matching_skill_ids(
                state,
                player,
                "cost_delta",
                lambda e: ActionType.CORRUPT_OFFICER.value in e["action_types"],
            ),
        )
    if seller_player_id is not None and payment is None:
        find_player(state, seller_player_id).money += base_price

    officer.owner_player_id = None
    if officer.officer_type == OfficerType.COP:
        officer.location_type = OfficerLocationType.HOOD
        officer.hood_id = HoodId(destination)
        state.board.hoods[officer.hood_id].cop_ids.append(officer.officer_id)
    else:
        officer.location_type = OfficerLocationType.SPOT
        officer.spot_id = SpotId(destination)
        state.board.spots[officer.spot_id].fed_ids.append(officer.officer_id)

    _emit(
        state,
        events,
        OfficerCorrupted,
        buyer_player_id=player.player_id,
        seller_player_id=seller_player_id,
        officer_id=officer.officer_id,
        price=buyer_price,
    )
    return None
