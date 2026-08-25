"""RandomLegalBot (CLAUDE.md section 14.2): picks uniformly among the
options `get_legal_decision` offered, never anything else.

Uses a deterministic sub-seed derived from (game_id, decision_id,
player_id) instead of threading the game's live RNG through every bot
call: since `decision_id` already encodes the revision at which the
decision was raised, this is fully reproducible without needing to
persist or advance any extra state (CLAUDE.md section 14.2 explicitly
allows "il RNG della partita o un sottoseed deterministico").

Plain uniform sampling is only safe when every option is an independent,
fungible slot. Several decision types break that assumption because
`application/legal_actions.py` only checks that *enough distinct
Criminals* qualify, not that *any* sampled subset of options is jointly
legal — the actual per-decision-type constraint tracking (Hood stock,
Covo room per Dope type, Spot capacity, money, pawn/officer dedup) now
lives in `bots/option_picking.py` (2026-08-25, extracted so
`bots/policies.py::HeuristicBot` can reuse it with a scoring `key`
instead of this file's own plain shuffle/cheapest-first order) — see
that module's docstring for the full history of why each budget exists.
"""

from __future__ import annotations

import random

from dope_engine.application.legal_actions import build_command_from_selection
from dope_engine.application.views import PlayerGameView
from dope_engine.bots.option_picking import (
    pick_buy_dope_options,
    pick_corrupt_officer_options,
    pick_move_criminal_options,
    pick_sell_dope_options,
)
from dope_engine.domain.commands import Command
from dope_engine.domain.decisions import PendingDecision


class RandomLegalBot:
    def choose(self, view: PlayerGameView, decision: PendingDecision) -> Command:
        rng = random.Random(f"{view.game_id}:{decision.decision_id}:{decision.player_id}")

        count = decision.min_selections
        if decision.max_selections > decision.min_selections:
            count = rng.randint(decision.min_selections, decision.max_selections)

        if count == 0:
            selected_ids: tuple[str, ...] = ()
        elif decision.decision_type == "buy_dope":
            selected_ids = pick_buy_dope_options(decision, count, rng, view)
        elif decision.decision_type == "corrupt_officer":
            selected_ids = pick_corrupt_officer_options(decision, count, rng)
        elif decision.decision_type == "move_criminal":
            selected_ids = pick_move_criminal_options(decision, count, rng, view)
        elif decision.decision_type == "sell_dope":
            selected_ids = pick_sell_dope_options(decision, count, rng, view)
        else:
            selected = rng.sample(decision.options, count)
            selected_ids = tuple(option.option_id for option in selected)

        return build_command_from_selection(view, decision, selected_ids)
