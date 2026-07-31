from dataclasses import dataclass

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import Command
from dope_engine.domain.ids import GameId
from dope_engine.rules.setup import create_initial_state


@dataclass(frozen=True)
class Ping(Command):
    pass


def _ping_handler(state, command: Ping) -> CommandSuccess:
    state.revision += 1
    state.event_log_cursor += 1
    return CommandSuccess(state=state, events=())


def _state(game_data):
    state, _events = create_initial_state(
        game_data, game_id=GameId("game_bus_test"), seed=1, human_seat=0
    )
    return state


def _ping(state, *, game_id=None, expected_revision=None) -> Ping:
    return Ping(
        game_id=game_id if game_id is not None else state.game_id,
        player_id=state.current_player_id,
        expected_revision=expected_revision if expected_revision is not None else state.revision,
    )


def test_unknown_command_is_rejected(game_data) -> None:
    bus = CommandBus()
    state = _state(game_data)

    outcome = bus.dispatch(state, _ping(state))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "unknown_command"


def test_registered_command_succeeds_and_bumps_revision(game_data) -> None:
    bus = CommandBus()
    bus.register(Ping, _ping_handler)
    state = _state(game_data)
    original_revision = state.revision

    outcome = bus.dispatch(state, _ping(state))

    assert isinstance(outcome, CommandSuccess)
    assert outcome.state.revision == original_revision + 1
    # The caller's original object must be untouched: dispatch worked on a copy.
    assert state.revision == original_revision


def test_revision_mismatch_is_rejected(game_data) -> None:
    bus = CommandBus()
    bus.register(Ping, _ping_handler)
    state = _state(game_data)

    outcome = bus.dispatch(state, _ping(state, expected_revision=state.revision + 1))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "revision_mismatch"


def test_wrong_game_id_is_rejected(game_data) -> None:
    bus = CommandBus()
    bus.register(Ping, _ping_handler)
    state = _state(game_data)

    outcome = bus.dispatch(state, _ping(state, game_id=GameId("some_other_game")))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_game"
