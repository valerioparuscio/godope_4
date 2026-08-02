"""Milestone 5 Stage 4a (Skill mechanical effects — "+1 Grinta sempre"
bundle): Artisti-1 (buy/sell Dope), Studenti-1 (move Criminal),
Manager-1 (place Criminal), Politici-1 (corrupt/buy Officer). Each
Skill's own `effect` payload (data/skills.json) is read from
`state.configuration["skill_effect_by_id"]` identically by the option
generator (application/legal_actions.py) and the command validator
(rules/economy.py::_validate_action_targets) — both sides are exercised
here, not just the pure `rules/skills.py::effective_action_count` helper.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import PlaceCriminal
from dope_engine.domain.enums import ActionType, ActiveStep
from dope_engine.domain.ids import GameId, HoodId, SkillId
from dope_engine.rules import economy, skills
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _bus(game_data, price_tracks, link_extra_action_types):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
    )
    return bus


def _enter_main_action(state, action_type, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    player.pending_action_type = action_type
    return player


# --- effective_action_count (pure) -----------------------------------------


def test_effective_action_count_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    count = skills.effective_action_count(state, player, ActionType.BUY_DOPE, 2)
    assert count == 2


def test_artisti_1_boosts_buy_and_sell_dope(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_1")]
    assert skills.effective_action_count(state, player, ActionType.BUY_DOPE, 2) == 3
    assert skills.effective_action_count(state, player, ActionType.SELL_DOPE, 1) == 2


def test_artisti_1_does_not_boost_unrelated_action_types(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_1")]
    assert skills.effective_action_count(state, player, ActionType.MOVE_CRIMINAL, 2) == 2
    assert skills.effective_action_count(state, player, ActionType.PLACE_CRIMINAL, 2) == 2


def test_studenti_1_boosts_move_criminal_only(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_studenti_1")]
    assert skills.effective_action_count(state, player, ActionType.MOVE_CRIMINAL, 1) == 2
    assert skills.effective_action_count(state, player, ActionType.BUY_DOPE, 1) == 1


def test_manager_1_boosts_place_criminal_only(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_manager_1")]
    assert skills.effective_action_count(state, player, ActionType.PLACE_CRIMINAL, 1) == 2
    assert skills.effective_action_count(state, player, ActionType.MOVE_CRIMINAL, 1) == 1


def test_politici_1_boosts_corrupt_and_buy_officer(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_politici_1")]
    assert skills.effective_action_count(state, player, ActionType.CORRUPT_OFFICER, 1) == 2
    assert skills.effective_action_count(state, player, ActionType.BUY_OFFICER, 1) == 2
    assert skills.effective_action_count(state, player, ActionType.SELL_DOPE, 1) == 1


def test_multiple_skills_boosting_the_same_action_type_stack(game_data) -> None:
    """Not explicitly ruled on, but the only reading consistent with each
    Skill being an independent permanent ability (§A10): two Skills that
    both boost the same action_type add up. Only one real Skill grants
    +1 Grit to buy_dope in the 15-skill set, so a synthetic second entry
    exercises the purely additive logic directly."""
    state, _ = _new_game(game_data)
    player = state.players[0]
    fake_skill_id = SkillId("skill_test_fake_extra_grit")
    state.configuration["skill_effect_by_id"][fake_skill_id] = {
        "type": "extra_grit",
        "action_types": ["buy_dope"],
        "amount": 1,
    }
    player.skill_ids = [SkillId("skill_artisti_1"), fake_skill_id]

    assert skills.effective_action_count(state, player, ActionType.BUY_DOPE, 1) == 3


# --- end-to-end: offer side + validation side agree -------------------


def test_manager_1_requires_the_boosted_target_count_end_to_end(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.skill_ids = [SkillId("skill_manager_1")]
    player.money = 100

    decision = get_legal_decision(
        state, player.player_id, price_tracks, link_extra_action_types
    )
    assert decision is not None
    assert decision.decision_type == "place_criminal"
    assert decision.min_selections == 2  # base Grit 1 + Manager-1's +1
    assert decision.max_selections == 2

    hood_ids = tuple(o.payload["hood_id"] for o in decision.options[:2])
    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=hood_ids,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome


def test_manager_1_rejects_the_unboosted_target_count(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.skill_ids = [SkillId("skill_manager_1")]
    player.money = 100

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(HoodId("hood_q2"),),  # only 1, but 2 are required now
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_target_count"
    assert outcome.error.details["expected"] == 2
