from dope_engine.domain.enums import DopeType
from dope_engine.domain.state import MarketState
from dope_engine.rules import prices

_TRACKS = {
    DopeType.RANA: (0, 1, 3, 5),
    DopeType.CAMALEONTE: (2, 3, 4, 6, 8),
    DopeType.POLPO: (3, 4, 5, 7, 9, 11),
    DopeType.GUFO: (4, 6, 8, 10, 12, 14),
}


def _market(**index_overrides: int) -> MarketState:
    index = {dt: 0 for dt in _TRACKS}
    index.update(index_overrides)
    return MarketState(price_index_by_dope_type=index, supply_remaining_by_dope_type={})


def test_current_price_reads_track_at_index() -> None:
    market = _market(rana=1)
    assert prices.current_price(market, _TRACKS, DopeType.RANA) == 1


def test_step_price_up_moves_one_position() -> None:
    market = _market(rana=1)
    result = prices.step_price(market, _TRACKS, DopeType.RANA, steps=1)

    assert result is not None
    assert result.old_index == 1
    assert result.new_index == 2
    assert market.price_index_by_dope_type[DopeType.RANA] == 2
    assert result.market_crashed is False


def test_step_price_down_moves_one_position() -> None:
    market = _market(rana=2)
    result = prices.step_price(market, _TRACKS, DopeType.RANA, steps=-1)

    assert result is not None
    assert result.new_index == 1


def test_step_price_clamps_at_top_of_track() -> None:
    market = _market(rana=3)
    result = prices.step_price(market, _TRACKS, DopeType.RANA, steps=5)

    assert result is None
    assert market.price_index_by_dope_type[DopeType.RANA] == 3


def test_step_price_clamps_at_bottom_of_track() -> None:
    market = _market(rana=0)
    result = prices.step_price(market, _TRACKS, DopeType.RANA, steps=-5)

    assert result is None
    assert market.price_index_by_dope_type[DopeType.RANA] == 0


def test_step_price_no_change_returns_none() -> None:
    market = _market(rana=1)
    result = prices.step_price(market, _TRACKS, DopeType.RANA, steps=0)

    assert result is None


def test_market_crash_resets_every_type_to_zero() -> None:
    market = _market(
        rana=2,
        camaleonte=4,
        polpo=5,
        gufo=5,
    )
    result = prices.step_price(market, _TRACKS, DopeType.RANA, steps=1)

    assert result is not None
    assert result.market_crashed is True
    for dope_type in _TRACKS:
        assert market.price_index_by_dope_type[dope_type] == 0


def test_market_no_crash_unless_all_types_at_max() -> None:
    market = _market(rana=2, camaleonte=3, polpo=4, gufo=3)
    result = prices.step_price(market, _TRACKS, DopeType.RANA, steps=1)

    assert result is not None
    assert result.market_crashed is False
    assert market.price_index_by_dope_type[DopeType.GUFO] == 3
