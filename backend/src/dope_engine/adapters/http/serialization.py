"""Domain objects -> the JSON shapes the HTTP adapter sends (events, views, decisions).

Shared by the solo routes (`app.py`) and the multiplayer routes (`multiplayer.py`); no state, no
routing, nothing here decides anything.
"""

from __future__ import annotations

from dataclasses import fields
from enum import Enum
from typing import Any

from dope_engine.adapters.http.schemas import (
    BrawlRewardResponse,
    DecisionOptionResponse,
    FinalScoreBreakdownResponse,
    FinalScoreResponse,
    GameViewResponse,
    LastBrawlOutcomeResponse,
    LastPokerMatchOutcomeResponse,
    LastRaidOutcomeResponse,
    PendingDecisionResponse,
    PublicHoodResponse,
    PublicJailSlotResponse,
    PublicJobBoardCellResponse,
    PublicJobProgressResponse,
    PublicOfficerResponse,
    PublicPawnResponse,
    PublicPlayerResponse,
    PublicSpotResponse,
    RaidStandingsResponse,
)
from dope_engine.application.human_planning import DecisionPlan
from dope_engine.application.views import PlayerGameView
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.events import DomainEvent


def json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    return value


def serialize_event(event: DomainEvent) -> dict[str, Any]:
    """Generic dataclass -> JSON dict passthrough (every DomainEvent field
    is a primitive, an ID (a plain str subtype), an Enum, or a simple
    container of those — see domain/events.py). Exposed on
    CommandResultResponse so the frontend can narrate what bots did during
    an advance() cascade instead of just jumping to the final state
    (CLAUDE.md section 9.2: "Gli eventi servono per: animazioni/transizioni
    del frontend... log leggibile", game designer request 2026-08-16)."""
    data = {f.name: json_safe(getattr(event, f.name)) for f in fields(event)}
    data["event_type"] = type(event).__name__
    return data


def option_to_response(option: DecisionOption) -> DecisionOptionResponse:
    return DecisionOptionResponse(
        option_id=option.option_id, label_key=option.label_key, payload=dict(option.payload)
    )


def decision_to_response(decision: PendingDecision) -> PendingDecisionResponse:
    return PendingDecisionResponse(
        decision_id=decision.decision_id,
        player_id=decision.player_id,
        decision_type=decision.decision_type,
        prompt_key=decision.prompt_key,
        context=dict(decision.context),
        options=[option_to_response(o) for o in decision.options],
        min_selections=decision.min_selections,
        max_selections=decision.max_selections,
        can_pass=decision.can_pass,
    )


def to_view_response(view: PlayerGameView, *, undo_available: bool = False) -> GameViewResponse:
    pending = (
        decision_to_response(view.pending_decision) if view.pending_decision is not None else None
    )

    return GameViewResponse(
        game_id=view.game_id,
        revision=view.revision,
        rules_version=view.rules_version,
        ruleset_id=view.ruleset_id,
        status=view.status.value,
        phase=view.phase.value,
        active_step=view.active_step.value,
        turn_index=view.turn_index,
        action_round_index=view.action_round_index,
        current_player_id=view.current_player_id,
        first_player_id=view.first_player_id,
        viewing_player_id=view.viewing_player_id,
        own_hand_card_ids=list(view.own_hand_card_ids),
        pending_decision=pending,
        players=[
            PublicPlayerResponse(
                player_id=p.player_id,
                seat_index=p.seat_index,
                controller_type=p.controller_type.value,
                display_name=p.display_name,
                money=p.money,
                hand_card_count=p.hand_card_count,
                dope_counts={k.value: v for k, v in p.base_inventory.dope_counts.items()},
                poker_chip_count=p.base_inventory.poker_chip_count,
                pawn_ids=list(p.pawn_ids),
                skill_ids=list(p.skill_ids),
                available_grit_values=list(p.available_grit_values),
            )
            for p in view.players
        ],
        hoods=[
            PublicHoodResponse(
                hood_id=h.hood_id,
                contact_id=h.contact_id,
                adjacent_hood_ids=list(h.adjacent_hood_ids),
                revealed=h.revealed,
                criminal_pawn_ids=list(h.criminal_pawn_ids),
                dope_stack=[d.value for d in h.dope_stack],
                cop_ids=list(h.cop_ids),
                capacity=h.capacity,
            )
            for h in view.hoods
        ],
        spots=[
            PublicSpotResponse(
                spot_id=s.spot_id,
                contact_id=s.contact_id,
                accepted_dope_type=s.accepted_dope_type.value,
                adjacent_spot_ids=list(s.adjacent_spot_ids),
                sold_dope_tokens=[d.value for d in s.sold_dope_tokens],
                fed_ids=list(s.fed_ids),
                capacity=s.capacity,
            )
            for s in view.spots
        ],
        pawns=[
            PublicPawnResponse(
                pawn_id=pawn.pawn_id,
                owner_player_id=pawn.owner_player_id,
                role=pawn.role.value,
                hood_id=pawn.hood_id,
                contact_id=pawn.contact_id,
                link_level=pawn.link_level,
            )
            for pawn in view.pawns
        ],
        den_gambler_pawn_ids=list(view.den_gambler_pawn_ids),
        den_capacity=view.den_capacity,
        den_capacity_per_player=view.den_capacity_per_player,
        current_price_by_dope_type={k.value: v for k, v in view.current_price_by_dope_type.items()},
        supply_remaining_by_dope_type={
            k.value: v for k, v in view.supply_remaining_by_dope_type.items()
        },
        officers=[
            PublicOfficerResponse(
                officer_id=o.officer_id,
                officer_type=o.officer_type.value,
                location_type=o.location_type.value,
                hood_id=o.hood_id,
                spot_id=o.spot_id,
                owner_player_id=o.owner_player_id,
            )
            for o in view.officers
        ],
        jail_slots=[
            PublicJailSlotResponse(
                index=slot.index,
                rat_pawn_id=slot.rat_pawn_id,
                confiscated_dope_type=(
                    slot.confiscated_dope_type.value if slot.confiscated_dope_type else None
                ),
            )
            for slot in view.jail_slots
        ],
        job_board=[
            PublicJobBoardCellResponse(
                job_id=cell.job_id,
                column_index=cell.column_index,
                player_id=cell.player_id,
                stained=cell.stained,
            )
            for cell in view.job_board
        ],
        job_progress_by_player={
            player_id: PublicJobProgressResponse(
                tier_piles={tier: list(pile) for tier, pile in progress.tier_piles.items()},
                revealed_job_id_by_tier=dict(progress.revealed_job_id_by_tier),
                displayed_job_id_by_tier=dict(
                    progress.displayed_job_id_by_tier or progress.revealed_job_id_by_tier
                ),
            )
            for player_id, progress in view.job_progress_by_player.items()
        },
        remaining_skill_count_by_contact={
            k: v for k, v in view.remaining_skill_count_by_contact.items()
        },
        raid_card_id=view.raid_card_id,
        raid_standings=(
            RaidStandingsResponse(
                escape_criterion=view.raid_standings.escape_criterion,
                team_a=list(view.raid_standings.team_a),
                team_b=list(view.raid_standings.team_b),
                total_a=view.raid_standings.total_a,
                total_b=view.raid_standings.total_b,
                leading_team=view.raid_standings.leading_team,
                lower_wins=view.raid_standings.lower_wins,
            )
            if view.raid_standings is not None
            else None
        ),
        raid_lost_occurrences_count=view.raid_lost_occurrences_count,
        raid_replacement_count=view.raid_replacement_count,
        last_raid_outcome=(
            LastRaidOutcomeResponse(
                raid_card_id=view.last_raid_outcome.raid_card_id,
                escaping_team=list(view.last_raid_outcome.escaping_team),
                caught_team=list(view.last_raid_outcome.caught_team),
                escape_criterion=view.last_raid_outcome.escape_criterion,
                escaping_team_total=view.last_raid_outcome.escaping_team_total,
                caught_team_total=view.last_raid_outcome.caught_team_total,
                stain_count_applied={
                    k: v for k, v in view.last_raid_outcome.stain_count_applied.items()
                },
            )
            if view.last_raid_outcome is not None
            else None
        ),
        last_brawl_outcome=(
            LastBrawlOutcomeResponse(
                hood_id=view.last_brawl_outcome.hood_id,
                winner_id=view.last_brawl_outcome.winner_id,
                loser_ids=list(view.last_brawl_outcome.loser_ids),
                force_by_player_id={
                    k: v for k, v in view.last_brawl_outcome.force_by_player_id.items()
                },
                pawn_count_by_player_id={
                    k: v for k, v in view.last_brawl_outcome.pawn_count_by_player_id.items()
                },
                gun_total_by_player_id={
                    k: v for k, v in view.last_brawl_outcome.gun_total_by_player_id.items()
                },
                rewards=[
                    BrawlRewardResponse(
                        loser_id=r.loser_id,
                        stole_card=r.stole_card,
                        money=r.money,
                        poker_chip=r.poker_chip,
                        dope_type=r.dope_type.value if r.dope_type is not None else None,
                    )
                    for r in view.last_brawl_outcome.rewards
                ],
            )
            if view.last_brawl_outcome is not None
            else None
        ),
        last_poker_outcome=(
            LastPokerMatchOutcomeResponse(
                match_id=view.last_poker_outcome.match_id,
                winner_id=view.last_poker_outcome.winner_id,
                tied_ids=list(view.last_poker_outcome.tied_ids),
                loser_ids=list(view.last_poker_outcome.loser_ids),
                cash_won=view.last_poker_outcome.cash_won,
                jackpot_carried=view.last_poker_outcome.jackpot_carried,
                hands_by_player_id={
                    k: [s.value for s in v]
                    for k, v in view.last_poker_outcome.hands_by_player_id.items()
                },
                top_hand_shape=view.last_poker_outcome.top_hand_shape,
                shape_by_player_id={
                    k: v for k, v in view.last_poker_outcome.shape_by_player_id.items()
                },
                arrested_loser_ids=list(view.last_poker_outcome.arrested_loser_ids),
                winner_evolved_to_link=view.last_poker_outcome.winner_evolved_to_link,
            )
            if view.last_poker_outcome is not None
            else None
        ),
        final_score=(
            FinalScoreResponse(
                breakdown_by_player={
                    player_id: FinalScoreBreakdownResponse(
                        money_track_position_points=b.money_track_position_points,
                        clean_reputation_points=b.clean_reputation_points,
                        stained_reputation_points=b.stained_reputation_points,
                        contact_majority_points=b.contact_majority_points,
                        base_chip_points=b.base_chip_points,
                        skill_points=b.skill_points,
                        total_points=b.total_points,
                        tie_break_clean_reputation=b.tie_break_clean_reputation,
                    )
                    for player_id, b in view.final_score.breakdown_by_player.items()
                },
                winner_ids=list(view.final_score.winner_ids),
            )
            if view.final_score is not None
            else None
        ),
        poker_launched_card_id=view.poker_launched_card_id,
        active_brawl_hood_id=view.active_brawl_hood_id,
        active_brawl_participant_ids=list(view.active_brawl_participant_ids),
        active_brawl_resolved=view.active_brawl_resolved,
        undo_available=undo_available,
    )


def plan_to_response(plan: DecisionPlan) -> dict[str, Any]:
    """The `/decisions/plan` payload: the previewed view plus, for the client's action chooser,
    each optional step's view and the action types offered after each Grit value."""
    grit = plan.grit
    return {
        "view": to_view_response(plan.view),
        "prefix": plan.prefix,
        "optional": [
            {"kind": item.kind, "view": to_view_response(item.view), "prefix": list(item.prefix)}
            for item in plan.optional
        ],
        "grit": (
            {
                "decision": (
                    decision_to_response(grit.decision) if grit.decision is not None else None
                ),
                "prefix": list(grit.prefix),
                "action_options": {
                    grit_value: [option_to_response(o) for o in options]
                    for grit_value, options in grit.action_options.items()
                },
            }
            if grit is not None
            else None
        ),
        "selected_grit": plan.selected_grit,
        "selected_action": plan.selected_action,
    }
