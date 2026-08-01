from dope_engine.application.command_bus import CommandFailure
from dope_engine.application.legal_actions import build_command_from_selection
from dope_engine.domain.decisions import PendingDecision
from dope_engine.domain.enums import ControllerType, GameStatus
from dope_engine.domain.ids import GameId
from dope_engine.domain.invariants import validate_invariants


def _select_first_legal_option_ids(decision: PendingDecision) -> tuple[str, ...]:
    """Like "always pick the first option(s)", but deduped by pawn for the
    decision types where a single pawn can appear in more than one option
    (see bots/random_legal.py's docstring for why plain slicing isn't safe
    there). `buy_dope`'s options are already price-sorted ascending by
    legal_actions.py, so plain slicing stays safe/affordable for it."""
    count = decision.max_selections
    if decision.decision_type not in ("move_criminal", "sell_dope"):
        return tuple(o.option_id for o in decision.options[:count])

    chosen: list[str] = []
    used_pawn_ids: set[str] = set()
    for option in decision.options:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        used_pawn_ids.add(pawn_id)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def test_create_game_lands_on_first_players_decision(game_service) -> None:
    result = game_service.create_game(game_id=GameId("g"), seed=1, human_seat=0)

    assert result.state.pending_decision is not None
    assert result.state.pending_decision.player_id == result.state.current_player_id


def test_advance_stops_at_human_turn_and_plays_bots_otherwise(game_service) -> None:
    result = game_service.create_game(game_id=GameId("g"), seed=1, human_seat=0)
    state = result.state

    result = game_service.advance(state)
    state = result.state

    human = next(p for p in state.players if p.controller_type is ControllerType.HUMAN)
    assert state.status is not GameStatus.FINISHED
    assert state.current_player_id == human.player_id
    assert state.pending_decision is not None
    assert state.pending_decision.player_id == human.player_id


def test_full_game_completes_via_service_with_human_picking_first_option(game_service) -> None:
    result = game_service.create_game(game_id=GameId("g"), seed=7, human_seat=2)
    state = result.state
    result = game_service.advance(state)
    state = result.state

    steps = 0
    while state.status is not GameStatus.FINISHED and steps < 200:
        steps += 1
        decision = state.pending_decision
        assert decision is not None
        view = game_service.view_for(state, decision.player_id)
        option_ids = _select_first_legal_option_ids(decision)
        command = build_command_from_selection(view, decision, option_ids)

        outcome = game_service.dispatch(state, command)
        assert not isinstance(outcome, CommandFailure), outcome
        state = outcome.state
        validate_invariants(state)

        result = game_service.advance(state)
        state = result.state

    assert state.status is GameStatus.FINISHED
    assert state.turn_index == 3
    assert state.final_score is not None
    assert len(state.final_score.winner_ids) >= 1


def test_bot_only_game_completes_deterministically(game_data):
    from dope_engine.application.game_service import GameService
    from dope_engine.bots.random_legal import RandomLegalBot

    service = GameService(game_data, bot_policy=RandomLegalBot())
    result = service.create_game(game_id=GameId("g"), seed=99, human_seat=0)
    state = result.state

    # Force every seat to BOT so advance() drives the whole game unattended.
    for player in state.players:
        player.controller_type = ControllerType.BOT

    result = service.advance(state, max_steps=1000)
    state = result.state

    assert state.status is GameStatus.FINISHED
    assert state.turn_index == 3
    assert state.final_score is not None
    assert len(state.final_score.winner_ids) >= 1
