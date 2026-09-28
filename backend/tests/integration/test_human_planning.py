import importlib

import pytest
from fastapi.testclient import TestClient

from dope_engine.domain.enums import ActiveStep, PawnRole
from dope_engine.domain.ids import ContactId
from dope_engine.domain.state import PendingSaleLinkEvolution
from dope_engine.rules import links

http = importlib.import_module("dope_engine.adapters.http.app")
client = TestClient(http.app)


@pytest.fixture
def game():
    response = client.post("/api/v1/games", json={"seed": 2, "human_seat": 0, "nickname": "Plan"})
    game_id = response.json()["game_id"]
    client.post(f"/api/v1/games/{game_id}/advance", params={"player_id": "player_0"})
    return game_id


def view(game):
    return client.get(f"/api/v1/games/{game}/view", params={"player_id": "player_0"}).json()


def plan(game, selections=None):
    response = client.post(f"/api/v1/games/{game}/decisions/plan", json={
        "player_id": "player_0", "decision_id": view(game)["pending_decision"]["decision_id"],
        "selections": selections or [],
    })
    assert response.status_code == 200, response.text
    return response.json()


def answer(game, prefix, selection):
    return client.post(f"/api/v1/games/{game}/decisions/answer", json={
        "player_id": "player_0", "decision_id": view(game)["pending_decision"]["decision_id"],
        "preparatory_selections": prefix, "selected_option_ids": selection,
    })


def test_action_preview_matches_each_grit_without_changing_state_or_replay(game):
    before = view(game)
    replay = http._service.export_replay(http._games[game])
    choices = plan(game)
    for grit_option in choices["grit"]["decision"]["options"]:
        staged = plan(game, [[grit_option["option_id"]]])
        assert staged["view"]["pending_decision"]["options"] == choices["grit"]["action_options"][
            str(grit_option["payload"]["grit_value"])
        ]
    assert view(game) == before
    assert http._service.export_replay(http._games[game]) == replay


def test_invalid_final_selection_does_not_consume_staged_grit(game):
    before = view(game)
    replay = http._service.export_replay(http._games[game])
    response = answer(game, [["grit_1"]], ["not_an_action"])
    assert response.status_code == 400
    assert view(game) == before
    assert http._service.export_replay(http._games[game]) == replay


def test_staged_choices_commit_together_and_undo_together(game):
    before = view(game)
    choices = plan(game, [["grit_1"]])
    option = choices["view"]["pending_decision"]["options"][0]["option_id"]
    response = answer(game, [["grit_1"]], [option])
    assert response.status_code == 200 and response.json()["ok"]
    assert len(http._service.export_replay(http._games[game])["commands"]) >= 2
    undone = client.post(f"/api/v1/games/{game}/undo", params={"player_id": "player_0"})
    assert undone.status_code == 200
    assert view(game)["pending_decision"] == before["pending_decision"]
    assert view(game)["players"] == before["players"]


@pytest.mark.parametrize("after_main", [False, True])
def test_link_is_optional_without_consuming_it_or_ending_round(game, after_main):
    state = http._games[game]
    player = state.players[0]
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    links.insert_link(state, player.player_id, pawn_id, ContactId("manager"), 1, [])
    player.extra_action_from_post_main = after_main
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    http._service._refresh_pending_decision(state)
    before = view(game)
    choices = plan(game)
    assert choices["optional"][0]["kind"] == "link"
    assert choices["view"]["pending_decision"]["decision_type"] == (
        "spend_link_for_extra_action" if after_main else "choose_grit_action"
    )
    assert view(game) == before
    link = choices["optional"][0]
    option_id = link["view"]["pending_decision"]["options"][0]["option_id"]
    response = answer(game, link["prefix"], [option_id])
    assert response.status_code == 200 and response.json()["ok"]
    assert http._games[game].pawns[pawn_id].role == PawnRole.IN_BASE


@pytest.mark.parametrize("card_count", [1, 2])
def test_marketing_button_keeps_targets_available_and_does_not_discard(game, card_count):
    state = http._games[game]
    player = state.players[0]
    cards = [card for card in http._service._game_data.customer_cards
             if card.stonk_count > 0 and card.contact_id != ContactId("preti")]
    player.hand_card_ids = [card.card_id for card in cards[:card_count]]
    player.money = 100
    http._service._refresh_pending_decision(state)
    before = view(game)
    choices = plan(game, [["grit_1"]])
    buy = next(option for option in choices["view"]["pending_decision"]["options"]
               if option["payload"]["action_type"] == "buy_dope")
    staged = plan(game, [["grit_1"], [buy["option_id"]]])
    assert any(option["kind"] == "marketing" for option in staged["optional"])
    assert staged["view"]["pending_decision"]["decision_type"] in {
        "buy_dope", "play_customer_card_boost",
    }
    assert view(game) == before


def test_preview_rejects_board_actions_and_wrong_player(game):
    http._games[game].players[0].hand_card_ids = []
    http._service._refresh_pending_decision(http._games[game])
    choices = plan(game, [["grit_1"]])
    action = next(o for o in choices["view"]["pending_decision"]["options"]
                  if o["payload"]["action_type"] == "place_criminal")
    staged = plan(game, [["grit_1"], [action["option_id"]]])
    # Even a valid pass or card play at the next non-preparatory step cannot be previewed.
    response = client.post(f"/api/v1/games/{game}/decisions/plan", json={
        "player_id": "player_0", "decision_id": view(game)["pending_decision"]["decision_id"],
        "selections": [*staged["prefix"], []],
    })
    assert response.status_code == 400
    response = client.post(f"/api/v1/games/{game}/decisions/plan", json={
        "player_id": "player_1", "decision_id": view(game)["pending_decision"]["decision_id"],
    })
    assert response.status_code == 400


def test_sale_evolution_identifies_each_queued_pawn_in_order(game):
    state = http._games[game]
    player = state.players[0]
    pawns = [state.pawns[pid] for pid in player.pawn_ids
             if state.pawns[pid].role == PawnRole.CRIMINAL][:2]
    entries = []
    for pawn in pawns:
        contact_id = state.board.hoods[pawn.location.hood_id].contact_id
        spot = next(spot for spot in state.board.spots.values() if spot.contact_id == contact_id)
        entries.append(PendingSaleLinkEvolution(
            pawn_id=pawn.pawn_id, contact_id=contact_id, spot_id=spot.spot_id,
        ))
    assert len(entries) == 2
    player.pending_sale_link_evolutions = entries
    state.active_step = ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE
    http._service._refresh_pending_decision(state)
    first = view(game)["pending_decision"]["options"][0]["payload"]
    assert first["pawn_id"] == entries[0].pawn_id
    assert first["contact_id"] == entries[0].contact_id
    response = answer(game, [], ["evolve_sale_link_no"])
    assert response.status_code == 200 and response.json()["ok"]
    second = response.json()["view"]["pending_decision"]["options"][0]["payload"]
    assert second["pawn_id"] == entries[1].pawn_id
    assert second["spot_id"] == entries[1].spot_id


def test_poker_is_an_optional_action_button_and_preview_does_not_launch_it(game):
    state = http._games[game]
    state.poker.current_match = None
    player = state.players[0]
    card = next(card for card in http._service._game_data.customer_cards
                if card.contact_id == ContactId("preti") and card.action_type.value == "buy_dope")
    player.hand_card_ids = [card.card_id]
    player.money = 100
    http._service._refresh_pending_decision(state)
    before = view(game)
    choices = plan(game, [["grit_1"]])
    action = next(o for o in choices["view"]["pending_decision"]["options"]
                  if o["payload"]["action_type"] == "buy_dope")
    staged = plan(game, [["grit_1"], [action["option_id"]]])
    assert staged["selected_action"] == "buy_dope"
    assert staged["view"]["pending_decision"]["decision_type"] != "launch_poker"
    poker = next(option for option in staged["optional"] if option["kind"] == "poker")
    assert poker["view"]["pending_decision"]["options"][0]["payload"]["card_id"] == card.card_id
    assert view(game) == before
    response = answer(game, poker["prefix"], [
        poker["view"]["pending_decision"]["options"][0]["option_id"],
    ])
    assert response.status_code == 200 and response.json()["ok"]
    assert http._games[game].poker.current_match is not None
