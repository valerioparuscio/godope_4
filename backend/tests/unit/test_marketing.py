"""Milestone 5 Stage 4c-bis (Marketing/Stonk, RULES_CANONICAL.md §C3/§C4/
§D3, 2026-08-17 decision): discarding a card to shift prices by its
Stonk symbols, *before* the whole Buy/Sell action only (offered right
after `ChooseActionType`, any Dope type — no package exists yet).
Superseded the earlier 2026-08-02 "before or after" version, which also
offered it *after* the package resolved — removed once playtesting
showed there was never a good reason to reach for "after" instead of
just using it "before". A normal player therefore gets exactly one shot
at Marketing per action, always "before"; Manager-3 is the only
exception (its own automatic replay, tested in test_skills.py).
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import (
    BuyDope,
    ChooseActionType,
    ChooseMarketingCard,
    PassOptionalStep,
    PlayMarketingCard,
)
from dope_engine.domain.enums import ActiveStep, PawnRole
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


def _give_two_marketing_cards(game_data, player) -> tuple[CardId, CardId, dict[CardId, int]]:
    """Two distinct real card_ids, both with Stonk symbols — for testing
    the "which card" choice sub-step (game designer, 2026-08-15), only
    offered with 2+ eligible cards."""
    card_a = game_data.customer_cards[0].card_id
    card_b = game_data.customer_cards[1].card_id
    for card_id in (card_a, card_b):
        if card_id not in player.hand_card_ids:
            player.hand_card_ids.append(card_id)
    return card_a, card_b, {card_a: 3, card_b: 1}


def _buy_one(state, bus, player, pawn_id):
    hood_id = state.pawns[pawn_id].location.hood_id
    return bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, hood_id),),
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


# --- no "after" offer (2026-08-17): declining/skipping "before" just ------
# --- finishes the action, Marketing is gone for this action instance ------


def test_buy_dope_never_offers_marketing_after_declining_before(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Declining "before" (previous 2026-08-02 behavior offered a second
    chance "after" the package) now simply finishes the action once the
    package resolves — Marketing was a one-shot "before" offer, and it
    was just declined."""
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
    starting_index = state.market.price_index_by_dope_type[dope_type]

    outcome = _buy_one(state, bus, player, pawn_id)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.marketing_pre_allocations == ()
    # Only the package's own automatic price step applied, nothing more.
    assert new_state.market.price_index_by_dope_type[dope_type] == starting_index + 1
    assert card_id in new_player.hand_card_ids


def test_buy_dope_finishes_directly_when_before_was_used(
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


def test_marketing_before_allows_splitting_stonks_across_two_dope_types(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """"si può fare dividendo gli stonk fra 2 merci a scelta" (game
    designer, 2026-08-17): with a 2-Stonk card, the allocations can
    freely span 2 *different* Dope types in the same play, not just
    stack both on one — `dope_type_not_in_package` no longer exists as a
    rejection reason now that "before" (unrestricted) is the only offer
    point left."""
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player, stonk_count=2)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    dope_type_a, dope_type_b = list(price_tracks)[:2]
    state.market.price_index_by_dope_type[dope_type_a] = 2
    state.market.price_index_by_dope_type[dope_type_b] = 2

    outcome = bus.dispatch(
        state,
        PlayMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_id,
            allocations=((dope_type_a, -1), (dope_type_b, 1)),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.market.price_index_by_dope_type[dope_type_a] == 1
    assert new_state.market.price_index_by_dope_type[dope_type_b] == 3


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


# --- "which card": a real choice with 2+ eligible cards (2026-08-15) ------


def test_marketing_offers_a_card_choice_with_two_eligible_cards(
    game_data, price_tracks, link_extra_action_types
) -> None:
    from dope_engine.application.legal_actions import get_legal_decision

    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_a, card_b, stonk_count_by_card_id = _give_two_marketing_cards(game_data, player)
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
    assert decision.decision_type == "choose_marketing_card"
    assert decision.can_pass is True
    assert decision.min_selections == 0
    assert decision.max_selections == 1
    assert {o.payload["card_id"] for o in decision.options} == {card_a, card_b}


def test_choosing_a_marketing_card_restricts_the_allocation_step_to_it(
    game_data, price_tracks, link_extra_action_types
) -> None:
    from dope_engine.application.legal_actions import get_legal_decision

    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_a, card_b, stonk_count_by_card_id = _give_two_marketing_cards(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_b,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.marketing_chosen_card_id == card_b
    assert new_state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE

    decision = get_legal_decision(
        new_state,
        player.player_id,
        price_tracks,
        link_extra_action_types,
        stonk_count_by_card_id=stonk_count_by_card_id,
    )
    assert decision is not None
    assert decision.decision_type == "play_marketing_card"
    assert decision.max_selections == stonk_count_by_card_id[card_b]
    assert all(o.payload["card_id"] == card_b for o in decision.options)


def test_declining_the_marketing_card_choice_declines_marketing_outright(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    _card_a, _card_b, stonk_count_by_card_id = _give_two_marketing_cards(game_data, player)
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

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.marketing_chosen_card_id is None


def test_choose_marketing_card_rejects_ineligible_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_choose_action_type(state)
    card_a, card_b, stonk_count_by_card_id = _give_two_marketing_cards(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    outcome = _choose_buy_dope(bus, state, player)
    state = outcome.state
    not_in_hand = next(
        c.card_id for c in game_data.customer_cards if c.card_id not in (card_a, card_b)
    )

    outcome = bus.dispatch(
        state,
        ChooseMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=not_in_hand,
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "card_not_eligible_for_marketing"
