"""Run many bot-only games end to end and check invariants after every
accepted command (CLAUDE.md section 17.3).

Drives one decision at a time for every seat via RandomLegalBot — including
the human seat, since this tool exists to shake out engine bugs, not to
exercise the human/bot split — so validate_invariants() runs after each
individual command rather than only at advance() boundaries.

Usage:
    python tools/run_full_test_game.py --seeds 1-200
    python tools/run_full_test_game.py --seeds 1-2000 --max-steps 4000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from dope_engine.application.command_bus import CommandFailure  # noqa: E402
from dope_engine.application.data_loader import GameData, load_game_data  # noqa: E402
from dope_engine.application.game_service import GameService  # noqa: E402
from dope_engine.application.save_load import save_to_file  # noqa: E402
from dope_engine.bots.random_legal import RandomLegalBot  # noqa: E402
from dope_engine.domain.enums import GameStatus  # noqa: E402
from dope_engine.domain.errors import InvariantViolation  # noqa: E402
from dope_engine.domain.ids import GameId  # noqa: E402
from dope_engine.domain.invariants import validate_invariants  # noqa: E402
from dope_engine.domain.state import GameState  # noqa: E402


def _parse_seed_range(text: str) -> range:
    if "-" in text:
        start, end = text.split("-", 1)
        return range(int(start), int(end) + 1)
    seed = int(text)
    return range(seed, seed + 1)


def run_one(data: GameData, seed: int, max_steps: int) -> tuple[bool, int, str, GameState]:
    """Returns (ok, steps_taken, failure_description, last_state)."""
    service = GameService(data, bot_policy=RandomLegalBot())
    bot = RandomLegalBot()
    result = service.create_game(game_id=GameId(f"sim_{seed}"), seed=seed, human_seat=0)
    state = result.state
    steps = 0

    try:
        while state.status is not GameStatus.FINISHED and steps < max_steps:
            steps += 1
            decision = state.pending_decision
            if decision is None:
                return False, steps, "no pending_decision but game is not finished", state

            view = service.view_for(state, decision.player_id)
            command = bot.choose(view, decision)
            outcome = service.dispatch(state, command)
            if isinstance(outcome, CommandFailure):
                return False, steps, f"CommandFailure: {outcome.error}", state
            state = outcome.state
            validate_invariants(state)
    except InvariantViolation as exc:
        return False, steps, f"InvariantViolation: {exc}", state
    except Exception as exc:  # noqa: BLE001 — any unexpected engine crash is a real failure
        return False, steps, f"Unexpected {type(exc).__name__}: {exc}", state

    if state.status is not GameStatus.FINISHED:
        return False, steps, f"did not reach FINISHED within {max_steps} steps", state
    return True, steps, "", state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="1-200", help="Seed or seed range, e.g. '1-200'")
    parser.add_argument("--max-steps", type=int, default=4000)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--failures-dir",
        type=Path,
        default=Path("debug_failures"),
        help="Where to dump each failing game's save file, for reproduction",
    )
    args = parser.parse_args()

    data = load_game_data(args.data_dir)
    seeds = _parse_seed_range(args.seeds)

    failures: list[tuple[int, int, str, GameState]] = []
    for seed in seeds:
        ok, steps, description, state = run_one(data, seed, args.max_steps)
        if not ok:
            failures.append((seed, steps, description, state))

    total = len(seeds)
    print(f"Ran {total} game(s), {total - len(failures)} passed, {len(failures)} failed.")
    if failures:
        args.failures_dir.mkdir(parents=True, exist_ok=True)
        for seed, steps, description, state in failures:
            path = args.failures_dir / f"seed_{seed}.json"
            save_to_file(state, path)
            print(f"  seed={seed} steps={steps}: {description}")
            print(f"    -> saved failing state to {path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
