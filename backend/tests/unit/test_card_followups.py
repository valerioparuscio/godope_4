"""Cards 11/19 (place), 14/16 (Den) and 17 (move) — game designer, 2026-10-15: after a
Buy/Sell package, the card's follow-up runs as a one-target Place/Move action restricted to
the pawns/Hoods that traded (mandatory when it can be done, like a normal placement: costs,
card draw; the Den entry draws a card; the move counts as the pawn's move this turn)."""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import (
    BuyDope,
    EvolveSaleLink,
    MoveCriminal,
    PlaceCriminal,
    SellDope,
)
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, PawnRole
from dope_engine.domain.ids import DEN_ID, ContactId, GameId, HoodId
from dope_engine.rules import economy, links
from dope_engine.rules.setup import create_initial_state


def _bus(game_data, price_tracks, link_extra_action_types):
    bus = CommandBus()
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id={c.card_id: c.contact_id for c in game_data.customer_cards},
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id={c.card_id: c.action_type for c in game_data.customer_cards},
    )
    return bus


def _player_buying(game_data, boost_type, action=ActionType.BUY_DOPE):
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = 1
    player.pending_action_type = action
    player.money = 50
    player.active_card_boost = {"type": boost_type, "action_types": [action.value]}
    return state, player


def _trader_and_hood(state, player):
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)
    return pawn_id, state.pawns[pawn_id].location.hood_id


def _buy(bus, state, player, pawn_id, hood_id):
    state.board.hoods[hood_id].dope_stack = [DopeType.RANA]
    return bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, hood_id),),
        ),
    )


def _decide(state, price_tracks, link_extra_action_types, player):
    return get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)


def test_place_after_buying_is_offered_only_where_the_player_bought(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _player_buying(game_data, "after_trade_place")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, hood_id = _trader_and_hood(state, player)

    outcome = _buy(bus, state, player, pawn_id, hood_id)

    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    player = next(p for p in state.players if p.player_id == player.player_id)
    assert state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    assert player.pending_action_type == ActionType.PLACE_CRIMINAL
    assert player.followup_restriction["kind"] == "place"
    decision = _decide(state, price_tracks, link_extra_action_types, player)
    assert decision.decision_type == "place_criminal"
    assert decision.context == {"card_followup": "place"}
    assert decision.max_selections == 1
    assert {o.payload["hood_id"] for o in decision.options} == {hood_id}


def test_place_followup_places_one_criminal_paying_and_finishes(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _player_buying(game_data, "after_trade_place")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, hood_id = _trader_and_hood(state, player)
    state = _buy(bus, state, player, pawn_id, hood_id).state
    player = next(p for p in state.players if p.player_id == player.player_id)
    money_before = player.money
    hand_before = len(player.hand_card_ids)
    criminals_before = len(state.board.hoods[hood_id].criminal_pawn_ids)

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(hood_id,),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    after = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert after.money == money_before - state.configuration["costs"]["place_criminal"]
    assert len(after.hand_card_ids) == hand_before + 1  # the normal placement draw
    assert len(outcome.state.board.hoods[hood_id].criminal_pawn_ids) == criminals_before + 1
    assert after.followup_restriction is None and after.active_card_boost is None
    assert after.pending_action_type is None


def test_place_followup_rejects_a_hood_where_the_player_did_not_trade(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _player_buying(game_data, "after_trade_place")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, hood_id = _trader_and_hood(state, player)
    state = _buy(bus, state, player, pawn_id, hood_id).state
    other = next(h for h in state.board.hoods if h != hood_id and state.board.hoods[h].revealed)

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(other,),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "followup_restriction_violated"


def test_place_followup_is_skipped_when_the_player_cannot_pay(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _player_buying(game_data, "after_trade_place")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, hood_id = _trader_and_hood(state, player)
    state.board.hoods[hood_id].dope_stack = [DopeType.RANA]
    player.money = 1  # exactly the price of the Rana: nothing left for the $2 placement

    outcome = _buy(bus, state, player, pawn_id, hood_id)

    assert isinstance(outcome, CommandSuccess), outcome
    after = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert after.followup_restriction is None
    assert after.pending_action_type is None


def test_den_followup_sends_the_chosen_trader_to_the_den_and_draws(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _player_buying(game_data, "after_trade_den", ActionType.SELL_DOPE)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, hood_id = _trader_and_hood(state, player)
    contact_id = state.board.hoods[hood_id].contact_id
    spot = next(s for s in state.board.spots.values() if s.contact_id == contact_id)
    player.base_inventory.dope_counts[spot.accepted_dope_type] = 1
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
    state = outcome.state
    player = next(p for p in state.players if p.player_id == player.player_id)
    if state.active_step == ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE:
        # a single-unit sale may offer the Link evolution first; decline it
        from dope_engine.domain.commands import EvolveSaleLink

        state = bus.dispatch(
            state,
            EvolveSaleLink(
                game_id=state.game_id,
                player_id=player.player_id,
                expected_revision=state.revision,
                evolve=False,
            ),
        ).state
        player = next(p for p in state.players if p.player_id == player.player_id)
    assert player.followup_restriction["kind"] == "den"
    decision = _decide(state, price_tracks, link_extra_action_types, player)
    assert {o.payload["destination_hood_id"] for o in decision.options} == {DEN_ID}
    assert {o.payload["pawn_id"] for o in decision.options} == {pawn_id}
    hand_before = len(player.hand_card_ids)

    outcome = bus.dispatch(
        state,
        MoveCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            moves=((pawn_id, DEN_ID, ContactId("artisti")),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    after = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert outcome.state.pawns[pawn_id].role == PawnRole.GAMBLER
    assert len(after.hand_card_ids) == hand_before + 1
    assert after.followup_restriction is None


def test_move_followup_moves_the_trader_to_an_adjacent_hood_and_counts_as_its_move(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _player_buying(game_data, "after_trade_move")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, hood_id = _trader_and_hood(state, player)
    state = _buy(bus, state, player, pawn_id, hood_id).state
    player = next(p for p in state.players if p.player_id == player.player_id)
    assert player.followup_restriction["kind"] == "move"
    decision = _decide(state, price_tracks, link_extra_action_types, player)
    assert decision.decision_type == "move_criminal"
    assert all(o.payload["pawn_id"] == pawn_id for o in decision.options)
    assert all(o.payload["destination_hood_id"] != DEN_ID for o in decision.options)
    destination = HoodId(decision.options[0].payload["destination_hood_id"])

    outcome = bus.dispatch(
        state,
        MoveCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            moves=((pawn_id, destination, None),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    after = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert outcome.state.pawns[pawn_id].location.hood_id == destination
    assert pawn_id in after.moved_pawn_ids_this_turn
    assert after.followup_restriction is None and after.pending_action_type is None


def test_move_followup_rejects_a_pawn_that_did_not_trade(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _player_buying(game_data, "after_trade_move")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, hood_id = _trader_and_hood(state, player)
    state = _buy(bus, state, player, pawn_id, hood_id).state
    player = next(p for p in state.players if p.player_id == player.player_id)
    other_pawn = next(
        pid
        for pid in player.pawn_ids
        if pid != pawn_id and state.pawns[pid].role == PawnRole.CRIMINAL
    )
    adjacent = state.board.hoods[state.pawns[other_pawn].location.hood_id].adjacent_hood_ids[0]

    outcome = bus.dispatch(
        state,
        MoveCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            moves=((other_pawn, adjacent, None),),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "followup_restriction_violated"


# --- Cards 12 "CONNECTION" and 13 "SPREADING": the Link a sale gives --------------------------


def _single_sale(game_data, price_tracks, link_extra_action_types, boost):
    """A one-unit sale by the first Criminal, with `boost` active: returns the state at the
    Link evolution choice, the player, the pawn and the Spot's Contact."""
    state, player = _player_buying(game_data, boost["type"], ActionType.SELL_DOPE)
    player.active_card_boost = {**boost, "action_types": ["sell_dope"]}
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, hood_id = _trader_and_hood(state, player)
    contact_id = state.board.hoods[hood_id].contact_id
    spot = next(s for s in state.board.spots.values() if s.contact_id == contact_id)
    player.base_inventory.dope_counts[spot.accepted_dope_type] = 1
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
    assert outcome.state.active_step == ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE
    return outcome.state, player, pawn_id, contact_id, bus


def test_spreading_puts_the_new_link_at_level_3_pushing_out_the_holder(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, contact_id, bus = _single_sale(
        game_data, price_tracks, link_extra_action_types, {"type": "sale_link_level", "level": 3}
    )
    holder = next(
        pid
        for pid in next(p for p in state.players if p.player_id == "player_1").pawn_ids
        if state.pawns[pid].role == PawnRole.IN_BASE
    )
    links.insert_link(state, "player_1", holder, contact_id, 3, [])

    outcome = bus.dispatch(
        state,
        EvolveSaleLink(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            evolve=True,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert new.pawns[pawn_id].role == PawnRole.LINK
    assert new.pawns[pawn_id].link_level == 3 and new.pawns[pawn_id].contact_id == contact_id
    assert new.pawns[holder].role == PawnRole.IN_BASE  # pushed out, back to its owner's Covo


def test_connection_lets_the_sale_link_be_of_any_contact(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, contact_id, bus = _single_sale(
        game_data, price_tracks, link_extra_action_types, {"type": "sale_link_any_contact"}
    )
    decision = _decide(state, price_tracks, link_extra_action_types, player)
    yes_contacts = {o.payload["contact_id"] for o in decision.options if o.payload["evolve"]}
    assert len(yes_contacts) == len({h.contact_id for h in state.board.hoods.values()})
    chosen = next(c for c in yes_contacts if c != contact_id)

    outcome = bus.dispatch(
        state,
        EvolveSaleLink(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            evolve=True,
            contact_id=chosen,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.pawns[pawn_id].role == PawnRole.LINK
    assert outcome.state.pawns[pawn_id].contact_id == chosen


def test_a_sale_link_of_another_contact_needs_the_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, contact_id, bus = _single_sale(
        game_data, price_tracks, link_extra_action_types, {"type": "ignore_officer_block"}
    )
    other = next(h.contact_id for h in state.board.hoods.values() if h.contact_id != contact_id)

    outcome = bus.dispatch(
        state,
        EvolveSaleLink(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            evolve=True,
            contact_id=other,
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "contact_not_allowed"
