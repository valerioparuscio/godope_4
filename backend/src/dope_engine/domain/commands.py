"""Base envelope for player-issued commands.

Every command names the game and revision it targets so the command bus
can reject stale or duplicate submissions (see application/command_bus.py).
Concrete commands (PlaceCriminal, BuyDope, ...) are added alongside the
rule module that handles them, starting with Milestone 1/2 — Milestone 0
only needs the envelope and the dispatch plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.ids import DecisionId, GameId, PlayerId


@dataclass(frozen=True)
class Command:
    game_id: GameId
    player_id: PlayerId
    expected_revision: int
    decision_id: DecisionId | None = None
