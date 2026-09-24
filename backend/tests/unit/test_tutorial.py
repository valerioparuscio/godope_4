"""Tutorial sandbox scenarios (application/tutorial.py, 2026-09-24 pilot)
— each scenario must land the human on exactly the decision_type it's
meant to teach, using the real `legal_actions.py` generator, not a
hand-asserted shortcut."""

import pytest

from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.application.tutorial import TUTORIAL_SCENARIO_IDS, build_tutorial_scenario
from dope_engine.domain.ids import GameId, PlayerId
from dope_engine.rules.setup import create_initial_state

EXPECTED_DECISION_TYPE_BY_SCENARIO = {
    "grit": "choose_grit_action",
    "place_criminal": "place_criminal",
    "move_criminal": "move_criminal",
    "buy_dope": "buy_dope",
    "brawl_card": "play_brawl_card",
}


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def test_expected_decision_types_cover_every_scenario_id() -> None:
    assert set(EXPECTED_DECISION_TYPE_BY_SCENARIO) == set(TUTORIAL_SCENARIO_IDS)


@pytest.mark.parametrize("scenario_id", TUTORIAL_SCENARIO_IDS)
def test_scenario_lands_on_its_own_decision_type(
    game_data, price_tracks, link_extra_action_types, scenario_id
) -> None:
    state, _ = _new_game(game_data)
    build_tutorial_scenario(scenario_id, state, game_data)

    decision = get_legal_decision(
        state,
        PlayerId("player_0"),
        price_tracks,
        link_extra_action_types,
        card_contact_by_id={c.card_id: c.contact_id for c in game_data.customer_cards},
        action_type_by_card_id={c.card_id: c.action_type for c in game_data.customer_cards},
        job_by_id={j.job_id: j for j in game_data.jobs},
        stonk_count_by_card_id={c.card_id: c.stonk_count for c in game_data.customer_cards},
        card_effect_by_id={c.card_id: c.effect for c in game_data.customer_cards},
    )

    assert decision is not None
    assert decision.decision_type == EXPECTED_DECISION_TYPE_BY_SCENARIO[scenario_id]
    assert decision.player_id == "player_0"
    assert len(decision.options) > 0


def test_move_criminal_scenario_offers_exactly_one_movable_pawn(game_data) -> None:
    """Setup gives every player 3 already-placed Criminals — left as-is,
    the decision would offer ~21 options across all 3 pawns at once, too
    busy for a single "click the pawn, then its destination" lesson
    (game designer, 2026-09-24)."""
    state, _ = _new_game(game_data)
    build_tutorial_scenario("move_criminal", state, game_data)

    pawn_ids = {pawn.pawn_id for pawn in state.pawns.values() if pawn.owner_player_id == "player_0"}
    movable_pawn_ids = {
        pid
        for pid in pawn_ids
        if state.board.hoods.get(state.pawns[pid].location.hood_id) is not None
        and pid in state.board.hoods[state.pawns[pid].location.hood_id].criminal_pawn_ids
    }
    assert movable_pawn_ids == {"pawn_player_0_01"}


def test_build_tutorial_scenario_rejects_an_unknown_id(game_data) -> None:
    state, _ = _new_game(game_data)
    with pytest.raises(KeyError):
        build_tutorial_scenario("not_a_real_scenario", state, game_data)
