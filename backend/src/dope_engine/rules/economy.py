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

from typing import Any

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
    DopeSold,
    FedEnteredSpot,
    GamblerEvictedFromDen,
    HoodRestocked,
    MarketCrashed,
    MarketingCardPlayed,
    OfficerReturnedToReserve,
    PawnBecameGambler,
    PriceChanged,
    SpotCleared,
)
from dope_engine.domain.ids import (
    DEN_ID,
    JAIL_ID,
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
    max_pawns_per_player_per_hood,
    own_pawns_in_hood,
)
from dope_engine.rules import customer_cards, jail, links, prices, skills, turn_flow
from dope_engine.rules.event_utils import emit as _emit
from dope_engine.rules.event_utils import emit_skill_effects
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
    card_effect_by_id: dict[CardId, dict | None] | None = None,
    tile_by_id: dict[Any, Any] | None = None,
) -> None:
    tile_by_id = tile_by_id or {}
    stonk_count_by_card_id = stonk_count_by_card_id or {}
    card_effect_by_id = card_effect_by_id or {}
    bus.register(
        ChooseActionType,
        lambda s, c: _handle_choose_action_type(
            s,
            c,
            link_extra_action_types,
            action_type_by_card_id,
            card_contact_by_id,
            stonk_count_by_card_id,
            card_effect_by_id,
        ),
    )
    bus.register(PlaceCriminal, lambda s, c: _handle_place_criminal(s, c, tile_by_id))
    bus.register(MoveCriminal, _handle_move_criminal)
    bus.register(BuyDope, lambda s, c: _handle_buy_dope(s, c, price_tracks))
    bus.register(SellDope, lambda s, c: _handle_sell_dope(s, c, price_tracks))
    bus.register(
        EvolveSaleLink,
        lambda s, c: _handle_evolve_sale_link(s, c, price_tracks),
    )
    bus.register(
        PlayMarketingCard,
        lambda s, c: _handle_play_marketing_card(
            s,
            c,
            price_tracks,
            stonk_count_by_card_id,
            card_contact_by_id,
            action_type_by_card_id,
            card_effect_by_id,
        ),
    )
    bus.register(
        ChooseMarketingCard,
        lambda s, c: _handle_choose_marketing_card(s, c, stonk_count_by_card_id),
    )


# --- shared presence helpers -----------------------------------------

# CLAUDE.md §11.4/§11.5/§11.6 + game designer (2026-08-15): a Link counts
# as presence in every Hood of its own Contact for Buy/Sell eligibility,
# exactly like it already did for Cop/Fed maneuver (rules/officers.py).
# Owned here (not rules/officers.py, which already depends on this
# module) so both directions of the "buy/sell presence" and "maneuver
# presence" checks share one definition instead of drifting independently.


def has_presence_at_hood(state: GameState, pawn: PawnState, hood_id: HoodId) -> bool:
    if pawn.role == PawnRole.CRIMINAL:
        return pawn.location.hood_id == hood_id
    if pawn.role == PawnRole.LINK:
        # Bug report (2026-09-07): a Link's own Contact always has 2
        # Hoods (RULES_CANONICAL.md §F3 — one can start "covered", not
        # yet revealed to any player), but a Link's virtual presence must
        # never reach the *unrevealed* one — nothing legitimately happens
        # in a covered Hood yet (a Cop can only ever spawn there via
        # `rules/economy.py::_restock_hood`, which itself only runs on an
        # already-revealed Hood being emptied). Without this, buying an
        # in-Covo officer via such a Link (`_corrupt_officer_destination`'s
        # own Hood scan, `application/legal_actions.py`) could pick that
        # covered Hood as the purchase's destination — the officer then
        # sits somewhere with no board position to highlight, and a
        # later `_corrupt_officer_options` call offers it again as an
        # already-on-map officer nobody can actually click on the board
        # (reported symptom: "solo alcuni Cops vengono evidenziati").
        hood = state.board.hoods[hood_id]
        return hood.revealed and hood.contact_id == pawn.contact_id
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
    if player.followup_restriction is not None:
        # A card follow-up (cards 11/14/16/17/19) is always a single target.
        max_count = min(max_count, 1)
    if expected == ActionType.CORRUPT_OFFICER:
        # Officers are bought one at a time (see
        # `PlayerState.officer_corruptor_pawn_ids_this_action`): what's left
        # of the Grit budget, and never more than one per command.
        max_count = min(1, max_count - len(player.officer_corruptor_pawn_ids_this_action))
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


def _emit_cost_delta_skill(
    state: GameState, events: list[DomainEvent], player: PlayerState, action_type: ActionType
) -> None:
    """§A10 flat-cost Skills (Manager-2, Politici-1) always change the
    price actually paid whenever they apply, so "used" here just means
    "matched this action_type" — no further condition needed."""
    emit_skill_effects(
        state,
        events,
        player.player_id,
        skills.matching_skill_ids(
            state, player, "cost_delta", lambda e: action_type.value in e["action_types"]
        ),
    )


def _emit_extra_grit_skill_if_used(
    state: GameState,
    events: list[DomainEvent],
    player: PlayerState,
    action_type: ActionType,
    target_count: int,
) -> None:
    """§A10 "+1 Grinta" Skills only actually mattered this time if the
    package's target count needed the boost over the round's base Grit
    value — a boost the player didn't need to use isn't "used"."""
    if target_count > player.current_round_grit_value:  # type: ignore[operator]
        emit_skill_effects(
            state,
            events,
            player.player_id,
            skills.matching_skill_ids(
                state, player, "extra_grit", lambda e: action_type.value in e["action_types"]
            ),
        )


def _emit_trade_price_skill(
    state: GameState, events: list[DomainEvent], player: PlayerState
) -> None:
    """§A10 Artisti-2 changes every unit's buy/sell price, so "used"
    just means the player owns it — no action_type gating needed since
    the effect dict itself carries both directions' deltas."""
    emit_skill_effects(
        state,
        events,
        player.player_id,
        skills.matching_skill_ids(state, player, "trade_price_delta"),
    )


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


def den_draw_contact(state: GameState) -> ContactId:
    """The deck a pawn entering the Den draws from: a random Contact's (game designer,
    2026-10-16: "quando vai nel Den peschi una carta a caso") — not a choice."""
    rng = GameRandom.from_state(state.rng_state)
    contact_id = rng.sample(list(state.decks.customer_decks_by_contact), 1)[0]
    state.rng_state = rng.get_state()
    return contact_id


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
    """§C3 "ricaricato di 3 merci": the shared bank per Dope type
    (`data/dope_types.json::total_supply`) is finite, same as the
    physical component set — confirmed intentional by the game designer
    (2026-08-23, RULE_CHANGELOG.md) that a restock can come up short
    (even just 1 unit) once that type's bank runs low, rather than
    always guaranteeing 3."""
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


def _extreme_current_price(state: GameState, price_tracks: PriceTracks, extreme: str) -> int:
    """Cards 002/006/014/016 ("al prezzo della più cara/meno cara"): the
    current price of whichever Dope type is currently most/least
    expensive, in place of the type actually being bought/sold."""
    # The types in play come from the data (a simplified pack has 3, not 4).
    prices_by_type = [prices.current_price(state.market, price_tracks, dt) for dt in price_tracks]
    return max(prices_by_type) if extreme == "max" else min(prices_by_type)


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


def extremes_mode(state: GameState) -> bool:
    """"Easy Price" variant (game designer, 2026-10-20): prices no longer move with every
    purchase/sale/confiscation, only jump to an extreme when a Spot fills / a Hood empties,
    and by Marketing."""
    return state.configuration.get("price_change_mode") == "extremes"


def _price_tracks_of(state: GameState) -> PriceTracks:
    return {
        DopeType(dope_type): tuple(track)
        for dope_type, track in state.configuration["price_track_by_dope_type"].items()
    }


def set_price_extreme(
    state: GameState, dope_type: DopeType, extreme: str, events: list[DomainEvent]
) -> None:
    result = prices.set_price_extreme(state.market, _price_tracks_of(state), dope_type, extreme)
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


def apply_ordinary_price_step(
    state: GameState,
    price_tracks: PriceTracks,
    dope_type: DopeType,
    *,
    steps: int,
    events: list[DomainEvent],
) -> None:
    """The price step a purchase/sale/confiscation used to cause — none in the "Easy Price"
    variant."""
    if extremes_mode(state):
        return
    _apply_price_step(state, price_tracks, dope_type, steps=steps, events=events)


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


def _apply_self_arrest_boost(
    state: GameState, player: PlayerState, first_pawn_id: PawnId, events: list[DomainEvent]
) -> None:
    """Cards 001/005 "TRY AGAIN"/"HIGH HIGH" ("manda in prigione un tuo
    criminale che ha acquistato/venduto"): the first pawn (command order,
    same "position is equivalent" convention as RULES_PENDING.md #4) that
    took part in this Buy/Sell package is arrested right after the
    package resolves — deliberately *before* `_finish_buy_or_sell_package`
    clears `active_card_boost`, since that's the boost this check reads.
    Mirrors `rules/officers.py::_apply_arrest`'s own Cop/Fed split for
    what bookkeeping an arrest needs beyond `jail.arrest_pawn` itself: a
    Hood-located Criminal's own `criminal_pawn_ids` entry (plus a
    Cop-removal recheck), or a Link's Spot-Fed-removal recheck — nothing
    for a Gambler, since this pawn just bought/sold and can't be one."""
    boost = player.active_card_boost
    if boost is None or boost["type"] != "self_arrest_after_action":
        return
    pawn = state.pawns[first_pawn_id]
    if pawn.role == PawnRole.CRIMINAL:
        hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
        hood.criminal_pawn_ids.remove(first_pawn_id)
        jail.arrest_pawn(state, first_pawn_id, events)
        _check_hood_cop_removal(state, hood, events)
    else:
        contact_id = pawn.contact_id
        jail.arrest_pawn(state, first_pawn_id, events)
        if contact_id is not None:
            links.check_spot_fed_removal_for_contact(state, contact_id, events)


def _finish_buy_or_sell_package(
    state: GameState,
    player: PlayerState,
    price_steps: dict[DopeType, int],
    events: list[DomainEvent],
    price_tracks: PriceTracks,
) -> None:
    """§D3 Marketing (2026-08-17 decision: Marketing can only be played
    *before* the whole Buy/Sell action, never after — RULES_CANONICAL.md
    §D3 updated, superseding the 2026-08-02 "before or after" version;
    game designer: playtesting showed "after" never made sense to reach
    for once the package's own price step had already moved the price).
    The package's own automatic price step (`price_steps`, already
    signed — positive for Buy, negative for Sell) always applies
    immediately. If the player used Marketing "before" this action, a
    Manager-3 owner gets those same allocations replayed here
    automatically (no new card, §A10) — everyone else's one "before"
    shot, once used, is already fully spent; if it was never used, it's
    simply gone once the package resolves, with no further offer."""
    arrest_pawn_id = player.pending_self_arrest_pawn_id
    player.pending_self_arrest_pawn_id = None
    if arrest_pawn_id is not None:
        _apply_self_arrest_boost(state, player, arrest_pawn_id, events)

    for dope_type, steps in price_steps.items():
        apply_ordinary_price_step(state, price_tracks, dope_type, steps=steps, events=events)
    # "Easy Price": the Hoods this package emptied / Spots it filled, in the order they happened.
    pending_extremes, player.pending_price_extremes = player.pending_price_extremes, ()
    for extreme_dope_type, extreme in pending_extremes:
        set_price_extreme(state, extreme_dope_type, extreme, events)

    if player.marketing_pre_allocations:
        if skills.marketing_applies_both_timings(state, player):
            for dope_type, delta in player.marketing_pre_allocations:
                _apply_price_step(state, price_tracks, dope_type, steps=delta, events=events)
            emit_skill_effects(
                state,
                events,
                player.player_id,
                skills.matching_skill_ids(state, player, "double_stonk"),
            )
        player.marketing_pre_allocations = ()

    if _begin_card_followup(state, player):
        return
    turn_flow.finish_action_or_extra(state, player, events)


_FOLLOWUP_KIND_BY_BOOST_TYPE = {
    "after_trade_place": "place",
    "after_trade_den": "den",
    "after_trade_move": "move",
}


def _begin_card_followup(state: GameState, player: PlayerState) -> bool:
    """Cards 11/19 (place), 14/16 (Den) and 17 (move) — game designer, 2026-10-15: once the
    Buy/Sell package is done, the card's follow-up runs as an ordinary one-target Place/Move
    action restricted to where/who traded; the card was played on purpose, so it is
    mandatory whenever it can be done. Returns whether a follow-up was started (the action
    then stays open until it is resolved); a follow-up that cannot be done is skipped."""
    boost = player.active_card_boost
    kind = _FOLLOWUP_KIND_BY_BOOST_TYPE.get(boost["type"]) if boost is not None else None
    if kind is None or not _followup_feasible(state, player, kind):
        return False
    player.followup_restriction = {
        "kind": kind,
        "hood_ids": list(player.trade_hood_ids),
        "pawn_ids": list(player.trade_pawn_ids),
    }
    player.pending_action_type = (
        ActionType.PLACE_CRIMINAL if kind == "place" else ActionType.MOVE_CRIMINAL
    )
    state.active_step = (
        ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
        if player.extra_action_link_pawn_id is not None
        else ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    )
    return True


def _followup_feasible(state: GameState, player: PlayerState, kind: str) -> bool:
    criminals = [
        pid
        for pid in player.trade_pawn_ids
        if state.pawns[pid].role == PawnRole.CRIMINAL
        and pid not in player.moved_pawn_ids_this_turn
    ]
    if kind == "place":
        cost = skills.effective_cost(
            state, player, ActionType.PLACE_CRIMINAL, state.configuration["costs"]["place_criminal"]
        )
        has_pawn = any(state.pawns[pid].role == PawnRole.IN_BASE for pid in player.pawn_ids)
        limit = state.configuration["brawl_trigger_criminal_count"] - 1
        return (
            has_pawn
            and player.money >= cost
            and any(
                hood_id in state.board.hoods
                and state.board.hoods[hood_id].revealed
                and len(state.board.hoods[hood_id].criminal_pawn_ids) < limit
                and own_pawns_in_hood(state, player.player_id, hood_id)
                < max_pawns_per_player_per_hood(state.configuration)
                for hood_id in player.trade_hood_ids
            )
        )
    if kind == "den":
        own_in_den = sum(
            1
            for pid in state.board.den_gambler_pawn_ids
            if state.pawns[pid].owner_player_id == player.player_id
        )
        return (
            bool(criminals)
            and len(state.board.den_gambler_pawn_ids) < state.configuration["den_capacity"]
            and own_in_den < state.configuration["den_capacity_per_player"]
        )
    # "move": an adjacent revealed Hood with room
    for pid in criminals:
        hood = state.board.hoods[state.pawns[pid].location.hood_id]  # type: ignore[index]
        for adjacent_id in hood.adjacent_hood_ids:
            adjacent = state.board.hoods[adjacent_id]
            if (
                adjacent.revealed
                and len(adjacent.criminal_pawn_ids) < adjacent.capacity
                and own_pawns_in_hood(state, player.player_id, adjacent_id)
                < max_pawns_per_player_per_hood(state.configuration)
            ):
                return True
    return False


def _followup_violation(
    player: PlayerState, *, hoods=(), moves=(), purchases=()
) -> DomainError | None:
    """A card follow-up's own restriction (see `_begin_card_followup`), validated here
    as well as offered by the legal-action generator (CLAUDE.md §10)."""
    restriction = player.followup_restriction
    if restriction is None:
        return None
    kind = restriction["kind"]
    ok = True
    if kind == "place":
        ok = all(hood_id in restriction["hood_ids"] for hood_id in hoods)
    elif kind == "buy":
        ok = all(
            pawn_id in restriction["pawn_ids"] and hood_id in restriction["hood_ids"]
            for pawn_id, hood_id in purchases
        )
    else:
        for pawn_id, destination in moves:
            if pawn_id not in restriction["pawn_ids"]:
                ok = False
            if (kind == "den") != (destination == DEN_ID) or destination == JAIL_ID:
                ok = False
    if ok:
        return None
    return DomainError(
        code="followup_restriction_violated",
        message="This card's follow-up only allows the pawns/Hoods where you traded.",
        details={},
    )


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
    action or, per the same confirmation, a Link's extra action).

    §D2 (2026-09-04 redesign): the single Gamble slot is shared by the
    whole table for the round — once anyone has launched a match this
    round, `state.poker.current_match` is set and stays set until that
    match resolves at round end, so nobody else (including the launcher)
    can launch a second one."""
    if state.poker.current_match is not None:
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
    card_effect_by_id: dict[CardId, dict | None],
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
    player.maneuvered_pawn_ids_this_action = []
    player.officer_corruptor_pawn_ids_this_action = []
    player.marketing_cards_played_this_action = 0
    player.marketing_after_boost = False
    if state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS:
        player.action_types_used_this_turn.append(action_type)
    events: list[DomainEvent] = []
    _emit(
        state, events, ActionTypeChosen, player_id=command.player_id, action_type=action_type.value
    )

    if _player_can_launch_poker_for_action(
        state, player, action_type, action_type_by_card_id, card_contact_by_id
    ):
        # A player eligible for both a Poker launch and Marketing on this
        # same action (a matching Preti card AND a Stonk card in hand)
        # gets the Poker offer first — Marketing, if still eligible, is
        # offered right after it resolves, via
        # `turn_flow.resume_after_poker_launch_offer` (game designer,
        # 2026-08-24: confirmed both should be offered in sequence, not
        # just one).
        player.poker_launch_return_step = state.active_step
        state.active_step = ActiveStep.WAITING_FOR_POKER_LAUNCH
    elif action_type in (ActionType.BUY_DOPE, ActionType.SELL_DOPE) and any(
        stonk_count_by_card_id.get(cid, 0) > 0 for cid in player.hand_card_ids
    ):
        # §D3 Marketing (corrected 2026-08-02): "before the whole
        # action" is offered here, the same way a Poker launch is.
        player.marketing_pre_return_step = state.active_step
        player.marketing_offer_is_pre = True
        state.active_step = ActiveStep.WAITING_FOR_CARD_USAGE
    else:
        # Chained last (game designer, 2026-08-27): a Card Boost only
        # gets offered here directly when the player wasn't already
        # eligible for a Poker launch or Marketing this action — either
        # of those, once resolved, re-checks Boost eligibility itself
        # (`customer_cards.offer_boost_or_resume`) before finally
        # resuming target selection.
        customer_cards.offer_boost_or_resume(
            state, player, state.active_step, card_effect_by_id, action_type_by_card_id
        )

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- PlaceCriminal ----------------------------------------------------------


def _handle_place_criminal(
    state: GameState, command: PlaceCriminal, tile_by_id: dict[Any, Any] | None = None
) -> CommandOutcome:
    error, player = _validate_action_targets(
        state, command.player_id, ActionType.PLACE_CRIMINAL, len(command.hood_ids)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    violation = _followup_violation(player, hoods=command.hood_ids)
    if violation is not None:
        return CommandFailure(violation)

    cost_each = skills.effective_cost(
        state, player, ActionType.PLACE_CRIMINAL, state.configuration["costs"]["place_criminal"]
    )
    total_cost = sum(
        placement_cost(state, player, hood_id, cost_each) for hood_id in command.hood_ids
    )
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
    # Cards 043/045 ("un criminale puoi piazzarlo in prigione") and
    # 054/059 "BIG RAT" ("...se c'è Evasione, non evade", game designer,
    # 2026-08-31): the `JAIL_ID` sentinel (mirrors rules/movement.py's
    # own `move_to_jail` handling of the same sentinel) — only legal at
    # all when one of these two boosts is active, and never subject to
    # the Hood existence/revealed/capacity checks below (the Jail is
    # never "full" per RULES_PENDING.md #15, so there's nothing to cap).
    boost = player.active_card_boost
    place_to_jail = boost is not None and boost["type"] == "place_to_jail"
    # Cards 048/055 "GO GAMBLE" ("puoi piazzare fino a due pedine nel
    # Den") and 042/057 "NO GAMBLE" ("piazza una pedina nel Den e rimuovi
    # una pedina nemica", game designer, 2026-08-31): `PlaceCriminal` can
    # normally never target the Den at all (only `MoveCriminal` can) —
    # `max_den_placements` caps how many of *this* package's targets may
    # be `DEN_ID`, on top of (not instead of) the normal Grit-based
    # package size; the rest of a larger package still needs real Hoods.
    place_in_den_evict = boost is not None and boost["type"] == "place_in_den_evict_enemy"
    place_in_den = place_in_den_evict or (boost is not None and boost["type"] == "place_in_den")
    max_den_placements = 1 if place_in_den_evict else (2 if place_in_den else 0)
    den_placement_count = 0
    hidden_hood_count = 0
    den_deck_index = 0
    remaining_den = state.configuration["den_capacity"] - len(state.board.den_gambler_pawn_ids)
    own_gamblers_in_den = sum(
        1
        for pid in state.board.den_gambler_pawn_ids
        if state.pawns[pid].owner_player_id == command.player_id
    )
    remaining_den_for_player = state.configuration["den_capacity_per_player"] - own_gamblers_in_den
    needed_per_hood: dict[HoodId, int] = {}
    for hood_id in command.hood_ids:
        if hood_id == JAIL_ID:
            if not place_to_jail:
                return CommandFailure(
                    DomainError(
                        code="unknown_hood", message=f"Unknown Hood '{hood_id}'.", details={}
                    )
                )
            continue
        if hood_id == DEN_ID:
            den_placement_count += 1
            if den_placement_count > max_den_placements:
                return CommandFailure(
                    DomainError(
                        code="unknown_hood", message=f"Unknown Hood '{hood_id}'.", details={}
                    )
                )
            if den_placement_count > remaining_den:
                return CommandFailure(
                    DomainError(code="den_full", message="The Den is full.", details={})
                )
            if den_placement_count > remaining_den_for_player:
                return CommandFailure(
                    DomainError(
                        code="den_full_for_player",
                        message="You already have the maximum number of pawns in the Den.",
                        details={},
                    )
                )
            continue
        if hood_id not in state.board.hoods:
            return CommandFailure(
                DomainError(code="unknown_hood", message=f"Unknown Hood '{hood_id}'.", details={})
            )
        if not state.board.hoods[hood_id].revealed:
            # Only a Brawl loser's relocation can reach an unrevealed
            # Hood (game designer, 2026-08-16) — and cards 46/58 "SCOUT", for one pawn.
            hidden_hood_count += 1
            if (
                boost is not None
                and boost["type"] == "place_in_hidden_hood"
                and hidden_hood_count == 1
            ):
                needed_per_hood[hood_id] = 1
                continue
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
        own_remaining = max_pawns_per_player_per_hood(state.configuration) - own_pawns_in_hood(
            state, command.player_id, hood_id
        )
        if needed > own_remaining:
            return CommandFailure(
                DomainError(
                    code="player_hood_limit_exceeded",
                    message=(
                        f"A player may have at most "
                        f"{max_pawns_per_player_per_hood(state.configuration)} pawns in Hood "
                        f"'{hood_id}'."
                    ),
                    details={"remaining_for_player": max(0, own_remaining)},
                )
            )

    state.revision += 1
    player.money -= total_cost
    events: list[DomainEvent] = []
    _emit_cost_delta_skill(state, events, player, ActionType.PLACE_CRIMINAL)
    _emit_extra_grit_skill_if_used(
        state, events, player, ActionType.PLACE_CRIMINAL, len(command.hood_ids)
    )
    placed_pawn_ids = available_pawns[: len(command.hood_ids)]
    den_deck_index = 0
    # Cards 053/058 "SHORTCUT" ("un criminale puoi piazzarlo su un
    # Gancio", game designer, 2026-08-31, confirmed: creates a *new*
    # level-1 Link at the chosen Hood's own Contact, rather than
    # boosting an existing one) — "un criminale" (singular) means at
    # most 1 placement in the whole package takes this shortcut, same
    # "position is equivalent" convention as RULES_PENDING.md #4; every
    # other target in the same package still places as a normal Criminal.
    shortcut_link_used = False
    free_hood_ids = {
        hood_id
        for hood_id in command.hood_ids
        if placement_cost(state, player, hood_id, cost_each) == 0 < cost_each
    }
    for pawn_id, hood_id in zip(placed_pawn_ids, command.hood_ids, strict=True):
        pawn = state.pawns[pawn_id]
        if hood_id == DEN_ID:
            # Cards 048/055 "GO GAMBLE" / 042/057 "NO GAMBLE" ("puoi
            # piazzare... nel Den", game designer, 2026-08-31): same
            # Den-entry effects as `MoveCriminal`'s own Den branch
            # (`rules/movement.py`) — role/location/roster/draw — just
            # reached directly from the Covo instead of via a Hood.
            deck_contact_id = (
                command.den_deck_contact_ids[den_deck_index]
                if den_deck_index < len(command.den_deck_contact_ids)
                else None
            ) or den_draw_contact(state)
            den_deck_index += 1
            pawn.role = PawnRole.GAMBLER
            pawn.location = PawnLocation.den()
            state.board.den_gambler_pawn_ids.append(pawn_id)
            _emit(state, events, PawnBecameGambler, player_id=command.player_id, pawn_id=pawn_id)
            _draw_card(state, deck_contact_id, events, command.player_id)
            if place_in_den_evict:
                # "rimuovi una pedina nemica" — automatic/best-effort:
                # no new interactive decision, no-op if no enemy Gambler
                # is currently in the Den (same "secondary automatic
                # effect" philosophy as `self_arrest_after_action` /
                # `arrest_extra_target` / `confiscate_extra_unit`).
                enemy_gambler_id = next(
                    (
                        pid
                        for pid in state.board.den_gambler_pawn_ids
                        if state.pawns[pid].owner_player_id != command.player_id
                    ),
                    None,
                )
                if enemy_gambler_id is not None:
                    enemy_pawn = state.pawns[enemy_gambler_id]
                    state.board.den_gambler_pawn_ids.remove(enemy_gambler_id)
                    enemy_pawn.role = PawnRole.IN_BASE
                    enemy_pawn.location = PawnLocation.base()
                    _emit(
                        state,
                        events,
                        GamblerEvictedFromDen,
                        player_id=enemy_pawn.owner_player_id,
                        pawn_id=enemy_gambler_id,
                    )
            continue
        if hood_id == JAIL_ID:
            # Cards 043/045 — straight from the Covo to a Rat, no Hood
            # stop in between (jail.arrest_pawn is role-agnostic: it only
            # ever *sets* role/contact_id/link_level/location, it doesn't
            # branch on what they were beforehand, so `IN_BASE` works
            # exactly like a Criminal/Link would). No card draw — there's
            # no Contact deck a Jail slot belongs to. Cards 054/059's own
            # immunity flag must be set *before* the call below — if this
            # placement itself fills the last free slot, `arrest_pawn` resolves
            # Evasion synchronously, and that check reads the flag.
            jail.arrest_pawn(state, pawn_id, events)
            continue
        hood = state.board.hoods[hood_id]
        if not hood.revealed:
            from dope_engine.rules import brawl

            brawl.reveal_covered_hood(state, hood, events, tile_by_id or {})
        if (
            boost is not None
            and boost["type"] == "shortcut_place_as_link"
            and not shortcut_link_used
        ):
            shortcut_link_used = True
            links.insert_link(state, command.player_id, pawn_id, hood.contact_id, 1, events)
        else:
            pawn.role = PawnRole.CRIMINAL
            pawn.location = PawnLocation.hood(hood_id)
            hood.criminal_pawn_ids.append(pawn_id)
            _emit(
                state,
                events,
                CriminalPlaced,
                player_id=command.player_id,
                pawn_id=pawn_id,
                hood_id=hood_id,
                cost=0 if hood_id in free_hood_ids else cost_each,
            )
        # Cards 041/049 "REINFORCE" ("piazzi 2 per ogni Grinta, ma non
        # peschi carte") suppress the normal per-pawn draw entirely — the
        # target-count *doubling* half of this same card lives in
        # `rules/skills.py::effective_action_count` instead, since that's
        # what both the option generator and this handler's own
        # `_validate_action_targets` already share.
        if boost is not None and boost["type"] in ("place_double_no_draw", "place_then_buy"):
            pass
        else:
            _draw_card(state, hood.contact_id, events, command.player_id)
            if boost is not None and boost["type"] == "bonus_card_draw_per_unit":
                # Cards 046/050 "MAKE FRIENDS" ("prendi 2 carte per ogni
                # criminale piazzato" — 2 *total*, confirmed by the user,
                # 2026-09-02: `data/customer_cards.json`'s own `count`
                # used to be 2, on top of the normal draw just above,
                # giving 3 total instead of the card's own printed 2 —
                # `count` is *additional* draws beyond the one normal
                # draw every placement already does, so it's 1, not 2):
                # extra draws from the same Contact deck as this
                # placement's own normal draw, per pawn placed.
                for _ in range(boost["count"]):
                    _draw_card(state, hood.contact_id, events, command.player_id)

    placed_criminals = [
        (pid, hid)
        for pid, hid in zip(placed_pawn_ids, command.hood_ids, strict=True)
        if state.pawns[pid].role == PawnRole.CRIMINAL
    ]
    if not _begin_place_card_followup(state, player, placed_criminals):
        turn_flow.finish_action_or_extra(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def player_has_presence(state: GameState, player: PlayerState, hood_id: HoodId) -> bool:
    return any(
        state.pawns[pid].role in (PawnRole.CRIMINAL, PawnRole.LINK)
        and has_presence_at_hood(state, state.pawns[pid], hood_id)
        for pid in player.pawn_ids
    )


def placement_cost(state: GameState, player: PlayerState, hood_id: HoodId, cost_each: int) -> int:
    """Card 44 "HOME TURF" (game designer, 2026-10-15): a pawn placed where the player already
    has presence (a Link counts) is free, the others pay as usual."""
    boost = player.active_card_boost
    if (
        boost is not None
        and boost["type"] == "place_free_where_present"
        and hood_id in state.board.hoods
        and player_has_presence(state, player, hood_id)
    ):
        return 0
    return cost_each


def _begin_place_card_followup(
    state: GameState, player: PlayerState, placed: list[tuple[PawnId, HoodId]]
) -> bool:
    """Cards 50 "BADGE HIRE" (corrupt a Cop), 51/57 "EXPANSION"/"FLASH MOB" (move a placed
    pawn), 52/55 "STASH"/"SUPPLY DROP" (a placed pawn may buy) and 54 "DECOY" (a Cop enters)
    — game designer, 2026-10-15: what follows the placement package, about the pawns just
    placed. Returns whether a follow-up step was opened."""
    boost = player.active_card_boost
    if boost is None or not placed:
        return False
    pawn_ids = [pid for pid, _ in placed]
    hood_ids = list(dict.fromkeys(hid for _, hid in placed))
    kind = boost["type"]
    if kind == "place_then_buy":
        if not any(
            state.board.hoods[hid].dope_stack and not state.board.hoods[hid].cop_ids
            for hid in hood_ids
        ):
            return False
        player.followup_restriction = {
            "kind": "buy",
            "hood_ids": hood_ids,
            "pawn_ids": pawn_ids,
            "optional": True,
        }
        player.pending_action_type = ActionType.BUY_DOPE
        state.active_step = (
            ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
            if player.extra_action_link_pawn_id is not None
            else ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
        )
        return True
    entries: dict[str, dict[str, Any]] = {
        "place_then_corrupt_cop": {"kind": "badge_hire", "hood_ids": hood_ids},
        "place_then_move": {"kind": "expansion", "pawn_ids": pawn_ids},
        "place_then_decoy": {"kind": "decoy", "hood_ids": hood_ids, "mandatory": True},
    }
    entry = entries.get(kind)
    if entry is None:
        return False
    from dope_engine.rules import move_followups

    player.pending_move_followups.append(entry)
    return move_followups.begin(state, player)


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
    violation = _followup_violation(player, moves=[(m[0], m[1]) for m in command.moves])
    if violation is not None:
        return CommandFailure(violation)

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

    # Cards 032/036 "PLAY!!": `extra_den_deck_contact_ids` is a parallel
    # tuple, one entry per `DEN_ID` move in `command.moves` (left to
    # right) — zipped onto its matching move here, once, so the rest of
    # the movement pipeline (including a Brawl pausing/resuming this same
    # queue) only ever deals with one already-aligned 4-tuple per move,
    # never a separate index to keep in sync.
    extra_index = 0
    queue: list[tuple[PawnId, HoodId, ContactId | None, ContactId | None]] = []
    for pawn_id, destination, deck_contact_id in command.moves:
        extra_deck_contact_id = None
        if destination == DEN_ID and extra_index < len(command.extra_den_deck_contact_ids):
            extra_deck_contact_id = command.extra_den_deck_contact_ids[extra_index]
            extra_index += 1
        queue.append((pawn_id, destination, deck_contact_id, extra_deck_contact_id))

    return movement.process_move_queue(state, command.player_id, player, queue, events)


# --- BuyDope ------------------------------------------------------------


def _handle_buy_dope(
    state: GameState,
    command: BuyDope,
    price_tracks: PriceTracks,
) -> CommandOutcome:
    error, player = _validate_action_targets(
        state, command.player_id, ActionType.BUY_DOPE, len(command.purchases)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    violation = _followup_violation(player, purchases=command.purchases)
    if violation is not None:
        return CommandFailure(violation)

    boost = player.active_card_boost
    # Card 007 ("acquisti fino a 3 merci con un criminale"): one pawn can
    # appear up to `max_repeats` times in the same package instead of the
    # usual "once per pawn" — see legal_actions.py::_buy_dope_options'
    # matching option duplication.
    repeat_cap = (
        boost["max_repeats"] if boost is not None and boost["type"] == "repeat_pawn_target" else 1
    )
    pawn_counts: dict[PawnId, int] = {}
    for pawn_id, _ in command.purchases:
        pawn_counts[pawn_id] = pawn_counts.get(pawn_id, 0) + 1
    if any(count > repeat_cap for count in pawn_counts.values()):
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
    _emit_extra_grit_skill_if_used(
        state, events, player, ActionType.BUY_DOPE, len(command.purchases)
    )
    _emit_trade_price_skill(state, events, player)
    # Cards 004/017 — see legal_actions.py::_buy_dope_options' own
    # matching bypasses (board-adjacent Hood vs. own-Contact's other
    # Hood — two different reaches, not interchangeable).
    buy_adjacent = boost is not None and boost["type"] == "adjacent_hood_presence"

    for pawn_id, hood_id in command.purchases:
        pawn = state.pawns.get(pawn_id)
        extra_reach = False
        if pawn is not None and pawn.role == PawnRole.CRIMINAL and hood_id in state.board.hoods:
            own_hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
            if buy_adjacent:
                extra_reach = hood_id in own_hood.adjacent_hood_ids
        eligible = (
            pawn is not None
            and pawn.owner_player_id == command.player_id
            and pawn.role in (PawnRole.CRIMINAL, PawnRole.LINK)
            and hood_id in state.board.hoods
            and (has_presence_at_hood(state, pawn, hood_id) or extra_reach)
        )
        if not eligible:
            return CommandFailure(
                DomainError(
                    code="pawn_not_eligible",
                    message=f"Pawn '{pawn_id}' cannot buy Dope at Hood '{hood_id}'.",
                    details={},
                )
            )
        assert pawn is not None  # narrowed by `eligible` above
        hood = state.board.hoods[hood_id]
        if hood.cop_ids and not (boost is not None and boost["type"] == "ignore_officer_block"):
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
        if boost is not None and boost["type"] == "price_at_extreme":
            base_price = _extreme_current_price(state, price_tracks, boost["extreme"])
        else:
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
        # §11.4/RULES_PENDING.md #26 (resolved by the game designer,
        # 2026-08-23): the Covo's 3-per-type cap *blocks* a purchase that
        # would exceed it — it doesn't let the purchase happen and then
        # discard the Dope afterward. Same atomic-per-command semantics
        # as every other check in this loop (`hood_has_no_dope`,
        # `insufficient_funds`): a command whose *own* package requests
        # too much of one type fails as a whole, not just this one unit
        # — a legal package instead picks fewer of the capped type and
        # fills the rest with something else (`_buy_dope_options`
        # already offers every option unbudgeted, same as Hood stock;
        # `bots/random_legal.py::_pick_buy_dope_options` budgets this
        # the same way it already budgets Hood stock).
        if player.base_inventory.dope_counts.get(dope_type, 0) >= 3:
            return CommandFailure(
                DomainError(
                    code="base_inventory_full",
                    message=f"Covo already holds 3 {dope_type.value}.",
                    details={"dope_type": dope_type.value},
                )
            )

        player.money -= price
        hood.dope_stack.pop()
        if extremes_mode(state) and not hood.dope_stack:
            player.pending_price_extremes += ((dope_type, "max"),)
        price_step_totals[dope_type] = price_step_totals.get(dope_type, 0) + 1
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

    player.pending_self_arrest_pawn_id = command.purchases[0][0]
    player.trade_pawn_ids = list(dict.fromkeys(pid for pid, _ in command.purchases))
    player.trade_hood_ids = list(dict.fromkeys(hid for _, hid in command.purchases))
    price_steps = dict(price_step_totals)
    _finish_buy_or_sell_package(state, player, price_steps, events, price_tracks)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- SellDope -----------------------------------------------------------


def _handle_sell_dope(
    state: GameState,
    command: SellDope,
    price_tracks: PriceTracks,
) -> CommandOutcome:
    error, player = _validate_action_targets(
        state, command.player_id, ActionType.SELL_DOPE, len(command.sales)
    )
    if error is not None or player is None:
        return CommandFailure(error)  # type: ignore[arg-type]

    boost = player.active_card_boost
    # Card 015 ("vendi fino a 3 merci con un criminale") — see
    # `_handle_buy_dope`'s matching comment for card 007; same shape,
    # applied to Sell instead of Buy.
    repeat_cap = (
        boost["max_repeats"] if boost is not None and boost["type"] == "repeat_pawn_target" else 1
    )
    pawn_counts: dict[PawnId, int] = {}
    for pid, _ in command.sales:
        pawn_counts[pid] = pawn_counts.get(pid, 0) + 1
    if any(count > repeat_cap for count in pawn_counts.values()):
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
    _emit_extra_grit_skill_if_used(state, events, player, ActionType.SELL_DOPE, len(command.sales))
    _emit_trade_price_skill(state, events, player)
    explicit_spot_by_sale: dict[tuple[PawnId, DopeType], SpotId] = {
        (pid, dt): spot_id for pid, dt, spot_id in command.explicit_spots
    }

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
        explicit_spot_id = explicit_spot_by_sale.get((pawn_id, dope_type))
        if explicit_spot_id is not None:
            # Card 012 ("vendi in un quartiere adiacente"): the client
            # names the Spot directly rather than leaving it to be
            # derived from the pawn's own Hood/Contact — the only way to
            # know which one was meant once `sell_adjacent` below makes
            # more than one reachable. Still fully validated: presence
            # (own Contact, or an adjacent Hood's Contact when boosted)
            # and that it actually accepts `dope_type`.
            spot = state.board.spots.get(explicit_spot_id)
            if spot is None or spot.accepted_dope_type != dope_type:
                return CommandFailure(
                    DomainError(
                        code="dope_type_not_accepted",
                        message=f"Spot '{explicit_spot_id}' does not accept {dope_type.value}.",
                        details={},
                    )
                )
            sell_adjacent = boost is not None and boost["type"] == "adjacent_hood_presence"
            has_presence = has_presence_at_spot(state, pawn, spot.spot_id)
            if not has_presence and sell_adjacent and pawn.role == PawnRole.CRIMINAL:
                own_hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
                has_presence = any(
                    state.board.hoods[adj_id].contact_id == spot.contact_id
                    for adj_id in own_hood.adjacent_hood_ids
                )
            if not has_presence:
                return CommandFailure(
                    DomainError(
                        code="pawn_not_eligible",
                        message=f"Pawn '{pawn_id}' cannot sell Dope at Spot '{explicit_spot_id}'.",
                        details={},
                    )
                )
        else:
            # A Link's presence isn't Hood-scoped at all
            # (has_presence_at_spot, game designer 2026-08-15) — its own
            # contact_id finds the Spot directly, no Hood lookup needed;
            # a Criminal's still comes from its current Hood, same as
            # before.
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
        if spot.fed_ids and not (boost is not None and boost["type"] == "ignore_officer_block"):
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
                DomainError(code="spot_full", message=f"Spot '{spot.spot_id}' is full.", details={})
            )

        if boost is not None and boost["type"] == "price_at_extreme":
            base_price = _extreme_current_price(state, price_tracks, boost["extreme"])
        else:
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
            if extremes_mode(state):
                player.pending_price_extremes += ((spot.accepted_dope_type, "min"),)
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
        # Card 015 ("vendi fino a 3 merci con un criminale"): the same
        # pawn can appear more than once in `seller_pawn_ids` now, so
        # this can't filter by `!=` (that would drop *every* occurrence
        # of the chosen pawn, undercounting the Link's own level below,
        # which must still equal the total units sold) — `list.remove`
        # only takes out the one instance being moved to the front.
        remaining_sellers = list(seller_pawn_ids)
        remaining_sellers.remove(criminal_seller_ids[0])
        evolving_first = [criminal_seller_ids[0]] + remaining_sellers
        if len(seller_pawn_ids) == 1 or (
            boost is not None and boost["type"] == "sale_link_any_contact"
        ):
            # §A5 (corrected 2026-08-02): a single-unit sale's Link
            # evolution is the player's own SI/NO choice — queued for an
            # interactive decision instead of applied here. Package
            # sales (>=2 units to the same Spot, below) stay automatic
            # per §C4's "si prende".
            pending_evolutions.append(
                PendingSaleLinkEvolution(
                    spot_id=spot_id,
                    pawn_id=criminal_seller_ids[0],
                    contact_id=spot.contact_id,
                    level=len(seller_pawn_ids),
                )
            )
            continue
        _evolve_sale_link(
            state, command.player_id, spot.contact_id, evolving_first, from_base, events
        )

    player.pending_self_arrest_pawn_id = command.sales[0][0]
    player.trade_pawn_ids = list(dict.fromkeys(pid for pid, _ in command.sales))
    player.trade_hood_ids = list(
        dict.fromkeys(
            hood_id
            for pid, _ in command.sales
            if state.pawns[pid].role == PawnRole.CRIMINAL
            and (hood_id := state.pawns[pid].location.hood_id) is not None
        )
    )
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
        _finish_buy_or_sell_package(state, player, price_steps, events, price_tracks)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _evolve_sale_link(
    state: GameState,
    player_id: PlayerId,
    contact_id: ContactId,
    seller_pawn_ids: list[PawnId],
    from_base: bool,
    events: list[DomainEvent],
    *,
    level: int | None = None,
) -> None:
    link_level = level if level is not None else len(seller_pawn_ids)
    boost = find_player(state, player_id).active_card_boost
    if boost is not None and boost["type"] == "sale_link_level":
        # Card 13 "SPREADING" (game designer, 2026-10-15): "prendi un Link 3" — the new Link
        # takes level 3, pushing out whoever holds it (`links.insert_link` returns that
        # pawn to its owner's Covo).
        link_level = boost["level"]
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
            links.insert_link(state, player_id, fresh, contact_id, link_level, events)
            emit_skill_effects(
                state,
                events,
                player_id,
                skills.matching_skill_ids(state, player, "link_from_base_on_sell"),
            )
            return
        # §19 fallback (confirmed 2026-08-02): no free Covo pawn -> falls
        # back to evolving the selling pawn as usual, same as a player
        # without the Skill, instead of skipping the evolution.
    evolving_pawn_id = seller_pawn_ids[0]
    evolving_pawn = state.pawns[evolving_pawn_id]
    hood = state.board.hoods[evolving_pawn.location.hood_id]  # type: ignore[index]
    hood.criminal_pawn_ids.remove(evolving_pawn_id)
    links.insert_link(state, player_id, evolving_pawn_id, contact_id, link_level, events)
    _check_hood_cop_removal(state, hood, events)


def _handle_evolve_sale_link(
    state: GameState,
    command: EvolveSaleLink,
    price_tracks: PriceTracks,
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
    contact_id = entry.contact_id
    if command.evolve and command.contact_id is not None and command.contact_id != contact_id:
        boost = player.active_card_boost
        known_contacts = {hood.contact_id for hood in state.board.hoods.values()}
        if (
            boost is None
            or boost["type"] != "sale_link_any_contact"
            or command.contact_id not in known_contacts
        ):
            return CommandFailure(
                DomainError(
                    code="contact_not_allowed",
                    message=f"The new Link cannot be of Contact '{command.contact_id}'.",
                    details={},
                )
            )
        contact_id = command.contact_id
    if command.evolve:
        from_base = skills.sell_link_from_base(state, player)
        _evolve_sale_link(
            state,
            command.player_id,
            contact_id,
            [entry.pawn_id],
            from_base,
            events,
            level=entry.level,
        )

    if not player.pending_sale_link_evolutions:
        price_steps = player.pending_sale_price_steps
        player.pending_sale_price_steps = {}
        _finish_buy_or_sell_package(state, player, price_steps, events, price_tracks)

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
    action_type_by_card_id: dict[CardId, ActionType | None],
    card_effect_by_id: dict[CardId, dict | None],
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
    if state.configuration.get("marketing_mode") == "distinct_exact":
        # "Easy Price" variant (game designer, 2026-10-20): every Stonk moves a different Dope
        # by exactly one level — none discarded, none stacked, none past an end of its track.
        dope_types = [dope_type for dope_type, _ in command.allocations]
        expected = min(stonk_count, len(price_tracks))
        if len(command.allocations) != expected or len(set(dope_types)) != len(dope_types):
            return CommandFailure(
                DomainError(
                    code="marketing_needs_distinct_goods",
                    message=f"Marketing must move {expected} different good(s), one level each.",
                    details={"expected": expected, "given": len(command.allocations)},
                )
            )
        for dope_type, delta in command.allocations:
            index = state.market.price_index_by_dope_type[dope_type]
            if (delta == 1 and index >= len(price_tracks[dope_type]) - 1) or (
                delta == -1 and index <= 0
            ):
                return CommandFailure(
                    DomainError(
                        code="price_out_of_track",
                        message=f"{dope_type.value} cannot move further that way.",
                        details={"dope_type": dope_type.value, "delta": delta},
                    )
                )
    # §D3 (2026-08-17 decision: Marketing is "before" only now, see
    # `_finish_buy_or_sell_package`'s docstring) — no package exists yet
    # at this point, so every Dope type is a free choice; no restriction
    # left to check here.
    for _dope_type, delta in command.allocations:
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
    state.decks.customer_decks_by_contact[contact_id].discard_pile_card_ids.append(command.card_id)
    _emit(
        state,
        events,
        MarketingCardPlayed,
        player_id=command.player_id,
        card_id=command.card_id,
        allocations=command.allocations,
        is_pre=True,
    )

    for dope_type, delta in command.allocations:
        _apply_price_step(state, price_tracks, dope_type, steps=delta, events=events)

    # Up to the action's Marketing limit (one, or two with "Fai 2 marketing"): the
    # allocations accumulate so Manager-3 can replay all of them after the action.
    player.marketing_pre_allocations = player.marketing_pre_allocations + tuple(
        command.allocations
    )
    player.marketing_cards_played_this_action += 1
    customer_cards.finish_marketing_offer(
        state,
        player,
        stonk_count_by_card_id,
        card_effect_by_id,
        action_type_by_card_id,
        declined=False,
    )

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# Public aliases for cross-module reuse (rules/officers.py maneuvers/moves
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
