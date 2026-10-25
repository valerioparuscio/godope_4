"""The multiplayer use cases: rooms, seats, and playing a game with several humans
(docs/architecture/GPT_MULTIPLAYER.md).

This is the layer between a transport (the HTTP routes) and the game engine. It never decides a
rule: it decides *who is allowed to ask* (seat tokens), *when* (one authoritative mutation at a
time per game, stale revisions refused), *who plays the bots* (the server, right after every
accepted human command) and *what each player gets to see* (a per-player view and a per-player
filtered event log).

A game's state is replaced, never mutated, once published (`CommandBus` always works on a copy), so
readers (views, event polling, plan previews) run without waiting for a bot cascade: they take the
session's `publish_lock` for an instant and read a consistent `(state, log)` pair. Writers hold
`session.lock` for the whole sequence: authorize, check the revision, apply, advance the bots,
store the events.
"""

from __future__ import annotations

import copy
import dataclasses
import logging
import re
import secrets
import threading
import time
import uuid
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass

from dope_engine.application.command_bus import CommandFailure
from dope_engine.application.game_service import GameService
from dope_engine.application.human_planning import (
    DecisionPlan,
    PlanningError,
    build_decision_plan,
)
from dope_engine.application.multiplayer.event_filter import filter_batch_for_viewer
from dope_engine.application.multiplayer.models import (
    BATCH_STATE_WINDOW,
    CLOSED_GRACE_SECONDS,
    FINISHED_GRACE_SECONDS,
    LOBBY_IDLE_SECONDS,
    MIN_HUMAN_SEATS,
    PURGE_INTERVAL_SECONDS,
    RUNNING_IDLE_SECONDS,
    SEAT_AWAY_SECONDS,
    SEAT_COUNT,
    EventBatch,
    GameSession,
    MultiplayerError,
    RoomStatus,
    Seat,
)
from dope_engine.application.multiplayer.registry import (
    GameRegistry,
    hash_token,
    normalize_room_code,
)
from dope_engine.application.multiplayer.snapshots import record_of, session_from_payload
from dope_engine.application.multiplayer.store import (
    NullSessionStore,
    SessionRecord,
    SessionStore,
    SnapshotWriter,
)
from dope_engine.application.telemetry import GameTelemetry, NullTelemetry
from dope_engine.application.views import PlayerGameView
from dope_engine.bots.base import BotPolicy
from dope_engine.domain.enums import ControllerType, GameStatus
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import GameId, PlayerId
from dope_engine.domain.state import GameState
from dope_engine.rules.setup import SeatConfig

logger = logging.getLogger("dope.multiplayer")

MAX_NICKNAME_LENGTH = 24
# A safety valve for the bot cascade that follows a human command; a whole game is a few thousand
# segments at most.
MAX_BOT_SEGMENTS = 20_000
# A lookup that found nothing in the store is not repeated for this long: a client that polls a room
# that is gone must not become a database query per second.
MISS_MEMORY_SECONDS = 20.0
MAX_REMEMBERED_MISSES = 1_000


def secure_seed() -> int:
    return secrets.randbelow(2**31 - 1) + 1


def new_game_id() -> GameId:
    return GameId(str(uuid.uuid4()))


@dataclass(frozen=True)
class SeatInfo:
    """What anyone in the room may know about a seat (never the token)."""

    seat_index: int
    player_id: PlayerId
    controller_type: ControllerType
    nickname: str | None
    # A human seat someone has taken (a bot seat is always "occupied").
    occupied: bool
    is_host: bool
    left: bool
    away: bool


@dataclass(frozen=True)
class RoomInfo:
    room_code: str
    status: RoomStatus
    ruleset: str
    human_seat_count: int
    bot_policy: str
    game_id: GameId | None
    seats: tuple[SeatInfo, ...]


@dataclass(frozen=True)
class Credentials:
    """Handed to a human when they create or join a room; the only time the token is visible."""

    room_code: str
    game_id: GameId | None
    seat_index: int
    player_id: PlayerId
    seat_token: str


@dataclass(frozen=True)
class PlayerSnapshot:
    room: RoomInfo
    me: SeatInfo
    revision: int
    status: RoomStatus
    awaiting_player_id: PlayerId | None
    view: PlayerGameView


@dataclass(frozen=True)
class EventsResult:
    game_id: GameId
    from_revision: int
    current_revision: int
    status: RoomStatus
    awaiting_player_id: PlayerId | None
    # True when `since` is ahead of the game: the client's picture is not this game's.
    requires_refresh: bool
    batches: tuple[EventBatch, ...]
    view: PlayerGameView | None
    # The viewer's own view right after each batch (same order and length as `batches`); only
    # when asked for, and None for a batch too old to still have its state.
    batch_views: tuple[PlayerGameView | None, ...] = ()


@dataclass(frozen=True)
class AnswerResult:
    revision: int
    status: RoomStatus
    awaiting_player_id: PlayerId | None
    batches: tuple[EventBatch, ...]
    view: PlayerGameView
    # As `EventsResult.batch_views`: the board after each step, so the client can replay the bots
    # one action at a time.
    batch_views: tuple[PlayerGameView | None, ...] = ()


def clean_nickname(nickname: str) -> str:
    cleaned = re.sub(r"\s+", " ", "".join(ch for ch in nickname if ch.isprintable())).strip()
    if not cleaned:
        raise MultiplayerError("invalid_request", "A nickname is required.")
    if len(cleaned) > MAX_NICKNAME_LENGTH:
        raise MultiplayerError(
            "invalid_request", f"A nickname is at most {MAX_NICKNAME_LENGTH} characters."
        )
    return cleaned


class MultiplayerService:
    def __init__(
        self,
        *,
        registry: GameRegistry,
        service_for_ruleset: Callable[[str], GameService],
        bot_policy_factory: Callable[[str, str], BotPolicy],
        rulesets: Collection[str],
        bot_policies: Collection[str],
        seed_factory: Callable[[], int] = secure_seed,
        game_id_factory: Callable[[], GameId] = new_game_id,
        clock: Callable[[], float] = time.time,
        store: SessionStore | None = None,
        synchronous_saves: bool = False,
        away_after_seconds: float = SEAT_AWAY_SECONDS,
        telemetry: GameTelemetry | None = None,
    ) -> None:
        self._registry = registry
        self._service_for_ruleset = service_for_ruleset
        self._bot_policy_factory = bot_policy_factory
        self._rulesets = frozenset(rulesets)
        self._bot_policies = frozenset(bot_policies)
        # Public so tests can pin a game's seed and id; HTTP clients never get to choose either.
        self.seed_factory = seed_factory
        self.game_id_factory = game_id_factory
        self._clock = clock
        # Rooms are kept in `store` (section 43) and read back, one at a time, the first time
        # somebody asks for them after a restart (not all at startup: during a deploy the old
        # process is still playing for a while, and a room loaded early would be out of date).
        self._store: SessionStore = store if store is not None else NullSessionStore()
        self._writer = SnapshotWriter(self._store, synchronous=synchronous_saves)
        self._away_after = away_after_seconds
        # Every game is recorded for analysis (games, players, events, the Jobs' progression):
        # from a background thread, so a slow database never holds a command up.
        self._telemetry: GameTelemetry = telemetry if telemetry is not None else NullTelemetry()
        self._rehydrate_lock = threading.Lock()
        self._misses: dict[str, float] = {}
        self._last_purge = clock()

    @property
    def registry(self) -> GameRegistry:
        return self._registry

    @property
    def persistence_enabled(self) -> bool:
        return self._store.enabled

    def flush_persistence(self, timeout: float = 10.0) -> bool:
        """Waits until every change so far has reached the store (shutdown, tests)."""
        return self._writer.flush(timeout)

    def flush_telemetry(self, timeout: float = 10.0) -> bool:
        return self._telemetry.flush(timeout)

    def close(self) -> None:
        """Writes what is still waiting for the store and the telemetry, and stops saving: call on
        shutdown."""
        self._writer.close()
        self._telemetry.close()

    # ------------------------------------------------------------------ rooms

    def create_room(
        self, *, ruleset: str, human_seats: int, bot_policy: str, nickname: str
    ) -> Credentials:
        nickname = clean_nickname(nickname)
        if ruleset not in self._rulesets:
            raise MultiplayerError("invalid_request", f"Unknown ruleset '{ruleset}'.")
        if bot_policy not in self._bot_policies:
            raise MultiplayerError("invalid_request", f"Unknown bot policy '{bot_policy}'.")
        if not MIN_HUMAN_SEATS <= human_seats <= SEAT_COUNT:
            raise MultiplayerError(
                "invalid_request",
                f"A room has between {MIN_HUMAN_SEATS} and {SEAT_COUNT} human players.",
            )
        seats = [
            Seat(
                player_id=PlayerId(f"player_{index}"),
                seat_index=index,
                controller_type=(
                    ControllerType.HUMAN if index < human_seats else ControllerType.BOT
                ),
                nickname=None if index < human_seats else f"Bot {index + 1}",
            )
            for index in range(SEAT_COUNT)
        ]
        self._maybe_purge()
        now = self._clock()
        session = GameSession(
            room_code=self._registry.new_room_code(self._code_kept_in_store),
            ruleset=ruleset,
            bot_policy_name=bot_policy,
            human_seat_count=human_seats,
            seats=seats,
            created_at=now,
            last_activity_at=now,
        )
        self._registry.add(session)
        host = seats[session.host_seat_index]
        host.joined = True
        host.nickname = nickname
        host.last_seen_at = now
        token = self._registry.issue_token(session, host)
        logger.info(
            "room created room=%s ruleset=%s humans=%d", session.room_code, ruleset, human_seats
        )
        self._persist(session)
        return self._credentials(session, host, token)

    def join_room(self, room_code: str, nickname: str) -> Credentials:
        nickname = clean_nickname(nickname)
        session = self._find_room(room_code)
        with session.lock:
            self._require_lobby(session)
            taken = {
                seat.nickname.casefold() for seat in session.seats if seat.joined and seat.nickname
            }
            if nickname.casefold() in taken:
                raise MultiplayerError("nickname_taken", "Somebody in this room has that nickname.")
            seat = next(
                (s for s in session.seats if s.is_human and not s.joined),
                None,
            )
            if seat is None:
                raise MultiplayerError("room_full", "Every human seat in this room is taken.")
            seat.joined = True
            seat.nickname = nickname
            token = self._registry.issue_token(session, seat)
            session.last_activity_at = seat.last_seen_at = self._clock()
            logger.info("seat joined room=%s seat=%d", session.room_code, seat.seat_index)
            self._persist(session)
            return self._credentials(session, seat, token)

    def room_info(self, room_code: str) -> RoomInfo:
        """The safe, public description of a room: who sits where, never a token."""
        session = self._find_room(room_code)
        with session.publish_lock:
            return self._room_info(session)

    def room_for_caller(
        self, room_code: str, seat_token: str | None
    ) -> tuple[RoomInfo, SeatInfo | None]:
        """`room_info` plus the caller's own seat, if the token is a valid one for *this* room —
        what a client that reloads the page asks to find out whether it still has its seat."""
        session = self._find_room(room_code)
        with session.publish_lock:
            info = self._room_info(session)
        resolved = self._resolve_token(seat_token)
        if resolved is None or resolved[0] is not session:
            return info, None
        seat = resolved[1]
        seat.last_seen_at = self._clock()
        return info, self._seat_info(session, seat)

    def start_room(self, room_code: str, seat_token: str | None) -> RoomInfo:
        session, seat = self._authenticate_room(room_code, seat_token)
        with session.lock:
            self._require_lobby(session)
            if seat.seat_index != session.host_seat_index:
                raise MultiplayerError("forbidden", "Only the host can start the game.")
            missing = [s.seat_index for s in session.seats if s.is_human and not s.joined]
            if missing:
                raise MultiplayerError(
                    "room_not_ready",
                    "Not every human seat is taken yet.",
                    {"missing_seat_indexes": missing},
                )
            service = self._service_for_ruleset(session.ruleset)
            game_id = self.game_id_factory()
            seed = session.seed if session.seed is not None else self.seed_factory()
            result = service.create_game_from_seats(
                game_id=game_id,
                seed=seed,
                seats=[SeatConfig(s.controller_type, s.nickname) for s in session.seats],
                bot_policy=self._bot_policy_factory(session.bot_policy_name, session.ruleset),
            )
            session.game_id = game_id
            self._registry.bind_game(session, game_id)
            now = self._clock()
            session.started_at = now
            session.last_activity_at = now
            self._commit(
                session,
                result.state,
                revision_from=0,
                actor=None,
                segment_type="game_start",
                events=result.events,
                status=RoomStatus.RUNNING,
            )
            self._advance_bots(session)
            logger.info("game started room=%s game=%s", session.room_code, game_id)
            self._persist(session)
            return self.room_info(room_code)

    def leave(self, room_code: str, seat_token: str | None) -> RoomInfo | None:
        """Lobby: the seat is freed (the host leaving closes the room). Running game: the seat
        turns into a bot and the game goes on. Finished: the token just stops working."""
        session, seat = self._authenticate_room(room_code, seat_token)
        with session.lock:
            if session.status is RoomStatus.LOBBY:
                if seat.seat_index == session.host_seat_index:
                    with session.publish_lock:
                        session.status = RoomStatus.CLOSED
                    for each in session.seats:
                        self._registry.revoke_token(each)
                    self._persist(session)
                    return None
                self._registry.revoke_token(seat)
                seat.joined = False
                seat.nickname = None
                self._persist(session)
                return self.room_info(room_code)
            if session.status is RoomStatus.RUNNING:
                self._seat_becomes_bot(session, seat)
            self._registry.revoke_token(seat)
            self._persist(session)
            return self.room_info(room_code)

    # --------------------------------------------------------------- the game

    def authenticate(self, game_id: str, seat_token: str | None) -> tuple[GameSession, Seat]:
        """The only way a game request learns who is calling: from the token, never from the
        request body (section 3.2). A token of another room is as good as none."""
        resolved = self._resolve_token(seat_token)
        if resolved is None:
            raise MultiplayerError("invalid_token", "Missing or unknown seat token.")
        session, seat = resolved
        if session.game_id is None or session.game_id != game_id:
            raise MultiplayerError("invalid_token", "That seat token is not for this game.")
        # Before anything else: being heard from is what keeps a seat from being taken over.
        seat.last_seen_at = self._clock()
        if seat.away:
            self._reclaim_seat(session, seat)
        return session, seat

    def snapshot(self, game_id: str, seat_token: str | None) -> PlayerSnapshot:
        session, seat = self.authenticate(game_id, seat_token)
        self._take_over_if_due(session)
        state, _batches, status = self._read(session, since=None)
        assert state is not None
        service = self._service_for_ruleset(session.ruleset)
        with session.publish_lock:
            room = self._room_info(session)
        return PlayerSnapshot(
            room=room,
            me=self._seat_info(session, seat),
            revision=state.revision,
            status=status,
            awaiting_player_id=self._awaiting(state),
            view=self._view(service, session, state, seat.player_id),
        )

    def events_since(
        self,
        game_id: str,
        seat_token: str | None,
        since: int,
        *,
        include_view: bool = False,
        include_batch_views: bool = False,
    ) -> EventsResult:
        """The event batches after revision `since`, as this player may see them. Read-only:
        polling never moves the game (section 19), except for one thing: a poll is also when the
        table notices that the player it is waiting for is gone and gives their seat to a bot."""
        session, seat = self.authenticate(game_id, seat_token)
        self._take_over_if_due(session)
        state, batches, status = self._read(session, since=since)
        assert state is not None
        service = self._service_for_ruleset(session.ruleset)
        return EventsResult(
            game_id=GameId(game_id),
            from_revision=since,
            current_revision=state.revision,
            status=status,
            awaiting_player_id=self._awaiting(state),
            requires_refresh=since > state.revision,
            batches=tuple(filter_batch_for_viewer(b, seat.player_id) for b in batches),
            view=(self._view(service, session, state, seat.player_id) if include_view else None),
            batch_views=(
                self._views_after(service, session, batches, seat.player_id)
                if include_batch_views
                else ()
            ),
        )

    def plan(
        self,
        game_id: str,
        seat_token: str | None,
        decision_id: str,
        selections: Sequence[Sequence[str]],
    ) -> DecisionPlan:
        """Preview of preparatory choices on copies of the state (section 24): nothing consumed,
        nothing stored, no revision moved, no bot advanced."""
        session, seat = self.authenticate(game_id, seat_token)
        state, _batches, _status = self._read(session, since=None)
        assert state is not None
        self._require_pending_decision(state, seat, decision_id)
        service = self._service_for_ruleset(session.ruleset)
        try:
            return build_decision_plan(
                service,
                state,
                seat.player_id,
                selections,
                view_for=lambda current: self._view(service, session, current, seat.player_id),
            )
        except PlanningError as exc:
            raise MultiplayerError("invalid_decision", str(exc)) from exc

    def answer(
        self,
        game_id: str,
        seat_token: str | None,
        *,
        decision_id: str,
        selected_option_ids: Sequence[str],
        preparatory_selections: Sequence[Sequence[str]] = (),
        expected_revision: int,
    ) -> AnswerResult:
        session, seat = self.authenticate(game_id, seat_token)
        with session.lock:
            state = session.state
            if session.status is RoomStatus.FINISHED or state is None:
                raise MultiplayerError("game_finished", "The game is over.")
            self._require_pending_decision(state, seat, decision_id, expected_revision)
            service = self._service_for_ruleset(session.ruleset)
            selections = [list(step) for step in preparatory_selections]
            selections.append(list(selected_option_ids))
            try:
                outcome = service.answer_sequence(state, seat.player_id, selections)
            except (KeyError, ValueError) as exc:
                raise MultiplayerError("invalid_decision", str(exc)) from exc
            if isinstance(outcome, CommandFailure):
                raise MultiplayerError(
                    "invalid_decision",
                    outcome.error.message,
                    {"domain_error": outcome.error.code},
                )
            logger.info(
                "answer game=%s revision=%d seat=%d decision=%s events=%d",
                game_id,
                state.revision,
                seat.seat_index,
                state.pending_decision.decision_type if state.pending_decision else "-",
                len(outcome.events),
            )
            produced = [
                self._commit(
                    session,
                    outcome.state,
                    revision_from=state.revision,
                    actor=seat.player_id,
                    segment_type="human_command",
                    events=outcome.events,
                )
            ]
            produced.extend(self._advance_bots(session))
            produced.extend(self._take_over_if_away(session))
            session.last_activity_at = self._clock()
            self._persist(session)
            final_state = session.state
            assert final_state is not None
            with session.publish_lock:
                status = session.status
            return AnswerResult(
                revision=final_state.revision,
                status=status,
                awaiting_player_id=self._awaiting(final_state),
                batches=tuple(filter_batch_for_viewer(b, seat.player_id) for b in produced),
                view=self._view(service, session, final_state, seat.player_id),
                # `produced` still holds every state, even if the window has already let the
                # oldest ones go from the log.
                batch_views=self._views_after(service, session, produced, seat.player_id),
            )

    # ---------------------------------------------------------------- internals

    def _authenticate_room(
        self, room_code: str, seat_token: str | None
    ) -> tuple[GameSession, Seat]:
        resolved = self._resolve_token(seat_token)
        if resolved is None:
            raise MultiplayerError("invalid_token", "Missing or unknown seat token.")
        session, seat = resolved
        if session.room_code != normalize_room_code(room_code):
            raise MultiplayerError("invalid_token", "That seat token is not for this room.")
        seat.last_seen_at = self._clock()
        return session, seat

    # ------------------------------------------------------- persistence (sections 43-46)

    def _persist(self, session: GameSession) -> None:
        """Hands the room as it is now to the store; a finished or closed room is deleted from it
        instead (nobody needs to come back to it after a restart). Never raises: a snapshot that
        cannot be built or written costs the room its restart safety, not the players their game."""
        if not self._store.enabled:
            return
        try:
            if session.status in (RoomStatus.FINISHED, RoomStatus.CLOSED):
                self._writer.delete(session.room_code)
                return
            with session.publish_lock:
                state = session.state
            state_dict = None
            if state is not None:
                state_dict = self._service_for_ruleset(session.ruleset).state_to_save_dict(state)
            self._writer.save(record_of(session, state_dict))
        except Exception as exc:  # noqa: BLE001 - see above
            logger.warning("snapshot of room=%s failed (%s)", session.room_code, type(exc).__name__)

    def _code_kept_in_store(self, room_code: str) -> bool:
        if not self._store.enabled:
            return False
        try:
            return self._store.exists(room_code)
        except Exception as exc:  # noqa: BLE001 - a code is picked anyway
            logger.warning("store lookup failed (%s)", type(exc).__name__)
            return False

    def _find_room(self, room_code: str) -> GameSession:
        """The room with this code: in memory, or else read back from the store."""
        session = self._registry.find_room(room_code)
        if session is not None:
            return session
        code = normalize_room_code(room_code)
        key = f"room:{code}"
        if self._store.enabled and not self._recently_missed(key):
            session = self._rehydrate(lambda: self._store.load_by_room_code(code))
            if session is not None:
                return session
            self._remember_miss(key)
        raise MultiplayerError("room_not_found", "No room with that code.")

    def _resolve_token(self, seat_token: str | None) -> tuple[GameSession, Seat] | None:
        """The room and seat a token belongs to: in memory, or else read back from the store (a
        player coming back after a restart)."""
        resolved = self._registry.resolve_token(seat_token)
        if resolved is not None or not seat_token or not self._store.enabled:
            return resolved
        token_hash = hash_token(seat_token)
        key = f"token:{token_hash}"
        if self._recently_missed(key):
            return None
        if self._rehydrate(lambda: self._store.load_by_token_hash(token_hash)) is None:
            self._remember_miss(key)
            return None
        return self._registry.resolve_token(seat_token)

    def _recently_missed(self, key: str) -> bool:
        expires = self._misses.get(key)
        return expires is not None and expires > self._clock()

    def _remember_miss(self, key: str) -> None:
        if len(self._misses) >= MAX_REMEMBERED_MISSES:
            self._misses.clear()
        self._misses[key] = self._clock() + MISS_MEMORY_SECONDS

    def _rehydrate(self, load: Callable[[], SessionRecord | None]) -> GameSession | None:
        """Brings back the room `load` finds in the store, once: two requests that ask for the
        same sleeping room at the same moment get the same session. None if there is no such room
        or it cannot be restored. A store that cannot be read is not "no such room": the client is
        told to try again (`store_unavailable`), not to give up its seat."""
        with self._rehydrate_lock:
            try:
                record = load()
            except Exception as exc:  # noqa: BLE001 - see above
                logger.warning("store read failed (%s)", type(exc).__name__)
                raise MultiplayerError(
                    "store_unavailable", "Saved games cannot be read right now: try again."
                ) from exc
            if record is None:
                return None
            existing = self._registry.find_room(record.room_code)
            if existing is not None:
                return existing
            return self._session_from_record(record)

    def _session_from_record(self, record: SessionRecord) -> GameSession | None:
        payload = record.payload
        now = self._clock()
        try:
            if self._is_idle(
                RoomStatus(payload["status"]),
                payload.get("finished_at"),
                float(payload["last_activity_at"]),
                now,
            ):
                # What purging would have dropped: do not bring it back, and let it go for good.
                self._writer.delete(record.room_code)
                return None
            ruleset = payload["ruleset"]
            if ruleset not in self._rulesets:
                raise ValueError(f"unknown ruleset {ruleset!r}")
            service = self._service_for_ruleset(ruleset)
            state = (
                service.state_from_save_dict(payload["state"])
                if payload["state"] is not None
                else None
            )
            session = session_from_payload(payload, state)
            bot_policy = self._bot_policy_factory(session.bot_policy_name, session.ruleset)
        except Exception as exc:  # noqa: BLE001 - a snapshot we cannot read is a room we do not have
            logger.warning("room=%s cannot be restored (%s)", record.room_code, type(exc).__name__)
            return None
        session.last_activity_at = now
        for seat in session.seats:
            # Everybody gets the full time to reconnect after a restart.
            seat.last_seen_at = now
        self._registry.adopt(session)
        if session.game_id is not None:
            service.adopt_game(session.game_id, bot_policy=bot_policy)
        logger.info(
            "room restored room=%s game=%s status=%s revision=%d",
            session.room_code,
            session.game_id,
            session.status.value,
            record.revision,
        )
        if session.status is RoomStatus.RUNNING:
            with session.lock:
                if self._advance_bots(session):
                    self._persist(session)
        return session

    # ------------------------------------------------------------------ idle rooms

    @staticmethod
    def _is_idle(
        status: RoomStatus, finished_at: float | None, last_touched_at: float, now: float
    ) -> bool:
        if status is RoomStatus.FINISHED:
            return now - (finished_at or last_touched_at) > FINISHED_GRACE_SECONDS
        limit = {
            RoomStatus.LOBBY: LOBBY_IDLE_SECONDS,
            RoomStatus.RUNNING: RUNNING_IDLE_SECONDS,
            RoomStatus.CLOSED: CLOSED_GRACE_SECONDS,
        }[status]
        return now - last_touched_at > limit

    def _maybe_purge(self) -> None:
        now = self._clock()
        if now - self._last_purge < PURGE_INTERVAL_SECONDS:
            return
        self._last_purge = now
        self.purge_idle(now)

    def purge_idle(self, now: float | None = None) -> list[str]:
        """Forgets the rooms nobody has touched for too long (see the `*_IDLE_SECONDS` limits),
        in memory and in the store. A room somebody is acting on right now is skipped. Returns the
        codes it dropped."""
        now = self._clock() if now is None else now
        dropped: list[str] = []
        for session in self._registry.sessions():
            if not self._is_idle(
                session.status, session.finished_at, session.last_touched_at(), now
            ):
                continue
            if not session.lock.acquire(blocking=False):
                continue
            try:
                self._registry.remove(session)
                if session.game_id is not None:
                    self._service_for_ruleset(session.ruleset).forget_game(session.game_id)
                if self._store.enabled:
                    self._writer.delete(session.room_code)
                dropped.append(session.room_code)
                logger.info(
                    "room dropped room=%s status=%s", session.room_code, session.status.value
                )
            finally:
                session.lock.release()
        return dropped

    @staticmethod
    def _require_lobby(session: GameSession) -> None:
        if session.status is RoomStatus.CLOSED:
            raise MultiplayerError("room_closed", "The host closed this room.")
        if session.status is not RoomStatus.LOBBY:
            raise MultiplayerError("room_already_started", "The game has already started.")

    @staticmethod
    def _awaiting(state: GameState) -> PlayerId | None:
        return state.pending_decision.player_id if state.pending_decision is not None else None

    def _require_pending_decision(
        self,
        state: GameState,
        seat: Seat,
        decision_id: str,
        expected_revision: int | None = None,
    ) -> None:
        pending = state.pending_decision
        if state.status is GameStatus.FINISHED or pending is None:
            raise MultiplayerError("game_finished", "The game is over.")
        if pending.player_id != seat.player_id:
            raise MultiplayerError("not_your_turn", "It is not your decision to make.")
        if expected_revision is not None and expected_revision != state.revision:
            raise MultiplayerError(
                "stale_revision",
                "The game moved on since you looked at it.",
                {"expected": state.revision, "received": expected_revision},
            )
        if pending.decision_id != decision_id:
            raise MultiplayerError("stale_decision", "That decision is no longer the pending one.")

    def _read(
        self, session: GameSession, *, since: int | None
    ) -> tuple[GameState | None, list[EventBatch], RoomStatus]:
        """A consistent (state, newer batches, status) triple, without waiting for a writer."""
        with session.publish_lock:
            batches = (
                [b for b in session.event_log if b.revision_to > since] if since is not None else []
            )
            return session.state, batches, session.status

    def _commit(
        self,
        session: GameSession,
        new_state: GameState,
        *,
        revision_from: int,
        actor: PlayerId | None,
        segment_type: str,
        events: Sequence[DomainEvent],
        status: RoomStatus | None = None,
    ) -> EventBatch:
        """Publishes a new state together with the batch of events that produced it."""
        with session.publish_lock:
            batch = EventBatch(
                index=len(session.event_log),
                revision_from=revision_from,
                revision_to=new_state.revision,
                actor_player_id=actor,
                segment_type=segment_type,
                events=tuple(events),
                state_after=new_state,
            )
            session.event_log.append(batch)
            # Only the latest batches keep their state (see BATCH_STATE_WINDOW).
            expired = batch.index - BATCH_STATE_WINDOW
            if expired >= 0 and session.event_log[expired].state_after is not None:
                session.event_log[expired] = dataclasses.replace(
                    session.event_log[expired], state_after=None
                )
            session.state = new_state
            if status is not None:
                session.status = status
            if new_state.status is GameStatus.FINISHED:
                session.status = RoomStatus.FINISHED
                session.finished_at = self._clock()
        self._record_telemetry(session, new_state, segment_type, events)
        return batch

    def _record_telemetry(
        self,
        session: GameSession,
        state: GameState,
        segment_type: str,
        events: Sequence[DomainEvent],
    ) -> None:
        """Hands one committed step to the recorder: the game itself with its first step, then the
        events of every step, and the final scores when the game ends. Never raises."""
        try:
            if segment_type == "game_start":
                self._telemetry.game_started(
                    state,
                    mode="multi",
                    bot_policy=session.bot_policy_name,
                    room_code=session.room_code,
                )
            if events:
                self._telemetry.events(state, tuple(events))
            if state.status is GameStatus.FINISHED:
                self._telemetry.game_finished(state)
        except Exception as exc:  # noqa: BLE001 - recording must never cost a player their game
            logger.warning("telemetry of game=%s failed (%s)", session.game_id, type(exc).__name__)

    @staticmethod
    def _view(
        service: GameService, session: GameSession, state: GameState, viewer: PlayerId
    ) -> PlayerGameView:
        """The viewer's board. A seat a bot is standing in for (`away`) still reads as its human's:
        the screen names a human by their nickname and a bot by its gang, and a player who is
        only gone for a while does not turn into a gang and back."""
        view = service.view_for(state, viewer, hide_future_jobs=True)
        away = {seat.player_id for seat in session.seats if seat.away}
        if not away:
            return view
        return dataclasses.replace(
            view,
            players=tuple(
                dataclasses.replace(player, controller_type=ControllerType.HUMAN)
                if player.player_id in away
                else player
                for player in view.players
            ),
        )

    def _views_after(
        self,
        service: GameService,
        session: GameSession,
        batches: Sequence[EventBatch],
        viewer: PlayerId,
    ) -> tuple[PlayerGameView | None, ...]:
        return tuple(
            self._view(service, session, b.state_after, viewer)
            if b.state_after is not None
            else None
            for b in batches
        )

    def _advance_bots(self, session: GameSession) -> list[EventBatch]:
        """Plays the bots and the automatic steps, one segment at a time (so every segment is its
        own batch for the clients to narrate), until a human has to decide or the game is over.
        The server does this after every accepted human command: no browser is in charge of
        making the game continue (section 12). Returns the batches it produced."""
        service = self._service_for_ruleset(session.ruleset)
        state = session.state
        assert state is not None
        produced: list[EventBatch] = []
        for _ in range(MAX_BOT_SEGMENTS):
            if state.status is GameStatus.FINISHED:
                return produced
            actor = state.current_player_id
            revision_from = state.revision
            result = service.advance(state, single_player_segment=True)
            if result.state is state:
                return produced  # nothing moved: a human decision is pending
            state = result.state
            produced.append(
                self._commit(
                    session,
                    state,
                    revision_from=revision_from,
                    actor=actor,
                    segment_type="bot_segment",
                    events=result.events,
                )
            )
        raise RuntimeError(f"Bot cascade of game {session.game_id} did not settle.")

    def _seat_becomes_bot(self, session: GameSession, seat: Seat) -> None:
        """A human left a running game: their seat is played by a bot from now on."""
        state = session.state
        assert state is not None
        new_state = copy.deepcopy(state)
        new_state.revision += 1
        player = next(p for p in new_state.players if p.player_id == seat.player_id)
        player.controller_type = ControllerType.BOT
        seat.controller_type = ControllerType.BOT
        seat.left = True
        seat.away = False
        logger.info("seat left game=%s seat=%d", session.game_id, seat.seat_index)
        self._commit(
            session,
            new_state,
            revision_from=state.revision,
            actor=seat.player_id,
            segment_type="seat_left",
            events=(),
        )
        self._advance_bots(session)

    # ------------------------------------------------------- absent players (section 47)

    def _is_absent(self, session: GameSession, seat: Seat) -> bool:
        """A human seat nobody has heard from for `SEAT_AWAY_SECONDS`. A seat is "heard from" when
        it joins, when this process first knows the room (a restart) and on every request of its."""
        if not seat.is_human or seat.left or seat.away:
            return False
        last_heard = seat.last_seen_at if seat.last_seen_at is not None else session.created_at
        return self._clock() - last_heard > self._away_after

    def _take_over_if_due(self, session: GameSession) -> None:
        """Called when somebody asks about the game: if it is waiting for a human who has gone,
        a bot takes the seat. Never waits for a game that is busy (a cascade is running: the next
        request will find it done)."""
        state = session.state
        if state is None or session.status is not RoomStatus.RUNNING:
            return
        pending = state.pending_decision
        if pending is None or not self._is_absent(
            session, session.seat_by_player(pending.player_id)
        ):
            return
        if not session.lock.acquire(blocking=False):
            return
        try:
            if self._take_over_if_away(session):
                self._persist(session)
        finally:
            session.lock.release()

    def _take_over_if_away(self, session: GameSession) -> list[EventBatch]:
        """While the game waits for an absent human, a bot plays their seat — which, as the bots
        play on until a human has to decide, is every decision of theirs up to the next present
        human. Holds `session.lock`. Returns the batches it produced."""
        produced: list[EventBatch] = []
        for _ in range(SEAT_COUNT):
            state = session.state
            if (
                state is None
                or state.status is GameStatus.FINISHED
                or state.pending_decision is None
            ):
                break
            seat = session.seat_by_player(state.pending_decision.player_id)
            if not self._is_absent(session, seat):
                break
            produced.append(self._set_seat_controller(session, seat, away=True))
            produced.extend(self._advance_bots(session))
        return produced

    def _reclaim_seat(self, session: GameSession, seat: Seat) -> None:
        """The player of a seat a bot has been playing is back: it is theirs again. The game is at
        a human decision (the bots play until one), never the returning player's own, so the
        handover is clean."""
        with session.lock:
            if not seat.away:
                return  # another request of theirs got here first
            if session.state is None or session.status is not RoomStatus.RUNNING:
                seat.away = False
                return
            self._set_seat_controller(session, seat, away=False)
            self._persist(session)

    def _set_seat_controller(self, session: GameSession, seat: Seat, *, away: bool) -> EventBatch:
        state = session.state
        assert state is not None
        new_state = copy.deepcopy(state)
        new_state.revision += 1
        player = next(p for p in new_state.players if p.player_id == seat.player_id)
        player.controller_type = ControllerType.BOT if away else ControllerType.HUMAN
        seat.away = away
        logger.info(
            "seat %s game=%s seat=%d",
            "away" if away else "returned",
            session.game_id,
            seat.seat_index,
        )
        return self._commit(
            session,
            new_state,
            revision_from=state.revision,
            actor=seat.player_id,
            segment_type="seat_away" if away else "seat_returned",
            events=(),
        )

    def _seat_info(self, session: GameSession, seat: Seat) -> SeatInfo:
        return SeatInfo(
            seat_index=seat.seat_index,
            player_id=seat.player_id,
            controller_type=seat.controller_type,
            nickname=seat.nickname,
            occupied=seat.joined or not seat.is_human,
            is_host=seat.seat_index == session.host_seat_index,
            left=seat.left,
            away=seat.away,
        )

    def _room_info(self, session: GameSession) -> RoomInfo:
        return RoomInfo(
            room_code=session.room_code,
            status=session.status,
            ruleset=session.ruleset,
            human_seat_count=session.human_seat_count,
            bot_policy=session.bot_policy_name,
            game_id=session.game_id,
            seats=tuple(self._seat_info(session, seat) for seat in session.seats),
        )

    @staticmethod
    def _credentials(session: GameSession, seat: Seat, token: str) -> Credentials:
        return Credentials(
            room_code=session.room_code,
            game_id=session.game_id,
            seat_index=seat.seat_index,
            player_id=seat.player_id,
            seat_token=token,
        )
