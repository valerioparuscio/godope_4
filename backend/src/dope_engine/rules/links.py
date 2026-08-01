"""Link creation/shifting (RULES_CANONICAL.md §A5): a Contact has 3 Link
slots, one per level (1/2/3), each holding at most one pawn. Inserting a
new Link at level N cascades every occupied slot from N upward one level
higher, ejecting the level-3 occupant (if any) back to its owner's Covo.

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
    PawnBecameLink,
)
from dope_engine.domain.ids import ContactId, PawnId, PlayerId
from dope_engine.domain.state import GameState
from dope_engine.rules.event_utils import emit as _emit

MAX_LINK_LEVEL = 3


def contact_links(
    state: GameState, player_id: PlayerId, contact_id: ContactId
) -> dict[int, PawnId]:
    """The player's currently occupied Link levels (1..3) for a Contact."""
    return {
        pawn.link_level: pawn_id
        for pawn_id, pawn in state.pawns.items()
        if (
            pawn.owner_player_id == player_id
            and pawn.role == PawnRole.LINK
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
    """Turns `pawn_id` into a Link of `contact_id` at `at_level`, cascading
    any occupants at that level and above one level higher first (ejecting
    a displaced level-3 occupant back to base)."""
    occupied = contact_links(state, player_id, contact_id)

    for level in range(MAX_LINK_LEVEL, at_level - 1, -1):
        occupant_pawn_id = occupied.get(level)
        if occupant_pawn_id is None:
            continue
        occupant = state.pawns[occupant_pawn_id]
        if level == MAX_LINK_LEVEL:
            occupant.role = PawnRole.IN_BASE
            occupant.contact_id = None
            occupant.link_level = None
            occupant.location = PawnLocation.base()
            _emit(
                state,
                events,
                LinkPawnReturnedToBase,
                player_id=player_id,
                pawn_id=occupant_pawn_id,
            )
        else:
            occupant.link_level = level + 1
            _emit(
                state,
                events,
                LinkLevelChanged,
                player_id=player_id,
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
