"""Card 99 "NEW ORDERS" (game designer, 2026-10-16): with 3 officers in the Covo the current
Raid is replaced by a random one that has not come out in the game yet."""

from dope_engine.application.command_bus import CommandBus, CommandSuccess
from dope_engine.domain.commands import PlayCustomerCardBoost
from dope_engine.domain.entities import OfficerLocationType, OfficerState
from dope_engine.domain.enums import ActionType, ActiveStep, OfficerType
from dope_engine.domain.ids import CardId, GameId, OfficerId
from dope_engine.rules import customer_cards, raids
from dope_engine.rules.setup import create_initial_state


def _setup(game_data, officers_in_base):
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=3, human_seat=0)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.raids.current_turn_card_id = state.raids.selected_card_ids[state.turn_index - 1]
    for i in range(officers_in_base):
        oid = OfficerId(f"officer_base_{i}")
        state.board.officers[oid] = OfficerState(
            officer_id=oid,
            officer_type=OfficerType.COP,
            location_type=OfficerLocationType.BASE,
            owner_player_id=player.player_id,
        )
    card = CardId("card_099")
    player.hand_card_ids.append(card)
    state.active_step = ActiveStep.WAITING_FOR_CARD_BOOST
    player.pending_action_type = ActionType.CORRUPT_OFFICER
    player.card_boost_return_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    return state, player, card


def _bus(game_data):
    bus = CommandBus()
    customer_cards.register_handlers(
        bus,
        card_effect_by_id={c.card_id: c.effect for c in game_data.customer_cards},
        action_type_by_card_id={c.card_id: c.action_type for c in game_data.customer_cards},
        card_contact_by_id={c.card_id: c.contact_id for c in game_data.customer_cards},
        stonk_count_by_card_id={c.card_id: c.stonk_count for c in game_data.customer_cards},
    )
    return bus


def _play(bus, state, player, card):
    return bus.dispatch(
        state,
        PlayCustomerCardBoost(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card,
        ),
    )


def test_new_orders_swaps_the_raid_for_one_not_yet_out(game_data) -> None:
    state, player, card = _setup(game_data, 3)
    old = state.raids.current_turn_card_id
    drawn = set(state.raids.selected_card_ids)

    outcome = _play(_bus(game_data), state, player, card)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    new = new_state.raids.current_turn_card_id
    assert new != old and new not in drawn
    assert new_state.raids.selected_card_ids[new_state.turn_index - 1] == new
    assert old in new_state.raids.replaced_card_ids
    assert new_state.raids.replacement_count == 1
    assert any(type(e).__name__ == "RaidReplaced" for e in outcome.events)


def test_new_orders_needs_three_officers_in_the_covo(game_data) -> None:
    state, player, card = _setup(game_data, 2)

    outcome = _play(_bus(game_data), state, player, card)

    assert not isinstance(outcome, CommandSuccess)


def test_a_replaced_raid_never_comes_back(game_data) -> None:
    state, player, card = _setup(game_data, 3)
    seen = {state.raids.current_turn_card_id}
    for _ in range(4):
        if not raids.can_replace_current_raid(state):
            break
        raids.replace_current_raid(state, [])
        assert state.raids.current_turn_card_id not in seen
        seen.add(state.raids.current_turn_card_id)
