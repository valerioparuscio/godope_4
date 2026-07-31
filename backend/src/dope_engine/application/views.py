"""Per-controller `GameView` (CLAUDE.md section 12): humans and bots both
get this instead of the raw GameState, so neither can see hidden
information (currently: other players' hand contents — Rissa covered
cards and future-card peeks are hidden the same way once Milestones 3/4
add them).

Board/market/jail/base inventory are public in the physical game (visible
on the table), so they pass through unredacted.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.decisions import PendingDecision
from dope_engine.domain.entities import BaseInventory
from dope_engine.domain.enums import ActiveStep, ControllerType, GamePhase, GameStatus
from dope_engine.domain.ids import CardId, GameId, PawnId, PlayerId, SkillId
from dope_engine.domain.state import GameState, find_player


@dataclass(frozen=True)
class PublicPlayerView:
    player_id: PlayerId
    seat_index: int
    controller_type: ControllerType
    display_name: str
    money: int
    hand_card_count: int
    base_inventory: BaseInventory
    pawn_ids: tuple[PawnId, ...]
    skill_ids: tuple[SkillId, ...]
    available_grit_values: tuple[int, ...]


@dataclass(frozen=True)
class PlayerGameView:
    game_id: GameId
    revision: int
    rules_version: str
    status: GameStatus
    phase: GamePhase
    active_step: ActiveStep
    turn_index: int
    action_round_index: int
    current_player_id: PlayerId
    first_player_id: PlayerId
    viewing_player_id: PlayerId
    players: tuple[PublicPlayerView, ...]
    own_hand_card_ids: tuple[CardId, ...]
    pending_decision: PendingDecision | None


def build_player_view(state: GameState, viewing_player_id: PlayerId) -> PlayerGameView:
    viewer = find_player(state, viewing_player_id)

    public_players = tuple(
        PublicPlayerView(
            player_id=p.player_id,
            seat_index=p.seat_index,
            controller_type=p.controller_type,
            display_name=p.display_name,
            money=p.money,
            hand_card_count=len(p.hand_card_ids),
            base_inventory=p.base_inventory,
            pawn_ids=tuple(p.pawn_ids),
            skill_ids=tuple(p.skill_ids),
            available_grit_values=tuple(p.available_grit_values),
        )
        for p in state.players
    )

    pending = state.pending_decision
    visible_pending = (
        pending if pending is not None and pending.player_id == viewing_player_id else None
    )

    return PlayerGameView(
        game_id=state.game_id,
        revision=state.revision,
        rules_version=state.rules_version,
        status=state.status,
        phase=state.phase,
        active_step=state.active_step,
        turn_index=state.turn_index,
        action_round_index=state.action_round_index,
        current_player_id=state.current_player_id,
        first_player_id=state.first_player_id,
        viewing_player_id=viewing_player_id,
        players=public_players,
        own_hand_card_ids=tuple(viewer.hand_card_ids),
        pending_decision=visible_pending,
    )
