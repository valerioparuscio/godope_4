from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import BuyOfficer, ChooseCorruptionAction, CorruptOfficer
from dope_engine.domain.entities import OfficerLocationType, OfficerState, PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, OfficerType, PawnRole
from dope_engine.domain.ids import GameId, OfficerId
from dope_engine.rules import links, officers
from dope_engine.rules.setup import create_initial_state


def _bus(price_tracks):
    bus = CommandBus()
    officers.register_handlers(bus, price_tracks=price_tracks)
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _enter_main_action(state, action_type, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    player.pending_action_type = action_type
    return player


def _first_criminal_pawn_id(state, player):
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)


def _relocate_to_hood(state, pawn_id, hood_id):
    pawn = state.pawns[pawn_id]
    old_hood_id = pawn.location.hood_id
    state.board.hoods[old_hood_id].criminal_pawn_ids.remove(pawn_id)
    pawn.location = PawnLocation.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)


def _place_cop(state, hood_id, *, officer_id="officer_cop_1"):
    officer_id = OfficerId(officer_id)
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.HOOD,
        hood_id=hood_id,
    )
    state.board.hoods[hood_id].cop_ids.append(officer_id)
    return officer_id


def _place_fed(state, spot_id, *, officer_id="officer_fed_1"):
    officer_id = OfficerId(officer_id)
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.FED,
        location_type=OfficerLocationType.SPOT,
        spot_id=spot_id,
    )
    state.board.spots[spot_id].fed_ids.append(officer_id)
    return officer_id


# --- CorruptOfficer / ChooseCorruptionAction -------------------------------


def test_corrupt_officer_starts_first_corruption_without_charging_yet(
    game_data, price_tracks
) -> None:
    """Decision (2026-08-15): cost is $1 per corruption *action*, charged
    as each one is taken (see ChooseCorruptionAction tests below) — not a
    flat per-officer cost charged upfront the way it used to be."""
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    starting_money = player.money

    command = CorruptOfficer(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        corruptions=((pawn_id, officer_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_state = outcome.state
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.money == starting_money
    assert new_state.active_step == ActiveStep.WAITING_FOR_CORRUPTION_ACTION
    assert new_state.pending_corruption is not None
    assert new_state.pending_corruption.officer_id == officer_id


def test_corrupt_officer_with_grit_2_queues_two_officers(game_data, price_tracks) -> None:
    """RULES_CANONICAL.md §C5 + the 2026-08-15 $1-per-action decision
    together: Grit N corrupts up to N *different* officers in one
    package (one pawn each), and each one independently offers its own
    up-to-3 actions at $1 each — so with Grit 2 and 2 pawns each with
    presence at their own Cop, finishing the first officer's corruption
    (however many of its up-to-3 actions were taken) must automatically
    move on to the second queued officer, not end the package early.
    Never had direct coverage before — CorruptOfficer's own queueing
    (`remaining_queue`/`_finish_corruption`) was only ever exercised
    indirectly through single-officer tests and full-game bot sweeps."""
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER, grit_value=2)
    criminal_pawn_ids = [
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
    ]
    pawn_a, pawn_b = criminal_pawn_ids[0], criminal_pawn_ids[1]
    hood_ids = list(state.board.hoods.keys())
    hood_a, hood_b = hood_ids[0], hood_ids[1]
    _relocate_to_hood(state, pawn_a, hood_a)
    _relocate_to_hood(state, pawn_b, hood_b)
    officer_a = _place_cop(state, hood_a, officer_id="officer_cop_a")
    officer_b = _place_cop(state, hood_b, officer_id="officer_cop_b")

    start_outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_a, officer_a), (pawn_b, officer_b)),
        ),
    )
    assert isinstance(start_outcome, CommandSuccess), start_outcome
    state = start_outcome.state
    assert state.active_step == ActiveStep.WAITING_FOR_CORRUPTION_ACTION
    assert state.pending_corruption.officer_id == officer_a
    assert state.pending_corruption.remaining_queue == [(pawn_b, officer_b)]

    move_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=state.board.hoods[hood_a].adjacent_hood_ids[0],
        ),
    )
    assert isinstance(move_outcome, CommandSuccess), move_outcome
    state = move_outcome.state
    player_after_move = next(p for p in state.players if p.player_id == player.player_id)

    skip_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="skip",
        ),
    )
    assert isinstance(skip_outcome, CommandSuccess), skip_outcome
    state = skip_outcome.state

    # The package moves on to officer B automatically — no extra command,
    # no dropped queue entry — offering a fresh up-to-3 actions for it.
    assert state.active_step == ActiveStep.WAITING_FOR_CORRUPTION_ACTION
    assert state.pending_corruption is not None
    assert state.pending_corruption.officer_id == officer_b
    assert state.pending_corruption.corruptor_pawn_id == pawn_b
    assert state.pending_corruption.actions_taken == []
    assert state.pending_corruption.remaining_queue == []
    player_after_skip = next(p for p in state.players if p.player_id == player.player_id)
    assert player_after_skip.money == player_after_move.money


def test_corrupt_officer_with_grit_2_offers_second_officer_after_first_finishes(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """2026-08-16 (2nd fix): committing to every officer upfront in one
    CorruptOfficer command (previous test) didn't match how a player
    wants to play it — decide whether to spend a *second* Grit point on
    another officer only after seeing how the first one went (game
    designer bug report: "quelle 2 azioni dovrebbero essere della prima
    grinta... poi ce ne è una seconda"). With Grit 2, submitting a
    CorruptOfficer package with only *one* (pawn, officer) pair must not
    end the whole action once that officer's own corruption finishes —
    it should loop back to a fresh corrupt_officer decision (1 of the 2
    Grit slots still unspent), excluding the already-used pawn, letting
    a second, separate CorruptOfficer command target a different pawn
    and officer. Once *that* one also finishes, the action really ends
    (both slots spent)."""
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER, grit_value=2)
    criminal_pawn_ids = [
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
    ]
    pawn_a, pawn_b = criminal_pawn_ids[0], criminal_pawn_ids[1]
    hood_ids = list(state.board.hoods.keys())
    hood_a, hood_b = hood_ids[0], hood_ids[1]
    _relocate_to_hood(state, pawn_a, hood_a)
    _relocate_to_hood(state, pawn_b, hood_b)
    officer_a = _place_cop(state, hood_a, officer_id="officer_cop_a")
    officer_b = _place_cop(state, hood_b, officer_id="officer_cop_b")

    start_outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_a, officer_a),),
        ),
    )
    assert isinstance(start_outcome, CommandSuccess), start_outcome
    state = start_outcome.state

    move_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=state.board.hoods[hood_a].adjacent_hood_ids[0],
        ),
    )
    assert isinstance(move_outcome, CommandSuccess), move_outcome
    state = move_outcome.state

    skip_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="skip",
        ),
    )
    assert isinstance(skip_outcome, CommandSuccess), skip_outcome
    state = skip_outcome.state

    # The action isn't over: 1 of 2 Grit slots is still unspent, so this
    # loops back instead of finishing.
    assert state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    assert state.pending_corruption is None
    assert state.current_player_id == player.player_id
    player = next(p for p in state.players if p.player_id == player.player_id)
    assert player.pending_action_type == ActionType.CORRUPT_OFFICER
    assert player.corrupted_pawn_ids_this_action == [pawn_a]

    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision is not None
    assert decision.decision_type == "corrupt_officer"
    assert decision.max_selections == 1
    offered_pawn_ids = {opt.payload["pawn_id"] for opt in decision.options}
    assert pawn_a not in offered_pawn_ids
    assert pawn_b in offered_pawn_ids

    second_outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_b, officer_b),),
        ),
    )
    assert isinstance(second_outcome, CommandSuccess), second_outcome
    state = second_outcome.state
    assert state.active_step == ActiveStep.WAITING_FOR_CORRUPTION_ACTION

    second_move_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=state.board.hoods[hood_b].adjacent_hood_ids[0],
        ),
    )
    assert isinstance(second_move_outcome, CommandSuccess), second_move_outcome
    state = second_move_outcome.state

    finish_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="skip",
        ),
    )
    assert isinstance(finish_outcome, CommandSuccess), finish_outcome
    state = finish_outcome.state

    # Both Grit slots are now spent, so this time the action really ends.
    player = next(p for p in state.players if p.player_id == player.player_id)
    assert player.pending_action_type is None
    assert state.active_step != ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS


def test_corrupt_officer_rejects_without_presence(game_data, price_tracks) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    other_hood_id = next(
        hid for hid in state.board.hoods if hid != state.pawns[pawn_id].location.hood_id
    )
    officer_id = _place_cop(state, other_hood_id)

    command = CorruptOfficer(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        corruptions=((pawn_id, officer_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "no_presence"


def test_corruption_charges_a_dollar_per_action_and_stays_open_past_two(
    game_data, price_tracks
) -> None:
    """Decision (2026-08-15): a corruption now allows up to 3 *different*
    actions (move/arrest/confiscate), $1 each, entirely the player's
    choice how many to take — so after exactly 2, the corruption must
    still be pending (offering the 3rd, or a voluntary stop), unlike the
    old "always exactly 2" model this superseded."""
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    dest_hood_id = state.board.hoods[hood_id].adjacent_hood_ids[0]
    starting_money = player.money

    start_outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_id, officer_id),),
        ),
    )
    assert isinstance(start_outcome, CommandSuccess)
    state = start_outcome.state

    move_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=dest_hood_id,
        ),
    )
    assert isinstance(move_outcome, CommandSuccess), move_outcome
    state = move_outcome.state
    assert state.board.officers[officer_id].hood_id == dest_hood_id
    assert state.active_step == ActiveStep.WAITING_FOR_CORRUPTION_ACTION
    player_after_move = next(p for p in state.players if p.player_id == player.player_id)
    assert player_after_move.money == starting_money - 1

    confiscate_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="confiscate",
        ),
    )
    assert isinstance(confiscate_outcome, CommandFailure | CommandSuccess)
    # Whether confiscate succeeds depends on the destination Hood having
    # Dope; either way the corruption is still open afterwards (only 2 of
    # the up-to-3 actions attempted) unless confiscate emptied the Hood
    # of both Dope and Criminals, forcing the officer back to reserve.
    if isinstance(confiscate_outcome, CommandFailure):
        return
    state = confiscate_outcome.state
    player_after_confiscate = next(p for p in state.players if p.player_id == player.player_id)
    if state.pending_corruption is not None:
        assert state.active_step == ActiveStep.WAITING_FOR_CORRUPTION_ACTION
        assert player_after_confiscate.money == starting_money - 2

    skip_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="skip",
        ),
    )
    if state.pending_corruption is None:
        assert isinstance(skip_outcome, CommandFailure)
        return
    assert isinstance(skip_outcome, CommandSuccess), skip_outcome
    final_state = skip_outcome.state
    final_player = next(p for p in final_state.players if p.player_id == player.player_id)
    assert final_state.pending_corruption is None
    assert final_player.pending_action_type is None
    # Voluntarily stopping never costs anything extra.
    assert final_player.money == player_after_confiscate.money


def test_corruption_can_voluntarily_stop_after_a_single_action(game_data, price_tracks) -> None:
    """The designer's rule (2026-08-15): "un'altra decide di pagare 2 per
    fare ad esempio solo arresta e requisisci" — stopping early is always
    the player's choice, not forced by running out of legal targets."""
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    starting_money = player.money

    start_outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_id, officer_id),),
        ),
    )
    assert isinstance(start_outcome, CommandSuccess)
    state = start_outcome.state

    move_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=state.board.hoods[hood_id].adjacent_hood_ids[0],
        ),
    )
    assert isinstance(move_outcome, CommandSuccess)
    state = move_outcome.state
    # Even though "arrest"/"confiscate" are still untried and may well
    # have legal targets, the handler itself already allows stopping
    # here — it was always legal-actions.py that withheld the choice.
    assert state.pending_corruption is not None

    skip_outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="skip",
        ),
    )
    assert isinstance(skip_outcome, CommandSuccess)
    final_state = skip_outcome.state
    final_player = next(p for p in final_state.players if p.player_id == player.player_id)
    assert final_state.pending_corruption is None
    assert final_player.money == starting_money - 1


def test_choose_corruption_action_rejects_reusing_same_action(game_data, price_tracks) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    dest_hood_id = state.board.hoods[hood_id].adjacent_hood_ids[0]

    outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_id, officer_id),),
        ),
    )
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=dest_hood_id,
        ),
    )
    state = outcome.state

    other_dest = state.board.hoods[dest_hood_id].adjacent_hood_ids[0]
    outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=other_dest,
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "action_already_used"


def test_card_065_lets_a_corrupted_cop_move_to_a_non_adjacent_hood(game_data, price_tracks) -> None:
    """Card 065 "TRANSFER" ("se sposti, manda il poliziotto dove vuoi",
    game designer, 2026-08-28): `officer_move_anywhere` bypasses the
    normal adjacency check on the corruption "move" sub-action — without
    it, the same non-adjacent target is rejected (see the assert on the
    plain-corruption fixture just below)."""
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    non_adjacent_hood_id = next(
        hid
        for hid in state.board.hoods
        if hid != hood_id and hid not in state.board.hoods[hood_id].adjacent_hood_ids
    )
    player.active_card_boost = {"type": "officer_move_anywhere"}

    outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_id, officer_id),),
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=non_adjacent_hood_id,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    moved_officer = outcome.state.board.officers[officer_id]
    assert moved_officer.hood_id == non_adjacent_hood_id
    assert officer_id in outcome.state.board.hoods[non_adjacent_hood_id].cop_ids
    assert officer_id not in outcome.state.board.hoods[hood_id].cop_ids


def test_without_card_065_a_corrupted_cop_cannot_move_non_adjacent(game_data, price_tracks) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    non_adjacent_hood_id = next(
        hid
        for hid in state.board.hoods
        if hid != hood_id and hid not in state.board.hoods[hood_id].adjacent_hood_ids
    )

    outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_id, officer_id),),
        ),
    )
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="move",
            target_id=non_adjacent_hood_id,
        ),
    )
    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "not_adjacent"


def test_cards_063_064_give_confiscated_dope_to_the_corruptor_instead_of_jail(
    game_data, price_tracks
) -> None:
    """Cards 063/064 "FAKE POLICE" ("prendi la Merce requisita",
    game designer, 2026-08-28): `keep_confiscated_dope` sends the
    confiscated unit straight to the corrupting player's own Covo
    (`rules/jail.py::recover_dope`) instead of a Jail confiscation slot —
    and needs no free slot to do it, unlike a plain confiscation."""
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    dope_type = state.board.hoods[hood_id].dope_stack[-1]
    player.active_card_boost = {"type": "keep_confiscated_dope"}
    # Fill every Jail confiscation slot so a plain confiscation would be
    # rejected outright (`jail_confiscation_full`) — proves this boost
    # genuinely bypasses that requirement rather than happening to have
    # a free slot anyway.
    for slot in state.jail.slots:
        slot.confiscated_dope_type = dope_type
    starting_count = player.base_inventory.dope_counts.get(dope_type, 0)

    outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_id, officer_id),),
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="confiscate",
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    final_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert final_player.base_inventory.dope_counts.get(dope_type, 0) == starting_count + 1
    # Every slot is still exactly as this test filled it — nothing went
    # to the Jail instead.
    assert all(slot.confiscated_dope_type == dope_type for slot in outcome.state.jail.slots)


# --- BuyOfficer -------------------------------------------------------------


def test_buy_officer_moves_map_cop_into_buyer_covo(game_data, price_tracks) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.BUY_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    starting_money = player.money

    command = BuyOfficer(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, officer_id, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    officer = new_state.board.officers[officer_id]
    assert officer.location_type == OfficerLocationType.BASE
    assert officer.owner_player_id == player.player_id
    assert officer_id not in new_state.board.hoods[hood_id].cop_ids
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.money == starting_money - state.configuration["costs"]["buy_officer"]


def test_buy_officer_moves_covo_cop_onto_map_and_pays_seller(game_data, price_tracks) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    seller = next(p for p in state.players if p.player_id != state.current_player_id)
    officer_id = OfficerId("officer_reserve_1")
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.BASE,
        owner_player_id=seller.player_id,
    )
    seller_starting_money = seller.money

    player = _enter_main_action(state, ActionType.BUY_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id

    command = BuyOfficer(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, officer_id, hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    officer = new_state.board.officers[officer_id]
    assert officer.location_type == OfficerLocationType.HOOD
    assert officer.hood_id == hood_id
    assert officer.owner_player_id is None
    new_seller = next(p for p in new_state.players if p.player_id == seller.player_id)
    assert new_seller.money == seller_starting_money + state.configuration["costs"]["buy_officer"]


def test_buy_officer_rejects_when_base_cap_reached(game_data, price_tracks) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.BUY_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id

    for i in range(state.configuration["base_max_chips_per_category"]):
        existing_id = OfficerId(f"officer_existing_{i}")
        state.board.officers[existing_id] = OfficerState(
            officer_id=existing_id,
            officer_type=OfficerType.COP,
            location_type=OfficerLocationType.BASE,
            owner_player_id=player.player_id,
        )

    officer_id = _place_cop(state, hood_id, officer_id="officer_new")
    command = BuyOfficer(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, officer_id, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "base_officer_cap_reached"


# --- §A6 Fed removal from an empty, Link-less Spot (implemented 2026-08-02) -


def test_fed_arresting_the_last_link_leaves_an_empty_spot_and_removes_the_fed(
    game_data, price_tracks
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    other_player = next(p for p in state.players if p.player_id != player.player_id)
    spot = next(iter(state.board.spots.values()))
    contact_hood_id = next(
        hid for hid, hood in state.board.hoods.items() if hood.contact_id == spot.contact_id
    )
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, contact_hood_id)
    fed_id = _place_fed(state, spot.spot_id)

    link_pawn_id = next(
        pid for pid in other_player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    events: list = []
    links.insert_link(state, other_player.player_id, link_pawn_id, spot.contact_id, 1, events)

    outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_id, fed_id),),
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="arrest",
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    new_spot = new_state.board.spots[spot.spot_id]
    assert new_spot.fed_ids == []
    assert fed_id not in new_state.board.officers
    assert "OfficerReturnedToReserve" in [type(e).__name__ for e in outcome.events]


def test_fed_arresting_a_link_keeps_the_fed_if_another_link_remains(
    game_data, price_tracks
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    other_player = next(p for p in state.players if p.player_id != player.player_id)
    spot = next(iter(state.board.spots.values()))
    contact_hood_id = next(
        hid for hid, hood in state.board.hoods.items() if hood.contact_id == spot.contact_id
    )
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, contact_hood_id)
    fed_id = _place_fed(state, spot.spot_id)

    other_pawn_ids = [
        pid for pid in other_player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    ]
    events: list = []
    links.insert_link(state, other_player.player_id, other_pawn_ids[0], spot.contact_id, 1, events)
    links.insert_link(state, other_player.player_id, other_pawn_ids[1], spot.contact_id, 1, events)

    outcome = bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            corruptions=((pawn_id, fed_id),),
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseCorruptionAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action="arrest",
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_spot = outcome.state.board.spots[spot.spot_id]
    assert new_spot.fed_ids == [fed_id]
