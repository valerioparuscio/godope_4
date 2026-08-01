"""Final-score data structures (RULES_CANONICAL.md §D6, CLAUDE.md
§11.14). Pure data — `rules/scoring.py` computes these; kept in the
domain package (not `rules/`) so `GameState.final_score` can be typed
precisely without `rules/` importing into `domain/`.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.ids import PlayerId


@dataclass(frozen=True)
class FinalScoreBreakdown:
    money_track_position_points: int
    clean_reputation_points: int
    stained_reputation_points: int
    contact_majority_points: int
    base_chip_points: int
    skill_points: int
    total_points: int
    # The raw *count* of clean (unstained) REP tokens — not points — used
    # only as the game's own tie-break criterion ("vince chi ha più REP
    # non macchiate"), kept separate from `clean_reputation_points`
    # (which is already ×2 and folded into `total_points`).
    tie_break_clean_reputation: int


@dataclass(frozen=True)
class FinalScoreState:
    breakdown_by_player: dict[PlayerId, FinalScoreBreakdown]
    # More than one entry means a shared victory (RULES_CANONICAL.md §D6:
    # "in caso di ulteriore pareggio la vittoria è condivisa").
    winner_ids: tuple[PlayerId, ...]
