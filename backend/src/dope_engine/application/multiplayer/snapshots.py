"""A room as a snapshot, and back (docs/architecture/GPT_MULTIPLAYER.md sections 43-44).

What is kept is what a restart would otherwise lose: who sits where (with the hash of each seat
token, never the token), the room's settings and clock, and the game state. What is not kept is
what can be rebuilt or does not matter after a restart: the locks, the event log (a client that
asks for events older than the restart is simply sent the current board) and the bot policy (made
again from its name).

The state travels as `GameService.state_to_save_dict` writes it, so a snapshot is exactly as
portable as a solo save; this module never looks inside it.
"""

from __future__ import annotations

from typing import Any

from dope_engine.application.multiplayer.models import GameSession, RoomStatus, Seat
from dope_engine.application.multiplayer.store import SNAPSHOT_FORMAT_VERSION, SessionRecord
from dope_engine.domain.enums import ControllerType
from dope_engine.domain.ids import GameId, PlayerId
from dope_engine.domain.state import GameState


def record_of(session: GameSession, state_dict: dict[str, Any] | None) -> SessionRecord:
    """The record to store for `session` as it is now. The caller holds the session still (its
    publish lock) so seats, status and state are one moment."""
    payload: dict[str, Any] = {
        "format_version": SNAPSHOT_FORMAT_VERSION,
        "room_code": session.room_code,
        "ruleset": session.ruleset,
        "bot_policy": session.bot_policy_name,
        "human_seat_count": session.human_seat_count,
        "host_seat_index": session.host_seat_index,
        "status": session.status.value,
        "game_id": session.game_id,
        "created_at": session.created_at,
        "started_at": session.started_at,
        "finished_at": session.finished_at,
        # Polling counts as being there: a room people are looking at is not idle.
        "last_activity_at": session.last_touched_at(),
        "seats": [
            {
                "player_id": seat.player_id,
                "seat_index": seat.seat_index,
                "controller_type": seat.controller_type.value,
                "nickname": seat.nickname,
                "token_hash": seat.token_hash,
                "joined": seat.joined,
                "left": seat.left,
            }
            for seat in session.seats
        ],
        "state": state_dict,
    }
    return SessionRecord(
        room_code=session.room_code,
        status=session.status.value,
        revision=session.state.revision if session.state is not None else 0,
        token_hashes=tuple(seat.token_hash for seat in session.seats if seat.token_hash),
        payload=payload,
    )


def session_from_payload(payload: dict[str, Any], state: GameState | None) -> GameSession:
    """The room a snapshot describes. `state` is the payload's game, already read back by the
    caller (which knows the schema it expects). Raises KeyError/ValueError on a payload that is not
    one of ours."""
    if payload["format_version"] != SNAPSHOT_FORMAT_VERSION:
        raise ValueError(f"unknown snapshot format {payload['format_version']!r}")
    status = RoomStatus(payload["status"])
    if status in (RoomStatus.RUNNING, RoomStatus.FINISHED) and state is None:
        raise ValueError("a started room's snapshot has no game state")
    seats = [
        Seat(
            player_id=PlayerId(item["player_id"]),
            seat_index=int(item["seat_index"]),
            controller_type=ControllerType(item["controller_type"]),
            nickname=item["nickname"],
            token_hash=item["token_hash"],
            joined=bool(item["joined"]),
            left=bool(item["left"]),
        )
        for item in payload["seats"]
    ]
    game_id = payload["game_id"]
    return GameSession(
        room_code=payload["room_code"],
        ruleset=payload["ruleset"],
        bot_policy_name=payload["bot_policy"],
        human_seat_count=int(payload["human_seat_count"]),
        seats=seats,
        host_seat_index=int(payload["host_seat_index"]),
        status=status,
        game_id=GameId(game_id) if game_id is not None else None,
        state=state,
        created_at=float(payload["created_at"]),
        started_at=payload["started_at"],
        finished_at=payload["finished_at"],
        last_activity_at=float(payload["last_activity_at"]),
    )
