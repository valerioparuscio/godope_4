"""Concrete BotPolicy implementations beyond the MVP RandomLegalBot
(CLAUDE.md §14.3: "euristiche modulari... profili di personalità...
livelli di difficoltà") — "basi per bot più intelligenti", 2026-08-25.

`HeuristicBot` is the first, deliberately modest step: reuses
`bots/option_picking.py`'s exact combinatorial pickers (Hood stock, Covo
room, Spot capacity, money, pawn/officer dedup — all unchanged from
RandomLegalBot), just ordered by `bots/scoring.py`'s simple heuristics
instead of "cheapest"/random. Explicitly out of scope for this first
pass: `choose_action_type`/Grit-value selection stays uniform-random,
same as RandomLegalBot — scoring which *type* of action to take well
would need evaluating hypothetical outcomes across types, closer to real
look-ahead than option-scoring.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from dope_engine.application.legal_actions import build_command_from_selection
from dope_engine.application.views import PlayerGameView
from dope_engine.bots.base import BotPolicy
from dope_engine.bots.option_picking import (
    pick_buy_dope_options,
    pick_corrupt_officer_options,
    pick_move_criminal_options,
    pick_place_criminal_options,
    pick_sell_dope_options,
)
from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.bots.scoring import DEFAULT_WEIGHTS, HeuristicWeights, score_option
from dope_engine.domain.commands import Command
from dope_engine.domain.decisions import DecisionOption, PendingDecision


class HeuristicBot:
    def __init__(self, weights: HeuristicWeights | None = None) -> None:
        self._weights = weights or DEFAULT_WEIGHTS

    def choose(self, view: PlayerGameView, decision: PendingDecision) -> Command:
        rng = random.Random(f"{view.game_id}:{decision.decision_id}:{decision.player_id}")

        count = decision.min_selections
        if decision.max_selections > decision.min_selections:
            count = rng.randint(decision.min_selections, decision.max_selections)

        def key(option: DecisionOption) -> float:
            # option_picking.py's pickers sort ascending (earlier = more
            # preferred), so a higher score() must sort *earlier* —
            # negated once here instead of every heuristic needing to
            # know this convention.
            return -score_option(option, decision, view, self._weights)

        if count == 0:
            selected_ids: tuple[str, ...] = ()
        elif decision.decision_type == "buy_dope":
            selected_ids = pick_buy_dope_options(decision, count, rng, view, key=key)
        elif decision.decision_type == "corrupt_officer":
            selected_ids = pick_corrupt_officer_options(decision, count, rng, key=key)
        elif decision.decision_type == "move_criminal":
            selected_ids = pick_move_criminal_options(decision, count, rng, view, key=key)
        elif decision.decision_type == "sell_dope":
            selected_ids = pick_sell_dope_options(decision, count, rng, view, key=key)
        elif decision.decision_type == "place_criminal":
            selected_ids = pick_place_criminal_options(decision, count, rng, key=key)
        else:
            selected = rng.sample(decision.options, count)
            selected_ids = tuple(option.option_id for option in selected)

        return build_command_from_selection(view, decision, selected_ids)


# Selectable at game creation (adapters/http/app.py::create_game,
# CreateGameRequest.bot_policy) and by tools/run_full_test_game.py's own
# --bot-policy flag — a single place both look up a policy name from,
# rather than each hardcoding its own name->class mapping.
BOT_POLICY_BY_NAME: dict[str, Callable[[], BotPolicy]] = {
    "random_legal": RandomLegalBot,
    "heuristic": HeuristicBot,
}
