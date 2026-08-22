"""Link creation/shifting (RULES_CANONICAL.md §A5): a Contact has 3 Link
slots, one per level (1/2/3), each holding at most one pawn — **shared
across all players** (confirmed by the game designer 2026-08-01, correcting
the original Milestone 3 implementation, which mistakenly scoped a
separate 3-slot track to each player independently): only one player's
pawn can ever occupy a given level for a given Contact at a time. This is
also why a Fed's forced "arrest the lowest-level Link" (§C5,
`rules/officers.py::_lowest_level_link_at_contact`) has always been
written as a single global minimum with no owner filter and no tie-break
needed — levels are globally unique by construction.

Inserting a new Link at level N cascades every occupied slot from N
upward one level higher (regardless of which player currently occupies
it), ejecting the level-3 occupant (if any) back to *its own owner's*
Covo — not the inserting player's.

A single Criminal evolving normally (winning a Rissa, selling 1 unit,
winning Poker, the Politici Link from a Jail escape) always inserts at
level 1. Milestone 2's "Vendita a pacchetto" (§C4) is the one case that
inserts directly at a level > 1: selling 2 or 3 Dope in one package
grants a single Link at that level, not 2-3 separate level-1 insertions.

No separate "Links" collection is kept anywhere (CLAUDE.md §7 — a single
authoritative representation per pawn): a Contact's occupied levels are
found by scanning `state.pawns` for LINK-role pawns with that
`contact_id`, exactly like `application/views.py` already does for
read-only views.
"""

from __future__ import annotations

from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import PawnRole
from dope_engine.domain.events import (
    DomainEvent,
    LinkLevelChanged,
    LinkPawnReturnedToBase,
    OfficerReturnedToReserve,
    PawnBecameLink,
)
from dope_engine.domain.ids import ContactId, PawnId, PlayerId
from dope_engine.domain.state import GameState
from dope_engine.rules.event_utils import emit as _emit

MAX_LINK_LEVEL = 3


def contact_links(state: GameState, contact_id: ContactId) -> dict[int, PawnId]:
    """The currently occupied Link levels (1..3) for a Contact, shared
    across every player — at most one pawn per level, regardless of
    owner."""
    return {
        pawn.link_level: pawn_id
        for pawn_id, pawn in state.pawns.items()
        if (
            pawn.role == PawnRole.LINK
            and pawn.contact_id == contact_id
            and pawn.link_level is not None
        )
    }


def insert_link(
    state: GameState,
    player_id: PlayerId,
    pawn_id: PawnId,
    contact_id: ContactId,
    at_level: int,
    events: list[DomainEvent],
) -> None:
    """Turns `pawn_id` (owned by `player_id`) into a Link of `contact_id`
    at `at_level`, cascading any occupants at that level and above one
    level higher first (ejecting a displaced level-3 occupant back to
    *its own owner's* base) — occupants can belong to any player, since
    the 3 slots are shared across the whole game (see module docstring).

    Only the *contiguous* run of occupied levels starting at `at_level`
    shifts — a level beyond a gap is never touched. Bug found by the game
    designer (2026-08-17): with only level 1 and level 3 occupied (level
    2 free), inserting at level 1 was incorrectly ejecting the level-3
    occupant too, because the old loop walked every occupied level from
    MAX_LINK_LEVEL down to `at_level` unconditionally, regardless of
    whether the levels in between were actually occupied — level 2 being
    empty means nothing is pushing into level 3, so it must stay put."""
    occupied = contact_links(state, contact_id)

    levels_to_shift: list[int] = []
    level = at_level
    while level <= MAX_LINK_LEVEL and level in occupied:
        levels_to_shift.append(level)
        level += 1

    for level in reversed(levels_to_shift):
        occupant_pawn_id = occupied[level]
        occupant = state.pawns[occupant_pawn_id]
        occupant_owner_id = occupant.owner_player_id
        if level == MAX_LINK_LEVEL:
            occupant.role = PawnRole.IN_BASE
            occupant.contact_id = None
            occupant.link_level = None
            occupant.location = PawnLocation.base()
            _emit(
                state,
                events,
                LinkPawnReturnedToBase,
                player_id=occupant_owner_id,
                pawn_id=occupant_pawn_id,
            )
        else:
            occupant.link_level = level + 1
            _emit(
                state,
                events,
                LinkLevelChanged,
                player_id=occupant_owner_id,
                pawn_id=occupant_pawn_id,
                contact_id=contact_id,
                new_link_level=level + 1,
            )

    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.LINK
    pawn.contact_id = contact_id
    pawn.link_level = at_level
    pawn.location = PawnLocation.link(contact_id)
    _emit(
        state,
        events,
        PawnBecameLink,
        player_id=player_id,
        pawn_id=pawn_id,
        contact_id=contact_id,
        link_level=at_level,
    )


def check_spot_fed_removal_for_contact(
    state: GameState, contact_id: ContactId, events: list[DomainEvent]
) -> None:
    """§A6 (implemented 2026-08-02, Milestone 3 gap closed): a Fed
    leaves a Spot once it has neither Dope nor a Link at its Contact.
    Lives here (not economy.py) because it must be called from both
    economy.py and turn_flow.py — turn_flow.py already imports
    economy.py, so the reverse import would cycle; both already import
    this module.

    Deliberately only ever called from a Link *disappearing*
    (`rules/officers.py`'s Fed arrest, `rules/turn_flow.py`'s spent-Link
    return-to-base) — never from the sale that empties a Spot itself: a
    Fed always spawns at the exact moment its own Spot goes dope-less
    (`rules/economy.py::_clear_spot_and_spawn_fed`), which would
    self-cancel the Fed immediately if checked there whenever no Link is
    already present, per CLAUDE.md's own note on why this was deferred
    past Milestone 2."""
    still_linked = any(
        pawn.role == PawnRole.LINK and pawn.contact_id == contact_id
        for pawn in state.pawns.values()
    )
    if still_linked:
        return
    for spot in state.board.spots.values():
        if spot.contact_id != contact_id or spot.sold_dope_tokens or not spot.fed_ids:
            continue
        for officer_id in list(spot.fed_ids):
            spot.fed_ids.remove(officer_id)
            officer = state.board.officers.pop(officer_id, None)
            if officer is not None:
                _emit(
                    state,
                    events,
                    OfficerReturnedToReserve,
                    officer_id=officer_id,
                    officer_type=officer.officer_type,
                )
