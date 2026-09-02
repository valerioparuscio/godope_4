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
    ChooseJobBonusAlternative,
    ChooseJobReward,
    ChooseMarketingCard,
    ChoosePokerSymbols,
    ChooseRaidFirstPlayer,
    ChooseReinforceDiscard,
    ChooseSkillToDiscard,
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
    PlayCustomerCardBoost,
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
    JobBonusType,
    OfficerType,
    PawnRole,
    PokerSymbolColor,
)
from dope_engine.domain.ids import (
    DEN_ID,
    JAIL_ID,
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
from dope_engine.domain.state import GameState, PlayerState, find_player, officer_count_in_base
from dope_engine.rules import customer_cards, jail, jobs, officers, prices, skills
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
    card_effect_by_id: dict[CardId, dict | None] | None = None,
) -> PendingDecision | None:
    if state.current_player_id != player_id:
        return None

    decision_id = DecisionId(f"decision_{state.revision:04d}")
    player = find_player(state, player_id)

    # WAITING_FOR_JOB_REWARD can be entered from *any* phase, not just the
    # three normal ones below — a Job completion is checked after every
    # command (CLAUDE.md §11.12), including the last turn's own Poker/Raid
    # resolution, which leaves `state.phase` at SHOWDOWN_PHASE by the time
    # `rules/jobs.py`'s post-success hook runs (game designer, 2026-08-17:
    # a Job only completed by that last-turn outcome must still be
    # claimable before the final score locks in — see `rules/turn_flow.py::
    # finalize_game_if_ready`). Checked before the phase guard below for
    # exactly this reason.
    if state.active_step == ActiveStep.WAITING_FOR_JOB_REWARD:
        assert job_by_id is not None
        return _job_reward_decision(state, player, decision_id, job_by_id)

    # Same "any phase" reasoning as WAITING_FOR_JOB_REWARD just above —
    # entered from inside that same reward-claim flow (game designer,
    # 2026-08-27: claiming a SKILL column at the 3-Skill cap).
    if state.active_step == ActiveStep.WAITING_FOR_SKILL_DISCARD_CHOICE:
        return _skill_discard_decision(state, player, decision_id)

    # Same "any phase" reasoning as WAITING_FOR_JOB_REWARD above — entered
    # from inside that same reward-claim flow (Job 8's own column 2
    # override, 2026-09-02).
    if state.active_step == ActiveStep.WAITING_FOR_JOB_BONUS_ALTERNATIVE_CHOICE:
        return _job_bonus_alternative_decision(player, decision_id)

    if state.phase not in (GamePhase.TIP_OFF, GamePhase.ACTION_PHASE, GamePhase.POKER_PHASE):
        return None

    if state.active_step == ActiveStep.WAITING_FOR_RAID_RESOLUTION:
        return _choose_raid_first_player_decision(state, player_id, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER:
        return _stain_reputation_for_money_decision(state, player_id, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE:
        assert stonk_count_by_card_id is not None
        return _marketing_decision(state, player, decision_id, stonk_count_by_card_id, price_tracks)

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

    if state.active_step == ActiveStep.WAITING_FOR_POKER_SYMBOL_CHOICE:
        return _choose_poker_symbols_decision(state, player_id, decision_id)

    if state.active_step == ActiveStep.WAITING_FOR_CARD_BOOST:
        assert card_effect_by_id is not None
        assert action_type_by_card_id is not None
        return _card_boost_decision(player, decision_id, card_effect_by_id, action_type_by_card_id)

    if state.active_step == ActiveStep.WAITING_FOR_REINFORCE_DISCARD:
        return _reinforce_discard_decision(player, decision_id)

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

    available_pawns = sum(1 for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    max_selectable = min(grit_value, affordable, available_pawns)
    if max_selectable < 1:
        return None

    # Placement must never itself bring a Hood to its Rissa-trigger count
    # (economy.py's `_handle_place_criminal` docstring/comment); only
    # Movement can reach that count, which is exactly what triggers the
    # Rissa (not yet implemented — Milestone 4).
    max_via_placement = state.configuration["brawl_trigger_criminal_count"] - 1
    options: list[DecisionOption] = []
    # Cards 043/045 ("un criminale puoi piazzarlo in prigione") and
    # 054/059 "BIG RAT" (same JAIL_ID target, plus an evasion-immunity
    # flag applied in rules/economy.py) — see
    # rules/economy.py::_handle_place_criminal's own JAIL_ID branch for
    # the matching validation side. No capacity cap (RULES_PENDING.md
    # #15: the Jail is never actually full), so up to `max_selectable`
    # duplicates, same shape as a Hood's own "up to remaining capacity"
    # duplicates just below.
    boost = player.active_card_boost
    if boost is not None and boost["type"] in ("place_to_jail", "place_to_jail_evasion_immune"):
        for i in range(max_selectable):
            options.append(
                DecisionOption(
                    option_id=f"place_jail_{i}",
                    label_key="decision.place_criminal.option",
                    payload={"hood_id": JAIL_ID},
                )
            )
    # Cards 048/055 "GO GAMBLE" (place_in_den, up to 2) and 042/057
    # "NO GAMBLE" (place_in_den_evict_enemy, up to 1, plus a best-effort
    # enemy-Gambler eviction applied automatically in
    # rules/economy.py::_handle_place_criminal — no separate option for
    # it here, same "secondary automatic effect" pattern as
    # self_arrest_after_action/arrest_extra_target). One option per
    # possible deck choice, mirroring `_move_criminal_options`'s own
    # DEN_ID offering.
    place_in_den_evict = boost is not None and boost["type"] == "place_in_den_evict_enemy"
    place_in_den = place_in_den_evict or (boost is not None and boost["type"] == "place_in_den")
    if place_in_den:
        max_den_placements = 1 if place_in_den_evict else 2
        remaining_den = state.configuration["den_capacity"] - len(state.board.den_gambler_pawn_ids)
        own_gamblers_in_den = sum(
            1
            for pid in state.board.den_gambler_pawn_ids
            if state.pawns[pid].owner_player_id == player.player_id
        )
        remaining_den_for_player = (
            state.configuration["den_capacity_per_player"] - own_gamblers_in_den
        )
        den_slots = min(max_den_placements, max_selectable, remaining_den, remaining_den_for_player)
        if den_slots > 0:
            contact_ids = list(state.decks.customer_decks_by_contact.keys())
            for i in range(den_slots):
                for contact_id in contact_ids:
                    options.append(
                        DecisionOption(
                            option_id=f"place_den_{i}_{contact_id}",
                            label_key="decision.place_criminal.option",
                            payload={
                                "hood_id": DEN_ID,
                                "deck_contact_id": contact_id,
                                # Several options here share the same real
                                # Den slot (one per deck choice) — a picker
                                # must dedup by this index, not by
                                # option_id, or it can request more Den
                                # placements than `den_slots` actually
                                # allows (bots/option_picking.py::
                                # pick_place_criminal_options).
                                "den_slot_index": i,
                            },
                        )
                    )
    # Card 044/051 "INVADE" ("piazzi uno in ogni quartiere dove sei
    # presente" — replaces the normal targeting entirely: exactly one
    # option per presence Hood, not the usual "up to remaining capacity"
    # duplicates just below, since the card grants one placement each,
    # not free choice of how many go where; `effective_action_count`
    # already turned `max_selectable` itself into the number of presence
    # Hoods, uncapped by Grit).
    invade = boost is not None and boost["type"] == "invade_own_hoods"
    for hood_id, hood in state.board.hoods.items():
        # An unrevealed Hood can only ever be reached by a Brawl loser's
        # relocation (game designer, 2026-08-16); it becomes a normal
        # placeable/movable Hood only once that reveals it
        # (rules/brawl.py sets hood.revealed = True there).
        if not hood.revealed:
            continue
        remaining = max_via_placement - len(hood.criminal_pawn_ids)
        if remaining <= 0:
            continue
        if invade:
            has_presence = any(
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
            if not has_presence:
                continue
            options.append(
                DecisionOption(
                    option_id=f"place_{hood_id}_0",
                    label_key="decision.place_criminal.option",
                    payload={"hood_id": hood_id},
                )
            )
            continue
        for i in range(min(remaining, max_selectable)):
            options.append(
                DecisionOption(
                    option_id=f"place_{hood_id}_{i}",
                    label_key="decision.place_criminal.option",
                    payload={"hood_id": hood_id},
                )
            )
    if not options:
        return None
    # Only revealed Hoods contribute options (above) — `max_selectable`
    # itself is computed from grit/money/available-pawns alone, none of
    # which account for how much placeable *capacity* actually exists
    # across just the revealed Hoods, so it can now legitimately exceed
    # the raw option count (game designer, 2026-08-16: unrevealed Hoods
    # dropped out of this pool entirely). Capped here the same way
    # `_move_criminal_options`/`_buy_dope_options` already cap theirs by
    # what was actually generated.
    max_selectable = min(max_selectable, len(options))
    return tuple(options), max_selectable


def _move_criminal_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[tuple[DecisionOption, ...], int] | None:
    """Every individually-legal (pawn, Hood-destination) pair is offered,
    checked against the real, unmodified board state — *not* a running
    budget shared across candidate pawns as options are generated.

    An earlier version of this function did budget Hood capacity across
    all candidates (so a same-size subset would always be jointly legal),
    but that meant a Criminal with an objectively free destination Hood
    could be silently excluded just because a *different* one of the
    player's own pawns, elsewhere on the board, was iterated first and
    claimed that Hood's last slot (game designer, 2026-08-16 bug reports:
    first with a single "Sposta", then again at Grit 3 into a Hood that
    already had 3 of 5 slots taken) — worse the more pawns/Grit are in
    play, i.e. worse exactly when the conservative budgeting was supposed
    to help most.

    This trades the *generator's own* jointly-legal-subset guarantee for
    a simpler one: any *individual* move is genuinely legal right now.
    A same-command batch that oversubscribes one Hood (e.g. the player
    picks 2 different pawns for the same Hood's only remaining slot)
    still gets caught — `process_move_queue` validates each queued move
    against the *live*, already-mutated state as it applies them
    sequentially, same as it always has, so an overcommitted package
    fails cleanly with a normal domain error instead of ever completing
    partially. `bots/random_legal.py`'s own `_pick_move_criminal_options`
    is what now keeps RandomLegalBot's uniform sampling from ever
    *submitting* such a batch in the first place (mirrors the budgeting
    this function used to do, just moved to where a decision about which
    pawn "wins" a scarce slot is actually being made).

    The Den's own capacity (global 6 + a 2-per-player cap) used to be
    budgeted across candidates the same conservative way — but that had
    the exact same bug the docstring above already fixed for ordinary
    Hoods: whichever pawn's `player.pawn_ids` position was iterated first
    claimed the Den's shared budget, silently hiding the Den as a
    destination for every pawn iterated after it even though real slots
    were still free (bug report, 2026-08-27: entering the Den worked for
    pawns in "manager" Hoods but not "artisti" ones, in the same package
    — purely an artifact of iteration order, not an actual Den capacity
    difference between Contacts). Now offered per-pawn like every other
    destination, gated only by the real (static) remaining counts; the
    bot-side budget moved to `bots/option_picking.py::
    pick_move_criminal_options`, mirroring Hood capacity there."""
    options: list[DecisionOption] = []
    distinct_pawns: set[str] = set()
    hood_capacity: dict[HoodId, int] = {
        hood_id: hood.capacity - len(hood.criminal_pawn_ids)
        for hood_id, hood in state.board.hoods.items()
    }
    remaining_den = state.configuration["den_capacity"] - len(state.board.den_gambler_pawn_ids)
    own_gamblers_in_den = sum(
        1
        for pid in state.board.den_gambler_pawn_ids
        if state.pawns[pid].owner_player_id == player.player_id
    )
    remaining_den_for_player = state.configuration["den_capacity_per_player"] - own_gamblers_in_den
    contact_ids = list(state.decks.customer_decks_by_contact.keys())
    # Card 033 ("muovi un criminale da un quartiere qualunque in
    # prigione") — see rules/movement.py::move_one_pawn's own JAIL_ID
    # branch for the matching validation side.
    boost = player.active_card_boost
    move_to_jail = boost is not None and boost["type"] == "move_to_jail"
    # Cards 032/036 "PLAY!!" ("se vai nel Den, peschi 2 carte a scelta",
    # game designer, 2026-08-31: confirmed 2 independent deck choices):
    # every (deck, extra_deck) pair is offered per pawn — combinatorial,
    # but `pick_move_criminal_options`'s existing per-*pawn* dedup (a
    # Criminal only ever contributes one selected option) already keeps a
    # picked package jointly legal without needing a further "which pair"
    # budget, unlike `PlaceCriminal`'s own Den offering (no pawn identity
    # there to dedup by, hence that one's `den_slot_index`).
    double_den_draw = boost is not None and boost["type"] == "double_den_draw"
    # Cards 034/035 "REPOSITION": a Link has no single "current Hood" —
    # every Hood adjacent to *either* of its own Contact's 2 Hoods,
    # belonging to a *different* Contact, is offered as a destination
    # (see rules/movement.py::move_one_pawn's own LINK branch for the
    # matching validation side, which re-derives the same adjacency set).
    link_reposition = boost is not None and boost["type"] == "link_reposition"

    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn_id in player.moved_pawn_ids_this_turn:
            continue

        if pawn.role == PawnRole.CRIMINAL:
            hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
            for dest_id in hood.adjacent_hood_ids:
                # An unrevealed Hood is only ever reached via a Brawl
                # loser's relocation, never a normal move (game designer,
                # 2026-08-16) — it becomes movable/placeable only once
                # that reveals it (rules/brawl.py sets hood.revealed).
                if not state.board.hoods[dest_id].revealed:
                    continue
                if hood_capacity.get(dest_id, 0) > 0:
                    options.append(_move_option(pawn_id, dest_id, None))
                    distinct_pawns.add(pawn_id)
            if remaining_den > 0 and remaining_den_for_player > 0:
                if double_den_draw:
                    for contact_id in contact_ids:
                        for extra_contact_id in contact_ids:
                            options.append(
                                _move_option(pawn_id, DEN_ID, contact_id, extra_contact_id)
                            )
                else:
                    for contact_id in contact_ids:
                        options.append(_move_option(pawn_id, DEN_ID, contact_id))
                distinct_pawns.add(pawn_id)
            if move_to_jail:
                options.append(_move_option(pawn_id, JAIL_ID, None))
                distinct_pawns.add(pawn_id)

        elif pawn.role == PawnRole.GAMBLER:
            for dest_id, dest_hood in state.board.hoods.items():
                if not dest_hood.revealed:
                    continue
                if hood_capacity.get(dest_id, 0) > 0:
                    options.append(_move_option(pawn_id, dest_id, None))
                    distinct_pawns.add(pawn_id)

        elif pawn.role == PawnRole.LINK and link_reposition:
            own_contact_hood_ids = [
                hid for hid, hood in state.board.hoods.items() if hood.contact_id == pawn.contact_id
            ]
            # RULES_PENDING.md #24 (engine determinism): a `set` of
            # HoodId strings iterates in an order that depends on
            # PYTHONHASHSEED, which is randomized per-process by default
            # — the same seed/commands could then offer these options in
            # a different order across two separate process runs, and
            # `bots/option_picking.py::pick_move_criminal_options`'s own
            # shuffle+walk over a differently-ordered input list picks a
            # different pawn/destination even with the same RNG seed.
            # `seen` below is only ever membership-tested (`in`), never
            # iterated, so it staying a set is fine — only the emitted
            # *order* of destinations must be deterministic, built here
            # from `own_contact_hood_ids`' own stable list order.
            seen_dest_ids: set[HoodId] = set()
            for hid in own_contact_hood_ids:
                for adj_id in state.board.hoods[hid].adjacent_hood_ids:
                    if adj_id in seen_dest_ids:
                        continue
                    seen_dest_ids.add(adj_id)
                    if state.board.hoods[adj_id].contact_id == pawn.contact_id:
                        continue
                    options.append(_move_option(pawn_id, adj_id, None))
                    distinct_pawns.add(pawn_id)

    max_selectable = min(grit_value, len(distinct_pawns))
    if max_selectable < 1:
        return None
    return tuple(options), max_selectable


def _move_option(
    pawn_id: str,
    destination: HoodId,
    deck_contact_id: ContactId | None,
    extra_deck_contact_id: ContactId | None = None,
) -> DecisionOption:
    suffix = f"_{deck_contact_id}" if deck_contact_id else ""
    if extra_deck_contact_id:
        suffix += f"_{extra_deck_contact_id}"
    return DecisionOption(
        option_id=f"move_{pawn_id}_{destination}{suffix}",
        label_key="decision.move_criminal.option",
        payload={
            "pawn_id": pawn_id,
            "destination_hood_id": destination,
            "deck_contact_id": deck_contact_id,
            "extra_deck_contact_id": extra_deck_contact_id,
        },
    )


def _buy_dope_options(
    state: GameState, player: PlayerState, grit_value: int, price_tracks: PriceTracks
) -> tuple[tuple[DecisionOption, ...], int] | None:
    """Like `_move_criminal_options` (2026-08-16 fix), every individually-
    legal (pawn, Hood) pair is offered, checked against the real,
    unmodified board state — *not* a running stock budget shared across
    candidate pawns as options are generated.

    An earlier version of this function budgeted each Hood's current
    `dope_stack` length across all candidates as they were generated (on
    the theory that buying the last unit in a Hood restocks it *and*
    spawns a blocking Cop, so a package can never legally buy more than
    one Hood's *starting* stock length from it). That reasoning is right
    about the final applied package, but wrong as a *generation-time*
    filter: whichever pawn happened to be iterated first in
    `player.pawn_ids` silently claimed a contested Hood's stock, even
    when a *different* assignment of pawns to Hoods would let strictly
    more of the player's own pawns act (game designer, 2026-08-16 bug
    report: Grit 3 "Acquista"/"Corrompi" only ever offered 1 option) —
    worse the more pawns with overlapping reach are in play, e.g. a Link
    (presence at *both* of its Contact's Hoods, 2026-08-15) iterated
    before a plain Criminal that can only reach one of those same two
    Hoods.

    A same-command batch that oversubscribes one Hood's real stock still
    gets caught cleanly: `_handle_buy_dope` applies each queued purchase
    against the *live*, already-mutated state in order, so a second
    purchase from a Hood the first purchase just emptied fails with its
    normal `hood_has_no_dope`/`hood_blocked_by_cop` domain error (a
    restock also spawns a Cop) instead of ever completing partially.
    `bots/random_legal.py::_pick_buy_dope_options` budgets each Hood's
    real stock the same way this function used to, just moved to where a
    decision about which pawn "wins" a scarce Hood is actually made.

    A Link counts as presence in *both* of its Contact's Hoods (game
    designer, 2026-08-15) — since each Hood has its own independent
    stock/price (unlike Sell Dope, whose Spots are Contact-scoped and so
    never need this), a Link with 2 legal candidates gets one option per
    Hood (`buy_{pawn_id}_{hood_id}`, not just `buy_{pawn_id}`, to keep
    the two distinct); the frontend disambiguates them exactly like Sell
    Dope's own pawn-with-2-legal-Spots case. Same tolerance as every
    other budgeted-candidate generator in this module: `max_selectable`
    counts raw candidates, not distinct pawns, so a same-Link pair (or a
    Hood whose real stock is smaller than the number of pawns reaching
    it) can inflate it beyond what's jointly achievable (the command
    handler's own duplicate-pawn/live-state checks are the real
    backstop) — bots already pick conservatively for this exact reason."""
    # Card 008 boost ("prima di acquistare ricarica fino a 3 merci nel
    # quartiere", rules/economy.py::_top_up_hood_for_boost): an empty
    # Hood it would top up first is offered here as if already stocked —
    # the top-up itself never spawns a Cop (unlike a normal empty-Hood
    # restock), so a Cop-blocked Hood stays excluded either way.
    boost = player.active_card_boost
    bypass_empty_stock = boost is not None and boost["type"] == "pre_action_restock"
    # Card 017 ("acquista in un quartiere adiacente"): a Criminal can
    # also buy at a Hood *adjacent* to its own (board adjacency, any
    # Contact) — `_handle_buy_dope`'s own validation mirrors this bypass.
    buy_adjacent = boost is not None and boost["type"] == "adjacent_hood_presence"
    # Card 004 ("acquista da un altro quartiere dello stesso cliente"): a
    # Criminal can also buy at its own Hood's Contact's *other* Hood —
    # exactly the Contact-wide reach a Link already has for free
    # (`officers.has_presence_at_hood`'s own LINK branch), extended here
    # to a Criminal too. Different from card 017 above: same-Contact, not
    # board-adjacent (the two are usually not the same Hood pair at all).
    buy_same_contact = boost is not None and boost["type"] == "same_contact_hood_presence"

    candidates: list[tuple[int, PawnId, HoodId, DopeType]] = []
    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK):
            continue
        for hood_id, hood in state.board.hoods.items():
            has_presence = officers.has_presence_at_hood(state, pawn, hood_id)
            if not has_presence and pawn.role == PawnRole.CRIMINAL:
                own_hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
                if buy_adjacent:
                    has_presence = hood_id in own_hood.adjacent_hood_ids
                elif buy_same_contact:
                    has_presence = hood.contact_id == own_hood.contact_id
            if not has_presence:
                continue
            if hood.cop_ids:
                continue
            if not hood.dope_stack:
                if (
                    not bypass_empty_stock
                    or hood.dope_type is None
                    or state.market.supply_remaining_by_dope_type.get(hood.dope_type, 0) <= 0
                ):
                    continue
                dope_type = hood.dope_type
            else:
                dope_type = hood.dope_stack[-1]
            # §11.4/RULES_PENDING.md #26: the Covo's 3-per-type cap blocks
            # a purchase outright (rules/economy.py::_handle_buy_dope's own
            # `base_inventory_full` check) — excluded here too so a
            # (pawn, Hood) pair that's already individually illegal never
            # gets offered at all, same as the Cop-block/no-stock filters
            # just above (unlike money/Hood-stock, which stay unbudgeted
            # *across* candidates by design, this cap makes a single
            # candidate illegal entirely on its own).
            if player.base_inventory.dope_counts.get(dope_type, 0) >= 3:
                continue
            price = skills.effective_trade_price(
                state,
                player,
                ActionType.BUY_DOPE,
                prices.current_price(state.market, price_tracks, dope_type),
            )
            candidates.append((price, pawn_id, hood_id, dope_type))

    if not candidates:
        return None

    # Card 007 ("acquisti fino a 3 merci con un criminale"): each
    # candidate is duplicated `max_repeats` times so the same pawn can be
    # selected that many times in one package — same "one raw option per
    # repeatable unit" shape as Marketing's own Stonk-allocation options
    # (_marketing_decision). `_handle_buy_dope`'s own duplicate-pawn check
    # allows the matching number of repeats.
    if boost is not None and boost["type"] == "repeat_pawn_target":
        candidates = [c for c in candidates for _ in range(boost["max_repeats"])]

    candidates.sort(key=lambda c: c[0])
    max_selectable = _max_affordable_prefix_count(
        [c[0] for c in candidates], player.money, grit_value
    )
    if max_selectable < 1:
        return None

    options = tuple(
        DecisionOption(
            option_id=f"buy_{pawn_id}_{hood_id}_{i}",
            label_key="decision.buy_dope.option",
            payload={
                "pawn_id": pawn_id,
                "hood_id": hood_id,
                "dope_type": dope_type.value,
                "price": price,
            },
        )
        for i, (price, pawn_id, hood_id, dope_type) in enumerate(candidates)
    )
    return options, max_selectable


def _sell_dope_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[tuple[DecisionOption, ...], int] | None:
    """A pawn's enabling presence at a Spot (§11.5/§11.6: Criminal in the
    Spot's Contact's own Hood, *or* a Link of that Contact — game
    designer, 2026-08-15) is entirely Spot/Contact-scoped, never
    Hood-scoped: both of a Contact's Hoods share the same 2 Spots, so a
    Link's presence at 2 Hoods never adds candidates beyond what a
    Criminal in either one already has access to — no Hood-disambiguation
    step needed here the way `_buy_dope_options` needs one (its
    dope_type/price/stock are genuinely per-Hood, not per-Contact).

    Like `_buy_dope_options`/`_corrupt_officer_options` (2026-08-16 fix):
    every individually-legal (pawn, Spot, dope_type) triple is offered,
    checked against the real board/inventory state — *not* budgeted
    across candidates as they're generated. An earlier version budgeted
    both a Spot's remaining capacity *and* the player's own base
    inventory count per Dope type across all candidates in generation
    order, so whichever pawn happened to be iterated first could silently
    claim the only unit of a Dope type (or the only free Spot slot),
    hiding an *individually completely legal* sale for a different pawn
    entirely (game designer, 2026-08-17 bug report: a Criminal standing
    right at a Preti Spot, holding the right Dope, with the Spot free,
    still wasn't offered a sell option — reproduced with a second pawn
    elsewhere also eligible to sell the same Dope type, iterated first).

    The command bus still validates each queued sale against the *live*
    state as it applies them (`no_dope_to_sell`/`spot_full`), so an
    over-generous combination a human builds on the board fails cleanly
    instead of silently overselling. `bots/random_legal.py::
    _pick_sell_dope_options` budgets both the per-Dope-type inventory and
    per-Spot capacity while picking, the same way `_pick_buy_dope_options`
    budgets Hood stock — the decision about which pawn "wins" a scarce
    unit or Spot slot moved from the generator to the picker."""
    # Card 010/019 boost ("prima di vendere svuota il punto di vendita",
    # rules/economy.py::_pre_clear_spot_for_boost): a Spot it would clear
    # is offered here as if already cleared — Fed-blocked or capacity-full
    # are otherwise always the same state (hitting capacity always
    # auto-clears+spawns a Fed in the very same sale, see
    # `_handle_sell_dope`), so bypassing both together covers it.
    boost = player.active_card_boost
    bypass_fed_and_capacity = boost is not None and boost["type"] == "pre_action_clear_spot"
    # Card 012 ("vendi in un quartiere adiacente"): a Criminal's selling
    # reach extends to the Contact of a Hood adjacent to its own too, on
    # top of the normal `has_presence_at_spot` reach (its own Hood's
    # Contact) — mirrors cards 004/017's Buy-side "adjacent Hood" bypass,
    # translated to Sell's Contact-based (not Hood-based) targeting. Now
    # that `SellDope.spot_id_by_pawn` can disambiguate which Spot was
    # meant (RULES_PENDING.md #26), `build_command_from_selection` below
    # always fills it in from the option's own `spot_id`, whether or not
    # this boost is what made it necessary.
    sell_adjacent = boost is not None and boost["type"] == "adjacent_hood_presence"

    candidates: list[tuple[PawnId, SpotId, DopeType]] = []
    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        if pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK):
            continue
        for spot in state.board.spots.values():
            has_presence = officers.has_presence_at_spot(state, pawn, spot.spot_id)
            if not has_presence and sell_adjacent and pawn.role == PawnRole.CRIMINAL:
                own_hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
                has_presence = any(
                    state.board.hoods[adj_id].contact_id == spot.contact_id
                    for adj_id in own_hood.adjacent_hood_ids
                )
            if not has_presence:
                continue
            if not bypass_fed_and_capacity:
                if spot.fed_ids:
                    continue
                if spot.capacity - len(spot.sold_dope_tokens) <= 0:
                    continue
            dope_type = spot.accepted_dope_type
            if player.base_inventory.dope_counts.get(dope_type, 0) <= 0:
                continue
            candidates.append((pawn_id, spot.spot_id, dope_type))

    if not candidates:
        return None

    # Card 015 ("vendi fino a 3 merci con un criminale"): each candidate
    # is duplicated `max_repeats` times, same "one raw option per
    # repeatable unit" shape as card 007's own Buy-side counterpart
    # (`_buy_dope_options`) — `_handle_sell_dope`'s duplicate-pawn check
    # allows the matching number of repeats.
    repeat_pawns = boost is not None and boost["type"] == "repeat_pawn_target"
    if repeat_pawns and boost is not None:
        candidates = [c for c in candidates for _ in range(boost["max_repeats"])]

    options = tuple(
        DecisionOption(
            option_id=f"sell_{pawn_id}_{dope_type.value}_{spot_id}_{i}",
            label_key="decision.sell_dope.option",
            payload={"pawn_id": pawn_id, "dope_type": dope_type.value, "spot_id": spot_id},
        )
        for i, (pawn_id, spot_id, dope_type) in enumerate(candidates)
    )
    if repeat_pawns:
        # Total package size is still capped at `grit_value` — the boost
        # only lifts the "N different pawns for N sales" requirement, not
        # the round's own Grit-based budget (mirrors `_buy_dope_options`'
        # own `_max_affordable_prefix_count(..., grit_value)` cap).
        max_selectable = min(grit_value, len(candidates))
    else:
        distinct_pawns = {pawn_id for pawn_id, _, _ in candidates}
        max_selectable = min(grit_value, len(distinct_pawns))
    if max_selectable < 1:
        return None
    return options, max_selectable


def _corrupt_officer_options(
    state: GameState, player: PlayerState, grit_value: int
) -> tuple[tuple[DecisionOption, ...], int] | None:
    """Like `_buy_dope_options` (2026-08-16 fix): every individually-legal
    (pawn, officer) pair is offered, checked against the real board
    state — *not* budgeted to at most one (pawn, officer) pair per pawn
    as options are generated.

    An earlier version stopped at each pawn's *first* eligible officer
    (`break`) and tracked a shared `used_officers` set, on the theory
    that no subset of selections should be able to target the same
    officer twice. That's true of the *final* package, but as a
    generation-time filter it silently picked the officer for a pawn
    eligible for several, and — worse — could starve a *different* pawn
    entirely: a Rat can corrupt any Cop anywhere (§C5), so a Rat iterated
    before a Criminal locked to a single Hood could "claim" the one Cop
    that Criminal could *also* reach, leaving the Criminal with nothing
    even though reassigning the Rat to a different Cop would let both
    act (game designer, 2026-08-16 bug report: Grit 3 "Corrompi" only
    ever offered 1 option; reproduced with exactly this Rat-then-Criminal
    ordering).

    The command bus still rejects a package that names the same officer
    twice (`duplicate_officer_in_targets`) or the same pawn twice
    (`duplicate_pawn_in_targets`), so an over-generous combination a
    human builds on the board fails cleanly instead of silently
    corrupting the same officer from two pawns.
    `bots/random_legal.py::_pick_corrupt_officer_options` dedupes by both
    pawn and officer while picking, the same way `_pick_move_criminal_
    options` budgets Hood capacity — the decision about which pawn
    "wins" a contested officer moved from the generator to the picker.

    Cheapest-`grit_value` affordability is checked the same way as
    `_buy_dope_options`, using the guaranteed *minimum* cost per officer
    (1 corruption action, $1) — same reasoning as officers.py's own
    upfront package check, since the real cost depends on however many
    actions get chosen later. Same raw-candidate-vs-distinct-pawn
    tolerance as `_buy_dope_options`: a pawn eligible for several
    officers (e.g. a Rat) now contributes one raw candidate per officer,
    which can inflate `max_selectable` beyond what's jointly achievable —
    the command handler's own duplicate checks are the real backstop.

    2026-08-16 (2nd fix): `grit_value` is the action's *original* full
    budget, not what's left — this decision can now be re-offered after
    an earlier officer's corruption already finished (rules/officers.py::
    _finish_corruption looping back instead of ending the action), so
    pawns already used this same action (`player.
    corrupted_pawn_ids_this_action`) are excluded from candidates
    entirely (a pawn corrupts at most one officer per action instance,
    same as before — see PlayerState's own docstring) and `max_selectable`
    is capped by the *remaining* budget, not the full one."""
    candidates: list[tuple[int, PawnId, OfficerId]] = []
    # Cards 061/062 "FAKE POLICE": 1 Dope unit (any type) per corruption
    # instead of the normal per-action money cost — reuses
    # `_max_affordable_prefix_count` below unchanged by treating "1 Dope
    # unit" as a flat cost of 1 against a "budget" of however many Dope
    # units the player actually holds, same shape as the real $-cost
    # case (rules/officers.py::_start_corruption/_handle_corrupt_officer
    # enforce the same thing again on the command side).
    boost = player.active_card_boost
    fake_police = boost is not None and boost["type"] == "fake_police_dope_payment"
    if fake_police:
        min_cost = 1
        affordability_budget = sum(player.base_inventory.dope_counts.values())
    else:
        min_cost = officers.corruption_action_cost(state, player)
        affordability_budget = player.money
    already_used = set(player.corrupted_pawn_ids_this_action)
    remaining_budget = grit_value - len(already_used)
    if remaining_budget < 1:
        return None

    for pawn_id in player.pawn_ids:
        if pawn_id in already_used:
            continue
        pawn = state.pawns[pawn_id]
        if pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK, PawnRole.RAT):
            continue
        for officer_id, officer in state.board.officers.items():
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

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[0])
    max_selectable = _max_affordable_prefix_count(
        [c[0] for c in candidates], affordability_budget, remaining_budget
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
    remaining_into_base = max(0, officer_cap - officer_count_in_base(state, player.player_id))

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
    # same "stop" as running out of legal targets would). Cards 061/062
    # "FAKE POLICE": the whole corruption was already paid for in Dope
    # when it started, so every further sub-action here is free.
    boost = player.active_card_boost
    fake_police = boost is not None and boost["type"] == "fake_police_dope_payment"
    if fake_police or officers.corruption_action_cost(state, player) <= player.money:
        for action in officers.CORRUPTION_ACTIONS:
            if action in progress.actions_taken:
                continue
            options.extend(_corruption_action_candidates(state, officer, action, player))

    # The player may always stop voluntarily once at least 1 action has
    # been taken — up to 3 actions total, $1 each, entirely their choice
    # how many and which (decision 2026-08-15) — not just when no legal
    # action remains. Also forced whenever `options` came back empty
    # (unaffordable, or no target left for any remaining action kind) even
    # with 0 actions_taken so far, so this never becomes an impossible
    # min_selections=1/max_selections=0 decision (CLAUDE.md section 17.3:
    # never a decision without options and without the ability to pass).
    can_pass = bool(progress.actions_taken) or not options
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
    state: GameState, officer: OfficerState, action: str, player: PlayerState
) -> list[DecisionOption]:
    options: list[DecisionOption] = []

    if action == "move":
        # Card 065 "TRANSFER" ("se sposti, manda il poliziotto dove
        # vuoi") — any other Hood (Cop) or Spot (Fed) instead of only an
        # adjacent one; `rules/officers.py::_apply_move` mirrors the same
        # bypass in its own validation. No "revealed" filter here either,
        # matching the adjacent-move case just below, which has never
        # required it (a Hood only reachable this way isn't necessarily
        # revealed, and corruption moves have never checked that).
        boost = player.active_card_boost
        anywhere = boost is not None and boost["type"] == "officer_move_anywhere"
        # Cards 069/070/071 "REASSIGN": an *additional* destination kind
        # (Cop -> a Spot of the same Contact becomes a Fed, Fed -> a
        # Hood of the same Contact becomes a Cop) — see
        # rules/officers.py::_apply_move's own matching bypass.
        cross_type = boost is not None and boost["type"] == "officer_move_cross_type"
        if officer.officer_type == OfficerType.COP:
            hood = state.board.hoods[officer.hood_id]  # type: ignore[index]
            dest_ids = (
                [h.hood_id for h in state.board.hoods.values() if h.hood_id != hood.hood_id]
                if anywhere
                else list(hood.adjacent_hood_ids)
            )
            for dest_id in dest_ids:
                options.append(_corruption_option(f"corr_move_{dest_id}", "move", dest_id))
            if cross_type:
                for spot in state.board.spots.values():
                    if spot.contact_id == hood.contact_id:
                        options.append(
                            _corruption_option(f"corr_move_{spot.spot_id}", "move", spot.spot_id)
                        )
        else:
            spot = state.board.spots[officer.spot_id]  # type: ignore[index]
            dest_spot_ids = (
                [s for s in state.board.spots if s != spot.spot_id]
                if anywhere
                else list(spot.adjacent_spot_ids)
            )
            for dest_spot_id in dest_spot_ids:
                options.append(
                    _corruption_option(f"corr_move_{dest_spot_id}", "move", dest_spot_id)
                )
            if cross_type:
                for hood in state.board.hoods.values():
                    if hood.contact_id == spot.contact_id:
                        options.append(
                            _corruption_option(f"corr_move_{hood.hood_id}", "move", hood.hood_id)
                        )

    elif action == "arrest":
        # Cards 073/074/075 "REDEEM": replaces "arrest" outright with
        # releasing up to 2 of the player's own Rats — needs no free
        # Jail slot (it frees one, doesn't fill one), so it's checked
        # before that gate, not after it.
        boost = player.active_card_boost
        if boost is not None and boost["type"] == "redeem_release_rats":
            if any(state.pawns[pid].role == PawnRole.RAT for pid in player.pawn_ids):
                options.append(_corruption_option("corr_arrest_redeem", "arrest", None))
            return options
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
        # Cards 063/064 "FAKE POLICE" ("prendi la Merce requisita",
        # rules/officers.py::_apply_confiscate): goes straight to the
        # confiscator's own Covo, so it needs no free Jail slot at all.
        boost = player.active_card_boost
        keeps_for_self = boost is not None and boost["type"] == "keep_confiscated_dope"
        if not keeps_for_self and not jail.has_free_confiscation_slot(state):
            return options
        # Card 066 "INSIDER" ("se requisisci, scegli dove mettere la
        # Merce"): one option per free Jail slot instead of the usual
        # single "confiscate" option — see
        # rules/officers.py::_apply_confiscate's own matching validation.
        choose_slot = boost is not None and boost["type"] == "insider_choose_jail_slot"
        has_dope_to_confiscate = (
            bool(state.board.hoods[officer.hood_id].dope_stack)  # type: ignore[index]
            if officer.officer_type == OfficerType.COP
            else bool(state.board.spots[officer.spot_id].sold_dope_tokens)  # type: ignore[index]
        )
        if choose_slot:
            if has_dope_to_confiscate:
                for slot in state.jail.slots:
                    if slot.confiscated_dope_type is None:
                        options.append(
                            _corruption_option(
                                f"corr_confiscate_slot_{slot.index}", "confiscate", str(slot.index)
                            )
                        )
        elif officer.officer_type == OfficerType.COP:
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
    winner = find_player(state, progress.winner_id)
    winner_boost = winner.active_card_boost
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
    # Cards 021/023 "FIGHT!!" (steal a Dope) / 028/039 "FIGHT!!" (steal
    # a Poker Chip) — only offered when the winner holds the matching
    # boost *and* the loser actually has something of that kind
    # (rules/brawl.py::_handle_choose_brawl_loser_reward re-derives both
    # checks again, CLAUDE.md §10).
    dope_theft_eligible = (
        winner_boost is not None and winner_boost["type"] == "brawl_reward_dope_theft"
    )
    if dope_theft_eligible and any(
        count > 0 for count in loser.base_inventory.dope_counts.values()
    ):
        options.append(
            DecisionOption(
                option_id="brawl_reward_dope",
                label_key="decision.choose_brawl_loser_reward.dope",
                payload={"loser_player_id": loser_id, "reward_type": "dope"},
            )
        )
    chip_theft_eligible = (
        winner_boost is not None and winner_boost["type"] == "brawl_reward_chip_theft"
    )
    if chip_theft_eligible and loser.base_inventory.poker_chip_count > 0:
        options.append(
            DecisionOption(
                option_id="brawl_reward_poker_chip",
                label_key="decision.choose_brawl_loser_reward.poker_chip",
                payload={"loser_player_id": loser_id, "reward_type": "poker_chip"},
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

    # A SKILL column at the 3-Skill cap (game designer, 2026-08-27) is
    # only offered if there's at least one currently-held Skill that
    # could actually be bumped to make room — rules/jobs.py's own
    # ChooseSkillToDiscard sub-step (entered right after this column is
    # picked) would otherwise have nothing valid to offer either.
    skill_cap = state.configuration["skill_cap"]
    skill_bonus_blocked = len(player.skill_ids) >= skill_cap and not jobs.discardable_skill_ids(
        state, player
    )

    options: list[DecisionOption] = []
    for cell in state.jobs.board:
        if cell.job_id != entry.job_id or cell.player_id is not None:
            continue
        bonus_type = jobs.effective_column_bonus_type(state, job_def, cell.column_index)
        if skill_bonus_blocked and bonus_type == JobBonusType.SKILL:
            continue
        # MONEY doesn't care which Contact — a flat cash grant offering
        # one duplicate option per Contact on a 2-Contact Job used to
        # force a pointless "which Contact" click (its own board target
        # even looked like picking a Link, designer's request,
        # 2026-09-02) for a reward that's the same either way. Every
        # other bonus type still needs the real choice (which Contact's
        # Skill pile/card deck/Link).
        contact_choices = (
            (job_def.contact_ids[0],)
            if two_contacts and bonus_type == JobBonusType.MONEY
            else (job_def.contact_ids if two_contacts else (None,))
        )
        for contact_id in contact_choices:
            options.append(
                DecisionOption(
                    option_id=f"job_reward_{entry.job_id}_{cell.column_index}_{contact_id}",
                    label_key="decision.choose_job_reward.option",
                    payload=(
                        {
                            "job_id": entry.job_id,
                            "column_index": cell.column_index,
                            "contact_id": contact_id,
                        }
                        if two_contacts
                        else {"job_id": entry.job_id, "column_index": cell.column_index}
                    ),
                )
            )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="choose_job_reward",
        prompt_key="decision.choose_job_reward.prompt",
        options=tuple(options),
        min_selections=1,
        max_selections=1,
        can_pass=False,
    )


def _skill_discard_decision(
    state: GameState, player: PlayerState, decision_id: DecisionId
) -> PendingDecision:
    options = tuple(
        DecisionOption(
            option_id=f"discard_skill_{skill_id}",
            label_key="decision.choose_skill_to_discard.option",
            payload={"skill_id": skill_id},
        )
        for skill_id in jobs.discardable_skill_ids(state, player)
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="choose_skill_to_discard",
        prompt_key="decision.choose_skill_to_discard.prompt",
        options=options,
        min_selections=1,
        max_selections=1,
        can_pass=False,
    )


def _job_bonus_alternative_decision(
    player: PlayerState, decision_id: DecisionId
) -> PendingDecision:
    """Job 8's own column 2 override (2026-09-02) — always exactly these
    2 options, no board-state lookup needed (see `JobBonusType.
    MONEY_OR_TWO_CARDS`'s own docstring)."""
    options = tuple(
        DecisionOption(
            option_id=f"job_bonus_alternative_{bonus_type.value}",
            label_key="decision.choose_job_bonus_alternative.option",
            payload={"bonus_type": bonus_type.value},
        )
        for bonus_type in (JobBonusType.MONEY, JobBonusType.TWO_CARDS)
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="choose_job_bonus_alternative",
        prompt_key="decision.choose_job_bonus_alternative.prompt",
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
    """§D3 (2026-08-17 decision: "before" the whole action only, never
    after — see `rules/economy.py::_finish_buy_or_sell_package`'s
    docstring): offered right after `ChooseActionType`, any Dope type,
    since no package exists yet. Only offered when the player holds at
    least one card with Stonk symbols, so `eligible_card_ids` below is
    never empty. **Which card — RESOLVED (game designer, 2026-08-15):**
    a genuine player choice, not an auto-pick of the highest-Stonk card;
    with 2+ eligible cards, `_choose_marketing_card_decision` offers
    that choice first (`ChooseMarketingCard`) and this function is
    re-entered afterwards with `player.marketing_chosen_card_id` set.
    With exactly one eligible card there's nothing to choose, so it's
    used directly, same as before. Each Stonk is one indivisible
    (dope_type, delta) allocation, duplicated `stonk_count` times per
    distinct combination so a player can freely stack several Stonks on
    the same good, or split them across up to `stonk_count` different
    ones, same as `_place_criminal_options`'s own duplicate-until-cap
    pattern."""
    eligible_card_ids = sorted(
        (cid for cid in player.hand_card_ids if stonk_count_by_card_id.get(cid, 0) > 0),
        key=lambda cid: -stonk_count_by_card_id[cid],
    )
    card_id = player.marketing_chosen_card_id
    if card_id is None:
        if len(eligible_card_ids) > 1:
            return _choose_marketing_card_decision(
                player, decision_id, eligible_card_ids, stonk_count_by_card_id
            )
        card_id = eligible_card_ids[0]
    stonk_count = stonk_count_by_card_id[card_id]
    dope_types = sorted(price_tracks, key=lambda dt: dt.value)

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


def _choose_marketing_card_decision(
    player: PlayerState,
    decision_id: DecisionId,
    eligible_card_ids: list[CardId],
    stonk_count_by_card_id: dict[CardId, int],
) -> PendingDecision:
    """The "which card" sub-step ahead of `_marketing_decision`'s own
    Stonk-allocation choice — only reached with 2+ eligible cards.
    `min_selections=0`/`can_pass=True`: declining here (0 selections)
    means declining Marketing outright for this offer, same as declining
    the allocation step itself would."""
    options = tuple(
        DecisionOption(
            option_id=f"mkt_card_{card_id}",
            label_key="decision.choose_marketing_card.option",
            payload={"card_id": card_id, "stonk_count": stonk_count_by_card_id[card_id]},
        )
        for card_id in eligible_card_ids
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="choose_marketing_card",
        prompt_key="decision.choose_marketing_card.prompt",
        options=options,
        min_selections=0,
        max_selections=1,
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
    # §D2 (confirmed 2026-08-01): a card normally only launches Poker in
    # the round matching its own bound action_type — but Preti-3's "poker
    # on any action" Skill lifts that requirement (mirrors the same
    # bypass already applied by economy.py::_player_can_launch_poker_for_action,
    # which decides *whether* to reach this decision at all, and by
    # rules/poker.py::_handle_launch_poker's own validation). Missing it
    # here left the prompt correctly offered but with no card actually
    # selectable (bug report, 2026-08-27).
    any_action = skills.can_launch_poker_any_action(state, player)
    options = tuple(
        DecisionOption(
            option_id=f"launch_poker_{card_id}",
            label_key="decision.launch_poker.option",
            payload={"card_id": card_id},
        )
        for card_id in player.hand_card_ids
        if card_contact_by_id.get(card_id) == ContactId("preti")
        and (any_action or action_type_by_card_id.get(card_id) == player.pending_action_type)
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


# --- Customer Card boost (WAITING_FOR_CARD_BOOST) -----------------------


def _card_boost_decision(
    player: PlayerState,
    decision_id: DecisionId,
    card_effect_by_id: dict[CardId, dict | None],
    action_type_by_card_id: dict[CardId, ActionType | None],
) -> PendingDecision:
    """Offered right after `ChooseActionType`, chained after any
    Poker-launch/Marketing offer (`rules/customer_cards.py::
    offer_boost_or_resume`) — a card whose own printed `action_type`
    matches `player.pending_action_type` and has a structured `effect`
    (not every card does yet, see data/customer_cards.json's
    `dataset_note`). Single choice, no sub-step: unlike Marketing's Stonk
    allocation, playing an eligible card is already the whole decision."""

    def _eligible(card_id: CardId) -> bool:
        effect = card_effect_by_id.get(card_id)
        if effect is None or action_type_by_card_id.get(card_id) != player.pending_action_type:
            return False
        # Cards 052/056 "REINFORCE": same Grit-3/has-Dope precondition as
        # `rules/customer_cards.py::can_play_boost_for_action` (which
        # gates whether this step is even entered) — repeated here since
        # this is the actual option list a player/bot sees once inside
        # it, and other boost-eligible cards can still put them here even
        # when this one specific card isn't playable yet.
        if effect["type"] == "reinforce_dope_discard":
            return customer_cards.reinforce_discard_eligible(player)
        return True

    options = tuple(
        DecisionOption(
            option_id=f"card_boost_{card_id}",
            label_key="decision.play_customer_card_boost.option",
            payload={"card_id": card_id},
        )
        for card_id in player.hand_card_ids
        if _eligible(card_id)
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="play_customer_card_boost",
        prompt_key="decision.play_customer_card_boost.prompt",
        options=options,
        min_selections=0,
        max_selections=1 if options else 0,
        can_pass=True,
    )


def _reinforce_discard_decision(player: PlayerState, decision_id: DecisionId) -> PendingDecision:
    """Cards 052/056 "REINFORCE": one option per Dope type currently held
    in the Covo — `rules/economy.py::_handle_choose_reinforce_discard`
    turns the pick into the actual `place_criminal` target count (that
    type's current sell price). No PassOptionalStep: the boost was
    already committed when the card was played
    (`reinforce_discard_eligible` guarantees at least one Dope type is
    available by the time this step is reached)."""
    options = tuple(
        DecisionOption(
            option_id=f"reinforce_discard_{dope_type.value}",
            label_key="decision.choose_reinforce_discard.option",
            payload={"dope_type": dope_type.value},
        )
        for dope_type, count in player.base_inventory.dope_counts.items()
        if count > 0
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="choose_reinforce_discard",
        prompt_key="decision.choose_reinforce_discard.prompt",
        options=options,
        min_selections=1,
        max_selections=1,
        can_pass=False,
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
            # gamble_card_id lets a client resolve this match to *its own*
            # launched-card slot on the board (PlayerGameView's
            # poker_launched_card_ids is in the same launch order) — the
            # command itself only ever needs match_id.
            payload={"match_id": match.match_id, "card_id": match.gamble_card_id},
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
    max_selections = min(_den_gambler_count(state, player_id), len(options), revealable_card_count)
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
    """§A10 Preti-1 ("Puoi giocare 2 carte per ogni Poker"): a bettor with
    this Skill gets `max_selections=2` here instead of the normal 1 —
    still purely optional (min stays 1, "puoi" not "devi"), capped by how
    many eligible cards are actually in hand. Selecting exactly 2 routes
    into `WAITING_FOR_POKER_SYMBOL_CHOICE` next (see `rules/poker.py::
    _handle_play_poker_card`); selecting 1 behaves exactly like a normal
    reveal, Skill or not.

    RULES_PENDING.md #25: `rules/poker.py::_handle_place_poker_bet` only
    checks the bettor has >= 1 non-Preti card *per match* bet on, at bet
    time — it has no way to know in advance how many of those this same
    Skill will actually spend on any *one* match. Revealing 2 here for an
    earlier-resolving match can starve a later one this same bettor is
    also staked on down to 0 eligible cards, which `min_selections=1`
    then can't satisfy (found via RULES_PENDING.md #24's determinism
    bisection, seed 288 — "revealing 0 cards" isn't a mechanic the
    rulebook describes, so the fix is preventing the shortfall, not
    offering a decline). `max_selectable` is capped here so at least 1
    non-Preti card is always left in reserve per other still-open match
    this bettor is staked on."""
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
    max_selectable = 1
    if skills.can_reveal_two_poker_cards(state, player):
        other_open_matches = sum(
            1
            for later_match in state.poker.matches_this_turn[
                state.poker.resolving_match_index + 1 :
            ]
            if player.player_id in later_match.bets_by_player_id
        )
        max_selectable = min(2, max(1, len(options) - other_open_matches))
    return PendingDecision(
        decision_id=decision_id,
        player_id=player.player_id,
        decision_type="play_poker_card",
        prompt_key="decision.play_poker_card.prompt",
        options=options,
        min_selections=1,
        max_selections=max_selectable,
        can_pass=False,
    )


def _choose_poker_symbols_decision(
    state: GameState, player_id: PlayerId, decision_id: DecisionId
) -> PendingDecision:
    """§A10 Preti-1's own second step: 4 options, one per revealed symbol
    *instance* (not deduped by color — a same color appearing on both
    revealed cards is 2 separate, both-selectable slots), exactly 2 to be
    picked. `_start_new_round`/etc. never build option_ids from a bare
    color alone elsewhere in this module, so the same "index the raw
    instance list" trick sell_dope's own duplicate-Stonk options already
    use is reused here to keep each of the (possibly repeated) colors its
    own selectable option."""
    pending = state.poker.pending_symbol_choice
    assert pending is not None
    options = tuple(
        DecisionOption(
            option_id=f"poker_symbol_{i}_{symbol.value}",
            label_key="decision.choose_poker_symbols.option",
            payload={"symbol": symbol.value, "match_id": pending.match_id},
        )
        for i, symbol in enumerate(pending.available_symbols)
    )
    return PendingDecision(
        decision_id=decision_id,
        player_id=player_id,
        decision_type="choose_poker_symbols",
        prompt_key="decision.choose_poker_symbols.prompt",
        options=options,
        min_selections=2,
        max_selections=2,
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
            den_deck_contact_ids=tuple(
                o.payload["deck_contact_id"] for o in selected if o.payload["hood_id"] == DEN_ID
            ),
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
            extra_den_deck_contact_ids=tuple(
                o.payload["extra_deck_contact_id"]
                for o in selected
                if o.payload.get("extra_deck_contact_id") is not None
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
            purchases=tuple((o.payload["pawn_id"], o.payload["hood_id"]) for o in selected),
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
            # Always filled in from the option's own `spot_id` (card 012,
            # RULES_PENDING.md #26) — harmless when there's only one
            # possible Spot anyway, needed once "vendi in un quartiere
            # adiacente" makes more than one reachable at once. One
            # triple per sale, not deduped by pawn — a repeated pawn
            # (card 015) selling different Dope types still needs its
            # own entry per sale.
            explicit_spots=tuple(
                (o.payload["pawn_id"], DopeType(o.payload["dope_type"]), o.payload["spot_id"])
                for o in selected
            ),
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

    if decision.decision_type == "choose_skill_to_discard":
        return ChooseSkillToDiscard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            skill_id=selected[0].payload["skill_id"],
        )

    if decision.decision_type == "choose_job_bonus_alternative":
        return ChooseJobBonusAlternative(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            bonus_type=selected[0].payload["bonus_type"],
        )

    if decision.decision_type == "choose_marketing_card":
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return ChooseMarketingCard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=selected[0].payload["card_id"],
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

    if decision.decision_type == "play_customer_card_boost":
        if not selected:
            return PassOptionalStep(
                game_id=game_id,
                player_id=player_id,
                expected_revision=expected_revision,
                decision_id=decision_id,
            )
        return PlayCustomerCardBoost(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=selected[0].payload["card_id"],
        )

    if decision.decision_type == "choose_reinforce_discard":
        return ChooseReinforceDiscard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            dope_type=DopeType(selected[0].payload["dope_type"]),
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
            card_ids=tuple(o.payload["card_id"] for o in selected),
        )

    if decision.decision_type == "choose_poker_symbols":
        chosen = tuple(PokerSymbolColor(o.payload["symbol"]) for o in selected)
        return ChoosePokerSymbols(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            match_id=selected[0].payload["match_id"],
            chosen_symbols=(chosen[0], chosen[1]),
        )

    raise ValueError(f"Unknown decision_type '{decision.decision_type}'")
