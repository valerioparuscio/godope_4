from pathlib import Path

import pytest

from dope_engine.application.data_loader import GameData, load_game_data
from dope_engine.application.game_service import GameService
from dope_engine.bots.random_legal import RandomLegalBot

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="session")
def game_data() -> GameData:
    return load_game_data(DATA_DIR)


@pytest.fixture()
def game_service(game_data: GameData) -> GameService:
    return GameService(game_data, bot_policy=RandomLegalBot())
