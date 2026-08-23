from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import (
    BuyDope,
    ChooseActionType,
    MoveCriminal,
    PlaceCriminal,
    SellDope,
)
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, PawnRole
from dope_engine.domain.ids import DEN_ID, ContactId, GameId, HoodId, OfficerId, SpotId
from dope_engine.rules import economy
from dope_engine.rules.setup import create_initial_state


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


# --- ChooseActionType: no repeat per turn (confirmed 2026-08-02) -------


def _enter_choose_action_type(state, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    return player


def test_choose_action_type_rejects_a_type_already_used_this_turn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_choose_action_type(state)
    player.action_types_used_this_turn = [ActionType.PLACE_CRIMINAL]

    outcome = bus.dispatch(
        state,
        ChooseActionType(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action_type="place_criminal",
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "action_type_already_used_this_turn"


def test_choose_action_type_records_the_type_as_used_this_turn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_choose_action_type(state)

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
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.action_types_used_this_turn == [ActionType.PLACE_CRIMINAL]


# --- PlaceCriminal -----------------------------------------------------


def test_place_criminal_charges_cost_moves_pawn_and_draws_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    starting_money = player.money
    starting_hand_size = len(player.hand_card_ids)
    hood = state.board.hoods[HoodId("hood_q2")]
    hood.revealed = True
    starting_criminal_count = len(hood.criminal_pawn_ids)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    new_hood = outcome.state.board.hoods[HoodId("hood_q2")]
    assert new_player.money == starting_money - state.configuration["costs"]["place_criminal"]
    assert len(new_hood.criminal_pawn_ids) == starting_criminal_count + 1
    assert len(new_player.hand_card_ids) == starting_hand_size + 1
    assert new_player.pending_action_type is None


def test_place_criminal_rejects_insufficient_funds(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.money = 0

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "insufficient_funds"


def test_place_criminal_rejects_hood_capacity_exceeded(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    hood = state.board.hoods[HoodId("hood_q2")]
    hood.revealed = True
    hood.criminal_pawn_ids = [f"filler_{i}" for i in range(hood.capacity)]

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "hood_capacity_exceeded"


def test_place_criminal_never_brings_hood_to_rissa_trigger_count(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Placing (unlike Moving) must never itself bring a Hood to its Rissa
    trigger count (docs/rules/RULE_CHANGELOG.md, 2026-07-31): a Hood one
    short of that count must still reject a further placement, even
    though raw capacity (5) is not yet reached."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    hood = state.board.hoods[HoodId("hood_q2")]
    hood.revealed = True
    trigger_count = state.configuration["brawl_trigger_criminal_count"]
    hood.criminal_pawn_ids = [f"filler_{i}" for i in range(trigger_count - 1)]
    assert len(hood.criminal_pawn_ids) < hood.capacity

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "hood_capacity_exceeded"


def test_place_criminal_rejects_unrevealed_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Game designer (2026-08-16): an unrevealed Hood can only ever be
    reached via a Brawl loser's relocation, never a normal placement —
    it becomes placeable/movable only once that reveals it
    (rules/brawl.py sets hood.revealed = True)."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    unrevealed = next(h for h in state.board.hoods.values() if not h.revealed)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(unrevealed.hood_id,),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "hood_not_revealed"


# --- MoveCriminal --------------------------------------------------------


def test_move_criminal_to_adjacent_hood_marks_moved_and_draws_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)
    from_hood_id = state.pawns[pawn_id].location.hood_id
    to_hood_id = state.board.hoods[from_hood_id].adjacent_hood_ids[0]

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, to_hood_id, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_state = outcome.state
    assert new_state.pawns[pawn_id].location.hood_id == to_hood_id
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert pawn_id in new_player.moved_pawn_ids_this_turn
    assert pawn_id not in new_state.board.hoods[from_hood_id].criminal_pawn_ids
    assert pawn_id in new_state.board.hoods[to_hood_id].criminal_pawn_ids


def test_move_criminal_rejects_non_adjacent_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)
    from_hood_id = state.pawns[pawn_id].location.hood_id
    non_adjacent = next(
        hid
        for hid in state.board.hoods
        if hid != from_hood_id and hid not in state.board.hoods[from_hood_id].adjacent_hood_ids
    )

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, non_adjacent, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "not_adjacent"


def test_move_criminal_into_den_without_deck_choice_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, DEN_ID, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "deck_choice_required"


def test_move_criminal_into_den_becomes_gambler(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)
    from_hood_id = state.pawns[pawn_id].location.hood_id

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, DEN_ID, ContactId("artisti")),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_state = outcome.state
    assert new_state.pawns[pawn_id].role == PawnRole.GAMBLER
    assert pawn_id in new_state.board.den_gambler_pawn_ids
    assert pawn_id not in new_state.board.hoods[from_hood_id].criminal_pawn_ids


def test_move_criminal_into_den_rejected_at_per_player_cap(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Decision (2026-08-15): a player can never have more than 2 of
    their own pawns in the Den at once, even though the Den's own global
    capacity (6) has room for more from other players."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    criminal_pawn_ids = [
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
    ]
    first_id, second_id, third_id = criminal_pawn_ids[:3]
    for pawn_id in (first_id, second_id):
        pawn = state.pawns[pawn_id]
        state.board.hoods[pawn.location.hood_id].criminal_pawn_ids.remove(pawn_id)
        pawn.role = PawnRole.GAMBLER
        pawn.location = PawnLocation.den()
        state.board.den_gambler_pawn_ids.append(pawn_id)

    outcome = bus.dispatch(
        state,
        MoveCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            moves=((third_id, DEN_ID, ContactId("artisti")),),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "den_full_for_player"


# --- BuyDope --------------------------------------------------------------


def test_buy_dope_deducts_money_and_adds_to_base_inventory(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_count = player.base_inventory.dope_counts.get(dope_type, 0)
    starting_stock = len(hood.dope_stack)

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood.hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money < 100
    assert new_player.base_inventory.dope_counts.get(dope_type, 0) == starting_count + 1
    new_hood = outcome.state.board.hoods[hood.hood_id]
    assert len(new_hood.dope_stack) == starting_stock - 1


def test_buy_dope_rejects_purchase_that_would_exceed_base_cap(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """§11.4/RULES_PENDING.md #26 (resolved by the game designer,
    2026-08-23): the Covo's 3-per-type cap blocks the purchase outright
    instead of letting it happen and discarding the Dope afterward — a
    behavior change from the earlier DopeLostToOverflow event, which no
    longer fires from Buy Dope (still used by Jail Escape recovery,
    untouched)."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_stock = len(hood.dope_stack)
    starting_money = player.money
    player.base_inventory.dope_counts[dope_type] = 3

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood.hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "base_inventory_full"
    # Rejected atomically — the original (unmutated) state is untouched.
    assert player.base_inventory.dope_counts[dope_type] == 3
    assert player.money == starting_money
    assert len(hood.dope_stack) == starting_stock


def test_buy_dope_restocks_hood_and_spawns_cop_when_emptied(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    hood.dope_stack = [dope_type]
    state.market.supply_remaining_by_dope_type[dope_type] = 10

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood.hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_hood = outcome.state.board.hoods[hood.hood_id]
    assert len(new_hood.dope_stack) == 3
    assert len(new_hood.cop_ids) == 1
    assert "HoodRestocked" in [type(e).__name__ for e in outcome.events]
    assert "CopEnteredHood" in [type(e).__name__ for e in outcome.events]


def test_buy_dope_rejects_hood_blocked_by_cop(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    hood.cop_ids = [OfficerId("officer_test")]

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood.hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "hood_blocked_by_cop"


def test_buy_dope_rejects_duplicate_pawn(game_data, price_tracks, link_extra_action_types) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE, grit_value=2)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood_id), (pawn_id, hood_id)),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "duplicate_pawn_in_targets"


# --- SellDope -------------------------------------------------------------


def test_sell_dope_adds_money_and_removes_from_base_inventory(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    starting_money = player.money

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money > starting_money
    assert new_player.base_inventory.dope_counts[DopeType.POLPO] == 0
    spot = outcome.state.board.spots[SpotId("spot_artisti_2")]
    assert spot.sold_dope_tokens == [DopeType.POLPO]


def test_sell_dope_clears_spot_and_spawns_fed_when_full(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    spot = state.board.spots[SpotId("spot_artisti_2")]
    spot.sold_dope_tokens = [DopeType.POLPO, DopeType.POLPO]

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_spot = outcome.state.board.spots[SpotId("spot_artisti_2")]
    assert new_spot.sold_dope_tokens == []
    assert len(new_spot.fed_ids) == 1
    assert "SpotCleared" in [type(e).__name__ for e in outcome.events]
    assert "FedEnteredSpot" in [type(e).__name__ for e in outcome.events]


def test_sell_dope_succeeds_despite_cop_in_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """A Cop in the Hood only blocks Buying there (§C3) — Selling is
    blocked exclusively by a Fed at the target Spot (§C4), never by a Cop
    in the Hood the seller is standing in."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    hood = state.board.hoods[HoodId("hood_q1")]
    hood.cop_ids = [OfficerId("officer_test")]

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    spot = outcome.state.board.spots[SpotId("spot_artisti_2")]
    assert spot.sold_dope_tokens == [DopeType.POLPO]


def test_sell_dope_rejects_spot_blocked_by_fed(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    spot = state.board.spots[SpotId("spot_artisti_2")]
    spot.fed_ids = [OfficerId("officer_test")]

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "spot_blocked_by_fed"


def test_sell_dope_rejects_dope_type_not_accepted(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.RANA] = 1

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.RANA),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "dope_type_not_accepted"


def test_sell_dope_rejects_no_dope_to_sell(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 0

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "no_dope_to_sell"


def test_sell_dope_package_of_two_grants_link_at_level_two(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE, grit_value=2)
    pawn_ids = [pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL][:2]
    for pawn_id in pawn_ids:
        _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 2

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=tuple((pawn_id, DopeType.POLPO) for pawn_id in pawn_ids),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    evolved_pawn = new_state.pawns[pawn_ids[0]]
    assert evolved_pawn.role == PawnRole.LINK
    assert evolved_pawn.contact_id == ContactId("artisti")
    assert evolved_pawn.link_level == 2
    other_pawn = new_state.pawns[pawn_ids[1]]
    assert other_pawn.role == PawnRole.CRIMINAL
    assert "PawnBecameLink" in [type(e).__name__ for e in outcome.events]
