"""Loads and validates the versioned data files under `data/` into the
typed definitions from `dope_engine.domain.content`.

This is the one place in the whole engine allowed to touch the
filesystem for game content: the domain package itself must stay free
of filesystem/network/FastAPI imports (CLAUDE.md section 3.3), so
`rules/setup.py` and friends only ever see the `GameData` this module
returns, never a Path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dope_engine.domain.content import (
    BoardDefinition,
    ContactsDefinition,
    DopeTypeDefinition,
    JobDefinition,
    RaidCardDefinition,
    SkillDefinition,
)
from dope_engine.domain.entities import CustomerCardDefinition
from dope_engine.domain.enums import DopeType
from dope_engine.domain.serialization import from_json_dict


@dataclass(frozen=True)
class GameData:
    config: dict[str, Any]
    dope_types: dict[DopeType, DopeTypeDefinition]
    board: BoardDefinition
    contacts: ContactsDefinition
    jobs: tuple[JobDefinition, ...]
    skills: tuple[SkillDefinition, ...]
    raids: tuple[RaidCardDefinition, ...]
    customer_cards: tuple[CustomerCardDefinition, ...]


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_game_data(data_dir: Path) -> GameData:
    config = _read_json(data_dir / "game_config.json")

    dope_types = from_json_dict(
        dict[DopeType, DopeTypeDefinition], _read_json(data_dir / "dope_types.json")
    )
    board = from_json_dict(BoardDefinition, _read_json(data_dir / "board.json"))
    contacts = from_json_dict(ContactsDefinition, _read_json(data_dir / "contacts.json"))
    jobs = tuple(from_json_dict(list[JobDefinition], _read_json(data_dir / "jobs.json")))
    skills = tuple(from_json_dict(list[SkillDefinition], _read_json(data_dir / "skills.json")))
    raids = tuple(from_json_dict(list[RaidCardDefinition], _read_json(data_dir / "raids.json")))

    customer_cards_payload = _read_json(data_dir / "customer_cards.json")
    customer_cards = tuple(
        from_json_dict(list[CustomerCardDefinition], customer_cards_payload["cards"])
    )

    return GameData(
        config=config,
        dope_types=dope_types,
        board=board,
        contacts=contacts,
        jobs=jobs,
        skills=skills,
        raids=raids,
        customer_cards=customer_cards,
    )
