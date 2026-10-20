"""The "Easy Price" variant (game designer, 2026-10-20; docs/variants/EASY_PRICE.md): four-level
price tracks, prices that move only when a Spot fills (to the minimum) / a Hood empties (to the
maximum) and by Marketing (one level per Stonk, each good at most once), and a Poker that earns
no money. The standard rules must stay as they were."""

import pytest
from test_marketing import _bus as _marketing_bus
from test_marketing import _choose_buy_dope, _enter_choose_action_type, _give_marketing_card
from test_officers import _place_cop
from test_poker import (
    ARANCIONE,
    ROSA,
    _place_all_bets,
    _reveal_all_cards,
    _setup_two_bettor_match,
)
from test_poker import (
    _new_game as _poker_new_game,
)

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.data_loader import load_game_data
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import (
    BuyDope,
    ChooseManeuverAction,
    EvolveSaleLink,
    ManeuverOfficer,
    PlayMarketingCard,
    SellDope,
)
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, PawnRole
from dope_engine.domain.ids import GameId
from dope_engine.domain.state import find_player
from dope_engine.rules import economy, officers, prices, turn_flow
from dope_engine.rules.setup import create_initial_state

RANA, CAMALEONTE, POLPO, GUFO = (
    DopeType.RANA,
    DopeType.CAMALEONTE,
    DopeType.POLPO,
    DopeType.GUFO,
)


@pytest.fixture(scope="module")
def easy_data():
    from conftest import REPO_ROOT

    return load_game_data(REPO_ROOT / "data_packs" / "easy_price")


@pytest.fixture()
def easy_tracks(easy_data):
    return {dt: d.price_track for dt, d in easy_data.dope_types.items()}


def _state(data, seed=1):
    state, _ = create_initial_state(data, game_id=GameId("g"), seed=seed, human_seat=0)
    return state


def _bus(data, tracks, link_extra_action_types, stonk_count_by_card_id=None):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in data.customer_cards}
    economy.register_handlers(
        bus,
        price_tracks=tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
        stonk_count_by_card_id=stonk_count_by_card_id or {},
    )
    officers.register_handlers(bus, price_tracks=tracks)
    turn_flow.register_handlers(bus, card_contact_by_id=card_contact_by_id)
    return bus


def _acting(state, action_type):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = 3
    player.pending_action_type = action_type
    player.money = 50
    return player


def _criminal_and_hood(state, player):
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)
    return pawn_id, state.pawns[pawn_id].location.hood_id


def _own_pawns_in(state, player, hood_id, count):
    """`count` Criminals of `player` standing in `hood_id` (others are moved there)."""
    from dope_engine.domain.entities import PawnLocation

    pawn_ids = [
        pid
        for pid in player.pawn_ids
        if state.pawns[pid].role == PawnRole.CRIMINAL
    ]
    chosen = pawn_ids[:count]
    for pid in chosen:
        old = state.pawns[pid].location.hood_id
        if old != hood_id:
            state.board.hoods[old].criminal_pawn_ids.remove(pid)
            state.pawns[pid].location = PawnLocation.hood(hood_id)
            state.board.hoods[hood_id].criminal_pawn_ids.append(pid)
    return chosen


def _buy(bus, state, player, pawn_id, hood_id, times=1):
    pawn_ids = (
        [pawn_id] if times == 1 else _own_pawns_in(state, player, hood_id, times)
    )
    return bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=tuple((pid, hood_id) for pid in pawn_ids),
        ),
    )


def _price(state, tracks, dope_type):
    return prices.current_price(state.market, tracks, dope_type)


# --- the pack ------------------------------------------------------------------


def test_the_pack_has_the_four_level_tracks_and_starts_every_good_at_its_lowest_price(
    easy_data, easy_tracks
):
    assert easy_tracks[RANA] == (0, 1, 2, 3)
    assert easy_tracks[CAMALEONTE] == (2, 3, 4, 6)
    assert easy_tracks[POLPO] == (4, 5, 7, 9)
    assert easy_tracks[GUFO] == (6, 8, 10, 13)
    state = _state(easy_data)
    assert state.configuration["ruleset_id"] == "easy_price"
    # every good starts at the lowest level of its track (game designer, 2026-10-20)
    assert {dt: _price(state, easy_tracks, dt) for dt in easy_tracks} == {
        RANA: 0,
        CAMALEONTE: 2,
        POLPO: 4,
        GUFO: 6,
    }
    assert all(state.market.price_index_by_dope_type[dt] == 0 for dt in easy_tracks)
    standard = load_game_data(__import__("conftest").DATA_DIR)
    assert easy_data.config["costs"] == standard.config["costs"]
    assert easy_data.config["starting_money"] == standard.config.get("starting_money")


def test_the_standard_game_keeps_its_price_rules(game_data, price_tracks, link_extra_action_types):
    state = _state(game_data)
    assert not economy.extremes_mode(state)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _acting(state, ActionType.BUY_DOPE)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    state.board.hoods[hood_id].cop_ids.clear()
    state.board.hoods[hood_id].dope_stack = [DopeType.RANA] * 3
    before = state.market.price_index_by_dope_type[DopeType.RANA]

    outcome = _buy(bus, state, player, pawn_id, hood_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.market.price_index_by_dope_type[DopeType.RANA] == before + 1


# --- prices ----------------------------------------------------------------------


def test_ordinary_trades_do_not_change_prices(easy_data, easy_tracks, link_extra_action_types):
    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.BUY_DOPE)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    hood = state.board.hoods[hood_id]
    hood.cop_ids.clear()
    hood.dope_stack = [DopeType.POLPO] * 3
    before = dict(state.market.price_index_by_dope_type)

    outcome = _buy(bus, state, player, pawn_id, hood_id, times=2)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.market.price_index_by_dope_type == before
    assert not any(type(e).__name__ == "PriceChanged" for e in outcome.events)


def test_emptying_a_hood_sends_the_price_to_the_maximum(
    easy_data, easy_tracks, link_extra_action_types
):
    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.BUY_DOPE)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    hood = state.board.hoods[hood_id]
    hood.cop_ids.clear()
    hood.dope_stack = [DopeType.POLPO] * 2
    state.market.price_index_by_dope_type[DopeType.POLPO] = 1

    outcome = _buy(bus, state, player, pawn_id, hood_id, times=2)

    assert isinstance(outcome, CommandSuccess), outcome
    assert _price(outcome.state, easy_tracks, DopeType.POLPO) == 9
    # both units of the package cost the price they had when it started
    paid = [e.price_paid for e in outcome.events if type(e).__name__ == "DopeBought"]
    assert paid == [5, 5]


def test_filling_a_spot_sends_the_price_to_the_minimum(
    easy_data, easy_tracks, link_extra_action_types
):
    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.SELL_DOPE)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    contact_id = state.board.hoods[hood_id].contact_id
    spot = next(s for s in state.board.spots.values() if s.contact_id == contact_id)
    spot.fed_ids.clear()
    spot.sold_dope_tokens = [spot.accepted_dope_type] * (spot.capacity - 1)
    player.base_inventory.dope_counts[spot.accepted_dope_type] = 2
    state.market.price_index_by_dope_type[spot.accepted_dope_type] = 3

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((pawn_id, spot.accepted_dope_type),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    if new.active_step == ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE:
        # the package's price update waits for the Link-evolution offer, like any price step
        passed = bus.dispatch(
            new,
            EvolveSaleLink(
                game_id=new.game_id,
                player_id=player.player_id,
                expected_revision=new.revision,
                evolve=False,
                contact_id=None,
            ),
        )
        assert isinstance(passed, CommandSuccess), passed
        new = passed.state
    track = easy_tracks[spot.accepted_dope_type]
    assert prices.current_price(new.market, easy_tracks, spot.accepted_dope_type) == track[0]
    assert new.board.spots[spot.spot_id].sold_dope_tokens == []  # cleared, Fed in


def test_a_sale_that_does_not_fill_the_spot_changes_nothing(
    easy_data, easy_tracks, link_extra_action_types
):
    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.SELL_DOPE)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    contact_id = state.board.hoods[hood_id].contact_id
    spot = next(s for s in state.board.spots.values() if s.contact_id == contact_id)
    spot.fed_ids.clear()
    spot.sold_dope_tokens = []
    player.base_inventory.dope_counts[spot.accepted_dope_type] = 2
    before = dict(state.market.price_index_by_dope_type)

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((pawn_id, spot.accepted_dope_type),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.market.price_index_by_dope_type == before


def _confiscate(bus, state, player, pawn_id, cop_id):
    state = bus.dispatch(
        state,
        ManeuverOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            maneuvers=((pawn_id, cop_id),),
        ),
    ).state
    return bus.dispatch(
        state,
        ChooseManeuverAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="confiscate",
        ),
    )


def test_a_requisition_that_empties_a_hood_sends_the_price_to_the_maximum(
    easy_data, easy_tracks, link_extra_action_types
):
    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.MANEUVER_OFFICER)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    hood = state.board.hoods[hood_id]
    hood.dope_stack = [DopeType.GUFO]
    cop_id = _place_cop(state, hood_id)
    state.market.price_index_by_dope_type[DopeType.GUFO] = 0

    outcome = _confiscate(bus, state, player, pawn_id, cop_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert _price(outcome.state, easy_tracks, DopeType.GUFO) == 13


def test_a_requisition_that_leaves_dope_in_the_hood_changes_no_price(
    easy_data, easy_tracks, link_extra_action_types
):
    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.MANEUVER_OFFICER)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    state.board.hoods[hood_id].dope_stack = [DopeType.GUFO] * 2
    cop_id = _place_cop(state, hood_id)
    before = dict(state.market.price_index_by_dope_type)

    outcome = _confiscate(bus, state, player, pawn_id, cop_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.market.price_index_by_dope_type == before


def test_the_extreme_is_applied_on_the_transition_only_and_marketing_can_move_it_afterwards(
    easy_data, easy_tracks, link_extra_action_types
):
    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.BUY_DOPE)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    hood = state.board.hoods[hood_id]
    hood.cop_ids.clear()
    hood.dope_stack = [DopeType.POLPO]
    state = _buy(bus, state, player, pawn_id, hood_id).state
    assert _price(state, easy_tracks, DopeType.POLPO) == 9
    # Marketing lowers it a level ...
    state.market.price_index_by_dope_type[DopeType.POLPO] = 2
    # ... and a later buy from a Hood that still has stock does not push it back to the maximum.
    state.current_player_id = player.player_id
    player = _acting(state, ActionType.BUY_DOPE)
    other = next(
        h for h in state.board.hoods.values() if h.hood_id != hood_id and h.revealed
    )
    other.cop_ids.clear()
    other.dope_stack = [DopeType.POLPO] * 2
    (mover,) = _own_pawns_in(state, player, other.hood_id, 1)

    after = _buy(bus, state, player, mover, other.hood_id)

    assert isinstance(after, CommandSuccess), after
    assert _price(after.state, easy_tracks, DopeType.POLPO) == 7


def test_the_zero_price_of_the_rana_is_a_real_price(
    easy_data, easy_tracks, link_extra_action_types
):
    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.BUY_DOPE)
    pawn_id, hood_id = _criminal_and_hood(state, player)
    hood = state.board.hoods[hood_id]
    hood.cop_ids.clear()
    hood.dope_stack = [DopeType.RANA] * 3
    state.market.price_index_by_dope_type[DopeType.RANA] = 0
    money = player.money

    outcome = _buy(bus, state, player, pawn_id, hood_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert next(e for e in outcome.events if type(e).__name__ == "DopeBought").price_paid == 0
    assert find_player(outcome.state, player.player_id).money == money
    assert _price(outcome.state, easy_tracks, DopeType.RANA) == 0


# --- marketing -----------------------------------------------------------------------


def _marketing_setup(easy_data, easy_tracks, link_extra_action_types, stonks):
    state = _state(easy_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_map = _give_marketing_card(easy_data, player, stonks)
    bus = _marketing_bus(easy_data, easy_tracks, link_extra_action_types, stonk_map)
    outcome = _choose_buy_dope(bus, state, player)
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE
    player = next(p for p in state.players if p.player_id == player.player_id)
    return state, player, card_id, bus, stonk_map


def _play(bus, state, player, card_id, allocations):
    return bus.dispatch(
        state,
        PlayMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_id,
            allocations=tuple(allocations),
        ),
    )


def test_marketing_moves_each_chosen_good_exactly_one_level(
    easy_data, easy_tracks, link_extra_action_types
):
    state, player, card_id, bus, stonk_map = _marketing_setup(
        easy_data, easy_tracks, link_extra_action_types, 3
    )
    # every good starts at the bottom of its track: lift the Camaleonte so it can also go down
    state.market.price_index_by_dope_type[CAMALEONTE] = 2
    before = dict(state.market.price_index_by_dope_type)

    outcome = _play(bus, state, player, card_id, [(RANA, 1), (CAMALEONTE, -1), (GUFO, 1)])

    assert isinstance(outcome, CommandSuccess), outcome
    after = outcome.state.market.price_index_by_dope_type
    assert after[RANA] == before[RANA] + 1
    assert after[CAMALEONTE] == before[CAMALEONTE] - 1
    assert after[GUFO] == before[GUFO] + 1
    assert after[POLPO] == before[POLPO]


def test_marketing_refuses_stacking_discarding_and_leaving_the_track(
    easy_data, easy_tracks, link_extra_action_types
):
    state, player, card_id, bus, stonk_map = _marketing_setup(
        easy_data, easy_tracks, link_extra_action_types, 3
    )
    stacked = _play(bus, state, player, card_id, [(RANA, 1), (RANA, 1), (GUFO, 1)])
    assert isinstance(stacked, CommandFailure)
    assert stacked.error.code == "marketing_needs_distinct_goods"
    discarded = _play(bus, state, player, card_id, [(RANA, 1), (GUFO, 1)])
    assert isinstance(discarded, CommandFailure)
    assert discarded.error.code == "marketing_needs_distinct_goods"

    state.market.price_index_by_dope_type[RANA] = 3  # at the top: up is not allowed
    off_track = _play(bus, state, player, card_id, [(RANA, 1), (GUFO, 1), (POLPO, 1)])
    assert isinstance(off_track, CommandFailure)
    assert off_track.error.code == "price_out_of_track"
    state.market.price_index_by_dope_type[RANA] = 0  # at the bottom: down is not allowed
    off_track = _play(bus, state, player, card_id, [(RANA, -1), (GUFO, 1), (POLPO, 1)])
    assert isinstance(off_track, CommandFailure)
    assert off_track.error.code == "price_out_of_track"


def test_the_marketing_decision_offers_only_legal_moves_and_the_exact_count(
    easy_data, easy_tracks, link_extra_action_types
):
    state, player, card_id, bus, stonk_map = _marketing_setup(
        easy_data, easy_tracks, link_extra_action_types, 4
    )
    state.market.price_index_by_dope_type[RANA] = 0
    state.market.price_index_by_dope_type[GUFO] = 3

    decision = get_legal_decision(
        state,
        player.player_id,
        easy_tracks,
        link_extra_action_types,
        stonk_count_by_card_id=stonk_map,
    )

    assert decision.decision_type == "play_marketing_card"
    assert decision.min_selections == decision.max_selections == 4
    offered = {(o.payload["dope_type"], o.payload["delta"]) for o in decision.options}
    assert ("rana", -1) not in offered and ("rana", 1) in offered
    assert ("gufo", 1) not in offered and ("gufo", -1) in offered


# --- poker --------------------------------------------------------------------------------


def _two_bettor_poker(easy_data, jackpot_chips=0):
    state, _ = _poker_new_game(easy_data)
    bus, match, card_a, card_b = _setup_two_bettor_match(
        easy_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ARANCIONE, ARANCIONE),  # -> "poker": wins
        card_b_symbols=(ROSA, ROSA),  # -> "full": loses
    )
    match.jackpot_chips = jackpot_chips
    p0, p1 = state.players[0].player_id, state.players[1].player_id
    money_before = {p.player_id: p.money for p in state.players}
    state = _place_all_bets(bus, state)
    state, outcome = _reveal_all_cards(bus, state, {p0: card_a, p1: card_b})
    return state, outcome, p0, p1, money_before


def test_the_poker_winner_is_paid_two_dollars_per_player_by_the_bank(easy_data):
    """Game designer, 2026-10-20: the winner earns $2 for every player who took part (himself
    included); the losers lose no money — the prize comes from the bank."""
    state, outcome, p0, p1, money_before = _two_bettor_poker(easy_data)

    resolved = next(e for e in outcome.events if type(e).__name__ == "PokerMatchResolved")
    assert resolved.winner_id == p0 and resolved.cash_won == 4  # 2 players x $2
    after = {p.player_id: p.money for p in state.players}
    assert after[p0] == money_before[p0] + 4
    assert after[p1] == money_before[p1]  # the loser pays nothing
    assert all(after[pid] == money_before[pid] for pid in after if pid != p0)
    # the other rewards stay: the winner still gets a Chip
    assert find_player(state, p0).base_inventory.poker_chip_count == 1


def test_the_chips_carried_by_a_tie_add_to_the_prize(easy_data):
    state, outcome, p0, p1, money_before = _two_bettor_poker(easy_data, jackpot_chips=1)

    resolved = next(e for e in outcome.events if type(e).__name__ == "PokerMatchResolved")
    assert resolved.cash_won == 6  # (2 players + 1 chip carried over) x $2
    assert find_player(state, p0).money == money_before[p0] + 6


def test_launching_poker_pays_nothing_in_the_variant(easy_data):
    from test_poker import _bus as poker_bus
    from test_poker import _prepare_for_launch, _preti_card_id

    from dope_engine.domain.commands import LaunchPoker

    state, _ = _poker_new_game(easy_data)
    bus = poker_bus(easy_data)
    player = find_player(state, state.current_player_id)
    card_id = _preti_card_id(easy_data)
    player.hand_card_ids = [card_id]
    money = player.money
    _prepare_for_launch(easy_data, state, player, card_id)

    outcome = bus.dispatch(
        state,
        LaunchPoker(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_id,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert find_player(outcome.state, player.player_id).money == money


def test_a_card_effect_that_empties_a_hood_also_sends_the_price_to_the_maximum(
    easy_data, easy_tracks, link_extra_action_types
):
    """EVIDENCE (card 84): the corrupted Cop takes a Dope along — the Hood it empties counts."""
    from dope_engine.domain.commands import CorruptOfficer

    state = _state(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    player = _acting(state, ActionType.CORRUPT_OFFICER)
    player.active_card_boost = {
        "type": "corrupt_officer_carries_dope",
        "action_types": ["corrupt_officer"],
    }
    player.base_inventory.dope_counts.clear()
    pawn_id, hood_id = _criminal_and_hood(state, player)
    state.board.hoods[hood_id].dope_stack = [DopeType.POLPO]
    cop_id = _place_cop(state, hood_id)
    state.market.price_index_by_dope_type[DopeType.POLPO] = 0

    outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, cop_id, None),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert _price(outcome.state, easy_tracks, DopeType.POLPO) == 9


def test_a_tie_accumulates_the_two_dollar_prizes_for_the_next_winner(easy_data):
    """Game designer, 2026-10-20: after a tie the $2-per-participant prizes accumulate: nobody
    is paid, the tied players' share stays in the pot and the winner of the next match gets it
    on top of that match's own prize."""
    from test_poker import PokerMatchState, _preti_card_id
    from test_poker import _bus as poker_bus

    from dope_engine.rules import poker

    state, _ = _poker_new_game(easy_data)
    bus, match, card_a, card_b = _setup_two_bettor_match(
        easy_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ROSA, ROSA),
        card_b_symbols=(ROSA, ROSA),  # the same hand: a full tie
    )
    p0, p1 = state.players[0].player_id, state.players[1].player_id
    money_before = {p.player_id: p.money for p in state.players}
    state = _place_all_bets(bus, state)
    state, outcome = _reveal_all_cards(bus, state, {p0: card_a, p1: card_b})

    tie = next(e for e in outcome.events if type(e).__name__ == "PokerMatchResolved")
    assert tie.winner_id is None and tie.cash_won == 0
    assert {p.player_id: p.money for p in state.players} == money_before  # nobody is paid
    assert state.poker.pending_jackpot_chips == 2  # the two tied players' $2 prizes

    # the next match, launched with the carried pot, is won by player_0
    bus2 = poker_bus(
        easy_data, poker_override={card_a: (ARANCIONE, ARANCIONE), card_b: (ROSA, ROSA)}
    )
    find_player(state, p0).hand_card_ids = [card_a]
    find_player(state, p1).hand_card_ids = [card_b]
    state.poker.current_match = PokerMatchState(
        match_id="m0",
        launched_by_player_id=p0,
        gamble_card_id=_preti_card_id(easy_data),
        banco_symbols=(ARANCIONE, ARANCIONE, ROSA),
        jackpot_chips=state.poker.pending_jackpot_chips,
    )
    state.poker.pending_jackpot_chips = 0
    poker.resolve_round_match(state, [])
    state = _place_all_bets(bus2, state)
    state, outcome = _reveal_all_cards(bus2, state, {p0: card_a, p1: card_b})

    final = next(e for e in outcome.events if type(e).__name__ == "PokerMatchResolved")
    assert final.winner_id == p0
    assert final.cash_won == 8  # (2 players + 2 carried) x $2
    assert find_player(state, p0).money == money_before[p0] + 8
    assert find_player(state, p1).money == money_before[p1]
