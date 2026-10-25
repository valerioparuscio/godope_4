"""Games recorded for later analysis (docs/architecture/telemetry.md): the solo and the multiplayer
games, their events and the progression of the Jobs, bots and humans alike.

The first part needs no database: the recorder port, the multiplayer and solo call sites, with
spies. The second part runs the real recorder against a Postgres of its own: set DOPE_TEST_DB_URL
to a throwaway database (these tests empty the telemetry tables of it), for example
    docker run -d --name dope-pg-test -e POSTGRES_PASSWORD=test -p 54329:5432 postgres:16-alpine
    DOPE_TEST_DB_URL=postgresql://postgres:test@localhost:54329/postgres pytest -k telemetry
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Sequence

import pytest
from test_multiplayer_persistence import Table, play, start_service

from dope_engine.application.multiplayer.store import InMemorySessionStore
from dope_engine.application.telemetry import BackgroundTelemetry, NullTelemetry
from dope_engine.domain.events import DomainEvent, JobBonusClaimed, JobCompleted
from dope_engine.domain.state import GameState

# --------------------------------------------------------------- the recorder port


class Spy:
    """A recorder that writes what it is asked to into a list."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.thread_names: set[str] = set()

    def game_started(self, state, *, mode, bot_policy, room_code) -> None:
        self.thread_names.add(threading.current_thread().name)
        self.calls.append(("started", state.game_id, mode, bot_policy, room_code))

    def events(self, state: GameState, events: Sequence[DomainEvent]) -> None:
        self.thread_names.add(threading.current_thread().name)
        self.calls.append(("events", state.game_id, len(events)))

    def game_finished(self, state: GameState) -> None:
        self.thread_names.add(threading.current_thread().name)
        self.calls.append(("finished", state.game_id))

    def flush(self, timeout: float = 10.0) -> bool:
        return True

    def close(self) -> None:
        self.calls.append(("closed",))


def test_the_background_recorder_runs_the_calls_in_order_from_its_own_thread() -> None:
    inner = Spy()
    background = BackgroundTelemetry(inner)
    state = _FakeState("g1")

    background.game_started(state, mode="solo", bot_policy="heuristic", room_code=None)
    for count in (3, 1, 2):
        background.events(state, [object()] * count)
    background.game_finished(state)

    assert background.flush()
    assert inner.calls == [
        ("started", "g1", "solo", "heuristic", None),
        ("events", "g1", 3),
        ("events", "g1", 1),
        ("events", "g1", 2),
        ("finished", "g1"),
    ]
    assert inner.thread_names == {"telemetry-writer"}
    background.close()
    assert inner.calls[-1] == ("closed",)


class _FakeState:
    def __init__(self, game_id: str) -> None:
        self.game_id = game_id


def test_a_recorder_that_fails_costs_nothing_and_the_next_call_still_runs(caplog) -> None:
    class Broken(Spy):
        def events(self, state, events) -> None:
            raise RuntimeError("password=hunter2 on a row with card_customer_priests_012")

    inner = Broken()
    background = BackgroundTelemetry(inner)
    with caplog.at_level(logging.WARNING, logger="dope.telemetry"):
        background.events(_FakeState("g"), [object()])
        background.game_finished(_FakeState("g"))
        assert background.flush()

    assert inner.calls == [("finished", "g")]
    assert "events failed" in caplog.text
    assert "hunter2" not in caplog.text and "card_customer" not in caplog.text
    background.close()


def test_a_full_queue_drops_calls_instead_of_waiting() -> None:
    gate = threading.Event()

    class Slow(Spy):
        def events(self, state, events) -> None:
            gate.wait(5)
            super().events(state, events)

    inner = Slow()
    background = BackgroundTelemetry(inner, max_pending=2)
    for _ in range(6):  # the first is being run (stuck), two wait, the rest are dropped
        background.events(_FakeState("g"), [object()])
    gate.set()

    assert background.flush()
    assert len(inner.calls) <= 4
    background.close()


def test_the_database_recorder_names_the_bots_class_not_the_factory() -> None:
    from dope_engine.adapters.persistence.telemetry import DbTelemetry

    class RecorderSpy:
        def __init__(self) -> None:
            self.started: list[dict] = []

        def record_game_started(self, state, **details) -> None:
            self.started.append(details)

    spy = RecorderSpy()
    telemetry = DbTelemetry(spy)  # type: ignore[arg-type]

    telemetry.game_started(_FakeState("g"), mode="multi", bot_policy="heuristic", room_code="ABCD")
    telemetry.game_started(_FakeState("g"), mode="solo", bot_policy="random_legal", room_code=None)

    assert [d["bot_type"] for d in spy.started] == ["HeuristicBot", "RandomLegalBot"]
    assert spy.started[0]["room_code"] == "ABCD" and spy.started[0]["mode"] == "multi"


def test_nothing_is_recorded_by_the_null_recorder() -> None:
    recorder = NullTelemetry()
    state = _FakeState("g")

    recorder.game_started(state, mode="solo", bot_policy=None, room_code=None)
    recorder.events(state, [])
    recorder.game_finished(state)
    assert recorder.flush() is True


# ------------------------------------------------------------- multiplayer call sites


def test_a_multiplayer_game_is_recorded_from_its_start_to_its_final_scores(game_data) -> None:
    spy = Spy()
    service, _ = start_service(game_data, InMemorySessionStore())
    service._telemetry = spy
    table = Table(service, humans=2)
    table.start()
    tokens = [c.seat_token for c in table.credentials]

    play(service, table.game_id, tokens)

    session = service.registry.room(table.room_code)
    kinds = [call[0] for call in spy.calls]
    assert kinds[0] == "started"
    assert spy.calls[0][2:] == ("multi", "random_legal", table.room_code)
    assert kinds.count("started") == 1 and kinds.count("finished") == 1
    assert kinds[-1] == "finished"
    # Every event of the log reaches the recorder, step by step.
    recorded = sum(call[2] for call in spy.calls if call[0] == "events")
    assert recorded == sum(len(batch.events) for batch in session.event_log)


def test_leaving_or_being_away_costs_the_recorder_nothing(game_data) -> None:
    spy = Spy()
    service, _ = start_service(game_data, InMemorySessionStore())
    service._telemetry = spy
    table = Table(service, humans=2)
    table.start()

    service.leave(table.room_code, table.token(1))  # a step with no events at all

    assert [call[0] for call in spy.calls].count("started") == 1


def test_closing_the_service_closes_the_recorder(game_data) -> None:
    spy = Spy()
    service, _ = start_service(game_data, InMemorySessionStore())
    service._telemetry = spy

    service.close()

    assert spy.calls[-1] == ("closed",)


# ------------------------------------------------------------------ solo call sites


def test_solo_games_of_the_recorded_rulesets_are_recorded_and_the_others_are_not(
    monkeypatch,
) -> None:
    from fastapi.testclient import TestClient

    from dope_engine.adapters.http import app as app_module

    calls: list[tuple] = []
    monkeypatch.setattr(
        app_module.db,
        "record_game_started",
        lambda state, **details: calls.append(("started", state.game_id, details)),
    )
    monkeypatch.setattr(
        app_module.db,
        "record_events",
        lambda state, events: calls.append(("events", state.game_id)),
    )
    monkeypatch.setattr(
        app_module.db,
        "record_game_finished",
        lambda state: calls.append(("finished", state.game_id)),
    )
    client = TestClient(app_module.app)

    def play_one(ruleset: str) -> str:
        created = client.post(
            "/api/v1/games",
            json={
                "human_seat": 0,
                "seed": 5,
                "nickname": "Tester",
                "ruleset": ruleset,
                "bot_policy": "heuristic",
            },
        )
        assert created.status_code == 200, created.text
        game_id = created.json()["game_id"]
        advanced = client.post(f"/api/v1/games/{game_id}/advance", params={"player_id": "player_0"})
        assert advanced.status_code == 200, advanced.text
        return game_id

    easy = play_one("easy_price")
    standard = play_one("standard")
    simple = play_one("simple")

    started = {call[1]: call[2] for call in calls if call[0] == "started"}
    assert set(started) == {easy, standard}
    assert started[easy] == {"mode": "solo", "bot_policy": "heuristic", "bot_type": "HeuristicBot"}
    # Only the recorded games send events on: the Small one has no game for them to belong to.
    sent = {call[1] for call in calls if call[0] == "events"}
    assert sent == {easy, standard} and simple not in sent


# ------------------------------------------------------------ the real recorder (Postgres)

needs_postgres = pytest.mark.skipif(
    not os.environ.get("DOPE_TEST_DB_URL"), reason="DOPE_TEST_DB_URL is not set"
)

# The three tables Supabase has had since 2026-08 (made by hand there, by this in the tests).
HAND_MADE_TABLES = """
CREATE TABLE IF NOT EXISTS games (
    id uuid PRIMARY KEY, game_version varchar, rules_version varchar, status varchar,
    started_at timestamptz, ended_at timestamptz, winner_seat int4, total_turns int4);
CREATE TABLE IF NOT EXISTS game_players (
    id bigserial PRIMARY KEY, game_id uuid REFERENCES games(id), seat int4,
    player_type varchar, character_id varchar, bot_type varchar, final_money int4, winner bool,
    money_track_position_points int4, clean_reputation_points int4,
    stained_reputation_points int4, contact_majority_points int4,
    base_chip_points int4, skill_points int4, total_points int4);
CREATE TABLE IF NOT EXISTS game_events (
    id bigserial PRIMARY KEY, game_id uuid REFERENCES games(id), turn_number int4, seat int4,
    event_type varchar, payload jsonb, created_at timestamptz);
"""


@pytest.fixture()
def recorder():
    from psycopg_pool import ConnectionPool

    from dope_engine.adapters.persistence import db

    pool = ConnectionPool(os.environ["DOPE_TEST_DB_URL"], min_size=1, max_size=2, open=True)
    with pool.connection() as conn:
        conn.execute(HAND_MADE_TABLES)
    telemetry_db = db.TelemetryDb(pool)
    with pool.connection() as conn:
        for table in (
            "game_events",
            "game_players",
            "game_job_completions",
            "game_info",
            "games",
        ):
            conn.execute(f"DELETE FROM {table}")
    yield telemetry_db
    pool.close()


def _rows(recorder, sql: str, *params):
    with recorder._pool.connection() as conn:
        return conn.execute(sql, params).fetchall()


def _record_whole_game(game_data, recorder, *, seed: int, human_name: str | None, mode: str):
    """Plays a game on the Easy Price rules, one command at a time, recording it the way the
    solo and multiplayer call sites do. With a human name the first seat is a human (answered by a
    bot policy of the test), otherwise four bots. Returns (state, the Job events, every event)."""
    from dope_engine.application.game_service import GameService
    from dope_engine.bots.policies import BOT_POLICY_BY_NAME
    from dope_engine.bots.random_legal import RandomLegalBot
    from dope_engine.domain.enums import ControllerType, GameStatus
    from dope_engine.domain.ids import GameId
    from dope_engine.rules.setup import SeatConfig

    # The heuristic bots complete Jobs in every game; random ones hardly ever do.
    bots = BOT_POLICY_BY_NAME["heuristic"](game_data)
    service = GameService(game_data, bot_policy=bots)
    seats = [
        SeatConfig(ControllerType.HUMAN, human_name)
        if index == 0 and human_name
        else SeatConfig(ControllerType.BOT, f"Bot {index + 1}")
        for index in range(4)
    ]
    game_id = GameId(f"00000000-0000-4000-8000-{seed:012d}")
    result = service.create_game_from_seats(
        game_id=game_id, seed=seed, seats=seats, bot_policy=bots
    )
    state = result.state
    recorder.record_game_started(state, mode=mode, bot_policy="heuristic", bot_type="HeuristicBot")
    all_events = list(result.events)
    recorder.record_events(state, result.events)
    job_events: list[DomainEvent] = []
    for _ in range(6000):
        if state.status is GameStatus.FINISHED:
            break
        out = service.advance(state)
        if out.state is not state:
            state = out.state
            all_events.extend(out.events)
            recorder.record_events(state, out.events)
            job_events.extend(
                e for e in out.events if isinstance(e, (JobCompleted, JobBonusClaimed))
            )
            continue
        # A human decision: answered with a legal selection.
        player_id = state.pending_decision.player_id
        view = service.view_for(state, player_id)
        decision = view.pending_decision
        selection = RandomLegalBot().select_option_ids(view, decision)
        outcome = service.answer_sequence(state, player_id, [list(selection)])
        state = outcome.state
        all_events.extend(outcome.events)
        recorder.record_events(state, outcome.events)
        job_events.extend(
            e for e in outcome.events if isinstance(e, (JobCompleted, JobBonusClaimed))
        )
    assert state.status is GameStatus.FINISHED
    recorder.record_game_finished(state)
    return state, job_events, all_events


@pytest.fixture()
def easy_price_data():
    from pathlib import Path

    from dope_engine.application.data_loader import load_game_data

    repo = Path(__file__).resolve().parents[3]
    return load_game_data(repo / "data_packs" / "easy_price", base_dir=repo / "data")


@needs_postgres
def test_a_game_is_recorded_with_its_players_events_and_job_progression(
    easy_price_data, recorder
) -> None:
    state, job_events, all_events = _record_whole_game(
        easy_price_data, recorder, seed=3, human_name="Marco", mode="solo"
    )
    game_id = str(state.game_id)

    assert _rows(recorder, "SELECT status FROM games") == [("finished",)]
    players = _rows(
        recorder,
        "SELECT seat, player_type, character_id, bot_type, total_points IS NOT NULL "
        "FROM game_players WHERE game_id = %s ORDER BY seat",
        game_id,
    )
    assert [p[:4] for p in players] == [
        (0, "human", "Marco", None),
        (1, "bot", None, "HeuristicBot"),
        (2, "bot", None, "HeuristicBot"),
        (3, "bot", None, "HeuristicBot"),
    ]
    assert all(p[4] for p in players)
    recorded_events = _rows(
        recorder, "SELECT COUNT(*) FROM game_events WHERE game_id = %s", game_id
    )
    assert recorded_events[0][0] == len(all_events)
    (info,) = _rows(
        recorder,
        "SELECT ruleset, mode, bot_policy, human_count, room_code "
        "FROM game_info WHERE game_id = %s",
        game_id,
    )
    assert info == ("easy_price", "solo", "heuristic", 1, None)

    completed = [e for e in job_events if isinstance(e, JobCompleted)]
    claimed = [e for e in job_events if isinstance(e, JobBonusClaimed)]
    assert completed, "this seed completes no Job: pick another one"
    rows = _rows(
        recorder,
        "SELECT seat, player_type, ordinal, job_id, tier, next_job_id, turn_number, phase, "
        "bonus_column_index, bonus_type, bonus_contact_id, bonus_claimed_at IS NOT NULL "
        "FROM game_job_completions WHERE game_id = %s ORDER BY id",
        game_id,
    )
    assert len(rows) == len(completed)
    seat_of = {p.player_id: p.seat_index for p in state.players}
    assert [(r[0], r[3], r[4]) for r in rows] == [
        (seat_of[e.player_id], str(e.job_id), e.tier) for e in completed
    ]
    # Bots and the human are both there, each player's Jobs numbered 1, 2, 3... in order.
    assert {r[1] for r in rows} <= {"human", "bot"}
    per_seat: dict[int, list[int]] = {}
    for row in rows:
        per_seat.setdefault(row[0], []).append(row[2])
    assert all(ordinals == list(range(1, len(ordinals) + 1)) for ordinals in per_seat.values())
    # Every reward was claimed (a game ends only after them): the column and bonus are recorded.
    assert len(claimed) == len(completed)
    assert all(row[11] for row in rows)
    assert sorted((r[8], r[9]) for r in rows) == sorted(
        (e.column_index, e.bonus_type) for e in claimed
    )


@needs_postgres
def test_a_game_of_four_bots_records_every_players_jobs_too(easy_price_data, recorder) -> None:
    state, job_events, _ = _record_whole_game(
        easy_price_data, recorder, seed=4, human_name=None, mode="multi"
    )

    rows = _rows(
        recorder,
        "SELECT DISTINCT player_type FROM game_job_completions WHERE game_id = %s",
        str(state.game_id),
    )
    assert rows == [("bot",)]
    (info,) = _rows(recorder, "SELECT mode, human_count FROM game_info")
    assert info == ("multi", 0)


@needs_postgres
def test_the_leaderboard_ranks_solo_games_and_leaves_multiplayer_ones_out(
    easy_price_data, recorder
) -> None:
    _record_whole_game(easy_price_data, recorder, seed=5, human_name="Marco", mode="solo")
    _record_whole_game(easy_price_data, recorder, seed=6, human_name="Luca", mode="multi")
    # Games recorded before there was a game_info table count as solo.
    old_style = _record_whole_game(
        easy_price_data, recorder, seed=7, human_name="Anna", mode="solo"
    )[0]
    with recorder._pool.connection() as conn:
        conn.execute("DELETE FROM game_info WHERE game_id = %s", (str(old_style.game_id),))
        conn.execute("UPDATE games SET started_at = now()")

    names = {entry["nickname"] for entry in recorder.fetch_leaderboard(limit=20)}

    assert names == {"Marco", "Anna"}


@needs_postgres
def test_without_its_own_tables_the_games_are_still_recorded_as_before(
    easy_price_data, recorder
) -> None:
    recorder._own_tables = False  # as if the two tables could not be created

    state, _jobs, all_events = _record_whole_game(
        easy_price_data, recorder, seed=3, human_name="Marco", mode="solo"
    )

    assert _rows(recorder, "SELECT COUNT(*) FROM game_events")[0][0] == len(all_events)
    assert _rows(recorder, "SELECT COUNT(*) FROM game_info")[0][0] == 0
    with recorder._pool.connection() as conn:
        conn.execute("UPDATE games SET started_at = now()")
    assert [e["nickname"] for e in recorder.fetch_leaderboard()] == ["Marco"]
