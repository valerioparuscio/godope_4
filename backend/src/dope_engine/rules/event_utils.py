"""Shared helper for constructing DomainEvents with stable, sequential
IDs during command handling. Used by every rules/*.py module that emits
events, so event numbering stays consistent across all of them.
"""

from __future__ import annotations

from dope_engine.domain.events import DomainEvent, SkillEffectApplied
from dope_engine.domain.ids import EventId, PlayerId, SkillId
from dope_engine.domain.state import GameState


def emit(state: GameState, events: list[DomainEvent], event_cls: type, **extra: object) -> None:
    event_id = EventId(f"event_{state.event_log_cursor + len(events) + 1:04d}")
    events.append(
        event_cls(event_id=event_id, game_id=state.game_id, revision=state.revision, **extra)
    )


def emit_skill_effects(
    state: GameState,
    events: list[DomainEvent],
    player_id: PlayerId,
    skill_ids: tuple[SkillId, ...],
) -> None:
    """One `SkillEffectApplied` per Skill that actually fired in a
    command's resolution — called from the exact `rules/skills.py`
    call site that consumed the boosted/overridden value, not from
    validation or option-generation (those never touch `events`)."""
    for skill_id in skill_ids:
        emit(state, events, SkillEffectApplied, player_id=player_id, skill_id=skill_id)
