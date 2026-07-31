from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.application.views import build_player_view
from dope_engine.domain.ids import GameId
from dope_engine.rules.setup import create_initial_state


def test_view_hides_other_players_hand_contents(game_data, price_tracks) -> None:
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    viewer_id = state.player_order[0]
    other_id = state.player_order[1]
    viewer_state = next(p for p in state.players if p.player_id == viewer_id)
    other_state = next(p for p in state.players if p.player_id == other_id)

    view = build_player_view(state, viewer_id, price_tracks)

    assert view.own_hand_card_ids == tuple(viewer_state.hand_card_ids)
    other_public = next(p for p in view.players if p.player_id == other_id)
    assert not hasattr(other_public, "hand_card_ids")
    assert other_public.hand_card_count == len(other_state.hand_card_ids)


def test_view_only_exposes_pending_decision_to_its_own_player(game_data, price_tracks) -> None:
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)

    state.pending_decision = get_legal_decision(state, state.current_player_id, price_tracks)
    other_id = next(p for p in state.player_order if p != state.current_player_id)

    own_view = build_player_view(state, state.current_player_id, price_tracks)
    other_view = build_player_view(state, other_id, price_tracks)

    assert own_view.pending_decision is not None
    assert other_view.pending_decision is None


def test_view_exposes_current_prices_and_board_state(game_data, price_tracks) -> None:
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)

    view = build_player_view(state, state.current_player_id, price_tracks)

    assert set(view.current_price_by_dope_type) == set(price_tracks)
    assert len(view.hoods) == len(state.board.hoods)
    assert len(view.spots) == len(state.board.spots)
    assert len(view.pawns) == len(state.pawns)
