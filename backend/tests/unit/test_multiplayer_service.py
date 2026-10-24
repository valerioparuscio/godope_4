"""Multiplayer service (docs/architecture/GPT_MULTIPLAYER.md): rooms, seat tokens, the server
playing the bots, the event log and what each player may see — all through the use-case API,
no HTTP.
"""

from __future__ import annotations

import json
import threading

import pytest

from dope_engine.adapters.http.serialization import serialize_event, to_view_response
from dope_engine.application.game_service import GameService
from dope_engine.application.multiplayer.models import MultiplayerError, RoomStatus
from dope_engine.application.multiplayer.registry import GameRegistry
from dope_engine.application.multiplayer.service import MultiplayerService, PlayerSnapshot
from dope_engine.bots.random_legal import RandomLegalBot
from dope_engine.domain.enums import ControllerType
from dope_engine.domain.events import GameStarted
from dope_engine.domain.ids import GameId

HUMAN_NAMES = ["Marco", "Luca", "Anna", "Sara"]


@pytest.fixture()
def mp(game_data) -> MultiplayerService:
    game_service = GameService(game_data, bot_policy=RandomLegalBot())
    counter = iter(range(1, 1000))
    return MultiplayerService(
        registry=GameRegistry(),
        service_for_ruleset=lambda ruleset: game_service,
        bot_policy_factory=lambda name, ruleset: RandomLegalBot(),
        rulesets={"standard"},
        bot_policies={"random_legal"},
        seed_factory=lambda: 7,
        game_id_factory=lambda: GameId(f"mp-game-{next(counter)}"),
    )


class Table:
    """A room with `humans` people at it, driven through the service like their clients would."""

    def __init__(self, mp: MultiplayerService, humans: int) -> None:
        self.mp = mp
        host = mp.create_room(
            ruleset="standard", human_seats=humans, bot_policy="random_legal", nickname="Marco"
        )
        self.room_code = host.room_code
        self.credentials = [host]
        for name in HUMAN_NAMES[1:humans]:
            self.credentials.append(mp.join_room(self.room_code, name))
        self.game_id: str = ""

    def start(self) -> None:
        self.mp.start_room(self.room_code, self.credentials[0].seat_token)
        game_id = self.mp.room_info(self.room_code).game_id
        assert game_id is not None
        self.game_id = game_id

    def token(self, seat_index: int) -> str:
        return self.credentials[seat_index].seat_token

    def snapshot(self, seat_index: int) -> PlayerSnapshot:
        return self.mp.snapshot(self.game_id, self.token(seat_index))

    def awaited_seat(self) -> int | None:
        snapshot = self.snapshot(0)
        if snapshot.awaiting_player_id is None:
            return None
        return int(snapshot.awaiting_player_id.split("_")[1])

    def act(self, seat_index: int) -> None:
        """Answers the pending decision of `seat_index` with a legal, deterministic selection."""
        snapshot = self.snapshot(seat_index)
        decision = snapshot.view.pending_decision
        assert decision is not None
        selection = RandomLegalBot().select_option_ids(snapshot.view, decision)
        self.mp.answer(
            self.game_id,
            self.token(seat_index),
            decision_id=decision.decision_id,
            selected_option_ids=list(selection),
            expected_revision=snapshot.revision,
        )

    def submit_twice_at_once(self, seat_index: int) -> list[str]:
        """Two threads send the very same answer at the very same moment; what each one got."""
        snapshot = self.snapshot(seat_index)
        decision = snapshot.view.pending_decision
        assert decision is not None
        selection = list(RandomLegalBot().select_option_ids(snapshot.view, decision))
        barrier = threading.Barrier(2)
        outcomes: list[str] = []

        def submit() -> None:
            barrier.wait()
            try:
                self.mp.answer(
                    self.game_id,
                    self.token(seat_index),
                    decision_id=decision.decision_id,
                    selected_option_ids=selection,
                    expected_revision=snapshot.revision,
                )
                outcomes.append("ok")
            except MultiplayerError as exc:
                outcomes.append(exc.code)

        threads = [threading.Thread(target=submit) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return outcomes

    def play(self, steps: int) -> None:
        """Plays at most `steps` human decisions (fewer if the game ends first)."""
        for _ in range(steps):
            awaited = self.awaited_seat()
            if awaited is None:
                return
            self.act(awaited)

    def play_to_the_end(self, max_steps: int = 1500) -> int:
        steps = 0
        while steps < max_steps:
            awaited = self.awaited_seat()
            if awaited is None:
                return steps
            self.act(awaited)
            steps += 1
        raise AssertionError("the game did not finish")


def error_code(callable_, *args, **kwargs) -> str:
    with pytest.raises(MultiplayerError) as excinfo:
        callable_(*args, **kwargs)
    return excinfo.value.code


# --------------------------------------------------------------------- rooms


def test_create_room_seats_the_host_and_fills_the_rest_with_bots(mp) -> None:
    credentials = mp.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="  Marco  "
    )

    room = mp.room_info(credentials.room_code)
    assert room.status is RoomStatus.LOBBY
    assert credentials.seat_index == 0 and credentials.player_id == "player_0"
    assert [seat.controller_type for seat in room.seats] == [
        ControllerType.HUMAN,
        ControllerType.HUMAN,
        ControllerType.BOT,
        ControllerType.BOT,
    ]
    assert [seat.nickname for seat in room.seats] == ["Marco", None, "Bot 3", "Bot 4"]
    assert [seat.occupied for seat in room.seats] == [True, False, True, True]
    assert room.seats[0].is_host and not room.seats[1].is_host
    assert room.game_id is None


def test_the_raw_seat_token_is_not_kept_anywhere_in_the_registry(mp) -> None:
    credentials = mp.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )
    session = mp.registry.room(credentials.room_code)

    assert credentials.seat_token not in repr(vars(mp.registry))
    assert credentials.seat_token not in repr(session)
    assert credentials.seat_token not in repr(session.seats)
    assert session.seats[0].token_hash is not None
    assert len(credentials.seat_token) >= 40  # 256 random bits


@pytest.mark.parametrize(
    "arguments",
    [
        {"human_seats": 1},
        {"human_seats": 5},
        {"nickname": "   "},
        {"nickname": "x" * 25},
        {"ruleset": "nope"},
        {"bot_policy": "nope"},
    ],
)
def test_create_room_rejects_bad_requests(mp, arguments) -> None:
    request = {
        "ruleset": "standard",
        "human_seats": 2,
        "bot_policy": "random_legal",
        "nickname": "Marco",
        **arguments,
    }

    assert error_code(mp.create_room, **request) == "invalid_request"


def test_joining_fills_the_human_seats_in_order_then_the_room_is_full(mp) -> None:
    host = mp.create_room(
        ruleset="standard", human_seats=3, bot_policy="random_legal", nickname="Marco"
    )
    luca = mp.join_room(host.room_code.lower(), "Luca")  # room codes are case-insensitive
    anna = mp.join_room(host.room_code, "Anna")

    assert (luca.seat_index, anna.seat_index) == (1, 2)
    assert len({host.seat_token, luca.seat_token, anna.seat_token}) == 3
    assert error_code(mp.join_room, host.room_code, "Sara") == "room_full"
    room = mp.room_info(host.room_code)
    assert [seat.nickname for seat in room.seats[:3]] == ["Marco", "Luca", "Anna"]


def test_two_players_cannot_share_a_nickname(mp) -> None:
    host = mp.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )

    assert error_code(mp.join_room, host.room_code, "marco") == "nickname_taken"


def test_joining_an_unknown_room_is_refused(mp) -> None:
    assert error_code(mp.join_room, "ZZZZ", "Luca") == "room_not_found"


def test_only_the_host_can_start_and_only_when_every_human_seat_is_taken(mp) -> None:
    host = mp.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )
    assert error_code(mp.start_room, host.room_code, host.seat_token) == "room_not_ready"

    luca = mp.join_room(host.room_code, "Luca")
    assert error_code(mp.start_room, host.room_code, luca.seat_token) == "forbidden"
    assert error_code(mp.start_room, host.room_code, None) == "invalid_token"

    room = mp.start_room(host.room_code, host.seat_token)
    assert room.status is RoomStatus.RUNNING and room.game_id is not None
    assert error_code(mp.start_room, host.room_code, host.seat_token) == "room_already_started"
    assert error_code(mp.join_room, host.room_code, "Anna") == "room_already_started"


def test_a_token_only_works_for_its_own_room(mp) -> None:
    first = mp.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )
    second = mp.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Zoe"
    )

    assert error_code(mp.start_room, first.room_code, second.seat_token) == "invalid_token"


def test_a_guest_leaving_the_lobby_frees_the_seat_and_the_host_leaving_closes_the_room(mp) -> None:
    host = mp.create_room(
        ruleset="standard", human_seats=2, bot_policy="random_legal", nickname="Marco"
    )
    luca = mp.join_room(host.room_code, "Luca")

    room = mp.leave(host.room_code, luca.seat_token)
    assert room is not None and not room.seats[1].occupied
    assert error_code(mp.start_room, host.room_code, host.seat_token) == "room_not_ready"
    assert mp.join_room(host.room_code, "Anna").seat_index == 1  # the freed seat is taken again
    # The old token is dead.
    assert error_code(mp.leave, host.room_code, luca.seat_token) == "invalid_token"

    assert mp.leave(host.room_code, host.seat_token) is None
    assert error_code(mp.join_room, host.room_code, "Sara") == "room_closed"


# ------------------------------------------------------------------ the game


def test_starting_deals_the_game_and_the_server_plays_the_bots_up_to_a_human(mp) -> None:
    table = Table(mp, humans=2)
    table.start()

    snapshot = table.snapshot(0)
    state = mp.registry.game(table.game_id).state
    assert state is not None
    assert snapshot.status is RoomStatus.RUNNING
    assert [p.controller_type for p in state.players] == [
        ControllerType.HUMAN,
        ControllerType.HUMAN,
        ControllerType.BOT,
        ControllerType.BOT,
    ]
    assert [p.display_name for p in state.players] == ["Marco", "Luca", "Bot 3", "Bot 4"]
    # The game never waits on a bot, and it never waits on nobody.
    awaited = table.awaited_seat()
    assert awaited in (0, 1)
    # Whoever the game waits for is the only one holding a decision.
    other = 1 - (awaited or 0)
    assert table.snapshot(awaited).view.pending_decision is not None
    assert table.snapshot(other).view.pending_decision is None


def test_the_first_event_batch_is_the_start_and_does_not_reveal_the_seed(mp) -> None:
    table = Table(mp, humans=2)
    table.start()

    result = mp.events_since(table.game_id, table.token(0), 0)

    first = result.batches[0]
    assert first.segment_type == "game_start"
    started = [e for e in first.events if isinstance(e, GameStarted)]
    assert len(started) == 1 and started[0].seed == 0
    # The authoritative state still has the real one.
    state = mp.registry.game(table.game_id).state
    assert state is not None and state.seed == 7


def test_game_requests_without_a_valid_seat_token_are_refused(mp) -> None:
    table = Table(mp, humans=2)
    other_room = Table(mp, humans=2)
    other_room.start()
    table.start()

    for token in (None, "", "nonsense", other_room.token(0)):
        assert error_code(mp.snapshot, table.game_id, token) == "invalid_token"
        assert error_code(mp.events_since, table.game_id, token, 0) == "invalid_token"
        assert (
            error_code(
                mp.answer,
                table.game_id,
                token,
                decision_id="x",
                selected_option_ids=[],
                expected_revision=1,
            )
            == "invalid_token"
        )
    assert error_code(mp.snapshot, "no-such-game", table.token(0)) == "invalid_token"


def test_answering_someone_elses_decision_is_refused(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    awaited = table.awaited_seat()
    assert awaited is not None
    intruder = 1 - awaited
    snapshot = table.snapshot(awaited)
    decision = snapshot.view.pending_decision
    assert decision is not None

    code = error_code(
        mp.answer,
        table.game_id,
        table.token(intruder),
        decision_id=decision.decision_id,
        selected_option_ids=[decision.options[0].option_id],
        expected_revision=snapshot.revision,
    )

    assert code == "not_your_turn"
    assert table.snapshot(awaited).revision == snapshot.revision  # nothing happened


def test_a_stale_revision_or_decision_is_refused_and_changes_nothing(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    awaited = table.awaited_seat()
    assert awaited is not None
    snapshot = table.snapshot(awaited)
    decision = snapshot.view.pending_decision
    assert decision is not None
    option = decision.options[0].option_id

    with pytest.raises(MultiplayerError) as stale:
        mp.answer(
            table.game_id,
            table.token(awaited),
            decision_id=decision.decision_id,
            selected_option_ids=[option],
            expected_revision=snapshot.revision - 1,
        )
    assert stale.value.code == "stale_revision"
    assert stale.value.details == {"expected": snapshot.revision, "received": snapshot.revision - 1}
    assert (
        error_code(
            mp.answer,
            table.game_id,
            table.token(awaited),
            decision_id="decision_0",
            selected_option_ids=[option],
            expected_revision=snapshot.revision,
        )
        == "stale_decision"
    )
    assert table.snapshot(awaited).revision == snapshot.revision


def test_an_illegal_selection_is_refused_with_a_typed_error(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    awaited = table.awaited_seat()
    assert awaited is not None
    snapshot = table.snapshot(awaited)
    decision = snapshot.view.pending_decision
    assert decision is not None

    code = error_code(
        mp.answer,
        table.game_id,
        table.token(awaited),
        decision_id=decision.decision_id,
        selected_option_ids=["not-an-option"],
        expected_revision=snapshot.revision,
    )

    assert code == "invalid_decision"
    assert table.snapshot(awaited).revision == snapshot.revision


def test_an_accepted_answer_moves_the_game_on_and_logs_what_happened(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    awaited = table.awaited_seat()
    assert awaited is not None
    before = table.snapshot(awaited).revision
    log_before = len(mp.registry.game(table.game_id).event_log)

    table.act(awaited)

    session = mp.registry.game(table.game_id)
    assert table.snapshot(awaited).revision > before
    new = session.event_log[log_before:]
    assert new[0].segment_type == "human_command"
    assert new[0].actor_player_id == f"player_{awaited}"
    assert all(batch.segment_type == "bot_segment" for batch in new[1:])


def test_polling_for_events_never_moves_the_game(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    session = mp.registry.game(table.game_id)
    state_before, log_before = session.state, len(session.event_log)

    results = [mp.events_since(table.game_id, table.token(1), 0) for _ in range(3)]

    assert session.state is state_before and len(session.event_log) == log_before
    # Asking again from the same revision returns the same thing.
    assert [len(r.batches) for r in results] == [len(results[0].batches)] * 3
    assert mp.events_since(table.game_id, table.token(1), state_before.revision).batches == ()
    assert not results[0].requires_refresh
    assert mp.events_since(table.game_id, table.token(1), 10**6).requires_refresh


def test_the_event_log_of_a_played_game_has_no_gaps_and_no_duplicates(mp) -> None:
    table = Table(mp, humans=3)
    table.start()

    table.play_to_the_end()

    session = mp.registry.game(table.game_id)
    batches = session.event_log
    assert session.status is RoomStatus.FINISHED
    assert [b.index for b in batches] == list(range(len(batches)))
    for earlier, later in zip(batches, batches[1:], strict=False):
        assert later.revision_from == earlier.revision_to
    assert batches[-1].revision_to == session.state.revision


def test_previewing_a_plan_changes_nothing(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    awaited = table.awaited_seat()
    assert awaited is not None
    snapshot = table.snapshot(awaited)
    decision = snapshot.view.pending_decision
    assert decision is not None
    session = mp.registry.game(table.game_id)
    state_before, log_before = session.state, len(session.event_log)

    plan = mp.plan(table.game_id, table.token(awaited), decision.decision_id, [])

    assert plan.view.viewing_player_id == f"player_{awaited}"
    assert session.state is state_before and len(session.event_log) == log_before
    other = 1 - awaited
    assert error_code(mp.plan, table.game_id, table.token(other), decision.decision_id, []) == (
        "not_your_turn"
    )


@pytest.mark.parametrize("humans", [2, 3, 4])
def test_a_full_game_with_several_humans_reaches_the_final_score(mp, humans) -> None:
    table = Table(mp, humans=humans)
    table.start()

    table.play_to_the_end()

    for seat_index in range(humans):
        snapshot = table.snapshot(seat_index)
        assert snapshot.status is RoomStatus.FINISHED
        assert snapshot.view.final_score is not None
        assert snapshot.awaiting_player_id is None
    scores = {table.snapshot(i).view.final_score.winner_ids for i in range(humans)}
    assert len(scores) == 1  # everybody sees the same result
    assert (
        error_code(
            mp.answer,
            table.game_id,
            table.token(0),
            decision_id="x",
            selected_option_ids=[],
            expected_revision=1,
        )
        == "game_finished"
    )


def test_two_simultaneous_submissions_of_the_same_move_let_exactly_one_through(mp) -> None:
    table = Table(mp, humans=2)
    table.start()

    for _ in range(25):
        awaited = table.awaited_seat()
        if awaited is None:
            break
        outcomes = table.submit_twice_at_once(awaited)

        assert outcomes.count("ok") == 1, outcomes
        (other,) = [o for o in outcomes if o != "ok"]
        assert other in {"stale_revision", "stale_decision", "not_your_turn"}

    session = mp.registry.game(table.game_id)
    assert [b.index for b in session.event_log] == list(range(len(session.event_log)))
    for earlier, later in zip(session.event_log, session.event_log[1:], strict=False):
        assert later.revision_from == earlier.revision_to


def test_reading_while_a_move_is_processed_does_not_break_anything(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    stop = threading.Event()
    errors: list[BaseException] = []

    def poll() -> None:
        revision = 0
        while not stop.is_set():
            try:
                result = mp.events_since(table.game_id, table.token(1), revision)
                revision = max(revision, result.current_revision)
                mp.snapshot(table.game_id, table.token(1))
            except BaseException as exc:  # noqa: BLE001 - reported below
                errors.append(exc)
                return

    reader = threading.Thread(target=poll)
    reader.start()
    try:
        table.play_to_the_end()
    finally:
        stop.set()
        reader.join()

    assert errors == []


def test_a_human_leaving_a_running_game_hands_the_seat_to_a_bot(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    session = mp.registry.game(table.game_id)
    revision_before = session.state.revision

    mp.leave(table.room_code, table.token(1))

    assert session.state.revision > revision_before
    assert session.state.players[1].controller_type is ControllerType.BOT
    assert session.seats[1].left
    # Their token is dead...
    assert error_code(mp.snapshot, table.game_id, table.token(1)) == "invalid_token"
    # ...and the remaining human can play the game to the end, with no one else to wait for.
    steps = table.play_to_the_end()
    assert steps > 0 and session.status is RoomStatus.FINISHED
    assert session.event_log[-1].revision_to == session.state.revision


# ---------------------------------------------------------- hidden information


def serialized(view_or_batches) -> str:
    if hasattr(view_or_batches, "model_dump_json"):
        return view_or_batches.model_dump_json()
    return json.dumps([[serialize_event(e) for e in batch.events] for batch in view_or_batches])


def test_nobody_ever_receives_the_identity_of_cards_in_another_players_hand(mp) -> None:
    """Release blocker (section 16): while a whole game is played, no response to a player ever
    names a card that sits in another player's hand at that moment."""
    table = Table(mp, humans=3)
    table.start()
    session = mp.registry.game(table.game_id)
    seen_revision = {seat: 0 for seat in range(3)}
    # A card a player once held is theirs to remember wherever it goes next (a stolen card).
    remembered: dict[int, set[str]] = {seat: set() for seat in range(3)}
    checks = 0

    while True:
        state = session.state
        assert state is not None
        hands = {p.player_id: set(p.hand_card_ids) for p in state.players}
        for seat in range(3):
            me = f"player_{seat}"
            remembered[seat] |= hands[me]
            held_by_others = set().union(*(h for pid, h in hands.items() if pid != me))
            forbidden = held_by_others - remembered[seat]
            snapshot = table.snapshot(seat)
            result = mp.events_since(table.game_id, table.token(seat), seen_revision[seat])
            seen_revision[seat] = result.current_revision
            text = serialized(to_view_response(snapshot.view)) + serialized(result.batches)
            leaked = {card for card in forbidden if card in text}
            assert not leaked, f"{me} was told about {sorted(leaked)} held by someone else"
            assert set(snapshot.view.own_hand_card_ids) == hands[me]
            checks += 1
        awaited = table.awaited_seat()
        if awaited is None:
            break
        table.act(awaited)

    assert checks > 30


def test_the_others_see_that_a_card_was_drawn_but_not_which(mp) -> None:
    table = Table(mp, humans=2)
    table.start()
    table.play(40)  # a few rounds: plenty of draws

    from dope_engine.domain.events import CardDrawn

    for_marco = mp.events_since(table.game_id, table.token(0), 0).batches
    for_luca = mp.events_since(table.game_id, table.token(1), 0).batches
    draws_marco = [e for b in for_marco for e in b.events if isinstance(e, CardDrawn)]
    draws_luca = [e for b in for_luca for e in b.events if isinstance(e, CardDrawn)]

    assert len(draws_marco) == len(draws_luca) > 0
    for seen_by_marco, seen_by_luca in zip(draws_marco, draws_luca, strict=True):
        assert seen_by_marco.player_id == seen_by_luca.player_id
        owner_sees = seen_by_marco if seen_by_marco.player_id == "player_0" else seen_by_luca
        other_sees = seen_by_luca if seen_by_marco.player_id == "player_0" else seen_by_marco
        if seen_by_marco.player_id in ("player_0", "player_1"):
            assert owner_sees.card_id is not None
            assert other_sees.card_id is None
        else:  # a bot's draw: nobody human may know it
            assert seen_by_marco.card_id is None and seen_by_luca.card_id is None


def test_the_order_of_the_unrevealed_jobs_is_not_sent(mp) -> None:
    table = Table(mp, humans=2)
    table.start()

    view = table.snapshot(0).view

    for progress in view.job_progress_by_player.values():
        assert all(not pile for pile in progress.tier_piles.values())
        assert any(job_id is not None for job_id in progress.revealed_job_id_by_tier.values())
