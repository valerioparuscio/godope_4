"""Milestone 5 Stage 4c-bis (Marketing/Stonk, RULES_CANONICAL.md §C3/§C4/
§D3): discarding a card to shift a just-completed Buy/Sell package's own
automatic price step by its Stonk symbols, deferred behind
`ActiveStep.WAITING_FOR_CARD_USAGE` only when the player holds an
eligible card (`stonk_count > 0`) — same "no eligible option, skip
straight through" precedent as Poker's own Gamble-launch offer
(`rules/economy.py::_player_can_launch_poker_for_action`).

The package's own automatic step and a Marketing allocation are
otherwise commutative (both are +/-1 moves on the same track), so the
only way to observe "before" vs "after" timing is via the track's own
clamp behavior — used deliberately in several tests below by pinning the
starting price index to the track's floor.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import BuyDope, PassOptionalStep, PlayMarketingCard
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, PawnRole
from dope_engine.domain.ids import CardId, GameId
from dope_engine.rules import economy, turn_flow
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id=None):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    turn_flow.register_handlers(
        bus, card_contact_by_id=card_contact_by_id, price_tracks=price_tracks
    )
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
        stonk_count_by_card_id=stonk_count_by_card_id or {},
    )
    return bus


def _enter_main_action(state, action_type, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    player.pending_action_type = action_type
    return player


def _first_criminal_pawn_id(state, player):
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)


def _give_marketing_card(game_data, player, stonk_count=2) -> tuple[CardId, dict[CardId, int]]:
    """A real card_id (so `card_contact_by_id` already has an entry for
    it), with its `stonk_count` overridden — same "override a real
    Skill/effect entry for full test control" convention already used
    elsewhere in this suite (e.g. test_skills.py's synthetic effects)."""
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


def test_buy_dope_applies_price_step_immediately_without_eligible_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_index = state.market.price_index_by_dope_type[dope_type]

    outcome = _buy_one(state, bus, player, pawn_id)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE
    assert outcome.state.market.price_index_by_dope_type[dope_type] == starting_index + 1


def test_buy_dope_defers_price_step_when_eligible_card_in_hand(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    _card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_index = state.market.price_index_by_dope_type[dope_type]

    outcome = _buy_one(state, bus, player, pawn_id)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE
    assert new_state.market.price_index_by_dope_type[dope_type] == starting_index
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.pending_marketing_price_steps == {dope_type: 1}


def test_marketing_before_timing_is_clamped_ahead_of_the_packages_own_step(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """A Stonk applied "before" the package's own step, on a price
    already at the track's floor, is a no-op (clamped) before the
    package's own +1 raises it — final index 1."""
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    state.market.price_index_by_dope_type[dope_type] = 0

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
            allocations=((dope_type, -1, True),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.market.price_index_by_dope_type[dope_type] == 1
    assert outcome.state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE


def test_marketing_after_timing_cancels_the_packages_own_step(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """The same -1 Stonk, applied "after" instead, lands once the price
    has already been raised to 1 by the package's own step — final
    index 0, unlike the "before" case above."""
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    state.market.price_index_by_dope_type[dope_type] = 0

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
            allocations=((dope_type, -1, False),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.market.price_index_by_dope_type[dope_type] == 0


def test_marketing_rejects_dope_type_not_in_package(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
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
            allocations=((other_dope_type, 1, True),),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "dope_type_not_in_package"


def test_marketing_rejects_more_allocations_than_stonk_count(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player, stonk_count=1)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]

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
            allocations=((dope_type, 1, True), (dope_type, -1, False)),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "too_many_stonk_allocations"


def test_declining_marketing_still_applies_the_deferred_price_step(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    _card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_index = state.market.price_index_by_dope_type[dope_type]

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
    assert outcome.state.market.price_index_by_dope_type[dope_type] == starting_index + 1
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.pending_marketing_price_steps == {}


def test_marketing_decision_offers_allocations_up_to_stonk_count(
    game_data, price_tracks, link_extra_action_types
) -> None:
    from dope_engine.application.legal_actions import get_legal_decision

    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    card_id, stonk_count_by_card_id = _give_marketing_card(game_data, player, stonk_count=2)
    bus = _bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)

    outcome = _buy_one(state, bus, player, pawn_id)
    assert isinstance(outcome, CommandSuccess), outcome
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
