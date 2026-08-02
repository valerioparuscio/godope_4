"""Skill mechanical effects (RULES_CANONICAL.md §A10, Milestone 5 Stage
4). Each Skill's `effect` (`data/skills.json`, loaded into
`SkillDefinition.effect`) is copied once onto
`state.configuration["skill_effect_by_id"]` at setup
(`rules/setup.py::create_initial_state`) — the same "static content
lives on `state.configuration`, reachable from any rule function without
threading" pattern already used for Raid escape criteria and price
tracks (see `rules/raids.py`'s own module docstring).

This module holds the *shared* effect-lookup helpers used from more than
one rules/*.py module (so both the option-generation side in
`application/legal_actions.py` and the validation side in
`rules/economy.py`/`rules/officers.py` compute the exact same boosted
value — CLAUDE.md §10: "la validazione deve comunque essere ripetuta nel
command handler"). Effects that only ever matter to a single module
(e.g. Poker's own launch-related Skills) are implemented directly in
that module instead, reading `state.configuration["skill_effect_by_id"]`
the same way.
"""

from __future__ import annotations

from dope_engine.domain.enums import ActionType
from dope_engine.domain.state import GameState, PlayerState


def _effects_of_type(state: GameState, player: PlayerState, effect_type: str) -> list[dict]:
    by_id = state.configuration["skill_effect_by_id"]
    return [
        effect
        for skill_id in player.skill_ids
        if (effect := by_id.get(skill_id)) is not None and effect["type"] == effect_type
    ]


def effective_action_count(
    state: GameState, player: PlayerState, action_type: ActionType, base_count: int
) -> int:
    """§A10 "+1 Grinta" Skills (Artisti-1, Studenti-1, Manager-1,
    Politici-1): the number of targets a package needs for
    `action_type`, after any owned Skill's bonus. Called identically by
    the option generator (`application/legal_actions.py::
    _options_for_action_type`'s callers) and the command validator
    (`rules/economy.py::_validate_action_targets`) so both sides always
    agree on the same number."""
    total = base_count
    for effect in _effects_of_type(state, player, "extra_grit"):
        if action_type.value in effect["action_types"]:
            total += effect["amount"]
    return total


def effective_cost(
    state: GameState, player: PlayerState, action_type: ActionType, base_cost: int
) -> int:
    """§A10 flat-cost Skills (Manager-2: Place Criminal; Politici-2:
    Corrupt/Buy Officer). Clamped at 0 — a cost can never go negative
    (no rule text covers a Skill paying the player to act), same
    defensive-clamp precedent as `rules/prices.py::step_price`'s own
    track-bounds clamp."""
    total = base_cost
    for effect in _effects_of_type(state, player, "cost_delta"):
        if action_type.value in effect["action_types"]:
            total += effect["amount"]
    return max(0, total)


def effective_trade_price(
    state: GameState, player: PlayerState, action_type: ActionType, base_price: int
) -> int:
    """§A10 Artisti-2: buy Dope at -1, sell Dope at +1 (per unit).
    Clamped at 0 for the same reason as `effective_cost`."""
    total = base_price
    for effect in _effects_of_type(state, player, "trade_price_delta"):
        if action_type == ActionType.BUY_DOPE:
            total += effect["buy_delta"]
        elif action_type == ActionType.SELL_DOPE:
            total += effect["sell_delta"]
    return max(0, total)
