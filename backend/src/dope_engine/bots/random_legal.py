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
- "sell_dope": legal_actions.py (2026-08-17 fix, same class of bug as
  "buy_dope"/"corrupt_officer" below) offers every individually-legal
  (pawn, Spot, dope_type) triple unbudgeted, so more than one option can
  point at a Spot that doesn't have room for all of them, or a Dope type
  the player doesn't hold enough of for all of them — same per-pawn dedup
  as the others, *plus* a real per-Dope-type inventory budget and
  per-Spot capacity budget, both enforced by `_pick_sell_dope_options`
  using the bot's own view.
- "move_criminal": same per-pawn duplicate risk as "sell_dope" above,
  *plus* a same-Hood-destination risk plain per-pawn dedup alone doesn't
  cover — `_move_criminal_options` (2026-08-16) stopped budgeting
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
- "buy_dope": legal_actions.py (2026-08-16) offers every individually-
  legal (pawn, Hood) pair without budgeting a Hood's real stock across
  candidates, so more than one option can point at a Hood that doesn't
  actually have enough stock for all of them — same per-pawn dedup as
  above (a Link can appear in more than one option, one per Hood of its
  own Contact, 2026-08-15), *plus* a real per-Hood stock budget
  `_pick_buy_dope_options` enforces using the bot's own view, picking
  cheapest-first (ties shuffled) exactly like `_pick_cheapest_options`
  otherwise would.
- "corrupt_officer": same 2026-08-16 relaxation — every individually-
  legal (pawn, officer) pair is offered unbudgeted, so a pawn eligible
  for several officers (a Rat can reach any Cop) produces one option per
  officer. `_pick_corrupt_officer_options` dedupes by *both* pawn and
  officer while picking cheapest-first, so it never submits two
  officers using the same pawn or the same officer from two pawns — no
  external view data needed for this one, unlike buy_dope's Hood stock,
  since "1 slot per officer" is exactly what deduping by `officer_id`
  already gives. ("buy_officer" doesn't need any of this: its cost is
  flat, so any same-size subset costs the same, and its options are
  still budgeted to distinct pawns/officers by legal_actions.py, which
  never had this bug.)
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
            selected_ids = _pick_buy_dope_options(decision, count, rng, view)
        elif decision.decision_type == "corrupt_officer":
            selected_ids = _pick_corrupt_officer_options(decision, count, rng)
        elif decision.decision_type == "move_criminal":
            selected_ids = _pick_move_criminal_options(decision, count, rng, view)
        elif decision.decision_type == "sell_dope":
            selected_ids = _pick_sell_dope_options(decision, count, rng, view)
        else:
            selected = rng.sample(decision.options, count)
            selected_ids = tuple(option.option_id for option in selected)

        return build_command_from_selection(view, decision, selected_ids)


def _pick_sell_dope_options(
    decision: PendingDecision, count: int, rng: random.Random, view: PlayerGameView
) -> tuple[str, ...]:
    """Deduped by pawn, plus a real per-Dope-type inventory budget and
    per-Spot capacity budget `_sell_dope_options` (2026-08-17) no longer
    enforces at generation time — mirrors `_pick_buy_dope_options`'s Hood
    stock budget, just keyed by the player's own base inventory and each
    Spot's remaining capacity instead."""
    own_player = next(p for p in view.players if p.player_id == view.viewing_player_id)
    dope_budget = {
        dope_type.value: amount
        for dope_type, amount in own_player.base_inventory.dope_counts.items()
    }
    spot_capacity = {
        spot.spot_id: spot.capacity - len(spot.sold_dope_tokens) for spot in view.spots
    }
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    used_pawn_ids: set[str] = set()
    chosen: list[str] = []
    for option in shuffled:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        dope_type = option.payload["dope_type"]
        if dope_budget.get(dope_type, 0) <= 0:
            continue
        spot_id = option.payload["spot_id"]
        if spot_capacity.get(spot_id, 0) <= 0:
            continue
        used_pawn_ids.add(pawn_id)
        dope_budget[dope_type] -= 1
        spot_capacity[spot_id] -= 1
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def _pick_move_criminal_options(
    decision: PendingDecision, count: int, rng: random.Random, view: PlayerGameView
) -> tuple[str, ...]:
    """Deduped by pawn, plus a real per-Hood capacity budget (the Den's
    own destination isn't in `hood_capacity`, so it passes through
    unrestricted here — its own capacity is still budgeted upstream in
    `_move_criminal_options`, unchanged)."""
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


def _pick_buy_dope_options(
    decision: PendingDecision, count: int, rng: random.Random, view: PlayerGameView
) -> tuple[str, ...]:
    """Cheapest-first (ties shuffled) per-pawn dedup, plus a real per-Hood
    stock budget `_buy_dope_options` (2026-08-16) no longer enforces at
    generation time — mirrors `_pick_move_criminal_options`'s Hood
    capacity budget, just keyed by stock instead of criminal slots.

    Also tracks running cost against the player's own money: `decision.
    max_selections` is only guaranteed affordable for the *unbudgeted*
    cheapest-N raw candidates (see `_buy_dope_options`'s own docstring on
    that pre-existing, accepted tolerance) — once Hood-stock budgeting
    forces this picker to skip a contested cheap candidate and reach
    `count` using a pricier one instead, the running total can exceed
    that bound. Stopping early (returning fewer than `count`) once no
    remaining candidate still fits is what keeps this from ever
    submitting an unaffordable package (bug found via a 1500-game bot
    sweep right after the Hood-stock-budgeting fix landed: sporadic
    `insufficient_funds` CommandFailures).

    Also budgets the player's own Covo capacity per Dope type (game
    designer, 2026-08-23 — a purchase that would push a type past 3 in
    the Covo is *rejected* by `_handle_buy_dope`, not silently lost, so
    the bot must skip it here the same way it already skips a Hood whose
    stock ran out, rather than submitting it and losing the purchase)."""
    hood_stock = {hood.hood_id: len(hood.dope_stack) for hood in view.hoods}
    own_player = next(p for p in view.players if p.player_id == view.viewing_player_id)
    dope_room = {
        dope_type.value: 3 - amount
        for dope_type, amount in own_player.base_inventory.dope_counts.items()
    }
    money = own_player.money
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    shuffled.sort(key=lambda option: option.payload["price"])
    used_pawn_ids: set[str] = set()
    chosen: list[str] = []
    for option in shuffled:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        hood_id = option.payload["hood_id"]
        if hood_stock.get(hood_id, 0) <= 0:
            continue
        dope_type = option.payload["dope_type"]
        if dope_room.get(dope_type, 3) <= 0:
            continue
        price = option.payload["price"]
        if price > money:
            continue
        used_pawn_ids.add(pawn_id)
        hood_stock[hood_id] -= 1
        dope_room[dope_type] = dope_room.get(dope_type, 3) - 1
        money -= price
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def _pick_corrupt_officer_options(
    decision: PendingDecision, count: int, rng: random.Random
) -> tuple[str, ...]:
    """Cheapest-first (ties shuffled), deduped by *both* pawn and officer
    — `_corrupt_officer_options` (2026-08-16) no longer budgets officers
    to one pawn each at generation time, so a pawn eligible for several
    (e.g. a Rat) can appear more than once here."""
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    shuffled.sort(key=lambda option: option.payload["cost"])
    used_pawn_ids: set[str] = set()
    used_officer_ids: set[str] = set()
    chosen: list[str] = []
    for option in shuffled:
        pawn_id = option.payload["pawn_id"]
        officer_id = option.payload["officer_id"]
        if pawn_id in used_pawn_ids or officer_id in used_officer_ids:
            continue
        used_pawn_ids.add(pawn_id)
        used_officer_ids.add(officer_id)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)
