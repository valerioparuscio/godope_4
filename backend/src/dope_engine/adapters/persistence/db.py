"""Postgres persistence adapter (analytics/logging only — designer's
request, 2026-08-23): records games, players and events to a
Supabase-hosted Postgres database for later playtest comparison across
code/rules versions. Purely additive telemetry, never authoritative —
`adapters/http/app.py`'s in-process `_games` dict stays the sole
authoritative live game state (CLAUDE.md section 3.1); nothing in the
domain or application layers imports this module, and no *gameplay* read
path depends on it — `fetch_leaderboard` (2026-09-26) is the one
exception, a purely cosmetic "classifica" display with no bearing on any
game's own rules or state.

Enabled only when `DOPE_DB_URL` is set (a standard libpq connection
string — Supabase's own "Connection string" from Project Settings ->
Database); every public function below is a silent no-op otherwise, so
local dev and the whole test suite never need a live database at all.
Every write is wrapped in its own try/except and only ever *logs* on
failure — "database failures must not interrupt gameplay" (designer's
own requirement): a Supabase outage, a bad connection string, or a
schema mismatch degrades to "this game just isn't being logged", never
a failed response to a real player's command. `fetch_leaderboard` keeps
the same policy for reads: any failure just means an empty leaderboard,
never a broken page.

Schema. The first three tables were created by hand in Supabase and are
not managed here:
    games(id uuid pk, game_version varchar, rules_version varchar,
          status varchar, started_at timestamptz, ended_at timestamptz,
          winner_seat int4, total_turns int4)
    game_players(id int8 pk, game_id uuid fk, seat int4,
                 player_type varchar, character_id varchar,
                 bot_type varchar, final_money int4, winner bool,
                 money_track_position_points int4, clean_reputation_points int4,
                 stained_reputation_points int4, contact_majority_points int4,
                 base_chip_points int4, skill_points int4, total_points int4)
    game_events(id int8 pk, game_id uuid fk, turn_number int4, seat int4,
                event_type varchar, payload jsonb, created_at timestamptz)

Two tables are this module's own (2026-10-25, Easy Price and multiplayer
games recorded) and are created if missing when the module starts, so no
table that already exists is ever altered — see docs/architecture/telemetry.md:
    game_info(game_id uuid pk, ruleset, mode 'solo'|'multi', bot_policy,
              human_count, room_code)
    game_job_completions(id, game_id, seat, player_type, ordinal, job_id,
              tier, next_job_id, turn_number, action_round_index, phase,
              completed_at, bonus_column_index, bonus_type, bonus_contact_id,
              bonus_skill_id, bonus_claimed_at)
          one row per Job a player completes — bots and humans alike — in the
          order they complete them (`ordinal`), filled in again when the reward
          column is claimed: the progression of the Jobs through a game.
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import fields
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.domain.events import DomainEvent, JobBonusClaimed, JobCompleted
from dope_engine.domain.ids import PlayerId
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


GAME_INFO_DDL = """
CREATE TABLE IF NOT EXISTS game_info (
    game_id      uuid PRIMARY KEY,
    ruleset      text NOT NULL,
    mode         text NOT NULL,
    bot_policy   text,
    human_count  integer,
    room_code    text
)
"""

GAME_JOB_COMPLETIONS_DDL = """
CREATE TABLE IF NOT EXISTS game_job_completions (
    id                  bigserial PRIMARY KEY,
    game_id             uuid NOT NULL,
    seat                integer NOT NULL,
    player_type         text,
    ordinal             integer NOT NULL,
    job_id              text NOT NULL,
    tier                integer,
    next_job_id         text,
    turn_number         integer,
    action_round_index  integer,
    phase               text,
    completed_at        timestamptz NOT NULL DEFAULT now(),
    bonus_column_index  integer,
    bonus_type          text,
    bonus_contact_id    text,
    bonus_skill_id      text,
    bonus_claimed_at    timestamptz
)
"""

GAME_JOB_COMPLETIONS_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS game_job_completions_game_seat_idx
    ON game_job_completions (game_id, seat)
"""


class TelemetryDb:
    """The recorder over one connection pool. Every method swallows (and
    logs) its own failures, see the module docstring."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool
        # False when this module's two own tables could not be created: games are then
        # recorded exactly as before, without the mode/Job rows.
        self._own_tables = self._ensure_own_tables()

    def _ensure_own_tables(self) -> bool:
        try:
            with self._pool.connection() as conn:
                conn.execute(GAME_INFO_DDL)
                conn.execute(GAME_JOB_COMPLETIONS_DDL)
                conn.execute(GAME_JOB_COMPLETIONS_INDEX_DDL)
            return True
        except Exception as exc:  # noqa: BLE001 - recording degrades, the game does not
            logger.error(
                "Persistence: cannot prepare game_info/game_job_completions (%s): "
                "games are recorded without them.",
                type(exc).__name__,
            )
            return False

    def record_game_started(
        self,
        state: GameState,
        *,
        mode: str = "solo",
        bot_policy: str | None = None,
        bot_type: str | None = None,
        room_code: str | None = None,
    ) -> None:
        """Called once, right after a game is created — writes the `games`
        row and all 4 `game_players` rows up front (seat/player_type/
        bot_type are already known at setup; final_money/winner stay NULL
        until `record_game_finished`), and the game's `game_info` row (its
        ruleset, solo or multi, the bots' policy). `bot_type` is the bots'
        class name when the caller knows it (default: RandomLegalBot, as
        before)."""
        ruleset = str(state.configuration.get("ruleset_id", "standard"))
        human_count = sum(1 for p in state.players if p.controller_type.value == "human")
        try:
            with self._pool.connection() as conn, conn.cursor() as cur:
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
                            (bot_type or RandomLegalBot.__name__)
                            if p.controller_type.value == "bot"
                            else None,
                        )
                        for p in state.players
                    ],
                )
                if self._own_tables:
                    cur.execute(
                        """
                        INSERT INTO game_info
                            (game_id, ruleset, mode, bot_policy, human_count, room_code)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (game_id) DO NOTHING
                        """,
                        (str(state.game_id), ruleset, mode, bot_policy, human_count, room_code),
                    )
        except Exception:
            logger.exception("Persistence: failed to record game start for %s.", state.game_id)

    def record_events(self, state: GameState, events: Iterable[DomainEvent]) -> None:
        """Called after every accepted command — one `game_events` row per
        DomainEvent. `seat` is best-effort: resolved only when the event
        happens to carry a plain `player_id` field (most, not all, do — e.g.
        MarketCrashed has no single actor); left NULL otherwise. Nothing is
        ever lost either way, since the full event is already in `payload`.

        The Job events also feed `game_job_completions`: a `JobCompleted` adds
        the player's next row (their n-th completed Job), the `JobBonusClaimed`
        that follows fills in which column and bonus they took."""
        events = list(events)
        if not events:
            return
        seat_by_player_id = {p.player_id: p.seat_index for p in state.players}
        type_by_player_id = {p.player_id: p.controller_type.value for p in state.players}

        def _seat_for(event: DomainEvent) -> int | None:
            player_id = getattr(event, "player_id", None)
            return seat_by_player_id.get(player_id) if player_id is not None else None

        try:
            with self._pool.connection() as conn, conn.cursor() as cur:
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
                if self._own_tables:
                    for event in events:
                        if isinstance(event, JobCompleted):
                            self._insert_job_completion(
                                cur, state, event, seat_by_player_id, type_by_player_id
                            )
                        elif isinstance(event, JobBonusClaimed):
                            self._fill_job_bonus(cur, state, event, seat_by_player_id)
        except Exception:
            logger.exception(
                "Persistence: failed to record %d event(s) for %s.", len(events), state.game_id
            )

    @staticmethod
    def _insert_job_completion(
        cur: Any,
        state: GameState,
        event: JobCompleted,
        seat_by_player_id: Mapping[PlayerId, int],
        type_by_player_id: Mapping[PlayerId, str],
    ) -> None:
        seat = seat_by_player_id.get(event.player_id)
        if seat is None:
            return
        cur.execute(
            """
            INSERT INTO game_job_completions
                (game_id, seat, player_type, ordinal, job_id, tier, next_job_id,
                 turn_number, action_round_index, phase)
            VALUES (%s, %s, %s,
                    (SELECT COUNT(*) + 1 FROM game_job_completions
                      WHERE game_id = %s AND seat = %s),
                    %s, %s, %s, %s, %s, %s)
            """,
            (
                str(state.game_id),
                seat,
                type_by_player_id.get(event.player_id),
                str(state.game_id),
                seat,
                str(event.job_id),
                event.tier,
                str(event.next_job_id) if event.next_job_id is not None else None,
                state.turn_index,
                state.action_round_index,
                state.phase.value,
            ),
        )

    @staticmethod
    def _fill_job_bonus(
        cur: Any,
        state: GameState,
        event: JobBonusClaimed,
        seat_by_player_id: Mapping[PlayerId, int],
    ) -> None:
        seat = seat_by_player_id.get(event.player_id)
        if seat is None:
            return
        cur.execute(
            """
            UPDATE game_job_completions
               SET bonus_column_index = %s, bonus_type = %s, bonus_contact_id = %s,
                   bonus_skill_id = %s, bonus_claimed_at = %s
             WHERE id = (SELECT id FROM game_job_completions
                          WHERE game_id = %s AND seat = %s AND job_id = %s
                            AND bonus_claimed_at IS NULL
                          ORDER BY id LIMIT 1)
            """,
            (
                event.column_index,
                event.bonus_type,
                str(event.contact_id),
                str(event.skill_id) if event.skill_id is not None else None,
                datetime.now(UTC),
                str(state.game_id),
                seat,
                str(event.job_id),
            ),
        )

    def record_game_finished(self, state: GameState) -> None:
        """Called once the game's own `status` first becomes FINISHED —
        updates the `games` row (ended_at/winner_seat/total_turns) and every
        `game_players` row's final_money/winner plus its full
        `FinalScoreBreakdown` (game designer, 2026-08-27: the final ranking
        itself wasn't being persisted at all — `total_points` is the actual
        "classifica", and the per-category columns let playtest analysis
        break it down, e.g. how often Contact majorities or Chip points
        decide a game). `winner_seat` only gets set for a single, undisputed
        winner: `games` has room for one seat, but RULES_CANONICAL.md §D6
        allows a shared victory on a further tie — the accurate picture for
        that case still lives in each `game_players.winner` (True for every
        co-winner) and `total_points` (identical for every co-winner), just
        not summarizable in one `games` column."""
        if state.final_score is None:
            return
        winner_ids = set(state.final_score.winner_ids)
        winner_seat = None
        if len(winner_ids) == 1:
            (only_winner_id,) = winner_ids
            winner_seat = next(
                (p.seat_index for p in state.players if p.player_id == only_winner_id), None
            )
        breakdown_by_player = state.final_score.breakdown_by_player
        try:
            with self._pool.connection() as conn, conn.cursor() as cur:
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
                    SET final_money = %s, winner = %s,
                        money_track_position_points = %s, clean_reputation_points = %s,
                        stained_reputation_points = %s, contact_majority_points = %s,
                        base_chip_points = %s, skill_points = %s, total_points = %s
                    WHERE game_id = %s AND seat = %s
                    """,
                    [
                        (
                            p.money,
                            p.player_id in winner_ids,
                            breakdown_by_player[p.player_id].money_track_position_points,
                            breakdown_by_player[p.player_id].clean_reputation_points,
                            breakdown_by_player[p.player_id].stained_reputation_points,
                            breakdown_by_player[p.player_id].contact_majority_points,
                            breakdown_by_player[p.player_id].base_chip_points,
                            breakdown_by_player[p.player_id].skill_points,
                            breakdown_by_player[p.player_id].total_points,
                            str(state.game_id),
                            p.seat_index,
                        )
                        for p in state.players
                    ],
                )
        except Exception:
            logger.exception("Persistence: failed to record game finish for %s.", state.game_id)

    def fetch_leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        """Top `limit` `game_players` rows by `total_points`, human seats only
        (`character_id` is only ever set for a human — see
        `record_game_started`), restricted to games started on or after
        `_LEADERBOARD_CUTOFF` — the arcade-style "classifica" button (game
        designer, 2026-09-26). This module's first *read* path: same
        "database failures must not interrupt gameplay" policy as every write
        above still applies, so this is silent-empty (never raises) whether
        that's because no DB is configured or because the query itself
        failed. A given nickname can appear more than once here on purpose —
        one row per game played, not one best-of per player, same as a real
        arcade high-score table.

        Solo games only (2026-10-25: multiplayer games are recorded now, but are
        not ranked against them without a product decision, GPT_MULTIPLAYER.md
        section 48): a game with no `game_info` row (every game recorded before
        that day) counts as solo."""
        solo_only = (
            "LEFT JOIN game_info gi ON gi.game_id = g.id" if self._own_tables else "",
            "AND COALESCE(gi.mode, 'solo') = 'solo'" if self._own_tables else "",
        )
        try:
            with self._pool.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT gp.character_id, gp.total_points, gp.winner
                    FROM game_players gp
                    JOIN games g ON g.id = gp.game_id
                    {solo_only[0]}
                    WHERE gp.character_id IS NOT NULL
                      AND gp.total_points IS NOT NULL
                      AND g.started_at >= %s
                      {solo_only[1]}
                    ORDER BY gp.total_points DESC
                    LIMIT %s
                    """,
                    (_LEADERBOARD_CUTOFF, limit),
                )
                rows = cur.fetchall()
            return [
                {"nickname": nickname, "total_points": total_points, "winner": bool(winner)}
                for nickname, total_points, winner in rows
            ]
        except Exception:
            logger.exception("Persistence: failed to fetch the leaderboard.")
            return []


# Include games started from 28 September 2026 at midnight in Italy
# (Europe/Rome, UTC+02:00), stored here as the equivalent UTC instant.
_LEADERBOARD_CUTOFF = datetime(2026, 9, 27, 22, 0, 0, tzinfo=UTC)


_pool: Any = None
if _DB_URL:
    try:
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(_DB_URL, min_size=1, max_size=5, open=True)
    except Exception:
        logger.exception("Persistence disabled: could not open the Postgres connection pool.")
        _pool = None

_db: TelemetryDb | None = TelemetryDb(_pool) if _pool is not None else None


def default_db() -> TelemetryDb | None:
    """The recorder over this process's own pool, or None without `DOPE_DB_URL`."""
    return _db


def record_game_started(state: GameState, **details: Any) -> None:
    if _db is not None:
        _db.record_game_started(state, **details)


def record_events(state: GameState, events: Iterable[DomainEvent]) -> None:
    if _db is not None:
        _db.record_events(state, events)


def record_game_finished(state: GameState) -> None:
    if _db is not None:
        _db.record_game_finished(state)


def fetch_leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    return _db.fetch_leaderboard(limit) if _db is not None else []
