from dope_engine.application.legal_actions import build_command_from_selection, get_legal_decision
from dope_engine.application.views import build_player_view
from dope_engine.domain.commands import ChooseGritAction, PassOptionalStep
from dope_engine.domain.enums import ActiveStep
from dope_engine.domain.ids import GameId
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def test_no_decision_for_non_current_player(game_data) -> None:
    state, _ = _new_game(game_data)
    other = next(p for p in state.player_order if p != state.current_player_id)

    assert get_legal_decision(state, other) is None


def test_grit_decision_offers_all_three_values(game_data) -> None:
    state, _ = _new_game(game_data)

    decision = get_legal_decision(state, state.current_player_id)

    assert decision is not None
    assert decision.decision_type == "choose_grit_action"
    assert decision.can_pass is False
    assert {o.payload["grit_value"] for o in decision.options} == {1, 2, 3}


def test_build_command_from_selection_for_grit(game_data) -> None:
    state, _ = _new_game(game_data)
    decision = get_legal_decision(state, state.current_player_id)
    view = build_player_view(state, state.current_player_id)

    option = next(o for o in decision.options if o.payload["grit_value"] == 3)
    command = build_command_from_selection(view, decision, (option.option_id,))

    assert isinstance(command, ChooseGritAction)
    assert command.grit_value == 3
    assert command.player_id == state.current_player_id
    assert command.expected_revision == state.revision


def test_main_action_decision_is_pass_only(game_data) -> None:
    state, _ = _new_game(game_data)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    decision = get_legal_decision(state, state.current_player_id)
    view = build_player_view(state, state.current_player_id)

    assert decision is not None
    assert decision.can_pass is True
    assert decision.options == ()

    command = build_command_from_selection(view, decision, ())
    assert isinstance(command, PassOptionalStep)


def test_hand_discard_requires_exact_overflow(game_data) -> None:
    state, _ = _new_game(game_data)
    state.active_step = ActiveStep.WAITING_FOR_HAND_DISCARD
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.hand_card_ids = ["card_001", "card_002", "card_003", "card_004", "card_005", "card_006"]

    decision = get_legal_decision(state, state.current_player_id)

    assert decision is not None
    assert decision.decision_type == "hand_discard"
    assert decision.min_selections == decision.max_selections == 1
    assert len(decision.options) == 6
