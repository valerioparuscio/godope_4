"""The four economic actions (RULES_CANONICAL.md §C1-C4): placing,
moving, buying and selling Criminals/Dope, plus the Cop/Fed spawn and
blocking mechanics those actions trigger (§A6).

Each of the 6 base actions (§B2) spends the round's whole Grit value at
once: choosing e.g. Grit 3 for "Acquistare" means exactly 3 *different*
Criminals each buy 1 Dope, bundled into a single BuyDope command. That
command's targets are validated and applied one at a time in this
module (not pre-validated as a batch) because buying/selling can change
board conditions (price, stock, Cop/Fed presence) *during* the package
that later targets in the same command depend on — only the "package"
price change is deferred to the end (§C3/§C4 "l'aumento/la riduzione
dei prezzi si applica alla fine"); restocks, Cop/Fed spawns and clears
happen immediately per unit, per the literal rule text.

A package's price step count equals the number of units bought/sold of
that Dope type (not a flat 1 per package) — confirmed by the game
designer (2026-07-31): buying/selling 3 in one package moves the price 3
positions, applied once at the end of the package (§C3/§C4 "l'aumento/la
riduzione dei prezzi si applica alla fine").

A Milestone-2 gap remains intentionally unimplemented (tracked in
docs/rules/RULES_PENDING.md, not a rules ambiguity — it belongs to a
later milestone): Fed removal-from-Spot ("senza Merci e senza Ganci",
§A6) — a Fed always spawns exactly when its Spot's condition would
already be "senza Merci" (right after emptying), which would
self-cancel immediately unless a Link is also present at that Spot's
Contact. Cop removal from a Hood *is* implemented, since "no Dope and no
Criminals" is not self-cancelling at spawn time (a restock always
leaves 1-3 Dope).

Selling a package grants a Link (§C4 "Vendita a pacchetto"), grouped by
*Spot* (not by Dope type — the rule text says "allo stesso Punto di
Vendita"): each Spot sold to in the package gets one Link at its
Contact, at the level equal to how many units went to that Spot, held
by the first pawn (in command order) that sold there. This is a
deliberate simplification of §A5's "può evolversi" (single-unit sales
*may* optionally evolve into a Link): Milestone 3 makes both the
single-unit and package cases automatic rather than adding another
interactive decision, tracked as PROVISIONAL in RULES_PENDING.md.
"""

from __future__ import annotations

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import (
    BuyDope,
    ChooseActionType,
    ChooseMarketingCard,
    EvolveSaleLink,
    MoveCriminal,
    PlaceCriminal,
    PlayMarketingCard,
    SellDope,
)
from dope_engine.domain.entities import (
    HoodState,
    OfficerLocationType,
    OfficerState,
    PawnLocation,
    PawnState,
    SalesSpotState,
)
from dope_engine.domain.enums import (
    ActionType,
    ActiveStep,
    DopeType,
    GamePhase,
    OfficerType,
    PawnRole,
)
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    ActionTypeChosen,
    CardDrawn,
    CopEnteredHood,
    CriminalPlaced,
    DomainEvent,
    DopeBought,
    DopeLostToOverflow,
    DopeSold,
    FedEnteredSpot,
    HoodRestocked,
    MarketCrashed,
    MarketingCardPlayed,
    OfficerReturnedToReserve,
    PriceChanged,
    SpotCleared,
)
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    HoodId,
    OfficerId,
    PawnId,
    PlayerId,
    SpotId,
)
from dope_engine.domain.rng import GameRandom
from dope_engine.domain.state import (
    GameState,
    PendingSaleLinkEvolution,
    PlayerState,
    find_player,
)
from dope_engine.rules import links, prices, skills, turn_flow
from dope_engine.rules.event_utils import emit as _emit
from dope_engine.rules.prices import PriceTracks

PRETI_CONTACT_ID = ContactId("preti")


def register_handlers(
    bus: CommandBus,
    *,
    price_tracks: PriceTracks,
    card_contact_by_id: dict[CardId, ContactId],
    link_extra_action_types: dict[ContactId, tuple[str, ...]],
    action_type_by_card_id: dict[CardId, ActionType | None],
    stonk_count_by_card_id: dict[CardId, int] | None = None,
) -> None:
    stonk_count_by_card_id = stonk_count_by_card_id or {}
    bus.register(
        ChooseActionType,
        lambda s, c: _handle_choose_action_type(
            s,
            c,
            link_extra_action_types,
            action_type_by_card_id,
            card_contact_by_id,
            stonk_count_by_card_id,
        ),
    )
    bus.register(PlaceCriminal, _handle_place_criminal)
    bus.register(MoveCriminal, _handle_move_criminal)
    bus.register(
        BuyDope, lambda s, c: _handle_buy_dope(s, c, price_tracks, stonk_count_by_card_id)
    )
    bus.register(
        SellDope, lambda s, c: _handle_sell_dope(s, c, price_tracks, stonk_count_by_card_id)
    )
    bus.register(
        EvolveSaleLink,
        lambda s, c: _handle_evolve_sale_link(s, c, price_tracks, stonk_count_by_card_id),
    )
    bus.register(
        PlayMarketingCard,
        lambda s, c: _handle_play_marketing_card(
            s, c, price_tracks, stonk_count_by_card_id, card_contact_by_id
        ),
    )
    bus.register(
        ChooseMarketingCard,
        lambda s, c: _handle_choose_marketing_card(s, c, stonk_count_by_card_id),
    )


# --- shared presence helpers -----------------------------------------

# CLAUDE.md §11.4/§11.5/§11.6 + game designer (2026-08-15): a Link counts
# as presence in every Hood of its own Contact for Buy/Sell eligibility,
# exactly like it already did for Cop/Fed corruption (rules/officers.py).
# Owned here (not rules/officers.py, which already depends on this
# module) so both directions of the "buy/sell presence" and "corrupt
# presence" checks share one definition instead of drifting independently.


def has_presence_at_hood(state: GameState, pawn: PawnState, hood_id: HoodId) -> bool:
    if pawn.role == PawnRole.CRIMINAL:
        return pawn.location.hood_id == hood_id
    if pawn.role == PawnRole.LINK:
        return state.board.hoods[hood_id].contact_id == pawn.contact_id
    return False


def has_presence_at_spot(state: GameState, pawn: PawnState, spot_id: SpotId) -> bool:
    spot = state.board.spots[spot_id]
    if pawn.role == PawnRole.CRIMINAL:
        return state.board.hoods[pawn.location.hood_id].contact_id == spot.contact_id  # type: ignore[index]
    if pawn.role == PawnRole.LINK:
        return pawn.contact_id == spot.contact_id
    return False


# --- validation helpers -----------------------------------------------


_TARGET_WAITING_STEPS = (
    ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS,
    ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION,
)


def _validate_step(state: GameState, player_id: PlayerId) -> DomainError | None:
    if state.phase != GamePhase.ACTION_PHASE:
        return wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value)
    if state.current_player_id != player_id:
        return wrong_player(str(state.current_player_id), str(player_id))
    if state.active_step not in _TARGET_WAITING_STEPS:
        return DomainError(
            code="wrong_active_step",
            message=(
                f"Not waiting for a main/extra action (state is at '{state.active_step.value}')."
            ),
            details={"actual_step": state.active_step.value},
        )
    return None


def _validate_action_targets(
    state: GameState, player_id: PlayerId, expected: ActionType, target_count: int
) -> tuple[DomainError | None, PlayerState | None]:
    error = _validate_step(state, player_id)
    if error is not None:
        return error, None

    player = find_player(state, player_id)
    if player.pending_action_type != expected:
        return (
            DomainError(
                code="wrong_action_type",
                message=f"Expected action type '{expected.value}', not yet chosen or different.",
                details={"pending_action_type": str(player.pending_action_type)},
            ),
            None,
        )
    assert player.current_round_grit_value is not None
    max_count = skills.effective_action_count(
        state, player, expected, player.current_round_grit_value
    )
    # Confirmed by the game designer (2026-08-02): a package never has to
    # use its full (possibly Skill-boosted) Grit value — any count from 1
    # up to it is legal. 0 isn't: declining the action entirely is
    # PassOptionalStep, not a same-type command with an empty package.
    if target_count < 1 or target_count > max_count:
        return (
            DomainError(
                code="wrong_target_count",
                message=f"Expected 1 to {max_count} target(s), got {target_count}.",
                details={"min": 1, "max": max_count, "given": target_count},
            ),
            None,
        )
    return None, player


# --- shared helpers -----------------------------------------------------


def _draw_card(
    state: GameState, contact_id: ContactId, events: list[DomainEvent], player_id: PlayerId
) -> CardId:
    deck = state.decks.customer_decks_by_contact[contact_id]
    if not deck.draw_pile_card_ids:
        rng = GameRandom.from_state(state.rng_state)
        deck.draw_pile_card_ids = list(deck.discard_pile_card_ids)
        deck.discard_pile_card_ids = []
        rng.shuffle(deck.draw_pile_card_ids)
        state.rng_state = rng.get_state()
    card_id = deck.draw_pile_card_ids.pop(0)
    find_player(state, player_id).hand_card_ids.append(card_id)
    _emit(state, events, CardDrawn, player_id=player_id, contact_id=contact_id, card_id=card_id)
    return card_id


def _spawn_cop(state: GameState, hood: HoodState, events: list[DomainEvent]) -> None:
    state.board.officer_seq += 1
    officer_id = OfficerId(f"officer_{state.board.officer_seq:04d}")
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.HOOD,
        hood_id=hood.hood_id,
    )
    hood.cop_ids.append(officer_id)
    _emit(state, events, CopEnteredHood, officer_id=officer_id, hood_id=hood.hood_id)


def _restock_hood(state: GameState, hood: HoodState, events: list[DomainEvent]) -> None:
    dope_type = hood.dope_type
    if dope_type is None:
        return
    available = state.market.supply_remaining_by_dope_type.get(dope_type, 0)
    restock_count = min(3, available)
    if restock_count <= 0:
        return
    hood.dope_stack = [dope_type] * restock_count
    state.market.supply_remaining_by_dope_type[dope_type] -= restock_count
    _emit(
        state, events, HoodRestocked, hood_id=hood.hood_id, dope_type=dope_type, count=restock_count
    )
    _spawn_cop(state, hood, events)


def _check_hood_cop_removal(state: GameState, hood: HoodState, events: list[DomainEvent]) -> None:
    if hood.dope_stack or hood.criminal_pawn_ids:
        return
    for officer_id in list(hood.cop_ids):
        hood.cop_ids.remove(officer_id)
        officer = state.board.officers.pop(officer_id, None)
        if officer is not None:
            _emit(
                state,
                events,
                OfficerReturnedToReserve,
                officer_id=officer_id,
                officer_type=officer.officer_type,
            )


def _find_spot(state: GameState, contact_id: ContactId, dope_type: DopeType):
    for spot in state.board.spots.values():
        if spot.contact_id == contact_id and spot.accepted_dope_type == dope_type:
            return spot
    return None


def _clear_spot_and_spawn_fed(state: GameState, spot, events: list[DomainEvent]) -> None:
    spot.sold_dope_tokens = []
    _emit(state, events, SpotCleared, spot_id=spot.spot_id)
    state.board.officer_seq += 1
    officer_id = OfficerId(f"officer_{state.board.officer_seq:04d}")
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.FED,
        location_type=OfficerLocationType.SPOT,
        spot_id=spot.spot_id,
    )
    spot.fed_ids.append(officer_id)
    _emit(state, events, FedEnteredSpot, officer_id=officer_id, spot_id=spot.spot_id)


def _apply_price_step(
    state: GameState,
    price_tracks: PriceTracks,
    dope_type: DopeType,
    *,
    steps: int,
    events: list[DomainEvent],
) -> None:
    result = prices.step_price(state.market, price_tracks, dope_type, steps=steps)
    if result is None:
        return
    _emit(
        state,
        events,
        PriceChanged,
        dope_type=dope_type,
        steps=result.new_index - result.old_index,
        new_index=result.new_index,
    )
    if result.market_crashed:
        _emit(state, events, MarketCrashed)


def _finish_buy_or_sell_package(
    state: GameState,
    player: PlayerState,
    price_steps: dict[DopeType, int],
    events: list[DomainEvent],
    stonk_count_by_card_id: dict[CardId, int],
    price_tracks: PriceTracks,
) -> None:
    """§D3 Marketing (corrected 2026-08-02): the package's own automatic
    price step (`price_steps`, already signed — positive for Buy,
    negative for Sell) always applies immediately now — "prima o dopo"
    is about the whole action, not this one step (see
    `PlayerState.marketing_pre_return_step`'s docstring). If the player
    used Marketing "before" this action, a Manager-3 owner gets those
    same allocations replayed here automatically (no new card); anyone
    else who used "before" gets no further offer (their one shot is
    spent). Otherwise, offer "after" if the player holds an eligible
    card — same "no eligible option, skip straight through" precedent as
    `rules/poker.py`'s own Gamble-launch offer."""
    for dope_type, steps in price_steps.items():
        _apply_price_step(state, price_tracks, dope_type, steps=steps, events=events)

    if player.marketing_pre_allocations:
        if skills.marketing_applies_both_timings(state, player):
            for dope_type, delta in player.marketing_pre_allocations:
                _apply_price_step(state, price_tracks, dope_type, steps=delta, events=events)
        player.marketing_pre_allocations = ()
        turn_flow.finish_action_or_extra(state, player, events)
        return

    has_eligible_card = any(
        stonk_count_by_card_id.get(card_id, 0) > 0 for card_id in player.hand_card_ids
    )
    if has_eligible_card:
        player.marketing_offer_is_pre = False
        player.marketing_eligible_dope_types = list(price_steps)
        state.active_step = ActiveStep.WAITING_FOR_CARD_USAGE
        return
    turn_flow.finish_action_or_extra(state, player, events)


# --- ChooseActionType -----------------------------------------------------


def _player_can_launch_poker_for_action(
    state: GameState,
    player: PlayerState,
    action_type: ActionType,
    action_type_by_card_id: dict[CardId, ActionType | None],
    card_contact_by_id: dict[CardId, ContactId],
) -> bool:
    """§D2 (confirmed 2026-08-01): a Preti Gamble card "si associa ad
    un'azione base" — it can only launch a Poker match in a round where
    the player is taking *that exact card's own* action_type (main
    action or, per the same confirmation, a Link's extra action)."""
    max_gamble = state.configuration["poker_max_gamble_cards_per_round"]
    if player.gamble_cards_played_this_round >= max_gamble:
        return False
    max_matches = state.configuration["poker_max_matches_per_turn"]
    if len(state.poker.matches_this_turn) >= max_matches:
        return False
    any_action = skills.can_launch_poker_any_action(state, player)
    return any(
        card_contact_by_id.get(card_id) == PRETI_CONTACT_ID
        and (any_action or action_type_by_card_id.get(card_id) == action_type)
        for card_id in player.hand_card_ids
    )


def _handle_choose_action_type(
    state: GameState,
    command: ChooseActionType,
    link_extra_action_types: dict[ContactId, tuple[str, ...]],
    action_type_by_card_id: dict[CardId, ActionType | None],
    card_contact_by_id: dict[CardId, ContactId],
    stonk_count_by_card_id: dict[CardId, int],
) -> CommandOutcome:
    error = _validate_step(state, command.player_id)
    if error is not None:
        return CommandFailure(error)

    player = find_player(state, command.player_id)
    if player.pending_action_type is not None:
        return CommandFailure(
            DomainError(
                code="action_type_already_chosen",
                message="An action type was already chosen for this round.",
                details={"pending_action_type": player.pending_action_type.value},
            )
        )
    try:
        action_type = ActionType(command.action_type)
    except ValueError:
        return CommandFailure(
            DomainError(
                code="unknown_action_type",
                message=f"'{command.action_type}' is not a known action type.",
                details={},
            )
        )

    if state.active_step == ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION:
        link_pawn_id = player.extra_action_link_pawn_id
        if link_pawn_id is None:
            return CommandFailure(
                DomainError(
                    code="no_link_chosen",
                    message="No Link has been spent for this extra action yet.",
                    details={},
                )
            )
        # The spent Link already returned to its Covo (contact_id
        # cleared) the moment it was chosen (rules/turn_flow.py, §A5,
        # confirmed 2026-08-01), so the Contact it unlocks comes from
        # the player's own cached `extra_action_contact_id`.
        contact_id = player.extra_action_contact_id
        allowed = link_extra_action_types.get(contact_id, ()) if contact_id is not None else ()
        if action_type.value not in allowed:
            return CommandFailure(
                DomainError(
                    code="action_type_not_allowed_for_link",
                    message=(
                        f"Contact '{contact_id}' does not allow '{action_type.value}' "
                        "as an extra action."
                    ),
                    details={"allowed": list(allowed)},
                )
            )
    elif action_type in player.action_types_used_this_turn:
        # Confirmed by the game designer (2026-08-02): a base Grit round's
        # action_type can't repeat within the same turn. Link extra
        # actions (branch above) are a separate mechanic, not restricted
        # by this.
        return CommandFailure(
            DomainError(
                code="action_type_already_used_this_turn",
                message=f"'{action_type.value}' was already used as a main action this turn.",
                details={"action_type": action_type.value},
            )
        )

    state.revision += 1
    player.pending_action_type = action_type
    if state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS:
        player.action_types_used_this_turn.append(action_type)
    events: list[DomainEvent] = []
    _emit(
        state, events, ActionTypeChosen, player_id=command.player_id, action_type=action_type.value
    )

    if _player_can_launch_poker_for_action(
        state, player, action_type, action_type_by_card_id, card_contact_by_id
    ):
        player.poker_launch_return_step = state.active_step
        state.active_step = ActiveStep.WAITING_FOR_POKER_LAUNCH
    elif action_type in (ActionType.BUY_DOPE, ActionType.SELL_DOPE) and any(
        stonk_count_by_card_id.get(cid, 0) > 0 for cid in player.hand_card_ids
    ):
        # §D3 Marketing (corrected 2026-08-02): "before the whole
        # action" is offered here, the same way a Poker launch is —
        # PROVISIONAL (RULES_PENDING.md): a player eligible for both
        # this round only ever gets the Poker offer, never both; a rare
        # overlap (a matching Preti card AND a Stonk card) not worth the
        # offer-chaining this would otherwise require.
        player.marketing_pre_return_step = state.active_step
        player.marketing_offer_is_pre = True
        state.active_step = ActiveStep.WAITING_FOR_CARD_USAGE

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- PlaceCriminal ----------------------------------------------------------


def _handle_place_criminal(state: GameState, command: PlaceCriminal) -> CommandOutcome:
    error, player = _validate_action_targets(
        state, command.player_id, ActionType.PLACE_CRIMINAL, len(command.hood_ids)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    cost_each = skills.effective_cost(
        state, player, ActionType.PLACE_CRIMINAL, state.configuration["costs"]["place_criminal"]
    )
    total_cost = cost_each * len(command.hood_ids)
    if player.money < total_cost:
        return CommandFailure(
            DomainError(
                code="insufficient_funds",
                message=f"Placing {len(command.hood_ids)} Criminal(s) costs ${total_cost}.",
                details={"required": total_cost, "available": player.money},
            )
        )

    available_pawns = sorted(
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    if len(available_pawns) < len(command.hood_ids):
        return CommandFailure(
            DomainError(
                code="not_enough_pawns_in_base",
                message="Not enough Criminals in the Covo.",
                details={"available": len(available_pawns), "needed": len(command.hood_ids)},
            )
        )

    # Placing (unlike moving) a Criminal never triggers a Rissa (§D1: it
    # "scatta quando si sposta il quinto Criminale") and Rissa resolution
    # isn't implemented until Milestone 4, so Place must never itself be
    # the action that brings a Hood to its Rissa-trigger count — otherwise
    # it would sit there indefinitely with no Milestone-2 mechanism to
    # resolve it, in violation of the confirmed design intent that a Hood
    # is never actually left full (see docs/rules/RULE_CHANGELOG.md,
    # 2026-07-31 entry).
    max_via_placement = state.configuration["brawl_trigger_criminal_count"] - 1
    needed_per_hood: dict[HoodId, int] = {}
    for hood_id in command.hood_ids:
        if hood_id not in state.board.hoods:
            return CommandFailure(
                DomainError(code="unknown_hood", message=f"Unknown Hood '{hood_id}'.", details={})
            )
        if not state.board.hoods[hood_id].revealed:
            # Only a Brawl loser's relocation can reach an unrevealed
            # Hood (game designer, 2026-08-16) — never a normal placement.
            return CommandFailure(
                DomainError(
                    code="hood_not_revealed",
                    message=f"Hood '{hood_id}' is not revealed yet.",
                    details={},
                )
            )
        needed_per_hood[hood_id] = needed_per_hood.get(hood_id, 0) + 1
    for hood_id, needed in needed_per_hood.items():
        hood = state.board.hoods[hood_id]
        remaining = max_via_placement - len(hood.criminal_pawn_ids)
        if needed > remaining:
            return CommandFailure(
                DomainError(
                    code="hood_capacity_exceeded",
                    message=f"Hood '{hood_id}' cannot fit {needed} more Criminal(s) via placement.",
                    details={"remaining_capacity": max(0, remaining)},
                )
            )

    state.revision += 1
    player.money -= total_cost
    events: list[DomainEvent] = []
    placed_pawn_ids = available_pawns[: len(command.hood_ids)]
    for pawn_id, hood_id in zip(placed_pawn_ids, command.hood_ids, strict=True):
        pawn = state.pawns[pawn_id]
        pawn.role = PawnRole.CRIMINAL
        pawn.location = PawnLocation.hood(hood_id)
        hood = state.board.hoods[hood_id]
        hood.criminal_pawn_ids.append(pawn_id)
        _emit(
            state,
            events,
            CriminalPlaced,
            player_id=command.player_id,
            pawn_id=pawn_id,
            hood_id=hood_id,
        )
        _draw_card(state, hood.contact_id, events, command.player_id)

    turn_flow.finish_action_or_extra(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- MoveCriminal -----------------------------------------------------------


def _handle_move_criminal(state: GameState, command: MoveCriminal) -> CommandOutcome:
    error, player = _validate_action_targets(
        state, command.player_id, ActionType.MOVE_CRIMINAL, len(command.moves)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    pawn_ids = [m[0] for m in command.moves]
    if len(set(pawn_ids)) != len(pawn_ids):
        return CommandFailure(
            DomainError(
                code="duplicate_pawn_in_targets",
                message="Each Criminal can only be moved once per action.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    # rules/movement.py owns the per-pawn move logic and the Rissa-trigger
    # check (§D1: the 5th Criminal can arrive on any move in this package,
    # not just the last one) — see its module docstring for why it lives
    # there instead of here. Deferred import: movement.py imports helpers
    # from this module, so importing it back at module load time would
    # be circular; by the time this handler actually runs, both modules
    # are already fully loaded.
    from dope_engine.rules import movement

    return movement.process_move_queue(
        state, command.player_id, player, list(command.moves), events
    )


# --- BuyDope ------------------------------------------------------------


def _handle_buy_dope(
    state: GameState,
    command: BuyDope,
    price_tracks: PriceTracks,
    stonk_count_by_card_id: dict[CardId, int],
) -> CommandOutcome:
    error, player = _validate_action_targets(
        state, command.player_id, ActionType.BUY_DOPE, len(command.purchases)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    if len({pawn_id for pawn_id, _ in command.purchases}) != len(command.purchases):
        return CommandFailure(
            DomainError(
                code="duplicate_pawn_in_targets",
                message="Each Criminal/Link can only buy once per action.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []
    price_step_totals: dict[DopeType, int] = {}

    for pawn_id, hood_id in command.purchases:
        pawn = state.pawns.get(pawn_id)
        if (
            pawn is None
            or pawn.owner_player_id != command.player_id
            or pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK)
            or hood_id not in state.board.hoods
            or not has_presence_at_hood(state, pawn, hood_id)
        ):
            return CommandFailure(
                DomainError(
                    code="pawn_not_eligible",
                    message=f"Pawn '{pawn_id}' cannot buy Dope at Hood '{hood_id}'.",
                    details={},
                )
            )
        hood = state.board.hoods[hood_id]
        if hood.cop_ids:
            return CommandFailure(
                DomainError(
                    code="hood_blocked_by_cop",
                    message=f"Hood '{hood.hood_id}' has a Cop.",
                    details={},
                )
            )
        if not hood.dope_stack:
            return CommandFailure(
                DomainError(
                    code="hood_has_no_dope",
                    message=f"Hood '{hood.hood_id}' has no Dope.",
                    details={},
                )
            )

        dope_type = hood.dope_stack[-1]
        base_price = prices.current_price(state.market, price_tracks, dope_type)
        price = skills.effective_trade_price(state, player, ActionType.BUY_DOPE, base_price)
        if player.money < price:
            return CommandFailure(
                DomainError(
                    code="insufficient_funds",
                    message=f"Buying {dope_type.value} costs ${price}, player has ${player.money}.",
                    details={},
                )
            )

        player.money -= price
        hood.dope_stack.pop()
        price_step_totals[dope_type] = price_step_totals.get(dope_type, 0) + 1

        if player.base_inventory.dope_counts.get(dope_type, 0) >= 3:
            _emit(
                state, events, DopeLostToOverflow, player_id=command.player_id, dope_type=dope_type
            )
        else:
            player.base_inventory.dope_counts[dope_type] = (
                player.base_inventory.dope_counts.get(dope_type, 0) + 1
            )

        _emit(
            state,
            events,
            DopeBought,
            player_id=command.player_id,
            pawn_id=pawn_id,
            hood_id=hood.hood_id,
            dope_type=dope_type,
            price_paid=price,
        )

        if not hood.dope_stack:
            _restock_hood(state, hood, events)
            _check_hood_cop_removal(state, hood, events)

    price_steps = dict(price_step_totals)
    _finish_buy_or_sell_package(
        state, player, price_steps, events, stonk_count_by_card_id, price_tracks
    )
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- SellDope -----------------------------------------------------------


def _handle_sell_dope(
    state: GameState,
    command: SellDope,
    price_tracks: PriceTracks,
    stonk_count_by_card_id: dict[CardId, int],
) -> CommandOutcome:
    error, player = _validate_action_targets(
        state, command.player_id, ActionType.SELL_DOPE, len(command.sales)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    if len({pid for pid, _ in command.sales}) != len(command.sales):
        return CommandFailure(
            DomainError(
                code="duplicate_pawn_in_targets",
                message="Each Criminal can only sell once per action.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []
    price_step_totals: dict[DopeType, int] = {}
    sellers_by_spot: dict[SpotId, list[PawnId]] = {}

    for pawn_id, dope_type in command.sales:
        pawn = state.pawns.get(pawn_id)
        if (
            pawn is None
            or pawn.owner_player_id != command.player_id
            or pawn.role not in (PawnRole.CRIMINAL, PawnRole.LINK)
        ):
            return CommandFailure(
                DomainError(
                    code="pawn_not_eligible",
                    message=f"Pawn '{pawn_id}' cannot sell Dope.",
                    details={},
                )
            )
        # A Link's presence isn't Hood-scoped at all (has_presence_at_spot,
        # game designer 2026-08-15) — its own contact_id finds the Spot
        # directly, no Hood lookup needed; a Criminal's still comes from
        # its current Hood, same as before.
        contact_id = (
            pawn.contact_id
            if pawn.role == PawnRole.LINK
            else state.board.hoods[pawn.location.hood_id].contact_id  # type: ignore[index]
        )
        spot = _find_spot(state, contact_id, dope_type)  # type: ignore[arg-type]
        if spot is None:
            return CommandFailure(
                DomainError(
                    code="dope_type_not_accepted",
                    message=f"Contact '{contact_id}' does not accept {dope_type.value}.",
                    details={},
                )
            )
        if spot.fed_ids:
            return CommandFailure(
                DomainError(
                    code="spot_blocked_by_fed",
                    message=f"Spot '{spot.spot_id}' has a Fed.",
                    details={},
                )
            )
        if player.base_inventory.dope_counts.get(dope_type, 0) <= 0:
            return CommandFailure(
                DomainError(
                    code="no_dope_to_sell",
                    message=f"No {dope_type.value} in the Covo.",
                    details={},
                )
            )
        if len(spot.sold_dope_tokens) >= spot.capacity:
            return CommandFailure(
                DomainError(
                    code="spot_full", message=f"Spot '{spot.spot_id}' is full.", details={}
                )
            )

        base_price = prices.current_price(state.market, price_tracks, dope_type)
        price = skills.effective_trade_price(state, player, ActionType.SELL_DOPE, base_price)
        player.base_inventory.dope_counts[dope_type] -= 1
        player.money += price
        spot.sold_dope_tokens.append(dope_type)
        price_step_totals[dope_type] = price_step_totals.get(dope_type, 0) + 1
        sellers_by_spot.setdefault(spot.spot_id, []).append(pawn_id)

        _emit(
            state,
            events,
            DopeSold,
            player_id=command.player_id,
            pawn_id=pawn_id,
            spot_id=spot.spot_id,
            dope_type=dope_type,
            price_received=price,
        )

        if len(spot.sold_dope_tokens) >= spot.capacity:
            _clear_spot_and_spawn_fed(state, spot, events)

    from_base = skills.sell_link_from_base(state, player)
    pending_evolutions: list[PendingSaleLinkEvolution] = []
    for spot_id, seller_pawn_ids in sellers_by_spot.items():
        spot = state.board.spots[spot_id]
        # §C4 says "il Criminale che ha venduto può evolvere" — only ever
        # a Criminal converting *into* a Link, never a Link's own further
        # evolution (undefined by the rulebook). With a Link now able to
        # sell too (game designer, 2026-08-15), a spot's sellers can be a
        # mix; the resulting Link's *level* still counts every unit sold
        # to the spot in the package (§C4: "livello pari al numero di
        # merci vendute"), Link-sourced units included — only *which
        # pawn* gets converted needs to be a Criminal, so a Criminal
        # candidate (if any) is moved first without dropping anyone else
        # from the count. PROVISIONAL (RULES_PENDING.md): an all-Link
        # group at a spot skips the evolution offer entirely rather than
        # guessing at semantics for "a Link evolving" the rulebook never
        # describes.
        criminal_seller_ids = [
            pid for pid in seller_pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
        ]
        if not criminal_seller_ids:
            continue
        evolving_first = [criminal_seller_ids[0]] + [
            pid for pid in seller_pawn_ids if pid != criminal_seller_ids[0]
        ]
        if len(seller_pawn_ids) == 1:
            # §A5 (corrected 2026-08-02): a single-unit sale's Link
            # evolution is the player's own SI/NO choice — queued for an
            # interactive decision instead of applied here. Package
            # sales (>=2 units to the same Spot, below) stay automatic
            # per §C4's "si prende".
            pending_evolutions.append(
                PendingSaleLinkEvolution(
                    spot_id=spot_id, pawn_id=criminal_seller_ids[0], contact_id=spot.contact_id
                )
            )
            continue
        _evolve_sale_link(state, command.player_id, spot, evolving_first, from_base, events)

    price_steps = {dope_type: -count for dope_type, count in price_step_totals.items()}
    if pending_evolutions:
        # The package's own price step (and any Marketing "after" offer)
        # waits until every queued evolution choice is resolved — see
        # _handle_evolve_sale_link / turn_flow.py's PassOptionalStep
        # branch for WAITING_FOR_LINK_EVOLUTION_CHOICE, which apply it
        # once the queue drains.
        player.pending_sale_link_evolutions = pending_evolutions
        player.pending_sale_price_steps = price_steps
        state.active_step = ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE
    else:
        _finish_buy_or_sell_package(
            state, player, price_steps, events, stonk_count_by_card_id, price_tracks
        )
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _evolve_sale_link(
    state: GameState,
    player_id: PlayerId,
    spot: SalesSpotState,
    seller_pawn_ids: list[PawnId],
    from_base: bool,
    events: list[DomainEvent],
) -> None:
    if from_base:
        # §A10 Artisti-3 (confirmed by the game designer, 2026-08-02 —
        # replaces, not adds to, the default evolution below): a fresh
        # Covo pawn becomes the Link instead of the selling pawn, which
        # stays a Criminal in the Hood.
        player = find_player(state, player_id)
        fresh = next(
            (pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE), None
        )
        if fresh is not None:
            links.insert_link(
                state, player_id, fresh, spot.contact_id, len(seller_pawn_ids), events
            )
            return
        # §19 fallback (confirmed 2026-08-02): no free Covo pawn -> falls
        # back to evolving the selling pawn as usual, same as a player
        # without the Skill, instead of skipping the evolution.
    evolving_pawn_id = seller_pawn_ids[0]
    evolving_pawn = state.pawns[evolving_pawn_id]
    hood = state.board.hoods[evolving_pawn.location.hood_id]  # type: ignore[index]
    hood.criminal_pawn_ids.remove(evolving_pawn_id)
    links.insert_link(
        state, player_id, evolving_pawn_id, spot.contact_id, len(seller_pawn_ids), events
    )
    _check_hood_cop_removal(state, hood, events)


def _handle_evolve_sale_link(
    state: GameState,
    command: EvolveSaleLink,
    price_tracks: PriceTracks,
    stonk_count_by_card_id: dict[CardId, int],
) -> CommandOutcome:
    if state.phase != GamePhase.ACTION_PHASE:
        return CommandFailure(wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(wrong_player(str(state.current_player_id), str(command.player_id)))
    if state.active_step != ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message=(
                    f"Not waiting for a sale Link evolution choice "
                    f"(state is at '{state.active_step.value}')."
                ),
                details={"actual_step": state.active_step.value},
            )
        )
    player = find_player(state, command.player_id)
    if not player.pending_sale_link_evolutions:
        return CommandFailure(
            DomainError(
                code="no_pending_sale_link_evolution",
                message="No sale Link evolution choice is pending.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    entry = player.pending_sale_link_evolutions.pop(0)
    if command.evolve:
        spot = state.board.spots[entry.spot_id]
        from_base = skills.sell_link_from_base(state, player)
        _evolve_sale_link(state, command.player_id, spot, [entry.pawn_id], from_base, events)

    if not player.pending_sale_link_evolutions:
        price_steps = player.pending_sale_price_steps
        player.pending_sale_price_steps = {}
        _finish_buy_or_sell_package(
            state, player, price_steps, events, stonk_count_by_card_id, price_tracks
        )

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- ChooseMarketingCard ---------------------------------------------------


def _handle_choose_marketing_card(
    state: GameState,
    command: ChooseMarketingCard,
    stonk_count_by_card_id: dict[CardId, int],
) -> CommandOutcome:
    """Resolves the "which card" sub-step `_marketing_decision` only
    offers with 2+ eligible cards (game designer, 2026-08-15) — sets
    `PlayerState.marketing_chosen_card_id` so the next `get_legal_decision`
    call re-enters `_marketing_decision` with a single, already-chosen
    card and builds the familiar Stonk-allocation options for it."""
    if state.phase != GamePhase.ACTION_PHASE:
        return CommandFailure(wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(wrong_player(str(state.current_player_id), str(command.player_id)))
    if state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message=f"Not waiting for card usage (state is at '{state.active_step.value}').",
                details={"actual_step": state.active_step.value},
            )
        )

    player = find_player(state, command.player_id)
    stonk_count = stonk_count_by_card_id.get(command.card_id, 0)
    if command.card_id not in player.hand_card_ids or stonk_count <= 0:
        return CommandFailure(
            DomainError(
                code="card_not_eligible_for_marketing",
                message=f"Card '{command.card_id}' has no Stonk symbols or isn't in hand.",
                details={},
            )
        )

    state.revision += 1
    player.marketing_chosen_card_id = command.card_id
    return CommandSuccess(state=state, events=())


# --- PlayMarketingCard ----------------------------------------------------


def _handle_play_marketing_card(
    state: GameState,
    command: PlayMarketingCard,
    price_tracks: PriceTracks,
    stonk_count_by_card_id: dict[CardId, int],
    card_contact_by_id: dict[CardId, ContactId],
) -> CommandOutcome:
    if state.phase != GamePhase.ACTION_PHASE:
        return CommandFailure(wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(wrong_player(str(state.current_player_id), str(command.player_id)))
    if state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message=f"Not waiting for card usage (state is at '{state.active_step.value}').",
                details={"actual_step": state.active_step.value},
            )
        )

    player = find_player(state, command.player_id)
    stonk_count = stonk_count_by_card_id.get(command.card_id, 0)
    if command.card_id not in player.hand_card_ids or stonk_count <= 0:
        return CommandFailure(
            DomainError(
                code="card_not_eligible_for_marketing",
                message=f"Card '{command.card_id}' has no Stonk symbols or isn't in hand.",
                details={},
            )
        )
    if len(command.allocations) > stonk_count:
        return CommandFailure(
            DomainError(
                code="too_many_stonk_allocations",
                message=f"Card '{command.card_id}' only has {stonk_count} Stonk symbol(s).",
                details={"max": stonk_count, "given": len(command.allocations)},
            )
        )
    is_pre = player.marketing_offer_is_pre
    # §D3 (corrected 2026-08-02): "before" the action has no package yet
    # to restrict Dope types to; "after" restricts to the Dope types the
    # just-completed package actually handled.
    eligible_dope_types = None if is_pre else set(player.marketing_eligible_dope_types)
    for dope_type, delta in command.allocations:
        if eligible_dope_types is not None and dope_type not in eligible_dope_types:
            return CommandFailure(
                DomainError(
                    code="dope_type_not_in_package",
                    message=f"'{dope_type.value}' wasn't part of the just-completed package.",
                    details={},
                )
            )
        if delta not in (-1, 1):
            return CommandFailure(
                DomainError(
                    code="invalid_stonk_delta",
                    message="Each Stonk allocation must be +1 or -1.",
                    details={"given": delta},
                )
            )

    state.revision += 1
    events: list[DomainEvent] = []

    player.hand_card_ids.remove(command.card_id)
    player.marketing_chosen_card_id = None
    contact_id = card_contact_by_id[command.card_id]
    state.decks.customer_decks_by_contact[contact_id].discard_pile_card_ids.append(
        command.card_id
    )
    _emit(
        state,
        events,
        MarketingCardPlayed,
        player_id=command.player_id,
        card_id=command.card_id,
        allocations=command.allocations,
        is_pre=is_pre,
    )

    for dope_type, delta in command.allocations:
        _apply_price_step(state, price_tracks, dope_type, steps=delta, events=events)

    if is_pre:
        player.marketing_pre_allocations = command.allocations
        player.marketing_offer_is_pre = False
        return_step = player.marketing_pre_return_step
        assert return_step is not None
        player.marketing_pre_return_step = None
        state.active_step = return_step
    else:
        player.marketing_eligible_dope_types = []
        turn_flow.finish_action_or_extra(state, player, events)

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# Public aliases for cross-module reuse (rules/officers.py corrupts/moves
# the same Cops/Feds and reuses the same main-action-target validation
# and price-step application; rules/movement.py and rules/brawl.py reuse
# the card draw and Cop-removal-recheck helpers).
validate_action_targets = _validate_action_targets
spawn_cop = _spawn_cop
check_hood_cop_removal = _check_hood_cop_removal
find_spot = _find_spot
clear_spot_and_spawn_fed = _clear_spot_and_spawn_fed
apply_price_step = _apply_price_step
draw_card = _draw_card
