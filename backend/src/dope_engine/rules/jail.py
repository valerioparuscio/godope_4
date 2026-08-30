"""Jail arrest, confiscation and Evasion (RULES_CANONICAL.md §A1/§C5):
shared primitives used by officer corruption (rules/officers.py) and, in
a later milestone, by Rissa/Raid resolution.

The 6 Jail slots hold Rats and confiscated Dope independently (§A1: "Nei
6 slot del Commissariato vengono messi i Rats e le Merci requisite") —
each slot's `rat_pawn_id` and `confiscated_dope_type` are filled by
separate "first available" searches, so a slot's two fields often (but
not always) end up paired from the same arrest+confiscation event, per
CLAUDE.md §7.5.
"""

from __future__ import annotations

from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import DopeType, PawnRole
from dope_engine.domain.events import (
    DomainEvent,
    DopeConfiscated,
    DopeLostToOverflow,
    JailEscapeTriggered,
    PawnArrested,
    RatReturnedToBase,
)
from dope_engine.domain.ids import ContactId, JobId, PawnId, PlayerId
from dope_engine.domain.state import GameState, find_player
from dope_engine.rules import links
from dope_engine.rules.event_utils import emit as _emit

POLITICI_CONTACT_ID = ContactId("politici")


def has_free_rat_slot(state: GameState) -> bool:
    return any(slot.rat_pawn_id is None for slot in state.jail.slots)


def has_free_confiscation_slot(state: GameState) -> bool:
    return any(slot.confiscated_dope_type is None for slot in state.jail.slots)


def arrest_pawn(state: GameState, pawn_id: PawnId, events: list[DomainEvent]) -> None:
    """Turns `pawn_id` (a Criminal or Link) into a Rat in the first free
    Jail slot. Does not touch the pawn's prior physical/virtual location
    collection (Hood.criminal_pawn_ids for a Criminal) — the caller,
    which knows where the pawn came from, is responsible for that."""
    pawn = state.pawns[pawn_id]
    owner_id = pawn.owner_player_id
    slot = next(s for s in state.jail.slots if s.rat_pawn_id is None)

    pawn.role = PawnRole.RAT
    pawn.contact_id = None
    pawn.link_level = None
    pawn.jail_slot = slot.index
    pawn.location = PawnLocation.jail()
    slot.rat_pawn_id = pawn_id

    _emit(
        state, events, PawnArrested, player_id=owner_id, pawn_id=pawn_id, jail_slot_index=slot.index
    )

    if all(s.rat_pawn_id is not None for s in state.jail.slots):
        # Bug report (2026-08-27): Job 4 ("Abbi 3 Rats") never completed
        # for a player whose 3rd Rat was also the one that triggered
        # Evasion — the post-success hook that normally checks Job
        # completion only runs once, at the very end of the whole
        # command, by which point _resolve_evasion below has already
        # returned every Rat (this player's included) to base, so the
        # live snapshot no longer shows 3. Checked here instead, at the
        # one moment the snapshot can actually be true: right as the 6th
        # slot fills, before Evasion undoes it. Lazy import (not a
        # module-level one) to avoid a cycle: rules/officers.py and
        # rules/poker.py both import this module and call arrest_pawn,
        # and rules/jobs.py needs no import back to either of them, so
        # this one edge is safe to add without looping.
        from dope_engine.domain.content import JobDefinition
        from dope_engine.rules import jobs

        job_by_id = {
            JobId(job_id): JobDefinition(
                job_id=JobId(d["job_id"]),
                title=d["title"],
                tier=d["tier"],
                contact_ids=tuple(ContactId(c) for c in d["contact_ids"]),
                requirement=d["requirement"],
            )
            for job_id, d in state.configuration["job_definition_by_id"].items()
        }
        jobs.detect_and_queue_completions(state, events, job_by_id)
        _resolve_evasion(state, pawn_id, events)


def confiscate_dope(state: GameState, dope_type: DopeType, events: list[DomainEvent]) -> None:
    slot = next(s for s in state.jail.slots if s.confiscated_dope_type is None)
    slot.confiscated_dope_type = dope_type
    _emit(state, events, DopeConfiscated, dope_type=dope_type, jail_slot_index=slot.index)


def _resolve_evasion(
    state: GameState, triggering_pawn_id: PawnId, events: list[DomainEvent]
) -> None:
    """RULES_CANONICAL.md §A1: the 6th Rat (the one that just filled the
    last slot) evolves directly into a Politici Link instead of
    returning to base; the other 5 return to their Covo, each bringing
    the Dope in its own slot (if any — recovered Dope above the usual
    3-per-type Covo cap is lost, same overflow rule as a purchase,
    §A2)."""
    _emit(state, events, JailEscapeTriggered, triggering_pawn_id=triggering_pawn_id)

    for slot in list(state.jail.slots):
        rat_pawn_id = slot.rat_pawn_id
        assert rat_pawn_id is not None
        pawn = state.pawns[rat_pawn_id]
        owner_id = pawn.owner_player_id
        dope_type = slot.confiscated_dope_type
        slot.rat_pawn_id = None
        slot.confiscated_dope_type = None

        if rat_pawn_id == triggering_pawn_id:
            links.insert_link(state, owner_id, rat_pawn_id, POLITICI_CONTACT_ID, 1, events)
            recover_dope(state, owner_id, dope_type, events)
            continue

        pawn.role = PawnRole.IN_BASE
        pawn.jail_slot = None
        pawn.location = PawnLocation.base()
        _emit(
            state,
            events,
            RatReturnedToBase,
            player_id=owner_id,
            pawn_id=rat_pawn_id,
            recovered_dope_type=dope_type,
        )
        recover_dope(state, owner_id, dope_type, events)


def recover_dope(
    state: GameState, owner_id: PlayerId, dope_type: DopeType | None, events: list[DomainEvent]
) -> None:
    """Adds one unit of `dope_type` to `owner_id`'s Covo, respecting the
    3-per-type cap (overflow lost, same rule as a purchase, §A2) — shared
    by `_resolve_evasion` above (a Rat's own slot) and
    `rules/officers.py::_apply_confiscate` (card 063/064 "FAKE POLICE",
    "prendi la Merce requisita": the confiscator keeps it immediately
    instead of it sitting in the Jail slot)."""
    if dope_type is None:
        return
    inventory = find_player(state, owner_id).base_inventory
    if inventory.dope_counts.get(dope_type, 0) >= 3:
        _emit(state, events, DopeLostToOverflow, player_id=owner_id, dope_type=dope_type)
    else:
        inventory.dope_counts[dope_type] = inventory.dope_counts.get(dope_type, 0) + 1
