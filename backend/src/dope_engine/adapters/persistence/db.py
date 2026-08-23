"""Postgres persistence adapter (analytics/logging only — designer's
request, 2026-08-23): records games, players and events to a
Supabase-hosted Postgres database for later playtest comparison across
code/rules versions. Purely additive telemetry, never authoritative —
`adapters/http/app.py`'s in-process `_games` dict stays the sole
authoritative live game state (CLAUDE.md section 3.1); nothing in the
domain or application layers imports this module, and no read path
anywhere depends on it.

Enabled only when `DOPE_DB_URL` is set (a standard libpq connection
string — Supabase's own "Connection string" from Project Settings ->
Database); every public function below is a silent no-op otherwise, so
local dev and the whole test suite never need a live database at all.
Every write is wrapped in its own try/except and only ever *logs* on
failure — "database failures must not interrupt gameplay" (designer's
own requirement): a Supabase outage, a bad connection string, or a
schema mismatch degrades to "this game just isn't being logged", never
a failed response to a real player's command.

Schema (already created by hand in Supabase, not managed here):
    games(id uuid pk, game_version varchar, rules_version varchar,
          status varchar, started_at timestamptz, ended_at timestamptz,
          winner_seat int4, total_turns int4)
    game_players(id int8 pk, game_id uuid fk, seat int4,
                 player_type varchar, character_id varchar,
                 bot_type varchar, final_money int4, winner bool)
    game_events(id int8 pk, game_id uuid fk, turn_number int4, seat int4,
                event_type varchar, payload jsonb, created_at timestamptz)
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Iterable
from dataclasses import fields
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.state import GameState

logger = logging.getLogger(__name__)

_DB_URL = os.environ.get("DOPE_DB_URL")


def _detect_game_version() -> str:
    """The running code's own short git commit hash — chosen over
    pyproject.toml's `version` field (still "0.1.0", never bumped in
    practice) so "compare playtests across versions" works automatically
    with no release-process discipline required. Falls back to
    "unknown" wherever `.git` isn't available (e.g. a stripped deploy)."""
    try:
        repo_root = Path(__file__).resolve().parents[5]
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


_GAME_VERSION = _detect_game_version()

_pool: Any = None
if _DB_URL:
    try:
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(_DB_URL, min_size=1, max_size=5, open=True)
    except Exception:
        logger.exception("Persistence disabled: could not open the Postgres connection pool.")
        _pool = None


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return value


def _event_payload(event: DomainEvent) -> dict[str, Any]:
    """Same generic dataclass -> JSON-safe dict shape as
    `adapters/http/app.py::_serialize_event` — duplicated rather than
    imported so this module never depends on the HTTP adapter (it could
    just as easily be wired up from a future non-HTTP entry point)."""
    data = {f.name: _json_safe(getattr(event, f.name)) for f in fields(event)}
    data["event_type"] = type(event).__name__
    return data


def record_game_started(state: GameState) -> None:
    """Called once, right after a game is created — writes the `games`
    row and all 4 `game_players` rows up front (seat/player_type/
    bot_type are already known at setup; final_money/winner stay NULL
    until `record_game_finished`)."""
    if _pool is None:
        return
    try:
        with _pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO games (id, game_version, rules_version, status, started_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(state.game_id),
                    _GAME_VERSION,
                    state.rules_version,
                    state.status.value,
                    datetime.now(UTC),
                ),
            )
            cur.executemany(
                """
                INSERT INTO game_players (game_id, seat, player_type, character_id, bot_type)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    (
                        str(state.game_id),
                        p.seat_index,
                        p.controller_type.value,
                        p.display_name if p.controller_type.value == "human" else None,
                        RandomLegalBot.__name__ if p.controller_type.value == "bot" else None,
                    )
                    for p in state.players
                ],
            )
    except Exception:
        logger.exception("Persistence: failed to record game start for %s.", state.game_id)


def record_events(state: GameState, events: Iterable[DomainEvent]) -> None:
    """Called after every accepted command — one `game_events` row per
    DomainEvent. `seat` is best-effort: resolved only when the event
    happens to carry a plain `player_id` field (most, not all, do — e.g.
    MarketCrashed has no single actor); left NULL otherwise. Nothing is
    ever lost either way, since the full event is already in `payload`."""
    if _pool is None:
        return
    events = list(events)
    if not events:
        return
    seat_by_player_id = {p.player_id: p.seat_index for p in state.players}

    def _seat_for(event: DomainEvent) -> int | None:
        player_id = getattr(event, "player_id", None)
        return seat_by_player_id.get(player_id) if player_id is not None else None

    try:
        with _pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO game_events
                    (game_id, turn_number, seat, event_type, payload, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        str(state.game_id),
                        state.turn_index,
                        _seat_for(event),
                        type(event).__name__,
                        Jsonb(_event_payload(event)),
                        datetime.now(UTC),
                    )
                    for event in events
                ],
            )
    except Exception:
        logger.exception(
            "Persistence: failed to record %d event(s) for %s.", len(events), state.game_id
        )


def record_game_finished(state: GameState) -> None:
    """Called once the game's own `status` first becomes FINISHED —
    updates the `games` row (ended_at/winner_seat/total_turns) and every
    `game_players` row's final_money/winner. `winner_seat` only gets set
    for a single, undisputed winner: `games` has room for one seat, but
    RULES_CANONICAL.md §D6 allows a shared victory on a further tie — the
    accurate picture for that case still lives in each `game_players.
    winner` (True for every co-winner), just not summarizable in one
    column."""
    if _pool is None or state.final_score is None:
        return
    winner_ids = set(state.final_score.winner_ids)
    winner_seat = None
    if len(winner_ids) == 1:
        (only_winner_id,) = winner_ids
        winner_seat = next(
            (p.seat_index for p in state.players if p.player_id == only_winner_id), None
        )
    try:
        with _pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE games
                SET status = %s, ended_at = %s, winner_seat = %s, total_turns = %s
                WHERE id = %s
                """,
                (
                    state.status.value,
                    datetime.now(UTC),
                    winner_seat,
                    state.turn_index,
                    str(state.game_id),
                ),
            )
            cur.executemany(
                """
                UPDATE game_players
                SET final_money = %s, winner = %s
                WHERE game_id = %s AND seat = %s
                """,
                [
                    (p.money, p.player_id in winner_ids, str(state.game_id), p.seat_index)
                    for p in state.players
                ],
            )
    except Exception:
        logger.exception("Persistence: failed to record game finish for %s.", state.game_id)
