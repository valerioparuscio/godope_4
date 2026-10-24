"""What each player may see of the event log (docs/architecture/GPT_MULTIPLAYER.md section 15).

Raw domain events are written for the engine and the replay: they name the cards a player drew,
discarded or stole, and the game's seed. A multiplayer client only ever gets them through
`filter_events_for_viewer`.

Every event type is classified, on purpose and in one place:

- `PUBLIC_EVENT_TYPES`: everyone sees it as it is. Reviewed one by one; the ones that mention a card
  id are cards played face up (a Marketing, Boost or Gamble card, a Poker or Rissa reveal).
- `REDACTORS`: a function that blanks what the viewer may not know, the way the card back is seen
  by the others at a real table: the *fact* ("Marco drew a card") stays, the *identity* goes.

A new event class that is in neither table fails `test_every_event_type_is_classified`, so nobody
can add one that leaks by forgetting this file.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import Any

from dope_engine.application.multiplayer.models import EventBatch
from dope_engine.domain import events as ev
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import PlayerId


def _blank(event: DomainEvent, **hidden: Any) -> DomainEvent:
    """The event with the given fields replaced by their "hidden" value (None, or a tuple of
    Nones for a list of cards: the same number of cards, no identity)."""
    return replace(event, **hidden)


def _hidden_cards(card_ids: tuple[Any, ...]) -> tuple[None, ...]:
    return tuple(None for _ in card_ids)


def _card_drawn(event: ev.CardDrawn, viewer: PlayerId) -> DomainEvent:
    return event if event.player_id == viewer else _blank(event, card_id=None)


def _cards_discarded(event: ev.CardsDiscarded, viewer: PlayerId) -> DomainEvent:
    if event.player_id == viewer:
        return event
    return _blank(event, card_ids=_hidden_cards(event.card_ids))


def _job_bonus_claimed(event: ev.JobBonusClaimed, viewer: PlayerId) -> DomainEvent:
    if event.player_id == viewer:
        return event
    return _blank(event, drawn_card_ids=_hidden_cards(event.drawn_card_ids))


def _brawl_reward(event: ev.BrawlLoserRewardChosen, viewer: PlayerId) -> DomainEvent:
    # The card changes hands between the two of them; nobody else sees which one.
    if viewer in (event.winner_id, event.loser_id):
        return event
    return _blank(event, stolen_card_id=None)


def _game_started(event: ev.GameStarted, viewer: PlayerId) -> DomainEvent:
    # The seed determines every shuffle: it never leaves the server.
    return replace(event, seed=0)


REDACTORS: dict[type[DomainEvent], Callable[[Any, PlayerId], DomainEvent]] = {
    ev.CardDrawn: _card_drawn,
    ev.CardsDiscarded: _cards_discarded,
    ev.JobBonusClaimed: _job_bonus_claimed,
    ev.BrawlLoserRewardChosen: _brawl_reward,
    ev.GameStarted: _game_started,
}

PUBLIC_EVENT_TYPES: frozenset[type[DomainEvent]] = frozenset(
    {
        ev.TurnStarted,
        ev.RaidRevealed,
        ev.RaidReplaced,
        ev.GritActionChosen,
        ev.MainActionPassed,
        ev.ActionTypeChosen,
        ev.CriminalPlaced,
        ev.CriminalMoved,
        ev.PawnBecameGambler,
        ev.GamblerBecameCriminal,
        ev.LinkBecameCriminal,
        ev.GamblerEvictedFromDen,
        ev.DopeBought,
        ev.DopeSold,
        ev.DopeLostToOverflow,
        ev.DopeRecovered,
        ev.PriceChanged,
        ev.MarketCrashed,
        # Played face up on the table.
        ev.MarketingCardPlayed,
        ev.CustomerCardBoostPlayed,
        ev.HoodRestocked,
        ev.CopEnteredHood,
        ev.SpotCleared,
        ev.FedEnteredSpot,
        ev.OfficerReturnedToReserve,
        ev.ActionRoundEnded,
        # The Gamble card is on the table; the cards of a Poker reveal are shown by definition.
        ev.PokerLaunched,
        ev.PokerBetsPlaced,
        # Only that the player has chosen: never which cards.
        ev.PokerCardCommitted,
        ev.PokerCardRevealed,
        ev.PokerSymbolsChosen,
        ev.PokerMatchResolved,
        ev.ShowdownPhaseResolved,
        ev.TurnEnded,
        ev.FinalScoreCalculated,
        ev.GameFinished,
        ev.PawnBecameLink,
        ev.LinkLevelChanged,
        ev.LinkPawnReturnedToBase,
        ev.LinkSpentForExtraAction,
        ev.OfficerManeuverStarted,
        ev.ManeuverPaidWithDope,
        ev.ManeuverActionApplied,
        ev.OfficerManeuverResolved,
        ev.QueuedManeuverSkipped,
        ev.OfficerMoved,
        ev.PawnArrested,
        ev.DopeConfiscated,
        ev.JailEscapeTriggered,
        ev.RatReturnedToBase,
        ev.OfficerCorrupted,
        ev.BrawlStarted,
        # Only that a card was put down face down, or that the player passed.
        ev.BrawlCardDeclared,
        # Every participant's card is turned over at once.
        ev.BrawlCardRevealed,
        ev.BrawlResolved,
        ev.BrawlTriggerTollCollected,
        ev.PawnDefeatedInBrawl,
        ev.CoveredHoodRevealed,
        ev.JobCompleted,
        ev.SkillDrawn,
        ev.SkillDiscarded,
        ev.SkillEffectApplied,
        ev.RaidFirstPlayerChosen,
        ev.RaidResolved,
        ev.ReputationStained,
    }
)


def filter_event_for_viewer(event: DomainEvent, viewer: PlayerId) -> DomainEvent:
    redactor = REDACTORS.get(type(event))
    if redactor is not None:
        return redactor(event, viewer)
    if type(event) in PUBLIC_EVENT_TYPES:
        return event
    # An event nobody classified: fail closed. (The classification test keeps this unreachable.)
    raise ValueError(f"Event type {type(event).__name__} has no visibility rule.")


def filter_events_for_viewer(
    events: Iterable[DomainEvent], viewer: PlayerId
) -> tuple[DomainEvent, ...]:
    return tuple(filter_event_for_viewer(event, viewer) for event in events)


def filter_batch_for_viewer(batch: EventBatch, viewer: PlayerId) -> EventBatch:
    return replace(batch, events=filter_events_for_viewer(batch.events, viewer))


def all_event_types() -> list[type[DomainEvent]]:
    """Every concrete event class in `domain/events.py` (for the classification test)."""
    return [
        cls
        for cls in vars(ev).values()
        if isinstance(cls, type) and issubclass(cls, DomainEvent) and cls is not DomainEvent
    ]
