"""Maneuver and Corrupt cards of the 2026-10 set (game designer, 2026-10-16): 81 "FULL CONTROL",
82 "PAYOFF", 84 "EVIDENCE", 85 "ESCORT", 87/88/93 (free move / confiscate / arrest), 91
"BACKROOM DEAL", 97 "REDEEM" and 100 "SWEEP"."""

from test_officers import (
    _enter_main_action,
    _first_criminal_pawn_id,
    _new_game,
    _place_cop,
)

from dope_engine.application.command_bus import CommandBus, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import (
    ChooseManeuverAction,
    CorruptOfficer,
    ManeuverOfficer,
    PassOptionalStep,
    ResolveMoveFollowup,
)
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, PawnRole
from dope_engine.rules import economy, jail, move_followups, officers, turn_flow


def _bus(game_data, price_tracks, link_extra_action_types):
    bus = CommandBus()
    officers.register_handlers(bus, price_tracks=price_tracks)
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


def _maneuvering(game_data, boost_type, grit=1):
    state, _ = _new_game(game_data)
    for hood in state.board.hoods.values():
        hood.revealed = True
    player = _enter_main_action(state, ActionType.MANEUVER_OFFICER, grit)
    player.money = 20
    player.active_card_boost = {"type": boost_type, "action_types": ["maneuver_officer"]}
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    cop_id = _place_cop(state, hood_id)
    return state, player, pawn_id, hood_id, cop_id


def _me(state, player):
    return next(p for p in state.players if p.player_id == player.player_id)


def _start(bus, state, player, pawn_id, officer_id):
    outcome = bus.dispatch(
        state,
        ManeuverOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            maneuvers=((pawn_id, officer_id),),
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    return outcome.state


def _act(bus, state, player, action, target_id=None, second_target_id=None):
    outcome = bus.dispatch(
        state,
        ChooseManeuverAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action=action,
            target_id=target_id,
            second_target_id=second_target_id,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    return outcome.state


def _pass(bus, state, player):
    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id, player_id=player.player_id, expected_revision=state.revision
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    return outcome.state


def _decision(state, player, price_tracks, link_extra_action_types):
    return get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)


def test_free_move_only_charges_the_other_actions(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_free_move")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _start(bus, state, player, pawn_id, cop_id)
    adjacent = state.board.hoods[hood_id].adjacent_hood_ids[0]

    state = _act(bus, state, player, "move", adjacent)
    assert _me(state, player).money == 20  # free
    state = _act(bus, state, player, "confiscate")
    assert _me(state, player).money == 19  # $1


def test_free_arrest_and_free_confiscate(game_data, price_tracks, link_extra_action_types) -> None:
    for boost_type, action in (
        ("maneuver_free_arrest", "arrest"),
        ("maneuver_free_confiscate", "confiscate"),
    ):
        state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, boost_type)
        bus = _bus(game_data, price_tracks, link_extra_action_types)
        target = next(
            pid
            for pid in state.board.hoods[hood_id].criminal_pawn_ids
            if state.pawns[pid].owner_player_id != player.player_id
        ) if action == "arrest" else None
        if action == "arrest" and target is None:
            other = next(p for p in state.players if p.player_id != player.player_id)
            target = next(
                pid for pid in other.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
            )
            state.pawns[target].role = PawnRole.CRIMINAL
            state.pawns[target].location = PawnLocation.hood(hood_id)
            state.board.hoods[hood_id].criminal_pawn_ids.append(target)
        state = _start(bus, state, player, pawn_id, cop_id)
        state = _act(bus, state, player, action, target)
        assert _me(state, player).money == 20, boost_type


def test_a_free_action_can_be_used_with_no_money(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_free_move")
    player.money = 0
    bus = _bus(game_data, price_tracks, link_extra_action_types)

    state = _start(bus, state, player, pawn_id, cop_id)
    decision = _decision(state, player, price_tracks, link_extra_action_types)

    assert {o.payload["action"] for o in decision.options} == {"move"}


def test_full_control_gives_a_free_corruption_with_grit_3(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_free_corrupt", 3)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _start(bus, state, player, pawn_id, cop_id)
    state = _act(bus, state, player, "confiscate")
    state = _act(bus, state, player, "skip")
    money = _me(state, player).money

    state = _pass(bus, state, player)

    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "full_control"
    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="full_control",
            officer_id=cop_id,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.board.officers[cop_id].owner_player_id == player.player_id
    assert _me(outcome.state, player).money == money  # free


def test_full_control_needs_grit_3(game_data, price_tracks, link_extra_action_types) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_free_corrupt", 2)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _start(bus, state, player, pawn_id, cop_id)
    state = _act(bus, state, player, "confiscate")
    state = _act(bus, state, player, "skip")
    state = _pass(bus, state, player)

    assert state.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP


def test_escort_moves_a_criminal_along_with_the_cop(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_escort")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    adjacent = state.board.hoods[hood_id].adjacent_hood_ids[0]
    state = _start(bus, state, player, pawn_id, cop_id)
    state = _act(bus, state, player, "move", adjacent)
    state = _act(bus, state, player, "skip")
    if state.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP:
        state = _pass(bus, state, player)

    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "escort" and decision.can_pass
    option = next(o for o in decision.options if o.payload["pawn_id"] == pawn_id)
    assert option.payload["destination_hood_id"] == adjacent
    money = _me(state, player).money
    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="escort",
            pawn_id=pawn_id,
            destination_hood_id=adjacent,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert pawn_id in new.board.hoods[adjacent].criminal_pawn_ids
    assert pawn_id in _me(new, player).moved_pawn_ids_this_turn
    assert _me(new, player).money == money


def test_backroom_deal_sends_the_maneuvering_criminal_to_the_den(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_den")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _start(bus, state, player, pawn_id, cop_id)
    state = _act(bus, state, player, "confiscate")
    state = _act(bus, state, player, "skip")

    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "backroom" and not decision.can_pass
    contact_id = decision.options[0].payload["deck_contact_id"]
    hand = len(_me(state, player).hand_card_ids)
    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="backroom",
            pawn_id=pawn_id,
            deck_contact_id=contact_id,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert new.pawns[pawn_id].role == PawnRole.GAMBLER
    assert pawn_id in new.board.den_gambler_pawn_ids
    assert len(_me(new, player).hand_card_ids) == hand + 1


def _jail_a_rat(state, owner_index):
    owner = state.players[owner_index]
    pawn_id = next(pid for pid in owner.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    jail.arrest_pawn(state, pawn_id, [])
    return pawn_id


def test_redeem_sends_a_rat_to_the_cops_hood_as_a_criminal(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_redeem_rat")
    other_index = next(i for i, p in enumerate(state.players) if p.player_id != player.player_id)
    rat_id = _jail_a_rat(state, other_index)
    state.jail.slots[state.pawns[rat_id].jail_slot].confiscated_dope_type = DopeType.RANA
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _start(bus, state, player, pawn_id, cop_id)
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    arrest = [o for o in decision.options if o.payload["action"] == "arrest"]
    assert [o.payload["target_id"] for o in arrest] == [rat_id]
    owner = state.players[other_index]
    hand = len(owner.hand_card_ids)
    dope_before = owner.base_inventory.dope_counts.get(DopeType.RANA, 0)

    state = _act(bus, state, player, "arrest", rat_id)

    assert state.pawns[rat_id].role == PawnRole.CRIMINAL
    assert rat_id in state.board.hoods[hood_id].criminal_pawn_ids
    owner = state.players[other_index]
    assert len(owner.hand_card_ids) == hand + 1
    assert owner.base_inventory.dope_counts.get(DopeType.RANA, 0) == dope_before + 1  # goes along
    assert all(s.rat_pawn_id != rat_id for s in state.jail.slots)


def test_redeem_into_a_hood_of_four_starts_a_rissa(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_redeem_rat")
    hood = state.board.hoods[hood_id]
    other_index = next(i for i, p in enumerate(state.players) if p.player_id != player.player_id)
    rat_id = _jail_a_rat(state, other_index)
    # fill the Hood to 4 Criminals (pawns of the two other players)
    fillers = [
        pid
        for p in state.players
        if p.player_id != player.player_id
        for pid in p.pawn_ids
        if state.pawns[pid].role == PawnRole.IN_BASE and pid != rat_id
    ]
    while len(hood.criminal_pawn_ids) < 4:
        pid = fillers.pop()
        state.pawns[pid].role = PawnRole.CRIMINAL
        state.pawns[pid].location = PawnLocation.hood(hood_id)
        hood.criminal_pawn_ids.append(pid)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _start(bus, state, player, pawn_id, cop_id)
    state = _act(bus, state, player, "arrest", rat_id)
    state = _act(bus, state, player, "skip")

    assert state.pending_brawl is not None


def test_sweep_swaps_the_arrested_criminal_with_a_rat(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_sweep")
    other_index = next(i for i, p in enumerate(state.players) if p.player_id != player.player_id)
    rat_id = _jail_a_rat(state, other_index)
    slot = state.pawns[rat_id].jail_slot
    state.jail.slots[slot].confiscated_dope_type = DopeType.RANA
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _start(bus, state, player, pawn_id, cop_id)
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    swaps = [o for o in decision.options if o.payload.get("second_target_id") == rat_id]
    assert any(o.payload["target_id"] == pawn_id for o in swaps)
    owner = state.players[other_index]
    hand = len(owner.hand_card_ids)

    state = _act(bus, state, player, "arrest", pawn_id, rat_id)

    assert state.pawns[pawn_id].role == PawnRole.RAT and state.pawns[pawn_id].jail_slot == slot
    assert state.jail.slots[slot].rat_pawn_id == pawn_id
    assert state.jail.slots[slot].confiscated_dope_type == DopeType.RANA  # the Dope stays
    assert state.pawns[rat_id].role == PawnRole.CRIMINAL
    assert rat_id in state.board.hoods[hood_id].criminal_pawn_ids
    assert pawn_id not in state.board.hoods[hood_id].criminal_pawn_ids
    assert len(state.players[other_index].hand_card_ids) == hand + 1


def test_sweep_works_with_a_full_jail(game_data, price_tracks, link_extra_action_types) -> None:
    state, player, pawn_id, hood_id, cop_id = _maneuvering(game_data, "maneuver_sweep")
    other_index = next(i for i, p in enumerate(state.players) if p.player_id != player.player_id)
    for _ in state.jail.slots[:-1]:
        owner = state.players[other_index]
        pid = next(p for p in owner.pawn_ids if state.pawns[p].role == PawnRole.IN_BASE)
        jail.arrest_pawn(state, pid, [])
    assert jail.has_free_rat_slot(state)
    last = state.jail.slots[-1]
    pid = next(
        p for p in state.players[other_index].pawn_ids if state.pawns[p].role == PawnRole.IN_BASE
    )
    last.rat_pawn_id = pid
    state.pawns[pid].role = PawnRole.RAT
    state.pawns[pid].jail_slot = last.index
    state.pawns[pid].location = PawnLocation.jail()
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _start(bus, state, player, pawn_id, cop_id)
    decision = _decision(state, player, price_tracks, link_extra_action_types)

    arrests = [o for o in decision.options if o.payload["action"] == "arrest"]
    assert arrests and all("second_target_id" in o.payload for o in arrests)


def _corrupting(game_data, boost_type):
    state, _ = _new_game(game_data)
    for hood in state.board.hoods.values():
        hood.revealed = True
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER, 1)
    player.money = 20
    player.active_card_boost = {"type": boost_type, "action_types": ["corrupt_officer"]}
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id
    cop_id = _place_cop(state, hood_id)
    return state, player, pawn_id, hood_id, cop_id


def _corrupt(bus, state, player, pawn_id, cop_id, payment=None):
    return bus.dispatch(
        state,
        CorruptOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, cop_id, None),),
            payment_dope_types=(payment,) if payment else (),
        ),
    )


def test_payoff_pays_a_dope_of_choice_back_to_the_supply(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _corrupting(game_data, "corrupt_pay_dope")
    player.base_inventory.dope_counts.clear()
    player.base_inventory.dope_counts[DopeType.RANA] = 2
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    payments = {o.payload.get("payment_dope_type") for o in decision.options}
    assert payments == {None, DopeType.RANA.value}
    supply = state.market.supply_remaining_by_dope_type.get(DopeType.RANA, 0)

    outcome = _corrupt(bus, state, player, pawn_id, cop_id, DopeType.RANA.value)

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert _me(new, player).money == 20
    assert _me(new, player).base_inventory.dope_counts[DopeType.RANA] == 1
    assert new.market.supply_remaining_by_dope_type[DopeType.RANA] == supply + 1
    assert new.board.officers[cop_id].owner_player_id == player.player_id


def test_payoff_works_without_money_and_rejects_a_dope_not_owned(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _corrupting(game_data, "corrupt_pay_dope")
    player.money = 0
    player.base_inventory.dope_counts.clear()
    player.base_inventory.dope_counts[DopeType.RANA] = 1
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert {o.payload["payment_dope_type"] for o in decision.options} == {DopeType.RANA.value}

    refused = _corrupt(bus, state, player, pawn_id, cop_id, DopeType.CAMALEONTE.value)
    assert not isinstance(refused, CommandSuccess)


def test_evidence_brings_a_dope_from_the_hood_when_there_is_room(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _corrupting(game_data, "corrupt_officer_carries_dope")
    hood = state.board.hoods[hood_id]
    assert hood.dope_stack
    dope = hood.dope_stack[-1]
    stack = len(hood.dope_stack)
    before = player.base_inventory.dope_counts.get(dope, 0)
    bus = _bus(game_data, price_tracks, link_extra_action_types)

    outcome = _corrupt(bus, state, player, pawn_id, cop_id)

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert _me(new, player).base_inventory.dope_counts[dope] == before + 1
    assert len(new.board.hoods[hood_id].dope_stack) == stack - 1


def test_evidence_takes_nothing_when_the_covo_is_full_of_that_dope(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _corrupting(game_data, "corrupt_officer_carries_dope")
    hood = state.board.hoods[hood_id]
    dope = hood.dope_stack[-1]
    player.base_inventory.dope_counts[dope] = 3
    stack = len(hood.dope_stack)
    bus = _bus(game_data, price_tracks, link_extra_action_types)

    outcome = _corrupt(bus, state, player, pawn_id, cop_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert len(outcome.state.board.hoods[hood_id].dope_stack) == stack
    assert _me(outcome.state, player).base_inventory.dope_counts[dope] == 3


# --- Corrupt cards 86, 89, 90, 92, 94, 96, 98 ---------------------------------


def _resolve(bus, state, player, **fields):
    return bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            **fields,
        ),
    )


def _corrupted(game_data, price_tracks, link_extra_action_types, boost_type):
    state, player, pawn_id, hood_id, cop_id = _corrupting(game_data, boost_type)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    outcome = _corrupt(bus, state, player, pawn_id, cop_id)
    assert isinstance(outcome, CommandSuccess), outcome
    return bus, outcome.state, player, pawn_id, hood_id, cop_id


def test_vacancy_moves_a_criminal_from_an_adjacent_hood_free_and_draws(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _corrupting(game_data, "corrupt_move_anywhere")
    adjacent = state.board.hoods[hood_id].adjacent_hood_ids[0]
    mover = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    state.pawns[mover].role = PawnRole.CRIMINAL
    state.pawns[mover].location = PawnLocation.hood(adjacent)
    state.board.hoods[adjacent].criminal_pawn_ids.append(mover)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _corrupt(bus, state, player, pawn_id, cop_id).state

    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "vacancy" and decision.can_pass
    assert mover in {o.payload["pawn_id"] for o in decision.options}
    money, hand = _me(state, player).money, len(_me(state, player).hand_card_ids)

    outcome = _resolve(
        bus, state, player, kind="vacancy", pawn_id=mover, destination_hood_id=hood_id
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert mover in new.board.hoods[hood_id].criminal_pawn_ids
    assert _me(new, player).money == money
    assert len(_me(new, player).hand_card_ids) == hand + 1


def test_riot_moves_a_criminal_from_any_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player, pawn_id, hood_id, cop_id = _corrupting(game_data, "corrupt_move_anywhere")
    far = next(
        h.hood_id
        for h in state.board.hoods.values()
        if h.hood_id != hood_id and h.hood_id not in state.board.hoods[hood_id].adjacent_hood_ids
    )
    mover = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    state.pawns[mover].role = PawnRole.CRIMINAL
    state.pawns[mover].location = PawnLocation.hood(far)
    state.board.hoods[far].criminal_pawn_ids.append(mover)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    state = _corrupt(bus, state, player, pawn_id, cop_id).state

    decision = _decision(state, player, price_tracks, link_extra_action_types)

    assert mover in {o.payload["pawn_id"] for o in decision.options}


def test_fixer_raises_the_link_that_corrupted_a_fed(
    game_data, price_tracks, link_extra_action_types
) -> None:
    from test_officers import _place_fed

    from dope_engine.domain.entities import OfficerLocationType
    from dope_engine.rules import links

    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.CORRUPT_OFFICER, 1)
    player.money = 20
    player.active_card_boost = {"type": "corrupt_link_up", "action_types": ["corrupt_officer"]}
    spot = next(iter(state.board.spots.values()))
    link_pawn = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    links.insert_link(state, player.player_id, link_pawn, spot.contact_id, 1, [])
    fed_id = _place_fed(state, spot.spot_id)
    assert state.board.officers[fed_id].location_type == OfficerLocationType.SPOT
    bus = _bus(game_data, price_tracks, link_extra_action_types)

    state = _corrupt(bus, state, player, link_pawn, fed_id).state

    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    outcome = _resolve(bus, state, player, kind="fixer", pawn_id=link_pawn)
    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.pawns[link_pawn].link_level == 2


def test_connection_turns_the_corrupting_criminal_into_a_link(
    game_data, price_tracks, link_extra_action_types
) -> None:
    bus, state, player, pawn_id, hood_id, cop_id = _corrupted(
        game_data, price_tracks, link_extra_action_types, "corrupt_to_link"
    )
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "connection" and decision.can_pass

    outcome = _resolve(bus, state, player, kind="connection", pawn_id=pawn_id)

    assert isinstance(outcome, CommandSuccess), outcome
    pawn = outcome.state.pawns[pawn_id]
    assert pawn.role == PawnRole.LINK and pawn.link_level == 1
    assert pawn_id not in outcome.state.board.hoods[hood_id].criminal_pawn_ids


def test_safe_passage_sends_the_corrupting_criminal_to_the_den(
    game_data, price_tracks, link_extra_action_types
) -> None:
    bus, state, player, pawn_id, hood_id, cop_id = _corrupted(
        game_data, price_tracks, link_extra_action_types, "corrupt_den"
    )
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "backroom" and not decision.can_pass

    outcome = _resolve(
        bus,
        state,
        player,
        kind="backroom",
        pawn_id=pawn_id,
        deck_contact_id=decision.options[0].payload["deck_contact_id"],
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.pawns[pawn_id].role == PawnRole.GAMBLER


def test_last_job_arrests_a_criminal_of_the_cops_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    bus, state, player, pawn_id, hood_id, cop_id = _corrupted(
        game_data, price_tracks, link_extra_action_types, "corrupt_arrest"
    )
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "last_job" and decision.can_pass
    assert pawn_id in {o.payload["pawn_id"] for o in decision.options}  # even your own

    outcome = _resolve(bus, state, player, kind="last_job", pawn_id=pawn_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.pawns[pawn_id].role == PawnRole.RAT
    assert pawn_id not in outcome.state.board.hoods[hood_id].criminal_pawn_ids


def test_cover_places_a_criminal_for_two_dollars_and_draws(
    game_data, price_tracks, link_extra_action_types
) -> None:
    bus, state, player, pawn_id, hood_id, cop_id = _corrupted(
        game_data, price_tracks, link_extra_action_types, "corrupt_place"
    )
    decision = _decision(state, player, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "cover" and decision.can_pass
    money, hand = _me(state, player).money, len(_me(state, player).hand_card_ids)
    cost = state.configuration["costs"]["place_criminal"]
    criminals = len(state.board.hoods[hood_id].criminal_pawn_ids)

    outcome = _resolve(bus, state, player, kind="cover", destination_hood_id=hood_id)

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert _me(new, player).money == money - cost
    assert len(_me(new, player).hand_card_ids) == hand + 1
    assert len(new.board.hoods[hood_id].criminal_pawn_ids) == criminals + 1
