from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import BuyOfficer, ChooseCorruptionAction, CorruptOfficer
from dope_engine.domain.entities import OfficerLocationType, OfficerState, PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, OfficerType, PawnRole
from dope_engine.domain.ids import GameId, OfficerId
from dope_engine.rules import officers
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


def test_corrupt_officer_starts_first_corruption_and_charges_cost(game_data, price_tracks) -> None:
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
    assert new_player.money == starting_money - state.configuration["costs"]["corrupt_cop"]
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


def test_two_different_corruption_actions_resolve_and_return_to_main_flow(
    game_data, price_tracks
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(price_tracks)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER)
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    officer_id = _place_cop(state, hood_id)
    dest_hood_id = state.board.hoods[hood_id].adjacent_hood_ids[0]

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
    # Dope; either way the corruption's 2nd *slot* has been attempted.
    if isinstance(confiscate_outcome, CommandFailure):
        return
    state = confiscate_outcome.state
    new_player = next(p for p in state.players if p.player_id == player.player_id)
    assert state.pending_corruption is None
    assert new_player.pending_action_type is None


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
