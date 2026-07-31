"""The authoritative GameState tree (CLAUDE.md section 7).

Every nested structure here is a plain (mutable) dataclass, deliberately
not frozen: rule handlers build the next state by deep-copying the
current one (see application/command_bus.py) and mutating the copy, so
a rejected command never leaves partial changes on the original.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dope_engine.domain.decisions import PendingDecision
from dope_engine.domain.entities import (
    BaseInventory,
    DeckState,
    HoodState,
    JailSlot,
    OfficerState,
    PawnState,
    SalesSpotState,
)
from dope_engine.domain.enums import (
    ActiveStep,
    ControllerType,
    DopeType,
    GamePhase,
    GameStatus,
    PokerSymbolColor,
)
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    GameId,
    HoodId,
    JobId,
    OfficerId,
    PawnId,
    PlayerId,
    RaidCardId,
    SkillId,
    SpotId,
    TileId,
)
from dope_engine.domain.rng import RngState


@dataclass
class PlayerState:
    player_id: PlayerId
    seat_index: int
    controller_type: ControllerType
    display_name: str
    money: int
    hand_card_ids: list[CardId] = field(default_factory=list)
    base_inventory: BaseInventory = field(default_factory=BaseInventory)
    pawn_ids: list[PawnId] = field(default_factory=list)
    skill_ids: list[SkillId] = field(default_factory=list)
    available_grit_values: list[int] = field(default_factory=lambda: [1, 2, 3])
    moved_pawn_ids_this_turn: list[PawnId] = field(default_factory=list)
    extra_action_used_this_turn: bool = False
    gamble_cards_played_this_round: int = 0


@dataclass
class BoardState:
    hoods: dict[HoodId, HoodState] = field(default_factory=dict)
    spots: dict[SpotId, SalesSpotState] = field(default_factory=dict)
    officers: dict[OfficerId, OfficerState] = field(default_factory=dict)
    den_gambler_pawn_ids: list[PawnId] = field(default_factory=list)
    # Hidden setup info (RULES_CANONICAL.md §F3): which round tile and
    # Dope type each covered Hood will reveal once a defeated Criminal is
    # sent there. Not exposed to any player-facing GameView until that
    # Hood is actually revealed.
    covered_hood_tile_assignment: dict[HoodId, tuple[TileId, DopeType]] = field(
        default_factory=dict
    )


@dataclass
class MarketState:
    price_index_by_dope_type: dict[DopeType, int] = field(default_factory=dict)
    supply_remaining_by_dope_type: dict[DopeType, int] = field(default_factory=dict)


@dataclass
class JailState:
    slots: list[JailSlot] = field(default_factory=list)


@dataclass
class DecksState:
    customer_decks_by_contact: dict[ContactId, DeckState] = field(default_factory=dict)


@dataclass
class PlayerJobProgress:
    tier_piles: dict[int, list[JobId]] = field(default_factory=dict)
    revealed_job_id_by_tier: dict[int, JobId | None] = field(default_factory=dict)


@dataclass
class JobBoardCell:
    job_id: JobId
    column_index: int
    player_id: PlayerId | None = None
    stained: bool = False


@dataclass
class JobsState:
    progress_by_player: dict[PlayerId, PlayerJobProgress] = field(default_factory=dict)
    board: list[JobBoardCell] = field(default_factory=list)


@dataclass
class RaidsState:
    selected_card_ids: tuple[RaidCardId, ...] = ()
    current_turn_card_id: RaidCardId | None = None
    lost_occurrences_count: int = 0


@dataclass
class PokerMatchState:
    match_id: str
    launched_by_player_id: PlayerId
    gamble_card_id: CardId
    banco_symbols: tuple[PokerSymbolColor, ...]
    bets_by_player_id: dict[PlayerId, int] = field(default_factory=dict)
    jackpot_chips: int = 0


@dataclass
class PokerState:
    matches_this_turn: list[PokerMatchState] = field(default_factory=list)


@dataclass
class GameState:
    schema_version: int
    rules_version: str
    game_id: GameId
    revision: int
    rng_state: RngState
    status: GameStatus
    configuration: dict[str, Any]
    players: list[PlayerState]
    player_order: list[PlayerId]
    first_player_id: PlayerId
    current_player_id: PlayerId
    turn_index: int
    action_round_index: int
    phase: GamePhase
    active_step: ActiveStep
    pawns: dict[PawnId, PawnState]
    board: BoardState
    market: MarketState
    jail: JailState
    decks: DecksState
    jobs: JobsState
    raids: RaidsState
    poker: PokerState
    pending_decision: PendingDecision | None
    event_log_cursor: int
    final_score: dict[str, Any] | None = None


def find_player(state: GameState, player_id: PlayerId) -> PlayerState:
    for player in state.players:
        if player.player_id == player_id:
            return player
    raise KeyError(f"No player '{player_id}' in game '{state.game_id}'.")
