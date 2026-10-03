"""Tutorial sandbox scenarios (application/tutorial.py, 2026-09-24 pilot)
— each scenario must land the human on exactly the decision_type it's
meant to teach, using the real `legal_actions.py` generator, not a
hand-asserted shortcut."""

import pytest

from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.application.tutorial import (
    TUTORIAL_SCENARIO_IDS,
    build_tutorial_scenario,
    prepare_tutorial_state,
)
from dope_engine.domain.ids import GameId, PlayerId
from dope_engine.rules.setup import create_initial_state

EXPECTED_DECISION_TYPE_BY_SCENARIO = {
    "intro": "choose_grit_action",
    "first_player_raid": "choose_raid_first_player",
    "goal": "choose_grit_action",
    "job_reward": "buy_officer",
    "criminal_states": "choose_grit_action",
    "grit": "choose_grit_action",
    "place_criminal": "place_criminal",
    "move_criminal": "move_criminal",
    "buy_dope": "buy_dope",
    "sell_dope": "sell_dope",
    "corrupt_officer": "corrupt_officer",
    "buy_officer": "buy_officer",
    "spend_link": "spend_link_for_extra_action",
    "brawl_trigger": "play_brawl_card",
    "jail_near_full": "choose_grit_action",
    "jail_evasion": "choose_grit_action",
    "poker": "place_poker_bet",
    "hand_discard": "hand_discard",
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
    prepare_tutorial_state(state)
    build_tutorial_scenario("move_criminal", state, game_data)

    pawn_ids = {pawn.pawn_id for pawn in state.pawns.values() if pawn.owner_player_id == "player_0"}
    movable_pawn_ids = {
        pid
        for pid in pawn_ids
        if state.board.hoods.get(state.pawns[pid].location.hood_id) is not None
        and pid in state.board.hoods[state.pawns[pid].location.hood_id].criminal_pawn_ids
    }
    assert movable_pawn_ids == {"pawn_player_0_01"}


def test_brawl_scenario_fills_the_hood_with_exactly_the_trigger_count(game_data) -> None:
    """The board has to actually *show* the situation the card describes
    (game designer, 2026-09-24: "non c'e' un quartiere effettivamente con
    5 pedine, di cui almeno una rossa") — setup already scatters a few
    Criminals into hood_q1, so the builder clears it before refilling."""
    state, _ = _new_game(game_data)
    build_tutorial_scenario("brawl_trigger", state, game_data)

    hood = state.board.hoods["hood_q1"]
    owners = [state.pawns[pid].owner_player_id for pid in hood.criminal_pawn_ids]
    assert len(hood.criminal_pawn_ids) == state.configuration["brawl_trigger_criminal_count"]
    assert "player_0" in owners
    assert state.pending_brawl is not None
    assert state.pending_brawl.hood_id == "hood_q1"
    # Every participant must really stand there, or the Rissa's own force
    # calculation would count presence the board doesn't show.
    assert set(state.pending_brawl.participants) <= set(owners)


def test_build_tutorial_scenario_rejects_an_unknown_id(game_data) -> None:
    state, _ = _new_game(game_data)
    with pytest.raises(KeyError):
        build_tutorial_scenario("not_a_real_scenario", state, game_data)


def test_evasion_lesson_shows_empty_jail_and_triggering_politici_link(game_data) -> None:
    from dope_engine.domain.enums import PawnRole

    state, _ = _new_game(game_data)
    build_tutorial_scenario("jail_evasion", state, game_data)
    assert all(slot.rat_pawn_id is None for slot in state.jail.slots)
    assert any(
        pawn.owner_player_id == "player_0"
        and pawn.role == PawnRole.LINK
        and pawn.contact_id == "politici"
        and pawn.link_level == 1
        for pawn in state.pawns.values()
    )
    assert not any(pawn.role == PawnRole.RAT for pawn in state.pawns.values())


def test_poker_lesson_can_bet_reveal_and_resolve() -> None:
    from dope_engine.adapters.http.app import _service
    from dope_engine.application.command_bus import CommandSuccess
    from dope_engine.application.legal_actions import build_command_from_selection

    state = _service.create_tutorial_game(game_id=GameId("t_poker"), scenario_id="poker").state
    for expected in ("place_poker_bet", "play_poker_card"):
        decision = state.pending_decision
        assert decision is not None and decision.decision_type == expected
        view = _service.view_for(state, PlayerId("player_0"))
        result = _service.dispatch(
            state, build_command_from_selection(view, decision, (decision.options[0].option_id,))
        )
        assert isinstance(result, CommandSuccess)
        state = result.state
        state = _service.advance(state).state
    assert state.poker.last_outcome is not None
    assert "player_0" in state.poker.last_outcome.hands_by_player_id


def test_job_reward_scenario_completes_a_job_and_offers_the_rep_grid(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Buying the Cop must really complete job_02 through the engine's own
    post-command Job check, landing on the 4-column REP reward choice."""
    from dope_engine.adapters.http.app import _service
    from dope_engine.application.legal_actions import build_command_from_selection

    result = _service.create_tutorial_game(game_id=GameId("t_job"), scenario_id="job_reward")
    state = result.state
    decision = state.pending_decision
    view = _service.view_for(state, PlayerId("player_0"))
    state = _service.dispatch(
        state, build_command_from_selection(view, decision, (decision.options[0].option_id,))
    ).state

    assert state.pending_decision is not None
    assert state.pending_decision.decision_type == "choose_job_reward"
    assert {o.payload["column_index"] for o in state.pending_decision.options} == {0, 1, 2, 3}


# The order `frontend/src/tutorial/scenarios.ts` applies its stages in — one
# continuous game, each lesson patched over whatever the previous left.
CONTINUOUS_STAGE_ORDER = (
    ("intro", "choose_grit_action"),
    ("grit", "choose_grit_action"),
    ("place_criminal", "place_criminal"),
    ("move_criminal", "move_criminal"),
    ("buy_dope", "buy_dope"),
    ("sell_dope", "sell_dope"),
    ("corrupt_officer", "corrupt_officer"),
    ("job_reward", "buy_officer"),
    ("first_player_raid", "choose_raid_first_player"),
    ("criminal_states", "choose_grit_action"),
    ("spend_link", "spend_link_for_extra_action"),
    ("brawl_trigger", "play_brawl_card"),
    ("jail_near_full", "choose_grit_action"),
    ("jail_evasion", "choose_grit_action"),
    ("poker", "place_poker_bet"),
    ("hand_discard", "hand_discard"),
)


def test_every_stage_runs_on_top_of_the_previous_in_one_game() -> None:
    from dope_engine.adapters.http.app import _service
    from dope_engine.domain.invariants import validate_invariants

    first, expected = CONTINUOUS_STAGE_ORDER[0]
    state = _service.create_tutorial_game(game_id=GameId("t_one_game"), scenario_id=first).state
    pawn_ids_at_start = set(state.pawns)
    assert state.pending_decision.decision_type == expected
    for scenario_id, expected in CONTINUOUS_STAGE_ORDER[1:]:
        revision = state.revision
        state = _service.apply_tutorial_stage(state, scenario_id)
        assert state.revision == revision + 1
        assert state.pending_decision is not None, scenario_id
        assert state.pending_decision.decision_type == expected, scenario_id
        assert state.pending_decision.player_id == "player_0", scenario_id
        assert set(state.pawns) == pawn_ids_at_start
        validate_invariants(state)


def test_stages_do_not_move_the_board_unless_the_lesson_needs_it() -> None:
    """Moving from the Grit lesson to the Place lesson must leave every
    pawn exactly where it was — no pawns re-entering between cards."""
    from dope_engine.adapters.http.app import _service

    state = _service.create_tutorial_game(game_id=GameId("t_still"), scenario_id="grit").state
    before = {pid: (p.role, p.location) for pid, p in state.pawns.items()}
    state = _service.apply_tutorial_stage(state, "place_criminal")
    assert {pid: (p.role, p.location) for pid, p in state.pawns.items()} == before


def test_officers_lesson_shows_a_cop_in_a_hood_and_a_fed_in_a_spot(game_data) -> None:
    state, _ = _new_game(game_data)
    build_tutorial_scenario("corrupt_officer", state, game_data)
    assert len(state.board.hoods["hood_q1"].cop_ids) == 1
    assert len(state.board.spots["spot_artisti_1"].fed_ids) == 1
    # Re-applying the stage (going back and forth) never stacks a second one.
    build_tutorial_scenario("corrupt_officer", state, game_data)
    assert len(state.board.hoods["hood_q1"].cop_ids) == 1
    assert len(state.board.spots["spot_artisti_1"].fed_ids) == 1


def test_answering_many_lessons_in_a_row_never_ends_the_turn() -> None:
    """Each answered lesson used to advance the round counter, so the 3rd
    one (Buy) ended the Turn and resolved a Raid mid-lesson."""
    from dope_engine.adapters.http.app import _service
    from dope_engine.application.legal_actions import build_command_from_selection

    state = _service.create_tutorial_game(game_id=GameId("t_rounds"), scenario_id="intro").state
    for stage in ("place_criminal", "move_criminal", "buy_dope", "sell_dope", "corrupt_officer"):
        state = _service.apply_tutorial_stage(state, stage)
        decision = state.pending_decision
        view = _service.view_for(state, PlayerId("player_0"))
        state = _service.dispatch(
            state, build_command_from_selection(view, decision, (decision.options[0].option_id,))
        ).state
        assert state.raids.last_outcome is None, stage
        assert state.turn_index == 1, stage


def test_evasion_stage_continues_the_jail_lesson_and_returns_its_events() -> None:
    """The Evasion card replays from real events: the 4th arrest reaches the
    Jail, then the Evasion fires (one Politici Link, the others go home)."""
    from dope_engine.adapters.http.app import _service

    state = _service.create_tutorial_game(game_id=GameId("t_evasion"), scenario_id="intro").state
    state = _service.apply_tutorial_stage(state, "jail_near_full")
    assert sum(slot.rat_pawn_id is not None for slot in state.jail.slots) == 3
    before = {pid: p.role for pid, p in state.pawns.items()}

    state, events = _service.apply_tutorial_stage_with_events(state, "jail_evasion")

    names = [type(e).__name__ for e in events]
    assert "PawnArrested" in names and "JailEscapeTriggered" in names
    assert names.index("PawnArrested") < names.index("JailEscapeTriggered")
    assert all(slot.rat_pawn_id is None for slot in state.jail.slots)
    # The first 3 Rats were already there: only the 4th pawn arrives.
    assert names.count("PawnArrested") == 1
    triggering = next(e for e in events if type(e).__name__ == "JailEscapeTriggered")
    assert before[triggering.triggering_pawn_id] != "rat"


def test_http_stage_endpoint_patches_the_running_tutorial_game() -> None:
    from fastapi.testclient import TestClient

    from dope_engine.adapters.http.app import app

    client = TestClient(app)
    created = client.post("/api/v1/tutorial/grit").json()
    game_id = created["game_id"]
    staged = client.post(f"/api/v1/tutorial/{game_id}/stage/place_criminal")
    assert staged.status_code == 200
    assert staged.json()["revision"] == created["revision"] + 1
    assert staged.json()["game_id"] == game_id
    view = client.get(f"/api/v1/games/{game_id}/view", params={"player_id": "player_0"}).json()
    assert view["pending_decision"]["decision_type"] == "place_criminal"
    assert client.post(f"/api/v1/tutorial/{game_id}/stage/nope").status_code == 404
    assert client.post("/api/v1/tutorial/not_a_tutorial/stage/grit").status_code == 400
