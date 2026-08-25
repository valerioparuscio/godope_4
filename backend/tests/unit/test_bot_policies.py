""" "Basi per bot più intelligenti" (2026-08-25): the shared, key-driven
option pickers (`bots/option_picking.py`) and the simple heuristics they
can be ordered by (`bots/scoring.py`). `hood_q1`/`hood_q2` are both
Contact "artisti" (`hood_q1` revealed at game start, `hood_q2` starts
empty/unrevealed) — same fixture pair `test_brawl.py` uses, for the same
reason: pre-placing exactly the Criminals a scenario needs gives an
exact, predictable count."""

import random

from dope_engine.application.views import build_player_view
from dope_engine.bots.option_picking import pick_buy_dope_options
from dope_engine.bots.scoring import score_option
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import DopeType, PawnRole
from dope_engine.domain.ids import ContactId, GameId, HoodId
from dope_engine.rules.setup import create_initial_state

ARTISTI = ContactId("artisti")
HOOD_1 = HoodId("hood_q1")
HOOD_2 = HoodId("hood_q2")


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _price_tracks(game_data):
    return {dope_type: d.price_track for dope_type, d in game_data.dope_types.items()}


def _fresh_pawn(state, player_index):
    player = state.players[player_index]
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)


def _put_criminal(state, pawn_id, hood_id):
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.CRIMINAL
    pawn.location = PawnLocation.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)


def _decision(player_id, decision_type, options, max_selections=1) -> PendingDecision:
    return PendingDecision(
        decision_id="decision_test",
        player_id=player_id,
        decision_type=decision_type,
        prompt_key="decision.test.prompt",
        options=tuple(options),
        min_selections=1,
        max_selections=max_selections,
    )


def test_key_reorders_buy_dope_pick_while_respecting_budget(game_data) -> None:
    state, _ = _new_game(game_data)
    state.board.hoods[HOOD_1].dope_stack = [DopeType.RANA, DopeType.RANA, DopeType.RANA]
    view = build_player_view(state, state.player_order[0], _price_tracks(game_data))

    options = [
        DecisionOption(
            option_id=f"buy_{i}",
            label_key="decision.buy_dope.option",
            payload={
                "pawn_id": f"fake_pawn_{i}",
                "hood_id": HOOD_1,
                "dope_type": "rana",
                "price": price,
            },
        )
        for i, price in enumerate([5, 1, 9])
    ]
    decision = _decision(state.player_order[0], "buy_dope", options)

    cheapest_first = pick_buy_dope_options(decision, 1, random.Random(1), view)
    priciest_first = pick_buy_dope_options(
        decision, 1, random.Random(1), view, key=lambda o: -o.payload["price"]
    )

    assert cheapest_first == ("buy_1",)  # price=1
    assert priciest_first == ("buy_2",)  # price=9


def test_score_option_sell_dope_prefers_higher_price(game_data) -> None:
    state, _ = _new_game(game_data)
    view = build_player_view(state, state.player_order[0], _price_tracks(game_data))
    prices = view.current_price_by_dope_type
    dope_high = max(prices, key=lambda dt: prices[dt])
    dope_low = min(prices, key=lambda dt: prices[dt])
    assert prices[dope_high] > prices[dope_low]

    spot_id = view.spots[0].spot_id

    def option(dope_type):
        return DecisionOption(
            option_id="sell",
            label_key="decision.sell_dope.option",
            payload={"pawn_id": "fake_pawn", "spot_id": spot_id, "dope_type": dope_type.value},
        )

    decision_high = _decision(state.player_order[0], "sell_dope", [option(dope_high)])
    decision_low = _decision(state.player_order[0], "sell_dope", [option(dope_low)])

    score_high = score_option(decision_high.options[0], decision_high, view)
    score_low = score_option(decision_low.options[0], decision_low, view)
    assert score_high > score_low


def test_score_option_move_criminal_penalizes_triggering_a_rissa(game_data) -> None:
    state, _ = _new_game(game_data)
    mover_id = state.player_order[0]
    # hood_q2 starts empty/unrevealed — reveal it and pre-place 4 other
    # players' Criminals so this player's own move into it would be the
    # 5th (RULES_CANONICAL.md §D1's trigger count, capacity=5).
    state.board.hoods[HOOD_2].revealed = True
    for i, player_id in enumerate(state.player_order):
        if player_id == mover_id:
            continue
        pawn_id = next(
            pid for pid in state.players[i].pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
        )
        _put_criminal(state, pawn_id, HOOD_2)
    # A 4th criminal is needed to reach capacity-1 (3 opponents were
    # placed above); who owns it doesn't matter — the Rissa-trigger check
    # only counts total criminals in the Hood, not per-owner — so reusing
    # one of the mover's own spare pawns is fine.
    extra_pawn_id = _fresh_pawn(state, 0)
    _put_criminal(state, extra_pawn_id, HOOD_2)
    assert len(state.board.hoods[HOOD_2].criminal_pawn_ids) == 4

    view = build_player_view(state, mover_id, _price_tracks(game_data))

    def move_option(destination):
        return DecisionOption(
            option_id="move",
            label_key="decision.move_criminal.option",
            payload={
                "pawn_id": "fake_pawn",
                "destination_hood_id": destination,
                "deck_contact_id": None,
            },
        )

    crowded = _decision(mover_id, "move_criminal", [move_option(HOOD_2)])
    safe = _decision(mover_id, "move_criminal", [move_option(HOOD_1)])

    score_crowded = score_option(crowded.options[0], crowded, view)
    score_safe = score_option(safe.options[0], safe, view)
    assert score_crowded < score_safe


def test_score_option_majority_bonus(game_data) -> None:
    state, _ = _new_game(game_data)
    seat0 = state.player_order[0]

    # seat0 gets strict majority at ARTISTI (hood_q1/hood_q2): 2 Criminals
    # vs seat1's 1. hood_q2 needs revealing first (starts unrevealed).
    state.board.hoods[HOOD_2].revealed = True
    p0_pawn_a = _fresh_pawn(state, 0)
    _put_criminal(state, p0_pawn_a, HOOD_1)
    p0_pawn_b = next(
        pid for pid in state.players[0].pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    _put_criminal(state, p0_pawn_b, HOOD_2)
    p1_pawn = _fresh_pawn(state, 1)
    _put_criminal(state, p1_pawn, HOOD_1)

    view = build_player_view(state, seat0, _price_tracks(game_data))

    # A Contact seat0 has no presence at all, for the control comparison.
    other_contact_hood = next(h for h in view.hoods if h.contact_id != ARTISTI and h.revealed)

    majority_option = DecisionOption(
        option_id="place_majority",
        label_key="decision.place_criminal.option",
        payload={"hood_id": HOOD_1},
    )
    no_presence_option = DecisionOption(
        option_id="place_none",
        label_key="decision.place_criminal.option",
        payload={"hood_id": other_contact_hood.hood_id},
    )

    decision_majority = _decision(seat0, "place_criminal", [majority_option])
    decision_none = _decision(seat0, "place_criminal", [no_presence_option])

    score_majority = score_option(majority_option, decision_majority, view)
    score_none = score_option(no_presence_option, decision_none, view)
    assert score_majority > score_none
