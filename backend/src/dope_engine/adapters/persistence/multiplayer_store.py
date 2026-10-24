"""Postgres store for multiplayer rooms (docs/architecture/GPT_MULTIPLAYER.md sections 43-46).

Implements the `SessionStore` port of `application/multiplayer/store.py`: one row per room in
`mp_sessions`, holding the whole snapshot as JSON next to what is needed to find it (room code,
token hashes) and to keep the newest (revision). It uses the same database as `db.py`'s telemetry
(`DOPE_DB_URL`) and, like it, is off when that is not set: `store_from_environment()` then returns
a store that keeps nothing, and local development and the test suite never need a database.

Unlike telemetry this one is read back, and it creates its own table (`CREATE TABLE IF NOT EXISTS`
at start) instead of expecting it to exist: the rest of the schema was made by hand, this is new.

An older snapshot never replaces a newer one (`WHERE revision <=`): during a deploy two processes
can briefly both hold a room, and the one that is behind must not undo the other.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dope_engine.application.multiplayer.store import (
    NullSessionStore,
    SessionRecord,
    SessionStore,
)

logger = logging.getLogger("dope.multiplayer.store")

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS mp_sessions (
    room_code    text PRIMARY KEY,
    status       text NOT NULL,
    revision     integer NOT NULL,
    token_hashes text[] NOT NULL,
    payload      jsonb NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now()
)
"""

UPSERT_SQL = """
INSERT INTO mp_sessions (room_code, status, revision, token_hashes, payload, updated_at)
VALUES (%s, %s, %s, %s, %s, now())
ON CONFLICT (room_code) DO UPDATE SET
    status = EXCLUDED.status,
    revision = EXCLUDED.revision,
    token_hashes = EXCLUDED.token_hashes,
    payload = EXCLUDED.payload,
    updated_at = now()
WHERE mp_sessions.revision <= EXCLUDED.revision
"""

_COLUMNS = "room_code, status, revision, token_hashes, payload"


def _record(row: tuple[Any, ...]) -> SessionRecord:
    room_code, status, revision, token_hashes, payload = row
    return SessionRecord(
        room_code=room_code,
        status=status,
        revision=revision,
        token_hashes=tuple(token_hashes),
        payload=payload,
    )


class PostgresSessionStore:
    enabled = True

    def __init__(self, dsn: str | None = None, *, pool: Any = None) -> None:
        if pool is None:
            from psycopg_pool import ConnectionPool

            assert dsn is not None
            pool = ConnectionPool(
                dsn,
                min_size=1,
                max_size=2,
                # Fail fast when the database is down: the writer retries, requests never wait.
                timeout=5,
                # Safe behind a transaction-mode pooler (Supabase's), which cannot keep prepared
                # statements from one query to the next.
                kwargs={"prepare_threshold": None},
                check=ConnectionPool.check_connection,
                open=True,
            )
        self._pool = pool
        try:
            with self._pool.connection() as conn:
                conn.execute(TABLE_DDL)
        except Exception as exc:  # noqa: BLE001 - no table, no persistence; the game goes on
            logger.error(
                "multiplayer persistence disabled: cannot prepare mp_sessions (%s)",
                type(exc).__name__,
            )
            self.enabled = False

    def save(self, record: SessionRecord) -> None:
        from psycopg.types.json import Jsonb

        with self._pool.connection() as conn:
            conn.execute(
                UPSERT_SQL,
                (
                    record.room_code,
                    record.status,
                    record.revision,
                    list(record.token_hashes),
                    Jsonb(record.payload),
                ),
            )

    def load_by_room_code(self, room_code: str) -> SessionRecord | None:
        return self._select("room_code = %s", room_code)

    def load_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        return self._select("%s = ANY(token_hashes)", token_hash)

    def exists(self, room_code: str) -> bool:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM mp_sessions WHERE room_code = %s", (room_code,)
            ).fetchone()
        return row is not None

    def delete(self, room_code: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM mp_sessions WHERE room_code = %s", (room_code,))

    def close(self) -> None:
        self._pool.close()

    def _select(self, condition: str, value: str) -> SessionRecord | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM mp_sessions WHERE {condition} LIMIT 1", (value,)
            ).fetchone()
        return _record(row) if row is not None else None


def store_from_environment() -> SessionStore:
    """The Postgres store when `DOPE_DB_URL` is set, otherwise one that keeps nothing."""
    dsn = os.environ.get("DOPE_DB_URL")
    if not dsn:
        logger.info("multiplayer persistence off (DOPE_DB_URL is not set)")
        return NullSessionStore()
    try:
        store = PostgresSessionStore(dsn)
    except Exception as exc:  # noqa: BLE001 - an unreachable database is not a reason not to start
        logger.error("multiplayer persistence off: cannot connect (%s)", type(exc).__name__)
        return NullSessionStore()
    if store.enabled:
        logger.info("multiplayer persistence on (Postgres)")
    return store
