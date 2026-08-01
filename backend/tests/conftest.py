from pathlib import Path

import pytest

from dope_engine.application.data_loader import GameData, load_game_data
from dope_engine.application.game_service import GameService
from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.domain.ids import ContactId
from dope_engine.rules.prices import PriceTracks

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="session")
def game_data() -> GameData:
    return load_game_data(DATA_DIR)


@pytest.fixture()
def price_tracks(game_data: GameData) -> PriceTracks:
    return {
        dope_type: definition.price_track for dope_type, definition in game_data.dope_types.items()
    }


@pytest.fixture()
def link_extra_action_types(game_data: GameData) -> dict[ContactId, tuple[str, ...]]:
    return {
        contact.contact_id: contact.link_extra_action_restricted_to
        for contact in game_data.contacts.contacts
    }


@pytest.fixture()
def game_service(game_data: GameData) -> GameService:
    return GameService(game_data, bot_policy=RandomLegalBot())
