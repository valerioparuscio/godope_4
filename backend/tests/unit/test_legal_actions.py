from dope_engine.application.legal_actions import build_command_from_selection, get_legal_decision
from dope_engine.application.views import build_player_view
from dope_engine.domain.commands import (
    BuyDope,
    ChooseActionType,
    ChooseCorruptionAction,
    ChooseGritAction,
    MoveCriminal,
    PassOptionalStep,
    PlaceCriminal,
)
from dope_engine.domain.entities import OfficerLocationType, OfficerState, PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, OfficerType, PawnRole
from dope_engine.domain.ids import GameId, OfficerId
from dope_engine.domain.state import CorruptionProgress
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _enter_main_action(state, grit_value=1):
    """Drive a fresh game to WAITING_FOR_MAIN_ACTION_TARGETS the same way
    turn_flow's ChooseGritAction handler does, so `current_round_grit_value`
    is set exactly as legal_actions.py expects it to be."""
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.available_grit_values.remove(grit_value)
    player.current_round_grit_value = grit_value
    return player


def _decide(state, price_tracks, link_extra_action_types, player_id=None):
    return get_legal_decision(
        state, player_id or state.current_player_id, price_tracks, link_extra_action_types
    )


def test_no_decision_for_non_current_player(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    other = next(p for p in state.player_order if p != state.current_player_id)

    assert _decide(state, price_tracks, link_extra_action_types, other) is None


def test_grit_decision_offers_all_three_values(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION  # skip the §D2 Poker-launch offer

    decision = _decide(state, price_tracks, link_extra_action_types)

    assert decision is not None
    assert decision.decision_type == "choose_grit_action"
    assert decision.can_pass is False
    assert {o.payload["grit_value"] for o in decision.options} == {1, 2, 3}


def test_build_command_from_selection_for_grit(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION  # skip the §D2 Poker-launch offer
    decision = _decide(state, price_tracks, link_extra_action_types)
    view = build_player_view(state, state.current_player_id, price_tracks)

    option = next(o for o in decision.options if o.payload["grit_value"] == 3)
    command = build_command_from_selection(view, decision, (option.option_id,))

    assert isinstance(command, ChooseGritAction)
    assert command.grit_value == 3
    assert command.player_id == state.current_player_id
    assert command.expected_revision == state.revision


def test_choose_action_type_offers_placing_and_moving(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    _enter_main_action(state, grit_value=1)

    decision = _decide(state, price_tracks, link_extra_action_types)

    assert decision is not None
    assert decision.decision_type == "choose_action_type"
    offered = {o.payload["action_type"] for o in decision.options}
    assert ActionType.PLACE_CRIMINAL.value in offered
    assert ActionType.MOVE_CRIMINAL.value in offered
    assert decision.can_pass is False
    assert decision.min_selections == decision.max_selections == 1


def test_choose_action_type_excludes_action_types_already_used_this_turn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, grit_value=1)
    player.action_types_used_this_turn = [ActionType.PLACE_CRIMINAL]

    decision = _decide(state, price_tracks, link_extra_action_types)

    assert decision is not None
    offered = {o.payload["action_type"] for o in decision.options}
    assert ActionType.PLACE_CRIMINAL.value not in offered
    assert ActionType.MOVE_CRIMINAL.value in offered


def test_build_command_from_selection_for_choose_action_type(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    _enter_main_action(state, grit_value=1)
    decision = _decide(state, price_tracks, link_extra_action_types)
    view = build_player_view(state, state.current_player_id, price_tracks)

    option = next(
        o for o in decision.options if o.payload["action_type"] == ActionType.PLACE_CRIMINAL.value
    )
    command = build_command_from_selection(view, decision, (option.option_id,))

    assert isinstance(command, ChooseActionType)
    assert command.action_type == ActionType.PLACE_CRIMINAL.value


def test_place_criminal_targets_allow_up_to_grit_value(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Confirmed by the game designer (2026-08-02): a package never has
    to use its full Grit value — 1 up to `grit_value` targets are legal,
    not only exactly `grit_value`."""
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, grit_value=2)
    player.pending_action_type = ActionType.PLACE_CRIMINAL

    decision = _decide(state, price_tracks, link_extra_action_types)
    view = build_player_view(state, state.current_player_id, price_tracks)

    assert decision is not None
    assert decision.decision_type == "place_criminal"
    assert decision.min_selections == 1
    assert decision.max_selections == 2

    selected = tuple(o.option_id for o in decision.options[:2])
    command = build_command_from_selection(view, decision, selected)
    assert isinstance(command, PlaceCriminal)
    assert len(command.hood_ids) == 2


def test_move_criminal_options_are_per_pawn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, grit_value=1)
    player.pending_action_type = ActionType.MOVE_CRIMINAL

    decision = _decide(state, price_tracks, link_extra_action_types)
    view = build_player_view(state, state.current_player_id, price_tracks)

    assert decision is not None
    assert decision.decision_type == "move_criminal"
    assert decision.min_selections == decision.max_selections == 1
    assert all("pawn_id" in o.payload for o in decision.options)

    command = build_command_from_selection(view, decision, (decision.options[0].option_id,))
    assert isinstance(command, MoveCriminal)
    assert len(command.moves) == 1


def test_move_criminal_never_offers_den_once_player_is_at_the_per_player_cap(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Decision (2026-08-15): the Den's own global capacity (6) is
    irrelevant here — a player already at their individual 2-pawn cap
    must never be offered a Den destination for any of their Criminals,
    even with plenty of global room left."""
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, grit_value=1)
    player.pending_action_type = ActionType.MOVE_CRIMINAL
    for pawn_id in [
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
    ][:2]:
        pawn = state.pawns[pawn_id]
        state.board.hoods[pawn.location.hood_id].criminal_pawn_ids.remove(pawn_id)
        pawn.role = PawnRole.GAMBLER
        pawn.location = PawnLocation.den()
        state.board.den_gambler_pawn_ids.append(pawn_id)

    decision = _decide(state, price_tracks, link_extra_action_types)

    assert decision is not None
    assert decision.decision_type == "move_criminal"
    assert all(o.payload.get("destination_hood_id") != "den" for o in decision.options)


def test_buy_dope_offered_once_criminal_boughtable(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, grit_value=1)
    player.money = 100
    player.pending_action_type = ActionType.BUY_DOPE

    decision = _decide(state, price_tracks, link_extra_action_types)
    view = build_player_view(state, state.current_player_id, price_tracks)

    assert decision is not None
    assert decision.decision_type == "buy_dope"
    assert len(decision.options) >= 1

    command = build_command_from_selection(view, decision, (decision.options[0].option_id,))
    assert isinstance(command, BuyDope)
    assert len(command.purchases) == 1


def test_sell_dope_not_offered_with_empty_base_inventory(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, grit_value=1)
    player.base_inventory.dope_counts = {}

    decision = _decide(state, price_tracks, link_extra_action_types)

    assert decision is not None
    offered = {o.payload["action_type"] for o in decision.options}
    assert ActionType.SELL_DOPE.value not in offered


def test_main_action_decision_is_pass_only_when_nothing_qualifies(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, grit_value=1)
    player.money = 0
    for pawn_id in player.pawn_ids:
        state.pawns[pawn_id].role = PawnRole.RAT
    for hood in state.board.hoods.values():
        hood.criminal_pawn_ids = []

    decision = _decide(state, price_tracks, link_extra_action_types)
    view = build_player_view(state, state.current_player_id, price_tracks)

    assert decision is not None
    assert decision.can_pass is True
    assert decision.options == ()

    command = build_command_from_selection(view, decision, ())
    assert isinstance(command, PassOptionalStep)


def test_hand_discard_requires_exact_overflow(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    state.active_step = ActiveStep.WAITING_FOR_HAND_DISCARD
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.hand_card_ids = ["card_001", "card_002", "card_003", "card_004", "card_005", "card_006"]

    decision = _decide(state, price_tracks, link_extra_action_types)

    assert decision is not None
    assert decision.decision_type == "hand_discard"
    assert decision.min_selections == decision.max_selections == 1
    assert len(decision.options) == 6


def test_corruption_action_offers_pass_alongside_remaining_actions(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Decision (2026-08-15): up to 3 different corruption actions, $1
    each, entirely the player's choice how many — so once at least 1 has
    been taken, "skip" (stop here) must be offered *alongside* whatever
    real actions are still legal, not only once none remain."""
    state, _ = _new_game(game_data)
    player = _enter_main_action(state)
    pawn_id = next(
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
    )
    hood_id = state.pawns[pawn_id].location.hood_id
    state.board.hoods[hood_id].dope_stack = [DopeType.RANA]

    officer_id = OfficerId("officer_test_cop")
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.HOOD,
        hood_id=hood_id,
    )
    state.board.hoods[hood_id].cop_ids.append(officer_id)

    state.active_step = ActiveStep.WAITING_FOR_CORRUPTION_ACTION
    state.pending_corruption = CorruptionProgress(
        player_id=player.player_id,
        corruptor_pawn_id=pawn_id,
        officer_id=officer_id,
        actions_taken=["move"],
    )

    decision = _decide(state, price_tracks, link_extra_action_types)
    view = build_player_view(state, state.current_player_id, price_tracks)

    assert decision is not None
    assert decision.decision_type == "corruption_action"
    # "confiscate" is still legal (Dope in the Hood) — the fix is that
    # stopping is offered *at the same time*, not only once no option is
    # left, so the player genuinely gets to choose to pay for it or not.
    assert len(decision.options) >= 1
    assert decision.can_pass is True
    assert decision.min_selections == 0

    command = build_command_from_selection(view, decision, ())
    assert isinstance(command, ChooseCorruptionAction)
    assert command.action == "skip"
