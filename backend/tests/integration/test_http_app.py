import os
from pathlib import Path

os.environ.setdefault("DOPE_DATA_DIR", str(Path(__file__).resolve().parents[3] / "data"))

from fastapi.testclient import TestClient  # noqa: E402

from dope_engine.adapters.http.app import app  # noqa: E402

client = TestClient(app)


def _create_game(seed: int = 1, human_seat: int = 0) -> str:
    response = client.post("/api/v1/games", json={"human_seat": human_seat, "seed": seed})
    assert response.status_code == 200
    return response.json()["game_id"]


def test_create_game_returns_in_progress_game() -> None:
    response = client.post("/api/v1/games", json={"human_seat": 0, "seed": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["revision"] >= 1


def _get_view(game_id: str, player_id: str) -> dict:
    return client.get(f"/api/v1/games/{game_id}/view", params={"player_id": player_id}).json()


def test_view_reflects_pending_decision_for_human() -> None:
    game_id = _create_game(seed=2, human_seat=0)

    view = _get_view(game_id, "player_0")

    assert view["phase"] == "action_phase"
    assert view["pending_decision"] is not None
    # §D2 (confirmed 2026-08-01): the Poker-launch offer no longer
    # precedes the round's own Grit pick — it only fires from
    # ChooseActionType, once a matching Preti card is held — so a fresh
    # round always starts at the Grit pick.
    assert view["pending_decision"]["decision_type"] == "choose_grit_action"


def test_view_for_unknown_game_is_404() -> None:
    response = client.get("/api/v1/games/does-not-exist/view", params={"player_id": "player_0"})

    assert response.status_code == 404


def test_submit_command_advances_game_and_returns_new_view() -> None:
    game_id = _create_game(seed=3, human_seat=0)
    view = _get_view(game_id, "player_0")
    decision = view["pending_decision"]
    option = decision["options"][0]

    response = client.post(
        f"/api/v1/games/{game_id}/commands",
        json={
            "command_type": "choose_grit_action",
            "player_id": "player_0",
            "expected_revision": view["revision"],
            "decision_id": decision["decision_id"],
            "payload": {"grit_value": option["payload"]["grit_value"]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["view"]["revision"] > view["revision"]


def test_submit_command_with_stale_revision_is_rejected() -> None:
    game_id = _create_game(seed=4, human_seat=0)
    view = _get_view(game_id, "player_0")
    decision = view["pending_decision"]
    option = decision["options"][0]

    response = client.post(
        f"/api/v1/games/{game_id}/commands",
        json={
            "command_type": "choose_grit_action",
            "player_id": "player_0",
            "expected_revision": view["revision"] + 999,
            "decision_id": decision["decision_id"],
            "payload": {"grit_value": option["payload"]["grit_value"]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "revision_mismatch"


def _select_options(decision: dict) -> list[dict]:
    """Pick `max_selections` options for `decision`, deduped by pawn_id for
    the two decision types where a single pawn can appear in more than one
    option (see bots/random_legal.py's docstring): a command naming the
    same pawn twice is rejected by the command bus. `buy_dope`'s options
    are already price-sorted ascending by legal_actions.py, so plain
    slicing there is already the cheapest (and thus affordable) subset."""
    count = decision["max_selections"]
    if decision["decision_type"] not in ("move_criminal", "sell_dope"):
        return decision["options"][:count]

    chosen = []
    used_pawn_ids = set()
    for option in decision["options"]:
        pawn_id = option["payload"]["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        used_pawn_ids.add(pawn_id)
        chosen.append(option)
        if len(chosen) == count:
            break
    return chosen


def _command_type_and_payload(decision: dict) -> tuple[str, dict]:
    decision_type = decision["decision_type"]
    selected = _select_options(decision)

    if decision_type == "corruption_action":
        if not selected:
            return "corruption_action", {"action": "skip"}
        return "corruption_action", {
            "action": selected[0]["payload"]["action"],
            "target_id": selected[0]["payload"]["target_id"],
        }
    # These three Rissa decisions accept an empty selection as a real,
    # typed "decline" payload (card_id/pawn_id/hood_id=None) rather than
    # the generic PassOptionalStep the shortcut below would send — that
    # command isn't registered for WAITING_FOR_BRAWL_* steps.
    if decision_type == "play_brawl_card":
        return decision_type, {"card_id": selected[0]["payload"]["card_id"] if selected else None}
    if decision_type == "choose_brawl_link_evolution":
        return decision_type, {"pawn_id": selected[0]["payload"]["pawn_id"] if selected else None}
    if decision_type == "choose_brawl_relocation_destination":
        return decision_type, {"hood_id": selected[0]["payload"]["hood_id"] if selected else None}
    if not selected and decision["can_pass"]:
        return "pass_optional_step", {}
    if decision_type == "choose_grit_action":
        return decision_type, {"grit_value": selected[0]["payload"]["grit_value"]}
    if decision_type == "hand_discard":
        return "discard_cards", {"card_ids": [o["payload"]["card_id"] for o in selected]}
    if decision_type == "choose_action_type":
        return decision_type, {"action_type": selected[0]["payload"]["action_type"]}
    if decision_type == "launch_poker":
        return decision_type, {"card_id": selected[0]["payload"]["card_id"]}
    if decision_type == "place_poker_bet":
        return decision_type, {"match_ids": [o["payload"]["match_id"] for o in selected]}
    if decision_type == "play_poker_card":
        return decision_type, {
            "match_id": selected[0]["payload"]["match_id"],
            "card_id": selected[0]["payload"]["card_id"],
        }
    if decision_type == "place_criminal":
        return decision_type, {"hood_ids": [o["payload"]["hood_id"] for o in selected]}
    if decision_type == "move_criminal":
        moves = [
            {
                "pawn_id": o["payload"]["pawn_id"],
                "destination_hood_id": o["payload"]["destination_hood_id"],
                "deck_contact_id": o["payload"]["deck_contact_id"],
            }
            for o in selected
        ]
        return decision_type, {"moves": moves}
    if decision_type == "buy_dope":
        return decision_type, {"pawn_ids": [o["payload"]["pawn_id"] for o in selected]}
    if decision_type == "sell_dope":
        sales = [
            {"pawn_id": o["payload"]["pawn_id"], "dope_type": o["payload"]["dope_type"]}
            for o in selected
        ]
        return decision_type, {"sales": sales}
    if decision_type == "corrupt_officer":
        corruptions = [
            {"pawn_id": o["payload"]["pawn_id"], "officer_id": o["payload"]["officer_id"]}
            for o in selected
        ]
        return decision_type, {"corruptions": corruptions}
    if decision_type == "buy_officer":
        purchases = [
            {
                "pawn_id": o["payload"]["pawn_id"],
                "officer_id": o["payload"]["officer_id"],
                "destination": o["payload"]["destination"],
            }
            for o in selected
        ]
        return decision_type, {"purchases": purchases}
    if decision_type == "spend_link_for_extra_action":
        return decision_type, {"pawn_id": selected[0]["payload"]["pawn_id"]}
    if decision_type == "assign_brawl_guns":
        return decision_type, {"target_player_id": selected[0]["payload"]["target_player_id"]}
    if decision_type == "choose_brawl_loser_reward":
        return decision_type, {
            "loser_player_id": selected[0]["payload"]["loser_player_id"],
            "reward_type": selected[0]["payload"]["reward_type"],
        }
    raise AssertionError(f"Unhandled decision_type '{decision_type}' in test helper")


def test_full_game_completes_through_http() -> None:
    game_id = _create_game(seed=5, human_seat=1)

    steps = 0
    while steps < 300:
        view = client.get(f"/api/v1/games/{game_id}/view", params={"player_id": "player_1"}).json()
        if view["status"] == "finished":
            break
        steps += 1
        decision = view["pending_decision"]
        assert decision is not None
        command_type, payload = _command_type_and_payload(decision)

        response = client.post(
            f"/api/v1/games/{game_id}/commands",
            json={
                "command_type": command_type,
                "player_id": "player_1",
                "expected_revision": view["revision"],
                "decision_id": decision["decision_id"],
                "payload": payload,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["ok"] is True, response.json()

    final_response = client.get(
        f"/api/v1/games/{game_id}/view", params={"player_id": "player_1"}
    )
    final_view = final_response.json()
    assert final_view["status"] == "finished"
    assert final_view["turn_index"] == 3
