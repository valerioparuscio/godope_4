from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import ChooseActionType, PlaceCriminal, SpendLinkForExtraAction
from dope_engine.domain.entities import OfficerLocationType, OfficerState
from dope_engine.domain.enums import (
    ActionType,
    ActiveStep,
    ControllerType,
    GamePhase,
    OfficerType,
    PawnRole,
)
from dope_engine.domain.ids import ContactId, GameId, HoodId, OfficerId
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

    state.board.hoods[HoodId("hood_q2")].revealed = True
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
    assert new_player.extra_actions_used_this_round == 1


def test_link_extra_action_may_repeat_an_action_type_already_used_this_turn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Confirmed by the game designer (2026-08-02): the no-repeat-per-turn
    rule (rules/economy.py::_handle_choose_action_type) only applies to
    base Grit rounds — a Link's extra action is a separate mechanic and
    may reuse an action_type already spent this turn."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.action_types_used_this_turn = [ActionType.PLACE_CRIMINAL]
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


def test_spending_the_only_link_at_a_contact_removes_a_now_unqualified_fed(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """§A6 (implemented 2026-08-02): a Fed leaves a dope-less Spot the
    moment its Contact's last Link disappears — here, by that Link being
    spent for its extra action and returning to the Covo."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    link_pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    contact_id = ContactId("manager")

    events: list = []
    links.insert_link(state, player.player_id, link_pawn_id, contact_id, 1, events)
    spot = next(s for s in state.board.spots.values() if s.contact_id == contact_id)
    fed_id = OfficerId("officer_fed_test")
    state.board.officers[fed_id] = OfficerState(
        officer_id=fed_id,
        officer_type=OfficerType.FED,
        location_type=OfficerLocationType.SPOT,
        spot_id=spot.spot_id,
    )
    spot.fed_ids.append(fed_id)
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
    new_spot = outcome.state.board.spots[spot.spot_id]
    assert new_spot.fed_ids == []
    assert fed_id not in outcome.state.board.officers


def test_advance_auto_skips_extra_action_offer_with_no_legal_target_for_any_link(
    game_service, price_tracks, link_extra_action_types
) -> None:
    """Game designer, 2026-09-18: reported being asked "vuoi spendere un
    gancio?" with the Link pawn never highlighted on the board — a lone
    Politici Link (corrupt_officer/buy_officer only) has no legal target
    when the player has no other pawn out and no officer exists anywhere
    yet, exactly the state right after game creation (the spent Link
    returns to its Covo before the extra action itself runs, per §A5, so
    it can never be the one executing it). A bot silently submits an
    empty selection here and never notices; only a human was stopped to
    click a "Salta" that was the sole possible answer. advance() should
    skip a decision shaped like this transparently for a human too."""
    result = game_service.create_game(game_id=GameId("g"), seed=1, human_seat=0)
    state = result.state
    human = next(p for p in state.players if p.controller_type is ControllerType.HUMAN)
    link_pawn_id = next(pid for pid in human.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    events: list = []
    links.insert_link(state, human.player_id, link_pawn_id, ContactId("politici"), 1, events)
    state.current_player_id = human.player_id
    state.phase = GamePhase.ACTION_PHASE
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    state.pending_decision = get_legal_decision(
        state, human.player_id, price_tracks, link_extra_action_types
    )
    assert state.pending_decision is not None
    assert state.pending_decision.decision_type == "spend_link_for_extra_action"
    assert state.pending_decision.options == ()

    result = game_service.advance(state)
    state = result.state

    assert state.active_step != ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    assert state.pending_decision is not None
    assert state.pending_decision.decision_type != "spend_link_for_extra_action"
    refreshed_human = next(p for p in state.players if p.player_id == human.player_id)
    assert refreshed_human.extra_action_link_pawn_id is None


def test_advance_still_stops_for_a_human_when_the_link_extra_action_has_real_options(
    game_service, price_tracks, link_extra_action_types
) -> None:
    """Regression guard for the fix above: a Link whose extra action DOES
    have a legal target (Manager's Link -> place_criminal, always
    achievable at game start — an in-base pawn plus an empty Hood) must
    still stop and wait for the human, not get swept up by the same
    auto-skip."""
    result = game_service.create_game(game_id=GameId("g"), seed=1, human_seat=0)
    state = result.state
    human = next(p for p in state.players if p.controller_type is ControllerType.HUMAN)
    link_pawn_id = next(pid for pid in human.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    events: list = []
    links.insert_link(state, human.player_id, link_pawn_id, ContactId("manager"), 1, events)
    state.current_player_id = human.player_id
    state.phase = GamePhase.ACTION_PHASE
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    state.pending_decision = get_legal_decision(
        state, human.player_id, price_tracks, link_extra_action_types
    )
    assert state.pending_decision is not None
    assert state.pending_decision.decision_type == "spend_link_for_extra_action"
    assert len(state.pending_decision.options) > 0

    result = game_service.advance(state)
    state = result.state

    assert state.active_step == ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    assert state.pending_decision is not None
    assert state.pending_decision.decision_type == "spend_link_for_extra_action"
