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
from dope_engine.domain.entities import BaseInventory, LocationType
from dope_engine.domain.enums import (
    ActiveStep,
    ControllerType,
    DopeType,
    GamePhase,
    GameStatus,
    PawnRole,
)
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    GameId,
    HoodId,
    OfficerId,
    PawnId,
    PlayerId,
    SkillId,
    SpotId,
)
from dope_engine.domain.state import GameState, find_player
from dope_engine.rules import prices
from dope_engine.rules.prices import PriceTracks


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
class PublicHoodView:
    hood_id: HoodId
    contact_id: ContactId
    adjacent_hood_ids: tuple[HoodId, ...]
    revealed: bool
    criminal_pawn_ids: tuple[PawnId, ...]
    dope_stack: tuple[DopeType, ...]
    cop_ids: tuple[OfficerId, ...]
    capacity: int


@dataclass(frozen=True)
class PublicSpotView:
    spot_id: SpotId
    contact_id: ContactId
    accepted_dope_type: DopeType
    adjacent_spot_ids: tuple[SpotId, ...]
    sold_dope_tokens: tuple[DopeType, ...]
    fed_ids: tuple[OfficerId, ...]
    capacity: int


@dataclass(frozen=True)
class PublicPawnView:
    pawn_id: PawnId
    owner_player_id: PlayerId
    role: PawnRole
    hood_id: HoodId | None
    contact_id: ContactId | None
    link_level: int | None


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
    hoods: tuple[PublicHoodView, ...]
    spots: tuple[PublicSpotView, ...]
    pawns: tuple[PublicPawnView, ...]
    den_gambler_pawn_ids: tuple[PawnId, ...]
    current_price_by_dope_type: dict[DopeType, int]


def build_player_view(
    state: GameState, viewing_player_id: PlayerId, price_tracks: PriceTracks
) -> PlayerGameView:
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

    hoods = tuple(
        PublicHoodView(
            hood_id=h.hood_id,
            contact_id=h.contact_id,
            adjacent_hood_ids=tuple(h.adjacent_hood_ids),
            revealed=h.revealed,
            criminal_pawn_ids=tuple(h.criminal_pawn_ids),
            dope_stack=tuple(h.dope_stack),
            cop_ids=tuple(h.cop_ids),
            capacity=h.capacity,
        )
        for h in state.board.hoods.values()
    )
    spots = tuple(
        PublicSpotView(
            spot_id=s.spot_id,
            contact_id=s.contact_id,
            accepted_dope_type=s.accepted_dope_type,
            adjacent_spot_ids=tuple(s.adjacent_spot_ids),
            sold_dope_tokens=tuple(s.sold_dope_tokens),
            fed_ids=tuple(s.fed_ids),
            capacity=s.capacity,
        )
        for s in state.board.spots.values()
    )
    pawns = tuple(
        PublicPawnView(
            pawn_id=pawn.pawn_id,
            owner_player_id=pawn.owner_player_id,
            role=pawn.role,
            hood_id=pawn.location.hood_id if pawn.location.type == LocationType.HOOD else None,
            contact_id=pawn.contact_id,
            link_level=pawn.link_level,
        )
        for pawn in state.pawns.values()
    )
    current_price_by_dope_type = {
        dope_type: prices.current_price(state.market, price_tracks, dope_type)
        for dope_type in price_tracks
    }

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
        hoods=hoods,
        spots=spots,
        pawns=pawns,
        den_gambler_pawn_ids=tuple(state.board.den_gambler_pawn_ids),
        current_price_by_dope_type=current_price_by_dope_type,
    )
