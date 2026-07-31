"""The single source of legal decisions (CLAUDE.md section 10): human
frontend, bots, tests and debug tools all call `get_legal_decision`
instead of reconstructing options on their own.

The main action (RULES_CANONICAL.md §B2) is a two-step decision: first
which of the 6 base actions to spend this round's Grit value on
("choose_action_type"), then exactly `grit_value` targets for that type
(decision_type equal to the action type itself, e.g. "buy_dope"). An
action type is only offered in step 1 if a *feasible* combination of
`grit_value` targets actually exists — see the per-type `_*_options`
helpers — so a bot picking blindly among step 2's options can still hit
an infeasible combination for `buy_dope`/`sell_dope` (money/inventory
shared across options); rules/economy.py is the final authority and
rejects those normally, and bots/random_legal.py picks conservatively
(cheapest-first / conflict-aware) specifically to avoid that.

`build_command_from_selection` is the matching inverse — turning a
chosen option (or set of options, for multi-select decisions) back into
the concrete `Command` the command bus expects — shared by bots and by
the HTTP layer so there is exactly one place that knows how a
decision_type maps to a command type.
"""

from __future__ import annotations

from dope_engine.application.views import PlayerGameView
from dope_engine.domain.commands import (
    BuyDope,
    ChooseActionType,
    ChooseGritAction,
    Command,
    DiscardCards,
    MoveCriminal,
    PassOptionalStep,
    PlaceCriminal,
    SellDope,
)
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, GamePhase, PawnRole
from dope_engine.domain.ids import DEN_ID, ContactId, DecisionId, HoodId, PawnId, PlayerId, SpotId
from dope_engine.domain.state import GameState, PlayerState, find_player
from dope_engine.rules import prices
from dope_engine.rules.prices import PriceTracks


def get_legal_decision(
    state: GameState, player_id: PlayerId, price_tracks: PriceTracks
) -> PendingDecision | None:
    if state.phase != GamePhase.ACTION_PHASE or state.current_player_id != player_id:
        return None

    decision_id = DecisionId(f"decision_{state.revision:04d}")
    player = find_player(state, player_id)

    if state.active_step == ActiveStep.WAITING_FOR_GRIT_ACTION:
        options = tuple(
            DecisionOption(
                option_id=f"grit_{value}",
                label_key="decision.choose_grit_action.option",
                payload={"grit_value": value},
            )
            for value in sorted(player.available_grit_values)
        )
        return PendingDecision(
            decision_id=decision_id,
            player_id=player_id,
            decision_type="choose_grit_action",
            prompt_key="decision.choose_grit_action.prompt",
            options=options,
            min_selections=1,
            max_selections=1,
            can_pass=False,
        )

    if state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS:
        if player.pending_action_type is None:
            return _choose_action_type_decision(state, player, decision_id, price_tracks)
        return _action_targets_decision(state, player, decision_id, price_tracks)

    if state.active_step == ActiveStep.WAITING_FOR_HAND_DISCARD:
        overflow = len(player.hand_card_ids) - state.configuration["max_hand_size"]
        options = tuple(
            DecisionOption(
                option_id=f"discard_{card_id}",
                label_key="decision.hand_discard.option",
                payload={"card_id": card_id},
            )
            for card_id in player.hand_card_ids
        )
        return PendingDecision(
            decision_id=decision_id,
            player_id=player_id,
            decision_type="hand_discard",
            prompt_key="decision.hand_discard.prompt",
            options=options,
            min_selections=overflow,
            max_selections=overflow,
            can_pass=False,
        )

    return None


# --- step 1: which action type -----------------------------------------


def _choose_action_type_decision(
    state: GameState, player: PlayerState, decision_id: DecisionId, price_tracks: PriceTracks
) -> PendingDecision:
    grit_value = player.current_round_grit_value
    assert grit_value is not None

    qualifying = []
    if _place_criminal_options(state, player, grit_value) is not None:
        qualifying.append(ActionType.PLACE_CRIMINAL)
    if _move_criminal_options(state, player, grit_value) is not None:
        qualifying.append(ActionType.MOVE_CRIMINAL)
    if _buy_dope_options(state, player, grit_value, price_tracks) is not None:
        qualifying.append(ActionType.BUY_DOPE)
    if _sell_dope_options(state, player, grit_value) is not None:
        qualifying.append(ActionType.SELL_DOPE)

    options = tuple(
        DecisionOption(
            option_id=f"action_type_{action_type.value}",
            label_key="decision.choose_action_type.option",
            payload={"action_type": action_type.value},
        )
        for action_type in qualifying
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="choose_action_type",
        prompt_key="decision.choose_action_type.prompt",
        options=options,
        min_selections=1 if options else 0,
        max_selections=1 if options else 0,
        can_pass=not options,
    )


def _action_targets_decision(
    state: GameState, player: PlayerState, decision_id: DecisionId, price_tracks: PriceTracks
) -> PendingDecision:
    action_type = player.pending_action_type
    grit_value = player.current_round_grit_value
    assert action_type is not None and grit_value is not None

    options: tuple[DecisionOption, ...]
    if action_type == ActionType.PLACE_CRIMINAL:
        options = _place_criminal_options(state, player, grit_value) or ()
    elif action_type == ActionType.MOVE_CRIMINAL:
        options = _move_criminal_options(state, player, grit_value) or ()
    elif action_type == ActionType.BUY_DOPE:
        options = _buy_dope_options(state, player, grit_value, price_tracks) or ()
    elif action_type == ActionType.SELL_DOPE:
        options = _sell_dope_options(state, player, grit_value) or ()
    else:
        options = ()

    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type=action_type.value,
        prompt_key=f"decision.{action_type.value}.prompt",
        options=options,
        min_selections=grit_value,
        max_selections=grit_value,
        can_pass=False,
    )


# --- per-action-type option generators ----------------------------------
#
# Each returns `None` if fewer than `grit_value` *distinct Criminals* can
# legally perform the action (so it must not be offered at step 1),
# otherwise the full option list for step 2.


def _place_criminal_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[DecisionOption, ...] | None:
    cost_each = state.configuration["costs"]["place_criminal"]
    if cost_each > 0 and player.money // cost_each < grit_value:
        return None

    available_pawns = sum(
        1 for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    if available_pawns < grit_value:
        return None

    # Placement must never itself bring a Hood to its Rissa-trigger count
    # (economy.py's `_handle_place_criminal` docstring/comment); only
    # Movement can reach that count, which is exactly what triggers the
    # Rissa (not yet implemented — Milestone 4).
    max_via_placement = state.configuration["brawl_trigger_criminal_count"] - 1
    options: list[DecisionOption] = []
    for hood_id, hood in state.board.hoods.items():
        remaining = max_via_placement - len(hood.criminal_pawn_ids)
        for i in range(max(0, min(remaining, grit_value))):
            options.append(
                DecisionOption(
                    option_id=f"place_{hood_id}_{i}",
                    label_key="decision.place_criminal.option",
                    payload={"hood_id": hood_id},
                )
            )
    if len(options) < grit_value:
        return None
    return tuple(options)


def _move_criminal_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[DecisionOption, ...] | None:
    """Like `_sell_dope_options`, every destination's remaining capacity is
    budgeted across *all* candidate pawns as options are generated (never
    just checked against the pre-command state), so that any subset of
    `grit_value` options later chosen is jointly legal — a single
    MoveCriminal command can move several different Criminals into the
    same Hood/Den at once, which plain per-option capacity checks against
    the unchanged state would not account for."""
    options: list[DecisionOption] = []
    distinct_pawns: set[str] = set()
    remaining_capacity: dict[HoodId, int] = {
        hood_id: hood.capacity - len(hood.criminal_pawn_ids)
        for hood_id, hood in state.board.hoods.items()
    }
    remaining_den = state.configuration["den_capacity"] - len(state.board.den_gambler_pawn_ids)
    contact_ids = list(state.decks.customer_decks_by_contact.keys())

    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn_id in player.moved_pawn_ids_this_turn:
            continue

        if pawn.role == PawnRole.CRIMINAL:
            hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
            for dest_id in hood.adjacent_hood_ids:
                if remaining_capacity.get(dest_id, 0) > 0:
                    options.append(_move_option(pawn_id, dest_id, None))
                    remaining_capacity[dest_id] -= 1
                    distinct_pawns.add(pawn_id)
            if remaining_den > 0:
                for contact_id in contact_ids:
                    options.append(_move_option(pawn_id, DEN_ID, contact_id))
                remaining_den -= 1
                distinct_pawns.add(pawn_id)

        elif pawn.role == PawnRole.GAMBLER:
            for dest_id in state.board.hoods:
                if remaining_capacity.get(dest_id, 0) > 0:
                    options.append(_move_option(pawn_id, dest_id, None))
                    remaining_capacity[dest_id] -= 1
                    distinct_pawns.add(pawn_id)

    if len(distinct_pawns) < grit_value:
        return None
    return tuple(options)


def _move_option(
    pawn_id: str, destination: HoodId, deck_contact_id: ContactId | None
) -> DecisionOption:
    suffix = f"_{deck_contact_id}" if deck_contact_id else ""
    return DecisionOption(
        option_id=f"move_{pawn_id}_{destination}{suffix}",
        label_key="decision.move_criminal.option",
        payload={
            "pawn_id": pawn_id,
            "destination_hood_id": destination,
            "deck_contact_id": deck_contact_id,
        },
    )


def _buy_dope_options(
    state: GameState, player: PlayerState, grit_value: int, price_tracks: PriceTracks
) -> tuple[DecisionOption, ...] | None:
    """Like `_move_criminal_options`, a Hood's current stock is budgeted
    across candidates as they're generated, not just checked against the
    pre-command state: buying the last unit in a Hood immediately either
    empties it (blocking further buys there this package with
    "hood_has_no_dope") or restocks *and* spawns a blocking Cop
    (§C3/§A6), so a single BuyDope package can never legally buy more
    than one Hood's starting `dope_stack` length from that Hood, no
    matter which Criminals are chosen."""
    remaining_stock: dict[HoodId, int] = {
        hood_id: len(hood.dope_stack) for hood_id, hood in state.board.hoods.items()
    }
    candidates: list[tuple[int, PawnId, HoodId, DopeType]] = []
    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn.role != PawnRole.CRIMINAL:
            continue
        hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
        if hood.cop_ids or not hood.dope_stack:
            continue
        if remaining_stock.get(hood.hood_id, 0) <= 0:
            continue
        dope_type = hood.dope_stack[-1]
        price = prices.current_price(state.market, price_tracks, dope_type)
        candidates.append((price, pawn_id, hood.hood_id, dope_type))
        remaining_stock[hood.hood_id] -= 1

    if len(candidates) < grit_value:
        return None

    candidates.sort(key=lambda c: c[0])
    cheapest_cost = sum(c[0] for c in candidates[:grit_value])
    if player.money < cheapest_cost:
        return None

    return tuple(
        DecisionOption(
            option_id=f"buy_{pawn_id}",
            label_key="decision.buy_dope.option",
            payload={
                "pawn_id": pawn_id,
                "hood_id": hood_id,
                "dope_type": dope_type.value,
                "price": price,
            },
        )
        for price, pawn_id, hood_id, dope_type in candidates
    )


def _sell_dope_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[DecisionOption, ...] | None:
    candidates_by_type: dict[DopeType, list[tuple[PawnId, HoodId, SpotId, int]]] = {}
    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn.role != PawnRole.CRIMINAL:
            continue
        hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
        for spot in state.board.spots.values():
            if spot.contact_id != hood.contact_id or spot.fed_ids:
                continue
            remaining = spot.capacity - len(spot.sold_dope_tokens)
            if remaining <= 0:
                continue
            candidates_by_type.setdefault(spot.accepted_dope_type, []).append(
                (pawn_id, hood.hood_id, spot.spot_id, remaining)
            )

    options: list[DecisionOption] = []
    for dope_type, candidates in candidates_by_type.items():
        base_available = player.base_inventory.dope_counts.get(dope_type, 0)
        if base_available <= 0:
            continue
        used_per_spot: dict[SpotId, int] = {}
        added = 0
        for pawn_id, _hood_id, spot_id, spot_remaining in candidates:
            if added >= base_available:
                break
            used = used_per_spot.get(spot_id, 0)
            if used >= spot_remaining:
                continue
            used_per_spot[spot_id] = used + 1
            options.append(
                DecisionOption(
                    option_id=f"sell_{pawn_id}_{dope_type.value}_{added}",
                    label_key="decision.sell_dope.option",
                    payload={"pawn_id": pawn_id, "dope_type": dope_type.value, "spot_id": spot_id},
                )
            )
            added += 1

    distinct_pawns = {opt.payload["pawn_id"] for opt in options}
    if len(distinct_pawns) < grit_value:
        return None
    return tuple(options)


# --- decision -> command --------------------------------------------------


def build_command_from_selection(
    view: PlayerGameView,
    decision: PendingDecision,
    selected_option_ids: tuple[str, ...],
) -> Command:
    game_id = view.game_id
    player_id = decision.player_id
    expected_revision = view.revision
    decision_id = decision.decision_id
    options_by_id = {option.option_id: option for option in decision.options}
    selected = [options_by_id[oid] for oid in selected_option_ids]

    if decision.decision_type == "choose_grit_action":
        return ChooseGritAction(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            grit_value=selected[0].payload["grit_value"],
        )

    if decision.decision_type == "choose_action_type":
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return ChooseActionType(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            action_type=selected[0].payload["action_type"],
        )

    if decision.decision_type == ActionType.PLACE_CRIMINAL.value:
        return PlaceCriminal(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            hood_ids=tuple(o.payload["hood_id"] for o in selected),
        )

    if decision.decision_type == ActionType.MOVE_CRIMINAL.value:
        return MoveCriminal(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            moves=tuple(
                (
                    o.payload["pawn_id"],
                    o.payload["destination_hood_id"],
                    o.payload["deck_contact_id"],
                )
                for o in selected
            ),
        )

    if decision.decision_type == ActionType.BUY_DOPE.value:
        return BuyDope(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            pawn_ids=tuple(o.payload["pawn_id"] for o in selected),
        )

    if decision.decision_type == ActionType.SELL_DOPE.value:
        return SellDope(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            sales=tuple((o.payload["pawn_id"], DopeType(o.payload["dope_type"])) for o in selected),
        )

    if decision.decision_type == "hand_discard":
        return DiscardCards(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_ids=tuple(o.payload["card_id"] for o in selected),
        )

    raise ValueError(f"Unknown decision_type '{decision.decision_type}'")
