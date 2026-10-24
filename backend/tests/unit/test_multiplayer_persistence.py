"""Multiplayer rooms kept outside the process (docs/architecture/GPT_MULTIPLAYER.md sections
43-46): a room survives a restart, an abandoned one is dropped, and a store that misbehaves never
costs the players their game.

A "restart" here is a second `MultiplayerService` (new registry, new `GameService`) over the same
store: the first one is simply never used again.
"""

from __future__ import annotations

import json
import logging
import os
import threading

import pytest

from dope_engine.application.game_service import GameService
from dope_engine.application.multiplayer.models import (
    CLOSED_GRACE_SECONDS,
    FINISHED_GRACE_SECONDS,
    LOBBY_IDLE_SECONDS,
    RUNNING_IDLE_SECONDS,
    MultiplayerError,
    RoomStatus,
)
from dope_engine.application.multiplayer.registry import GameRegistry
from dope_engine.application.multiplayer.service import MultiplayerService
from dope_engine.application.multiplayer.store import (
    InMemorySessionStore,
    SessionRecord,
    SnapshotWriter,
)
from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.domain.ids import GameId

NAMES = ["Marco", "Luca", "Anna", "Sara"]


class Clock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def start_service(
    game_data, store, *, clock: Clock | None = None, synchronous: bool = True
) -> tuple[MultiplayerService, GameService]:
    """A backend process: fresh registry and fresh GameService, whatever the store holds."""
    game_service = GameService(game_data, bot_policy=RandomLegalBot())
    counter = iter(range(1, 1000))
    service = MultiplayerService(
        registry=GameRegistry(),
        service_for_ruleset=lambda ruleset: game_service,
        bot_policy_factory=lambda name, ruleset: RandomLegalBot(),
        rulesets={"standard"},
        bot_policies={"random_legal"},
        seed_factory=lambda: 7,
        game_id_factory=lambda: GameId(f"persisted-game-{next(counter)}"),
        clock=clock or Clock(),
        store=store,
        synchronous_saves=synchronous,
    )
    return service, game_service


class Table:
    def __init__(self, service: MultiplayerService, humans: int = 2) -> None:
        self.service = service
        host = service.create_room(
            ruleset="standard", human_seats=humans, bot_policy="random_legal", nickname="Marco"
        )
        self.room_code = host.room_code
        self.credentials = [host]
        for name in NAMES[1:humans]:
            self.credentials.append(service.join_room(self.room_code, name))
        self.game_id = ""

    def start(self) -> None:
        self.service.start_room(self.room_code, self.credentials[0].seat_token)
        game_id = self.service.room_info(self.room_code).game_id
        assert game_id is not None
        self.game_id = game_id

    def token(self, seat: int) -> str:
        return self.credentials[seat].seat_token


def act(service: MultiplayerService, game_id: str, token: str) -> None:
    snapshot = service.snapshot(game_id, token)
    decision = snapshot.view.pending_decision
    assert decision is not None
    selection = RandomLegalBot().select_option_ids(snapshot.view, decision)
    service.answer(
        game_id,
        token,
        decision_id=decision.decision_id,
        selected_option_ids=list(selection),
        expected_revision=snapshot.revision,
    )


def play(service: MultiplayerService, game_id: str, tokens: list[str], steps: int = 1500) -> int:
    """Plays human decisions (whoever is awaited) until the game ends or `steps` are spent."""
    for done in range(steps):
        awaiting = service.snapshot(game_id, tokens[0]).awaiting_player_id
        if awaiting is None:
            return done
        act(service, game_id, tokens[int(awaiting.split("_")[1])])
    return steps


# --------------------------------------------------------------------- lobbies


def test_a_lobby_survives_a_restart(game_data) -> None:
    store = InMemorySessionStore()
    before, _ = start_service(game_data, store)
    host = before.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )

    after, _ = start_service(game_data, store)
    room = after.room_info(host.room_code)
    assert room.status is RoomStatus.LOBBY
    assert [seat.nickname for seat in room.seats] == ["Marco", None, "Bot 3", "Bot 4"]
    # The host's own token still opens their seat...
    info, me = after.room_for_caller(host.room_code, host.seat_token)
    assert me is not None and me.seat_index == 0 and me.is_host
    # ...and the room carries on: the other human joins and the host starts the game.
    guest = after.join_room(host.room_code, "Luca")
    assert guest.seat_index == 1
    after.start_room(host.room_code, host.seat_token)
    assert after.room_info(host.room_code).status is RoomStatus.RUNNING


def test_the_host_closing_a_lobby_takes_it_out_of_the_store(game_data) -> None:
    store = InMemorySessionStore()
    service, _ = start_service(game_data, store)
    host = service.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )
    assert store.exists(host.room_code)

    service.leave(host.room_code, host.seat_token)

    assert not store.exists(host.room_code)
    restarted, _ = start_service(game_data, store)
    with pytest.raises(MultiplayerError) as excinfo:
        restarted.room_info(host.room_code)
    assert excinfo.value.code == "room_not_found"


# ---------------------------------------------------------------------- games


def test_a_running_game_survives_a_restart_and_can_be_finished(game_data) -> None:
    store = InMemorySessionStore()
    before, _ = start_service(game_data, store)
    table = Table(before, humans=2)
    table.start()
    tokens = [c.seat_token for c in table.credentials]
    play(before, table.game_id, tokens, steps=25)
    seen = before.snapshot(table.game_id, tokens[0])
    seen_other = before.snapshot(table.game_id, tokens[1])

    after, _ = start_service(game_data, store)
    resumed = after.snapshot(table.game_id, tokens[0])
    resumed_other = after.snapshot(table.game_id, tokens[1])

    assert resumed.revision == seen.revision
    assert resumed.awaiting_player_id == seen.awaiting_player_id
    assert resumed.view.own_hand_card_ids == seen.view.own_hand_card_ids
    assert resumed_other.view.own_hand_card_ids == seen_other.view.own_hand_card_ids
    if seen.view.pending_decision is not None:
        assert resumed.view.pending_decision is not None
        assert resumed.view.pending_decision.decision_id == seen.view.pending_decision.decision_id
    # The rest of the game is played on the restarted process, and it ends.
    play(after, table.game_id, tokens)
    final = after.snapshot(table.game_id, tokens[0])
    assert final.status is RoomStatus.FINISHED
    assert final.view.status == "finished"


def test_a_restored_game_answers_to_the_same_tokens_and_to_nobody_else(game_data) -> None:
    store = InMemorySessionStore()
    before, _ = start_service(game_data, store)
    table = Table(before, humans=2)
    table.start()
    play(before, table.game_id, [c.seat_token for c in table.credentials], steps=5)

    after, _ = start_service(game_data, store)

    with pytest.raises(MultiplayerError) as excinfo:
        after.snapshot(table.game_id, "not-a-token-of-this-game")
    assert excinfo.value.code == "invalid_token"
    assert after.snapshot(table.game_id, table.token(1)).me.seat_index == 1


def test_a_seat_that_left_stays_a_bot_after_a_restart(game_data) -> None:
    store = InMemorySessionStore()
    before, _ = start_service(game_data, store)
    table = Table(before, humans=2)
    table.start()
    before.leave(table.room_code, table.token(1))

    after, _ = start_service(game_data, store)

    room = after.room_info(table.room_code)
    assert room.seats[1].left and room.seats[1].controller_type.value == "bot"
    with pytest.raises(MultiplayerError) as excinfo:
        after.snapshot(table.game_id, table.token(1))
    assert excinfo.value.code == "invalid_token"
    # The one human left plays on against four bots.
    play(after, table.game_id, [table.token(0)] * 4)
    assert after.snapshot(table.game_id, table.token(0)).status is RoomStatus.FINISHED


def test_a_finished_game_is_taken_out_of_the_store(game_data) -> None:
    store = InMemorySessionStore()
    service, _ = start_service(game_data, store)
    table = Table(service, humans=2)
    table.start()
    assert store.exists(table.room_code)

    play(service, table.game_id, [c.seat_token for c in table.credentials])

    assert service.snapshot(table.game_id, table.token(0)).status is RoomStatus.FINISHED
    assert not store.exists(table.room_code)


def test_a_client_that_missed_the_restart_is_sent_the_board_as_it_is(game_data) -> None:
    store = InMemorySessionStore()
    before, _ = start_service(game_data, store)
    table = Table(before, humans=2)
    table.start()
    play(before, table.game_id, [c.seat_token for c in table.credentials], steps=10)
    revision = before.snapshot(table.game_id, table.token(0)).revision

    after, _ = start_service(game_data, store)
    behind = after.events_since(table.game_id, table.token(0), revision - 3, include_view=True)
    ahead = after.events_since(table.game_id, table.token(0), revision + 5, include_view=True)

    # The log did not survive: no batches, but the current board, which is what the client needs.
    assert behind.batches == () and behind.view is not None
    assert behind.current_revision == revision and not behind.requires_refresh
    assert behind.view.revision == revision
    # A client that had seen more than was saved (the process died before the last write) is told.
    assert ahead.requires_refresh and ahead.current_revision == revision


def test_the_snapshot_holds_token_hashes_never_tokens(game_data) -> None:
    store = InMemorySessionStore()
    service, _ = start_service(game_data, store)
    table = Table(service, humans=2)
    table.start()
    play(service, table.game_id, [c.seat_token for c in table.credentials], steps=3)

    record = store.records[table.room_code]
    dumped = json.dumps(record.payload)

    for credentials in table.credentials:
        assert credentials.seat_token not in dumped
    assert len(record.token_hashes) == 2
    assert all(token_hash in dumped for token_hash in record.token_hashes)


# ----------------------------------------------------------------- store rules


def record(room_code: str, revision: int, **payload) -> SessionRecord:
    return SessionRecord(
        room_code=room_code,
        status="running",
        revision=revision,
        token_hashes=("hash-" + room_code,),
        payload={"revision": revision, **payload},
    )


def test_an_older_snapshot_never_replaces_a_newer_one() -> None:
    store = InMemorySessionStore()
    store.save(record("ABCD", 10))
    store.save(record("ABCD", 7))
    store.save(record("ABCD", 10, note="same revision: the later one wins"))

    stored = store.load_by_room_code("ABCD")
    assert stored is not None and stored.revision == 10
    assert stored.payload["note"] == "same revision: the later one wins"


def test_a_room_asleep_in_the_store_keeps_its_code(game_data) -> None:
    registry = GameRegistry()

    code = registry.new_room_code(lambda candidate: not candidate.startswith("A"))

    assert code.startswith("A")


def test_two_requests_for_a_sleeping_room_restore_it_once(game_data) -> None:
    store = InMemorySessionStore()
    before, _ = start_service(game_data, store)
    host = before.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )
    after, _ = start_service(game_data, store)
    barrier = threading.Barrier(6)
    errors: list[BaseException] = []

    def ask() -> None:
        try:
            barrier.wait()
            after.room_info(host.room_code)
            after.room_for_caller(host.room_code, host.seat_token)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=ask) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert len(after.registry.sessions()) == 1


class CountingStore(InMemorySessionStore):
    def __init__(self) -> None:
        super().__init__()
        self.token_lookups = 0
        self.room_lookups = 0

    def load_by_token_hash(self, token_hash: str):
        self.token_lookups += 1
        return super().load_by_token_hash(token_hash)

    def load_by_room_code(self, room_code: str):
        self.room_lookups += 1
        return super().load_by_room_code(room_code)


def test_a_token_or_room_nobody_knows_is_not_looked_up_over_and_over(game_data) -> None:
    store = CountingStore()
    clock = Clock()
    service, _ = start_service(game_data, store, clock=clock)

    for _ in range(5):
        for call in (
            lambda: service.snapshot("some-game", "unknown-token"),
            lambda: service.room_info("ZZZZ"),
        ):
            with pytest.raises(MultiplayerError):
                call()

    assert store.token_lookups == 1 and store.room_lookups == 1
    clock.advance(60)  # a lookup is allowed again after a while
    with pytest.raises(MultiplayerError):
        service.room_info("ZZZZ")
    assert store.room_lookups == 2


# ----------------------------------------------------------------- idle rooms


def test_an_abandoned_lobby_is_dropped_but_a_watched_one_is_not(game_data) -> None:
    store = InMemorySessionStore()
    clock = Clock()
    service, _ = start_service(game_data, store, clock=clock)
    abandoned = service.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )
    watched = service.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Anna"
    )

    clock.advance(LOBBY_IDLE_SECONDS - 60)
    service.room_for_caller(watched.room_code, watched.seat_token)  # somebody is looking
    clock.advance(120)
    dropped = service.purge_idle()

    assert dropped == [abandoned.room_code]
    with pytest.raises(MultiplayerError):
        service.room_info(abandoned.room_code)
    assert service.room_info(watched.room_code).status is RoomStatus.LOBBY
    assert not store.exists(abandoned.room_code) and store.exists(watched.room_code)


def test_a_running_game_nobody_plays_or_watches_is_dropped_with_everything_kept_for_it(
    game_data,
) -> None:
    store = InMemorySessionStore()
    clock = Clock()
    service, game_service = start_service(game_data, store, clock=clock)
    table = Table(service, humans=2)
    table.start()
    assert table.game_id in game_service._bot_policy_by_game_id

    clock.advance(RUNNING_IDLE_SECONDS - 60)
    assert service.purge_idle() == []
    clock.advance(120)
    assert service.purge_idle() == [table.room_code]

    assert table.game_id not in game_service._bot_policy_by_game_id
    assert table.game_id not in game_service._command_history
    assert not store.exists(table.room_code)
    with pytest.raises(MultiplayerError) as excinfo:
        service.snapshot(table.game_id, table.token(0))
    assert excinfo.value.code == "invalid_token"


def test_finished_and_closed_rooms_get_a_short_grace_period(game_data) -> None:
    store = InMemorySessionStore()
    clock = Clock()
    service, _ = start_service(game_data, store, clock=clock)
    table = Table(service, humans=2)
    table.start()
    play(service, table.game_id, [c.seat_token for c in table.credentials])
    closed = service.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Anna"
    )
    service.leave(closed.room_code, closed.seat_token)

    clock.advance(CLOSED_GRACE_SECONDS - 5)
    assert service.purge_idle() == []
    clock.advance(10)
    assert service.purge_idle() == [closed.room_code]
    clock.advance(FINISHED_GRACE_SECONDS)
    assert service.purge_idle() == [table.room_code]


def test_a_room_somebody_is_acting_on_is_not_purged(game_data) -> None:
    clock = Clock()
    service, _ = start_service(game_data, InMemorySessionStore(), clock=clock)
    host = service.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )
    session = service.registry.room(host.room_code)
    clock.advance(LOBBY_IDLE_SECONDS + 1)

    with session.lock:
        assert service.purge_idle() == []
    assert service.purge_idle() == [host.room_code]


def test_creating_a_room_drops_the_idle_ones_now_and_then(game_data) -> None:
    clock = Clock()
    service, _ = start_service(game_data, InMemorySessionStore(), clock=clock)
    old = service.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )

    clock.advance(LOBBY_IDLE_SECONDS + 120)
    service.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Anna"
    )

    assert old.room_code not in [s.room_code for s in service.registry.sessions()]


def test_a_snapshot_too_old_is_not_brought_back_and_is_deleted(game_data) -> None:
    store = InMemorySessionStore()
    clock = Clock()
    before, _ = start_service(game_data, store, clock=clock)
    host = before.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )

    clock.advance(LOBBY_IDLE_SECONDS + 60)
    after, _ = start_service(game_data, store, clock=clock)

    with pytest.raises(MultiplayerError) as excinfo:
        after.room_for_caller(host.room_code, host.seat_token)
    assert excinfo.value.code == "room_not_found"
    assert not store.exists(host.room_code)


# ------------------------------------------------------------ misbehaving stores


class BrokenStore(InMemorySessionStore):
    def save(self, record: SessionRecord) -> None:
        raise RuntimeError("password=hunter2 and a whole hand of card_customer_priests_012")

    def load_by_room_code(self, room_code: str):
        raise RuntimeError("down")

    def load_by_token_hash(self, token_hash: str):
        raise RuntimeError("down")

    def exists(self, room_code: str) -> bool:
        raise RuntimeError("down")


def test_a_store_that_fails_never_costs_the_players_their_game(game_data, caplog) -> None:
    service, _ = start_service(game_data, BrokenStore())
    with caplog.at_level(logging.WARNING):
        table = Table(service, humans=2)
        table.start()
        play(service, table.game_id, [c.seat_token for c in table.credentials])
        with pytest.raises(MultiplayerError) as excinfo:
            service.room_info("ZZZZ")

    assert service.snapshot(table.game_id, table.token(0)).status is RoomStatus.FINISHED
    # A room that cannot be looked up is "try again", never "it does not exist".
    assert excinfo.value.code == "store_unavailable"
    assert "failed" in caplog.text
    # What the log says about a failure is its kind: a database error can quote the row it refused.
    assert "hunter2" not in caplog.text and "card_customer" not in caplog.text


class FlakyStore(InMemorySessionStore):
    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures = failures
        self.attempts = 0

    def save(self, record: SessionRecord) -> None:
        self.attempts += 1
        if self.failures > 0:
            self.failures -= 1
            raise RuntimeError("down")
        super().save(record)


def test_the_writer_tries_again_when_the_store_comes_back() -> None:
    store = FlakyStore(failures=2)
    waits: list[float] = []
    writer = SnapshotWriter(store, sleep=waits.append)

    writer.save(record("ABCD", 1))

    assert writer.flush()
    writer.close()
    assert store.exists("ABCD") and store.attempts == 3
    assert waits == [1.0, 2.0]


def test_the_writer_gives_up_on_a_store_that_stays_down(caplog) -> None:
    store = FlakyStore(failures=100)
    writer = SnapshotWriter(store, sleep=lambda _: None)

    with caplog.at_level(logging.ERROR, logger="dope.multiplayer.store"):
        writer.save(record("ABCD", 1))
        assert writer.flush()
    writer.close()

    assert store.attempts == 5 and not store.exists("ABCD")
    assert "giving up" in caplog.text


class SlowStore(InMemorySessionStore):
    def __init__(self) -> None:
        super().__init__()
        self.release = threading.Event()
        self.started = threading.Event()
        self.written: list[int] = []

    def save(self, record: SessionRecord) -> None:
        self.written.append(record.revision)
        self.started.set()
        self.release.wait(5)
        super().save(record)


def test_the_writer_keeps_only_the_latest_snapshot_of_a_room() -> None:
    store = SlowStore()
    writer = SnapshotWriter(store)

    writer.save(record("ABCD", 1))
    assert store.started.wait(5)  # the first one is being written (slowly)
    for revision in range(2, 8):
        writer.save(record("ABCD", revision))
    store.release.set()

    assert writer.flush()
    writer.close()
    assert store.written == [1, 7]
    stored = store.load_by_room_code("ABCD")
    assert stored is not None and stored.revision == 7


def test_a_delete_replaces_a_save_that_was_not_written_yet() -> None:
    store = SlowStore()
    writer = SnapshotWriter(store)

    writer.save(record("AAAA", 1))
    assert store.started.wait(5)
    writer.save(record("BBBB", 1))
    writer.delete("BBBB")
    store.release.set()

    assert writer.flush()
    writer.close()
    assert store.exists("AAAA") and not store.exists("BBBB")
    assert store.written == [1]


def test_close_writes_what_is_waiting(game_data) -> None:
    store = InMemorySessionStore()
    service, _ = start_service(game_data, store, synchronous=False)
    service.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )

    service.close()

    assert len(store.records) == 1


# ------------------------------------------------------------ the real database
#
# Needs a Postgres of its own: set DOPE_TEST_DB_URL to a throwaway database (the tests empty the
# `mp_sessions` table of it). Without it they are skipped, like the rest of the suite never needs a
# database. For example:
#   docker run -d --name dope-pg-test -e POSTGRES_PASSWORD=test -p 54329:5432 postgres:16-alpine
#   DOPE_TEST_DB_URL=postgresql://postgres:test@localhost:54329/postgres pytest -k postgres

needs_postgres = pytest.mark.skipif(
    not os.environ.get("DOPE_TEST_DB_URL"), reason="DOPE_TEST_DB_URL is not set"
)


@pytest.fixture()
def postgres_store():
    from dope_engine.adapters.persistence.multiplayer_store import PostgresSessionStore

    store = PostgresSessionStore(os.environ["DOPE_TEST_DB_URL"])
    assert store.enabled
    with store._pool.connection() as conn:
        conn.execute("DELETE FROM mp_sessions")
    yield store
    store.close()


@needs_postgres
def test_postgres_store_saves_finds_and_deletes_rooms(postgres_store) -> None:
    store = postgres_store
    payload = {"nested": {"numbers": [1, 2.5, None], "text": "ciao"}, "flag": True}

    store.save(record("ABCD", 4, **payload))

    by_code = store.load_by_room_code("ABCD")
    assert by_code is not None
    assert by_code.revision == 4 and by_code.status == "running"
    assert by_code.payload["nested"] == payload["nested"] and by_code.payload["flag"] is True
    by_token = store.load_by_token_hash("hash-ABCD")
    assert by_token is not None and by_token.room_code == "ABCD"
    assert store.load_by_token_hash("hash-nobody") is None
    assert store.exists("ABCD") and not store.exists("WXYZ")
    store.delete("ABCD")
    assert not store.exists("ABCD")
    store.delete("ABCD")  # deleting what is not there is fine


@needs_postgres
def test_postgres_store_never_lets_an_older_snapshot_replace_a_newer_one(postgres_store) -> None:
    store = postgres_store

    store.save(record("ABCD", 10))
    store.save(record("ABCD", 7))
    stored = store.load_by_room_code("ABCD")
    assert stored is not None and stored.revision == 10

    store.save(record("ABCD", 10, note="later, same revision"))
    store.save(record("ABCD", 11))
    stored = store.load_by_room_code("ABCD")
    assert stored is not None and stored.revision == 11


@needs_postgres
def test_a_game_survives_a_restart_through_postgres(game_data, postgres_store) -> None:
    from dope_engine.adapters.persistence.multiplayer_store import PostgresSessionStore

    before, _ = start_service(game_data, postgres_store, synchronous=False)
    table = Table(before, humans=2)
    table.start()
    tokens = [c.seat_token for c in table.credentials]
    play(before, table.game_id, tokens, steps=20)
    assert before.flush_persistence()
    seen = before.snapshot(table.game_id, tokens[0])

    restarted_store = PostgresSessionStore(os.environ["DOPE_TEST_DB_URL"])
    after, _ = start_service(game_data, restarted_store)
    resumed = after.snapshot(table.game_id, tokens[0])

    assert resumed.revision == seen.revision
    assert resumed.view.own_hand_card_ids == seen.view.own_hand_card_ids
    play(after, table.game_id, tokens)
    assert after.snapshot(table.game_id, tokens[0]).status is RoomStatus.FINISHED
    assert not restarted_store.exists(table.room_code)
    restarted_store.close()
    before.close()


class FlakyReadStore(InMemorySessionStore):
    def __init__(self) -> None:
        super().__init__()
        self.down = False

    def load_by_token_hash(self, token_hash: str):
        if self.down:
            raise RuntimeError("down")
        return super().load_by_token_hash(token_hash)


def test_a_player_whose_room_cannot_be_read_yet_is_told_to_retry_not_to_give_up(
    game_data,
) -> None:
    store = FlakyReadStore()
    before, _ = start_service(game_data, store)
    table = Table(before, humans=2)
    table.start()
    store.down = True
    after, _ = start_service(game_data, store)

    with pytest.raises(MultiplayerError) as excinfo:
        after.snapshot(table.game_id, table.token(0))
    assert excinfo.value.code == "store_unavailable"

    store.down = False  # the database is back: the very next poll finds the game
    assert after.snapshot(table.game_id, table.token(0)).status is RoomStatus.RUNNING
