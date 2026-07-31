"""Entities nested inside GameState: pawns, hoods, jail, spots, officers,
customer cards and decks.

Some fields CLAUDE.md lists under PlayerState (Links, completed Jobs,
REP tokens) are intentionally *not* duplicated here as separate
collections: they are derivable from a single authoritative source
(pawns for Links, `JobsState.board` for completed Jobs and REP tokens)
per the "one authoritative representation" rule in
docs/rules/CLAUDE.md section 7. See `application/views.py` (added in a
later milestone) for the read-side helpers that compute them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from dope_engine.domain.enums import ActionType, DopeType, OfficerType, PawnRole, PokerSymbolColor
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    HoodId,
    OfficerId,
    PawnId,
    PlayerId,
    SpotId,
)


class LocationType(StrEnum):
    BASE = "base"
    HOOD = "hood"
    DEN = "den"
    LINK = "link"
    JAIL = "jail"


@dataclass(frozen=True)
class PawnLocation:
    """The single authoritative position of a pawn.

    Only the fields relevant to `type` are meaningful:
    - HOOD: `hood_id` set.
    - LINK: `contact_id` set (the level is on PawnState.link_level).
    - BASE, DEN, JAIL: no extra field needed (JAIL detail lives in
      PawnState.jail_slot / JailState.slots).
    """

    type: LocationType
    hood_id: HoodId | None = None
    contact_id: ContactId | None = None

    @staticmethod
    def base() -> PawnLocation:
        return PawnLocation(type=LocationType.BASE)

    @staticmethod
    def hood(hood_id: HoodId) -> PawnLocation:
        return PawnLocation(type=LocationType.HOOD, hood_id=hood_id)

    @staticmethod
    def den() -> PawnLocation:
        return PawnLocation(type=LocationType.DEN)

    @staticmethod
    def link(contact_id: ContactId) -> PawnLocation:
        return PawnLocation(type=LocationType.LINK, contact_id=contact_id)

    @staticmethod
    def jail() -> PawnLocation:
        return PawnLocation(type=LocationType.JAIL)


@dataclass
class PawnState:
    pawn_id: PawnId
    owner_player_id: PlayerId
    role: PawnRole
    location: PawnLocation
    contact_id: ContactId | None = None  # set only when role == LINK
    link_level: int | None = None  # 1..3, set only when role == LINK
    jail_slot: int | None = None  # 0..5, set only when role == RAT


@dataclass
class HoodState:
    hood_id: HoodId
    contact_id: ContactId
    adjacent_hood_ids: list[HoodId]
    revealed: bool
    criminal_pawn_ids: list[PawnId] = field(default_factory=list)
    dope_stack: list[DopeType] = field(default_factory=list)
    cop_ids: list[OfficerId] = field(default_factory=list)
    capacity: int = 5
    # The single Dope type this Hood's market ever deals in (its starting
    # type if revealed at setup, or the type its round tile assigns once
    # activated — RULES_CANONICAL.md §F1/§F3). Kept separately from
    # `dope_stack` so a restock still knows what to refill with even
    # after the stack empties to [].
    dope_type: DopeType | None = None


@dataclass
class JailSlot:
    index: int
    rat_pawn_id: PawnId | None = None
    confiscated_dope_type: DopeType | None = None


@dataclass
class SalesSpotState:
    spot_id: SpotId
    contact_id: ContactId
    accepted_dope_type: DopeType
    adjacent_spot_ids: list[SpotId]
    sold_dope_tokens: list[DopeType] = field(default_factory=list)
    fed_ids: list[OfficerId] = field(default_factory=list)
    capacity: int = 3


class OfficerLocationType(StrEnum):
    HOOD = "hood"
    SPOT = "spot"
    BASE = "base"


@dataclass
class OfficerState:
    officer_id: OfficerId
    officer_type: OfficerType
    location_type: OfficerLocationType
    hood_id: HoodId | None = None  # set when location_type == HOOD
    spot_id: SpotId | None = None  # set when location_type == SPOT
    owner_player_id: PlayerId | None = None  # set when location_type == BASE


@dataclass
class BaseInventory:
    """A player's Covo holdings that are not pawns (Dope, Poker Chips).

    Cops/Feds held in the Covo are *not* duplicated here: they are
    OfficerState instances with location_type == BASE and
    owner_player_id set to this player.
    """

    dope_counts: dict[DopeType, int] = field(default_factory=dict)
    poker_chip_count: int = 0


@dataclass(frozen=True)
class CustomerCardDefinition:
    """Immutable definition of a Customer Card (data-driven, loaded once).

    `action_type` is `None` only for provisional/placeholder entries in
    the current PROVISIONAL card dataset (see data/customer_cards.json)
    whose base action could not be mapped to a known ActionType.
    """

    card_id: CardId
    title: str
    contact_id: ContactId
    action_type: ActionType | None
    poker_symbols: tuple[PokerSymbolColor, ...]
    stonk_count: int
    gun_count: int
    boost_text: str | None
    banco_symbols: tuple[PokerSymbolColor, ...]
    provisional: bool = False
    notes: str | None = None


@dataclass
class DeckState:
    draw_pile_card_ids: list[CardId] = field(default_factory=list)
    discard_pile_card_ids: list[CardId] = field(default_factory=list)
