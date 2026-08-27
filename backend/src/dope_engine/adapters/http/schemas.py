"""Pydantic I/O schemas for the HTTP adapter (CLAUDE.md section 4: Pydantic
is used only at this transport boundary, never inside the domain).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from dope_engine.bots.policies import BOT_POLICY_BY_NAME


class CreateGameRequest(BaseModel):
    human_seat: int = 0
    seed: int
    nickname: str = Field(min_length=1, max_length=32)
    bot_policy: str = "random_legal"

    @field_validator("nickname")
    @classmethod
    def _nickname_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("nickname must not be blank")
        return stripped

    @field_validator("bot_policy")
    @classmethod
    def _bot_policy_known(cls, value: str) -> str:
        if value not in BOT_POLICY_BY_NAME:
            raise ValueError(f"unknown bot_policy '{value}'")
        return value


class CreateGameResponse(BaseModel):
    game_id: str
    revision: int
    status: str


class SaveGameResponse(BaseModel):
    schema_version: int
    rules_version: str
    snapshot: dict[str, Any]


class LoadGameRequest(BaseModel):
    schema_version: int
    rules_version: str
    snapshot: dict[str, Any]


class LoadGameResponse(BaseModel):
    game_id: str
    revision: int
    status: str


class ReplayResponse(BaseModel):
    schema_version: int
    rules_version: str
    game_id: str
    seed: int
    human_seat: int
    human_nickname: str | None
    commands: list[dict[str, Any]]


class CommandRequest(BaseModel):
    command_type: str
    player_id: str
    expected_revision: int
    decision_id: str | None = None
    payload: dict[str, Any] = {}


class AnswerDecisionRequest(BaseModel):
    player_id: str
    decision_id: str
    selected_option_ids: list[str] = []


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


class PublicHoodResponse(BaseModel):
    hood_id: str
    contact_id: str
    adjacent_hood_ids: list[str]
    revealed: bool
    criminal_pawn_ids: list[str]
    dope_stack: list[str]
    cop_ids: list[str]
    capacity: int


class PublicSpotResponse(BaseModel):
    spot_id: str
    contact_id: str
    accepted_dope_type: str
    adjacent_spot_ids: list[str]
    sold_dope_tokens: list[str]
    fed_ids: list[str]
    capacity: int


class PublicPawnResponse(BaseModel):
    pawn_id: str
    owner_player_id: str
    role: str
    hood_id: str | None
    contact_id: str | None
    link_level: int | None


class PublicOfficerResponse(BaseModel):
    officer_id: str
    officer_type: str
    location_type: str
    hood_id: str | None
    spot_id: str | None
    owner_player_id: str | None


class PublicJailSlotResponse(BaseModel):
    index: int
    rat_pawn_id: str | None
    confiscated_dope_type: str | None


class PublicJobBoardCellResponse(BaseModel):
    job_id: str
    column_index: int
    player_id: str | None
    stained: bool


class PublicJobProgressResponse(BaseModel):
    tier_piles: dict[int, list[str]]
    revealed_job_id_by_tier: dict[int, str | None]


class FinalScoreBreakdownResponse(BaseModel):
    money_track_position_points: int
    clean_reputation_points: int
    stained_reputation_points: int
    contact_majority_points: int
    base_chip_points: int
    skill_points: int
    total_points: int
    tie_break_clean_reputation: int


class FinalScoreResponse(BaseModel):
    breakdown_by_player: dict[str, FinalScoreBreakdownResponse]
    winner_ids: list[str]


class LastRaidOutcomeResponse(BaseModel):
    raid_card_id: str
    escaping_team: list[str]
    caught_team: list[str]
    escape_criterion: str
    escaping_team_total: int
    caught_team_total: int
    stain_count_applied: dict[str, int]


class LastBrawlOutcomeResponse(BaseModel):
    hood_id: str
    winner_id: str | None
    loser_ids: list[str]
    force_by_player_id: dict[str, int]
    pawn_count_by_player_id: dict[str, int]
    gun_total_by_player_id: dict[str, int]


class LastPokerMatchOutcomeResponse(BaseModel):
    match_id: str
    winner_id: str | None
    tied_ids: list[str]
    loser_ids: list[str]
    cash_won: int
    jackpot_carried: int
    hands_by_player_id: dict[str, list[str]]
    top_hand_shape: str | None
    arrested_loser_ids: list[str]
    winner_evolved_to_link: bool


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
    hoods: list[PublicHoodResponse]
    spots: list[PublicSpotResponse]
    pawns: list[PublicPawnResponse]
    den_gambler_pawn_ids: list[str]
    den_capacity: int
    den_capacity_per_player: int
    current_price_by_dope_type: dict[str, int]
    supply_remaining_by_dope_type: dict[str, int]
    officers: list[PublicOfficerResponse]
    jail_slots: list[PublicJailSlotResponse]
    job_board: list[PublicJobBoardCellResponse]
    job_progress_by_player: dict[str, PublicJobProgressResponse]
    remaining_skill_count_by_contact: dict[str, int]
    raid_card_id: str | None
    raid_lost_occurrences_count: int
    last_raid_outcome: LastRaidOutcomeResponse | None
    last_brawl_outcome: LastBrawlOutcomeResponse | None
    last_poker_outcomes: list[LastPokerMatchOutcomeResponse]
    final_score: FinalScoreResponse | None
    poker_launched_card_ids: list[str]
    undo_available: bool


class CommandResultResponse(BaseModel):
    ok: bool
    view: GameViewResponse | None = None
    error: DomainErrorResponse | None = None
    # Every domain event produced by this command *and* the bot/automatic
    # cascade advance() ran afterward, in order — a generic
    # {event_type, ...fields} dict per event (app.py's _serialize_event),
    # not a typed union, since the frontend only needs a curated subset of
    # event types to narrate what bots did (game designer, 2026-08-16).
    events: list[dict[str, Any]] = []
