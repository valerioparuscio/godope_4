"""Reconstruct and verify a game from a replay file (CLAUDE.md §16):
initial seed + human seat + the sequence of accepted commands, exported
via `GET /api/v1/games/{game_id}/replay` (or `GameService.export_replay`
directly, e.g. from a test).

Usage:
    python tools/replay_game.py --replay my_game_replay.json
    python tools/replay_game.py --replay my_game_replay.json --compare-save my_game_save.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from dope_engine.application.data_loader import load_game_data  # noqa: E402
from dope_engine.application.replay import (  # noqa: E402
    ReplayReconstructionError,
    reconstruct_from_replay,
)
from dope_engine.application.save_load import load_from_file  # noqa: E402
from dope_engine.domain.serialization import to_json_dict  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, required=True, help="Path to a replay JSON file")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--compare-save",
        type=Path,
        default=None,
        help="Optional: a save file (GET .../save) from the same game, to verify the "
        "reconstructed final state matches exactly",
    )
    args = parser.parse_args()

    data = load_game_data(args.data_dir)
    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    command_count = len(replay["commands"])

    try:
        state = reconstruct_from_replay(data, replay)
    except ReplayReconstructionError as exc:
        print(f"FAILED: {exc}")
        return 1

    print(f"OK: replayed {command_count} command(s).")
    print(f"  revision={state.revision} status={state.status.value}")
    if state.final_score is not None:
        print(f"  winner_ids={state.final_score.winner_ids}")

    if args.compare_save is not None:
        expected_state = load_from_file(
            args.compare_save, expected_schema_version=data.config["schema_version"]
        )
        if to_json_dict(state) == to_json_dict(expected_state):
            print(f"  MATCH: identical to {args.compare_save}.")
        else:
            print(f"  MISMATCH: reconstructed state differs from {args.compare_save}.")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
