"""Shared helper for constructing DomainEvents with stable, sequential
IDs during command handling. Used by every rules/*.py module that emits
events, so event numbering stays consistent across all of them.
"""

from __future__ import annotations

from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import EventId
from dope_engine.domain.state import GameState


def emit(state: GameState, events: list[DomainEvent], event_cls: type, **extra: object) -> None:
    event_id = EventId(f"event_{state.event_log_cursor + len(events) + 1:04d}")
    events.append(
        event_cls(event_id=event_id, game_id=state.game_id, revision=state.revision, **extra)
    )
