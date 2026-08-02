"""Milestone 5 Stage 4c-bis (Marketing/Stonk, RULES_CANONICAL.md §C3/§C4/
§D3, corrected 2026-08-02): discarding a card to shift prices by its
Stonk symbols either *before* the whole Buy/Sell action (offered right
after `ChooseActionType`, any Dope type — no package exists yet) or
*after* it has fully resolved, including its own automatic price step
(offered at the tail of `BuyDope`/`SellDope`, restricted to the Dope
types the package actually handled). A normal player gets one or the
other, never both in the same action.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import (
    BuyDope,
    ChooseActionType,
    PassOptionalStep,
    PlayMarketingCard,
)
from dope_engine.domain.enums import ActiveStep, DopeType, PawnRole
from dope_engine.domain.ids import CardId, GameId
from dope_engine.rules import economy, turn_flow
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id=None):
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
        stonk_count_by_card_id=stonk_count_by_card_id or {},
    )
    return bus


def _enter_choose_action_type(state):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = 1
    player.pending_action_type = None
    return player


def _choose_buy_dope(bus, state, player):
    return bus.dispatch(
        state,
        ChooseActionType(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action_type="buy_dope",
        ),
    )


def _first_criminal_pawn_id(state, player):
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)


def _give_marketing_card(game_data, player, stonk_count=2) -> tuple[CardId, dict[CardId, int]]:
    """A real card_id (so `card_contact_by_id` already has an entry for
    it), with its `stonk_count` overridden — same "override a real
    Skill/effect entry for full test control" convention used elsewhere
    in this suite (e.g. test_skills.py's synthetic effects)."""
    card_id = game_data.customer_cards[0].card_id
    if card_id not in player.hand_card_ids:
        player.hand_card_ids.append(card_id)
    return card_id, {card_id: stonk_count}


def _buy_one(state, bus, player, pawn_id):
    return bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            pawn_ids=(pawn_id,),
        ),
    )


# --- no eligible card: unaffected -----------------------------------------


def test_choose_action_type_does_not_offer_marketing_without_eligible_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_choose_action_type(state)

    outcome = _choose_buy_dope(bus, state, player)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS


def test_buy_dope_applies_price_step_immediately_without_eligible_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_choose_action_type(state)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    player = next(p for p in state.players if p.player_id == player.player_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_index = state.market.price_index_by_dope_type[dope_type]

    outcome = _buy_one(state, bus, player, pawn_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE
    assert outcome.state.market.price_index_by_dope_type[dope_type] == starting_index + 1


# --- "before": offered right after ChooseActionType, any Dope type --------


def test_choose_action_type_offers_marketing_before_with_eligible_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)

    outcome = _choose_buy_dope(bus, state, player)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.marketing_offer_is_pre is True


def test_marketing_before_shifts_price_immediately_and_resumes_targets(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    dope_type = next(iter(price_tracks))
    state.market.price_index_by_dope_type[dope_type] = 2

    outcome = bus.dispatch(
        state,
        PlayMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_id,
            allocations=((dope_type, -1),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    assert new_state.market.price_index_by_dope_type[dope_type] == 1
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.marketing_pre_allocations == ((dope_type, -1),)


def test_declining_marketing_before_resumes_targets_without_shifting_price(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    _card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    dope_type = next(iter(price_tracks))
    starting_index = state.market.price_index_by_dope_type[dope_type]

    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    assert new_state.market.price_index_by_dope_type[dope_type] == starting_index
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.marketing_pre_allocations == ()


# --- "after": offered at the package's tail, restricted to its Dope types -


def test_buy_dope_offers_marketing_after_when_before_was_not_used(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    # Decline "before" so "after" is still available.
    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
        ),
    )
    state = outcome.state
    player = next(p for p in state.players if p.player_id == player.player_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_index = state.market.price_index_by_dope_type[dope_type]

    outcome = _buy_one(state, bus, player, pawn_id)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.marketing_offer_is_pre is False
    assert new_player.marketing_eligible_dope_types == [dope_type]
    # The package's own step already applied — "after" only adds on top.
    assert new_state.market.price_index_by_dope_type[dope_type] == starting_index + 1


def test_buy_dope_does_not_offer_marketing_after_when_before_was_used(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player, stonk_count=1)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    dope_type = next(iter(price_tracks))
    outcome = bus.dispatch(
        state,
        PlayMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_id,
            allocations=((dope_type, 1),),
        ),
    )
    state = outcome.state
    player = next(p for p in state.players if p.player_id == player.player_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)

    outcome = _buy_one(state, bus, player, pawn_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.marketing_pre_allocations == ()


def test_marketing_rejects_dope_type_not_in_package(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
        ),
    )
    state = outcome.state
    player = next(p for p in state.players if p.player_id == player.player_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    other_dope_type = next(dt for dt in DopeType if dt != dope_type)

    outcome = _buy_one(state, bus, player, pawn_id)
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    outcome = bus.dispatch(
        state,
        PlayMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_id,
            allocations=((other_dope_type, 1),),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "dope_type_not_in_package"


def test_marketing_rejects_more_allocations_than_stonk_count(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player, stonk_count=1)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    dope_type = next(iter(price_tracks))

    outcome = bus.dispatch(
        state,
        PlayMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_id,
            allocations=((dope_type, 1), (dope_type, -1)),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "too_many_stonk_allocations"


def test_declining_marketing_after_still_finishes_the_action(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    _card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
        ),
    )
    state = outcome.state
    player = next(p for p in state.players if p.player_id == player.player_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)

    outcome = _buy_one(state, bus, player, pawn_id)
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE

    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE


def test_marketing_decision_offers_allocations_up_to_stonk_count(
    game_data, price_tracks, link_extra_action_types
) -> None:
    from dope_engine.application.legal_actions import get_legal_decision

    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player, stonk_count=2)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state

    decision = get_legal_decision(
        state,
        player.player_id,
        price_tracks,
        link_extra_action_types,
        stonk_count_by_card_id=stonk_count_by_card_id,
    )

    assert decision is not None
    assert decision.decision_type == "play_marketing_card"
    assert decision.can_pass is True
    assert decision.min_selections == 0
    assert decision.max_selections == 2
    assert all(o.payload["card_id"] == card_id for o in decision.options)
    # "before": unrestricted, every Dope type in the game is offered.
    offered_types = {o.payload["dope_type"] for o in decision.options}
    assert offered_types == {dt.value for dt in price_tracks}
