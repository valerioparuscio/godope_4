import json
from dataclasses import dataclass
from enum import StrEnum

from dope_engine.domain.entities import PawnLocation, PawnState
from dope_engine.domain.enums import PawnRole
from dope_engine.domain.ids import GameId, PawnId, PlayerId
from dope_engine.domain.serialization import from_json_dict, to_json_dict


class Color(StrEnum):
    RED = "red"
    BLUE = "blue"


@dataclass(frozen=True)
class Inner:
    color: Color
    values: tuple[int, ...]


@dataclass
class Outer:
    name: str
    inner: Inner
    optional_inner: Inner | None
    by_key: dict[str, Inner]
    tiered: dict[int, list[str]]


def test_round_trip_nested_dataclasses_enums_and_containers() -> None:
    original = Outer(
        name="test",
        inner=Inner(color=Color.RED, values=(1, 2, 3)),
        optional_inner=None,
        by_key={"a": Inner(color=Color.BLUE, values=())},
        tiered={1: ["x", "y"], 2: []},
    )

    payload = to_json_dict(original)
    # Must be plain JSON-safe values (round-trips through json.dumps/loads).
    raw = json.loads(json.dumps(payload))
    rebuilt = from_json_dict(Outer, raw)

    assert rebuilt == original


def test_optional_field_present() -> None:
    original = Outer(
        name="test2",
        inner=Inner(color=Color.BLUE, values=(9,)),
        optional_inner=Inner(color=Color.RED, values=(1,)),
        by_key={},
        tiered={},
    )

    raw = json.loads(json.dumps(to_json_dict(original)))
    rebuilt = from_json_dict(Outer, raw)

    assert rebuilt == original
    assert rebuilt.optional_inner == Inner(color=Color.RED, values=(1,))


def test_pawn_state_round_trip() -> None:
    pawn = PawnState(
        pawn_id=PawnId("pawn_player_0_00"),
        owner_player_id=PlayerId("player_0"),
        role=PawnRole.LINK,
        location=PawnLocation.link(contact_id="artisti"),  # type: ignore[arg-type]
        contact_id="artisti",  # type: ignore[arg-type]
        link_level=2,
    )

    raw = json.loads(json.dumps(to_json_dict(pawn)))
    rebuilt = from_json_dict(PawnState, raw)

    assert rebuilt == pawn
    assert rebuilt.role is PawnRole.LINK
    assert isinstance(rebuilt.location, PawnLocation)


def test_game_state_full_round_trip(game_data) -> None:
    from dope_engine.domain.state import GameState
    from dope_engine.rules.setup import create_initial_state

    state, _events = create_initial_state(
        game_data, game_id=GameId("game_roundtrip"), seed=7, human_seat=0
    )

    raw = json.loads(json.dumps(to_json_dict(state)))
    rebuilt = from_json_dict(GameState, raw)

    assert rebuilt == state
