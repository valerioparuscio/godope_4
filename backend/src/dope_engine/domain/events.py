"""Domain events: what actually happened, for animations, replay and logs.

`DomainEvent` is the common envelope; concrete rule events (CardPlayed,
DopeBought, BrawlResolved, ...) are added milestone by milestone,
alongside the rule module that produces them, rather than all at once
here.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.ids import CardId, EventId, GameId, PlayerId, RaidCardId


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
    """Milestone 1 placeholder: no economic action exists yet, so the
    main action step is always passed. Removed once Milestone 2 adds
    real actions to choose from instead."""

    player_id: PlayerId


@dataclass(frozen=True)
class CardsDiscarded(DomainEvent):
    player_id: PlayerId
    card_ids: tuple[CardId, ...]


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
