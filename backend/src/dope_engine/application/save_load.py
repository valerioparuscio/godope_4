"""Snapshot save/load (CLAUDE.md section 16): a thin envelope around
`domain/serialization.py`'s already-generic, already-tested
`to_json_dict`/`from_json_dict` — `GameState` round-trips through JSON
perfectly on its own (see `tests/unit/test_serialization.py::
test_game_state_full_round_trip`), so this module's only real job is the
save format's stable envelope (`schema_version`, `rules_version`,
`snapshot`) and file I/O.

`expected_schema_version` is threaded in by the caller (typically
`GameData.config["schema_version"]`, loaded once at process start) rather
than hardcoded here, so this module never needs its own copy of
`data/game_config.json` — consistent with keeping content out of the
engine (CLAUDE.md section 3.5) and with every other schema/rules-version
comparison in this codebase being explicit, not a hidden global.

No migration function exists yet: nothing has ever shipped a save under a
different schema_version, so there is nothing to migrate *from*. When
schema_version first changes, add a migration step here rather than
silently accepting a mismatched snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dope_engine.domain.errors import SaveFormatError
from dope_engine.domain.serialization import from_json_dict, to_json_dict
from dope_engine.domain.state import GameState


def to_save_dict(state: GameState) -> dict[str, Any]:
    return {
        "schema_version": state.schema_version,
        "rules_version": state.rules_version,
        "snapshot": to_json_dict(state),
    }


def from_save_dict(data: dict[str, Any], *, expected_schema_version: int) -> GameState:
    for key in ("schema_version", "snapshot"):
        if key not in data:
            raise SaveFormatError(f"Save data is missing required key '{key}'.")
    actual_version = data["schema_version"]
    if actual_version != expected_schema_version:
        raise SaveFormatError(
            f"Save was written with schema_version {actual_version}, but this engine "
            f"expects {expected_schema_version}. No migration is available yet."
        )
    return from_json_dict(GameState, data["snapshot"])


def save_to_file(state: GameState, path: Path) -> None:
    path.write_text(json.dumps(to_save_dict(state), indent=2), encoding="utf-8")


def load_from_file(path: Path, *, expected_schema_version: int) -> GameState:
    data = json.loads(path.read_text(encoding="utf-8"))
    return from_save_dict(data, expected_schema_version=expected_schema_version)
