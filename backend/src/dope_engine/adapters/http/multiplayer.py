"""Multiplayer HTTP routes (docs/architecture/GPT_MULTIPLAYER.md sections 10, 18, 28).

Thin on purpose: parse, call `MultiplayerService`, serialize. Who is calling comes from the
`Authorization: Bearer <seat token>` header and nowhere else — these routes take no `player_id`.
The solo routes in `app.py` are untouched and cannot reach a multiplayer game: its state lives only
in the multiplayer registry.

Errors are typed (section 57): `{"error": <code>, "message": ..., "details": {...}}` with a status
the client can act on (401 unknown token, 403 not allowed, 404 no such room, 409 the game moved on).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any, Literal

from fastapi import APIRouter, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dope_engine.adapters.http.schemas import GameViewResponse
from dope_engine.adapters.http.serialization import (
    plan_to_response,
    serialize_event,
    to_view_response,
)
from dope_engine.application.multiplayer.models import EventBatch, MultiplayerError
from dope_engine.application.multiplayer.service import (
    AnswerResult,
    Credentials,
    EventsResult,
    MultiplayerService,
    PlayerSnapshot,
    RoomInfo,
    SeatInfo,
)
from dope_engine.application.views import PlayerGameView

STATUS_BY_ERROR_CODE: dict[str, int] = {
    "invalid_request": 400,
    "invalid_decision": 400,
    "invalid_token": 401,
    "forbidden": 403,
    "room_not_found": 404,
    "game_not_found": 404,
    "room_full": 409,
    "room_already_started": 409,
    "room_not_ready": 409,
    "room_closed": 409,
    "room_code_taken": 409,
    "nickname_taken": 409,
    "not_your_turn": 409,
    "stale_revision": 409,
    "stale_decision": 409,
    "game_finished": 409,
    # Saved games cannot be read right now (a restart with the database down): try again.
    "store_unavailable": 503,
}


# ------------------------------------------------------------------ requests


class CreateRoomRequest(BaseModel):
    ruleset: Literal["standard", "simple", "easy_price"] = "easy_price"
    human_seats: int = Field(ge=2, le=4)
    bot_policy: Literal["random_legal", "heuristic"] = "heuristic"
    nickname: str = Field(min_length=1, max_length=64)
    # No `seed`: whoever chose it could work out every hand.


class JoinRoomRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=64)


class AnswerRequest(BaseModel):
    decision_id: str
    expected_revision: int
    selected_option_ids: list[str] = Field(default_factory=list, max_length=64)
    preparatory_selections: list[list[str]] = Field(default_factory=list, max_length=8)


class PlanRequest(BaseModel):
    decision_id: str
    selections: list[list[str]] = Field(default_factory=list, max_length=8)


# ----------------------------------------------------------------- responses


class SeatResponse(BaseModel):
    seat_index: int
    player_id: str
    controller_type: str
    nickname: str | None
    occupied: bool
    is_host: bool
    left: bool
    # Not answering: a bot plays this seat until its player comes back.
    away: bool = False


class RoomResponse(BaseModel):
    room_code: str
    status: str
    ruleset: str
    human_seats: int
    bot_policy: str
    game_id: str | None
    seats: list[SeatResponse]
    # The caller's own seat, only on `GET /rooms/{code}` and only with a valid token for that room.
    me: SeatResponse | None = None


class CredentialsResponse(BaseModel):
    room_code: str
    game_id: str | None
    seat_index: int
    player_id: str
    seat_token: str


class LeaveResponse(BaseModel):
    room: RoomResponse | None


class MultiplayerViewResponse(BaseModel):
    room: RoomResponse
    me: SeatResponse
    revision: int
    status: str
    awaiting_player_id: str | None
    view: GameViewResponse


class EventBatchResponse(BaseModel):
    index: int
    revision_from: int
    revision_to: int
    actor_player_id: str | None
    segment_type: str
    events: list[dict[str, Any]]
    # The caller's view right after this step, when asked for (`include_views`) and the step is
    # recent enough to still have its board: what lets a client replay a bot cascade one action
    # at a time instead of jumping to the end.
    view: GameViewResponse | None = None


class EventsResponse(BaseModel):
    game_id: str
    from_revision: int
    current_revision: int
    status: str
    awaiting_player_id: str | None
    requires_refresh: bool
    batches: list[EventBatchResponse]
    view: GameViewResponse | None = None


class AnswerResponse(BaseModel):
    ok: bool = True
    revision: int
    status: str
    awaiting_player_id: str | None
    batches: list[EventBatchResponse]
    view: GameViewResponse


# ------------------------------------------------------------------- mapping


def _seat(seat: SeatInfo) -> SeatResponse:
    return SeatResponse(
        seat_index=seat.seat_index,
        player_id=seat.player_id,
        controller_type=seat.controller_type.value,
        nickname=seat.nickname,
        occupied=seat.occupied,
        is_host=seat.is_host,
        left=seat.left,
        away=seat.away,
    )


def _room(room: RoomInfo) -> RoomResponse:
    return RoomResponse(
        room_code=room.room_code,
        status=room.status.value,
        ruleset=room.ruleset,
        human_seats=room.human_seat_count,
        bot_policy=room.bot_policy,
        game_id=room.game_id,
        seats=[_seat(seat) for seat in room.seats],
    )


def _credentials(credentials: Credentials) -> CredentialsResponse:
    return CredentialsResponse(
        room_code=credentials.room_code,
        game_id=credentials.game_id,
        seat_index=credentials.seat_index,
        player_id=credentials.player_id,
        seat_token=credentials.seat_token,
    )


def _batch(batch: EventBatch, view: PlayerGameView | None = None) -> EventBatchResponse:
    return EventBatchResponse(
        index=batch.index,
        revision_from=batch.revision_from,
        revision_to=batch.revision_to,
        actor_player_id=batch.actor_player_id,
        segment_type=batch.segment_type,
        events=[serialize_event(event) for event in batch.events],
        view=to_view_response(view) if view is not None else None,
    )


def _batches(
    batches: Sequence[EventBatch], views: Sequence[PlayerGameView | None]
) -> list[EventBatchResponse]:
    """The batches, each with its own view when views were requested."""
    paired = zip(batches, views, strict=True) if views else ((b, None) for b in batches)
    return [_batch(batch, view) for batch, view in paired]


def _snapshot(snapshot: PlayerSnapshot) -> MultiplayerViewResponse:
    return MultiplayerViewResponse(
        room=_room(snapshot.room),
        me=_seat(snapshot.me),
        revision=snapshot.revision,
        status=snapshot.status.value,
        awaiting_player_id=snapshot.awaiting_player_id,
        view=to_view_response(snapshot.view),
    )


def _events(result: EventsResult) -> EventsResponse:
    return EventsResponse(
        game_id=result.game_id,
        from_revision=result.from_revision,
        current_revision=result.current_revision,
        status=result.status.value,
        awaiting_player_id=result.awaiting_player_id,
        requires_refresh=result.requires_refresh,
        batches=_batches(result.batches, result.batch_views),
        view=to_view_response(result.view) if result.view is not None else None,
    )


def _answer(result: AnswerResult) -> AnswerResponse:
    return AnswerResponse(
        revision=result.revision,
        status=result.status.value,
        awaiting_player_id=result.awaiting_player_id,
        batches=_batches(result.batches, result.batch_views),
        view=to_view_response(result.view),
    )


def bearer_token(authorization: str | None) -> str | None:
    """The token out of `Authorization: Bearer <token>`; anything else is "no token"."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


Authorization = Annotated[str | None, Header()]


def build_router(service: MultiplayerService) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    # -------------------------------------------------------------- rooms

    @router.post("/rooms", response_model=CredentialsResponse)
    def create_room(req: CreateRoomRequest) -> CredentialsResponse:
        return _credentials(
            service.create_room(
                ruleset=req.ruleset,
                human_seats=req.human_seats,
                bot_policy=req.bot_policy,
                nickname=req.nickname,
            )
        )

    @router.get("/rooms/{room_code}", response_model=RoomResponse)
    def get_room(room_code: str, authorization: Authorization = None) -> RoomResponse:
        room, me = service.room_for_caller(room_code, bearer_token(authorization))
        response = _room(room)
        response.me = _seat(me) if me is not None else None
        return response

    @router.post("/rooms/{room_code}/join", response_model=CredentialsResponse)
    def join_room(room_code: str, req: JoinRoomRequest) -> CredentialsResponse:
        return _credentials(service.join_room(room_code, req.nickname))

    @router.post("/rooms/{room_code}/start", response_model=RoomResponse)
    def start_room(room_code: str, authorization: Authorization = None) -> RoomResponse:
        return _room(service.start_room(room_code, bearer_token(authorization)))

    @router.post("/rooms/{room_code}/leave", response_model=LeaveResponse)
    def leave_room(room_code: str, authorization: Authorization = None) -> LeaveResponse:
        room = service.leave(room_code, bearer_token(authorization))
        return LeaveResponse(room=_room(room) if room is not None else None)

    # -------------------------------------------------------------- games

    @router.get("/mp/games/{game_id}/view", response_model=MultiplayerViewResponse)
    def get_view(game_id: str, authorization: Authorization = None) -> MultiplayerViewResponse:
        return _snapshot(service.snapshot(game_id, bearer_token(authorization)))

    @router.get("/mp/games/{game_id}/events", response_model=EventsResponse)
    def get_events(
        game_id: str,
        since: int = 0,
        include_view: bool = False,
        include_views: bool = False,
        authorization: Authorization = None,
    ) -> EventsResponse:
        return _events(
            service.events_since(
                game_id,
                bearer_token(authorization),
                since,
                include_view=include_view,
                include_batch_views=include_views,
            )
        )

    @router.post("/mp/games/{game_id}/decisions/plan")
    def plan_decision(
        game_id: str, req: PlanRequest, authorization: Authorization = None
    ) -> dict[str, Any]:
        plan = service.plan(game_id, bearer_token(authorization), req.decision_id, req.selections)
        return plan_to_response(plan)

    @router.post("/mp/games/{game_id}/decisions/answer", response_model=AnswerResponse)
    def answer_decision(
        game_id: str, req: AnswerRequest, authorization: Authorization = None
    ) -> AnswerResponse:
        return _answer(
            service.answer(
                game_id,
                bearer_token(authorization),
                decision_id=req.decision_id,
                selected_option_ids=req.selected_option_ids,
                preparatory_selections=req.preparatory_selections,
                expected_revision=req.expected_revision,
            )
        )

    @router.post("/mp/games/{game_id}/leave", response_model=LeaveResponse)
    def leave_game(game_id: str, authorization: Authorization = None) -> LeaveResponse:
        session, _seat = service.authenticate(game_id, bearer_token(authorization))
        room = service.leave(session.room_code, bearer_token(authorization))
        return LeaveResponse(room=_room(room) if room is not None else None)

    return router


def install(app: FastAPI, service: MultiplayerService) -> None:
    """Adds the multiplayer routes and their typed error responses to `app`."""

    @app.exception_handler(MultiplayerError)
    async def _multiplayer_error(_request: Request, exc: MultiplayerError) -> JSONResponse:
        return JSONResponse(
            status_code=STATUS_BY_ERROR_CODE.get(exc.code, 400),
            content={"error": exc.code, "message": exc.message, "details": exc.details},
        )

    app.include_router(build_router(service))
