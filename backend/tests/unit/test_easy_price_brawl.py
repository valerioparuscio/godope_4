"""The Rissa reward in the "Easy Price" variant (game designer, 2026-10-20): the winner no longer
chooses between money and a card — he always steals a random card from each defeated participant,
and the cards that give something extra (SHAKE DOWN money, TAKE THE POT a Poker Chip, SPOILS a
Dope) add it to the card. The other modes keep the money-or-card choice
(tests/unit/test_brawl.py)."""

import pytest
from test_brawl import (
    _bus,
    _declare_no_cards,
    _fresh_pawn,
    _new_game,
    _put_criminal,
)

from dope_engine.application.command_bus import CommandSuccess
from dope_engine.application.data_loader import load_game_data
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import (
    ChooseBrawlLinkEvolution,
    ChooseBrawlLoserReward,
    ChooseBrawlRelocationDestination,
)
from dope_engine.domain.enums import ActiveStep, DopeType
from dope_engine.domain.ids import HoodId
from dope_engine.domain.serialization import from_json_dict, to_json_dict
from dope_engine.domain.state import GameState, find_player
from dope_engine.rules import brawl

# Easy Price has its own map (data_packs/easy_price/board.json): hood_q1 starts covered and empty,
# so it is the Rissa Hood here (test_brawl.py's hood_q2 is revealed and populated in this pack).
HOOD = HoodId("hood_q1")
BIG_HOOD = HoodId("hood_q2")  # the same role on the Big's map (data/board.json)


@pytest.fixture(scope="module")
def easy_data():
    from conftest import REPO_ROOT

    return load_game_data(REPO_ROOT / "data_packs" / "easy_price")


@pytest.fixture()
def easy_tracks(easy_data):
    return {dt: d.price_track for dt, d in easy_data.dope_types.items()}


def _rissa(easy_data, easy_tracks, link_extra_action_types, *, losers=1, winner_boost=None):
    """player_0 (winner: 3 Criminals) against `losers` single-Criminal opponents in HOOD; the
    declarations are made (nobody plays a card), so the Force has been resolved."""
    state, _ = _new_game(easy_data)
    bus = _bus(easy_data, easy_tracks, link_extra_action_types)
    p0 = state.players[0].player_id
    find_player(state, p0).active_card_boost = winner_boost
    for _ in range(3):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    for index in range(1, losers + 1):
        _put_criminal(state, _fresh_pawn(state, index), HOOD)
    return state, bus, p0


def _fight(state, bus, p0, losers=1):
    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p0, [], events)
    return _declare_no_cards(bus, state, losers + 1)


def _hand(state, player_id):
    return list(find_player(state, player_id).hand_card_ids)


def test_the_winner_always_steals_a_card_and_no_money_moves(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(easy_data, easy_tracks, link_extra_action_types)
    p1 = state.players[1].player_id
    cards = [easy_data.customer_cards[0].card_id, easy_data.customer_cards[1].card_id]
    find_player(state, p1).hand_card_ids = list(cards)
    find_player(state, p1).money = 10
    winner_hand, winner_money = _hand(state, p0), find_player(state, p0).money

    state, outcome = _fight(state, bus, p0)

    # no reward decision: the card was taken in the same command that resolved the Rissa
    assert state.pending_brawl.loser_ids == [p1]
    assert state.pending_brawl.reward_loser_index == 1
    decision = get_legal_decision(state, p0, easy_tracks, link_extra_action_types)
    assert decision.decision_type == "choose_brawl_link_evolution"
    # exactly one card moved, from the loser to the winner; no money changed hands
    stolen = [c for c in _hand(state, p0) if c not in winner_hand]
    assert len(stolen) == 1 and stolen[0] in cards
    assert len(_hand(state, p1)) == 1
    assert find_player(state, p0).money == winner_money
    assert find_player(state, p1).money == 10
    reward_events = [e for e in outcome.events if type(e).__name__ == "BrawlLoserRewardChosen"]
    assert len(reward_events) == 1
    assert reward_events[0].reward_type == "card" and reward_events[0].stolen_card_id == stolen[0]
    assert reward_events[0].money_taken == 0 and not reward_events[0].stolen_poker_chip
    # the recap carries what was taken (without naming the card)
    summary = state.last_brawl_outcome.rewards
    assert len(summary) == 1 and summary[0].loser_id == p1 and summary[0].stole_card
    assert summary[0].money == 0 and not summary[0].poker_chip and summary[0].dope_type is None


def test_a_loser_without_cards_loses_nothing(easy_data, easy_tracks, link_extra_action_types):
    state, bus, p0 = _rissa(easy_data, easy_tracks, link_extra_action_types)
    p1 = state.players[1].player_id
    find_player(state, p1).hand_card_ids = []
    find_player(state, p1).money = 10
    winner_hand = _hand(state, p0)

    state, _ = _fight(state, bus, p0)

    assert _hand(state, p0) == winner_hand and find_player(state, p1).money == 10
    assert state.last_brawl_outcome.rewards[0].stole_card is False


def test_every_defeated_participant_is_robbed_in_turn(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(easy_data, easy_tracks, link_extra_action_types, losers=2)
    loser_a, loser_b = state.players[1].player_id, state.players[2].player_id
    find_player(state, loser_a).hand_card_ids = [easy_data.customer_cards[0].card_id]
    find_player(state, loser_b).hand_card_ids = [easy_data.customer_cards[1].card_id]
    winner_hand = _hand(state, p0)

    state, _ = _fight(state, bus, p0, losers=2)

    assert sorted(state.pending_brawl.loser_ids) == sorted([loser_a, loser_b])
    assert len(_hand(state, p0)) == len(winner_hand) + 2
    assert _hand(state, loser_a) == [] and _hand(state, loser_b) == []
    assert len(state.last_brawl_outcome.rewards) == 2


def test_shake_down_adds_four_dollars_to_the_card(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(
        easy_data,
        easy_tracks,
        link_extra_action_types,
        winner_boost={"type": "brawl_reward_money_bonus", "amount": 2},
    )
    p1 = state.players[1].player_id
    find_player(state, p1).hand_card_ids = [easy_data.customer_cards[0].card_id]
    find_player(state, p1).money = 10
    winner_money = find_player(state, p0).money

    state, outcome = _fight(state, bus, p0)

    assert find_player(state, p0).money == winner_money + 4
    assert find_player(state, p1).money == 6
    assert len(_hand(state, p1)) == 0  # the card too
    event = next(e for e in outcome.events if type(e).__name__ == "BrawlLoserRewardChosen")
    assert event.money_taken == 4 and event.stolen_card_id is not None
    assert state.last_brawl_outcome.rewards[0].money == 4


def test_shake_down_cannot_take_more_than_the_loser_has(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(
        easy_data,
        easy_tracks,
        link_extra_action_types,
        winner_boost={"type": "brawl_reward_money_bonus", "amount": 2},
    )
    p1 = state.players[1].player_id
    find_player(state, p1).money = 3
    winner_money = find_player(state, p0).money

    state, _ = _fight(state, bus, p0)

    assert find_player(state, p0).money == winner_money + 3
    assert find_player(state, p1).money == 0


def test_take_the_pot_adds_a_poker_chip_to_the_card(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(
        easy_data,
        easy_tracks,
        link_extra_action_types,
        winner_boost={"type": "brawl_reward_chip_theft"},
    )
    p1 = state.players[1].player_id
    find_player(state, p1).hand_card_ids = [easy_data.customer_cards[0].card_id]
    find_player(state, p1).base_inventory.poker_chip_count = 2
    find_player(state, p0).base_inventory.poker_chip_count = 0

    state, outcome = _fight(state, bus, p0)

    assert find_player(state, p1).base_inventory.poker_chip_count == 1
    assert find_player(state, p0).base_inventory.poker_chip_count == 1
    assert _hand(state, p1) == []
    event = next(e for e in outcome.events if type(e).__name__ == "BrawlLoserRewardChosen")
    assert event.stolen_poker_chip and event.stolen_card_id is not None
    assert state.last_brawl_outcome.rewards[0].poker_chip


def test_a_chip_taken_by_a_winner_with_three_chips_is_not_kept_beyond_the_cap(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(
        easy_data,
        easy_tracks,
        link_extra_action_types,
        winner_boost={"type": "brawl_reward_chip_theft"},
    )
    p1 = state.players[1].player_id
    find_player(state, p1).base_inventory.poker_chip_count = 1
    find_player(state, p0).base_inventory.poker_chip_count = 3

    state, _ = _fight(state, bus, p0)

    assert find_player(state, p0).base_inventory.poker_chip_count == 3
    assert find_player(state, p1).base_inventory.poker_chip_count == 0


def test_spoils_takes_the_only_dope_type_automatically(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(
        easy_data,
        easy_tracks,
        link_extra_action_types,
        winner_boost={"type": "brawl_reward_dope_theft"},
    )
    p1 = state.players[1].player_id
    find_player(state, p1).hand_card_ids = [easy_data.customer_cards[0].card_id]
    find_player(state, p1).base_inventory.dope_counts.clear()
    find_player(state, p1).base_inventory.dope_counts[DopeType.POLPO] = 2
    find_player(state, p0).base_inventory.dope_counts.clear()

    state, _ = _fight(state, bus, p0)

    assert find_player(state, p1).base_inventory.dope_counts[DopeType.POLPO] == 1
    assert find_player(state, p0).base_inventory.dope_counts[DopeType.POLPO] == 1
    assert _hand(state, p1) == []
    assert state.last_brawl_outcome.rewards[0].dope_type == DopeType.POLPO


def test_spoils_asks_which_dope_only_when_the_loser_holds_several_types(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(
        easy_data,
        easy_tracks,
        link_extra_action_types,
        winner_boost={"type": "brawl_reward_dope_theft"},
    )
    p1 = state.players[1].player_id
    find_player(state, p1).hand_card_ids = [easy_data.customer_cards[0].card_id]
    find_player(state, p1).base_inventory.dope_counts.clear()
    find_player(state, p1).base_inventory.dope_counts.update({DopeType.POLPO: 1, DopeType.GUFO: 1})
    find_player(state, p0).base_inventory.dope_counts.clear()
    winner_hand = _hand(state, p0)

    state, _ = _fight(state, bus, p0)

    # the card is not taken yet and nothing is published yet: the winner must pick the Dope
    assert state.active_step == ActiveStep.WAITING_FOR_BRAWL_REWARD
    assert state.pending_brawl.reward_loser_index == 0
    assert state.last_brawl_outcome is None or state.last_brawl_outcome.rewards == ()
    decision = get_legal_decision(state, p0, easy_tracks, link_extra_action_types)
    assert decision.decision_type == "choose_brawl_loser_reward"
    assert decision.context == {"steal_card": True}
    assert {o.payload["reward_type"] for o in decision.options} == {"dope"}
    assert {o.payload["dope_type"] for o in decision.options} == {"polpo", "gufo"}

    # money / card cannot be asked for in this variant
    refused = bus.dispatch(
        state,
        ChooseBrawlLoserReward(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            loser_player_id=p1,
            reward_type="money",
        ),
    )
    assert not isinstance(refused, CommandSuccess)

    chosen = bus.dispatch(
        state,
        ChooseBrawlLoserReward(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            loser_player_id=p1,
            reward_type="dope",
            dope_type="gufo",
        ),
    )
    assert isinstance(chosen, CommandSuccess), chosen
    state = chosen.state
    assert find_player(state, p0).base_inventory.dope_counts[DopeType.GUFO] == 1
    assert find_player(state, p1).base_inventory.dope_counts[DopeType.GUFO] == 0
    assert find_player(state, p1).base_inventory.dope_counts[DopeType.POLPO] == 1
    assert len(_hand(state, p0)) == len(winner_hand) + 1  # the card came with it
    assert state.last_brawl_outcome.rewards[0].dope_type == DopeType.GUFO


def test_the_rissa_runs_to_its_end_after_the_automatic_reward(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(easy_data, easy_tracks, link_extra_action_types)
    state, _ = _fight(state, bus, p0)

    outcome = bus.dispatch(
        state,
        ChooseBrawlLinkEvolution(
            game_id=state.game_id, player_id=p0, expected_revision=state.revision, pawn_id=None
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.pending_brawl is not None and state.pending_brawl.link_evolution_done
    hidden = next(hid for hid, h in state.board.hoods.items() if not h.revealed and hid != HOOD)
    outcome = bus.dispatch(
        state,
        ChooseBrawlRelocationDestination(
            game_id=state.game_id, player_id=p0, expected_revision=state.revision, hood_id=hidden
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.pending_brawl is None


def test_the_recap_with_the_rewards_survives_save_and_load(
    easy_data, easy_tracks, link_extra_action_types
) -> None:
    state, bus, p0 = _rissa(
        easy_data,
        easy_tracks,
        link_extra_action_types,
        winner_boost={"type": "brawl_reward_money_bonus", "amount": 2},
    )
    state, _ = _fight(state, bus, p0)

    reloaded = from_json_dict(GameState, to_json_dict(state))

    assert reloaded.last_brawl_outcome == state.last_brawl_outcome
    assert reloaded.last_brawl_outcome.rewards[0].money == state.last_brawl_outcome.rewards[0].money


def test_the_standard_rissa_still_offers_the_money_or_card_choice(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0 = state.players[0].player_id
    for _ in range(3):
        _put_criminal(state, _fresh_pawn(state, 0), BIG_HOOD)
    _put_criminal(state, _fresh_pawn(state, 1), BIG_HOOD)
    events: list = []
    brawl.start_brawl(state, state.board.hoods[BIG_HOOD], p0, [], events)
    state, _ = _declare_no_cards(bus, state, 2)

    decision = get_legal_decision(state, p0, price_tracks, link_extra_action_types)

    assert decision.decision_type == "choose_brawl_loser_reward"
    assert "money" in {o.payload["reward_type"] for o in decision.options}
    assert state.pending_brawl.reward_loser_index == 0
