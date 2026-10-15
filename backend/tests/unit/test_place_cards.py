"""Placement cards of the 2026-10 set (game designer, 2026-10-15): 44 "HOME TURF" (free where
present), 46/58 "SCOUT" (one unrevealed Hood), 49 "RESERVES" (all pawns in the Covo at $3),
50 "BADGE HIRE", 51/57 "EXPANSION", 52/55 "STASH" (no draw, a placed pawn may buy) and
54 "DECOY" (a Cop enters)."""

from dope_engine.application.command_bus import CommandBus, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import (
    BuyDope,
    PassOptionalStep,
    PlaceCriminal,
    ResolveMoveFollowup,
)
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, PawnRole
from dope_engine.domain.ids import GameId
from dope_engine.rules import economy, move_followups, skills, turn_flow
from dope_engine.rules.setup import create_initial_state


def _bus(game_data, price_tracks, link_extra_action_types):
    bus = CommandBus()
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id={c.card_id: c.contact_id for c in game_data.customer_cards},
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id={c.card_id: c.action_type for c in game_data.customer_cards},
        tile_by_id={t.tile_id: t for t in game_data.board.covered_hood_tiles.tile_values},
    )
    move_followups.register_handlers(bus)
    turn_flow.register_handlers(
        bus, card_contact_by_id={c.card_id: c.contact_id for c in game_data.customer_cards}
    )
    return bus


def _placing(game_data, boost_type, **boost_fields):
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = 2
    player.pending_action_type = ActionType.PLACE_CRIMINAL
    player.money = 20
    player.active_card_boost = {
        "type": boost_type,
        "action_types": ["place_criminal"],
        **boost_fields,
    }
    return state, player


def _own_hood(state, player):
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)
    return state.pawns[pawn_id].location.hood_id


def _free_hoods(state, player, count, *, besides=()):
    """Revealed Hoods where `player` has no pawn."""
    found = [
        h.hood_id
        for h in state.board.hoods.values()
        if h.revealed
        and h.hood_id not in besides
        and not any(
            state.pawns[pid].owner_player_id == player.player_id for pid in h.criminal_pawn_ids
        )
        and not economy.player_has_presence(state, player, h.hood_id)
        and len(h.criminal_pawn_ids) < 3
    ]
    return found[:count]


def _place(bus, state, player, hood_ids):
    return bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=tuple(hood_ids),
        ),
    )


def _me(state, player):
    return next(p for p in state.players if p.player_id == player.player_id)


def test_home_turf_is_free_only_where_the_player_is_present(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_free_where_present")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    home = _own_hood(state, player)
    (elsewhere,) = _free_hoods(state, player, 1)
    paid = state.configuration["costs"]["place_criminal"]
    money = player.money

    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    costs = {o.payload["hood_id"]: o.payload["cost"] for o in decision.options}
    assert costs[home] == 0 and costs[elsewhere] == paid
    assert decision.context["budget"] == money

    outcome = _place(bus, state, player, [home, elsewhere])

    assert isinstance(outcome, CommandSuccess), outcome
    assert _me(outcome.state, player).money == money - paid


def test_home_turf_counts_a_link_as_presence(game_data) -> None:
    state, player = _placing(game_data, "place_free_where_present")
    link_pawn = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    contact = next(iter(state.board.hoods.values())).contact_id
    from dope_engine.rules import links

    links.insert_link(state, player.player_id, link_pawn, contact, 1, [])
    hood = next(h for h in state.board.hoods.values() if h.contact_id == contact and h.revealed)

    assert economy.placement_cost(state, player, hood.hood_id, 2) == 0


def test_reserves_places_every_pawn_in_the_covo_at_three_dollars(game_data) -> None:
    state, player = _placing(game_data, "place_all_reserves", cost=3)
    in_base = sum(1 for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    assert skills.effective_action_count(state, player, ActionType.PLACE_CRIMINAL, 1) == in_base
    assert skills.effective_cost(state, player, ActionType.PLACE_CRIMINAL, 2) == 3


def test_scout_places_in_an_unrevealed_hood_and_reveals_it(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_in_hidden_hood")
    hidden = next((h for h in state.board.hoods.values() if not h.revealed), None)
    assert hidden is not None
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert any(o.payload.get("hidden") for o in decision.options)
    hand_before = len(player.hand_card_ids)
    money = player.money

    outcome = _place(bus, state, player, [hidden.hood_id])

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert new.board.hoods[hidden.hood_id].revealed
    assert len(new.board.hoods[hidden.hood_id].criminal_pawn_ids) == 1
    after = _me(new, player)
    assert after.money == money - state.configuration["costs"]["place_criminal"]
    assert len(after.hand_card_ids) == hand_before + 1


def test_a_hidden_hood_is_refused_without_scout(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_free_where_present")
    hidden = next(h for h in state.board.hoods.values() if not h.revealed)
    bus = _bus(game_data, price_tracks, link_extra_action_types)

    outcome = _place(bus, state, player, [hidden.hood_id])

    assert not isinstance(outcome, CommandSuccess)


def test_stash_draws_nothing_then_lets_a_placed_pawn_buy_or_pass(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_then_buy")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    (target,) = _free_hoods(state, player, 1)
    hood = state.board.hoods[target]
    hood.dope_stack = [DopeType.RANA]
    hood.cop_ids.clear()
    hand_before = len(player.hand_card_ids)

    outcome = _place(bus, state, player, [target])

    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    me = _me(state, player)
    assert len(me.hand_card_ids) == hand_before  # no card draw
    assert me.followup_restriction["kind"] == "buy"
    assert state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision.decision_type == "buy_dope" and decision.can_pass
    assert {o.payload["hood_id"] for o in decision.options} == {target}

    declined = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id, player_id=player.player_id, expected_revision=state.revision
        ),
    )
    assert isinstance(declined, CommandSuccess), declined
    assert _me(declined.state, player).followup_restriction is None
    assert declined.state.active_step != ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS

    pawn_id = decision.options[0].payload["pawn_id"]
    bought = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, target),),
        ),
    )
    assert isinstance(bought, CommandSuccess), bought
    assert _me(bought.state, player).followup_restriction is None


def test_stash_buy_refuses_a_pawn_that_was_not_just_placed(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_then_buy")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    (target,) = _free_hoods(state, player, 1)
    state.board.hoods[target].dope_stack = [DopeType.RANA]
    state.board.hoods[target].cop_ids.clear()
    state = _place(bus, state, player, [target]).state
    old_pawn = next(
        pid
        for pid in player.pawn_ids
        if state.pawns[pid].role == PawnRole.CRIMINAL
        and state.pawns[pid].location.hood_id != target
    )
    home = state.pawns[old_pawn].location.hood_id
    state.board.hoods[home].dope_stack = [DopeType.RANA]
    state.board.hoods[home].cop_ids.clear()

    outcome = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((old_pawn, home),),
        ),
    )

    assert not isinstance(outcome, CommandSuccess)


def test_badge_hire_corrupts_a_cop_where_a_pawn_was_placed(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_then_corrupt_cop")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    (target,) = _free_hoods(state, player, 1)
    economy.spawn_cop(state, state.board.hoods[target], [])
    cop_id = state.board.hoods[target].cop_ids[-1]
    money = player.money
    price = state.configuration["costs"]["corrupt_officer"]

    state = _place(bus, state, player, [target]).state

    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "badge_hire" and decision.can_pass
    assert cop_id in {o.payload["officer_id"] for o in decision.options}
    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="badge_hire",
            officer_id=cop_id,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert cop_id not in new.board.hoods[target].cop_ids
    assert new.board.officers[cop_id].owner_player_id == player.player_id
    assert _me(new, player).money == money - 2 - price  # placement + corruption


def test_badge_hire_is_skipped_without_a_cop(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_then_corrupt_cop")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    (target,) = _free_hoods(state, player, 1)
    state.board.hoods[target].cop_ids.clear()

    state = _place(bus, state, player, [target]).state

    assert state.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP


def test_expansion_moves_a_placed_pawn_for_free(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_then_move")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    (target,) = _free_hoods(state, player, 1)

    state = _place(bus, state, player, [target]).state

    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "expansion" and decision.can_pass
    option = decision.options[0]
    pawn_id, destination = option.payload["pawn_id"], option.payload["destination_hood_id"]
    assert destination in state.board.hoods[target].adjacent_hood_ids
    money = _me(state, player).money

    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="expansion",
            pawn_id=pawn_id,
            destination_hood_id=destination,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert pawn_id in new.board.hoods[destination].criminal_pawn_ids
    assert pawn_id not in new.board.hoods[target].criminal_pawn_ids
    assert pawn_id in _me(new, player).moved_pawn_ids_this_turn
    assert _me(new, player).money == money  # free
    assert new.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP


def test_decoy_is_mandatory_and_adds_a_cop_where_a_pawn_was_placed(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, player = _placing(game_data, "place_then_decoy")
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    (target,) = _free_hoods(state, player, 1)
    cops_before = len(state.board.hoods[target].cop_ids)

    state = _place(bus, state, player, [target]).state

    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "decoy" and not decision.can_pass
    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            kind="decoy",
            destination_hood_id=target,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    assert len(outcome.state.board.hoods[target].cop_ids) == cops_before + 1
    assert outcome.state.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
