"""Milestone 5 Stage 4 (Skill mechanical effects).

Stage 4a — "+1 Grinta sempre" bundle: Artisti-1 (buy/sell Dope),
Studenti-1 (move Criminal), Manager-1 (place Criminal), Politici-1
(corrupt/buy Officer).

Stage 4b — flat cost/price modifiers: Artisti-2 (buy Dope -1 / sell Dope
+1 per unit), Manager-2 (place Criminal costs $1 instead of $2),
Politici-2 (corrupt/buy Officer -$1).

Each Skill's own `effect` payload (data/skills.json) is read from
`state.configuration["skill_effect_by_id"]` identically by the option
generator (application/legal_actions.py) and the command validator/
mutator (rules/economy.py, rules/officers.py) — both sides are exercised
here, not just the pure `rules/skills.py` helpers.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import BuyOfficer, PlaceCriminal
from dope_engine.domain.enums import ActionType, ActiveStep, OfficerType
from dope_engine.domain.ids import GameId, HoodId, OfficerId, SkillId
from dope_engine.rules import economy, officers, skills
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
    officers.register_handlers(bus, price_tracks=price_tracks)
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


def test_manager_1_raises_the_max_target_count_end_to_end(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Confirmed by the game designer (2026-08-02): a package may use
    fewer than its (possibly Skill-boosted) max — Manager-1 raises the
    *ceiling* to 2, it doesn't force exactly 2."""
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
    assert decision.min_selections == 1
    assert decision.max_selections == 2  # base Grit 1 + Manager-1's +1

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


def test_manager_1_still_allows_using_fewer_than_the_boosted_max(
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
            hood_ids=(HoodId("hood_q2"),),  # 1 of the 2 the Skill allows
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome


def test_place_criminal_rejects_more_than_the_boosted_max(
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
            hood_ids=(HoodId("hood_q1"), HoodId("hood_q2"), HoodId("hood_q3")),  # 3 > max of 2
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_target_count"
    assert outcome.error.details["max"] == 2


def test_place_criminal_rejects_zero_targets(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.money = 100

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_target_count"
    assert outcome.error.details["min"] == 1


# --- Stage 4b: flat cost/price modifiers -------------------------------


def test_effective_cost_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    assert skills.effective_cost(state, player, ActionType.PLACE_CRIMINAL, 2) == 2


def test_manager_2_reduces_place_criminal_cost_by_one(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_manager_2")]
    assert skills.effective_cost(state, player, ActionType.PLACE_CRIMINAL, 2) == 1
    # Doesn't affect an unrelated action_type.
    assert skills.effective_cost(state, player, ActionType.BUY_OFFICER, 7) == 7


def test_politici_2_reduces_corrupt_and_buy_officer_cost_by_one(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_politici_2")]
    assert skills.effective_cost(state, player, ActionType.CORRUPT_OFFICER, 2) == 1
    assert skills.effective_cost(state, player, ActionType.BUY_OFFICER, 7) == 6


def test_effective_cost_never_goes_negative(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    state.configuration["skill_effect_by_id"][SkillId("skill_test_fake_cost")] = {
        "type": "cost_delta",
        "action_types": ["place_criminal"],
        "amount": -100,
    }
    player.skill_ids = [SkillId("skill_test_fake_cost")]
    assert skills.effective_cost(state, player, ActionType.PLACE_CRIMINAL, 2) == 0


def test_artisti_2_shifts_buy_and_sell_price(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_2")]
    assert skills.effective_trade_price(state, player, ActionType.BUY_DOPE, 5) == 4
    assert skills.effective_trade_price(state, player, ActionType.SELL_DOPE, 5) == 6


def test_effective_trade_price_never_goes_negative(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_2")]
    assert skills.effective_trade_price(state, player, ActionType.BUY_DOPE, 0) == 0


def test_manager_2_charges_the_discounted_cost_end_to_end(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.skill_ids = [SkillId("skill_manager_2")]
    starting_money = player.money

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(HoodId("hood_q2"),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money == starting_money - 1  # $1, not the base $2


def test_politici_2_charges_the_discounted_cost_for_buy_officer_into_base(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.skill_ids = [SkillId("skill_politici_2")]
    player.money = 100
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = ActionType.BUY_OFFICER
    player.current_round_grit_value = 1

    hood_id = next(h.hood_id for h in state.board.hoods.values() if h.revealed)
    officer_id = OfficerId("officer_test_cop")
    from dope_engine.domain.entities import OfficerLocationType, OfficerState

    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.HOOD,
        hood_id=hood_id,
    )
    state.board.hoods[hood_id].cop_ids.append(officer_id)
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == "criminal")
    state.pawns[pawn_id].location = state.pawns[pawn_id].location.__class__.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)
    starting_money = player.money

    outcome = bus.dispatch(
        state,
        BuyOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, officer_id, None),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money == starting_money - 6  # $6, not the base $7
