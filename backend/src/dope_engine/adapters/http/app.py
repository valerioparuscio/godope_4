"""Minimal local HTTP adapter (CLAUDE.md section 13): create a game, read
a player's view, submit a command, and let bots/automatic phases advance.

This module is the only place in the backend allowed to import FastAPI;
the domain and application layers never do (section 3.3). Game state is
kept in an in-process dict, which is enough for the single-machine,
no-multiplayer MVP (section 1) — swap in real persistence in
application/save_load.py without touching this file's route shapes.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import fields
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from dope_engine.adapters.http.schemas import (
    AnswerDecisionRequest,
    CommandRequest,
    CommandResultResponse,
    CreateGameRequest,
    CreateGameResponse,
    DecisionOptionResponse,
    DomainErrorResponse,
    FinalScoreBreakdownResponse,
    FinalScoreResponse,
    GameViewResponse,
    LastBrawlOutcomeResponse,
    LastPokerMatchOutcomeResponse,
    LastRaidOutcomeResponse,
    LoadGameRequest,
    LoadGameResponse,
    PendingDecisionResponse,
    PublicHoodResponse,
    PublicJailSlotResponse,
    PublicJobBoardCellResponse,
    PublicJobProgressResponse,
    PublicOfficerResponse,
    PublicPawnResponse,
    PublicPlayerResponse,
    PublicSpotResponse,
    SaveGameResponse,
)
from dope_engine.application.command_bus import CommandFailure, CommandSuccess
from dope_engine.application.data_loader import load_game_data
from dope_engine.application.game_service import GameService
from dope_engine.application.legal_actions import build_command_from_selection
from dope_engine.application.save_load import from_save_dict, to_save_dict
from dope_engine.application.views import PlayerGameView
from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.domain.commands import (
    AssignBrawlGuns,
    BuyDope,
    BuyOfficer,
    ChooseActionType,
    ChooseBrawlLinkEvolution,
    ChooseBrawlLoserReward,
    ChooseBrawlRelocationDestination,
    ChooseCorruptionAction,
    ChooseGritAction,
    ChooseJobReward,
    ChooseMarketingCard,
    ChooseRaidFirstPlayer,
    Command,
    CorruptOfficer,
    DiscardCards,
    EvolveSaleLink,
    LaunchPoker,
    MoveCriminal,
    PassOptionalStep,
    PlaceCriminal,
    PlacePokerBet,
    PlayBrawlCard,
    PlayMarketingCard,
    PlayPokerCard,
    SellDope,
    SpendLinkForExtraAction,
    StainReputationForMoney,
)
from dope_engine.domain.enums import DopeType
from dope_engine.domain.errors import SaveFormatError
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    DecisionId,
    GameId,
    HoodId,
    OfficerId,
    PawnId,
    PlayerId,
)
from dope_engine.domain.state import GameState

_REPO_ROOT = Path(__file__).resolve().parents[5]
DATA_DIR = Path(os.environ.get("DOPE_DATA_DIR", str(_REPO_ROOT / "data")))

app = FastAPI(title="DOPE Engine (dev)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.1.209:8080",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5183",
        "http://localhost:5183",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_game_data = load_game_data(DATA_DIR)
_service = GameService(_game_data, bot_policy=RandomLegalBot())
_games: dict[str, GameState] = {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return value


def _serialize_event(event: DomainEvent) -> dict[str, Any]:
    """Generic dataclass -> JSON dict passthrough (every DomainEvent field
    is a primitive, an ID (a plain str subtype), an Enum, or a simple
    container of those — see domain/events.py). Exposed on
    CommandResultResponse so the frontend can narrate what bots did during
    an advance() cascade instead of just jumping to the final state
    (CLAUDE.md section 9.2: "Gli eventi servono per: animazioni/transizioni
    del frontend... log leggibile", game designer request 2026-08-16)."""
    data = {f.name: _json_safe(getattr(event, f.name)) for f in fields(event)}
    data["event_type"] = type(event).__name__
    return data


def _get_state(game_id: str) -> GameState:
    state = _games.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Unknown game '{game_id}'")
    return state


def _to_view_response(view: PlayerGameView) -> GameViewResponse:
    pending = None
    if view.pending_decision is not None:
        pending = PendingDecisionResponse(
            decision_id=view.pending_decision.decision_id,
            player_id=view.pending_decision.player_id,
            decision_type=view.pending_decision.decision_type,
            prompt_key=view.pending_decision.prompt_key,
            options=[
                DecisionOptionResponse(
                    option_id=o.option_id, label_key=o.label_key, payload=dict(o.payload)
                )
                for o in view.pending_decision.options
            ],
            min_selections=view.pending_decision.min_selections,
            max_selections=view.pending_decision.max_selections,
            can_pass=view.pending_decision.can_pass,
        )

    return GameViewResponse(
        game_id=view.game_id,
        revision=view.revision,
        rules_version=view.rules_version,
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
        current_price_by_dope_type={
            k.value: v for k, v in view.current_price_by_dope_type.items()
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
            )
            for player_id, progress in view.job_progress_by_player.items()
        },
        remaining_skill_count_by_contact={
            k: v for k, v in view.remaining_skill_count_by_contact.items()
        },
        raid_card_id=view.raid_card_id,
        raid_lost_occurrences_count=view.raid_lost_occurrences_count,
        last_raid_outcome=(
            LastRaidOutcomeResponse(
                raid_card_id=view.last_raid_outcome.raid_card_id,
                escaping_team=list(view.last_raid_outcome.escaping_team),
                caught_team=list(view.last_raid_outcome.caught_team),
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
            )
            if view.last_brawl_outcome is not None
            else None
        ),
        last_poker_outcomes=[
            LastPokerMatchOutcomeResponse(
                match_id=o.match_id,
                winner_id=o.winner_id,
                tied_ids=list(o.tied_ids),
                loser_ids=list(o.loser_ids),
                cash_won=o.cash_won,
                jackpot_carried=o.jackpot_carried,
            )
            for o in view.last_poker_outcomes
        ],
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
        poker_launched_card_ids=list(view.poker_launched_card_ids),
    )


def _build_command(req: CommandRequest, game_id: GameId) -> Command:
    player_id = PlayerId(req.player_id)
    expected_revision = req.expected_revision
    decision_id = DecisionId(req.decision_id) if req.decision_id else None

    if req.command_type == "choose_grit_action":
        return ChooseGritAction(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            grit_value=int(req.payload["grit_value"]),
        )
    if req.command_type == "pass_optional_step":
        return PassOptionalStep(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
        )
    if req.command_type == "discard_cards":
        card_ids = tuple(CardId(c) for c in req.payload["card_ids"])
        return DiscardCards(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_ids=card_ids,
        )
    if req.command_type == "choose_action_type":
        return ChooseActionType(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            action_type=str(req.payload["action_type"]),
        )
    if req.command_type == "place_criminal":
        hood_ids = tuple(HoodId(h) for h in req.payload["hood_ids"])
        return PlaceCriminal(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            hood_ids=hood_ids,
        )
    if req.command_type == "move_criminal":
        moves = tuple(
            (
                PawnId(m["pawn_id"]),
                HoodId(m["destination_hood_id"]),
                ContactId(m["deck_contact_id"]) if m.get("deck_contact_id") else None,
            )
            for m in req.payload["moves"]
        )
        return MoveCriminal(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            moves=moves,
        )
    if req.command_type == "buy_dope":
        dope_purchases = tuple(
            (PawnId(p["pawn_id"]), HoodId(p["hood_id"])) for p in req.payload["purchases"]
        )
        return BuyDope(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            purchases=dope_purchases,
        )
    if req.command_type == "sell_dope":
        sales = tuple(
            (PawnId(s["pawn_id"]), DopeType(s["dope_type"])) for s in req.payload["sales"]
        )
        return SellDope(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            sales=sales,
        )
    if req.command_type == "corrupt_officer":
        corruptions = tuple(
            (PawnId(c["pawn_id"]), OfficerId(c["officer_id"])) for c in req.payload["corruptions"]
        )
        return CorruptOfficer(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            corruptions=corruptions,
        )
    if req.command_type == "corruption_action":
        return ChooseCorruptionAction(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            action=str(req.payload["action"]),
            target_id=req.payload.get("target_id"),
        )
    if req.command_type == "buy_officer":
        purchases = tuple(
            (PawnId(p["pawn_id"]), OfficerId(p["officer_id"]), p.get("destination"))
            for p in req.payload["purchases"]
        )
        return BuyOfficer(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            purchases=purchases,
        )
    if req.command_type == "spend_link_for_extra_action":
        return SpendLinkForExtraAction(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            pawn_id=PawnId(req.payload["pawn_id"]),
        )
    if req.command_type == "play_brawl_card":
        card_id = req.payload.get("card_id")
        return PlayBrawlCard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=CardId(card_id) if card_id else None,
        )
    if req.command_type == "assign_brawl_guns":
        return AssignBrawlGuns(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            target_player_id=PlayerId(req.payload["target_player_id"]),
        )
    if req.command_type == "choose_brawl_loser_reward":
        return ChooseBrawlLoserReward(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            loser_player_id=PlayerId(req.payload["loser_player_id"]),
            reward_type=str(req.payload["reward_type"]),
        )
    if req.command_type == "choose_brawl_link_evolution":
        pawn_id = req.payload.get("pawn_id")
        return ChooseBrawlLinkEvolution(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            pawn_id=PawnId(pawn_id) if pawn_id else None,
        )
    if req.command_type == "choose_brawl_relocation_destination":
        hood_id = req.payload.get("hood_id")
        return ChooseBrawlRelocationDestination(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            hood_id=HoodId(hood_id) if hood_id else None,
        )
    if req.command_type == "launch_poker":
        return LaunchPoker(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=CardId(req.payload["card_id"]),
        )
    if req.command_type == "place_poker_bet":
        match_ids = tuple(str(m) for m in req.payload.get("match_ids", []))
        return PlacePokerBet(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            match_ids=match_ids,
        )
    if req.command_type == "play_poker_card":
        return PlayPokerCard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            match_id=str(req.payload["match_id"]),
            card_id=CardId(req.payload["card_id"]),
        )
    if req.command_type == "choose_job_reward":
        contact_id = req.payload.get("contact_id")
        return ChooseJobReward(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            column_index=int(req.payload["column_index"]),
            contact_id=ContactId(contact_id) if contact_id else None,
        )
    if req.command_type == "choose_raid_first_player":
        return ChooseRaidFirstPlayer(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            chosen_first_player_id=PlayerId(req.payload["chosen_first_player_id"]),
        )
    if req.command_type == "stain_reputation_for_money":
        return StainReputationForMoney(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
        )
    if req.command_type == "play_marketing_card":
        allocations = tuple(
            (DopeType(a["dope_type"]), int(a["delta"])) for a in req.payload["allocations"]
        )
        return PlayMarketingCard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=CardId(req.payload["card_id"]),
            allocations=allocations,
        )
    if req.command_type == "choose_marketing_card":
        return ChooseMarketingCard(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_id=CardId(req.payload["card_id"]),
        )
    if req.command_type == "evolve_sale_link":
        return EvolveSaleLink(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            evolve=bool(req.payload["evolve"]),
        )
    raise HTTPException(status_code=400, detail=f"Unknown command_type '{req.command_type}'")


@app.post("/api/v1/games", response_model=CreateGameResponse)
def create_game(req: CreateGameRequest) -> CreateGameResponse:
    game_id = GameId(str(uuid.uuid4()))
    result = _service.create_game(game_id=game_id, seed=req.seed, human_seat=req.human_seat)
    state = result.state
    advance_result = _service.advance(state)
    state = advance_result.state
    _games[game_id] = state
    return CreateGameResponse(game_id=game_id, revision=state.revision, status=state.status.value)


@app.get("/api/v1/games/{game_id}/view", response_model=GameViewResponse)
def get_view(game_id: str, player_id: str) -> GameViewResponse:
    state = _get_state(game_id)
    view = _service.view_for(state, PlayerId(player_id))
    return _to_view_response(view)


@app.post("/api/v1/games/{game_id}/commands", response_model=CommandResultResponse)
def submit_command(game_id: str, req: CommandRequest) -> CommandResultResponse:
    """Dispatch-only (section 13): does *not* run the bot/automatic
    cascade — see /advance for that, a deliberately separate step so a
    client can render the effect of *this* command (e.g. the human's own
    Criminal actually moving) before whatever bots do next, rather than
    both arriving at once with no way to tell which pawn moved because of
    what (game designer, 2026-08-16: "vedo la pedina che si sposta dopo i
    popup delle azioni dei bot" — the human's own move was being held
    back behind the *bots'* narration instead of showing immediately)."""
    state = _get_state(game_id)
    command = _build_command(req, GameId(game_id))

    outcome = _service.dispatch(state, command)
    if isinstance(outcome, CommandFailure):
        return CommandResultResponse(
            ok=False,
            error=DomainErrorResponse(
                code=outcome.error.code,
                message=outcome.error.message,
                details=dict(outcome.error.details),
            ),
        )

    assert isinstance(outcome, CommandSuccess)
    new_state = outcome.state
    _games[game_id] = new_state

    view = _service.view_for(new_state, PlayerId(req.player_id))
    events = [_serialize_event(e) for e in outcome.events]
    return CommandResultResponse(ok=True, view=_to_view_response(view), events=events)


@app.post("/api/v1/games/{game_id}/decisions/answer", response_model=CommandResultResponse)
def answer_decision(game_id: str, req: AnswerDecisionRequest) -> CommandResultResponse:
    """Generic decision-answering endpoint: the client only ever picks
    among `PendingDecision.options` and never constructs a command payload
    itself (CLAUDE.md section 10) — reuses the same
    `build_command_from_selection` that `tools/play_cli.py`'s textual
    debug frontend already relies on, instead of requiring every client
    to know each command_type's exact payload shape like /commands does.

    Dispatch-only, same as /commands above — the client calls /advance
    itself right after to progress bots, separately."""
    state = _get_state(game_id)
    pending = state.pending_decision
    if pending is None or pending.decision_id != req.decision_id:
        raise HTTPException(status_code=409, detail="Decision is no longer pending")

    view = _service.view_for(state, PlayerId(req.player_id))
    try:
        command = build_command_from_selection(view, pending, tuple(req.selected_option_ids))
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown option_id: {exc}") from exc

    outcome = _service.dispatch(state, command)
    if isinstance(outcome, CommandFailure):
        return CommandResultResponse(
            ok=False,
            error=DomainErrorResponse(
                code=outcome.error.code,
                message=outcome.error.message,
                details=dict(outcome.error.details),
            ),
        )

    assert isinstance(outcome, CommandSuccess)
    new_state = outcome.state
    _games[game_id] = new_state

    view = _service.view_for(new_state, PlayerId(req.player_id))
    events = [_serialize_event(e) for e in outcome.events]
    return CommandResultResponse(ok=True, view=_to_view_response(view), events=events)


@app.post("/api/v1/games/{game_id}/advance", response_model=CommandResultResponse)
def advance_game(game_id: str, player_id: str) -> CommandResultResponse:
    state = _get_state(game_id)
    result = _service.advance(state)
    _games[game_id] = result.state
    view = _service.view_for(result.state, PlayerId(player_id))
    events = [_serialize_event(e) for e in result.events]
    return CommandResultResponse(ok=True, view=_to_view_response(view), events=events)


@app.get("/api/v1/games/{game_id}/save", response_model=SaveGameResponse)
def save_game(game_id: str) -> SaveGameResponse:
    state = _get_state(game_id)
    return SaveGameResponse(**to_save_dict(state))


@app.post("/api/v1/games/load", response_model=LoadGameResponse)
def load_game(req: LoadGameRequest) -> LoadGameResponse:
    try:
        state = from_save_dict(
            req.model_dump(), expected_schema_version=_game_data.config["schema_version"]
        )
    except SaveFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _games[state.game_id] = state
    return LoadGameResponse(
        game_id=state.game_id, revision=state.revision, status=state.status.value
    )
