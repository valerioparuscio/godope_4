"""The telemetry port (`application/telemetry.py`) over the Postgres recorder (`db.py`)."""

from __future__ import annotations

from collections.abc import Sequence

from dope_engine.adapters.persistence import db
from dope_engine.application.telemetry import BackgroundTelemetry, GameTelemetry, NullTelemetry
from dope_engine.bots.policies import HeuristicBot
from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.state import GameState

# The class of the bots a policy name stands for (the registry holds factories, not classes).
BOT_TYPE_BY_POLICY = {
    "random_legal": RandomLegalBot.__name__,
    "heuristic": HeuristicBot.__name__,
}


class DbTelemetry:
    """Records into the database `recorder` writes to."""

    def __init__(self, recorder: db.TelemetryDb) -> None:
        self._recorder = recorder

    def game_started(
        self, state: GameState, *, mode: str, bot_policy: str | None, room_code: str | None
    ) -> None:
        self._recorder.record_game_started(
            state,
            mode=mode,
            bot_policy=bot_policy,
            bot_type=BOT_TYPE_BY_POLICY.get(bot_policy or "", bot_policy),
            room_code=room_code,
        )

    def events(self, state: GameState, events: Sequence[DomainEvent]) -> None:
        self._recorder.record_events(state, events)

    def game_finished(self, state: GameState) -> None:
        self._recorder.record_game_finished(state)

    def flush(self, timeout: float = 10.0) -> bool:
        return True

    def close(self) -> None:
        return None


def telemetry_from_environment() -> GameTelemetry:
    """Recording to the database when `DOPE_DB_URL` is set (from a background thread: a request
    never waits for it), otherwise nothing."""
    recorder = db.default_db()
    if recorder is None:
        return NullTelemetry()
    return BackgroundTelemetry(DbTelemetry(recorder))
