"""Rissa cards of the 2026-10 set (game designer, 2026-10-15): 22 "RIOT SQUAD" (+2 Guns per Cop
already in the Hood), 33/34 "FALL GUY" (losers to Jail instead of a hidden Hood), 35 "STREET
CRED" (the winner's Link takes level 3), 36 "AFTERSHOCK" (corrupt the Cop that enters) and 37
"FOLLOW ME" (place a Criminal here for free, asked last)."""

from test_brawl import (
    HOOD,
    _bus,
    _declare_no_cards,
    _enter_main_action,
    _fresh_pawns,
    _new_game,
    _put_criminal,
)

from dope_engine.application.command_bus import CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import (
    ChooseBrawlLinkEvolution,
    ChooseBrawlLoserReward,
    ChooseBrawlRelocationDestination,
    PassOptionalStep,
    ResolveMoveFollowup,
)
from dope_engine.domain.enums import ActionType, ActiveStep, PawnRole
from dope_engine.rules import brawl, economy, move_followups


def _brawl_setup(game_data, price_tracks, link_extra_action_types, boost):
    """Player 0 (with `boost` active) has 2 Criminals in HOOD, player 1 has 1; both HOOD and
    every other Hood revealed, so a Rissa needs no relocation choice."""
    state, _ = _new_game(game_data)
    for hood in state.board.hoods.values():
        hood.revealed = True
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    move_followups.register_handlers(bus)
    p0, p1 = state.players[0].player_id, state.players[1].player_id
    state.current_player_id = p0
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    player.active_card_boost = {**boost, "action_types": ["move_criminal"]}
    for pid in _fresh_pawns(state, 0, 2):
        _put_criminal(state, pid, HOOD)
    for pid in _fresh_pawns(state, 1, 2):
        _put_criminal(state, pid, HOOD)
    return state, bus, p0, p1


def _run_brawl(state, bus, p0, p1):
    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p0, [], events)
    state, _ = _declare_no_cards(bus, state, len(state.pending_brawl.participants))
    return state


def _answer_reward(bus, state, winner, loser):
    return bus.dispatch(
        state,
        ChooseBrawlLoserReward(
            game_id=state.game_id,
            player_id=winner,
            expected_revision=state.revision,
            loser_player_id=loser,
            reward_type="money",
        ),
    )


def _decline_link_evolution(bus, state, winner):
    return bus.dispatch(
        state,
        ChooseBrawlLinkEvolution(
            game_id=state.game_id,
            player_id=winner,
            expected_revision=state.revision,
            pawn_id=None,
        ),
    )


def test_riot_squad_adds_two_guns_for_each_cop_already_in_the_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, bus, p0, p1 = _brawl_setup(
        game_data,
        price_tracks,
        link_extra_action_types,
        {"type": "provoker_gun_bonus_per_cop", "amount": 2},
    )
    for _ in range(2):
        economy.spawn_cop(state, state.board.hoods[HOOD], [])

    state = _run_brawl(state, bus, p0, p1)

    outcome = state.last_brawl_outcome
    assert outcome.gun_total_by_player_id[p0] == 4  # two Cops x 2 Guns
    assert outcome.gun_total_by_player_id[p1] == 0


def test_fall_guy_sends_the_loser_to_jail_and_still_gives_the_reward(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, bus, p0, p1 = _brawl_setup(
        game_data, price_tracks, link_extra_action_types, {"type": "brawl_losers_to_jail"}
    )
    state.players[0].money = 10
    state.players[1].money = 10
    state = _run_brawl(state, bus, p0, p1)
    assert state.pending_brawl.winner_id == p0 and state.pending_brawl.loser_ids == [p1]

    outcome = _answer_reward(bus, state, p0, p1)
    assert isinstance(outcome, CommandSuccess), outcome
    assert next(p for p in outcome.state.players if p.player_id == p0).money > 10  # the reward
    outcome = _decline_link_evolution(bus, outcome.state, p0)

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert new.pending_brawl is None  # no relocation step
    loser_rats = [
        pid
        for pid in next(p for p in new.players if p.player_id == p1).pawn_ids
        if new.pawns[pid].role == PawnRole.RAT
    ]
    assert len(loser_rats) == 1
    assert sum(1 for s in new.jail.slots if s.rat_pawn_id is not None) == 1
    assert len([pid for pid in new.board.hoods[HOOD].criminal_pawn_ids]) == 3


def test_street_cred_gives_the_winner_a_level_3_link(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, bus, p0, p1 = _brawl_setup(
        game_data,
        price_tracks,
        link_extra_action_types,
        {"type": "brawl_win_link_level", "level": 3},
    )
    state = _run_brawl(state, bus, p0, p1)
    state = _answer_reward(bus, state, p0, p1).state
    winner_pawn = next(
        pid for pid in state.board.hoods[HOOD].criminal_pawn_ids
        if state.pawns[pid].owner_player_id == p0
    )

    outcome = bus.dispatch(
        state,
        ChooseBrawlLinkEvolution(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            pawn_id=winner_pawn,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    pawn = outcome.state.pawns[winner_pawn]
    assert pawn.role == PawnRole.LINK and pawn.link_level == 3
    assert pawn.contact_id == state.board.hoods[HOOD].contact_id


def _finish_to_followups(state, bus, p0, p1):
    state = _run_brawl(state, bus, p0, p1)
    state = _answer_reward(bus, state, p0, p1).state
    state = _decline_link_evolution(bus, state, p0).state
    outcome = bus.dispatch(
        state,
        ChooseBrawlRelocationDestination(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            hood_id=None,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    return outcome.state


def test_aftershock_lets_the_winner_corrupt_the_cop_that_enters(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, bus, p0, p1 = _brawl_setup(
        game_data, price_tracks, link_extra_action_types, {"type": "brawl_win_corrupt_cop"}
    )
    state.players[0].money = 30
    state = _finish_to_followups(state, bus, p0, p1)
    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = get_legal_decision(state, p0, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "aftershock" and decision.can_pass
    officer_id = decision.options[0].payload["officer_id"]
    assert officer_id in state.board.hoods[HOOD].cop_ids
    price = state.configuration["costs"]["corrupt_officer"]
    money_before = next(p for p in state.players if p.player_id == p0).money

    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            kind="aftershock",
            officer_id=officer_id,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    assert officer_id not in new.board.hoods[HOOD].cop_ids
    assert new.board.officers[officer_id].owner_player_id == p0
    assert next(p for p in new.players if p.player_id == p0).money == money_before - price
    assert new.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP


def test_aftershock_is_not_offered_without_the_money(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, bus, p0, p1 = _brawl_setup(
        game_data, price_tracks, link_extra_action_types, {"type": "brawl_win_corrupt_cop"}
    )
    state.players[0].money = 0
    state = _finish_to_followups(state, bus, p0, p1)

    assert state.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP


def test_follow_me_asks_last_and_places_a_free_criminal_with_a_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, bus, p0, p1 = _brawl_setup(
        game_data, price_tracks, link_extra_action_types, {"type": "brawl_win_free_place"}
    )
    state.players[0].money = 20
    state = _finish_to_followups(state, bus, p0, p1)
    assert state.active_step == ActiveStep.WAITING_FOR_MOVE_FOLLOWUP
    decision = get_legal_decision(state, p0, price_tracks, link_extra_action_types)
    assert decision.context["followup"] == "follow_me" and decision.can_pass
    player = next(p for p in state.players if p.player_id == p0)
    hand_before = len(player.hand_card_ids)
    money_before = player.money
    pawns_before = len(state.board.hoods[HOOD].criminal_pawn_ids)

    outcome = bus.dispatch(
        state,
        ResolveMoveFollowup(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            kind="follow_me",
            destination_hood_id=HOOD,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new = outcome.state
    after = next(p for p in new.players if p.player_id == p0)
    assert after.money == money_before  # free
    assert len(after.hand_card_ids) == hand_before + 1  # the normal placement draw
    assert len(new.board.hoods[HOOD].criminal_pawn_ids) == pawns_before + 1


def test_follow_me_can_be_declined(game_data, price_tracks, link_extra_action_types) -> None:
    state, bus, p0, p1 = _brawl_setup(
        game_data, price_tracks, link_extra_action_types, {"type": "brawl_win_free_place"}
    )
    state = _finish_to_followups(state, bus, p0, p1)
    pawns_before = len(state.board.hoods[HOOD].criminal_pawn_ids)

    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id, player_id=p0, expected_revision=state.revision
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert len(outcome.state.board.hoods[HOOD].criminal_pawn_ids) == pawns_before
    assert outcome.state.active_step != ActiveStep.WAITING_FOR_MOVE_FOLLOWUP

