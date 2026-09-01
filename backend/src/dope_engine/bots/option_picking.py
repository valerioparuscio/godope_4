"""Shared combinatorial option-picking for any `BotPolicy` that needs to
turn a package decision's raw legal options into one jointly-legal
selection — extracted from `random_legal.py` (2026-08-25, "basi per bot
più intelligenti") so a scoring-driven bot (`bots/policies.py::
HeuristicBot`) can reuse the exact same hard-won constraint-tracking
logic instead of duplicating it.

Every picker below keeps its original, RandomLegalBot-era default
behavior when called with no `key`: `RandomLegalBot` (`random_legal.py`)
calls these with no `key` and must see byte-for-byte the same choices it
made before this extraction — that's what "no regression" means here,
verified by the existing test suite and bot-only sweep both continuing to
pass unchanged.

Passing a `key` (an option -> float scoring function, higher is better)
sorts the shuffled candidates by it before the same budgeting loop runs —
the constraint tracking itself (Hood stock, Covo room per Dope type, Spot
capacity, money, pawn/officer dedup) never changes based on `key`; only
the *order* candidates are considered in does, same as it always varied
with RandomLegalBot's own shuffle/price-ascending order.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from dope_engine.application.views import PlayerGameView
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.ids import DEN_ID

ScoreKey = Callable[[DecisionOption], float]


def pick_buy_dope_options(
    decision: PendingDecision,
    count: int,
    rng: random.Random,
    view: PlayerGameView,
    *,
    key: ScoreKey | None = None,
) -> tuple[str, ...]:
    """Cheapest-first (ties shuffled) per-pawn dedup by default — see
    `random_legal.py`'s original docstring for the full history of why
    this budgets Hood stock, the player's own Covo room per Dope type,
    and running money, none of which change based on `key`. Passing a
    `key` (e.g. a higher-is-better score, sorted via `-key(...)`)
    reorders which affordable/in-stock candidates are preferred; a
    scoring bot is responsible for negating its own "higher is better"
    convention into this function's ascending-sort convention."""
    hood_stock = {hood.hood_id: len(hood.dope_stack) for hood in view.hoods}
    own_player = next(p for p in view.players if p.player_id == view.viewing_player_id)
    dope_room = {
        dope_type.value: 3 - amount
        for dope_type, amount in own_player.base_inventory.dope_counts.items()
    }
    money = own_player.money
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    shuffled.sort(key=key if key is not None else lambda option: option.payload["price"])
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


def pick_sell_dope_options(
    decision: PendingDecision,
    count: int,
    rng: random.Random,
    view: PlayerGameView,
    *,
    key: ScoreKey | None = None,
) -> tuple[str, ...]:
    """Deduped by pawn, plus a real per-Dope-type inventory budget and
    per-Spot capacity budget. No default ordering (pure shuffle) unless
    `key` is given — RandomLegalBot never prioritized sell price."""
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
    if key is not None:
        shuffled.sort(key=key)
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


def pick_move_criminal_options(
    decision: PendingDecision,
    count: int,
    rng: random.Random,
    view: PlayerGameView,
    *,
    key: ScoreKey | None = None,
) -> tuple[str, ...]:
    """Deduped by pawn, plus a real per-Hood capacity budget. The Den
    (`destination_hood_id == "den"`, not in `hood_capacity`) gets its own
    analogous budget — global remaining slots and this player's own
    2-per-player cap — now tracked *here* instead of upstream in
    `legal_actions.py::_move_criminal_options` (2026-08-27: that budget
    used to live there, across-candidates, which silently hid the Den as
    a destination for whichever pawn wasn't iterated first; moved here so
    every individually-legal pawn is offered the Den, same as every other
    destination, while this picker still keeps a submitted package
    jointly legal). No default ordering (pure shuffle) unless `key` is
    given."""
    hood_capacity = {
        hood.hood_id: hood.capacity - len(hood.criminal_pawn_ids) for hood in view.hoods
    }
    remaining_den = view.den_capacity - len(view.den_gambler_pawn_ids)
    viewer_id = decision.player_id
    own_gamblers_in_den = sum(
        1
        for pawn in view.pawns
        if pawn.pawn_id in view.den_gambler_pawn_ids and pawn.owner_player_id == viewer_id
    )
    remaining_den_for_player = view.den_capacity_per_player - own_gamblers_in_den
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    if key is not None:
        shuffled.sort(key=key)
    used_pawn_ids: set[str] = set()
    chosen: list[str] = []
    for option in shuffled:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        destination_id = option.payload["destination_hood_id"]
        if destination_id == DEN_ID:
            if remaining_den <= 0 or remaining_den_for_player <= 0:
                continue
            remaining_den -= 1
            remaining_den_for_player -= 1
        elif destination_id in hood_capacity:
            if hood_capacity[destination_id] <= 0:
                continue
            hood_capacity[destination_id] -= 1
        used_pawn_ids.add(pawn_id)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def pick_place_criminal_options(
    decision: PendingDecision,
    count: int,
    rng: random.Random,
    *,
    key: ScoreKey | None = None,
) -> tuple[str, ...]:
    """Real-Hood and Jail duplicate options are already jointly legal by
    raw count alone (`legal_actions.py::_place_criminal_options` caps
    each Hood's duplicates at its own remaining capacity, and the Jail is
    never full per RULES_PENDING.md #15), so picking any subset without
    replacement stays legal on its own — no budget needed for either. The
    Den is different (cards 048/055/042/057): it offers one option per
    (slot, deck-choice) pair so the player can choose which Contact deck
    to draw from, which means several *different* options can represent
    the *same* underlying Den slot — deduped here by `den_slot_index`
    (mirrors the pawn-id dedup every other package picker in this module
    already does), so at most one deck choice per real slot is ever
    picked."""
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    if key is not None:
        shuffled.sort(key=key)
    used_den_slot_indices: set[int] = set()
    chosen: list[str] = []
    for option in shuffled:
        if option.payload["hood_id"] == DEN_ID:
            slot_index = option.payload["den_slot_index"]
            if slot_index in used_den_slot_indices:
                continue
            used_den_slot_indices.add(slot_index)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def pick_corrupt_officer_options(
    decision: PendingDecision,
    count: int,
    rng: random.Random,
    *,
    key: ScoreKey | None = None,
) -> tuple[str, ...]:
    """Cheapest-first (ties shuffled) by default, deduped by *both* pawn
    and officer — a pawn eligible for several officers (e.g. a Rat) can
    appear more than once in `decision.options`."""
    shuffled: list[DecisionOption] = list(decision.options)
    rng.shuffle(shuffled)
    shuffled.sort(key=key if key is not None else lambda option: option.payload["cost"])
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
