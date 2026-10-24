"""A human who stops answering does not stop the table (docs/architecture/GPT_MULTIPLAYER.md
section 47): when the game waits for a seat nobody has heard from for SEAT_AWAY_SECONDS, a bot
plays it until its player is back.

"Heard from" is any request with the seat's token (a browser that is open asks every second or so),
so a player who is only thinking is never replaced.
"""

from __future__ import annotations

from test_multiplayer_persistence import Clock, Table, act, play, start_service

from dope_engine.application.multiplayer.models import SEAT_AWAY_SECONDS, RoomStatus
from dope_engine.application.multiplayer.service import MultiplayerService
from dope_engine.application.multiplayer.store import InMemorySessionStore
from dope_engine.domain.enums import ControllerType


def start_table(game_data, humans: int = 2, store=None):
    clock = Clock()
    service, _ = start_service(game_data, store or InMemorySessionStore(), clock=clock)
    table = Table(service, humans=humans)
    table.start()
    return clock, service, table


def awaiting(service: MultiplayerService, table: Table) -> str | None:
    return service.snapshot(table.game_id, table.token(0)).awaiting_player_id


def drive_to(service: MultiplayerService, table: Table, seat: int) -> None:
    """Plays whoever is awaited, until the game waits for `seat`."""
    for _ in range(800):
        current = awaiting(service, table)
        if current == f"player_{seat}":
            return
        assert current is not None, "the game ended before it waited for that seat"
        act(service, table.game_id, table.token(int(current.split("_")[1])))
    raise AssertionError("the game never waited for that seat")


def segment_types(result) -> list[str]:
    return [batch.segment_type for batch in result.batches]


def player_controller(service: MultiplayerService, table: Table, seat: int) -> ControllerType:
    state = service.registry.game(table.game_id).state
    assert state is not None
    return state.players[seat].controller_type


def test_a_player_who_has_gone_is_replaced_by_a_bot_after_90_seconds(game_data) -> None:
    clock, service, table = start_table(game_data)
    drive_to(service, table, 1)
    revision = service.snapshot(table.game_id, table.token(0)).revision

    clock.advance(SEAT_AWAY_SECONDS + 1)
    seen = service.events_since(table.game_id, table.token(0), revision, include_view=True)

    assert segment_types(seen)[0] == "seat_away"
    assert seen.batches[0].actor_player_id == "player_1" and seen.batches[0].events == ()
    # The bots played the absent seat on, and the game stopped at the next present human.
    assert "bot_segment" in segment_types(seen)
    assert seen.awaiting_player_id == "player_0"
    assert player_controller(service, table, 1) is ControllerType.BOT
    assert service.room_info(table.room_code).seats[1].away
    # Their seat is still theirs: it is not a "left" seat, and nobody else got its token.
    assert not service.room_info(table.room_code).seats[1].left


def test_nothing_happens_before_the_time_is_up(game_data) -> None:
    clock, service, table = start_table(game_data)
    drive_to(service, table, 1)
    revision = service.snapshot(table.game_id, table.token(0)).revision

    clock.advance(SEAT_AWAY_SECONDS - 1)
    early = service.events_since(table.game_id, table.token(0), revision)
    assert early.batches == () and early.awaiting_player_id == "player_1"

    clock.advance(2)
    late = service.events_since(table.game_id, table.token(0), revision)
    assert segment_types(late)[0] == "seat_away"


def test_a_player_who_is_only_thinking_is_never_replaced(game_data) -> None:
    clock, service, table = start_table(game_data)
    drive_to(service, table, 1)

    for _ in range(10):  # five minutes, the player's browser asking every 30 seconds
        clock.advance(30)
        service.snapshot(table.game_id, table.token(1))
        service.snapshot(table.game_id, table.token(0))

    assert awaiting(service, table) == "player_1"
    assert player_controller(service, table, 1) is ControllerType.HUMAN
    assert not service.room_info(table.room_code).seats[1].away


def test_a_request_from_the_player_arriving_first_wins_the_race(game_data) -> None:
    clock, service, table = start_table(game_data)
    drive_to(service, table, 1)

    clock.advance(SEAT_AWAY_SECONDS + 30)
    service.snapshot(table.game_id, table.token(1))  # they were just late: here they are
    service.snapshot(table.game_id, table.token(0))

    assert awaiting(service, table) == "player_1"
    assert not service.room_info(table.room_code).seats[1].away


def test_the_seat_is_given_back_when_its_player_returns_and_the_game_goes_on(game_data) -> None:
    clock, service, table = start_table(game_data)
    drive_to(service, table, 1)
    clock.advance(SEAT_AWAY_SECONDS + 1)
    service.snapshot(table.game_id, table.token(0))  # the table notices: a bot plays seat 1
    assert service.room_info(table.room_code).seats[1].away
    before = service.snapshot(table.game_id, table.token(0)).revision

    back = service.snapshot(table.game_id, table.token(1))  # their browser asks again

    assert not back.me.away
    assert player_controller(service, table, 1) is ControllerType.HUMAN
    others = service.events_since(table.game_id, table.token(0), before)
    assert segment_types(others) == ["seat_returned"]
    assert others.batches[0].actor_player_id == "player_1"
    # Both humans play the game to its end.
    play(service, table.game_id, [c.seat_token for c in table.credentials])
    assert service.snapshot(table.game_id, table.token(0)).status is RoomStatus.FINISHED


def test_two_absent_humans_are_both_replaced_in_one_go(game_data) -> None:
    clock, service, table = start_table(game_data, humans=3)
    drive_to(service, table, 1)

    clock.advance(SEAT_AWAY_SECONDS + 1)
    service.snapshot(table.game_id, table.token(0))

    seats = service.room_info(table.room_code).seats
    assert seats[1].away and seats[2].away and not seats[0].away
    assert awaiting(service, table) == "player_0"


def test_a_present_players_answer_takes_over_the_next_absent_player_at_once(game_data) -> None:
    clock, service, table = start_table(game_data)
    drive_to(service, table, 0)
    clock.advance(SEAT_AWAY_SECONDS + 1)

    outcomes: list[str] = []
    for _ in range(50):
        if awaiting(service, table) != "player_0":
            break
        snapshot = service.snapshot(table.game_id, table.token(0))
        decision = snapshot.view.pending_decision
        assert decision is not None
        from dope_engine.bots.random_legal import RandomLegalBot

        result = service.answer(
            table.game_id,
            table.token(0),
            decision_id=decision.decision_id,
            selected_option_ids=list(RandomLegalBot().select_option_ids(snapshot.view, decision)),
            expected_revision=snapshot.revision,
        )
        outcomes.extend(segment_types(result))
        if "seat_away" in outcomes:
            break

    # Seat 0's own answer response carries the takeover and the bots' play: no poll was needed.
    assert "seat_away" in outcomes
    assert service.room_info(table.room_code).seats[1].away


def test_a_player_who_is_not_awaited_is_left_alone(game_data) -> None:
    clock, service, table = start_table(game_data)
    drive_to(service, table, 0)

    clock.advance(10 * SEAT_AWAY_SECONDS)
    service.snapshot(table.game_id, table.token(0))

    # Seat 1 has been gone for ages, but the table is waiting for seat 0: nothing to take over.
    assert not service.room_info(table.room_code).seats[1].away
    assert player_controller(service, table, 1) is ControllerType.HUMAN


def test_leaving_while_a_bot_plays_the_seat_makes_it_final(game_data) -> None:
    clock, service, table = start_table(game_data)
    drive_to(service, table, 1)
    clock.advance(SEAT_AWAY_SECONDS + 1)
    service.snapshot(table.game_id, table.token(0))

    service.leave(table.room_code, table.token(1))

    seat = service.room_info(table.room_code).seats[1]
    assert seat.left and not seat.away
    assert seat.controller_type is ControllerType.BOT


def test_an_absence_survives_a_restart_and_so_does_the_return(game_data) -> None:
    store = InMemorySessionStore()
    clock, service, table = start_table(game_data, store=store)
    drive_to(service, table, 1)
    clock.advance(SEAT_AWAY_SECONDS + 1)
    service.snapshot(table.game_id, table.token(0))

    restarted, _ = start_service(game_data, store, clock=clock)

    assert restarted.room_info(table.room_code).seats[1].away
    assert restarted.snapshot(table.game_id, table.token(0)).awaiting_player_id == "player_0"
    back = restarted.snapshot(table.game_id, table.token(1))
    assert not back.me.away
    state = restarted.registry.game(table.game_id).state
    assert state is not None and state.players[1].controller_type is ControllerType.HUMAN


def test_after_a_restart_everybody_gets_the_full_time_to_reconnect(game_data) -> None:
    store = InMemorySessionStore()
    clock, service, table = start_table(game_data, store=store)
    drive_to(service, table, 1)

    clock.advance(10 * SEAT_AWAY_SECONDS)  # the server was down a long time
    restarted, _ = start_service(game_data, store, clock=clock)
    restarted.snapshot(table.game_id, table.token(0))
    assert not restarted.room_info(table.room_code).seats[1].away

    clock.advance(SEAT_AWAY_SECONDS + 1)  # and then nobody heard from seat 1 for 90 seconds
    restarted.snapshot(table.game_id, table.token(0))
    assert restarted.room_info(table.room_code).seats[1].away
