"""Domain events: what actually happened, for animations, replay and logs.

`DomainEvent` is the common envelope; concrete rule events (CardPlayed,
DopeBought, BrawlResolved, ...) are added milestone by milestone,
alongside the rule module that produces them, rather than all at once
here.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.enums import DopeType, OfficerType
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    EventId,
    GameId,
    HoodId,
    OfficerId,
    PawnId,
    PlayerId,
    RaidCardId,
    SpotId,
)


@dataclass(frozen=True)
class DomainEvent:
    event_id: EventId
    game_id: GameId
    revision: int


@dataclass(frozen=True)
class GameStarted(DomainEvent):
    seed: int
    rules_version: str
    player_ids: tuple[PlayerId, ...]


@dataclass(frozen=True)
class TurnStarted(DomainEvent):
    turn_index: int
    first_player_id: PlayerId


@dataclass(frozen=True)
class RaidRevealed(DomainEvent):
    turn_index: int
    raid_card_id: RaidCardId


@dataclass(frozen=True)
class GritActionChosen(DomainEvent):
    player_id: PlayerId
    grit_value: int


@dataclass(frozen=True)
class MainActionPassed(DomainEvent):
    """The player had no legal action-type to spend this round's Grit
    marker on (or chose to decline it)."""

    player_id: PlayerId


@dataclass(frozen=True)
class CardsDiscarded(DomainEvent):
    player_id: PlayerId
    card_ids: tuple[CardId, ...]


@dataclass(frozen=True)
class ActionTypeChosen(DomainEvent):
    player_id: PlayerId
    action_type: str


@dataclass(frozen=True)
class CardDrawn(DomainEvent):
    player_id: PlayerId
    contact_id: ContactId
    card_id: CardId


@dataclass(frozen=True)
class CriminalPlaced(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    hood_id: HoodId


@dataclass(frozen=True)
class CriminalMoved(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    from_hood_id: HoodId | None
    to_hood_id: HoodId


@dataclass(frozen=True)
class PawnBecameGambler(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId


@dataclass(frozen=True)
class GamblerBecameCriminal(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    hood_id: HoodId


@dataclass(frozen=True)
class DopeBought(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    hood_id: HoodId
    dope_type: DopeType
    price_paid: int


@dataclass(frozen=True)
class DopeSold(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    spot_id: SpotId
    dope_type: DopeType
    price_received: int


@dataclass(frozen=True)
class DopeLostToOverflow(DomainEvent):
    player_id: PlayerId
    dope_type: DopeType


@dataclass(frozen=True)
class PriceChanged(DomainEvent):
    dope_type: DopeType
    steps: int
    new_index: int


@dataclass(frozen=True)
class MarketCrashed(DomainEvent):
    pass


@dataclass(frozen=True)
class HoodRestocked(DomainEvent):
    hood_id: HoodId
    dope_type: DopeType
    count: int


@dataclass(frozen=True)
class CopEnteredHood(DomainEvent):
    officer_id: OfficerId
    hood_id: HoodId


@dataclass(frozen=True)
class SpotCleared(DomainEvent):
    spot_id: SpotId


@dataclass(frozen=True)
class FedEnteredSpot(DomainEvent):
    officer_id: OfficerId
    spot_id: SpotId


@dataclass(frozen=True)
class OfficerReturnedToReserve(DomainEvent):
    officer_id: OfficerId
    officer_type: OfficerType


@dataclass(frozen=True)
class ActionRoundEnded(DomainEvent):
    turn_index: int
    action_round_index: int
    player_id: PlayerId


@dataclass(frozen=True)
class PokerPhaseResolved(DomainEvent):
    turn_index: int


@dataclass(frozen=True)
class ShowdownPhaseResolved(DomainEvent):
    turn_index: int


@dataclass(frozen=True)
class TurnEnded(DomainEvent):
    turn_index: int


@dataclass(frozen=True)
class GameFinished(DomainEvent):
    turn_index: int
