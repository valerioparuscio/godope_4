"""Multiplayer over HTTP (docs/architecture/GPT_MULTIPLAYER.md sections 30-33, 49-51): the security
checklist, the lobby, polling, and whole games played by scripted humans that only use the API.
"""

from __future__ import annotations

import json
import logging

import pytest
from fake_human import API, FakeHuman, create_room, play_in_parallel, play_in_turns
from starlette.testclient import TestClient
from test_http_app import _select_options

from dope_engine.adapters.http.app import app, multiplayer_service
from dope_engine.application.multiplayer.models import RoomStatus

HUMAN_NAMES = ["Marco", "Luca", "Anna", "Sara"]


@pytest.fixture()
def http():
    # Used as a context manager: one event loop for the whole test, not one per request.
    with TestClient(app) as client:
        yield client


def table(http: TestClient, humans: int, **room_options: object) -> list[FakeHuman]:
    """A started room with `humans` scripted players; the first one is the host."""
    host = FakeHuman(http, create_room(http, humans=humans, **room_options))  # type: ignore[arg-type]
    players = [host] + [
        FakeHuman.join(http, host.room_code, name) for name in HUMAN_NAMES[1:humans]
    ]
    host.start()
    for player in players:
        player.learn_game_id()
    return players


def error_of(response) -> dict:
    body = response.json()
    assert set(body) == {"error", "message", "details"}, body
    return body


# ------------------------------------------------------------------- the lobby


def test_a_room_is_created_joined_and_started_over_http(http) -> None:
    host = FakeHuman(http, create_room(http, humans=3))
    assert host.player_id == "player_0" and host.game_id is None

    lobby = http.get(f"{API}/rooms/{host.room_code}").json()
    assert lobby["status"] == "lobby" and lobby["game_id"] is None
    assert [s["occupied"] for s in lobby["seats"]] == [True, False, False, True]
    assert "seat_token" not in json.dumps(lobby)

    luca = FakeHuman.join(http, host.room_code, "Luca")
    anna = FakeHuman.join(http, host.room_code, "Anna")
    assert (luca.seat_index, anna.seat_index) == (1, 2)
    assert len({host.token, luca.token, anna.token}) == 3

    room = host.start()
    assert room["status"] == "running" and room["game_id"]
    assert [s["controller_type"] for s in room["seats"]] == ["human", "human", "human", "bot"]
    assert [s["nickname"] for s in room["seats"]] == ["Marco", "Luca", "Anna", "Bot 4"]


def test_lobby_failures_are_typed_and_have_a_useful_status(http) -> None:
    host = FakeHuman(http, create_room(http, humans=2))

    unknown = http.get(f"{API}/rooms/ZZZZ")
    assert unknown.status_code == 404 and error_of(unknown)["error"] == "room_not_found"

    early = http.post(f"{API}/rooms/{host.room_code}/start", headers=host.headers)
    assert early.status_code == 409 and error_of(early)["error"] == "room_not_ready"
    assert error_of(early)["details"] == {"missing_seat_indexes": [1]}

    luca = FakeHuman.join(http, host.room_code, "Luca")
    by_guest = http.post(f"{API}/rooms/{host.room_code}/start", headers=luca.headers)
    assert by_guest.status_code == 403 and error_of(by_guest)["error"] == "forbidden"

    without_token = http.post(f"{API}/rooms/{host.room_code}/start")
    assert without_token.status_code == 401
    assert error_of(without_token)["error"] == "invalid_token"

    full = http.post(f"{API}/rooms/{host.room_code}/join", json={"nickname": "Anna"})
    assert full.status_code == 409 and error_of(full)["error"] == "room_full"

    host.start()
    late = http.post(f"{API}/rooms/{host.room_code}/join", json={"nickname": "Anna"})
    assert late.status_code == 409 and error_of(late)["error"] == "room_already_started"


@pytest.mark.parametrize(
    "body",
    [
        {"human_seats": 1, "nickname": "Marco"},
        {"human_seats": 5, "nickname": "Marco"},
        {"human_seats": 2, "nickname": ""},
        {"human_seats": 2, "nickname": "Marco", "ruleset": "nope"},
    ],
)
def test_a_malformed_room_request_is_refused(http, body) -> None:
    assert http.post(f"{API}/rooms", json=body).status_code == 422


def test_a_client_cannot_choose_the_seed(http) -> None:
    host = FakeHuman(http, create_room(http, humans=2))
    FakeHuman.join(http, host.room_code, "Luca")
    response = http.post(
        f"{API}/rooms", json={"human_seats": 2, "nickname": "Zoe", "seed": 1, "ruleset": "standard"}
    )

    # An unknown field is simply not read: the room gets a server-side random seed.
    assert response.status_code == 200
    session = multiplayer_service.registry.room(response.json()["room_code"])
    assert session.seed is None


# ------------------------------------------------------- the security checklist


def test_game_routes_need_a_valid_seat_token(http) -> None:
    players = table(http, 2)
    other_room = table(http, 2)
    game_id = players[0].game_id

    attempts = [
        {},  # no header
        {"Authorization": "Bearer nonsense"},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer "},
        other_room[0].headers,  # a real token, of another game
    ]
    for headers in attempts:
        for method, path, extra in (
            ("get", f"/mp/games/{game_id}/view", {}),
            ("get", f"/mp/games/{game_id}/events", {}),
            ("post", f"/mp/games/{game_id}/decisions/plan", {"json": {"decision_id": "x"}}),
            (
                "post",
                f"/mp/games/{game_id}/decisions/answer",
                {"json": {"decision_id": "x", "expected_revision": 1}},
            ),
            ("post", f"/mp/games/{game_id}/leave", {}),
        ):
            response = getattr(http, method)(f"{API}{path}", headers=headers, **extra)
            assert response.status_code == 401, (method, path, headers, response.text)
            assert error_of(response)["error"] == "invalid_token"


def test_the_caller_is_whoever_the_token_says_not_whoever_the_request_claims(http) -> None:
    players = table(http, 2)
    marco, luca = players
    snapshot = marco.view()
    awaited = snapshot["awaiting_player_id"]
    waiting, intruder = (marco, luca) if awaited == marco.player_id else (luca, marco)

    # A player_id in the query string is not read: you still get your own view.
    spoofed = http.get(
        f"{API}/mp/games/{marco.game_id}/view",
        params={"player_id": luca.player_id},
        headers=marco.headers,
    ).json()
    assert spoofed["view"]["viewing_player_id"] == marco.player_id
    assert spoofed["me"]["player_id"] == marco.player_id

    # Claiming to be the player the game is waiting for does not make you them.
    decision = waiting.view()["view"]["pending_decision"]
    response = http.post(
        f"{API}/mp/games/{marco.game_id}/decisions/answer",
        headers=intruder.headers,
        json={
            "player_id": waiting.player_id,
            "decision_id": decision["decision_id"],
            "expected_revision": snapshot["revision"],
            "selected_option_ids": [decision["options"][0]["option_id"]],
        },
    )
    assert response.status_code == 409 and error_of(response)["error"] == "not_your_turn"
    assert marco.view()["revision"] == snapshot["revision"]


def test_the_solo_routes_cannot_reach_a_multiplayer_game(http) -> None:
    players = table(http, 2)
    game_id = players[0].game_id
    revision = players[0].view()["revision"]

    for response in (
        http.get(f"{API}/games/{game_id}/view", params={"player_id": "player_0"}),
        http.get(f"{API}/games/{game_id}/save"),
        http.get(f"{API}/games/{game_id}/replay"),
        http.post(f"{API}/games/{game_id}/advance", params={"player_id": "player_0"}),
        http.post(
            f"{API}/games/{game_id}/commands",
            json={
                "command_type": "pass_optional_step",
                "player_id": "player_0",
                "expected_revision": revision,
                "payload": {},
            },
        ),
    ):
        assert response.status_code == 404, response.text
    # There is no undo stack for a multiplayer game (undo is off, section 23).
    undo = http.post(f"{API}/games/{game_id}/undo", params={"player_id": "player_0"})
    assert undo.status_code in (404, 409), undo.text
    assert players[0].view()["revision"] == revision


def test_loading_a_save_cannot_replace_a_running_multiplayer_game(http) -> None:
    players = table(http, 2)
    game_id = players[0].game_id
    before = players[0].view()
    solo = http.post(
        f"{API}/games", json={"human_seat": 0, "seed": 3, "nickname": "Solo", "ruleset": "standard"}
    ).json()["game_id"]
    save = http.get(f"{API}/games/{solo}/save").json()
    save["game_id"] = game_id  # a save claiming to be that very game

    http.post(f"{API}/games/load", json=save)

    after = players[0].view()
    assert after["revision"] == before["revision"]
    assert after["view"]["players"] == before["view"]["players"]


def test_seat_tokens_never_reach_the_logs_or_other_players(http, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        players = table(http, 2)
        for player in players:
            player.view()
            player.poll()
    tokens = [player.token for player in players]

    assert not any(token in caplog.text for token in tokens)
    everything = json.dumps(
        [
            http.get(f"{API}/rooms/{players[0].room_code}").json(),
            players[1].view(),
            players[1].poll(),
        ]
    )
    assert players[0].token not in everything


def test_the_response_to_a_player_does_not_contain_the_seed_or_other_players_hands(http) -> None:
    players = table(http, 3)
    session = multiplayer_service.registry.room(players[0].room_code)
    state = session.state
    assert state is not None and state.seed > 1000  # distinctive enough to search for

    for me, viewer in enumerate(players):
        text = json.dumps([viewer.view(), viewer.poll()])
        assert f'"seed": {state.seed}' not in text
        for other, player_state in enumerate(state.players):
            if other == me:
                continue
            for card_id in player_state.hand_card_ids:
                assert card_id not in text, f"seat {me} was told about {card_id} of seat {other}"


def test_a_stale_answer_is_refused_with_what_the_client_needs_to_recover(http) -> None:
    players = table(http, 2)
    snapshot = players[0].view()
    actor = next(p for p in players if p.player_id == snapshot["awaiting_player_id"])
    snapshot = actor.view()
    decision = snapshot["view"]["pending_decision"]

    response = http.post(
        f"{API}/mp/games/{actor.game_id}/decisions/answer",
        headers=actor.headers,
        json={
            "decision_id": decision["decision_id"],
            "expected_revision": snapshot["revision"] - 1,
            "selected_option_ids": [decision["options"][0]["option_id"]],
        },
    )

    assert response.status_code == 409
    body = error_of(response)
    assert body["error"] == "stale_revision"
    assert body["details"] == {
        "expected": snapshot["revision"],
        "received": snapshot["revision"] - 1,
    }
    assert actor.view()["revision"] == snapshot["revision"]


def test_an_illegal_selection_is_refused_and_changes_nothing(http) -> None:
    players = table(http, 2)
    actor = next(p for p in players if p.player_id == players[0].view()["awaiting_player_id"])
    snapshot = actor.view()
    decision = snapshot["view"]["pending_decision"]

    response = http.post(
        f"{API}/mp/games/{actor.game_id}/decisions/answer",
        headers=actor.headers,
        json={
            "decision_id": decision["decision_id"],
            "expected_revision": snapshot["revision"],
            "selected_option_ids": ["there-is-no-such-option"],
        },
    )

    assert response.status_code == 400 and error_of(response)["error"] == "invalid_decision"
    assert actor.view()["revision"] == snapshot["revision"]


def test_polling_and_planning_leave_the_game_exactly_as_it_was(http) -> None:
    players = table(http, 2)
    actor = next(p for p in players if p.player_id == players[0].view()["awaiting_player_id"])
    session = multiplayer_service.registry.room(actor.room_code)
    state_before, log_before = session.state, len(session.event_log)
    decision = actor.view()["view"]["pending_decision"]

    for player in players:
        for _ in range(3):
            player.poll()
    planned = http.post(
        f"{API}/mp/games/{actor.game_id}/decisions/plan",
        headers=actor.headers,
        json={"decision_id": decision["decision_id"], "selections": []},
    )

    assert planned.status_code == 200, planned.text
    assert session.state is state_before and len(session.event_log) == log_before
    other = next(p for p in players if p is not actor)
    refused = http.post(
        f"{API}/mp/games/{actor.game_id}/decisions/plan",
        headers=other.headers,
        json={"decision_id": decision["decision_id"], "selections": []},
    )
    assert refused.status_code == 409 and error_of(refused)["error"] == "not_your_turn"


def test_polling_from_a_revision_returns_only_what_came_after(http) -> None:
    players = table(http, 2)
    marco = players[0]
    everything = marco.poll()
    assert everything["batches"][0]["segment_type"] == "game_start"
    again = http.get(
        f"{API}/mp/games/{marco.game_id}/events", params={"since": 0}, headers=marco.headers
    ).json()
    assert again["batches"] == everything["batches"]  # asking twice gives the same answer

    nothing_new = marco.poll()
    assert nothing_new["batches"] == []

    ahead = http.get(
        f"{API}/mp/games/{marco.game_id}/events", params={"since": 10**6}, headers=marco.headers
    ).json()
    assert ahead["requires_refresh"] is True


# --------------------------------------------------------- whole games over HTTP


@pytest.mark.parametrize(
    ("humans", "expected_bots"), [(2, 2), (3, 1), (4, 0)], ids=["2H+2B", "3H+1B", "4H"]
)
def test_a_whole_game_is_played_by_scripted_humans_taking_turns(
    http, humans, expected_bots
) -> None:
    players = table(http, humans)

    steps = play_in_turns(players)

    assert steps > humans
    views = [p.view() for p in players]
    assert all(v["status"] == "finished" for v in views)
    winners = {tuple(v["view"]["final_score"]["winner_ids"]) for v in views}
    assert len(winners) == 1 and winners.pop()
    room = http.get(f"{API}/rooms/{players[0].room_code}").json()
    assert room["status"] == "finished"
    assert sum(1 for s in room["seats"] if s["controller_type"] == "bot") == expected_bots
    # Everybody's log is the same story: contiguous, complete, same length.
    first = players[0].batches
    for player in players:
        assert [b["index"] for b in player.batches] == list(range(len(player.batches)))
        assert len(player.batches) == len(first)
        for earlier, later in zip(player.batches, player.batches[1:], strict=False):
            assert later["revision_from"] == earlier["revision_to"]
        started = [
            e for b in player.batches for e in b["events"] if e["event_type"] == "GameStarted"
        ]
        assert [e["seed"] for e in started] == [0]


def test_a_game_against_the_heuristic_bots_also_finishes(http) -> None:
    players = table(http, 2, bot_policy="heuristic")

    play_in_turns(players)

    assert players[0].view()["status"] == "finished"


def test_the_easy_price_ruleset_is_playable_with_several_humans(http) -> None:
    players = table(http, 3, ruleset="easy_price")

    play_in_turns(players)

    view = players[0].view()
    assert view["status"] == "finished"
    assert view["view"]["ruleset_id"] == "easy_price"


@pytest.mark.parametrize("humans", [2, 4])
def test_humans_acting_on_their_own_threads_with_random_pauses_finish_the_game(
    http, humans
) -> None:
    players = table(http, humans)
    credentials = [
        {
            "room_code": p.room_code,
            "seat_index": p.seat_index,
            "player_id": p.player_id,
            "seat_token": p.token,
            "game_id": p.game_id,
        }
        for p in players
    ]

    running = play_in_parallel(app, credentials, pass_probability=0.1)

    session = multiplayer_service.registry.room(players[0].room_code)
    assert session.status is RoomStatus.FINISHED
    batches = session.event_log
    assert [b.index for b in batches] == list(range(len(batches)))
    for earlier, later in zip(batches, batches[1:], strict=False):
        assert later.revision_from == earlier.revision_to
    assert all(len(h.batches) == len(batches) or h.batches for h in running)


def test_a_player_who_reloads_the_page_gets_the_same_seat_and_the_whole_story(http) -> None:
    players = table(http, 2)
    marco = players[0]
    for _ in range(6):
        snapshot = marco.view()
        actor = next(p for p in players if p.player_id == snapshot["awaiting_player_id"])
        actor.act()
        marco.poll()
    story_before = list(marco.batches)

    # A fresh browser tab: nothing but the stored token.
    reloaded = FakeHuman(
        http,
        {
            "room_code": marco.room_code,
            "seat_index": marco.seat_index,
            "player_id": marco.player_id,
            "seat_token": marco.token,
            "game_id": marco.game_id,
        },
    )
    view = reloaded.view()
    reloaded.poll()

    assert view["me"]["player_id"] == marco.player_id
    assert reloaded.batches == story_before
    assert view["revision"] == marco.view()["revision"]


def test_leaving_a_running_game_over_http_hands_the_seat_to_a_bot(http) -> None:
    players = table(http, 2)
    marco, luca = players

    response = http.post(f"{API}/mp/games/{marco.game_id}/leave", headers=luca.headers)

    assert response.status_code == 200
    assert response.json()["room"]["seats"][1]["controller_type"] == "bot"
    assert http.get(f"{API}/mp/games/{marco.game_id}/view", headers=luca.headers).status_code == 401
    play_in_turns([marco])
    assert marco.view()["status"] == "finished"


# ------------------------------------------------------------ same game, two paths


def test_the_http_game_is_the_direct_game_with_the_same_choices(
    http, monkeypatch, game_data
) -> None:
    """Parity (section 33): the same seed, game id and human choices give the same final state
    whether the game is played straight on the engine or through rooms, tokens and HTTP."""
    from dope_engine.adapters.http.serialization import to_view_response
    from dope_engine.application.game_service import GameService
    from dope_engine.application.legal_actions import build_command_from_selection
    from dope_engine.bots.random_legal import RandomLegalBot
    from dope_engine.domain.enums import ControllerType
    from dope_engine.domain.ids import GameId
    from dope_engine.rules.setup import SeatConfig

    seed, game_id = 4242, GameId("parity-game")
    monkeypatch.setattr(multiplayer_service, "seed_factory", lambda: seed)
    monkeypatch.setattr(multiplayer_service, "game_id_factory", lambda: game_id)

    def pick(view_json: dict) -> list[str]:
        """The same function of (decision, view) for both paths."""
        decision = view_json["pending_decision"]
        return [o["option_id"] for o in _select_options(decision, view_json)]

    # Path B: rooms, tokens and HTTP.
    players = table(http, 2)
    for _ in range(4000):
        snapshot = players[0].view()
        if snapshot["status"] == "finished":
            break
        actor = next(p for p in players if p.player_id == snapshot["awaiting_player_id"])
        own = actor.view()
        response = http.post(
            f"{API}/mp/games/{actor.game_id}/decisions/answer",
            headers=actor.headers,
            json={
                "decision_id": own["view"]["pending_decision"]["decision_id"],
                "expected_revision": own["revision"],
                "selected_option_ids": pick(own["view"]),
            },
        )
        assert response.status_code == 200, response.text
    http_state = multiplayer_service.registry.room(players[0].room_code).state
    assert http_state is not None and http_state.status.value == "finished"

    # Path A: the engine, driven directly with the same choices.
    service = GameService(game_data, bot_policy=RandomLegalBot())
    state = service.create_game_from_seats(
        game_id=game_id,
        seed=seed,
        seats=[
            SeatConfig(ControllerType.HUMAN, "Marco"),
            SeatConfig(ControllerType.HUMAN, "Luca"),
            SeatConfig(ControllerType.BOT, "Bot 3"),
            SeatConfig(ControllerType.BOT, "Bot 4"),
        ],
        bot_policy=RandomLegalBot(),
    ).state
    state = service.advance(state).state
    for _ in range(4000):
        if state.status.value == "finished":
            break
        decision = state.pending_decision
        assert decision is not None
        view = service.view_for(state, decision.player_id)
        dumped = to_view_response(view).model_dump(mode="json")
        option_ids = pick(dumped)
        command = build_command_from_selection(view, decision, tuple(option_ids))
        outcome = service.dispatch(state, command)
        state = service.advance(outcome.state).state

    assert state == http_state


def test_the_browser_may_send_the_authorization_header_cross_origin(http) -> None:
    response = http.options(
        f"{API}/mp/games/anything/view",
        headers={
            "Origin": "https://www.dope-game.it",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_the_room_tells_the_caller_which_seat_is_theirs_if_the_token_is_valid(http) -> None:
    marco = FakeHuman(http, create_room(http, humans=2))
    luca = FakeHuman.join(http, marco.room_code, "Luca")
    elsewhere = FakeHuman(http, create_room(http, humans=2, nickname="Zoe"))

    anonymous = http.get(f"{API}/rooms/{marco.room_code}").json()
    as_luca = http.get(f"{API}/rooms/{marco.room_code}", headers=luca.headers).json()
    as_marco = http.get(f"{API}/rooms/{marco.room_code}", headers=marco.headers).json()
    wrong_room = http.get(f"{API}/rooms/{marco.room_code}", headers=elsewhere.headers).json()
    garbage = http.get(
        f"{API}/rooms/{marco.room_code}", headers={"Authorization": "Bearer nonsense"}
    ).json()

    assert anonymous["me"] is None and wrong_room["me"] is None and garbage["me"] is None
    assert as_luca["me"]["seat_index"] == 1 and as_luca["me"]["nickname"] == "Luca"
    assert as_marco["me"]["is_host"] is True
    assert luca.token not in json.dumps([anonymous, as_marco, as_luca])
