"""The set of live rooms/games and the seat-token index (docs/architecture/GPT_MULTIPLAYER.md
sections 8, 9, 11).

Rooms and games live in this process's memory (one backend process, section 45). The registry
only does bookkeeping under one short lock; the work on a game happens under that game's own lock
(`GameSession.lock`), never under this one.

Seat tokens are generated here, handed out once, and kept only as SHA-256 hashes: a token is 256
random bits, so the hash is enough to look it up and the raw value can't be recovered from the
registry (or from a log or a dump of it).
"""

from __future__ import annotations

import hashlib
import secrets
import threading

from dope_engine.application.multiplayer.models import GameSession, MultiplayerError, Seat
from dope_engine.domain.ids import GameId

# No 0/O, 1/I/L: room codes get read out loud and typed by hand.
ROOM_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
ROOM_CODE_LENGTH = 4


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_room_code(code: str) -> str:
    return code.strip().upper()


class GameRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_room_code: dict[str, GameSession] = {}
        self._by_game_id: dict[GameId, GameSession] = {}
        # token hash -> (room code, seat index)
        self._seat_by_token_hash: dict[str, tuple[str, int]] = {}

    # --- rooms and games

    def new_room_code(self) -> str:
        """A fresh code, unique among the rooms alive right now. Call `add` with it right away
        (the caller holds no lock in between: a clash is retried there)."""
        while True:
            code = "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))
            with self._lock:
                if code not in self._by_room_code:
                    return code

    def add(self, session: GameSession) -> None:
        with self._lock:
            if session.room_code in self._by_room_code:
                raise MultiplayerError("room_code_taken", "That room code is already in use.")
            self._by_room_code[session.room_code] = session

    def room(self, room_code: str) -> GameSession:
        with self._lock:
            session = self._by_room_code.get(normalize_room_code(room_code))
        if session is None:
            raise MultiplayerError("room_not_found", "No room with that code.")
        return session

    def game(self, game_id: str) -> GameSession:
        with self._lock:
            session = self._by_game_id.get(GameId(game_id))
        if session is None:
            raise MultiplayerError("game_not_found", "No multiplayer game with that id.")
        return session

    def bind_game(self, session: GameSession, game_id: GameId) -> None:
        with self._lock:
            self._by_game_id[game_id] = session

    def remove(self, session: GameSession) -> None:
        """Forgets a room/game and every token that belonged to it."""
        with self._lock:
            self._by_room_code.pop(session.room_code, None)
            if session.game_id is not None:
                self._by_game_id.pop(session.game_id, None)
            for seat in session.seats:
                if seat.token_hash is not None:
                    self._seat_by_token_hash.pop(seat.token_hash, None)

    def sessions(self) -> list[GameSession]:
        with self._lock:
            return list(self._by_room_code.values())

    # --- seat tokens

    def issue_token(self, session: GameSession, seat: Seat) -> str:
        """A new secret for `seat`; any earlier one stops working. Returned once, never stored."""
        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)
        with self._lock:
            if seat.token_hash is not None:
                self._seat_by_token_hash.pop(seat.token_hash, None)
            seat.token_hash = token_hash
            self._seat_by_token_hash[token_hash] = (session.room_code, seat.seat_index)
        return token

    def revoke_token(self, seat: Seat) -> None:
        with self._lock:
            if seat.token_hash is not None:
                self._seat_by_token_hash.pop(seat.token_hash, None)
            seat.token_hash = None

    def resolve_token(self, token: str | None) -> tuple[GameSession, Seat] | None:
        """The room and seat a token belongs to, or None. The token is the only thing that says
        who is calling (section 3.2)."""
        if not token:
            return None
        with self._lock:
            located = self._seat_by_token_hash.get(hash_token(token))
            session = self._by_room_code.get(located[0]) if located is not None else None
        if located is None or session is None:
            return None
        return session, session.seats[located[1]]
