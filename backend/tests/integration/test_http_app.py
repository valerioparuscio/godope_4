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


def test_view_reflects_pending_decision_for_human() -> None:
    game_id = _create_game(seed=2, human_seat=0)

    response = client.get(f"/api/v1/games/{game_id}/view", params={"player_id": "player_0"})

    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "action_phase"
    assert body["pending_decision"] is not None
    assert body["pending_decision"]["decision_type"] == "choose_grit_action"


def test_view_for_unknown_game_is_404() -> None:
    response = client.get("/api/v1/games/does-not-exist/view", params={"player_id": "player_0"})

    assert response.status_code == 404


def test_submit_command_advances_game_and_returns_new_view() -> None:
    game_id = _create_game(seed=3, human_seat=0)
    view = client.get(f"/api/v1/games/{game_id}/view", params={"player_id": "player_0"}).json()
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
    view = client.get(f"/api/v1/games/{game_id}/view", params={"player_id": "player_0"}).json()
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


def test_full_game_completes_through_http() -> None:
    game_id = _create_game(seed=5, human_seat=1)

    steps = 0
    while steps < 200:
        view = client.get(f"/api/v1/games/{game_id}/view", params={"player_id": "player_1"}).json()
        if view["status"] == "finished":
            break
        steps += 1
        decision = view["pending_decision"]
        assert decision is not None
        count = decision["max_selections"]
        if decision["decision_type"] == "choose_grit_action":
            payload = {"grit_value": decision["options"][0]["payload"]["grit_value"]}
        elif decision["decision_type"] == "hand_discard":
            card_ids = [decision["options"][i]["payload"]["card_id"] for i in range(count)]
            payload = {"card_ids": card_ids}
        else:
            payload = {}

        response = client.post(
            f"/api/v1/games/{game_id}/commands",
            json={
                "command_type": decision["decision_type"]
                if decision["decision_type"] != "main_action_targets"
                else "pass_optional_step",
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
