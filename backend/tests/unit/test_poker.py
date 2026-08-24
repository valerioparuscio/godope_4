"""Milestone 4 (Poker) scenario tests: launching a match, the per-round
and per-turn launch caps, the betting round, reveal restrictions, hand
resolution (clear win, full tie/jackpot carry), and win/loss
consequences (Chip banking, cash, Preti Link evolution, Gambler arrest).

Most tests construct a `PokerMatchState` directly and drive
`poker.enter_poker_phase` (bypassing `LaunchPoker`) for precise control
over the Hood-free, purely symbol-driven ranking logic — mirroring how
tests/unit/test_brawl.py calls `brawl.start_brawl` directly. The launch
tests go through the real `LaunchPoker` command instead, since that's
exactly what they're checking.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import LaunchPoker, PassOptionalStep, PlacePokerBet, PlayPokerCard
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActiveStep, GamePhase, PawnRole, PokerSymbolColor
from dope_engine.domain.ids import ContactId, GameId
from dope_engine.domain.state import GameState, PokerMatchState, find_player
from dope_engine.rules import jail, poker, turn_flow
from dope_engine.rules.setup import create_initial_state

PRETI = ContactId("preti")
ARANCIONE = PokerSymbolColor.ARANCIONE
ROSA = PokerSymbolColor.ROSA


def _bus(game_data, banco_override=None, poker_override=None, stonk_count_by_card_id=None):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    banco_symbols_by_card_id = {c.card_id: c.banco_symbols for c in game_data.customer_cards}
    poker_symbols_by_card_id = {c.card_id: c.poker_symbols for c in game_data.customer_cards}
    if banco_override:
        banco_symbols_by_card_id.update(banco_override)
    if poker_override:
        poker_symbols_by_card_id.update(poker_override)
    poker.register_handlers(
        bus,
        banco_symbols_by_card_id=banco_symbols_by_card_id,
        poker_symbols_by_card_id=poker_symbols_by_card_id,
        card_contact_by_id=card_contact_by_id,
        action_type_by_card_id=action_type_by_card_id,
        stonk_count_by_card_id=stonk_count_by_card_id,
    )
    turn_flow.register_handlers(
        bus, card_contact_by_id=card_contact_by_id, stonk_count_by_card_id=stonk_count_by_card_id
    )
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _preti_card_id(game_data) -> str:
    return next(c.card_id for c in game_data.customer_cards if c.contact_id == PRETI)


def _preti_card_id_for_action(game_data, action_type: str) -> str:
    return next(
        c.card_id
        for c in game_data.customer_cards
        if c.contact_id == PRETI and c.action_type == action_type
    )


def _non_preti_card_id(game_data, *, exclude: set[str] = frozenset()) -> str:
    return next(
        c.card_id
        for c in game_data.customer_cards
        if c.contact_id != PRETI and c.card_id not in exclude
    )


def _put_gambler(state: GameState, pawn_id: str) -> None:
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.GAMBLER
    pawn.location = PawnLocation.den()
    state.board.den_gambler_pawn_ids.append(pawn_id)


def _fresh_pawn(state: GameState, player_index: int) -> str:
    player = state.players[player_index]
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)


def _prepare_for_launch(game_data, state, player, card_id: str) -> None:
    """§D2 (confirmed 2026-08-01): launching is only offered once the
    round's action_type matches the card's own — mirror that
    prerequisite (normally set up by rules/economy.py::
    _handle_choose_action_type) directly, since these tests dispatch
    `LaunchPoker` in isolation."""
    action_type = next(c.action_type for c in game_data.customer_cards if c.card_id == card_id)
    player.pending_action_type = action_type
    player.poker_launch_return_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    state.active_step = ActiveStep.WAITING_FOR_POKER_LAUNCH
    state.current_player_id = player.player_id


# --- launch --------------------------------------------------------------


def test_launch_poker_charges_cashout_creates_match_and_continues_the_round(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    player = find_player(state, player_id)
    card_id = _preti_card_id(game_data)
    player.hand_card_ids = [card_id]
    starting_money = player.money
    _prepare_for_launch(game_data, state, player, card_id)

    command = LaunchPoker(
        game_id=state.game_id,
        player_id=player_id,
        expected_revision=state.revision,
        card_id=card_id,
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert len(new_state.poker.matches_this_turn) == 1
    match = new_state.poker.matches_this_turn[0]
    assert match.launched_by_player_id == player_id
    assert match.gamble_card_id == card_id
    new_player = find_player(new_state, player_id)
    assert new_player.money == starting_money + new_state.configuration["poker_launch_cashout"]
    assert card_id not in new_player.hand_card_ids
    assert new_player.gamble_cards_played_this_round == 1
    # A fresh Criminal went from the Covo straight into the Den.
    assert len(new_state.board.den_gambler_pawn_ids) == 1
    gambler_pawn_id = new_state.board.den_gambler_pawn_ids[0]
    assert new_state.pawns[gambler_pawn_id].owner_player_id == player_id
    assert new_state.pawns[gambler_pawn_id].role == PawnRole.GAMBLER
    # Launching doesn't consume the round: it continues normally.
    assert new_state.active_step != ActiveStep.WAITING_FOR_POKER_LAUNCH
    assert "PokerLaunched" in [type(e).__name__ for e in outcome.events]


def test_launch_poker_rejects_second_gamble_card_same_round(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    player = find_player(state, player_id)
    card_a = _preti_card_id(game_data)
    action_type_a = next(c.action_type for c in game_data.customer_cards if c.card_id == card_a)
    preti_cards = [
        c.card_id
        for c in game_data.customer_cards
        if c.contact_id == PRETI and c.action_type == action_type_a
    ]
    card_b = next(cid for cid in preti_cards if cid != card_a)
    player.hand_card_ids = [card_a, card_b]
    _prepare_for_launch(game_data, state, player, card_a)

    outcome = bus.dispatch(
        state,
        LaunchPoker(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            card_id=card_a,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    # Re-enter the launch offer directly (bypassing the rest of the round)
    # to isolate the per-round cap from turn_flow's own round machinery.
    find_player(state, player_id).pending_action_type = action_type_a
    state.active_step = ActiveStep.WAITING_FOR_POKER_LAUNCH
    state.current_player_id = player_id

    outcome = bus.dispatch(
        state,
        LaunchPoker(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            card_id=card_b,
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "gamble_limit_reached_this_round"


def test_launch_poker_rejects_third_match_same_turn(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    player = find_player(state, player_id)
    preti_cards = [c.card_id for c in game_data.customer_cards if c.contact_id == PRETI][:3]
    player.hand_card_ids = list(preti_cards)
    state.poker.matches_this_turn = [
        PokerMatchState(
            match_id=f"poker_t1_{i}",
            launched_by_player_id=player_id,
            gamble_card_id=preti_cards[i],
            banco_symbols=(ARANCIONE, ARANCIONE, ARANCIONE),
        )
        for i in range(2)
    ]
    _prepare_for_launch(game_data, state, player, preti_cards[2])

    outcome = bus.dispatch(
        state,
        LaunchPoker(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            card_id=preti_cards[2],
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "poker_match_limit_reached_this_turn"


def test_launch_poker_when_den_is_full_still_launches_without_a_gambler(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    player = find_player(state, player_id)
    card_id = _preti_card_id(game_data)
    player.hand_card_ids = [card_id]
    den_capacity = state.configuration["den_capacity"]
    state.board.den_gambler_pawn_ids = [f"filler_{i}" for i in range(den_capacity)]
    _prepare_for_launch(game_data, state, player, card_id)

    outcome = bus.dispatch(
        state,
        LaunchPoker(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            card_id=card_id,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    # The launch itself (cashout, card discard, match creation) still
    # happened; only the "send a fresh Gambler" step was skipped.
    assert len(new_state.poker.matches_this_turn) == 1
    new_player = find_player(new_state, player_id)
    assert card_id not in new_player.hand_card_ids
    assert len(new_state.board.den_gambler_pawn_ids) == state.configuration["den_capacity"]


# --- resuming into a still-eligible Marketing offer (2026-08-24) ----------
# A Buy/Sell round eligible for *both* a Poker launch (a matching Preti
# card) and Marketing (a Stonk card) used to lose the Marketing offer
# entirely — economy.py's own `_handle_choose_action_type` only ever
# offered one or the other. Fixed by chaining into Marketing once the
# Poker offer resolves, via `turn_flow.resume_after_poker_launch_offer`
# (game designer, reported: "no Marketing offer after buying/selling and
# launching a Poker").


def test_launching_poker_then_offers_marketing_if_still_eligible(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    player = find_player(state, player_id)
    preti_card_id = _preti_card_id_for_action(game_data, "buy_dope")
    stonk_card_id = _non_preti_card_id(game_data, exclude={preti_card_id})
    player.hand_card_ids = [preti_card_id, stonk_card_id]
    bus = _bus(game_data, stonk_count_by_card_id={stonk_card_id: 2})
    _prepare_for_launch(game_data, state, player, preti_card_id)

    outcome = bus.dispatch(
        state,
        LaunchPoker(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            card_id=preti_card_id,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    new_player = find_player(new_state, player_id)
    assert new_state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE
    assert new_player.marketing_offer_is_pre is True
    assert new_player.poker_launch_return_step is None


def test_declining_poker_then_offers_marketing_if_still_eligible(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    player = find_player(state, player_id)
    preti_card_id = _preti_card_id_for_action(game_data, "buy_dope")
    stonk_card_id = _non_preti_card_id(game_data, exclude={preti_card_id})
    player.hand_card_ids = [preti_card_id, stonk_card_id]
    bus = _bus(game_data, stonk_count_by_card_id={stonk_card_id: 2})
    _prepare_for_launch(game_data, state, player, preti_card_id)

    outcome = bus.dispatch(
        state,
        PassOptionalStep(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE


def test_launching_poker_without_a_stonk_card_skips_marketing_as_before(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    player = find_player(state, player_id)
    preti_card_id = _preti_card_id_for_action(game_data, "buy_dope")
    player.hand_card_ids = [preti_card_id]
    bus = _bus(game_data)
    _prepare_for_launch(game_data, state, player, preti_card_id)

    outcome = bus.dispatch(
        state,
        LaunchPoker(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            card_id=preti_card_id,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS


# --- betting ---------------------------------------------------------------


def test_place_poker_bet_rejects_more_bets_than_own_gamblers(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.players[0].player_id
    _put_gambler(state, _fresh_pawn(state, 0))
    state.poker.matches_this_turn = [
        PokerMatchState(
            match_id="m0",
            launched_by_player_id=player_id,
            gamble_card_id="card_x",
            banco_symbols=(ARANCIONE, ARANCIONE, ARANCIONE),
        ),
        PokerMatchState(
            match_id="m1",
            launched_by_player_id=player_id,
            gamble_card_id="card_y",
            banco_symbols=(ROSA, ROSA, ROSA),
        ),
    ]
    state.phase = GamePhase.POKER_PHASE
    state.active_step = ActiveStep.WAITING_FOR_POKER_BETS
    state.current_player_id = player_id

    outcome = bus.dispatch(
        state,
        PlacePokerBet(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            match_ids=("m0", "m1"),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "not_enough_gamblers"


def test_place_poker_bet_rejects_not_enough_revealable_cards(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.players[0].player_id
    player = find_player(state, player_id)
    _put_gambler(state, _fresh_pawn(state, 0))
    _put_gambler(state, _fresh_pawn(state, 0))
    player.hand_card_ids = [_preti_card_id(game_data)]  # only a Preti card: 0 revealable
    state.poker.matches_this_turn = [
        PokerMatchState(
            match_id="m0",
            launched_by_player_id=player_id,
            gamble_card_id="card_x",
            banco_symbols=(ARANCIONE, ARANCIONE, ARANCIONE),
        )
    ]
    state.phase = GamePhase.POKER_PHASE
    state.active_step = ActiveStep.WAITING_FOR_POKER_BETS
    state.current_player_id = player_id

    outcome = bus.dispatch(
        state,
        PlacePokerBet(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            match_ids=("m0",),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "not_enough_cards_to_reveal"


# --- reveal + resolution ---------------------------------------------------


def _setup_two_bettor_match(game_data, state, *, banco, card_a_symbols, card_b_symbols):
    """player_0 and player_1 each get a Gambler and one hand card whose
    `poker_symbols` are overridden so the resulting 5-symbol hand is
    fully deterministic. Returns (bus, match, card_a_id, card_b_id)."""
    player_0 = find_player(state, state.players[0].player_id)
    player_1 = find_player(state, state.players[1].player_id)
    card_a = _non_preti_card_id(game_data)
    card_b = _non_preti_card_id(game_data, exclude={card_a})
    player_0.hand_card_ids = [card_a]
    player_1.hand_card_ids = [card_b]
    _put_gambler(state, _fresh_pawn(state, 0))
    _put_gambler(state, _fresh_pawn(state, 1))

    bus = _bus(game_data, poker_override={card_a: card_a_symbols, card_b: card_b_symbols})
    match = PokerMatchState(
        match_id="m0",
        launched_by_player_id=player_0.player_id,
        gamble_card_id=_preti_card_id(game_data),
        banco_symbols=banco,
    )
    state.poker.matches_this_turn = [match]
    state.phase = GamePhase.POKER_PHASE

    events: list = []
    poker.enter_poker_phase(state, events)
    return bus, match, card_a, card_b


def _place_all_bets(bus, state):
    while state.active_step == ActiveStep.WAITING_FOR_POKER_BETS:
        current = state.current_player_id
        outcome = bus.dispatch(
            state,
            PlacePokerBet(
                game_id=state.game_id,
                player_id=current,
                expected_revision=state.revision,
                match_ids=("m0",),
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state
    return state


def _reveal_all_cards(bus, state, card_id_by_player):
    """Reveals in whichever order `current_player_id` actually dictates
    (rotation from `first_player_id`, not necessarily seat order) —
    `card_id_by_player` maps every bettor to the card they hold."""
    outcome = None
    while state.active_step == ActiveStep.WAITING_FOR_POKER_CARD:
        current = state.current_player_id
        outcome = bus.dispatch(
            state,
            PlayPokerCard(
                game_id=state.game_id,
                player_id=current,
                expected_revision=state.revision,
                match_id="m0",
                card_ids=(card_id_by_player[current],),
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state
    return state, outcome


def test_clear_winner_gets_cash_chip_and_link_evolution_loser_is_arrested(game_data) -> None:
    state, _ = _new_game(game_data)
    bus, match, card_a, card_b = _setup_two_bettor_match(
        game_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ARANCIONE, ARANCIONE),  # -> 4 ARANCIONE + 1 ROSA: "poker"
        card_b_symbols=(ROSA, ROSA),  # -> 2 ARANCIONE + 3 ROSA: "full"
    )
    player_0_id = state.players[0].player_id
    player_1_id = state.players[1].player_id
    state = _place_all_bets(bus, state)
    assert state.active_step == ActiveStep.WAITING_FOR_POKER_CARD

    state, outcome = _reveal_all_cards(bus, state, {player_0_id: card_a, player_1_id: card_b})

    resolved_events = [e for e in outcome.events if type(e).__name__ == "PokerMatchResolved"]
    assert len(resolved_events) == 1
    resolved = resolved_events[0]
    assert resolved.winner_id == player_0_id
    assert resolved.tied_ids == ()
    assert resolved.loser_ids == (player_1_id,)
    assert resolved.cash_won == state.configuration["poker_win_cash_per_chip"] * 2

    winner = find_player(state, player_0_id)
    loser = find_player(state, player_1_id)
    assert winner.base_inventory.poker_chip_count == 1
    assert loser.base_inventory.poker_chip_count == 0
    assert winner.player_id not in [
        state.pawns[pid].owner_player_id for pid in state.board.den_gambler_pawn_ids
    ]
    winner_link_pawns = [
        pid
        for pid in winner.pawn_ids
        if state.pawns[pid].role == PawnRole.LINK and state.pawns[pid].contact_id == PRETI
    ]
    assert len(winner_link_pawns) == 1
    loser_rat_pawns = [pid for pid in loser.pawn_ids if state.pawns[pid].role == PawnRole.RAT]
    assert len(loser_rat_pawns) == 1
    assert loser_rat_pawns[0] not in state.board.den_gambler_pawn_ids


def test_second_defeated_gambler_is_arrested_right_after_the_first_triggers_evasion(
    game_data,
) -> None:
    """§A1/§C5 (confirmed by the game designer, 2026-08-02, resolving
    RULES_PENDING.md #15): the Jail is never actually "full" at the
    moment a Gambler needs arresting — with Jail at 5 and 2 Poker
    losers, the first loser's arrest is the 6th Rat and triggers Evasion
    immediately (`rules/jail.py::arrest_pawn`), emptying all 6 slots
    back to 0 before that same call returns; the second loser's arrest
    then lands cleanly in the now-empty slot 0. The per-loser loop in
    `rules/poker.py::_resolve_match` already re-checks
    `jail.has_free_rat_slot` fresh for every arrest (not once up front),
    so this was already correct — this test locks in the exact scenario
    as a named regression."""
    state, _ = _new_game(game_data)
    filler_pawn_ids = state.players[3].pawn_ids[:5]
    events: list = []
    for pawn_id in filler_pawn_ids:
        jail.arrest_pawn(state, pawn_id, events)
    assert jail.has_free_rat_slot(state)  # exactly 1 of 6 slots still open

    player_0 = find_player(state, state.players[0].player_id)
    player_1 = find_player(state, state.players[1].player_id)
    player_2 = find_player(state, state.players[2].player_id)
    card_a = _non_preti_card_id(game_data)
    card_b = _non_preti_card_id(game_data, exclude={card_a})
    card_c = _non_preti_card_id(game_data, exclude={card_a, card_b})
    player_0.hand_card_ids = [card_a]
    player_1.hand_card_ids = [card_b]
    player_2.hand_card_ids = [card_c]
    _put_gambler(state, _fresh_pawn(state, 0))
    _put_gambler(state, _fresh_pawn(state, 1))
    _put_gambler(state, _fresh_pawn(state, 2))

    bus = _bus(
        game_data,
        poker_override={
            card_a: (ARANCIONE, ARANCIONE),  # -> 4 ARANCIONE + 1 ROSA: "poker" (winner)
            card_b: (ROSA, ROSA),  # -> 2 ARANCIONE + 3 ROSA: "full" (loser)
            card_c: (ROSA, ROSA),  # -> same "full": tied loser
        },
    )
    match = PokerMatchState(
        match_id="m0",
        launched_by_player_id=player_0.player_id,
        gamble_card_id=_preti_card_id(game_data),
        banco_symbols=(ARANCIONE, ARANCIONE, ROSA),
    )
    state.poker.matches_this_turn = [match]
    state.phase = GamePhase.POKER_PHASE
    enter_events: list = []
    poker.enter_poker_phase(state, enter_events)

    state = _place_all_bets(bus, state)
    state, outcome = _reveal_all_cards(
        bus,
        state,
        {player_0.player_id: card_a, player_1.player_id: card_b, player_2.player_id: card_c},
    )

    resolved = next(e for e in outcome.events if type(e).__name__ == "PokerMatchResolved")
    assert set(resolved.loser_ids) == {player_1.player_id, player_2.player_id}
    assert any(type(e).__name__ == "JailEscapeTriggered" for e in outcome.events)
    # player_0's own hand ("poker", the winning shape) names the whole
    # match's top_hand_shape — the two tied losers' own "full" shape
    # never surfaces there, only on their own hands_by_player_id entry.
    assert resolved.top_hand_shape == "poker"
    assert set(resolved.arrested_loser_ids) == {player_1.player_id, player_2.player_id}
    assert resolved.winner_evolved_to_link is True
    last_outcome = state.poker.last_outcomes[-1]
    assert last_outcome.top_hand_shape == "poker"
    assert set(last_outcome.arrested_loser_ids) == {player_1.player_id, player_2.player_id}
    assert last_outcome.hands_by_player_id[player_0.player_id].count(ARANCIONE) == 4
    assert last_outcome.hands_by_player_id[player_1.player_id].count(ROSA) == 3
    for pawn_id in filler_pawn_ids:
        assert state.pawns[pawn_id].role == PawnRole.IN_BASE

    # Whichever loser was processed first became the 6th Rat and evolved
    # straight into a Politici Link instead of staying a Rat (§A1); the
    # other landed as a plain Rat in the now-empty Jail's slot 0.
    loser_1 = find_player(state, player_1.player_id)
    loser_2 = find_player(state, player_2.player_id)
    loser_pawns = [
        state.pawns[pid]
        for player in (loser_1, loser_2)
        for pid in player.pawn_ids
        if state.pawns[pid].role in (PawnRole.RAT, PawnRole.LINK)
    ]
    rats = [p for p in loser_pawns if p.role == PawnRole.RAT]
    evolved = [p for p in loser_pawns if p.role == PawnRole.LINK]
    assert len(rats) == 1
    assert len(evolved) == 1
    assert evolved[0].contact_id == "politici"
    assert evolved[0].link_level == 1
    assert state.jail.slots[0].rat_pawn_id == rats[0].pawn_id
    for slot in state.jail.slots[1:]:
        assert slot.rat_pawn_id is None


def test_full_tie_carries_jackpot_to_next_match_without_naming_a_winner(game_data) -> None:
    state, _ = _new_game(game_data)
    bus, match, card_a, card_b = _setup_two_bettor_match(
        game_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        # -> ARANCIONE,ARANCIONE,ROSA,ROSA,ROSA: full (3 ROSA/2 ARANCIONE)
        card_a_symbols=(ROSA, ROSA),
        card_b_symbols=(ROSA, ROSA),  # -> identical multiset: exact tie
    )
    player_0_id = state.players[0].player_id
    player_1_id = state.players[1].player_id
    state = _place_all_bets(bus, state)

    state, outcome = _reveal_all_cards(bus, state, {player_0_id: card_a, player_1_id: card_b})

    resolved = next(e for e in outcome.events if type(e).__name__ == "PokerMatchResolved")
    assert resolved.winner_id is None
    assert set(resolved.tied_ids) == {player_0_id, player_1_id}
    assert resolved.loser_ids == ()
    assert state.poker.pending_jackpot_chips == 2

    p0 = find_player(state, player_0_id)
    p1 = find_player(state, player_1_id)
    assert p0.base_inventory.poker_chip_count == 0
    assert p1.base_inventory.poker_chip_count == 0
    # Neither tied bettor's Gambler was touched (no win, no loss).
    assert len(state.board.den_gambler_pawn_ids) == 2


def test_winner_chip_count_is_capped_at_three(game_data) -> None:
    state, _ = _new_game(game_data)
    bus, match, card_a, card_b = _setup_two_bettor_match(
        game_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ARANCIONE, ARANCIONE),
        card_b_symbols=(ROSA, ROSA),
    )
    player_0_id = state.players[0].player_id
    player_1_id = state.players[1].player_id
    find_player(state, player_0_id).base_inventory.poker_chip_count = 3
    state = _place_all_bets(bus, state)

    state, _ = _reveal_all_cards(bus, state, {player_0_id: card_a, player_1_id: card_b})

    winner = find_player(state, player_0_id)
    assert winner.base_inventory.poker_chip_count == 3


def test_cannot_reveal_a_preti_gamble_card(game_data) -> None:
    state, _ = _new_game(game_data)
    bus, match, card_a, card_b = _setup_two_bettor_match(
        game_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ARANCIONE, ARANCIONE),
        card_b_symbols=(ROSA, ROSA),
    )
    state = _place_all_bets(bus, state)
    revealer = state.current_player_id
    preti_card_id = _preti_card_id(game_data)
    find_player(state, revealer).hand_card_ids.append(preti_card_id)

    outcome = bus.dispatch(
        state,
        PlayPokerCard(
            game_id=state.game_id,
            player_id=revealer,
            expected_revision=state.revision,
            match_id="m0",
            card_ids=(preti_card_id,),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "cannot_reveal_gamble_card"


# --- Preti-1: reveal 2 cards, choose 2 of the 4 symbols --------------------


def _setup_one_bettor_match(game_data, state, *, banco, card_a_symbols, card_b_symbols):
    """player_0 gets a Gambler and 2 hand cards with overridden
    `poker_symbols`, for testing the Preti-1 2-card reveal in isolation
    (no second bettor to compete against)."""
    player_0 = find_player(state, state.players[0].player_id)
    card_a = _non_preti_card_id(game_data)
    card_b = _non_preti_card_id(game_data, exclude={card_a})
    player_0.hand_card_ids = [card_a, card_b]
    _put_gambler(state, _fresh_pawn(state, 0))

    bus = _bus(game_data, poker_override={card_a: card_a_symbols, card_b: card_b_symbols})
    match = PokerMatchState(
        match_id="m0",
        launched_by_player_id=player_0.player_id,
        gamble_card_id=_preti_card_id(game_data),
        banco_symbols=banco,
    )
    state.poker.matches_this_turn = [match]
    state.phase = GamePhase.POKER_PHASE

    events: list = []
    poker.enter_poker_phase(state, events)
    return bus, match, card_a, card_b


def test_revealing_two_cards_without_the_skill_is_rejected(game_data) -> None:
    state, _ = _new_game(game_data)
    bus, match, card_a, card_b = _setup_one_bettor_match(
        game_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ARANCIONE, ROSA),
        card_b_symbols=(ROSA, ROSA),
    )
    state = _place_all_bets(bus, state)
    player_id = state.current_player_id

    outcome = bus.dispatch(
        state,
        PlayPokerCard(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            match_id="m0",
            card_ids=(card_a, card_b),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "cannot_reveal_two_cards"


def test_preti_1_reveal_two_cards_then_choose_symbols_end_to_end(game_data) -> None:
    """§A10 Preti-1: reveals both hand cards at once (both discarded
    immediately, matching the normal single-card case), pauses at
    WAITING_FOR_POKER_SYMBOL_CHOICE with all 4 symbols available, then
    picks 2 that *aren't* just "both symbols of one card" — proving the
    choice can genuinely mix symbols from the two revealed cards."""
    from dope_engine.domain.commands import ChoosePokerSymbols
    from dope_engine.domain.ids import SkillId

    state, _ = _new_game(game_data)
    bus, match, card_a, card_b = _setup_one_bettor_match(
        game_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ARANCIONE, PokerSymbolColor.VERDE),
        card_b_symbols=(PokerSymbolColor.GRIGIO, ROSA),
    )
    player_0 = find_player(state, state.players[0].player_id)
    player_0.skill_ids = [SkillId("skill_preti_1")]
    state = _place_all_bets(bus, state)
    player_id = state.current_player_id
    assert player_id == player_0.player_id

    reveal_outcome = bus.dispatch(
        state,
        PlayPokerCard(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            match_id="m0",
            card_ids=(card_a, card_b),
        ),
    )
    assert isinstance(reveal_outcome, CommandSuccess), reveal_outcome
    from dope_engine.domain.events import SkillEffectApplied

    assert {e.skill_id for e in reveal_outcome.events if isinstance(e, SkillEffectApplied)} == {
        SkillId("skill_preti_1")
    }
    state = reveal_outcome.state

    assert state.active_step == ActiveStep.WAITING_FOR_POKER_SYMBOL_CHOICE
    assert state.current_player_id == player_id
    pending = state.poker.pending_symbol_choice
    assert pending is not None
    assert pending.match_id == "m0"
    assert pending.player_id == player_id
    assert set(pending.available_symbols) == {
        ARANCIONE,
        PokerSymbolColor.VERDE,
        PokerSymbolColor.GRIGIO,
        ROSA,
    }
    new_player = find_player(state, player_id)
    assert card_a not in new_player.hand_card_ids
    assert card_b not in new_player.hand_card_ids

    # Mix one symbol from each revealed card instead of keeping a card's
    # own original pair together.
    chosen = (ARANCIONE, PokerSymbolColor.GRIGIO)
    choice_outcome = bus.dispatch(
        state,
        ChoosePokerSymbols(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            match_id="m0",
            chosen_symbols=chosen,
        ),
    )
    assert isinstance(choice_outcome, CommandSuccess), choice_outcome
    state = choice_outcome.state

    assert state.poker.pending_symbol_choice is None
    chosen_event = next(
        e for e in choice_outcome.events if type(e).__name__ == "PokerSymbolsChosen"
    )
    assert chosen_event.player_id == player_id
    assert chosen_event.chosen_symbols == chosen
    # Single bettor, nothing left to reveal -> match resolution completes
    # and `finish_poker_phase` clears `matches_this_turn`; the resolved
    # outcome lands in `last_outcomes` instead.
    assert state.active_step != ActiveStep.WAITING_FOR_POKER_SYMBOL_CHOICE
    assert state.active_step != ActiveStep.WAITING_FOR_POKER_CARD
    assert len(state.poker.last_outcomes) == 1
    assert state.poker.last_outcomes[0].match_id == "m0"


def test_play_poker_card_decision_offers_two_selections_with_the_skill(
    game_data, price_tracks, link_extra_action_types
) -> None:
    from dope_engine.application.legal_actions import get_legal_decision
    from dope_engine.domain.ids import SkillId

    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}

    state, _ = _new_game(game_data)
    bus, match, card_a, card_b = _setup_one_bettor_match(
        game_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ARANCIONE, ARANCIONE),
        card_b_symbols=(ROSA, ROSA),
    )
    state = _place_all_bets(bus, state)

    without_skill = get_legal_decision(
        state,
        state.current_player_id,
        price_tracks,
        link_extra_action_types,
        card_contact_by_id=card_contact_by_id,
    )
    assert without_skill is not None
    assert without_skill.decision_type == "play_poker_card"
    assert without_skill.min_selections == 1
    assert without_skill.max_selections == 1

    # `_place_all_bets` dispatches through the command bus, which returns
    # a fresh state each time (never mutates in place) -- must re-fetch
    # the player from the *current* `state`, not the one captured before.
    player_0 = find_player(state, state.current_player_id)
    player_0.skill_ids = [SkillId("skill_preti_1")]
    with_skill = get_legal_decision(
        state,
        state.current_player_id,
        price_tracks,
        link_extra_action_types,
        card_contact_by_id=card_contact_by_id,
    )
    assert with_skill is not None
    assert with_skill.decision_type == "play_poker_card"
    assert with_skill.min_selections == 1
    assert with_skill.max_selections == 2
    offered_card_ids = {o.payload["card_id"] for o in with_skill.options}
    assert offered_card_ids == {card_a, card_b}


def test_choose_poker_symbols_rejects_a_symbol_not_among_the_four_revealed(game_data) -> None:
    from dope_engine.domain.commands import ChoosePokerSymbols
    from dope_engine.domain.ids import SkillId

    state, _ = _new_game(game_data)
    bus, match, card_a, card_b = _setup_one_bettor_match(
        game_data,
        state,
        banco=(ARANCIONE, ARANCIONE, ROSA),
        card_a_symbols=(ARANCIONE, ARANCIONE),
        card_b_symbols=(ROSA, ROSA),
    )
    player_0 = find_player(state, state.players[0].player_id)
    player_0.skill_ids = [SkillId("skill_preti_1")]
    state = _place_all_bets(bus, state)
    player_id = state.current_player_id

    reveal_outcome = bus.dispatch(
        state,
        PlayPokerCard(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            match_id="m0",
            card_ids=(card_a, card_b),
        ),
    )
    state = reveal_outcome.state

    outcome = bus.dispatch(
        state,
        ChoosePokerSymbols(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            match_id="m0",
            chosen_symbols=(ARANCIONE, PokerSymbolColor.VERDE),  # VERDE never revealed
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "symbol_not_available"
