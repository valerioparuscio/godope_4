from pathlib import Path

import pytest

from dope_engine.application.data_loader import GameData, load_game_data

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="session")
def game_data() -> GameData:
    return load_game_data(DATA_DIR)
