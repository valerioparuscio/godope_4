"""Domain events: what actually happened, for animations, replay and logs.

`DomainEvent` is the common envelope; concrete rule events (CardPlayed,
DopeBought, BrawlResolved, ...) are added milestone by milestone,
alongside the rule module that produces them, rather than all at once
here.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.ids import EventId, GameId, PlayerId


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
