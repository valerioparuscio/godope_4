"""Immutable definitions loaded once from data/*.json (CLAUDE.md section
3.5 — map, decks, Jobs, Raids etc. must be data-driven, never hardcoded).

These are templates, not runtime state: e.g. HoodDefinition never changes
during a game, while the corresponding HoodState (domain/entities.py)
does. application/data_loader.py is the only place allowed to read the
files and construct these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dope_engine.domain.enums import DopeType, PokerSymbolColor
from dope_engine.domain.ids import ContactId, HoodId, JobId, RaidCardId, SkillId, SpotId, TileId


@dataclass(frozen=True)
class DopeTypeDefinition:
    total_supply: int
    price_track: tuple[int, ...]
    initial_price_index: int


@dataclass(frozen=True)
class HoodDefinition:
    hood_id: HoodId
    label: str
    contact_id: ContactId
    revealed: bool
    starting_dope_type: DopeType | None
    adjacent_hood_ids: tuple[HoodId, ...]


@dataclass(frozen=True)
class CoveredHoodTileDefinition:
    tile_id: TileId
    dope_count: int
    adds_cop: bool


@dataclass(frozen=True)
class CoveredHoodTilesDefinition:
    tile_values: tuple[CoveredHoodTileDefinition, ...]
    dope_pool: tuple[DopeType, ...]


@dataclass(frozen=True)
class BoardDefinition:
    hoods: tuple[HoodDefinition, ...]
    covered_hood_tiles: CoveredHoodTilesDefinition


@dataclass(frozen=True)
class ContactDefinition:
    contact_id: ContactId
    background_color: PokerSymbolColor
    boosted_actions: tuple[str, ...]
    link_extra_action_restricted_to: tuple[str, ...]
    note: str | None = None


@dataclass(frozen=True)
class SpotDefinition:
    spot_id: SpotId
    contact_id: ContactId
    accepted_dope_type: DopeType
    adjacent_spot_ids: tuple[SpotId, ...]


@dataclass(frozen=True)
class ContactsDefinition:
    contacts: tuple[ContactDefinition, ...]
    spots: tuple[SpotDefinition, ...]


@dataclass(frozen=True)
class JobDefinition:
    job_id: JobId
    title: str
    tier: int
    contact_ids: tuple[ContactId, ...]
    requirement: dict[str, Any]
    # Per-Job override of `game_config.json`'s own
    # `job_board_column_bonuses` (2026-09-02): column_index -> a
    # `JobBonusType` value, for the rare case a specific Job's row needs
    # a different bonus on one of its columns than every other Job's row
    # does (today, only Job 8's own column 2 — see JobBonusType.
    # MONEY_OR_TWO_CARDS's own docstring). Empty for every other Job.
    column_bonus_overrides: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillDefinition:
    skill_id: SkillId
    contact_id: ContactId
    text: str
    effect: dict[str, Any]


@dataclass(frozen=True)
class RaidCardDefinition:
    raid_card_id: RaidCardId
    escape_criterion: str
    text: str
