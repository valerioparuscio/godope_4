"""RandomLegalBot (CLAUDE.md section 14.2): picks uniformly among the
options `get_legal_decision` offered, never anything else.

Uses a deterministic sub-seed derived from (game_id, decision_id,
player_id) instead of threading the game's live RNG through every bot
call: since `decision_id` already encodes the revision at which the
decision was raised, this is fully reproducible without needing to
persist or advance any extra state (CLAUDE.md section 14.2 explicitly
allows "il RNG della partita o un sottoseed deterministico").
"""

from __future__ import annotations

import random

from dope_engine.application.legal_actions import build_command_from_selection
from dope_engine.application.views import PlayerGameView
from dope_engine.domain.commands import Command
from dope_engine.domain.decisions import PendingDecision


class RandomLegalBot:
    def choose(self, view: PlayerGameView, decision: PendingDecision) -> Command:
        rng = random.Random(f"{view.game_id}:{decision.decision_id}:{decision.player_id}")

        count = decision.min_selections
        if decision.max_selections > decision.min_selections:
            count = rng.randint(decision.min_selections, decision.max_selections)

        selected = rng.sample(decision.options, count) if count > 0 else []
        selected_ids = tuple(option.option_id for option in selected)
        return build_command_from_selection(view, decision, selected_ids)
