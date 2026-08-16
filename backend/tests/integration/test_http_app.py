import os
from pathlib import Path

os.environ.setdefault("DOPE_DATA_DIR", str(Path(__file__).resolve().parents[3] / "data"))

from fastapi.testclient import TestClient  # noqa: E402

from dope_engine.adapters.http.app import app  # noqa: E402

client = TestClient(app)


def _create_game(seed: int = 1, human_seat: int = 0) -> str:
    """/api/v1/games no longer auto-advances any leading bots (2026-08-16,
    same reason /commands and /decisions/answer don't either) — a real
    client always calls /advance right after creating a game, same as
    after every other command, so this helper does too, matching that
    contract for every test that expects to land on the human's own
    first decision (or, for player_1+, don't call this and drive
    /advance directly — see test_full_game_completes_through_http)."""
    response = client.post("/api/v1/games", json={"human_seat": human_seat, "seed": seed})
    assert response.status_code == 200
    game_id = response.json()["game_id"]
    advance_response = client.post(
        f"/api/v1/games/{game_id}/advance", params={"player_id": f"player_{human_seat}"}
    )
    assert advance_response.status_code == 200, advance_response.text
    return game_id


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


def test_answer_decision_accepts_a_generic_option_selection() -> None:
    game_id = _create_game(seed=9, human_seat=0)
    view = _get_view(game_id, "player_0")
    decision = view["pending_decision"]
    option = decision["options"][0]

    response = client.post(
        f"/api/v1/games/{game_id}/decisions/answer",
        json={
            "player_id": "player_0",
            "decision_id": decision["decision_id"],
            "selected_option_ids": [option["option_id"]],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["view"]["revision"] > view["revision"]


def test_answer_decision_rejects_a_stale_decision_id() -> None:
    game_id = _create_game(seed=10, human_seat=0)
    view = _get_view(game_id, "player_0")
    decision = view["pending_decision"]

    response = client.post(
        f"/api/v1/games/{game_id}/decisions/answer",
        json={
            "player_id": "player_0",
            "decision_id": "stale-decision-id",
            "selected_option_ids": [decision["options"][0]["option_id"]],
        },
    )

    assert response.status_code == 409


def test_view_exposes_job_board_raid_and_final_score_fields() -> None:
    game_id = _create_game(seed=11, human_seat=0)
    view = _get_view(game_id, "player_0")

    assert "job_board" in view
    assert "job_progress_by_player" in view
    assert "remaining_skill_count_by_contact" in view
    assert "raid_card_id" in view
    # This test is about the *fields* being exposed at all, not about game
    # state — the initial bot cascade before the human's first decision
    # can legitimately already contain a resolved Rissa (move_criminal no
    # longer artificially restricts bot movement, 2026-08-16), so only
    # `final_score`/`last_poker_outcomes` (never true this early) assert a
    # specific value; `last_brawl_outcome`'s own behavior is covered by
    # test_views.py::test_view_exposes_the_last_resolved_brawl_outcome.
    assert "last_brawl_outcome" in view
    assert view["last_poker_outcomes"] == []  # no Poker resolved yet
    assert view["final_score"] is None  # game just started, not finished yet


def test_save_then_load_restores_the_same_view() -> None:
    game_id = _create_game(seed=6, human_seat=0)
    view_before = _get_view(game_id, "player_0")

    save_response = client.get(f"/api/v1/games/{game_id}/save")
    assert save_response.status_code == 200
    save_body = save_response.json()
    assert save_body["snapshot"]["game_id"] == game_id

    load_response = client.post("/api/v1/games/load", json=save_body)
    assert load_response.status_code == 200
    load_body = load_response.json()
    assert load_body["game_id"] == game_id
    assert load_body["revision"] == view_before["revision"]

    view_after = _get_view(game_id, "player_0")
    assert view_after == view_before


def test_loaded_game_can_still_receive_commands() -> None:
    game_id = _create_game(seed=7, human_seat=0)
    save_body = client.get(f"/api/v1/games/{game_id}/save").json()
    client.post("/api/v1/games/load", json=save_body)

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
    assert response.json()["ok"] is True


def test_load_rejects_schema_version_mismatch() -> None:
    game_id = _create_game(seed=8, human_seat=0)
    save_body = client.get(f"/api/v1/games/{game_id}/save").json()
    save_body["schema_version"] += 1

    response = client.post("/api/v1/games/load", json=save_body)

    assert response.status_code == 400
    assert "schema_version" in response.json()["detail"]


def _select_options(decision: dict, view: dict) -> list[dict]:
    """Pick `max_selections` options for `decision`, deduped by pawn_id for
    the decision types where a single pawn can appear in more than one
    option (see bots/random_legal.py's docstring): a command naming the
    same pawn twice is rejected by the command bus. `buy_dope`'s options
    are already price-sorted ascending by legal_actions.py, so plain
    slicing there is already the cheapest (and thus affordable) subset —
    but (2026-08-16) no longer budgets a Hood's real stock across
    candidates as they're generated, so 2 cheapest options can both point
    at a Hood that only has 1 real unit left; also dedupe by `hood_id`
    there against each Hood's real stock (from `view`), same as
    `bots/random_legal.py::_pick_buy_dope_options`, or the second
    purchase fails with `hood_blocked_by_cop` once the first empties and
    restocks it. Also tracks running cost against the player's own
    money there: once Hood-stock budgeting forces skipping a contested
    cheap option in favor of a pricier one to still reach `count`, the
    plain "already cheapest-N" affordability guarantee no longer holds —
    same reasoning (and same bug, caught the same way, via a bot sweep)
    as `_pick_buy_dope_options`. `corrupt_officer` needs the same
    per-pawn dedup (a pawn eligible for several officers, e.g. a Rat,
    now gets one raw option per officer — see `_corrupt_officer_options`'s
    own docstring), *plus* a same-officer dedup so two different pawns
    can't both target it, mirroring `bots/random_legal.py::
    _pick_corrupt_officer_options` exactly."""
    count = decision["max_selections"]
    dedup_types = ("move_criminal", "sell_dope", "buy_dope", "corrupt_officer")
    if decision["decision_type"] not in dedup_types:
        return decision["options"][:count]

    hood_stock = None
    money = None
    if decision["decision_type"] == "buy_dope":
        hood_stock = {h["hood_id"]: len(h["dope_stack"]) for h in view["hoods"]}
        money = next(p["money"] for p in view["players"] if p["player_id"] == decision["player_id"])

    used_officer_ids = set()
    chosen = []
    used_pawn_ids = set()
    for option in decision["options"]:
        pawn_id = option["payload"]["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        if decision["decision_type"] == "corrupt_officer":
            officer_id = option["payload"]["officer_id"]
            if officer_id in used_officer_ids:
                continue
            used_officer_ids.add(officer_id)
        if hood_stock is not None:
            hood_id = option["payload"]["hood_id"]
            if hood_stock.get(hood_id, 0) <= 0:
                continue
            price = option["payload"]["price"]
            assert money is not None
            if price > money:
                continue
            hood_stock[hood_id] -= 1
            money -= price
        used_pawn_ids.add(pawn_id)
        chosen.append(option)
        if len(chosen) == count:
            break
    return chosen


def _command_type_and_payload(decision: dict, view: dict) -> tuple[str, dict]:
    decision_type = decision["decision_type"]
    selected = _select_options(decision, view)

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
        purchases = [
            {"pawn_id": o["payload"]["pawn_id"], "hood_id": o["payload"]["hood_id"]}
            for o in selected
        ]
        return decision_type, {"purchases": purchases}
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
    if decision_type == "choose_job_reward":
        return decision_type, {
            "column_index": selected[0]["payload"]["column_index"],
            "contact_id": selected[0]["payload"].get("contact_id"),
        }
    if decision_type == "choose_raid_first_player":
        return decision_type, {
            "chosen_first_player_id": selected[0]["payload"]["chosen_first_player_id"]
        }
    if decision_type == "stain_reputation_for_money":
        return decision_type, {}
    if decision_type == "choose_marketing_card":
        return decision_type, {"card_id": selected[0]["payload"]["card_id"]}
    if decision_type == "play_marketing_card":
        return decision_type, {
            "card_id": selected[0]["payload"]["card_id"],
            "allocations": [
                {"dope_type": o["payload"]["dope_type"], "delta": o["payload"]["delta"]}
                for o in selected
            ],
        }
    if decision_type == "evolve_sale_link":
        return decision_type, {"evolve": selected[0]["payload"]["evolve"]}
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
        command_type, payload = _command_type_and_payload(decision, view)

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

        # /commands only dispatches (2026-08-16) — the bot/automatic
        # cascade is a deliberately separate step now, same as a real
        # client (frontend) driving the game would do.
        advance_response = client.post(
            f"/api/v1/games/{game_id}/advance", params={"player_id": "player_1"}
        )
        assert advance_response.status_code == 200, advance_response.text
        assert advance_response.json()["ok"] is True, advance_response.json()

    final_response = client.get(
        f"/api/v1/games/{game_id}/view", params={"player_id": "player_1"}
    )
    final_view = final_response.json()
    assert final_view["status"] == "finished"
    assert final_view["turn_index"] == 3
    assert final_view["final_score"] is not None
    assert len(final_view["final_score"]["winner_ids"]) >= 1
