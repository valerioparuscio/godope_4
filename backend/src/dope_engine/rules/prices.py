"""Per-Dope-type price track math (RULES_CANONICAL.md §A3): each type
has its own non-linear track of allowed values; "sale/scende di 1" means
one *step* along that type's track, not one dollar.

Pure functions only — no event construction here (that needs a GameState
and an event-id sequence, which live in rules/economy.py). `price_tracks`
(each type's ordered tuple of allowed values, loaded once from
data/dope_types.json) is threaded in by the caller rather than looked up
here, keeping this module free of any data-loading concerns.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.enums import DopeType
from dope_engine.domain.state import MarketState

PriceTracks = dict[DopeType, tuple[int, ...]]


@dataclass(frozen=True)
class PriceStepResult:
    dope_type: DopeType
    old_index: int
    new_index: int
    market_crashed: bool


def current_price(market: MarketState, price_tracks: PriceTracks, dope_type: DopeType) -> int:
    track = price_tracks[dope_type]
    return track[market.price_index_by_dope_type[dope_type]]


def step_price(
    market: MarketState, price_tracks: PriceTracks, dope_type: DopeType, *, steps: int
) -> PriceStepResult | None:
    """Move `dope_type`'s price by `steps` track positions (positive =
    up, negative = down), clamped to the track's bounds. Returns `None`
    if the clamp meant nothing actually changed; otherwise the result,
    including whether this triggered a full market crash (all 4 types
    now at their max — RULES_CANONICAL.md §A3), which resets every
    type's index to 0.
    """
    track = price_tracks[dope_type]
    old_index = market.price_index_by_dope_type[dope_type]
    new_index = max(0, min(len(track) - 1, old_index + steps))
    if new_index == old_index:
        return None

    market.price_index_by_dope_type[dope_type] = new_index

    crashed = all(
        market.price_index_by_dope_type[dt] == len(price_tracks[dt]) - 1 for dt in price_tracks
    )
    if crashed:
        for dt in price_tracks:
            market.price_index_by_dope_type[dt] = 0

    return PriceStepResult(
        dope_type=dope_type, old_index=old_index, new_index=new_index, market_crashed=crashed
    )
