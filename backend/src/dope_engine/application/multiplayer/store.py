"""Keeping rooms and games outside the process (docs/architecture/GPT_MULTIPLAYER.md sections
43-46): a snapshot of every room is saved after each operation that changes it, and a room that is
asked for after a restart is read back from there.

The application layer only knows the `SessionStore` port. Real storage is an adapter
(`adapters/persistence/multiplayer_store.py`); `NullSessionStore` keeps nothing (local development,
most tests) and `InMemorySessionStore` stands in for a database in tests.

Saving never sits in the way of play: `SnapshotWriter` hands records to a background thread that
keeps only the latest one per room, and a store that fails is logged and retried a few times, never
raised into a request. What the log says is limited to the room code and the kind of failure: a
record holds hands and hashes, and a database error can quote the row it refused.
"""

from __future__ import annotations

import copy
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger("dope.multiplayer.store")

# The shape of `SessionRecord.payload`; bump it (and migrate) when it changes.
SNAPSHOT_FORMAT_VERSION = 1


@dataclass(frozen=True)
class SessionRecord:
    """One room as it is stored. `payload` is the whole snapshot (JSON-friendly); the other fields
    are what a store needs to find and order it without opening the payload."""

    room_code: str
    status: str
    # Of the game; 0 in a lobby. A store never lets an older record replace a newer one.
    revision: int
    # SHA-256 of each seat token (never the tokens): how a returning player's seat is found.
    token_hashes: tuple[str, ...]
    payload: dict[str, Any]


class SessionStore(Protocol):
    # False for a store that keeps nothing: the service then does not even build snapshots.
    enabled: bool

    def save(self, record: SessionRecord) -> None: ...

    def load_by_room_code(self, room_code: str) -> SessionRecord | None: ...

    def load_by_token_hash(self, token_hash: str) -> SessionRecord | None: ...

    def exists(self, room_code: str) -> bool: ...

    def delete(self, room_code: str) -> None: ...


class NullSessionStore:
    """Keeps nothing: rooms live and die with the process."""

    enabled = False

    def save(self, record: SessionRecord) -> None:
        return None

    def load_by_room_code(self, room_code: str) -> SessionRecord | None:
        return None

    def load_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        return None

    def exists(self, room_code: str) -> bool:
        return False

    def delete(self, room_code: str) -> None:
        return None


class InMemorySessionStore:
    """A store in a dict, with the same rules as the real one (an older revision never replaces a
    newer one): what tests use to restart a service without a database."""

    enabled = True

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.records: dict[str, SessionRecord] = {}
        self.save_count = 0

    def save(self, record: SessionRecord) -> None:
        with self._lock:
            current = self.records.get(record.room_code)
            if current is not None and current.revision > record.revision:
                return
            self.records[record.room_code] = copy.deepcopy(record)
            self.save_count += 1

    def load_by_room_code(self, room_code: str) -> SessionRecord | None:
        with self._lock:
            record = self.records.get(room_code)
            return copy.deepcopy(record) if record is not None else None

    def load_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        with self._lock:
            for record in self.records.values():
                if token_hash in record.token_hashes:
                    return copy.deepcopy(record)
        return None

    def exists(self, room_code: str) -> bool:
        with self._lock:
            return room_code in self.records

    def delete(self, room_code: str) -> None:
        with self._lock:
            self.records.pop(room_code, None)


# How many times a failed write is tried again (waiting 1, 2, 4... seconds, at most MAX_RETRY_WAIT)
# before it is given up on; a newer record for the same room replaces it meanwhile.
MAX_WRITE_ATTEMPTS = 5
MAX_RETRY_WAIT_SECONDS = 30.0


class SnapshotWriter:
    """Writes records to a store from a background thread, latest one per room.

    A room that changes ten times while the store is slow is written once, with its newest state;
    a delete replaces a save that has not been written yet. `flush()` waits until everything handed
    in so far is written (shutdown, tests). With `synchronous=True` nothing is deferred: each call
    writes right there (tests that need a deterministic order)."""

    def __init__(
        self,
        store: SessionStore,
        *,
        synchronous: bool = False,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._store = store
        self._synchronous = synchronous
        self._sleep = sleep
        self._cond = threading.Condition()
        # room code -> the record to save, or None for "delete". Insertion order = oldest first.
        self._pending: dict[str, SessionRecord | None] = {}
        self._attempts: dict[str, int] = {}
        self._busy = False
        self._closed = False
        self._thread: threading.Thread | None = None

    def save(self, record: SessionRecord) -> None:
        self._submit(record.room_code, record)

    def delete(self, room_code: str) -> None:
        self._submit(room_code, None)

    def flush(self, timeout: float = 10.0) -> bool:
        """True once every record handed in so far has been written (or given up on)."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while self._pending or self._busy:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cond.wait(remaining)
        return True

    def close(self, timeout: float = 10.0) -> None:
        """Writes what is left, then stops the thread."""
        self.flush(timeout)
        with self._cond:
            self._closed = True
            self._cond.notify_all()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    # -- internals

    def _submit(self, room_code: str, record: SessionRecord | None) -> None:
        if self._synchronous:
            self._write(room_code, record)
            return
        with self._cond:
            if self._closed:
                return
            # Re-inserting keeps the newest change last in line.
            self._pending.pop(room_code, None)
            self._pending[room_code] = record
            self._attempts.pop(room_code, None)
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run, name="mp-snapshot-writer", daemon=True
                )
                self._thread.start()
            self._cond.notify_all()

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._pending and not self._closed:
                    self._cond.wait()
                if not self._pending:
                    return
                room_code = next(iter(self._pending))
                record = self._pending.pop(room_code)
                self._busy = True
            try:
                if not self._write(room_code, record):
                    # Still "busy" while it waits, so flush() does not take the room for saved.
                    self._retry_later(room_code, record)
            finally:
                with self._cond:
                    self._busy = False
                    self._cond.notify_all()

    def _retry_later(self, room_code: str, record: SessionRecord | None) -> None:
        with self._cond:
            attempts = self._attempts.get(room_code, 0) + 1
            if room_code in self._pending:
                # A newer change came in while this one was failing: it supersedes it.
                self._attempts.pop(room_code, None)
                return
            if attempts >= MAX_WRITE_ATTEMPTS:
                self._attempts.pop(room_code, None)
                logger.error("giving up saving room=%s after %d attempts", room_code, attempts)
                return
            self._attempts[room_code] = attempts
        self._sleep(min(2.0 ** (attempts - 1), MAX_RETRY_WAIT_SECONDS))
        with self._cond:
            if room_code not in self._pending and not self._closed:
                self._pending[room_code] = record

    def _write(self, room_code: str, record: SessionRecord | None) -> bool:
        try:
            if record is None:
                self._store.delete(room_code)
            else:
                self._store.save(record)
        except Exception as exc:  # noqa: BLE001 - a store failure must never reach a request
            logger.warning("saving room=%s failed (%s)", room_code, type(exc).__name__)
            return False
        return True
