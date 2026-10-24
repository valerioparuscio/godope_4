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
import logging
import re
import secrets
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
    MIN_HUMAN_SEATS,
    SEAT_COUNT,
    EventBatch,
    GameSession,
    MultiplayerError,
    RoomStatus,
    Seat,
)
from dope_engine.application.multiplayer.registry import GameRegistry, normalize_room_code
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


@dataclass(frozen=True)
class AnswerResult:
    revision: int
    status: RoomStatus
    awaiting_player_id: PlayerId | None
    batches: tuple[EventBatch, ...]
    view: PlayerGameView


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

    @property
    def registry(self) -> GameRegistry:
        return self._registry

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
        session = GameSession(
            room_code=self._registry.new_room_code(),
            ruleset=ruleset,
            bot_policy_name=bot_policy,
            human_seat_count=human_seats,
            seats=seats,
        )
        self._registry.add(session)
        host = seats[session.host_seat_index]
        host.joined = True
        host.nickname = nickname
        token = self._registry.issue_token(session, host)
        logger.info(
            "room created room=%s ruleset=%s humans=%d", session.room_code, ruleset, human_seats
        )
        return self._credentials(session, host, token)

    def join_room(self, room_code: str, nickname: str) -> Credentials:
        nickname = clean_nickname(nickname)
        session = self._registry.room(room_code)
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
            session.last_activity_at = self._clock()
            logger.info("seat joined room=%s seat=%d", session.room_code, seat.seat_index)
            return self._credentials(session, seat, token)

    def room_info(self, room_code: str) -> RoomInfo:
        """The safe, public description of a room: who sits where, never a token."""
        session = self._registry.room(room_code)
        with session.publish_lock:
            return self._room_info(session)

    def room_for_caller(
        self, room_code: str, seat_token: str | None
    ) -> tuple[RoomInfo, SeatInfo | None]:
        """`room_info` plus the caller's own seat, if the token is a valid one for *this* room —
        what a client that reloads the page asks to find out whether it still has its seat."""
        session = self._registry.room(room_code)
        with session.publish_lock:
            info = self._room_info(session)
        resolved = self._registry.resolve_token(seat_token)
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
                    return None
                self._registry.revoke_token(seat)
                seat.joined = False
                seat.nickname = None
                return self.room_info(room_code)
            if session.status is RoomStatus.RUNNING:
                self._seat_becomes_bot(session, seat)
            self._registry.revoke_token(seat)
            return self.room_info(room_code)

    # --------------------------------------------------------------- the game

    def authenticate(self, game_id: str, seat_token: str | None) -> tuple[GameSession, Seat]:
        """The only way a game request learns who is calling: from the token, never from the
        request body (section 3.2). A token of another room is as good as none."""
        resolved = self._registry.resolve_token(seat_token)
        if resolved is None:
            raise MultiplayerError("invalid_token", "Missing or unknown seat token.")
        session, seat = resolved
        if session.game_id is None or session.game_id != game_id:
            raise MultiplayerError("invalid_token", "That seat token is not for this game.")
        seat.last_seen_at = self._clock()
        return session, seat

    def snapshot(self, game_id: str, seat_token: str | None) -> PlayerSnapshot:
        session, seat = self.authenticate(game_id, seat_token)
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
            view=service.view_for(state, seat.player_id, hide_future_jobs=True),
        )

    def events_since(
        self, game_id: str, seat_token: str | None, since: int, *, include_view: bool = False
    ) -> EventsResult:
        """The event batches after revision `since`, as this player may see them. Read-only:
        polling never moves the game (section 19)."""
        session, seat = self.authenticate(game_id, seat_token)
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
            view=(
                service.view_for(state, seat.player_id, hide_future_jobs=True)
                if include_view
                else None
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
                view_for=lambda current: service.view_for(
                    current, seat.player_id, hide_future_jobs=True
                ),
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
            first_new_batch = len(session.event_log)
            logger.info(
                "answer game=%s revision=%d seat=%d decision=%s events=%d",
                game_id,
                state.revision,
                seat.seat_index,
                state.pending_decision.decision_type if state.pending_decision else "-",
                len(outcome.events),
            )
            self._commit(
                session,
                outcome.state,
                revision_from=state.revision,
                actor=seat.player_id,
                segment_type="human_command",
                events=outcome.events,
            )
            self._advance_bots(session)
            session.last_activity_at = self._clock()
            final_state = session.state
            assert final_state is not None
            with session.publish_lock:
                new_batches = tuple(session.event_log[first_new_batch:])
                status = session.status
            return AnswerResult(
                revision=final_state.revision,
                status=status,
                awaiting_player_id=self._awaiting(final_state),
                batches=tuple(filter_batch_for_viewer(b, seat.player_id) for b in new_batches),
                view=service.view_for(final_state, seat.player_id, hide_future_jobs=True),
            )

    # ---------------------------------------------------------------- internals

    def _authenticate_room(
        self, room_code: str, seat_token: str | None
    ) -> tuple[GameSession, Seat]:
        resolved = self._registry.resolve_token(seat_token)
        if resolved is None:
            raise MultiplayerError("invalid_token", "Missing or unknown seat token.")
        session, seat = resolved
        if session.room_code != normalize_room_code(room_code):
            raise MultiplayerError("invalid_token", "That seat token is not for this room.")
        seat.last_seen_at = self._clock()
        return session, seat

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
    ) -> None:
        """Publishes a new state together with the batch of events that produced it."""
        with session.publish_lock:
            session.event_log.append(
                EventBatch(
                    index=len(session.event_log),
                    revision_from=revision_from,
                    revision_to=new_state.revision,
                    actor_player_id=actor,
                    segment_type=segment_type,
                    events=tuple(events),
                )
            )
            session.state = new_state
            if status is not None:
                session.status = status
            if new_state.status is GameStatus.FINISHED:
                session.status = RoomStatus.FINISHED
                session.finished_at = self._clock()

    def _advance_bots(self, session: GameSession) -> None:
        """Plays the bots and the automatic steps, one segment at a time (so every segment is its
        own batch for the clients to narrate), until a human has to decide or the game is over.
        The server does this after every accepted human command: no browser is in charge of
        making the game continue (section 12)."""
        service = self._service_for_ruleset(session.ruleset)
        state = session.state
        assert state is not None
        for _ in range(MAX_BOT_SEGMENTS):
            if state.status is GameStatus.FINISHED:
                return
            actor = state.current_player_id
            revision_from = state.revision
            result = service.advance(state, single_player_segment=True)
            if result.state is state:
                return  # nothing moved: a human decision is pending
            state = result.state
            self._commit(
                session,
                state,
                revision_from=revision_from,
                actor=actor,
                segment_type="bot_segment",
                events=result.events,
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

    def _seat_info(self, session: GameSession, seat: Seat) -> SeatInfo:
        return SeatInfo(
            seat_index=seat.seat_index,
            player_id=seat.player_id,
            controller_type=seat.controller_type,
            nickname=seat.nickname,
            occupied=seat.joined or not seat.is_human,
            is_host=seat.seat_index == session.host_seat_index,
            left=seat.left,
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
