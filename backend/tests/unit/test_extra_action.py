from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import (
    ChooseActionType,
    PassOptionalStep,
    PlaceCriminal,
    SpendLinkForExtraAction,
)
from dope_engine.domain.entities import OfficerLocationType, OfficerState
from dope_engine.domain.enums import (
    ActionType,
    ActiveStep,
    ControllerType,
    GamePhase,
    OfficerType,
    PawnRole,
)
from dope_engine.domain.ids import ContactId, GameId, HoodId, OfficerId, SkillId
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
    Politici Link (maneuver_officer/corrupt_officer only) has no legal target
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


def test_manager_link_qualifies_to_spend_even_with_no_other_free_base_pawn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Bug report (game designer, 2026-09-26): "la pedina gancio si
    illumina anche se ne ho 10 in gioco... mentre se ho un gancio dai
    manager questa non lampeggia" — a Manager Link (place_criminal only,
    data/contacts.json) never glowed as spendable once every other pawn
    was already deployed, even though spending it returns it to base
    *before* Piazza runs (§A5), which should make Piazza achievable with
    that exact pawn. A multi-action Contact like Preti masked the same
    gap (buy_dope/sell_dope/maneuver_officer can each qualify on their
    own, with no free base pawn needed), so it only ever surfaced for a
    Contact restricted to place_criminal alone."""
    state, _ = _new_game(game_data)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    pawn_ids = list(player.pawn_ids)
    link_pawn_id = pawn_ids[0]

    # Deploy every *other* pawn onto the board — only the Link candidate
    # itself would still be "available", and it's about to stop being
    # IN_BASE too (insert_link below turns it into a Link).
    hood_ids = list(state.board.hoods.keys())
    for i, pawn_id in enumerate(pawn_ids[1:]):
        pawn = state.pawns[pawn_id]
        pawn.role = PawnRole.CRIMINAL
        pawn.hood_id = hood_ids[i % len(hood_ids)]

    events: list = []
    links.insert_link(state, player.player_id, link_pawn_id, ContactId("manager"), 1, events)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    assert not any(
        state.pawns[pid].role == PawnRole.IN_BASE for pid in pawn_ids if pid != link_pawn_id
    )

    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision is not None
    assert decision.decision_type == "spend_link_for_extra_action"
    assert any(option.payload["pawn_id"] == link_pawn_id for option in decision.options)


def test_link_extra_action_is_never_offered_past_the_per_round_cap(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """The cap can shrink while the offer is pending (a Job reward bumping the
    Skill that raised it), and spending would then be refused with
    "extra_action_already_used" — found by a bot sweep, 2026-10-06."""
    state, _ = _new_game(game_data)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    link_pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    links.insert_link(state, player.player_id, link_pawn_id, ContactId("preti"), 2, [])
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision is not None and decision.options  # room under the cap: offered

    player.extra_actions_used_this_round = 1  # the base cap
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision is not None
    assert decision.decision_type == "spend_link_for_extra_action"
    assert decision.options == ()


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


# --- Politici-3 ("2 Ganci a turno"): both Links usable before, after, or one on each side ---------


def _politici_3_player_with_two_manager_links(state):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.skill_ids = [SkillId("skill_politici_3")]
    player.money = 100
    base_pawn_ids = [pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE]
    link_pawn_ids = base_pawn_ids[:2]
    for pawn_id in link_pawn_ids:
        links.insert_link(state, player.player_id, pawn_id, ContactId("manager"), 1, [])
    return player, link_pawn_ids


def _spend_link_and_place_criminal(bus, state, player_id, pawn_id):
    """One whole Link extra action (a Manager Link: Piazza only); returns (state, events)."""
    events: list = []

    def send(command):
        nonlocal state
        outcome = bus.dispatch(state, command)
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state
        events.extend(outcome.events)

    def header():
        return {
            "game_id": state.game_id,
            "player_id": player_id,
            "expected_revision": state.revision,
        }

    send(SpendLinkForExtraAction(**header(), pawn_id=pawn_id))
    send(ChooseActionType(**header(), action_type="place_criminal"))
    hood_id = next(h.hood_id for h in state.board.hoods.values() if h.revealed)
    send(PlaceCriminal(**header(), hood_ids=(hood_id,)))
    return state, events


def test_politici_3_both_links_can_be_spent_before_the_main_action(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player, (first, second) = _politici_3_player_with_two_manager_links(state)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    state, _ = _spend_link_and_place_criminal(bus, state, player.player_id, first)

    # The cap isn't reached yet and a Link is left: the "prima" offer comes back.
    assert state.current_player_id == player.player_id
    assert state.active_step == ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision is not None
    assert decision.decision_type == "spend_link_for_extra_action"
    assert [o.payload["pawn_id"] for o in decision.options] == [second]

    state, _ = _spend_link_and_place_criminal(bus, state, player.player_id, second)

    refreshed = next(p for p in state.players if p.player_id == player.player_id)
    assert refreshed.extra_actions_used_this_round == 2
    assert state.active_step == ActiveStep.WAITING_FOR_GRIT_ACTION


def test_politici_3_both_links_can_be_spent_after_the_main_action(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player, (first, second) = _politici_3_player_with_two_manager_links(state)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    player.extra_action_from_post_main = True  # the "dopo" offer point

    state, _ = _spend_link_and_place_criminal(bus, state, player.player_id, first)

    assert state.current_player_id == player.player_id
    assert state.active_step == ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    refreshed = next(p for p in state.players if p.player_id == player.player_id)
    assert refreshed.extra_action_from_post_main is True

    state, events = _spend_link_and_place_criminal(bus, state, player.player_id, second)

    refreshed = next(p for p in state.players if p.player_id == player.player_id)
    assert refreshed.extra_actions_used_this_round == 2
    assert "ActionRoundEnded" in [type(e).__name__ for e in events]


def test_politici_3_one_link_before_and_one_after_the_main_action(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player, (first, second) = _politici_3_player_with_two_manager_links(state)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    state, _ = _spend_link_and_place_criminal(bus, state, player.player_id, first)
    # Decline the second "prima" offer and play the round's own action instead.
    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id, player_id=player.player_id, expected_revision=state.revision
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step == ActiveStep.WAITING_FOR_GRIT_ACTION

    # The main action is over: the "dopo" offer still has the second Link.
    refreshed = next(p for p in state.players if p.player_id == player.player_id)
    events: list = []
    turn_flow.proceed_after_main_action(state, refreshed, events)
    assert state.active_step == ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    assert refreshed.extra_action_from_post_main is True

    state, events = _spend_link_and_place_criminal(bus, state, player.player_id, second)
    assert "ActionRoundEnded" in [type(e).__name__ for e in events]


def test_without_politici_3_the_offer_does_not_come_back_after_the_first_link(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player, (first, _second) = _politici_3_player_with_two_manager_links(state)
    player.skill_ids = []
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    state, _ = _spend_link_and_place_criminal(bus, state, player.player_id, first)

    assert state.active_step == ActiveStep.WAITING_FOR_GRIT_ACTION


# --- a Skill is active from the moment it is taken, the same round included -------------------


def _remove_politici_3_from_the_piles(state):
    for pile in state.skills.remaining_by_contact.values():
        if SkillId("skill_politici_3") in pile:
            pile.remove(SkillId("skill_politici_3"))


def test_after_main_offer_stays_open_at_the_cap_while_politici_3_can_still_be_taken(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """The Job reward that may hand over Politici-3 is claimed *after* the action's tail has
    decided what comes next, so with the cap reached and a Link left the "dopo" offer is
    kept open: empty (nothing to spend) unless the Skill arrives."""
    state, _ = _new_game(game_data)
    player, _links = _politici_3_player_with_two_manager_links(state)
    player.skill_ids = []
    player.extra_actions_used_this_round = 1  # the base cap, reached with the "prima" Link
    assert any(
        SkillId("skill_politici_3") in pile for pile in state.skills.remaining_by_contact.values()
    )

    events: list = []
    turn_flow.proceed_after_main_action(state, player, events)

    assert state.active_step == ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    assert player.extra_action_from_post_main is True
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision is not None
    assert decision.options == ()

    # The Skill arrives (the Job reward): the very same offer now has the second Link.
    player.skill_ids = [SkillId("skill_politici_3")]
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision is not None
    assert len(decision.options) == 2


def test_after_main_offer_is_not_kept_open_once_politici_3_is_out_of_the_piles(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    player, _links = _politici_3_player_with_two_manager_links(state)
    player.skill_ids = []
    player.extra_actions_used_this_round = 1
    _remove_politici_3_from_the_piles(state)

    events: list = []
    turn_flow.proceed_after_main_action(state, player, events)

    assert "ActionRoundEnded" in [type(e).__name__ for e in events]
    assert state.active_step != ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION


def test_after_main_offer_is_not_kept_open_without_a_link_left(game_data) -> None:
    state, _ = _new_game(game_data)
    player, (first, second) = _politici_3_player_with_two_manager_links(state)
    player.skill_ids = []
    player.extra_actions_used_this_round = 1
    for pawn_id in (first, second):  # both spent: back in the Covo
        state.pawns[pawn_id].role = PawnRole.IN_BASE
        state.pawns[pawn_id].contact_id = None

    events: list = []
    turn_flow.proceed_after_main_action(state, player, events)

    assert "ActionRoundEnded" in [type(e).__name__ for e in events]
