import pytest

from dope_engine.application.command_bus import CommandFailure
from dope_engine.application.legal_actions import build_command_from_selection
from dope_engine.application.views import PlayerGameView
from dope_engine.domain.decisions import PendingDecision
from dope_engine.domain.enums import ControllerType, GameStatus
from dope_engine.domain.ids import GameId
from dope_engine.domain.invariants import validate_invariants
from dope_engine.rules.setup import SeatConfig, solo_seats


def _select_first_legal_option_ids(
    decision: PendingDecision, view: PlayerGameView
) -> tuple[str, ...]:
    """Like "always pick the first option(s)", but deduped by pawn for the
    decision types where a single pawn can appear in more than one option
    (see bots/random_legal.py's docstring for why plain slicing isn't safe
    there). `buy_dope` also needs a real per-Hood stock + money + Covo
    room (2026-08-27: adding the Covo-room budget here too, mirroring
    test_http_app.py's own `_select_options`, after a Den-move fix
    elsewhere shifted this suite's RNG-consumed path enough to newly hit
    the gap), `sell_dope` a per-Dope-type inventory + per-Spot capacity
    budget (2026-08-27: a card boost's `trade_price_delta` sell bonus
    shifted this suite's own RNG-consumed path enough to newly hit this
    gap too — same missing budget test_http_app.py's own `_select_options`
    already needed for `sell_dope`), and `maneuver_officer` a
    same-officer dedup — all three generators (2026-08-16/17) stopped
    budgeting those at generation time, so plain "first N,
    already-cheapest-sorted" slicing can pick options that jointly
    oversubscribe a Hood/Covo/Dope-type/Spot or double-target one
    officer, same as `bots/random_legal.py`'s own pickers had to start
    doing."""
    count = decision.max_selections
    dedup_types = ("move_criminal", "sell_dope", "buy_dope", "maneuver_officer")
    if decision.decision_type not in dedup_types:
        return tuple(o.option_id for o in decision.options[:count])

    hood_stock = None
    money = None
    covo_room = None
    if decision.decision_type == "buy_dope":
        hood_stock = {h.hood_id: len(h.dope_stack) for h in view.hoods}
        buyer = next(p for p in view.players if p.player_id == decision.player_id)
        money = buyer.money
        covo_room = {
            dope_type: 3 - amount for dope_type, amount in buyer.base_inventory.dope_counts.items()
        }

    dope_budget = None
    spot_capacity = None
    if decision.decision_type == "sell_dope":
        seller = next(p for p in view.players if p.player_id == decision.player_id)
        dope_budget = dict(seller.base_inventory.dope_counts)
        spot_capacity = {s.spot_id: s.capacity - len(s.sold_dope_tokens) for s in view.spots}

    used_officer_ids: set[str] = set()
    chosen: list[str] = []
    used_pawn_ids: set[str] = set()
    for option in decision.options:
        pawn_id = option.payload["pawn_id"]
        if pawn_id in used_pawn_ids:
            continue
        if decision.decision_type == "maneuver_officer":
            officer_id = option.payload["officer_id"]
            if officer_id in used_officer_ids:
                continue
            used_officer_ids.add(officer_id)
        if hood_stock is not None:
            hood_id = option.payload["hood_id"]
            if hood_stock.get(hood_id, 0) <= 0:
                continue
            assert covo_room is not None
            dope_type = option.payload["dope_type"]
            if covo_room.get(dope_type, 3) <= 0:
                continue
            price = option.payload["price"]
            assert money is not None
            if price > money:
                continue
            hood_stock[hood_id] -= 1
            covo_room[dope_type] = covo_room.get(dope_type, 3) - 1
            money -= price
        if dope_budget is not None:
            assert spot_capacity is not None
            dope_type = option.payload["dope_type"]
            spot_id = option.payload["spot_id"]
            if dope_budget.get(dope_type, 0) <= 0 or spot_capacity.get(spot_id, 0) <= 0:
                continue
            dope_budget[dope_type] -= 1
            spot_capacity[spot_id] -= 1
        used_pawn_ids.add(pawn_id)
        chosen.append(option.option_id)
        if len(chosen) == count:
            break
    return tuple(chosen)


def test_create_game_lands_on_first_players_decision(game_service) -> None:
    result = game_service.create_game(game_id=GameId("g"), seed=1, human_seat=0)

    assert result.state.pending_decision is not None
    assert result.state.pending_decision.player_id == result.state.current_player_id


def test_advance_stops_at_human_turn_and_plays_bots_otherwise(game_service) -> None:
    result = game_service.create_game(game_id=GameId("g"), seed=1, human_seat=0)
    state = result.state

    result = game_service.advance(state)
    state = result.state

    human = next(p for p in state.players if p.controller_type is ControllerType.HUMAN)
    assert state.status is not GameStatus.FINISHED
    assert state.current_player_id == human.player_id
    assert state.pending_decision is not None
    assert state.pending_decision.player_id == human.player_id


def test_single_player_segments_end_after_every_bot_action(game_service) -> None:
    """Game designer, 2026-10-06: a bot's Grit action and its Link extra
    action are narrated and revealed one after the other, so a segment
    never holds more than one chosen action type."""
    from dope_engine.domain.events import ActionTypeChosen

    state = game_service.create_game(game_id=GameId("seg"), seed=3, human_seat=3).state
    human = next(p for p in state.players if p.controller_type is ControllerType.HUMAN)
    segments = 0
    for _ in range(200):
        if state.current_player_id == human.player_id or state.status is GameStatus.FINISHED:
            break
        result = game_service.advance(state, single_player_segment=True)
        state = result.state
        segments += 1
        chosen = [e for e in result.events if isinstance(e, ActionTypeChosen)]
        assert len(chosen) <= 1
    assert state.current_player_id == human.player_id
    # 3 bots x 1 round: well over 3 segments only if actions are cut apart.
    assert segments >= 3


def test_full_game_completes_via_service_with_human_picking_first_option(game_service) -> None:
    result = game_service.create_game(game_id=GameId("g"), seed=7, human_seat=2)
    state = result.state
    result = game_service.advance(state)
    state = result.state

    steps = 0
    while state.status is not GameStatus.FINISHED and steps < 200:
        steps += 1
        decision = state.pending_decision
        assert decision is not None
        view = game_service.view_for(state, decision.player_id)
        option_ids = _select_first_legal_option_ids(decision, view)
        command = build_command_from_selection(view, decision, option_ids)

        outcome = game_service.dispatch(state, command)
        assert not isinstance(outcome, CommandFailure), outcome
        state = outcome.state
        validate_invariants(state)

        result = game_service.advance(state)
        state = result.state

    assert state.status is GameStatus.FINISHED
    assert state.turn_index == 3
    assert state.final_score is not None
    assert len(state.final_score.winner_ids) >= 1


def test_bot_only_game_completes_deterministically(game_data):
    from dope_engine.application.game_service import GameService
    from dope_engine.bots.random_legal import RandomLegalBot

    service = GameService(game_data, bot_policy=RandomLegalBot())
    result = service.create_game(game_id=GameId("g"), seed=99, human_seat=0)
    state = result.state

    # Force every seat to BOT so advance() drives the whole game unattended.
    for player in state.players:
        player.controller_type = ControllerType.BOT

    result = service.advance(state, max_steps=1000)
    state = result.state

    assert state.status is GameStatus.FINISHED
    assert state.turn_index == 3
    assert state.final_score is not None
    assert len(state.final_score.winner_ids) >= 1


def test_a_poker_launch_marketing_or_link_spend_each_end_their_segment(game_service) -> None:
    """Game designer, 2026-10-16: a bot's Poker launch, Marketing card and Link spent for an
    extra action are separate steps, narrated and shown on the board one by one — so a segment
    never holds two of them."""
    from dope_engine.domain.events import (
        LinkSpentForExtraAction,
        MarketingCardPlayed,
        PokerLaunched,
    )

    step_events = (PokerLaunched, MarketingCardPlayed, LinkSpentForExtraAction)
    seen = 0
    for seed in range(1, 40):
        state = game_service.create_game(game_id=GameId(f"s{seed}"), seed=seed, human_seat=3).state
        for _ in range(200):
            if state.current_player_id == state.players[3].player_id or (
                state.status is GameStatus.FINISHED
            ):
                break
            result = game_service.advance(state, single_player_segment=True)
            state = result.state
            count = sum(isinstance(e, step_events) for e in result.events)
            seen += count
            assert count <= 1
    assert seen > 0


# --- explicit seats (multiplayer) ----------------------------------------


def test_create_game_from_solo_seats_equals_create_game(game_service) -> None:
    solo = game_service.create_game(game_id=GameId("a"), seed=9, human_seat=1, human_nickname="Ana")
    seated = game_service.create_game_from_seats(
        game_id=GameId("a"), seed=9, seats=solo_seats(4, 1, "Ana")
    )

    assert solo.state == seated.state
    assert solo.events == seated.events


def _seats_with_humans(humans: int) -> list[SeatConfig]:
    return [
        SeatConfig(ControllerType.HUMAN, f"Human {i + 1}")
        if i < humans
        else SeatConfig(ControllerType.BOT, f"Bot {i + 1}")
        for i in range(4)
    ]


def test_advance_stops_at_every_human_seat_not_only_the_first(game_service) -> None:
    state = game_service.create_game_from_seats(
        game_id=GameId("mp"), seed=4, seats=_seats_with_humans(4)
    ).state

    # With four humans there is nothing for advance() to play: it hands the first decision over.
    result = game_service.advance(state)

    assert result.state is state and result.events == ()
    decision = state.pending_decision
    assert decision is not None
    decider = next(p for p in state.players if p.player_id == decision.player_id)
    assert decider.controller_type is ControllerType.HUMAN


@pytest.mark.parametrize("humans", [2, 3, 4])
def test_full_game_with_several_human_seats_completes(game_service, humans) -> None:
    state = game_service.create_game_from_seats(
        game_id=GameId(f"mp{humans}"), seed=13 + humans, seats=_seats_with_humans(humans)
    ).state
    human_ids = {p.player_id for p in state.players if p.controller_type is ControllerType.HUMAN}
    humans_who_acted: set[str] = set()

    state = game_service.advance(state).state
    steps = 0
    while state.status is not GameStatus.FINISHED and steps < 400:
        steps += 1
        decision = state.pending_decision
        assert decision is not None
        # advance() only ever stops on a human decision.
        assert decision.player_id in human_ids
        humans_who_acted.add(decision.player_id)
        view = game_service.view_for(state, decision.player_id)
        command = build_command_from_selection(
            view, decision, _select_first_legal_option_ids(decision, view)
        )
        outcome = game_service.dispatch(state, command)
        assert not isinstance(outcome, CommandFailure), outcome
        state = outcome.state
        validate_invariants(state)
        state = game_service.advance(state).state

    assert state.status is GameStatus.FINISHED
    assert humans_who_acted == human_ids
