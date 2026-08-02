"""Officer corruption and purchase (RULES_CANONICAL.md §C5-C6): the two
Politici-boosted actions.

Corruption is the one main action that can't resolve within a single
command: each corrupted officer needs exactly 2 *different* follow-up
sub-actions (move/arrest/confiscate), and the 2nd action's legal targets
depend on the 1st's effect (e.g. a Cop that just moved can now only be
told to arrest/confiscate in its *new* Hood), so each sub-action is its
own interactive decision. `CorruptOfficer` only starts the first officer
in its package; `ChooseCorruptionAction` resolves one sub-action at a
time and auto-advances to the next queued officer once both are done
(GameState.pending_corruption / ActiveStep.WAITING_FOR_CORRUPTION_ACTION).
The whole package's total cost is validated upfront so a later officer
in the queue can never fail on money grounds after earlier ones already
committed (unlike Buy/Sell, a corruption sub-flow can't be discarded and
retried once underway without losing real progress).

Buying an officer (§C6) is a simple one-shot package like Buy/Sell Dope.

PROVISIONAL (docs/rules/RULES_PENDING.md): §C5 requires exactly 2
*different* actions, but the 2nd's legal targets depend on the 1st's
effect, so it's theoretically possible (a Cop moves into a Hood with no
Criminals and no Dope) for *no* 2nd action to be legal at all. `action`
accepts a "skip" sentinel for exactly that dead end — legal_actions.py
only offers it when no real option exists for any remaining action, and
the handler only accepts it once at least 1 real action was already
taken (so a corruption can never skip both).
"""

from __future__ import annotations

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import BuyOfficer, ChooseCorruptionAction, CorruptOfficer
from dope_engine.domain.entities import OfficerLocationType, OfficerState, PawnState
from dope_engine.domain.enums import ActionType, ActiveStep, GamePhase, OfficerType, PawnRole
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    CorruptionActionApplied,
    DomainEvent,
    OfficerBought,
    OfficerCorruptionResolved,
    OfficerCorruptionStarted,
    OfficerMoved,
)
from dope_engine.domain.ids import ContactId, HoodId, OfficerId, PawnId, PlayerId, SpotId
from dope_engine.domain.state import CorruptionProgress, GameState, PlayerState, find_player
from dope_engine.rules import economy, jail, links, skills, turn_flow
from dope_engine.rules.event_utils import emit as _emit
from dope_engine.rules.prices import PriceTracks

CORRUPTION_ACTIONS = ("move", "arrest", "confiscate")


def register_handlers(bus: CommandBus, *, price_tracks: PriceTracks) -> None:
    bus.register(CorruptOfficer, lambda s, c: _handle_corrupt_officer(s, c, price_tracks))
    bus.register(
        ChooseCorruptionAction, lambda s, c: _handle_choose_corruption_action(s, c, price_tracks)
    )
    bus.register(BuyOfficer, _handle_buy_officer)


# --- shared presence helpers ----------------------------------------------


def has_presence_at_hood(state: GameState, pawn: PawnState, hood_id: HoodId) -> bool:
    if pawn.role == PawnRole.CRIMINAL:
        return pawn.location.hood_id == hood_id
    if pawn.role == PawnRole.LINK:
        return state.board.hoods[hood_id].contact_id == pawn.contact_id
    return False


def has_presence_at_spot(state: GameState, pawn: PawnState, spot_id: SpotId) -> bool:
    spot = state.board.spots[spot_id]
    if pawn.role == PawnRole.CRIMINAL:
        return state.board.hoods[pawn.location.hood_id].contact_id == spot.contact_id  # type: ignore[index]
    if pawn.role == PawnRole.LINK:
        return pawn.contact_id == spot.contact_id
    return False


def can_corrupt_cop(state: GameState, pawn: PawnState, hood_id: HoodId) -> bool:
    return pawn.role == PawnRole.RAT or has_presence_at_hood(state, pawn, hood_id)


def can_corrupt_fed(state: GameState, pawn: PawnState, spot_id: SpotId) -> bool:
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


def officer_count_in_base(state: GameState, player_id: PlayerId) -> int:
    return sum(
        1
        for officer in state.board.officers.values()
        if officer.location_type == OfficerLocationType.BASE
        and officer.owner_player_id == player_id
    )


def corruption_cost(state: GameState, player: PlayerState, officer_type: OfficerType) -> int:
    key = "corrupt_cop" if officer_type == OfficerType.COP else "corrupt_fed"
    base_cost: int = state.configuration["costs"][key]
    return skills.effective_cost(state, player, ActionType.CORRUPT_OFFICER, base_cost)


# --- CorruptOfficer / ChooseCorruptionAction -------------------------------


def _start_corruption(
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
            message=f"Pawn '{pawn_id}' cannot corrupt an officer.",
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
        if not can_corrupt_cop(state, pawn, officer.hood_id):
            return DomainError(
                code="no_presence", message="No presence to corrupt this Cop.", details={}
            )
    else:
        if officer.location_type != OfficerLocationType.SPOT or officer.spot_id is None:
            return DomainError(
                code="officer_not_on_map", message="Fed is not in a Spot.", details={}
            )
        if not can_corrupt_fed(state, pawn, officer.spot_id):
            return DomainError(
                code="no_presence", message="No presence to corrupt this Fed.", details={}
            )

    cost = corruption_cost(state, player, officer.officer_type)
    if player.money < cost:
        return DomainError(
            code="insufficient_funds",
            message=f"Corrupting costs ${cost}.",
            details={"required": cost, "available": player.money},
        )

    player.money -= cost
    state.pending_corruption = CorruptionProgress(
        player_id=player.player_id, corruptor_pawn_id=pawn_id, officer_id=officer_id
    )
    _emit(
        state,
        events,
        OfficerCorruptionStarted,
        player_id=player.player_id,
        pawn_id=pawn_id,
        officer_id=officer_id,
        officer_type=officer.officer_type,
    )
    return None


def _handle_corrupt_officer(
    state: GameState, command: CorruptOfficer, price_tracks: PriceTracks
) -> CommandOutcome:
    error, player = economy.validate_action_targets(
        state, command.player_id, ActionType.CORRUPT_OFFICER, len(command.corruptions)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    if len({pid for pid, _ in command.corruptions}) != len(command.corruptions):
        return CommandFailure(
            DomainError(
                code="duplicate_pawn_in_targets",
                message="Each Criminal/Link/Rat can only start one corruption per action.",
                details={},
            )
        )
    if len({oid for _, oid in command.corruptions}) != len(command.corruptions):
        return CommandFailure(
            DomainError(
                code="duplicate_officer_in_targets",
                message="Each officer can only be targeted once per action.",
                details={},
            )
        )

    total_cost = 0
    for _, officer_id in command.corruptions:
        officer = state.board.officers.get(officer_id)
        if officer is None:
            return CommandFailure(
                DomainError(
                    code="unknown_officer",
                    message=f"Unknown officer '{officer_id}'.",
                    details={},
                )
            )
        total_cost += corruption_cost(state, player, officer.officer_type)
    if player.money < total_cost:
        return CommandFailure(
            DomainError(
                code="insufficient_funds",
                message=f"Corrupting this package costs ${total_cost}.",
                details={"required": total_cost, "available": player.money},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []
    queue = list(command.corruptions)
    first_pawn_id, first_officer_id = queue.pop(0)

    error = _start_corruption(state, player, first_pawn_id, first_officer_id, events)
    if error is not None:
        return CommandFailure(error)

    assert state.pending_corruption is not None
    state.pending_corruption.remaining_queue = queue
    state.active_step = ActiveStep.WAITING_FOR_CORRUPTION_ACTION
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _handle_choose_corruption_action(
    state: GameState, command: ChooseCorruptionAction, price_tracks: PriceTracks
) -> CommandOutcome:
    if state.phase != GamePhase.ACTION_PHASE:
        return CommandFailure(wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(wrong_player(str(state.current_player_id), str(command.player_id)))
    wrong_step = state.active_step != ActiveStep.WAITING_FOR_CORRUPTION_ACTION
    if wrong_step or state.pending_corruption is None:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message="Not waiting for a corruption action.",
                details={"actual_step": state.active_step.value},
            )
        )

    progress = state.pending_corruption
    if command.action == "skip":
        if not progress.actions_taken:
            return CommandFailure(
                DomainError(
                    code="cannot_skip_first_action",
                    message="Cannot skip before at least 1 corruption action was taken.",
                    details={},
                )
            )
        state.revision += 1
        skip_events: list[DomainEvent] = []
        return _finish_corruption(state, command.player_id, progress, skip_events)

    if command.action not in CORRUPTION_ACTIONS:
        return CommandFailure(
            DomainError(
                code="unknown_corruption_action",
                message=f"'{command.action}' is not a valid corruption action.",
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

    state.revision += 1
    events: list[DomainEvent] = []

    error = _apply_corruption_action(
        state, progress, officer, command.action, command.target_id, price_tracks, events
    )
    if error is not None:
        return CommandFailure(error)

    progress.actions_taken.append(command.action)
    _emit(
        state,
        events,
        CorruptionActionApplied,
        player_id=command.player_id,
        officer_id=progress.officer_id,
        action=command.action,
    )

    # The action just applied can itself remove the officer being
    # corrupted (e.g. a Cop's own "confiscate" empties its Hood of both
    # Dope and Criminals, triggering the standing "no Dope/no Criminals"
    # reserve-return check — corruption grants it no immunity from that,
    # per the confirmed "immediate re-check after every relevant event"
    # decision). With nothing left to act with, the corruption is forced
    # to a close after just this 1 action instead of the usual 2.
    officer_still_exists = progress.officer_id in state.board.officers
    if len(progress.actions_taken) < 2 and officer_still_exists:
        state.event_log_cursor += len(events)
        return CommandSuccess(state=state, events=tuple(events))

    return _finish_corruption(state, command.player_id, progress, events)


def _finish_corruption(
    state: GameState, player_id: PlayerId, progress: CorruptionProgress, events: list[DomainEvent]
) -> CommandOutcome:
    _emit(
        state,
        events,
        OfficerCorruptionResolved,
        player_id=player_id,
        officer_id=progress.officer_id,
    )
    player = find_player(state, player_id)

    # An earlier officer in the same package can, through its own 2
    # actions, invalidate a *later* queued (pawn, officer) pair (e.g. a
    # Fed's "arrest" happens to jail the very pawn queued as the next
    # corruptor). Rather than failing the whole command — which would
    # roll back this already-legitimately-applied action too, unlike
    # Buy/Sell where a failed later target never committed anything —
    # the rest of the package is simply dropped and the main/extra
    # action finishes with whatever was completed so far.
    started_next = False
    if progress.remaining_queue:
        remaining_queue = progress.remaining_queue
        next_pawn_id, next_officer_id = remaining_queue.pop(0)
        error = _start_corruption(state, player, next_pawn_id, next_officer_id, events)
        if error is None:
            assert state.pending_corruption is not None
            state.pending_corruption.remaining_queue = remaining_queue
            started_next = True

    if not started_next:
        state.pending_corruption = None
        turn_flow.finish_action_or_extra(state, player, events)

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _apply_corruption_action(
    state: GameState,
    progress: CorruptionProgress,
    officer: OfficerState,
    action: str,
    target_id: str | None,
    price_tracks: PriceTracks,
    events: list[DomainEvent],
) -> DomainError | None:
    if action == "move":
        return _apply_move(state, officer, target_id, events)
    if action == "arrest":
        return _apply_arrest(state, officer, target_id, events)
    return _apply_confiscate(state, officer, price_tracks, events)


def _apply_move(
    state: GameState, officer: OfficerState, target_id: str | None, events: list[DomainEvent]
) -> DomainError | None:
    if target_id is None:
        return DomainError(
            code="target_required", message="Move requires a destination.", details={}
        )

    if officer.officer_type == OfficerType.COP:
        current_hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
        destination = HoodId(target_id)
        if destination not in current_hood.adjacent_hood_ids:
            return DomainError(
                code="not_adjacent", message=f"'{destination}' is not adjacent.", details={}
            )
        current_hood.cop_ids.remove(officer.officer_id)
        officer.hood_id = destination
        state.board.hoods[destination].cop_ids.append(officer.officer_id)
        _emit(state, events, OfficerMoved, officer_id=officer.officer_id, hood_id=destination)
        economy.check_hood_cop_removal(state, current_hood, events)
        return None

    current_spot = state.board.spots[officer.spot_id]  # type: ignore[index]
    destination_spot = SpotId(target_id)
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
    state: GameState, officer: OfficerState, target_id: str | None, events: list[DomainEvent]
) -> DomainError | None:
    if not jail.has_free_rat_slot(state):
        return DomainError(code="jail_full", message="No free Jail slot for a Rat.", details={})

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
    links.check_spot_fed_removal_for_contact(state, spot.contact_id, events)
    return None


def _apply_confiscate(
    state: GameState, officer: OfficerState, price_tracks: PriceTracks, events: list[DomainEvent]
) -> DomainError | None:
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
        jail.confiscate_dope(state, dope_type, events)
        economy.apply_price_step(state, price_tracks, dope_type, steps=1, events=events)
        economy.check_hood_cop_removal(state, hood, events)
        return None

    spot = state.board.spots[officer.spot_id]  # type: ignore[index]
    if not spot.sold_dope_tokens:
        return DomainError(
            code="spot_has_no_dope", message=f"Spot '{spot.spot_id}' has no Dope.", details={}
        )
    dope_type = spot.sold_dope_tokens.pop()
    jail.confiscate_dope(state, dope_type, events)
    economy.apply_price_step(state, price_tracks, dope_type, steps=1, events=events)
    return None


# --- BuyOfficer -------------------------------------------------------------


def _handle_buy_officer(state: GameState, command: BuyOfficer) -> CommandOutcome:
    error, player = economy.validate_action_targets(
        state, command.player_id, ActionType.BUY_OFFICER, len(command.purchases)
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
        state, player, ActionType.BUY_OFFICER, state.configuration["costs"]["buy_officer"]
    )

    for pawn_id, officer_id, destination in command.purchases:
        if player.money < price:
            return CommandFailure(
                DomainError(
                    code="insufficient_funds",
                    message=f"Buying an officer costs ${price}.",
                    details={"required": price, "available": player.money},
                )
            )
        pawn = state.pawns.get(pawn_id)
        if pawn is None or pawn.owner_player_id != command.player_id or pawn.role not in (
            PawnRole.CRIMINAL,
            PawnRole.LINK,
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

        if officer.location_type == OfficerLocationType.BASE:
            error = _buy_officer_onto_map(state, player, pawn, officer, destination, events)
        else:
            error = _buy_officer_into_base(state, player, pawn, officer, events)
        if error is not None:
            return CommandFailure(error)
        # Milestone 5: Job 2 / Raid 5 count Cops and Feds together
        # (confirmed 2026-08-01), so one shared cumulative counter.
        player.officers_bought_count += 1

    turn_flow.finish_action_or_extra(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _buy_officer_into_base(
    state: GameState,
    player: PlayerState,
    pawn: PawnState,
    officer: OfficerState,
    events: list[DomainEvent],
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
        state, player, ActionType.BUY_OFFICER, state.configuration["costs"]["buy_officer"]
    )
    player.money -= price
    if officer.officer_type == OfficerType.COP:
        state.board.hoods[officer.hood_id].cop_ids.remove(officer.officer_id)  # type: ignore[index]
    else:
        state.board.spots[officer.spot_id].fed_ids.remove(officer.officer_id)  # type: ignore[index]

    officer.location_type = OfficerLocationType.BASE
    officer.hood_id = None
    officer.spot_id = None
    officer.owner_player_id = player.player_id
    _emit(
        state,
        events,
        OfficerBought,
        buyer_player_id=player.player_id,
        seller_player_id=None,
        officer_id=officer.officer_id,
        price=price,
    )
    return None


def _buy_officer_onto_map(
    state: GameState,
    player: PlayerState,
    pawn: PawnState,
    officer: OfficerState,
    destination: str | None,
    events: list[DomainEvent],
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
    base_price = state.configuration["costs"]["buy_officer"]
    # PROVISIONAL (docs/rules/RULES_PENDING.md): §C6 doesn't say whether
    # Politici-2's "-1$" is a personal discount to what the buyer pays,
    # or a market-wide price cut that also reduces what the seller
    # receives. Read as a purely personal benefit (the buyer's own Skill,
    # not the transaction's) — the seller still receives the full,
    # un-discounted price regardless of the buyer's Skills.
    buyer_price = skills.effective_cost(state, player, ActionType.BUY_OFFICER, base_price)
    player.money -= buyer_price
    if seller_player_id is not None:
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
        OfficerBought,
        buyer_player_id=player.player_id,
        seller_player_id=seller_player_id,
        officer_id=officer.officer_id,
        price=buyer_price,
    )
    return None
