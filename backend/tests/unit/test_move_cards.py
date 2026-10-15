"""Move cards of the 2026-10 set (game designer, 2026-10-15): 40 "MAKE FRIENDS" (2 cards when
entering a Hood where you have no Criminal), 31 "SPLIT" (a Link comes back as a Criminal),
26 "BADGE HUNT" (move a Cop of the Hood you enter, $1) and 32 "SEAT SWAP" (swap with an
opposing Gambler when entering the Den)."""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import MoveCriminal, PassOptionalStep, ResolveMoveFollowup
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, PawnRole
from dope_engine.domain.ids import DEN_ID, ContactId, GameId
from dope_engine.domain.state import hoods_within_two_steps
from dope_engine.rules import economy, links, move_followups, turn_flow
from dope_engine.rules.setup import create_initial_state


def _bus(game_data, price_tracks, link_extra_action_types):
    bus = CommandBus()
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id={c.card_id: c.contact_id for c in game_data.customer_cards},
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id={c.card_id: c.action_type for c in game_data.customer_cards},
    )
    move_followups.register_handlers(bus)
    turn_flow.register_handlers(
        bus, card_contact_by_id={c.card_id: c.contact_id for c in game_data.customer_cards}
    )
    return bus


def _moving_player(game_data, boost_type):
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = 1
    player.pending_action_type = ActionType.MOVE_CRIMINAL
    player.money = 50
    player.active_card_boost = {"type": boost_type, "action_types": ["move_criminal"], "count": 1}
    return state, player


def _criminal_and_empty_neighbour(state, player):
    """A Criminal of the player and an adjacent Hood where the player has no pawn."""
    for pid in player.pawn_ids:
        pawn = state.pawns[pid]
        if pawn.role != PawnRole.CRIMINAL:
            continue
        hood = state.board.hoods[pawn.location.hood_id]
        for adjacent_id in hood.adjacent_hood_ids:
            adjacent = state.board.hoods[adjacent_id]
            if adjacent.revealed and not any(
                state.pawns[p].owner_player_id == player.player_id
                for p in adjacent.criminal_pawn_ids
            ):
                return pid, hood.hood_id, adjacent_id
    raise AssertionError("no such pawn")


def _move(bus, state, player, pawn_id, destination, deck=None):
    return bus.dispatch(
        state,
        MoveCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            moves=((pawn_id, destination, deck),),
        ),
    )


def _me(state, player):
    return next(p for p in state.players if p.player_id == player.player_id)


# --- 40 MAKE FRIENDS ----------------------------------------------------------------------


def test_make_friends_draws_two_cards_entering_a_hood_without_own_criminals(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _moving_player(game_data, "bonus_card_draw_new_hood")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, _from_hood, empty = _criminal_and_empty_neighbour(state, player)
    hand_before = len(player.hand_card_ids)

    outcome = _move(bus, state, player, pawn_id, empty)

    assert isinstance(outcome, CommandSuccess), outcome
    assert len(_me(outcome.state, player).hand_card_ids) == hand_before + 2


def test_make_friends_draws_the_normal_one_card_where_the_player_is_present(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _moving_player(game_data, "bonus_card_draw_new_hood")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, _from_hood, empty = _criminal_and_empty_neighbour(state, player)
    # another pawn of the player already stands in the destination
    other = next(
        pid
        for pid in player.pawn_ids
        if state.pawns[pid].role == PawnRole.IN_BASE
    )
    state.pawns[other].role = PawnRole.CRIMINAL
    state.pawns[other].location = PawnLocation.hood(empty)
    state.board.hoods[empty].criminal_pawn_ids.append(other)
    hand_before = len(player.hand_card_ids)

    outcome = _move(bus, state, player, pawn_id, empty)

    assert isinstance(outcome, CommandSuccess), outcome
    assert len(_me(outcome.state, player).hand_card_ids) == hand_before + 1


# --- 31 SPLIT -----------------------------------------------------------------------------


def test_split_brings_a_link_back_as_a_criminal_in_a_hood_of_its_contact(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _moving_player(game_data, "link_to_criminal")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    contact = ContactId("artisti")
    link_pawn = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    links.insert_link(state, player.player_id, link_pawn, contact, 1, [])
    hoods = [h for h in state.board.hoods.values() if h.contact_id == contact and h.revealed]
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    destinations = {
        o.payload["destination_hood_id"]
        for o in decision.options
        if o.payload["pawn_id"] == link_pawn
    }
    assert destinations == {h.hood_id for h in hoods}
    hand_before = len(player.hand_card_ids)

    outcome = _move(bus, state, player, link_pawn, hoods[0].hood_id)

    assert isinstance(outcome, CommandSuccess), outcome
    pawn = outcome.state.pawns[link_pawn]
    assert pawn.role == PawnRole.CRIMINAL and pawn.link_level is None and pawn.contact_id is None
    assert link_pawn in outcome.state.board.hoods[hoods[0].hood_id].criminal_pawn_ids
    assert links.contact_links(outcome.state, contact) == {}
    assert len(_me(outcome.state, player).hand_card_ids) == hand_before + 1


def test_split_rejects_a_hood_of_another_contact(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _moving_player(game_data, "link_to_criminal")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    contact = ContactId("artisti")
    link_pawn = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    links.insert_link(state, player.player_id, link_pawn, contact, 1, [])
    other = next(
        h.hood_id for h in state.board.hoods.values() if h.contact_id != contact and h.revealed
    )

    outcome = _move(bus, state, player, link_pawn, other)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "not_a_hood_of_the_contact"


# --- 26 BADGE HUNT ------------------------------------------------------------------------


def _badge_hunt_move(game_data, price_tracks, link_extra_action_types):
    state, player = _moving_player(game_data, "badge_hunt")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, _from_hood, destination = _criminal_and_empty_neighbour(state, player)
    economy.spawn_cop(state, state.board.hoods[destination], [])
    outcome = _move(bus, state, player, pawn_id, destination)
    assert isinstance(outcome, CommandSuccess), outcome
    return outcome.state, player, destination, bus


def test_badge_hunt_moves_a_cop_of_the_entered_hood_for_a_dollar(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, destination, bus = _badge_hunt_move(
        game_data, price_tracks, link_extra_action_types
    )
    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision.decision_type == "move_followup" and decision.can_pass
    option = decision.options[0].payload
    assert option["destination_hood_id"] in state.board.hoods[destination].adjacent_hood_ids
    money_before = _me(state, player).money

    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="badge_hunt",
            officer_id=option["officer_id"],
            destination_hood_id=option["destination_hood_id"],
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert option["officer_id"] in new.board.hoods[option["destination_hood_id"]].cop_ids
    assert option["officer_id"] not in new.board.hoods[destination].cop_ids
    assert _me(new, player).money == money_before - 1
    assert _me(new, player).pending_action_type is None
    assert new.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP


def test_badge_hunt_can_be_declined(game_data, price_tracks, link_extra_action_types) -> None:
    state, player, destination, bus = _badge_hunt_move(
        game_data, price_tracks, link_extra_action_types
    )
    money_before = _me(state, player).money

    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert _me(outcome.state, player).money == money_before
    assert outcome.state.board.hoods[destination].cop_ids  # the Cop stayed


# --- 32 SEAT SWAP -------------------------------------------------------------------------


def _make_gambler(state, pawn_id):
    pawn = state.pawns[pawn_id]
    if pawn.role == PawnRole.CRIMINAL:
        state.board.hoods[pawn.location.hood_id].criminal_pawn_ids.remove(pawn_id)
    pawn.role = PawnRole.GAMBLER
    pawn.location = PawnLocation.den()
    state.board.den_gambler_pawn_ids.append(pawn_id)


def _opponents(state, player):
    return [p.player_id for p in state.players if p.player_id != player.player_id]


def _free_pawns(state, player_id, count):
    player = next(p for p in state.players if p.player_id == player_id)
    return [pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE][:count]


def test_seat_swap_brings_an_opposing_gambler_out_into_the_hood_left(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _moving_player(game_data, "den_seat_swap")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    enemy = _free_pawns(state, _opponents(state, player)[0], 1)[0]
    _make_gambler(state, enemy)
    pawn_id, from_hood, _ = _criminal_and_empty_neighbour(state, player)

    outcome = _move(bus, state, player, pawn_id, DEN_ID, ContactId("artisti"))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert [o.payload["gambler_pawn_id"] for o in decision.options] == [enemy]

    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="den_swap",
            gambler_pawn_id=enemy,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert new.pawns[enemy].role == PawnRole.CRIMINAL
    assert new.pawns[enemy].location.hood_id == from_hood
    assert new.pawns[pawn_id].role == PawnRole.GAMBLER
    assert pawn_id in new.board.den_gambler_pawn_ids and enemy not in new.board.den_gambler_pawn_ids


def test_seat_swap_works_with_a_full_den_and_is_then_mandatory(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _moving_player(game_data, "den_seat_swap")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    capacity = state.configuration["den_capacity"]
    enemies = []
    for owner in _opponents(state, player):
        enemies += _free_pawns(state, owner, 2)
    assert len(enemies) == capacity
    for pid in enemies:
        _make_gambler(state, pid)
    pawn_id, _from_hood, _ = _criminal_and_empty_neighbour(state, player)

    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert any(o.payload["destination_hood_id"] == DEN_ID for o in decision.options)

    outcome = _move(bus, state, player, pawn_id, DEN_ID, ContactId("artisti"))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert len(state.board.den_gambler_pawn_ids) == capacity + 1
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert not decision.can_pass

    refused = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id, player_id=player.player_id, expected_revision=state.revision
        ),
    )
    assert isinstance(refused, CommandFailure)
    assert refused.error.code == "followup_mandatory"

    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="den_swap",
            gambler_pawn_id=enemies[0],
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    assert len(outcome.state.board.den_gambler_pawn_ids) == capacity


# --- 29 LONG WAY --------------------------------------------------------------------------


def _two_steps_away(state, player):
    """A Criminal of the player and a revealed Hood exactly two steps from it."""
    for pid in player.pawn_ids:
        pawn = state.pawns[pid]
        if pawn.role != PawnRole.CRIMINAL:
            continue
        hood = state.board.hoods[pawn.location.hood_id]
        for hood_id in hoods_within_two_steps(state, hood.hood_id):
            far = state.board.hoods[hood_id]
            if hood_id not in hood.adjacent_hood_ids and far.revealed:
                return pid, hood_id
    raise AssertionError("no Hood two steps away")


def test_long_way_lets_a_criminal_move_two_steps(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _moving_player(game_data, "move_distance_2")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    pawn_id, far = _two_steps_away(state, player)
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert any(
        o.payload["pawn_id"] == pawn_id and o.payload["destination_hood_id"] == far
        for o in decision.options
    )

    outcome = _move(bus, state, player, pawn_id, far)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.pawns[pawn_id].location.hood_id == far


def test_without_long_way_a_move_two_steps_away_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _moving_player(game_data, "move_distance_2")
    pawn_id, far = _two_steps_away(state, player)
    player.active_card_boost = None
    bus = _bus(game_data, price_tracks, link_extra_action_types)

    outcome = _move(bus, state, player, pawn_id, far)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "not_adjacent"
