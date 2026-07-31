"""The single pending decision a controller (human or bot) must resolve.

Options carry stable IDs and enough metadata for the UI to render them;
Godot (or a bot) must never reconstruct legal options on its own, only
choose among what `PendingDecision.options` already lists.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from dope_engine.domain.ids import DecisionId, PlayerId


@dataclass(frozen=True)
class DecisionOption:
    option_id: str
    label_key: str
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PendingDecision:
    decision_id: DecisionId
    player_id: PlayerId
    decision_type: str
    prompt_key: str
    context: Mapping[str, Any] = field(default_factory=dict)
    options: tuple[DecisionOption, ...] = field(default_factory=tuple)
    min_selections: int = 1
    max_selections: int = 1
    can_pass: bool = False
