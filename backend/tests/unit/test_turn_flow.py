from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import ChooseGritAction, PassOptionalStep
from dope_engine.domain.enums import ActiveStep, GamePhase, GameStatus, PawnRole
from dope_engine.domain.ids import ContactId, GameId
from dope_engine.domain.invariants import validate_invariants
from dope_engine.rules import links
from dope_engine.rules.setup import create_initial_state
from dope_engine.rules.turn_flow import register_handlers


def _bus(game_data):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    register_handlers(bus, card_contact_by_id=card_contact_by_id)
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _grit(state, player_id, value):
    return ChooseGritAction(
        game_id=state.game_id,
        player_id=player_id,
        expected_revision=state.revision,
        grit_value=value,
    )


def _pass(state, player_id):
    return PassOptionalStep(
        game_id=state.game_id, player_id=player_id, expected_revision=state.revision
    )


def test_game_boots_directly_into_action_phase(game_data) -> None:
    state, events = _new_game(game_data)

    assert state.phase is GamePhase.ACTION_PHASE
    # §D2: the Poker-launch offer ("prima" the round's own Grit pick) is
    # checked first, ahead of Grit itself, whenever the player still has
    # any hand card and hasn't exhausted the per-round/per-turn caps —
    # true for every player's very first round.
    assert state.active_step is ActiveStep.WAITING_FOR_POKER_LAUNCH
    assert state.turn_index == 1
    assert state.action_round_index == 1
    assert state.current_player_id == state.first_player_id
    event_types = [type(e).__name__ for e in events]
    assert event_types == ["GameStarted", "RaidRevealed", "TurnStarted"]


def test_choose_grit_action_then_pass_advances_to_next_player(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    first_player = state.current_player_id

    outcome = bus.dispatch(state, _pass(state, first_player))  # decline the Poker-launch offer
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION

    outcome = bus.dispatch(state, _grit(state, first_player, 2))
    assert isinstance(outcome, CommandSuccess)
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player = next(p for p in state.players if p.player_id == first_player)
    assert 2 not in player.available_grit_values

    outcome = bus.dispatch(state, _pass(state, first_player))
    assert isinstance(outcome, CommandSuccess)
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_POKER_LAUNCH
    assert state.current_player_id != first_player


def test_wrong_player_is_rejected(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    other_player = next(p for p in state.player_order if p != state.current_player_id)

    outcome = bus.dispatch(state, _grit(state, other_player, 1))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_player"


def test_unavailable_grit_value_is_rejected(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    outcome = bus.dispatch(state, _pass(state, player_id))  # decline the Poker-launch offer
    state = outcome.state

    outcome = bus.dispatch(state, _grit(state, player_id, 9))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "grit_value_unavailable"


def test_wrong_step_is_rejected(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    outcome = bus.dispatch(state, _pass(state, player_id))  # decline the Poker-launch offer
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION

    outcome = bus.dispatch(state, _pass(state, player_id))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_active_step"


def test_full_game_reaches_finished_deterministically(game_data) -> None:
    def run(seed: int) -> tuple:
        state, _ = _new_game(game_data, seed=seed)
        bus = _bus(game_data)
        steps = 0
        while state.status is not GameStatus.FINISHED and steps < 500:
            steps += 1
            player_id = state.current_player_id
            if state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION:
                player = next(p for p in state.players if p.player_id == player_id)
                command = _grit(state, player_id, player.available_grit_values[0])
            else:
                command = _pass(state, player_id)
            outcome = bus.dispatch(state, command)
            assert isinstance(outcome, CommandSuccess), outcome
            state = outcome.state
            validate_invariants(state)
        return state, steps

    state_a, steps_a = run(seed=42)
    state_b, steps_b = run(seed=42)

    assert state_a.status is GameStatus.FINISHED
    assert state_a.turn_index == 3
    # 3 turns x 4 players x 3 rounds x 3 commands each: decline the
    # Poker-launch offer, grit, decline the post-main offers down to
    # round-end (this bus doesn't register rules/poker.py, so the
    # Poker-launch offer is always declinable and never actually
    # launches anything).
    assert steps_a == 108
    assert steps_a == steps_b
    assert state_a == state_b


def test_next_player_with_unused_link_is_offered_extra_action_before_grit(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    first_player_id = state.current_player_id
    start = state.player_order.index(first_player_id)
    rotation = state.player_order[start:] + state.player_order[:start]
    second_player_id = rotation[1]
    second_player = next(p for p in state.players if p.player_id == second_player_id)
    link_pawn_id = next(
        pid for pid in second_player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    links.insert_link(state, second_player_id, link_pawn_id, ContactId("manager"), 1, [])

    outcome = bus.dispatch(state, _pass(state, first_player_id))  # decline Poker-launch offer
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    outcome = bus.dispatch(state, _grit(state, first_player_id, 1))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    outcome = bus.dispatch(state, _pass(state, first_player_id))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    assert state.current_player_id == second_player_id
    assert state.active_step is ActiveStep.WAITING_FOR_POKER_LAUNCH

    outcome = bus.dispatch(state, _pass(state, second_player_id))  # decline Poker-launch offer
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    outcome = bus.dispatch(state, _pass(state, second_player_id))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION
    new_second_player = next(p for p in state.players if p.player_id == second_player_id)
    assert new_second_player.extra_action_used_this_turn is False
