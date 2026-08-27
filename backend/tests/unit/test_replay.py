"""Replay (CLAUDE.md §16): reconstruct a game from its initial seed + the
sequence of accepted commands, verified against a live-played game's own
final state — distinct from save_load.py's whole-state snapshot tests."""

import pytest

from dope_engine.application.command_bus import CommandFailure
from dope_engine.application.legal_actions import build_command_from_selection
from dope_engine.application.replay import ReplayReconstructionError, reconstruct_from_replay
from dope_engine.application.views import PlayerGameView
from dope_engine.domain.commands import ChooseGritAction
from dope_engine.domain.decisions import PendingDecision
from dope_engine.domain.enums import GameStatus
from dope_engine.domain.ids import GameId
from dope_engine.domain.serialization import to_json_dict


def _select_first_legal_option_ids(
    decision: PendingDecision, view: PlayerGameView
) -> tuple[str, ...]:
    """Same "first legal option(s), deduped by pawn" pattern as
    test_game_service.py's own helper (duplicated rather than imported —
    every test file in this suite defines its own small game-driving
    helpers instead of cross-importing). Needed because plain "first N"
    slicing can pick the same pawn twice across move_criminal/sell_dope/
    buy_dope/corrupt_officer's own option lists, which the engine rejects
    (duplicate_pawn_in_targets) the same way it would a real bot doing
    the same thing wrong. `buy_dope` also needs a real Covo-room budget
    (2026-08-27: mirrors test_http_app.py's own `_select_options`, added
    here after a Den-move fix elsewhere shifted this suite's RNG-consumed
    path enough to newly hit the gap)."""
    count = decision.max_selections
    dedup_types = ("move_criminal", "sell_dope", "buy_dope", "corrupt_officer")
    if decision.decision_type not in dedup_types:
        return tuple(o.option_id for o in decision.options[:count])

    hood_stock = None
    money = None
    covo_room = None
    if decision.decision_type == "buy_dope":
        hood_stock = {h.hood_id: len(h.dope_stack) for h in view.hoods}
        buyer = next(p for p in view.players if p.player_id == decision.player_id)
        money = buyer.money
        covo_room = {
            dope_type: 3 - amount for dope_type, amount in buyer.base_inventory.dope_counts.items()
        }

    used_officer_ids: set[str] = set()
    chosen: list[str] = []
    used_pawn_ids: set[str] = set()
    for option in decision.options:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        if decision.decision_type == "corrupt_officer":
            officer_id = option.payload["officer_id"]
            if officer_id in used_officer_ids:
                continue
            used_officer_ids.add(officer_id)
        if hood_stock is not None:
            hood_id = option.payload["hood_id"]
            if hood_stock.get(hood_id, 0) <= 0:
                continue
            assert covo_room is not None
            dope_type = option.payload["dope_type"]
            if covo_room.get(dope_type, 3) <= 0:
                continue
            price = option.payload["price"]
            assert money is not None
            if price > money:
                continue
            hood_stock[hood_id] -= 1
            covo_room[dope_type] = covo_room.get(dope_type, 3) - 1
            money -= price
        used_pawn_ids.add(pawn_id)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def test_accepted_command_is_recorded_and_rejected_one_is_not(game_service) -> None:
    result = game_service.create_game(game_id=GameId("g"), seed=1, human_seat=0)
    state = result.state
    decision = state.pending_decision
    assert decision is not None
    player_id = decision.player_id

    good_command = ChooseGritAction(
        game_id=state.game_id,
        player_id=player_id,
        expected_revision=state.revision,
        grit_value=decision.options[0].payload["grit_value"],
    )
    outcome = game_service.dispatch(state, good_command)
    assert not isinstance(outcome, CommandFailure), outcome
    state = outcome.state

    stale_command = ChooseGritAction(
        game_id=state.game_id,
        player_id=player_id,
        expected_revision=state.revision + 999,
        grit_value=1,
    )
    outcome = game_service.dispatch(state, stale_command)
    assert isinstance(outcome, CommandFailure)

    replay = game_service.export_replay(state)
    assert len(replay["commands"]) == 1
    assert replay["commands"][0]["command_type"] == "ChooseGritAction"
    assert replay["seed"] == 1
    assert replay["human_seat"] == 0


def test_export_replay_for_a_fresh_game_has_no_commands(game_service) -> None:
    result = game_service.create_game(game_id=GameId("g"), seed=1, human_seat=0)
    replay = game_service.export_replay(result.state)
    assert replay["commands"] == []


def test_full_game_replay_reconstructs_the_identical_final_state(game_service, game_data) -> None:
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
        option_ids = _select_first_legal_option_ids(decision, view)
        command = build_command_from_selection(view, decision, option_ids)

        outcome = game_service.dispatch(state, command)
        assert not isinstance(outcome, CommandFailure), outcome
        state = outcome.state

        result = game_service.advance(state)
        state = result.state

    assert state.status is GameStatus.FINISHED

    replay = game_service.export_replay(state)
    assert len(replay["commands"]) > 0

    reconstructed = reconstruct_from_replay(game_data, replay)

    assert reconstructed.status is GameStatus.FINISHED
    assert to_json_dict(reconstructed) == to_json_dict(state)


def test_reconstruct_from_replay_rejects_an_unknown_command_type(game_data) -> None:
    replay = {
        "schema_version": 1,
        "rules_version": game_data.config["rules_version"],
        "game_id": "g",
        "seed": 1,
        "human_seat": 0,
        "human_nickname": None,
        "commands": [{"command_type": "NotARealCommand"}],
    }
    with pytest.raises(ReplayReconstructionError, match="NotARealCommand"):
        reconstruct_from_replay(game_data, replay)


def test_reconstruct_from_replay_rejects_a_mismatched_rules_version(game_data) -> None:
    replay = {
        "schema_version": 1,
        "rules_version": "not-the-current-version",
        "game_id": "g",
        "seed": 1,
        "human_seat": 0,
        "human_nickname": None,
        "commands": [],
    }
    with pytest.raises(ReplayReconstructionError, match="rules_version"):
        reconstruct_from_replay(game_data, replay)
