"""Pydantic I/O schemas for the HTTP adapter (CLAUDE.md section 4: Pydantic
is used only at this transport boundary, never inside the domain).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateGameRequest(BaseModel):
    human_seat: int = 0
    seed: int


class CreateGameResponse(BaseModel):
    game_id: str
    revision: int
    status: str


class CommandRequest(BaseModel):
    command_type: str
    player_id: str
    expected_revision: int
    decision_id: str | None = None
    payload: dict[str, Any] = {}


class DomainErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class DecisionOptionResponse(BaseModel):
    option_id: str
    label_key: str
    payload: dict[str, Any]


class PendingDecisionResponse(BaseModel):
    decision_id: str
    player_id: str
    decision_type: str
    prompt_key: str
    options: list[DecisionOptionResponse]
    min_selections: int
    max_selections: int
    can_pass: bool


class PublicPlayerResponse(BaseModel):
    player_id: str
    seat_index: int
    controller_type: str
    display_name: str
    money: int
    hand_card_count: int
    dope_counts: dict[str, int]
    poker_chip_count: int
    pawn_ids: list[str]
    skill_ids: list[str]
    available_grit_values: list[int]


class GameViewResponse(BaseModel):
    game_id: str
    revision: int
    rules_version: str
    status: str
    phase: str
    active_step: str
    turn_index: int
    action_round_index: int
    current_player_id: str
    first_player_id: str
    viewing_player_id: str
    players: list[PublicPlayerResponse]
    own_hand_card_ids: list[str]
    pending_decision: PendingDecisionResponse | None


class CommandResultResponse(BaseModel):
    ok: bool
    view: GameViewResponse | None = None
    error: DomainErrorResponse | None = None
