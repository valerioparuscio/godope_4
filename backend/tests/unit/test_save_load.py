from pathlib import Path

import pytest

from dope_engine.application.save_load import (
    from_save_dict,
    load_from_file,
    save_to_file,
    to_save_dict,
)
from dope_engine.domain.errors import SaveFormatError
from dope_engine.domain.ids import GameId
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=7, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def test_to_save_dict_round_trips_via_from_save_dict(game_data) -> None:
    state, _ = _new_game(game_data)

    data = to_save_dict(state)
    rebuilt = from_save_dict(data, expected_schema_version=state.schema_version)

    assert rebuilt == state


def test_save_dict_carries_the_seed_for_a_future_replay(game_data) -> None:
    state, _ = _new_game(game_data, seed=42)

    data = to_save_dict(state)
    rebuilt = from_save_dict(data, expected_schema_version=state.schema_version)

    assert rebuilt.seed == 42


def test_from_save_dict_rejects_schema_version_mismatch(game_data) -> None:
    state, _ = _new_game(game_data)
    data = to_save_dict(state)

    with pytest.raises(SaveFormatError, match="schema_version"):
        from_save_dict(data, expected_schema_version=state.schema_version + 1)


def test_from_save_dict_rejects_missing_envelope_keys(game_data) -> None:
    with pytest.raises(SaveFormatError, match="schema_version"):
        from_save_dict({"snapshot": {}}, expected_schema_version=1)

    with pytest.raises(SaveFormatError, match="snapshot"):
        from_save_dict({"schema_version": 1}, expected_schema_version=1)


def test_save_and_load_from_file_round_trip(game_data, tmp_path: Path) -> None:
    state, _ = _new_game(game_data)
    path = tmp_path / "save.json"

    save_to_file(state, path)
    rebuilt = load_from_file(path, expected_schema_version=state.schema_version)

    assert rebuilt == state
    assert path.exists()
