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
legal:
- "sell_dope": a single Criminal can appear in more than one option
  (several accepted Dope types at its Contact), but the command bus
  rejects a command naming the same pawn twice. `_pick_one_option_per_pawn`
  dedupes by `payload["pawn_id"]` before sampling, which is enough — see
  the qualifying check ensuring distinct-pawn count in legal_actions.py.
- "move_criminal": same per-pawn duplicate risk as "sell_dope" above,
  *plus* a same-Hood-destination risk `_pick_one_option_per_pawn` alone
  doesn't cover — `_move_criminal_options` (2026-08-16) stopped budgeting
  a Hood's remaining capacity across candidate pawns as options are
  generated (that budgeting was silently hiding an objectively legal move
  whenever a *different* one of the player's own pawns got iterated first
  and "claimed" the scarce slot), so its options can now legitimately
  offer more than one pawn into the very same Hood even when only 1 slot
  is actually free. `_pick_move_criminal_options` does that budgeting
  here instead, using `view.hoods`' own capacity/criminal_pawn_ids —
  the decision about which pawn "wins" a scarce slot moved from the
  generator (blind to what will actually be selected) to the picker
  (which knows exactly what it's about to submit).
- "buy_dope"/"corrupt_officer": legal_actions.py only guarantees the
  *cheapest* `grit_value` options are affordable, not an arbitrary
  same-size subset. `_pick_cheapest_options` sorts by cost (after an RNG
  shuffle, so ties break randomly) and takes the cheapest slice, one per
  pawn — a Link can appear in more than one "buy_dope" option (one per
  Hood of its own Contact, game designer, 2026-08-15), the same
  more-than-one-option-per-pawn case "move_criminal"/"sell_dope" already
  had, so this needs the same per-pawn dedup they get, just cost-ordered
  instead of shuffle-ordered. ("buy_officer" doesn't need this: its cost
  is flat, so any same-size subset costs the same, and its options are
  already budgeted to distinct pawns/officers the same way
  "corrupt_officer"'s are — see legal_actions.py.)
"""

from __future__ import annotations

import random

from dope_engine.application.legal_actions import build_command_from_selection
from dope_engine.application.views import PlayerGameView
from dope_engine.domain.commands import Command
from dope_engine.domain.decisions import DecisionOption, PendingDecision


class RandomLegalBot:
    def choose(self, view: PlayerGameView, decision: PendingDecision) -> Command:
        rng = random.Random(f"{view.game_id}:{decision.decision_id}:{decision.player_id}")

        count = decision.min_selections
        if decision.max_selections > decision.min_selections:
            count = rng.randint(decision.min_selections, decision.max_selections)

        if count == 0:
            selected_ids: tuple[str, ...] = ()
        elif decision.decision_type == "buy_dope":
            selected_ids = _pick_cheapest_options(decision, count, rng, cost_key="price")
        elif decision.decision_type == "corrupt_officer":
            selected_ids = _pick_cheapest_options(decision, count, rng, cost_key="cost")
        elif decision.decision_type == "move_criminal":
            selected_ids = _pick_move_criminal_options(decision, count, rng, view)
        elif decision.decision_type == "sell_dope":
            selected_ids = _pick_one_option_per_pawn(decision, count, rng)
        else:
            selected = rng.sample(decision.options, count)
            selected_ids = tuple(option.option_id for option in selected)

        return build_command_from_selection(view, decision, selected_ids)


def _pick_one_option_per_pawn(
    decision: PendingDecision, count: int, rng: random.Random
) -> tuple[str, ...]:
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    used_pawn_ids: set[str] = set()
    chosen: list[str] = []
    for option in shuffled:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        used_pawn_ids.add(pawn_id)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def _pick_move_criminal_options(
    decision: PendingDecision, count: int, rng: random.Random, view: PlayerGameView
) -> tuple[str, ...]:
    """Like `_pick_one_option_per_pawn`, plus a real per-Hood capacity
    budget (the Den's own destination isn't in `hood_capacity`, so it
    passes through unrestricted here — its own capacity is still budgeted
    upstream in `_move_criminal_options`, unchanged)."""
    hood_capacity = {
        hood.hood_id: hood.capacity - len(hood.criminal_pawn_ids) for hood in view.hoods
    }
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    used_pawn_ids: set[str] = set()
    chosen: list[str] = []
    for option in shuffled:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        destination_id = option.payload["destination_hood_id"]
        if destination_id in hood_capacity:
            if hood_capacity[destination_id] <= 0:
                continue
            hood_capacity[destination_id] -= 1
        used_pawn_ids.add(pawn_id)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def _pick_cheapest_options(
    decision: PendingDecision, count: int, rng: random.Random, *, cost_key: str
) -> tuple[str, ...]:
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    shuffled.sort(key=lambda option: option.payload[cost_key])
    used_pawn_ids: set[str] = set()
    chosen: list[str] = []
    for option in shuffled:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        used_pawn_ids.add(pawn_id)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)
