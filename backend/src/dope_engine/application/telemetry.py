"""Recording a game for later analysis (analytics only, never authoritative): what the games, their
players, every event and the progression of the Jobs look like once they are over.

The application layer only knows this port; the database behind it is an adapter
(`adapters/persistence/telemetry.py`, `adapters/persistence/db.py`). `NullTelemetry` records
nothing (local development, most tests). `BackgroundTelemetry` hands every call to one thread, in
order, so a slow or unreachable database never makes a player's command wait; a call that fails is
logged (its kind only) and dropped, and a full queue drops what does not fit rather than grow.
"""

from __future__ import annotations

import contextlib
import logging
import queue
import threading
from collections.abc import Sequence
from typing import Any, Protocol

from dope_engine.domain.events import DomainEvent
from dope_engine.domain.state import GameState

logger = logging.getLogger("dope.telemetry")


class GameTelemetry(Protocol):
    def game_started(
        self, state: GameState, *, mode: str, bot_policy: str | None, room_code: str | None
    ) -> None: ...

    def events(self, state: GameState, events: Sequence[DomainEvent]) -> None: ...

    def game_finished(self, state: GameState) -> None: ...

    def flush(self, timeout: float = 10.0) -> bool: ...

    def close(self) -> None: ...


class NullTelemetry:
    """Records nothing."""

    def game_started(
        self, state: GameState, *, mode: str, bot_policy: str | None, room_code: str | None
    ) -> None:
        return None

    def events(self, state: GameState, events: Sequence[DomainEvent]) -> None:
        return None

    def game_finished(self, state: GameState) -> None:
        return None

    def flush(self, timeout: float = 10.0) -> bool:
        return True

    def close(self) -> None:
        return None


MAX_PENDING_CALLS = 20_000


class BackgroundTelemetry:
    """Runs the calls on `inner` from one background thread, in the order they were made."""

    def __init__(self, inner: GameTelemetry, *, max_pending: int = MAX_PENDING_CALLS) -> None:
        self._inner = inner
        self._queue: queue.Queue[tuple[str, tuple[Any, ...], dict[str, Any]] | None] = queue.Queue(
            maxsize=max_pending
        )
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._closed = False
        self._dropped = 0

    # -- the port

    def game_started(
        self, state: GameState, *, mode: str, bot_policy: str | None, room_code: str | None
    ) -> None:
        self._put(
            "game_started",
            (state,),
            {"mode": mode, "bot_policy": bot_policy, "room_code": room_code},
        )

    def events(self, state: GameState, events: Sequence[DomainEvent]) -> None:
        self._put("events", (state, tuple(events)), {})

    def game_finished(self, state: GameState) -> None:
        self._put("game_finished", (state,), {})

    def flush(self, timeout: float = 10.0) -> bool:
        """True once every call made so far has been run (shutdown, tests)."""
        done = threading.Event()

        def wait() -> None:
            self._queue.join()
            done.set()

        threading.Thread(target=wait, daemon=True).start()
        return done.wait(timeout)

    def close(self) -> None:
        """Runs what is still waiting, then stops the thread."""
        self.flush()
        with self._lock:
            self._closed = True
            thread = self._thread
        if thread is not None:
            with contextlib.suppress(queue.Full):
                self._queue.put_nowait(None)
            thread.join(5.0)
        self._inner.close()

    # -- internals

    def _put(self, name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        with self._lock:
            if self._closed:
                return
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run, name="telemetry-writer", daemon=True
                )
                self._thread.start()
        try:
            self._queue.put_nowait((name, args, kwargs))
        except queue.Full:
            self._dropped += 1
            if self._dropped == 1 or self._dropped % 1000 == 0:
                logger.error("telemetry queue is full: %d call(s) dropped so far", self._dropped)

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                name, args, kwargs = item
                try:
                    getattr(self._inner, name)(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - telemetry never reaches a player
                    logger.warning("telemetry %s failed (%s)", name, type(exc).__name__)
            finally:
                self._queue.task_done()
