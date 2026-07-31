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
from pathlib import Path

from fastapi import FastAPI, HTTPException

from dope_engine.adapters.http.schemas import (
    CommandRequest,
    CommandResultResponse,
    CreateGameRequest,
    CreateGameResponse,
    DecisionOptionResponse,
    DomainErrorResponse,
    GameViewResponse,
    PendingDecisionResponse,
    PublicPlayerResponse,
)
from dope_engine.application.command_bus import CommandFailure, CommandSuccess
from dope_engine.application.data_loader import load_game_data
from dope_engine.application.game_service import GameService
from dope_engine.application.views import PlayerGameView, build_player_view
from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.domain.commands import ChooseGritAction, Command, DiscardCards, PassOptionalStep
from dope_engine.domain.ids import CardId, DecisionId, GameId, PlayerId
from dope_engine.domain.state import GameState

_REPO_ROOT = Path(__file__).resolve().parents[5]
DATA_DIR = Path(os.environ.get("DOPE_DATA_DIR", str(_REPO_ROOT / "data")))

app = FastAPI(title="DOPE Engine (dev)")

_game_data = load_game_data(DATA_DIR)
_service = GameService(_game_data, bot_policy=RandomLegalBot())
_games: dict[str, GameState] = {}


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
    view = build_player_view(state, PlayerId(player_id))
    return _to_view_response(view)


@app.post("/api/v1/games/{game_id}/commands", response_model=CommandResultResponse)
def submit_command(game_id: str, req: CommandRequest) -> CommandResultResponse:
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
    advance_result = _service.advance(new_state)
    new_state = advance_result.state
    _games[game_id] = new_state

    view = build_player_view(new_state, PlayerId(req.player_id))
    return CommandResultResponse(ok=True, view=_to_view_response(view))


@app.post("/api/v1/games/{game_id}/advance", response_model=GameViewResponse)
def advance_game(game_id: str, player_id: str) -> GameViewResponse:
    state = _get_state(game_id)
    result = _service.advance(state)
    _games[game_id] = result.state
    view = build_player_view(result.state, PlayerId(player_id))
    return _to_view_response(view)
