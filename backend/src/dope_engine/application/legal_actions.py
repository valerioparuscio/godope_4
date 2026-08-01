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
    AssignBrawlGuns,
    BuyDope,
    BuyOfficer,
    ChooseActionType,
    ChooseBrawlLinkEvolution,
    ChooseBrawlLoserReward,
    ChooseBrawlRelocationDestination,
    ChooseCorruptionAction,
    ChooseGritAction,
    Command,
    CorruptOfficer,
    DiscardCards,
    MoveCriminal,
    PassOptionalStep,
    PlaceCriminal,
    PlayBrawlCard,
    SellDope,
    SpendLinkForExtraAction,
)
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.entities import OfficerLocationType, OfficerState, PawnState
from dope_engine.domain.enums import (
    ActionType,
    ActiveStep,
    DopeType,
    GamePhase,
    OfficerType,
    PawnRole,
)
from dope_engine.domain.ids import (
    DEN_ID,
    ContactId,
    DecisionId,
    HoodId,
    OfficerId,
    PawnId,
    PlayerId,
    SpotId,
)
from dope_engine.domain.state import GameState, PlayerState, find_player
from dope_engine.rules import jail, officers, prices
from dope_engine.rules.prices import PriceTracks


def get_legal_decision(
    state: GameState,
    player_id: PlayerId,
    price_tracks: PriceTracks,
    link_extra_action_types: dict[ContactId, tuple[str, ...]],
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

    if state.active_step == ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION:
        return _link_extra_action_decision(
            state, player, decision_id, price_tracks, link_extra_action_types
        )

    if state.active_step == ActiveStep.WAITING_FOR_CORRUPTION_ACTION:
        return _corruption_action_decision(state, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_BRAWL_CARD:
        return _brawl_card_decision(state, player_id, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_BRAWL_ASSIGNMENT:
        return _brawl_assignment_decision(state, player_id, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_BRAWL_REWARD:
        return _brawl_reward_decision(state, player_id, decision_id)

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

_ALL_ACTION_TYPES: tuple[ActionType, ...] = (
    ActionType.PLACE_CRIMINAL,
    ActionType.MOVE_CRIMINAL,
    ActionType.BUY_DOPE,
    ActionType.SELL_DOPE,
    ActionType.CORRUPT_OFFICER,
    ActionType.BUY_OFFICER,
)


def _options_for_action_type(
    action_type: ActionType,
    state: GameState,
    player: PlayerState,
    grit_value: int,
    price_tracks: PriceTracks,
) -> tuple[DecisionOption, ...] | None:
    if action_type == ActionType.PLACE_CRIMINAL:
        return _place_criminal_options(state, player, grit_value)
    if action_type == ActionType.MOVE_CRIMINAL:
        return _move_criminal_options(state, player, grit_value)
    if action_type == ActionType.BUY_DOPE:
        return _buy_dope_options(state, player, grit_value, price_tracks)
    if action_type == ActionType.SELL_DOPE:
        return _sell_dope_options(state, player, grit_value)
    if action_type == ActionType.CORRUPT_OFFICER:
        return _corrupt_officer_options(state, player, grit_value)
    return _buy_officer_options(state, player, grit_value)


def _choose_action_type_decision(
    state: GameState,
    player: PlayerState,
    decision_id: DecisionId,
    price_tracks: PriceTracks,
    candidate_action_types: tuple[ActionType, ...] = _ALL_ACTION_TYPES,
) -> PendingDecision:
    grit_value = player.current_round_grit_value
    assert grit_value is not None

    qualifying = [
        action_type
        for action_type in candidate_action_types
        if _options_for_action_type(action_type, state, player, grit_value, price_tracks)
        is not None
    ]

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

    options = _options_for_action_type(action_type, state, player, grit_value, price_tracks) or ()

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


# --- Link extra action (WAITING_FOR_LINK_EXTRA_ACTION) ---------------------


def _link_extra_action_decision(
    state: GameState,
    player: PlayerState,
    decision_id: DecisionId,
    price_tracks: PriceTracks,
    link_extra_action_types: dict[ContactId, tuple[str, ...]],
) -> PendingDecision:
    if player.extra_action_link_pawn_id is None:
        return _choose_extra_action_link_decision(
            state, player, decision_id, price_tracks, link_extra_action_types
        )

    # The spent Link already returned to its Covo (contact_id cleared)
    # the moment it was chosen (rules/turn_flow.py, §A5, confirmed
    # 2026-08-01), so which action types it unlocks is read from the
    # player's own cached `extra_action_contact_id`, not the pawn.
    contact_id = player.extra_action_contact_id
    assert contact_id is not None
    allowed_types = tuple(
        ActionType(value) for value in link_extra_action_types.get(contact_id, ())
    )
    if player.pending_action_type is None:
        return _choose_action_type_decision(state, player, decision_id, price_tracks, allowed_types)
    return _action_targets_decision(state, player, decision_id, price_tracks)


def _choose_extra_action_link_decision(
    state: GameState,
    player: PlayerState,
    decision_id: DecisionId,
    price_tracks: PriceTracks,
    link_extra_action_types: dict[ContactId, tuple[str, ...]],
) -> PendingDecision:
    options: list[DecisionOption] = []
    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn.role != PawnRole.LINK or pawn.link_level is None or pawn.contact_id is None:
            continue
        allowed_types = tuple(
            ActionType(value) for value in link_extra_action_types.get(pawn.contact_id, ())
        )
        qualifies = any(
            _options_for_action_type(action_type, state, player, pawn.link_level, price_tracks)
            is not None
            for action_type in allowed_types
        )
        if qualifies:
            options.append(
                DecisionOption(
                    option_id=f"spend_link_{pawn_id}",
                    label_key="decision.spend_link_for_extra_action.option",
                    payload={
                        "pawn_id": pawn_id,
                        "contact_id": pawn.contact_id,
                        "link_level": pawn.link_level,
                    },
                )
            )

    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="spend_link_for_extra_action",
        prompt_key="decision.spend_link_for_extra_action.prompt",
        options=tuple(options),
        min_selections=0,
        max_selections=1 if options else 0,
        can_pass=True,
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


def _corrupt_officer_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[DecisionOption, ...] | None:
    """Like `_buy_dope_options`: each candidate officer is budgeted to at
    most one (pawn, officer) pair (`used_officers`) so no subset of
    `grit_value` selections can target the same officer twice — the
    command bus also rejects that, but conservative generation keeps a
    uniformly-sampling bot safe by construction. Cheapest-`grit_value`
    affordability is checked the same way as `_buy_dope_options`."""
    candidates: list[tuple[int, PawnId, OfficerId]] = []
    used_officers: set[OfficerId] = set()

    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK, PawnRole.RAT):
            continue
        for officer_id, officer in state.board.officers.items():
            if officer_id in used_officers:
                continue
            if officer.officer_type == OfficerType.COP:
                if officer.location_type != OfficerLocationType.HOOD or officer.hood_id is None:
                    continue
                if not officers.can_corrupt_cop(state, pawn, officer.hood_id):
                    continue
                cost = state.configuration["costs"]["corrupt_cop"]
            else:
                if officer.location_type != OfficerLocationType.SPOT or officer.spot_id is None:
                    continue
                if not officers.can_corrupt_fed(state, pawn, officer.spot_id):
                    continue
                cost = state.configuration["costs"]["corrupt_fed"]

            candidates.append((cost, pawn_id, officer_id))
            used_officers.add(officer_id)
            break

    if len(candidates) < grit_value:
        return None

    candidates.sort(key=lambda c: c[0])
    cheapest_cost = sum(c[0] for c in candidates[:grit_value])
    if player.money < cheapest_cost:
        return None

    return tuple(
        DecisionOption(
            option_id=f"corrupt_{pawn_id}_{officer_id}",
            label_key="decision.corrupt_officer.option",
            payload={"pawn_id": pawn_id, "officer_id": officer_id, "cost": cost},
        )
        for cost, pawn_id, officer_id in candidates
    )


def _buy_officer_destination(
    state: GameState, pawn: PawnState, officer: OfficerState
) -> tuple[bool, str | None]:
    if officer.location_type == OfficerLocationType.BASE:
        if officer.officer_type == OfficerType.COP:
            for hood_id in state.board.hoods:
                if officers.has_presence_at_hood(state, pawn, hood_id):
                    return True, hood_id
            return False, None
        for spot_id in state.board.spots:
            if officers.has_presence_at_spot(state, pawn, spot_id):
                return True, spot_id
        return False, None

    if officer.officer_type == OfficerType.COP:
        if officer.hood_id is not None and officers.has_presence_at_hood(
            state, pawn, officer.hood_id
        ):
            return True, None
        return False, None
    if officer.spot_id is not None and officers.has_presence_at_spot(state, pawn, officer.spot_id):
        return True, None
    return False, None


def _buy_officer_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[DecisionOption, ...] | None:
    """One option per qualifying (pawn, officer) pair, budgeted to at most
    one pawn per officer (`used_officers`) — same reasoning as
    `_corrupt_officer_options`. Cost is flat ($7 each), so affordability
    is just `grit_value * cost_each`, no cheapest-first sort needed."""
    cost_each = state.configuration["costs"]["buy_officer"]
    if player.money < cost_each * grit_value:
        return None

    options: list[DecisionOption] = []
    distinct_pawns: set[str] = set()
    used_officers: set[OfficerId] = set()

    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK):
            continue
        for officer_id, officer in state.board.officers.items():
            if officer_id in used_officers:
                continue
            matched, destination = _buy_officer_destination(state, pawn, officer)
            if not matched:
                continue
            options.append(
                DecisionOption(
                    option_id=f"buyofficer_{pawn_id}_{officer_id}",
                    label_key="decision.buy_officer.option",
                    payload={
                        "pawn_id": pawn_id,
                        "officer_id": officer_id,
                        "destination": destination,
                    },
                )
            )
            used_officers.add(officer_id)
            distinct_pawns.add(pawn_id)
            break

    if len(distinct_pawns) < grit_value:
        return None
    return tuple(options)


# --- corruption sub-decision (WAITING_FOR_CORRUPTION_ACTION) --------------


def _corruption_action_decision(state: GameState, decision_id: DecisionId) -> PendingDecision:
    progress = state.pending_corruption
    assert progress is not None
    officer = state.board.officers[progress.officer_id]

    options: list[DecisionOption] = []
    for action in officers.CORRUPTION_ACTIONS:
        if action in progress.actions_taken:
            continue
        options.extend(_corruption_action_candidates(state, officer, action))

    can_pass = not options and bool(progress.actions_taken)
    return PendingDecision(
        decision_id=decision_id,
        player_id=progress.player_id,
        decision_type="corruption_action",
        prompt_key="decision.corruption_action.prompt",
        options=tuple(options),
        min_selections=0 if can_pass else 1,
        max_selections=0 if can_pass else 1,
        can_pass=can_pass,
    )


def _corruption_action_candidates(
    state: GameState, officer: OfficerState, action: str
) -> list[DecisionOption]:
    options: list[DecisionOption] = []

    if action == "move":
        if officer.officer_type == OfficerType.COP:
            hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
            for dest_id in hood.adjacent_hood_ids:
                options.append(_corruption_option(f"corr_move_{dest_id}", "move", dest_id))
        else:
            spot = state.board.spots[officer.spot_id]  # type: ignore[index]
            for dest_spot_id in spot.adjacent_spot_ids:
                options.append(
                    _corruption_option(f"corr_move_{dest_spot_id}", "move", dest_spot_id)
                )

    elif action == "arrest":
        if not jail.has_free_rat_slot(state):
            return options
        if officer.officer_type == OfficerType.COP:
            hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
            for pawn_id in hood.criminal_pawn_ids:
                options.append(_corruption_option(f"corr_arrest_{pawn_id}", "arrest", pawn_id))
        else:
            spot = state.board.spots[officer.spot_id]  # type: ignore[index]
            if officers.has_arrestable_link(state, spot.contact_id):
                options.append(_corruption_option("corr_arrest_fed", "arrest", None))

    else:  # confiscate
        if not jail.has_free_confiscation_slot(state):
            return options
        if officer.officer_type == OfficerType.COP:
            hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
            if hood.dope_stack:
                options.append(_corruption_option("corr_confiscate", "confiscate", None))
        else:
            spot = state.board.spots[officer.spot_id]  # type: ignore[index]
            if spot.sold_dope_tokens:
                options.append(_corruption_option("corr_confiscate", "confiscate", None))

    return options


def _corruption_option(option_id: str, action: str, target_id: str | None) -> DecisionOption:
    return DecisionOption(
        option_id=option_id,
        label_key=f"decision.corruption_action.{action}",
        payload={"action": action, "target_id": target_id},
    )


# --- Rissa/Brawl sub-decisions (WAITING_FOR_BRAWL_*) -----------------------


def _brawl_card_decision(
    state: GameState, player_id: PlayerId, decision_id: DecisionId
) -> PendingDecision:
    """§D1 declare step: the current declarer may play one hand card
    face-down (any card — there's no rule requiring it to carry a Gun)
    or pass. `player_id` is already known to equal `state.current_player_id`
    (get_legal_decision's own entry check), which rules/brawl.py always
    keeps pointed at whichever participant is up next."""
    player = find_player(state, player_id)
    options = tuple(
        DecisionOption(
            option_id=f"brawl_card_{card_id}",
            label_key="decision.play_brawl_card.option",
            payload={"card_id": card_id},
        )
        for card_id in player.hand_card_ids
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="play_brawl_card",
        prompt_key="decision.play_brawl_card.prompt",
        options=options,
        min_selections=0,
        max_selections=1,
        can_pass=True,
    )


def _brawl_assignment_decision(
    state: GameState, player_id: PlayerId, decision_id: DecisionId
) -> PendingDecision:
    progress = state.pending_brawl
    assert progress is not None
    options = tuple(
        DecisionOption(
            option_id=f"brawl_target_{target_id}",
            label_key="decision.assign_brawl_guns.option",
            payload={"target_player_id": target_id},
        )
        for target_id in progress.participants
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="assign_brawl_guns",
        prompt_key="decision.assign_brawl_guns.prompt",
        options=options,
        min_selections=1,
        max_selections=1,
        can_pass=False,
    )


def _brawl_reward_decision(
    state: GameState, player_id: PlayerId, decision_id: DecisionId
) -> PendingDecision:
    progress = state.pending_brawl
    assert progress is not None

    if progress.reward_loser_index < len(progress.loser_ids):
        return _brawl_loser_reward_decision(state, progress, player_id, decision_id)
    if not progress.link_evolution_done:
        return _brawl_link_evolution_decision(state, progress, player_id, decision_id)
    return _brawl_relocation_decision(state, progress, player_id, decision_id)


def _brawl_loser_reward_decision(state, progress, player_id, decision_id) -> PendingDecision:
    loser_id = progress.loser_ids[progress.reward_loser_index]
    loser = find_player(state, loser_id)
    options = [
        DecisionOption(
            option_id="brawl_reward_money",
            label_key="decision.choose_brawl_loser_reward.money",
            payload={"loser_player_id": loser_id, "reward_type": "money"},
        )
    ]
    if loser.hand_card_ids:
        options.append(
            DecisionOption(
                option_id="brawl_reward_card",
                label_key="decision.choose_brawl_loser_reward.card",
                payload={"loser_player_id": loser_id, "reward_type": "card"},
            )
        )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="choose_brawl_loser_reward",
        prompt_key="decision.choose_brawl_loser_reward.prompt",
        options=tuple(options),
        min_selections=1,
        max_selections=1,
        can_pass=False,
    )


def _brawl_link_evolution_decision(state, progress, player_id, decision_id) -> PendingDecision:
    hood = state.board.hoods[progress.hood_id]
    options = tuple(
        DecisionOption(
            option_id=f"brawl_link_{pawn_id}",
            label_key="decision.choose_brawl_link_evolution.option",
            payload={"pawn_id": pawn_id},
        )
        for pawn_id in hood.criminal_pawn_ids
        if state.pawns[pawn_id].owner_player_id == player_id
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="choose_brawl_link_evolution",
        prompt_key="decision.choose_brawl_link_evolution.prompt",
        options=options,
        min_selections=0,
        max_selections=1,
        can_pass=True,
    )


def _brawl_relocation_decision(state, progress, player_id, decision_id) -> PendingDecision:
    options = tuple(
        DecisionOption(
            option_id=f"brawl_dest_{hood_id}",
            label_key="decision.choose_brawl_relocation_destination.option",
            payload={"hood_id": hood_id},
        )
        for hood_id, hood in state.board.hoods.items()
        if not hood.revealed
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="choose_brawl_relocation_destination",
        prompt_key="decision.choose_brawl_relocation_destination.prompt",
        options=options,
        min_selections=1 if options else 0,
        max_selections=1 if options else 0,
        can_pass=not options,
    )


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

    if decision.decision_type == "spend_link_for_extra_action":
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return SpendLinkForExtraAction(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            pawn_id=selected[0].payload["pawn_id"],
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

    if decision.decision_type == ActionType.CORRUPT_OFFICER.value:
        return CorruptOfficer(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            corruptions=tuple((o.payload["pawn_id"], o.payload["officer_id"]) for o in selected),
        )

    if decision.decision_type == "corruption_action":
        if not selected:
            return ChooseCorruptionAction(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
                action="skip",
            )
        return ChooseCorruptionAction(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            action=selected[0].payload["action"],
            target_id=selected[0].payload["target_id"],
        )

    if decision.decision_type == ActionType.BUY_OFFICER.value:
        return BuyOfficer(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            purchases=tuple(
                (o.payload["pawn_id"], o.payload["officer_id"], o.payload["destination"])
                for o in selected
            ),
        )

    if decision.decision_type == "hand_discard":
        return DiscardCards(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_ids=tuple(o.payload["card_id"] for o in selected),
        )

    if decision.decision_type == "play_brawl_card":
        return PlayBrawlCard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=selected[0].payload["card_id"] if selected else None,
        )

    if decision.decision_type == "assign_brawl_guns":
        return AssignBrawlGuns(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            target_player_id=selected[0].payload["target_player_id"],
        )

    if decision.decision_type == "choose_brawl_loser_reward":
        return ChooseBrawlLoserReward(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            loser_player_id=selected[0].payload["loser_player_id"],
            reward_type=selected[0].payload["reward_type"],
        )

    if decision.decision_type == "choose_brawl_link_evolution":
        return ChooseBrawlLinkEvolution(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            pawn_id=selected[0].payload["pawn_id"] if selected else None,
        )

    if decision.decision_type == "choose_brawl_relocation_destination":
        return ChooseBrawlRelocationDestination(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            hood_id=selected[0].payload["hood_id"] if selected else None,
        )

    raise ValueError(f"Unknown decision_type '{decision.decision_type}'")
