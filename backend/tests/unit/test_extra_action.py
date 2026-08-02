from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import ChooseActionType, PlaceCriminal, SpendLinkForExtraAction
from dope_engine.domain.enums import ActiveStep, PawnRole
from dope_engine.domain.ids import ContactId, GameId, HoodId
from dope_engine.rules import economy, links, turn_flow
from dope_engine.rules.setup import create_initial_state


def _bus(game_data, price_tracks, link_extra_action_types):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    turn_flow.register_handlers(bus, card_contact_by_id=card_contact_by_id)
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
    )
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def test_spend_link_for_extra_action_uses_link_level_as_grit_value(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    link_pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    events: list = []
    links.insert_link(state, player.player_id, link_pawn_id, ContactId("manager"), 2, events)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    outcome = bus.dispatch(
        state,
        SpendLinkForExtraAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            pawn_id=link_pawn_id,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    new_player = next(p for p in state.players if p.player_id == player.player_id)
    assert new_player.current_round_grit_value == 2
    assert new_player.extra_action_link_pawn_id == link_pawn_id


def test_extra_action_rejects_action_type_not_allowed_for_contact(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    link_pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    events: list = []
    links.insert_link(state, player.player_id, link_pawn_id, ContactId("manager"), 1, events)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    outcome = bus.dispatch(
        state,
        SpendLinkForExtraAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            pawn_id=link_pawn_id,
        ),
    )
    state = outcome.state

    # Manager's Link only allows place_criminal (data/contacts.json); buy_dope must be rejected.
    outcome = bus.dispatch(
        state,
        ChooseActionType(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action_type="buy_dope",
        ),
    )
    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "action_type_not_allowed_for_link"


def test_completed_extra_action_returns_link_to_base_and_marks_used(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    link_pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    events: list = []
    links.insert_link(state, player.player_id, link_pawn_id, ContactId("manager"), 1, events)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    spend_outcome = bus.dispatch(
        state,
        SpendLinkForExtraAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            pawn_id=link_pawn_id,
        ),
    )
    assert isinstance(spend_outcome, CommandSuccess), spend_outcome
    state = spend_outcome.state

    # §A5 (confirmed 2026-08-01): the Link returns to its Covo
    # immediately when spent, before the extra action itself runs.
    assert state.pawns[link_pawn_id].role == PawnRole.IN_BASE
    assert state.pawns[link_pawn_id].contact_id is None
    assert "LinkPawnReturnedToBase" in [type(e).__name__ for e in spend_outcome.events]

    outcome = bus.dispatch(
        state,
        ChooseActionType(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action_type="place_criminal",
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

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
    state = outcome.state

    new_player = next(p for p in state.players if p.player_id == player.player_id)
    assert new_player.extra_action_link_pawn_id is None
    assert new_player.extra_actions_used_this_turn == 1
