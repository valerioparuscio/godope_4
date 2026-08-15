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
    ChooseJobReward,
    ChooseRaidFirstPlayer,
    Command,
    CorruptOfficer,
    DiscardCards,
    EvolveSaleLink,
    LaunchPoker,
    MoveCriminal,
    PassOptionalStep,
    PlaceCriminal,
    PlacePokerBet,
    PlayBrawlCard,
    PlayMarketingCard,
    PlayPokerCard,
    SellDope,
    SpendLinkForExtraAction,
    StainReputationForMoney,
)
from dope_engine.domain.content import JobDefinition
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
    CardId,
    ContactId,
    DecisionId,
    HoodId,
    JobId,
    OfficerId,
    PawnId,
    PlayerId,
    SpotId,
)
from dope_engine.domain.state import GameState, PlayerState, find_player
from dope_engine.rules import jail, officers, prices, skills
from dope_engine.rules.prices import PriceTracks


def get_legal_decision(
    state: GameState,
    player_id: PlayerId,
    price_tracks: PriceTracks,
    link_extra_action_types: dict[ContactId, tuple[str, ...]],
    card_contact_by_id: dict[CardId, ContactId] | None = None,
    action_type_by_card_id: dict[CardId, ActionType | None] | None = None,
    job_by_id: dict[JobId, JobDefinition] | None = None,
    stonk_count_by_card_id: dict[CardId, int] | None = None,
) -> PendingDecision | None:
    if state.current_player_id != player_id:
        return None
    if state.phase not in (GamePhase.TIP_OFF, GamePhase.ACTION_PHASE, GamePhase.POKER_PHASE):
        return None

    decision_id = DecisionId(f"decision_{state.revision:04d}")
    player = find_player(state, player_id)

    if state.active_step == ActiveStep.WAITING_FOR_RAID_RESOLUTION:
        return _choose_raid_first_player_decision(state, player_id, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER:
        return _stain_reputation_for_money_decision(state, player_id, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_JOB_REWARD:
        assert job_by_id is not None
        return _job_reward_decision(state, player, decision_id, job_by_id)

    if state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE:
        assert stonk_count_by_card_id is not None
        return _marketing_decision(
            state, player, decision_id, stonk_count_by_card_id, price_tracks
        )

    if state.active_step == ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE:
        return _sale_link_evolution_decision(player, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_POKER_LAUNCH:
        assert card_contact_by_id is not None
        assert action_type_by_card_id is not None
        return _launch_poker_decision(
            state, player, decision_id, card_contact_by_id, action_type_by_card_id
        )

    if state.active_step == ActiveStep.WAITING_FOR_POKER_BETS:
        assert card_contact_by_id is not None
        return _place_poker_bet_decision(state, player_id, decision_id, card_contact_by_id)

    if state.active_step == ActiveStep.WAITING_FOR_POKER_CARD:
        assert card_contact_by_id is not None
        return _play_poker_card_decision(state, player, decision_id, card_contact_by_id)

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
            candidate_action_types = tuple(
                action_type
                for action_type in _ALL_ACTION_TYPES
                if action_type not in player.action_types_used_this_turn
            )
            return _choose_action_type_decision(
                state, player, decision_id, price_tracks, candidate_action_types
            )
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
) -> tuple[tuple[DecisionOption, ...], int] | None:
    """Returns `(options, max_selectable)` where `1 <= max_selectable <=
    grit_value`, or `None` if not even a single target is achievable.
    Confirmed by the game designer (2026-08-02): a package never has to
    use its full Grit value — a player may commit to fewer targets than
    `grit_value` (down to 1) whenever the full amount isn't affordable or
    achievable, rather than that action_type simply not being offered at
    all. `max_selectable` is the largest count actually usable; the
    caller (`_action_targets_decision`) exposes `min_selections=1,
    max_selections=max_selectable`."""
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


def _max_affordable_prefix_count(sorted_costs: list[int], money: int, cap: int) -> int:
    """The largest N (<= `cap`) such that the N cheapest costs in
    `sorted_costs` (already sorted ascending) sum to at most `money` —
    shared by `_buy_dope_options`/`_corrupt_officer_options`, whose
    per-candidate costs vary, unlike the flat per-unit costs of Place/Buy
    Officer."""
    count = 0
    total = 0
    for cost in sorted_costs[:cap]:
        if total + cost > money:
            break
        total += cost
        count += 1
    return count


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
        if _options_for_action_type(
            action_type,
            state,
            player,
            skills.effective_action_count(state, player, action_type, grit_value),
            price_tracks,
        )
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
    grit_value = skills.effective_action_count(state, player, action_type, grit_value)

    result = _options_for_action_type(action_type, state, player, grit_value, price_tracks)

    # §D2 (confirmed 2026-08-01): a Poker match can now be launched
    # between ChooseActionType and this decision, and the launch can
    # itself send one of this player's own base pawns to the Den as a
    # Gambler — which can starve the very action_type just committed to
    # (e.g. PLACE_CRIMINAL's own grit_value no longer has enough IN_BASE
    # pawns left, not even 1). `_options_for_action_type` returning
    # `None` here is always this "the round's commitment became
    # unfulfillable mid-flight" dead end, not a normal partial shortage
    # (confirmed 2026-08-02: a package may use *fewer* than `grit_value`
    # targets, down to 1 — see that function's own docstring — so `None`
    # only ever means zero targets are achievable at all): must remain
    # declinable via PassOptionalStep, exactly like
    # `_choose_action_type_decision` already tolerates zero qualifying
    # action types.
    if result is None:
        return PendingDecision(
            decision_id=decision_id,
            player_id=player.player_id,
            decision_type=action_type.value,
            prompt_key=f"decision.{action_type.value}.prompt",
            options=(),
            min_selections=0,
            max_selections=0,
            can_pass=True,
        )

    options, max_selectable = result
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type=action_type.value,
        prompt_key=f"decision.{action_type.value}.prompt",
        options=options,
        min_selections=1,
        max_selections=max_selectable,
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
            _options_for_action_type(
                action_type,
                state,
                player,
                skills.effective_action_count(state, player, action_type, pawn.link_level),
                price_tracks,
            )
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
# Each returns `None` if not even 1 target is achievable (so the
# action_type must not be offered at all), otherwise `(options,
# max_selectable)` — confirmed 2026-08-02: a package may commit to
# *fewer* than `grit_value` targets, so `max_selectable` (1..grit_value)
# is the real cap, not `grit_value` itself.


def _place_criminal_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[tuple[DecisionOption, ...], int] | None:
    cost_each = skills.effective_cost(
        state, player, ActionType.PLACE_CRIMINAL, state.configuration["costs"]["place_criminal"]
    )
    affordable = grit_value if cost_each == 0 else min(grit_value, player.money // cost_each)

    available_pawns = sum(
        1 for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    max_selectable = min(grit_value, affordable, available_pawns)
    if max_selectable < 1:
        return None

    # Placement must never itself bring a Hood to its Rissa-trigger count
    # (economy.py's `_handle_place_criminal` docstring/comment); only
    # Movement can reach that count, which is exactly what triggers the
    # Rissa (not yet implemented — Milestone 4).
    max_via_placement = state.configuration["brawl_trigger_criminal_count"] - 1
    options: list[DecisionOption] = []
    for hood_id, hood in state.board.hoods.items():
        remaining = max_via_placement - len(hood.criminal_pawn_ids)
        for i in range(max(0, min(remaining, max_selectable))):
            options.append(
                DecisionOption(
                    option_id=f"place_{hood_id}_{i}",
                    label_key="decision.place_criminal.option",
                    payload={"hood_id": hood_id},
                )
            )
    if not options:
        return None
    return tuple(options), max_selectable


def _move_criminal_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[tuple[DecisionOption, ...], int] | None:
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

    max_selectable = min(grit_value, len(distinct_pawns))
    if max_selectable < 1:
        return None
    return tuple(options), max_selectable


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
) -> tuple[tuple[DecisionOption, ...], int] | None:
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
        price = skills.effective_trade_price(
            state,
            player,
            ActionType.BUY_DOPE,
            prices.current_price(state.market, price_tracks, dope_type),
        )
        candidates.append((price, pawn_id, hood.hood_id, dope_type))
        remaining_stock[hood.hood_id] -= 1

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[0])
    max_selectable = _max_affordable_prefix_count(
        [c[0] for c in candidates], player.money, grit_value
    )
    if max_selectable < 1:
        return None

    options = tuple(
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
    return options, max_selectable


def _sell_dope_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[tuple[DecisionOption, ...], int] | None:
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
    max_selectable = min(grit_value, len(distinct_pawns))
    if max_selectable < 1:
        return None
    return tuple(options), max_selectable


def _corrupt_officer_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[tuple[DecisionOption, ...], int] | None:
    """Like `_buy_dope_options`: each candidate officer is budgeted to at
    most one (pawn, officer) pair (`used_officers`) so no subset of
    `grit_value` selections can target the same officer twice — the
    command bus also rejects that, but conservative generation keeps a
    uniformly-sampling bot safe by construction. Cheapest-`grit_value`
    affordability is checked the same way as `_buy_dope_options`, using
    the guaranteed *minimum* cost per officer (1 corruption action, $1) —
    same reasoning as officers.py's own upfront package check, since the
    real cost depends on however many actions get chosen later."""
    candidates: list[tuple[int, PawnId, OfficerId]] = []
    used_officers: set[OfficerId] = set()
    min_cost = officers.corruption_action_cost(state, player)

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
            else:
                if officer.location_type != OfficerLocationType.SPOT or officer.spot_id is None:
                    continue
                if not officers.can_corrupt_fed(state, pawn, officer.spot_id):
                    continue
            candidates.append((min_cost, pawn_id, officer_id))
            used_officers.add(officer_id)
            break

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[0])
    max_selectable = _max_affordable_prefix_count(
        [c[0] for c in candidates], player.money, grit_value
    )
    if max_selectable < 1:
        return None

    options = tuple(
        DecisionOption(
            option_id=f"corrupt_{pawn_id}_{officer_id}",
            label_key="decision.corrupt_officer.option",
            payload={"pawn_id": pawn_id, "officer_id": officer_id, "cost": cost},
        )
        for cost, pawn_id, officer_id in candidates
    )
    return options, max_selectable


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
) -> tuple[tuple[DecisionOption, ...], int] | None:
    """One option per qualifying (pawn, officer) pair, budgeted to at most
    one pawn per officer (`used_officers`) — same reasoning as
    `_corrupt_officer_options`. Cost is flat ($7 each), so affordability
    is just how many the player can afford at that flat rate, no
    cheapest-first sort needed.

    An officer bought with `destination=None` (already on the map, so
    the purchase brings it straight into the buyer's own Covo — see
    `_buy_officer_destination`) is capped by how much Covo capacity is
    actually left (`rules/officers.py::_buy_officer_into_base`'s own
    `base_officer_cap_reached` check): offering more such options than
    fit would let a same-size, jointly-selectable subset overflow the
    cap and have the whole package rejected. Buying one already in a
    Covo (a real hood/spot `destination`) has no such limit."""
    cost_each = skills.effective_cost(
        state, player, ActionType.BUY_OFFICER, state.configuration["costs"]["buy_officer"]
    )
    affordable = grit_value if cost_each == 0 else min(grit_value, player.money // cost_each)
    if affordable < 1:
        return None

    officer_cap = state.configuration["base_max_chips_per_category"]
    remaining_into_base = max(
        0, officer_cap - officers.officer_count_in_base(state, player.player_id)
    )

    options: list[DecisionOption] = []
    distinct_pawns: set[str] = set()
    used_officers: set[OfficerId] = set()
    into_base_offered = 0

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
            if destination is None:
                if into_base_offered >= remaining_into_base:
                    continue
                into_base_offered += 1
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

    max_selectable = min(affordable, len(distinct_pawns))
    if max_selectable < 1:
        return None
    return tuple(options), max_selectable


# --- corruption sub-decision (WAITING_FOR_CORRUPTION_ACTION) --------------


def _corruption_action_decision(state: GameState, decision_id: DecisionId) -> PendingDecision:
    progress = state.pending_corruption
    assert progress is not None
    officer = state.board.officers[progress.officer_id]
    player = find_player(state, progress.player_id)

    options: list[DecisionOption] = []
    # $1 per action (2026-08-15) — once the player can no longer afford
    # another action, no further real options are offered (forcing the
    # same "stop" as running out of legal targets would).
    if officers.corruption_action_cost(state, player) <= player.money:
        for action in officers.CORRUPTION_ACTIONS:
            if action in progress.actions_taken:
                continue
            options.extend(_corruption_action_candidates(state, officer, action))

    # The player may always stop voluntarily once at least 1 action has
    # been taken — up to 3 actions total, $1 each, entirely their choice
    # how many and which (decision 2026-08-15) — not just when no legal
    # action remains.
    can_pass = bool(progress.actions_taken)
    return PendingDecision(
        decision_id=decision_id,
        player_id=progress.player_id,
        decision_type="corruption_action",
        prompt_key="decision.corruption_action.prompt",
        options=tuple(options),
        min_selections=0 if can_pass else 1,
        max_selections=1 if options else 0,
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
        max_selections=1 if options else 0,
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


# --- Raids (WAITING_FOR_RAID_RESOLUTION / WAITING_FOR_STAIN_FOR_CASH_OFFER)


def _choose_raid_first_player_decision(
    state: GameState, player_id: PlayerId, decision_id: DecisionId
) -> PendingDecision:
    options = tuple(
        DecisionOption(
            option_id=f"raid_first_{pid}",
            label_key="decision.choose_raid_first_player.option",
            payload={"chosen_first_player_id": pid},
        )
        for pid in state.player_order
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="choose_raid_first_player",
        prompt_key="decision.choose_raid_first_player.prompt",
        options=options,
        min_selections=1,
        max_selections=1,
        can_pass=False,
    )


def _stain_reputation_for_money_decision(
    state: GameState, player_id: PlayerId, decision_id: DecisionId
) -> PendingDecision:
    options = (
        DecisionOption(
            option_id="stain_for_cash",
            label_key="decision.stain_reputation_for_money.option",
            payload={},
        ),
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="stain_reputation_for_money",
        prompt_key="decision.stain_reputation_for_money.prompt",
        options=options,
        min_selections=0,
        max_selections=1,
        can_pass=True,
    )


# --- Jobs (WAITING_FOR_JOB_REWARD) --------------------------------------


def _job_reward_decision(
    state: GameState,
    player: PlayerState,
    decision_id: DecisionId,
    job_by_id: dict[JobId, JobDefinition],
) -> PendingDecision:
    progress = state.pending_job_reward
    assert progress is not None and progress.queue
    entry = progress.queue[0]
    job_def = job_by_id[entry.job_id]
    two_contacts = len(job_def.contact_ids) > 1

    options = tuple(
        DecisionOption(
            option_id=f"job_reward_{entry.job_id}_{cell.column_index}_{contact_id}",
            label_key="decision.choose_job_reward.option",
            payload=(
                {"column_index": cell.column_index, "contact_id": contact_id}
                if two_contacts
                else {"column_index": cell.column_index}
            ),
        )
        for cell in state.jobs.board
        if cell.job_id == entry.job_id and cell.player_id is None
        for contact_id in (job_def.contact_ids if two_contacts else (None,))
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="choose_job_reward",
        prompt_key="decision.choose_job_reward.prompt",
        options=options,
        min_selections=1,
        max_selections=1,
        can_pass=False,
    )


# --- Marketing (WAITING_FOR_CARD_USAGE, §D3) ----------------------------


def _marketing_decision(
    state: GameState,
    player: PlayerState,
    decision_id: DecisionId,
    stonk_count_by_card_id: dict[CardId, int],
    price_tracks: PriceTracks,
) -> PendingDecision:
    """§D3 (corrected 2026-08-02): offered either right after
    `ChooseActionType` ("before" the whole action —
    `player.marketing_offer_is_pre`, any Dope type, since no package
    exists yet) or at the tail of `BuyDope`/`SellDope` ("after",
    restricted to `player.marketing_eligible_dope_types` — the Dope
    types the completed package actually handled). Either entry point
    only offers this step when the player holds at least one card with
    Stonk symbols, so `card_id` below is always found. PROVISIONAL
    (RULES_PENDING.md): with more than one eligible card, only the one
    with the most Stonks is offered — no separate "which card"
    sub-step. Each Stonk is one indivisible (dope_type, delta)
    allocation, duplicated `stonk_count` times per distinct combination
    so a player can freely stack several Stonks on the same good, same
    as `_place_criminal_options`'s own duplicate-until-cap pattern."""
    card_id = max(
        (cid for cid in player.hand_card_ids if stonk_count_by_card_id.get(cid, 0) > 0),
        key=lambda cid: stonk_count_by_card_id[cid],
    )
    stonk_count = stonk_count_by_card_id[card_id]
    dope_types = (
        sorted(price_tracks, key=lambda dt: dt.value)
        if player.marketing_offer_is_pre
        else sorted(player.marketing_eligible_dope_types, key=lambda dt: dt.value)
    )

    options = [
        DecisionOption(
            option_id=f"mkt_{dope_type.value}_{'up' if delta == 1 else 'down'}_{i}",
            label_key="decision.play_marketing_card.option",
            payload={"card_id": card_id, "dope_type": dope_type.value, "delta": delta},
        )
        for dope_type in dope_types
        for delta in (1, -1)
        for i in range(stonk_count)
    ]
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="play_marketing_card",
        prompt_key="decision.play_marketing_card.prompt",
        options=tuple(options),
        min_selections=0,
        max_selections=stonk_count,
        can_pass=True,
    )


# --- Sale Link evolution (WAITING_FOR_LINK_EVOLUTION_CHOICE, §A5/§C4) ----


def _sale_link_evolution_decision(player: PlayerState, decision_id: DecisionId) -> PendingDecision:
    """§A5 (corrected 2026-08-02): a single-unit sale's Link evolution
    is a real SI/NO choice, not a skippable optional step — both
    directions go through `EvolveSaleLink(evolve=...)`
    (`build_command_from_selection`), so `can_pass` is False and both
    options are always present."""
    options = (
        DecisionOption(
            option_id="evolve_sale_link_yes",
            label_key="decision.evolve_sale_link.yes",
            payload={"evolve": True},
        ),
        DecisionOption(
            option_id="evolve_sale_link_no",
            label_key="decision.evolve_sale_link.no",
            payload={"evolve": False},
        ),
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="evolve_sale_link",
        prompt_key="decision.evolve_sale_link.prompt",
        options=options,
        min_selections=1,
        max_selections=1,
        can_pass=False,
    )


# --- Poker (WAITING_FOR_POKER_LAUNCH/BETS/CARD) -----------------------


def _launch_poker_decision(
    state: GameState,
    player: PlayerState,
    decision_id: DecisionId,
    card_contact_by_id: dict[CardId, ContactId],
    action_type_by_card_id: dict[CardId, ActionType | None],
) -> PendingDecision:
    options = tuple(
        DecisionOption(
            option_id=f"launch_poker_{card_id}",
            label_key="decision.launch_poker.option",
            payload={"card_id": card_id},
        )
        for card_id in player.hand_card_ids
        if card_contact_by_id.get(card_id) == ContactId("preti")
        and action_type_by_card_id.get(card_id) == player.pending_action_type
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="launch_poker",
        prompt_key="decision.launch_poker.prompt",
        options=options,
        min_selections=0,
        max_selections=1 if options else 0,
        can_pass=True,
    )


def _den_gambler_count(state: GameState, player_id: PlayerId) -> int:
    return sum(
        1
        for pid in state.board.den_gambler_pawn_ids
        if state.pawns[pid].owner_player_id == player_id
    )


def _place_poker_bet_decision(
    state: GameState,
    player_id: PlayerId,
    decision_id: DecisionId,
    card_contact_by_id: dict[CardId, ContactId],
) -> PendingDecision:
    options = tuple(
        DecisionOption(
            option_id=f"poker_bet_{match.match_id}",
            label_key="decision.place_poker_bet.option",
            payload={"match_id": match.match_id},
        )
        for match in state.poker.matches_this_turn
    )
    player = find_player(state, player_id)
    # A bettor reveals one non-Preti card per match staked on (a Preti
    # "Gamble" card has no `poker_symbols` of its own); capping here
    # avoids offering a bet the player can't actually follow through on.
    revealable_card_count = sum(
        1
        for card_id in player.hand_card_ids
        if card_contact_by_id.get(card_id) != ContactId("preti")
    )
    max_selections = min(
        _den_gambler_count(state, player_id), len(options), revealable_card_count
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="place_poker_bet",
        prompt_key="decision.place_poker_bet.prompt",
        options=options,
        min_selections=0,
        max_selections=max_selections,
        can_pass=True,
    )


def _play_poker_card_decision(
    state: GameState,
    player: PlayerState,
    decision_id: DecisionId,
    card_contact_by_id: dict[CardId, ContactId],
) -> PendingDecision:
    match = state.poker.matches_this_turn[state.poker.resolving_match_index]
    options = tuple(
        DecisionOption(
            option_id=f"poker_card_{card_id}",
            label_key="decision.play_poker_card.option",
            payload={"card_id": card_id, "match_id": match.match_id},
        )
        for card_id in player.hand_card_ids
        # A Preti "Gamble" card has no `poker_symbols` (only the launch
        # card's own `banco_symbols` matter) — revealing one would
        # contribute 0 symbols instead of 2, breaking the 5-symbol hand.
        if card_contact_by_id.get(card_id) != ContactId("preti")
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="play_poker_card",
        prompt_key="decision.play_poker_card.prompt",
        options=options,
        min_selections=1,
        max_selections=1,
        can_pass=False,
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

    # §D2 (confirmed 2026-08-01): a Poker match launched between
    # ChooseActionType and this decision can starve the just-committed
    # action_type of the resources (e.g. base pawns) its grit_value
    # needs — `_action_targets_decision` then reports zero options and
    # `can_pass=True` as the only way out. Each of the 6 action-type
    # decisions below must fall back to declining, same as
    # "choose_action_type"/"spend_link_for_extra_action" already do.
    if decision.decision_type == ActionType.PLACE_CRIMINAL.value:
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return PlaceCriminal(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            hood_ids=tuple(o.payload["hood_id"] for o in selected),
        )

    if decision.decision_type == ActionType.MOVE_CRIMINAL.value:
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
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
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return BuyDope(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            pawn_ids=tuple(o.payload["pawn_id"] for o in selected),
        )

    if decision.decision_type == ActionType.SELL_DOPE.value:
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return SellDope(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            sales=tuple((o.payload["pawn_id"], DopeType(o.payload["dope_type"])) for o in selected),
        )

    if decision.decision_type == ActionType.CORRUPT_OFFICER.value:
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
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
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
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

    if decision.decision_type == "choose_job_reward":
        return ChooseJobReward(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            column_index=selected[0].payload["column_index"],
            contact_id=selected[0].payload.get("contact_id"),
        )

    if decision.decision_type == "play_marketing_card":
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return PlayMarketingCard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=selected[0].payload["card_id"],
            allocations=tuple(
                (DopeType(o.payload["dope_type"]), o.payload["delta"]) for o in selected
            ),
        )

    if decision.decision_type == "evolve_sale_link":
        return EvolveSaleLink(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            evolve=selected[0].payload["evolve"],
        )

    if decision.decision_type == "choose_raid_first_player":
        return ChooseRaidFirstPlayer(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            chosen_first_player_id=selected[0].payload["chosen_first_player_id"],
        )

    if decision.decision_type == "stain_reputation_for_money":
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return StainReputationForMoney(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
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

    if decision.decision_type == "launch_poker":
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return LaunchPoker(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=selected[0].payload["card_id"],
        )

    if decision.decision_type == "place_poker_bet":
        return PlacePokerBet(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            match_ids=tuple(o.payload["match_id"] for o in selected),
        )

    if decision.decision_type == "play_poker_card":
        return PlayPokerCard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            match_id=selected[0].payload["match_id"],
            card_id=selected[0].payload["card_id"],
        )

    raise ValueError(f"Unknown decision_type '{decision.decision_type}'")
