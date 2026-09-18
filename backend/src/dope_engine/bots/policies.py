"""Concrete BotPolicy implementations beyond the MVP RandomLegalBot
(CLAUDE.md §14.3: "euristiche modulari... profili di personalità...
livelli di difficoltà") — "basi per bot più intelligenti", 2026-08-25;
extended 2026-09-18 (game designer: "ragioniamo sul rendere piu
intelligenti i bot").

`HeuristicBot` is deliberately modest: reuses `bots/option_picking.py`'s
exact combinatorial pickers (Hood stock, Covo room, Spot capacity, money,
pawn/officer dedup — all unchanged from RandomLegalBot) for the 5 package
decision types, ordered by `bots/scoring.py`'s heuristics instead of
"cheapest"/random; and, since 2026-09-18, no longer uniform-random for a
handful of small yes/no and card-play decisions that were previously pure
coinflips regardless of how obviously good the "yes"/"play" side was (see
each branch below for the specific reasoning). Explicitly still out of
scope: `choose_action_type`/Grit-value selection (stays uniform-random,
same as RandomLegalBot) — scoring which *type* of action to take well
would need evaluating hypothetical outcomes across types, closer to real
look-ahead than option-scoring.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from dope_engine.application.data_loader import GameData
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
from dope_engine.domain.content import JobDefinition, RaidCardDefinition
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.ids import CardId, JobId, RaidCardId

# Decisions where declining/under-selecting is almost never the better
# move (game designer, 2026-09-18: "raramente conviene conservare una
# carta") — the default min..max *random* count is overridden with the
# full max_selections (capped by how many options actually exist, so an
# empty option list still safely falls through to "pass" instead of
# crashing). Which specific option(s) get picked among what's left is
# still handled per decision_type below — this only fixes *whether* to
# act at all.
_ALWAYS_MAX_DECISION_TYPES = frozenset(
    {
        "choose_brawl_link_evolution",
        "launch_poker",
        "place_poker_bet",
        "play_marketing_card",
    }
)


class HeuristicBot:
    def __init__(
        self,
        weights: HeuristicWeights | None = None,
        *,
        job_by_id: dict[JobId, JobDefinition] | None = None,
        raid_by_id: dict[RaidCardId, RaidCardDefinition] | None = None,
        gun_count_by_card_id: dict[CardId, int] | None = None,
    ) -> None:
        self._weights = weights or DEFAULT_WEIGHTS
        self._job_by_id = job_by_id or {}
        self._raid_by_id = raid_by_id or {}
        self._gun_count_by_card_id = gun_count_by_card_id or {}

    def choose(self, view: PlayerGameView, decision: PendingDecision) -> Command:
        rng = random.Random(f"{view.game_id}:{decision.decision_id}:{decision.player_id}")

        count = decision.min_selections
        if decision.max_selections > decision.min_selections:
            count = rng.randint(decision.min_selections, decision.max_selections)
        if decision.decision_type in _ALWAYS_MAX_DECISION_TYPES:
            count = min(decision.max_selections, len(decision.options))

        def key(option: DecisionOption) -> float:
            # option_picking.py's pickers sort ascending (earlier = more
            # preferred), so a higher score() must sort *earlier* —
            # negated once here instead of every heuristic needing to
            # know this convention.
            return -score_option(
                option,
                decision,
                view,
                self._weights,
                job_by_id=self._job_by_id,
                raid_by_id=self._raid_by_id,
            )

        if decision.decision_type == "evolve_sale_link":
            # Always evolve — a Link is a strictly-better standing asset
            # (double-Hood presence for buy/sell/corrupt/Rissa, extra-
            # action eligibility, end-game majority points) than the
            # Criminal it replaces. Game designer, 2026-09-18: "prendere
            # ganci dopo vendite... è in generale molto conveniente".
            yes_option = next(o for o in decision.options if o.payload.get("evolve") is True)
            selected_ids: tuple[str, ...] = (yes_option.option_id,)
        elif decision.decision_type == "play_brawl_card":
            # Play the highest-Gun card in hand — same "don't hold back"
            # principle, concretely: "se hai 3 o 4 pistole giocala
            # sempre". A 0-Gun card is neutral either way; still played,
            # same spirit (never a reason to hold back here).
            if decision.options:
                gun_counts = self._gun_count_by_card_id
                best = max(decision.options, key=lambda o: gun_counts.get(o.payload["card_id"], 0))
                selected_ids = (best.option_id,)
            else:
                selected_ids = ()
        elif decision.decision_type == "assign_brawl_guns":
            # Assigning to self always *adds* Guns to your own total
            # (assigning to someone else only ever subtracts from
            # *theirs*) — self-buffing is the simpler, more broadly
            # correct default for a modest heuristic than modelling
            # which rival is worth sabotaging instead.
            self_option = next(
                (
                    o
                    for o in decision.options
                    if o.payload.get("target_player_id") == decision.player_id
                ),
                None,
            )
            chosen = self_option or decision.options[0]
            selected_ids = (chosen.option_id,)
        elif decision.decision_type == "choose_marketing_card":
            # Which card to spend on Marketing, when 2+ qualify — more
            # Stonks means more price-manipulation power, so pick the
            # richest one rather than a random eligible card.
            if decision.options:
                best = max(decision.options, key=lambda o: o.payload["stonk_count"])
                selected_ids = (best.option_id,)
            else:
                selected_ids = ()
        elif count == 0:
            selected_ids = ()
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


def _heuristic_bot_factory(game_data: GameData) -> BotPolicy:
    return HeuristicBot(
        job_by_id={job.job_id: job for job in game_data.jobs},
        raid_by_id={raid.raid_card_id: raid for raid in game_data.raids},
        gun_count_by_card_id={card.card_id: card.gun_count for card in game_data.customer_cards},
    )


# Selectable at game creation (adapters/http/app.py::create_game,
# CreateGameRequest.bot_policy) and by tools/run_full_test_game.py's own
# --bot-policy flag — a single place both look up a policy name from,
# rather than each hardcoding its own name->class mapping. Every factory
# takes the loaded `GameData` (2026-09-18, widened from a bare zero-arg
# `Callable[[], BotPolicy]` so `HeuristicBot` can be handed the Job/Raid
# content its scoring needs — see scoring.py's own module docstring for
# why that's not the same as widening BotPolicy.choose() itself) even
# though `RandomLegalBot` itself has no use for it.
BOT_POLICY_BY_NAME: dict[str, Callable[[GameData], BotPolicy]] = {
    "random_legal": lambda game_data: RandomLegalBot(),
    "heuristic": _heuristic_bot_factory,
}
