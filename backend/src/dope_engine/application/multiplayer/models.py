"""Rooms, seats and the per-game event log (docs/architecture/GPT_MULTIPLAYER.md sections 5-9, 14).

Everything multiplayer sits *around* the game engine: a `GameSession` owns one `GameState` (never
mutated once published: every command makes a new one) together with who sits where, the secret
credentials of the human seats and the append-only log of what happened. Nothing here knows about
HTTP.

Vocabulary (section 59): *room* = the pre-game lobby and its lifecycle, *game* = the running
match, *seat* = one of the four positions, `player_id` = the engine identity (`player_0`...),
*seat token* = the secret that proves who is calling, *controller* = HUMAN or BOT, *revision* =
the authoritative state version, *event batch* = what one authoritative step produced.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from dope_engine.domain.enums import ControllerType
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import GameId, PlayerId
from dope_engine.domain.state import GameState

# DOPE always has four gameplay seats (the Raids split the players 1+4 against 2+3).
SEAT_COUNT = 4
MIN_HUMAN_SEATS = 2
# How many of the latest event batches keep the game state they produced. A client replaying what
# happened (one bot action at a time) needs the board after *each* step, not only the last one;
# an older step is told without its board, and the client just jumps to the next one that has it.
# A state is ~75 KB, so this is a few MB per game.
BATCH_STATE_WINDOW = 80

# How long a room may sit untouched (no command, no join, nobody polling) before it is dropped from
# memory and from the store. A running game gets a long time: a table can stop for dinner.
LOBBY_IDLE_SECONDS = 2 * 60 * 60
RUNNING_IDLE_SECONDS = 6 * 60 * 60
# A finished or closed room is kept a little, so late pollers still read why it ended.
FINISHED_GRACE_SECONDS = 15 * 60
CLOSED_GRACE_SECONDS = 10 * 60
# Dropping idle rooms is done at most this often, when a room is created.
PURGE_INTERVAL_SECONDS = 60
# A human whose browser has not been heard from for this long while the game waits for them is
# replaced by a bot until they come back (section 47). A browser that is open asks every second or
# so, even from a background tab, so this means "gone", not "thinking".
SEAT_AWAY_SECONDS = 90


class RoomStatus(StrEnum):
    LOBBY = "lobby"
    RUNNING = "running"
    FINISHED = "finished"
    # The host left before the game started.
    CLOSED = "closed"


class MultiplayerError(Exception):
    """A typed failure meant for the client (section 57): `code` is stable, `message` is for
    humans, `details` carries what the client needs to recover (never anything hidden)."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass
class Seat:
    player_id: PlayerId
    seat_index: int
    controller_type: ControllerType
    nickname: str | None = None
    # SHA-256 of the seat token; the raw token is handed out once and never kept.
    token_hash: str | None = None
    # A human seat someone has taken (a bot seat never "joins").
    joined: bool = False
    # A human who left a running game: the seat is a bot from then on.
    left: bool = False
    # A human who stopped answering while the game waited for them: a bot plays the seat (in the
    # game state) until they come back. The seat stays theirs: their token still works.
    away: bool = False
    last_seen_at: float | None = None

    @property
    def is_human(self) -> bool:
        return self.controller_type == ControllerType.HUMAN


@dataclass(frozen=True)
class EventBatch:
    """What one authoritative step produced, in the order it happened (section 14). `index` is the
    batch's position in the game's log; `revision_to` is the state revision after the step."""

    index: int
    revision_from: int
    revision_to: int
    actor_player_id: PlayerId | None
    # "game_start", "human_command", "bot_segment", "seat_left", "seat_away" or "seat_returned".
    segment_type: str
    events: tuple[DomainEvent, ...]
    # The game as it was right after this step, kept only for the latest `BATCH_STATE_WINDOW`
    # batches (then None). Never sent as it is: a viewer's own view of it is.
    state_after: GameState | None = field(default=None, repr=False, compare=False)


@dataclass
class GameSession:
    room_code: str
    ruleset: str
    bot_policy_name: str
    human_seat_count: int
    seats: list[Seat]
    host_seat_index: int = 0
    status: RoomStatus = RoomStatus.LOBBY
    game_id: GameId | None = None
    # The authoritative state. Replaced, never mutated, once published.
    state: GameState | None = None
    event_log: list[EventBatch] = field(default_factory=list)
    # Fixed by tests only; real games get a server-side random seed (a client-chosen seed would let
    # its author work out every hand).
    seed: int | None = field(default=None, repr=False)
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    last_activity_at: float = field(default_factory=time.time)
    # One authoritative mutation at a time per game (section 21): read, authorize, validate the
    # revision, apply, advance the bots, store the events. Never held across games.
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    # Taken for an instant to publish (state, log) together or to read them together, so readers
    # never wait for a bot cascade and never see a state without its events.
    publish_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def seat_by_player(self, player_id: PlayerId) -> Seat:
        return next(seat for seat in self.seats if seat.player_id == player_id)

    def last_touched_at(self) -> float:
        """The last time anything happened here or somebody looked: a command, a join, a poll."""
        return max(
            [
                self.last_activity_at,
                *(seat.last_seen_at for seat in self.seats if seat.last_seen_at),
            ]
        )
