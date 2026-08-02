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
    PublicHoodResponse,
    PublicJailSlotResponse,
    PublicOfficerResponse,
    PublicPawnResponse,
    PublicPlayerResponse,
    PublicSpotResponse,
)
from dope_engine.application.command_bus import CommandFailure, CommandSuccess
from dope_engine.application.data_loader import load_game_data
from dope_engine.application.game_service import GameService
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
        pawn_ids = tuple(PawnId(p) for p in req.payload["pawn_ids"])
        return BuyDope(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            pawn_ids=pawn_ids,
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

    view = _service.view_for(new_state, PlayerId(req.player_id))
    return CommandResultResponse(ok=True, view=_to_view_response(view))


@app.post("/api/v1/games/{game_id}/advance", response_model=GameViewResponse)
def advance_game(game_id: str, player_id: str) -> GameViewResponse:
    state = _get_state(game_id)
    result = _service.advance(state)
    _games[game_id] = result.state
    view = _service.view_for(result.state, PlayerId(player_id))
    return _to_view_response(view)
