"""A scripted "browser" for the multiplayer HTTP API (docs/architecture/GPT_MULTIPLAYER.md sections
31-32): it holds one seat token and talks to the server only through HTTP, exactly like the real
client will — view, poll the event log, answer decisions. The choices are random but legal, so a
whole game can be played to prove the protocol, not to play well.
"""

from __future__ import annotations

import random
import time
from typing import Any

from starlette.testclient import TestClient
from test_http_app import _select_options  # the existing "pick a jointly legal selection" helper

API = "/api/v1"


def create_room(
    http: TestClient,
    *,
    humans: int,
    bot_policy: str = "random_legal",
    ruleset: str = "standard",
    nickname: str = "Marco",
) -> dict[str, Any]:
    response = http.post(
        f"{API}/rooms",
        json={
            "ruleset": ruleset,
            "human_seats": humans,
            "bot_policy": bot_policy,
            "nickname": nickname,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


class FakeHuman:
    def __init__(
        self,
        http: TestClient,
        credentials: dict[str, Any],
        *,
        rng: random.Random | None = None,
        pass_probability: float = 0.0,
    ) -> None:
        self.http = http
        self.room_code: str = credentials["room_code"]
        self.seat_index: int = credentials["seat_index"]
        self.player_id: str = credentials["player_id"]
        self.token: str = credentials["seat_token"]
        self.game_id: str | None = credentials.get("game_id")
        self.rng = rng or random.Random(self.seat_index)
        self.pass_probability = pass_probability
        self.last_seen_revision = 0
        self.batches: list[dict[str, Any]] = []
        self.rejections: list[dict[str, Any]] = []

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    # ------------------------------------------------------------------ lobby

    @classmethod
    def join(cls, http: TestClient, room_code: str, nickname: str, **kwargs: Any) -> FakeHuman:
        response = http.post(f"{API}/rooms/{room_code}/join", json={"nickname": nickname})
        assert response.status_code == 200, response.text
        return cls(http, response.json(), **kwargs)

    def start(self) -> dict[str, Any]:
        response = self.http.post(f"{API}/rooms/{self.room_code}/start", headers=self.headers)
        assert response.status_code == 200, response.text
        room = response.json()
        self.game_id = room["game_id"]
        return room

    def learn_game_id(self) -> str:
        if self.game_id is None:
            self.game_id = self.http.get(f"{API}/rooms/{self.room_code}").json()["game_id"]
        assert self.game_id is not None
        return self.game_id

    # ------------------------------------------------------------------- game

    def view(self) -> dict[str, Any]:
        response = self.http.get(
            f"{API}/mp/games/{self.learn_game_id()}/view", headers=self.headers
        )
        assert response.status_code == 200, response.text
        return response.json()

    def poll(self) -> dict[str, Any]:
        """Asks for what happened since the last poll; keeps the batches it was given."""
        response = self.http.get(
            f"{API}/mp/games/{self.learn_game_id()}/events",
            params={"since": self.last_seen_revision},
            headers=self.headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        self.batches.extend(body["batches"])
        self.last_seen_revision = body["current_revision"]
        return body

    def choose(self, snapshot: dict[str, Any]) -> list[str]:
        """A random but legal selection for the decision in `snapshot`."""
        view = snapshot["view"]
        decision = view["pending_decision"]
        if (
            decision["can_pass"]
            and decision["min_selections"] == 0
            and self.rng.random() < self.pass_probability
        ):
            return []
        options = list(decision["options"])
        if decision["decision_type"] not in (
            "move_criminal",
            "sell_dope",
            "buy_dope",
            "maneuver_officer",
            "place_criminal",
        ):
            self.rng.shuffle(options)
        shuffled = {**decision, "options": options}
        selected = _select_options(shuffled, view)
        if decision["decision_type"] == "place_criminal":
            # The SCOUT card lets exactly one pawn go to a face-down Hood: never pick two.
            kept: list[dict[str, Any]] = []
            for option in selected:
                if option["payload"].get("hidden") and any(
                    k["payload"].get("hidden") for k in kept
                ):
                    continue
                kept.append(option)
            selected = kept
        return [option["option_id"] for option in selected]

    def act(self, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        """Answers the pending decision (which must be this player's)."""
        snapshot = snapshot or self.view()
        decision = snapshot["view"]["pending_decision"]
        assert decision is not None, "no decision to answer"
        selection = self.choose(snapshot)
        response = self.http.post(
            f"{API}/mp/games/{self.learn_game_id()}/decisions/answer",
            headers=self.headers,
            json={
                "decision_id": decision["decision_id"],
                "expected_revision": snapshot["revision"],
                "selected_option_ids": selection,
            },
        )
        if response.status_code == 409:
            # Somebody else's request got in first: refresh and try again, like a client would.
            self.rejections.append(response.json())
            return response.json()
        assert response.status_code == 200, (
            f"{response.text} while answering {decision['decision_type']} "
            f"{[o['payload'] for o in decision['options'] if o['option_id'] in selection]}"
        )
        return response.json()


def play_in_turns(humans: list[FakeHuman], *, max_steps: int = 4000) -> int:
    """One request at a time: whoever the game is waiting for answers; everybody else polls."""
    by_player = {human.player_id: human for human in humans}
    steps = 0
    while steps < max_steps:
        snapshot = humans[0].view()
        if snapshot["status"] == "finished":
            for human in humans:
                human.poll()
            return steps
        actor = by_player[snapshot["awaiting_player_id"]]
        actor.act(snapshot if actor is humans[0] else None)
        for human in humans:
            human.poll()
        steps += 1
    raise AssertionError("the game did not finish")


def play_in_parallel(
    app: Any,
    credentials: list[dict[str, Any]],
    *,
    deadline_seconds: float = 180.0,
    pass_probability: float = 0.0,
) -> list[FakeHuman]:
    """Every human runs by themselves in their own thread with their own client: no coordination,
    random pauses, polling and answering whenever they think it is their turn. (Each thread keeps
    one `TestClient` open for its whole life: building a new one per request makes Windows create
    an event loop per call, and that stalls under this many threads.)"""
    import threading

    humans: list[FakeHuman | None] = [None] * len(credentials)
    errors: list[BaseException] = []
    finished = threading.Event()
    deadline = time.monotonic() + deadline_seconds

    def run(slot: int) -> None:
        try:
            with TestClient(app) as http:
                human = FakeHuman(
                    http,
                    credentials[slot],
                    rng=random.Random(100 + credentials[slot]["seat_index"]),
                    pass_probability=pass_probability,
                )
                humans[slot] = human
                while not finished.is_set() and time.monotonic() < deadline:
                    body = human.poll()
                    if body["status"] == "finished":
                        return
                    if body["awaiting_player_id"] == human.player_id:
                        human.act()
                    else:
                        time.sleep(human.rng.uniform(0.0, 0.01))
        except BaseException as exc:  # noqa: BLE001 - re-raised by the test
            errors.append(exc)
            finished.set()

    threads = [threading.Thread(target=run, args=(slot,)) for slot in range(len(credentials))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=deadline_seconds + 10)
    assert not errors, errors[0]
    assert all(not thread.is_alive() for thread in threads), "a fake human is still running"
    assert all(human is not None for human in humans)
    return [human for human in humans if human is not None]
