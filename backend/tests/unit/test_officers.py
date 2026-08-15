from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
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


def test_corrupt_officer_rejects_without_presence(game_data, price_tracks) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    other_hood_id = next(
        hid
        for hid in state.board.hoods
        if hid != state.pawns[pawn_id].location.hood_id
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


def test_corruption_can_voluntarily_stop_after_a_single_action(
    game_data, price_tracks
) -> None:
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
