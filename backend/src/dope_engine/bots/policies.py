"""Concrete BotPolicy implementations beyond the MVP RandomLegalBot
(CLAUDE.md §14.3: "euristiche modulari... profili di personalità...
livelli di difficoltà") — "basi per bot più intelligenti", 2026-08-25;
extended 2026-09-18 (game designer: "ragioniamo sul rendere piu
intelligenti i bot").

`HeuristicBot` is deliberately modest: reuses `bots/option_picking.py`'s
exact combinatorial pickers (Hood stock, Covo room, Spot capacity, money,
pawn/officer dedup — all unchanged from RandomLegalBot) for the 5 package
decision types, ordered by `bots/scoring.py`'s heuristics instead of
"cheapest"/random; since 2026-09-18, no longer uniform-random for a
handful of small yes/no and card-play decisions that were previously pure
coinflips regardless of how obviously good the "yes"/"play" side was (see
each branch below for the specific reasoning); since 2026-09-23,
`choose_action_type` itself is scored too (`bots/scoring.py::
score_action_type`) — a real but modest lever, measured (100-game sweep)
at +0.36 avg final score; and, same day, once that sweep showed *why*
that wasn't enough (bots completing under 1 Job/game on average),
`choose_action_type`/target-level scoring both got a `_committed_job_id`
concentration bonus, and `spend_link_for_extra_action` (previously a
literal coinflip on whether to act at all) got its own scored branch
below — measured impact was still modest (5.16 -> 5.72 avg final score
across a 200-game sweep), so the same day, `move_criminal` also gained a
job-gated override of its own Rissa-avoidance penalty (only when a
`win_brawls` Job is revealed *and* the hand holds a 2+-Gun card), and
`play_poker_card` (previously a random hand card) got its own scored
branch too — this pair was the biggest single jump of the sequence
(5.72 -> 6.21 avg). See `bots/scoring.py`'s module docstring for the
full reasoning and numbers behind all of the above. Also 2026-09-24
(game designer: "rissa and sell sono importanti per ottenere ganci da
spendere... vendendo merci con guadagni piccoli, senza necessariamente
aspettare che i prezzi siano alti"): `sell_dope`'s package size used to
be a random count between the legal min and max, same as any other
un-scored decision — since a Link's own level is set by how many units
the package sold (CLAUDE.md §11.5), a smaller-than-necessary random
package was quietly capping the Link a sale could produce. Moved into
`_ALWAYS_MAX_DECISION_TYPES` below: sell the largest legal package every
time, price be damned — `score_option`'s existing price preference still
picks *which* units fill it when there's a choice, it just no longer
also decides *how many*. Still out of scope: Grit-value selection (stays
uniform-random) and genuine look-ahead.
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
from dope_engine.bots.scoring import (
    DEFAULT_WEIGHTS,
    HeuristicWeights,
    score_action_type,
    score_option,
    score_play_poker_card_option,
    score_spend_link_for_extra_action_option,
)
from dope_engine.domain.commands import Command
from dope_engine.domain.content import JobDefinition, RaidCardDefinition
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.enums import PokerSymbolColor
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
        "sell_dope",
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
        link_extra_action_types: dict[str, tuple[str, ...]] | None = None,
        poker_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]] | None = None,
        banco_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]] | None = None,
        poker_rank_order: list[str] | None = None,
    ) -> None:
        self._weights = weights or DEFAULT_WEIGHTS
        self._job_by_id = job_by_id or {}
        self._raid_by_id = raid_by_id or {}
        self._gun_count_by_card_id = gun_count_by_card_id or {}
        self._link_extra_action_types = link_extra_action_types or {}
        self._poker_symbols_by_card_id = poker_symbols_by_card_id or {}
        self._banco_symbols_by_card_id = banco_symbols_by_card_id or {}
        self._poker_rank_order = poker_rank_order or []

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
                gun_count_by_card_id=self._gun_count_by_card_id,
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
        elif decision.decision_type == "play_poker_card":
            # Which hand card to reveal — never scored before (a random
            # hand card). Always reveals exactly 1, even when a Skill
            # would allow 2 (that routes into a separate symbol-choice
            # sub-step this bot doesn't otherwise handle) — picks
            # whichever single card forms the strongest shape against
            # the match's public banco symbols. No job-gating: unlike
            # a Rissa, revealing a better card has no extra downside
            # (the bet is already placed either way).
            if decision.options:
                best = max(
                    decision.options,
                    key=lambda o: score_play_poker_card_option(
                        o.payload["card_id"],
                        view,
                        self._poker_symbols_by_card_id,
                        self._banco_symbols_by_card_id,
                        self._poker_rank_order,
                    ),
                )
                selected_ids = (best.option_id,)
            else:
                selected_ids = ()
        elif decision.decision_type == "choose_marketing_card":
            # Which card to spend on Marketing, when 2+ qualify — more
            # Stonks means more price-manipulation power, so pick the
            # richest one rather than a random eligible card.
            if decision.options:
                best = max(decision.options, key=lambda o: o.payload["stonk_count"])
                selected_ids = (best.option_id,)
            else:
                selected_ids = ()
        elif decision.decision_type == "choose_action_type":
            # Which of the 6 action types to spend this round's Grit on —
            # the dominant lever for actually completing Jobs (see module
            # docstring). Shuffle first so ties (e.g. no Job cares about
            # any of the currently-qualifying types yet) still break
            # randomly instead of always favoring whichever type happens
            # to sort first, same pattern option_picking.py's own pickers
            # use for their own tie-breaks.
            if decision.options:
                shuffled = list(decision.options)
                rng.shuffle(shuffled)
                best = max(
                    shuffled,
                    key=lambda o: score_action_type(
                        o.payload["action_type"],
                        view,
                        decision.player_id,
                        self._job_by_id,
                        self._raid_by_id,
                        self._weights,
                    ),
                )
                selected_ids = (best.option_id,)
            else:
                selected_ids = ()
        elif decision.decision_type == "spend_link_for_extra_action":
            # Not one of _ALWAYS_MAX_DECISION_TYPES on purpose — spending
            # a Link permanently demotes it back to a plain Covo pawn, so
            # "always take it" would ignore the real cost of setting back
            # an unmet own_links Job requirement (see scoring.py's
            # module docstring). Score each candidate Link by the best
            # action type its Contact would unlock, minus that cost, and
            # only spend when it comes out ahead.
            if decision.options:

                def link_score(option: DecisionOption) -> float:
                    return score_spend_link_for_extra_action_option(
                        option.payload,
                        view,
                        decision.player_id,
                        self._job_by_id,
                        self._raid_by_id,
                        self._link_extra_action_types,
                        self._weights,
                    )

                best_link = max(decision.options, key=link_score)
                selected_ids = (best_link.option_id,) if link_score(best_link) >= 0.0 else ()
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
        link_extra_action_types={
            contact.contact_id: contact.link_extra_action_restricted_to
            for contact in game_data.contacts.contacts
        },
        poker_symbols_by_card_id={c.card_id: c.poker_symbols for c in game_data.customer_cards},
        banco_symbols_by_card_id={c.card_id: c.banco_symbols for c in game_data.customer_cards},
        poker_rank_order=game_data.config.get("poker_rank_order"),
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
