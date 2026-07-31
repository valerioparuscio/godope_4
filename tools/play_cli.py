"""Minimal textual debug frontend (CLAUDE.md Milestone 1): play one
local game from the terminal, one human seat, three RandomLegalBot
seats, talking to the engine directly (no HTTP round-trip needed for
local debugging).

Usage:
    python tools/play_cli.py [--seed 42] [--human-seat 0]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

from dope_engine.application.command_bus import CommandFailure  # noqa: E402
from dope_engine.application.data_loader import load_game_data  # noqa: E402
from dope_engine.application.game_service import GameService  # noqa: E402
from dope_engine.application.legal_actions import build_command_from_selection  # noqa: E402
from dope_engine.application.views import PlayerGameView  # noqa: E402
from dope_engine.bots.random_legal import RandomLegalBot  # noqa: E402
from dope_engine.domain.decisions import PendingDecision  # noqa: E402
from dope_engine.domain.enums import GameStatus  # noqa: E402
from dope_engine.domain.ids import GameId  # noqa: E402


def _print_view(view: PlayerGameView) -> None:
    print(
        f"\n=== Turn {view.turn_index}/3, Round {view.action_round_index}/3, "
        f"Phase {view.phase.value} ==="
    )
    for p in view.players:
        marker = ">" if p.player_id == view.current_player_id else " "
        print(
            f"{marker} {p.player_id} ({p.controller_type.value}): "
            f"${p.money}, grit left={p.available_grit_values}, hand={p.hand_card_count}"
        )
    print(f"Your hand: {list(view.own_hand_card_ids)}")


def _prompt_selection(decision: PendingDecision) -> tuple[str, ...]:
    print(f"\n{decision.prompt_key}")
    if not decision.options:
        input("(nothing to choose) Press Enter to pass... ")
        return ()

    for i, option in enumerate(decision.options):
        print(f"  [{i}] {option.label_key} {dict(option.payload)}")

    count = decision.min_selections
    while True:
        raw = input(f"Choose {count} option index(es), comma-separated: ").strip()
        try:
            indexes = [int(x) for x in raw.split(",")] if raw else []
        except ValueError:
            print("Not a number, try again.")
            continue
        if len(indexes) != count or any(not (0 <= i < len(decision.options)) for i in indexes):
            print(f"Pick exactly {count} valid index(es).")
            continue
        return tuple(decision.options[i].option_id for i in indexes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--human-seat", type=int, default=0)
    args = parser.parse_args()

    game_data = load_game_data(DATA_DIR)
    service = GameService(game_data, bot_policy=RandomLegalBot())

    result = service.create_game(
        game_id=GameId("cli-game"), seed=args.seed, human_seat=args.human_seat
    )
    result = service.advance(result.state)
    state = result.state

    while state.status != GameStatus.FINISHED:
        decision = state.pending_decision
        assert decision is not None
        view = service.view_for(state, decision.player_id)
        _print_view(view)

        selected_ids = _prompt_selection(decision)
        command = build_command_from_selection(view, decision, selected_ids)
        outcome = service.dispatch(state, command)
        if isinstance(outcome, CommandFailure):
            print(f"Illegal move rejected: {outcome.error.message}")
            continue

        result = service.advance(outcome.state)
        state = result.state

    print("\n=== Game finished ===")
    for p in state.players:
        print(f"{p.player_id}: ${p.money}")


if __name__ == "__main__":
    main()
