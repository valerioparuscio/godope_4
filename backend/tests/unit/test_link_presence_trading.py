"""CLAUDE.md §11.4/§11.5/§11.6 + game designer (2026-08-15): a Link counts
as presence in every Hood of its own Contact for Buy/Sell eligibility,
exactly like it already did for Cop/Fed corruption (rules/officers.py).
Buy Dope needs a genuine per-Hood choice (each of a Contact's 2 Hoods has
its own independent stock/price — BuyDope.purchases now carries
(pawn_id, hood_id) pairs instead of bare pawn_ids); Sell Dope doesn't
(Spots are Contact-, not Hood-scoped, so both Hoods share the same 2
Spots — SellDope.sales is unchanged).
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import BuyDope, SellDope
from dope_engine.domain.enums import ActionType, ActiveStep, PawnRole
from dope_engine.domain.ids import ContactId, GameId
from dope_engine.rules import economy, links
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


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


def _enter_main_action(state, action_type, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    player.pending_action_type = action_type
    return player


def _make_link(state, player, contact_id, level=1):
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    links.insert_link(state, player.player_id, pawn_id, contact_id, level, [])
    return pawn_id


def _contact_hood_ids(state, contact_id):
    return [hood_id for hood_id, hood in state.board.hoods.items() if hood.contact_id == contact_id]


# --- BuyDope via a Link -----------------------------------------------


def test_buy_dope_options_offer_both_of_a_links_hoods(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    contact_id = ContactId("artisti")
    link_pawn_id = _make_link(state, player, contact_id)
    hood_ids = _contact_hood_ids(state, contact_id)
    assert len(hood_ids) == 2
    for hood_id in hood_ids:
        hood = state.board.hoods[hood_id]
        hood.cop_ids = []
        if not hood.dope_stack:
            # Unrevealed Hoods start with no stock at all (only revealed
            # by a Criminal entering) — stock it directly so both of this
            # Link's Hoods are genuinely buyable, same as
            # test_economy.py's own "set up a Hood's stock by hand"
            # convention.
            hood.dope_stack = [next(iter(price_tracks))]

    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)

    assert decision is not None
    assert decision.decision_type == "buy_dope"
    link_options = [o for o in decision.options if o.payload["pawn_id"] == link_pawn_id]
    assert {o.payload["hood_id"] for o in link_options} == set(hood_ids)


def test_random_legal_bot_never_double_buys_through_the_same_link(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Regression (2026-08-16): a Link's 2 Hood options for "buy_dope"
    are both real, distinct DecisionOptions for the *same* pawn_id
    (previous test) — RandomLegalBot's old `_pick_cheapest_options`
    didn't dedupe by pawn (only "move_criminal"/"sell_dope" ever needed
    that before), so if both of a Link's options landed among the
    cheapest, it could pick both and produce a BuyDope with the same
    pawn twice, which the command bus rejects with
    duplicate_pawn_in_targets — hit in the full-game bot sweep
    (tools/run_full_test_game.py, seed 317). Uses a hand-built decision
    (both of a Link's options priced cheapest, so a naive cost-sort pick
    would grab both) rather than a real board state.

    Updated (2026-08-16, second fix): `_pick_buy_dope_options` now also
    budgets each Hood's real stock from `view.hoods` (see
    `_buy_dope_options`'s own docstring), so this needs real Hood ids
    with real stock from the actual initial state instead of the
    fabricated "hood_a"/"hood_b"/"hood_c" this test used before — an
    unknown Hood id would otherwise budget to 0 stock and get skipped."""
    from dope_engine.application.views import build_player_view
    from dope_engine.bots.random_legal import RandomLegalBot
    from dope_engine.domain.decisions import DecisionOption, PendingDecision

    state, _ = _new_game(game_data)
    view = build_player_view(state, state.current_player_id, price_tracks)
    hood_a, hood_b, hood_c = (h.hood_id for h in view.hoods[:3])
    link_pawn_id = "pawn_link_x"
    other_pawn_id = "pawn_criminal_y"
    decision = PendingDecision(
        decision_id="decision_test",
        player_id=state.current_player_id,
        decision_type="buy_dope",
        prompt_key="decision.buy_dope.prompt",
        options=(
            DecisionOption(
                option_id="buy_link_hood_a",
                label_key="decision.buy_dope.option",
                payload={
                    "pawn_id": link_pawn_id,
                    "hood_id": hood_a,
                    "dope_type": "rana",
                    "price": 1,
                },
            ),
            DecisionOption(
                option_id="buy_link_hood_b",
                label_key="decision.buy_dope.option",
                payload={
                    "pawn_id": link_pawn_id,
                    "hood_id": hood_b,
                    "dope_type": "rana",
                    "price": 1,
                },
            ),
            DecisionOption(
                option_id="buy_other",
                label_key="decision.buy_dope.option",
                payload={
                    "pawn_id": other_pawn_id,
                    "hood_id": hood_c,
                    "dope_type": "rana",
                    "price": 5,
                },
            ),
        ),
        min_selections=2,
        max_selections=2,
        can_pass=True,
    )

    command = RandomLegalBot().choose(view, decision)

    assert isinstance(command, BuyDope)
    pawn_ids = [pid for pid, _hood_id in command.purchases]
    assert len(pawn_ids) == len(set(pawn_ids)), command.purchases


def test_buy_dope_via_link_pawn_succeeds(game_data, price_tracks, link_extra_action_types) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    contact_id = ContactId("artisti")
    link_pawn_id = _make_link(state, player, contact_id)
    hood_id = _contact_hood_ids(state, contact_id)[0]
    hood = state.board.hoods[hood_id]
    hood.cop_ids = []
    dope_type = hood.dope_stack[-1]
    starting_count = player.base_inventory.dope_counts.get(dope_type, 0)

    outcome = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((link_pawn_id, hood_id),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.base_inventory.dope_counts.get(dope_type, 0) == starting_count + 1


def test_buy_dope_via_link_rejects_hood_outside_its_contact(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    link_pawn_id = _make_link(state, player, ContactId("artisti"))
    other_hood_id = _contact_hood_ids(state, ContactId("studenti"))[0]

    outcome = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((link_pawn_id, other_hood_id),),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "pawn_not_eligible"


# --- SellDope via a Link ------------------------------------------------


def test_sell_dope_options_offered_for_a_link_pawn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    contact_id = ContactId("artisti")
    link_pawn_id = _make_link(state, player, contact_id)
    for spot in state.board.spots.values():
        if spot.contact_id == contact_id:
            player.base_inventory.dope_counts[spot.accepted_dope_type] = 1

    decision = get_legal_decision(state, player.player_id, price_tracks, link_extra_action_types)

    assert decision is not None
    assert decision.decision_type == "sell_dope"
    assert any(o.payload["pawn_id"] == link_pawn_id for o in decision.options)


def test_sell_dope_via_link_pawn_succeeds(game_data, price_tracks, link_extra_action_types) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    contact_id = ContactId("artisti")
    link_pawn_id = _make_link(state, player, contact_id)
    spot = next(s for s in state.board.spots.values() if s.contact_id == contact_id)
    player.base_inventory.dope_counts[spot.accepted_dope_type] = 1
    starting_money = player.money

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((link_pawn_id, spot.accepted_dope_type),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money > starting_money
    assert new_player.base_inventory.dope_counts[spot.accepted_dope_type] == 0


def test_sell_dope_via_link_does_not_offer_evolution(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """PROVISIONAL (RULES_PENDING.md): a sale sourced entirely from a
    Link (already a Link, not a Criminal) never queues/triggers the
    evolve-to-Link offer — the rulebook only ever describes a *Criminal*
    converting into a Link."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    contact_id = ContactId("artisti")
    link_pawn_id = _make_link(state, player, contact_id)
    spot = next(s for s in state.board.spots.values() if s.contact_id == contact_id)
    player.base_inventory.dope_counts[spot.accepted_dope_type] = 1

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((link_pawn_id, spot.accepted_dope_type),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_state.active_step != ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE
    assert new_player.pending_sale_link_evolutions == []
