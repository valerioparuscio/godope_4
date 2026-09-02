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

from collections.abc import Callable

from dope_engine.domain.enums import ActionType, PawnRole
from dope_engine.domain.ids import SkillId
from dope_engine.domain.state import GameState, PlayerState


def _effects_of_type(state: GameState, player: PlayerState, effect_type: str) -> list[dict]:
    by_id = state.configuration["skill_effect_by_id"]
    effects = [
        effect
        for skill_id in player.skill_ids
        if (effect := by_id.get(skill_id)) is not None and effect["type"] == effect_type
    ]
    # A played Customer Card boost (game designer, 2026-08-27,
    # rules/customer_cards.py) is mechanically just a one-shot, one-action
    # Skill: `PlayerState.active_card_boost` is shaped identically to a
    # skill_effect_by_id entry, so it folds into the exact same
    # effective_cost/effective_action_count/effective_trade_price lookups
    # everywhere they're already called, with no changes needed there.
    boost = player.active_card_boost
    if boost is not None and boost["type"] == effect_type:
        effects.append(boost)
    return effects


def matching_skill_ids(
    state: GameState,
    player: PlayerState,
    effect_type: str,
    predicate: Callable[[dict], bool] | None = None,
) -> tuple[SkillId, ...]:
    """The `skill_id`s (not the effect dicts) among the player's owned
    Skills whose effect is `effect_type` and, if given, satisfies
    `predicate` — for `rules/event_utils.py::emit_skill_effects` to
    attribute a `SkillEffectApplied` event to. A resolution handler calls
    this with the *same* condition its own `effective_*`/`can_*` call
    above just used, so "matched" here always means "actually applied to
    this specific command", never just "the player happens to own it"."""
    by_id = state.configuration["skill_effect_by_id"]
    return tuple(
        skill_id
        for skill_id in player.skill_ids
        if (effect := by_id.get(skill_id)) is not None
        and effect["type"] == effect_type
        and (predicate is None or predicate(effect))
    )


def effective_action_count(
    state: GameState, player: PlayerState, action_type: ActionType, base_count: int
) -> int:
    """§A10 "+1 Grinta" Skills (Artisti-1, Studenti-1, Manager-1,
    Politici-2 — was Politici-1 before the 2026-09-02 text/effect swap):
    the number of targets a package needs for
    `action_type`, after any owned Skill's bonus. Called identically by
    the option generator (`application/legal_actions.py::
    _options_for_action_type`'s callers) and the command validator
    (`rules/economy.py::_validate_action_targets`) so both sides always
    agree on the same number."""
    total = base_count
    for effect in _effects_of_type(state, player, "extra_grit"):
        if action_type.value in effect["action_types"]:
            total += effect["amount"]
    # Cards 041/049 "REINFORCE" ("piazzi 2 per ogni Grinta, ma non peschi
    # carte"): a multiplier, not a flat delta — applied after the
    # additive Skills above, same "one shared function both sides call"
    # principle. The "non peschi carte" half lives in
    # `rules/economy.py::_handle_place_criminal` instead (nothing to do
    # with the target *count* this function computes).
    boost = player.active_card_boost
    if (
        boost is not None
        and boost["type"] == "place_double_no_draw"
        and action_type.value in boost["action_types"]
    ):
        total *= boost["multiplier"]
    # Cards 044/051 "INVADE" ("piazzi uno in ogni quartiere dove sei
    # presente", game designer, 2026-08-31: "ignora il valore di Grinta"
    # — confirmed uncapped, not just an additive/multiplicative bonus on
    # top of it): replaces `total` outright with the number of revealed
    # Hoods where the player already has a Criminal or Link (a Link
    # counts in both Hoods of its Contact, same canonical "presence"
    # `rules/economy.py::has_presence_at_hood` already uses everywhere
    # else — inlined here, not imported, since economy.py already
    # imports this module and importing it back would cycle). The real
    # ceiling on how many of those a package can actually use (available
    # Covo pawns, money, remaining Hood capacity) is still enforced
    # downstream exactly like any other action, unaffected by this
    # override.
    if (
        boost is not None
        and boost["type"] == "invade_own_hoods"
        and action_type.value in boost["action_types"]
    ):
        total = sum(
            1
            for hood_id, hood in state.board.hoods.items()
            if hood.revealed
            and any(
                (
                    state.pawns[pid].role == PawnRole.CRIMINAL
                    and state.pawns[pid].location.hood_id == hood_id
                )
                or (
                    state.pawns[pid].role == PawnRole.LINK
                    and state.pawns[pid].contact_id == hood.contact_id
                )
                for pid in player.pawn_ids
            )
        )
    # Cards 052/056 "REINFORCE" ("con Grinta 3, scarta una Merce e piazzi
    # quanto il suo valore" — confirmed 2026-08-31: the value is the
    # discarded Dope's *current sell price*, ignoring Grit entirely, same
    # "replace, don't add" override shape as `invade_own_hoods` above):
    # `rules/customer_cards.py`'s boost application defers this exact
    # count to `ChooseReinforceDiscard`
    # (`rules/economy.py::_handle_choose_reinforce_discard`), which
    # stores it back onto the boost dict once the player picks which
    # Dope type to discard — `get(..., 0)` is only ever hit in the brief
    # window before that choice resolves, when this function isn't
    # actually consulted yet (nothing offers `place_criminal` targets
    # before `ActiveStep.WAITING_FOR_REINFORCE_DISCARD` clears).
    if (
        boost is not None
        and boost["type"] == "reinforce_dope_discard"
        and action_type.value in boost["action_types"]
    ):
        total = boost.get("reinforce_placement_count", 0)
    return total


def effective_cost(
    state: GameState, player: PlayerState, action_type: ActionType, base_cost: int
) -> int:
    """§A10 flat-cost Skills (Manager-2: Place Criminal; Politici-1 —
    was Politici-2 before the 2026-09-02 text/effect swap: Corrupt/Buy
    Officer). Clamped at 0 — a cost can never go negative
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


def extra_gun_bonus(state: GameState, player: PlayerState) -> int:
    """§A10 Studenti-2: +1 Gun whenever this player fields a played
    Brawl card (`rules/brawl.py::_effective_guns`) — attached to the
    card's own Gun count rather than a standalone bonus, since Guns only
    ever matter once assigned to a target and a card-less participant
    never reaches the assignment step at all."""
    return sum(effect["amount"] for effect in _effects_of_type(state, player, "extra_gun"))


def poker_launch_cashout(state: GameState, player: PlayerState, base_amount: int) -> int:
    """§A10 Preti-2: launching a Poker match pays a flat 6 instead of
    the base cashout — `data/skills.json`'s `amount: 6` is the full
    replacement value, not a delta on top of the base."""
    overrides = _effects_of_type(state, player, "poker_launch_cashout_override")
    if overrides:
        return overrides[-1]["amount"]
    return base_amount


def can_launch_poker_any_action(state: GameState, player: PlayerState) -> bool:
    """§A10 Preti-3: removes the "the card's own action_type must match
    this round's action" restriction (RULES_CANONICAL.md §D2) on
    launching a Poker match."""
    return bool(_effects_of_type(state, player, "poker_launch_any_action"))


def can_reveal_two_poker_cards(state: GameState, player: PlayerState) -> bool:
    """§A10 Preti-1 "Puoi giocare 2 carte per ogni Poker (scegli 2
    simboli)": lets a bettor reveal 2 hand cards for one match instead of
    1, choosing 2 of the resulting 4 symbols for their final hand
    (`rules/poker.py::_handle_play_poker_card`/`_handle_choose_poker_symbols`,
    `domain/state.py::PendingPokerSymbolChoice`). Purely optional
    ("puoi") — revealing just 1 card still works exactly as without the
    Skill."""
    return bool(_effects_of_type(state, player, "poker_reveal_two_cards"))


def max_link_extra_actions_per_round(state: GameState, player: PlayerState) -> int:
    """§A10 Politici-3: the Link extra action, normally usable once per
    *round* (§A5, 2026-08-17 decision — was once per whole turn until
    then), becomes usable up to `amount` times per round instead. The
    card's own printed text ("Puoi attivare 2 Ganci a turno") predates
    that decision and still reads "per turn" — reinterpreted as "per
    round" here so the Skill stays a real 2x multiplier on the new
    baseline instead of *underselling* it (a literal "2 per turn" would
    be worse than the un-boosted "1 per round = 3 per turn" baseline).
    Flagged to the game designer for confirmation, not a settled
    decision — see RULE_CHANGELOG.md's 2026-08-17 entry."""
    total = 1
    for effect in _effects_of_type(state, player, "extra_link_action_slot"):
        total = max(total, effect["amount"])
    return total


def sell_link_from_base(state: GameState, player: PlayerState) -> bool:
    """§A10 Artisti-3: replaces (confirmed by the game designer,
    2026-08-02 — not additive) the automatic sell-Dope Link evolution
    (`rules/economy.py::_handle_sell_dope`): instead of the selling pawn
    itself evolving, a fresh Covo pawn does, and the selling pawn stays
    a Criminal in the Hood."""
    return bool(_effects_of_type(state, player, "link_from_base_on_sell"))


def marketing_applies_both_timings(state: GameState, player: PlayerState) -> bool:
    """§A10 Manager-3 "Applichi Stonk 2 volte, prima e dopo l'azione":
    each allocated Stonk (`rules/economy.py::_handle_play_marketing_card`)
    fires at both the "before" and "after" checkpoint automatically,
    instead of the player choosing one timing per Stonk (base behavior)."""
    return bool(_effects_of_type(state, player, "double_stonk"))


def brawl_win_link_from_base(state: GameState, player: PlayerState) -> bool:
    """§A10 Studenti-3: same replacement as `sell_link_from_base`, for
    the Rissa winner's Link-evolution reward
    (`rules/brawl.py::_handle_choose_brawl_loser_reward`'s tail) —
    becomes automatic (a fresh Covo pawn evolves whenever one is
    available) rather than an explicit player choice, matching
    Artisti-3's own automatic wording ("quando vendi/vinci... mandi")."""
    return bool(_effects_of_type(state, player, "link_from_base_on_brawl_win"))
