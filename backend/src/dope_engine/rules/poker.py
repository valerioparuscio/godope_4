"""Poker (RULES_CANONICAL.md §D2): launching a match with a Preti
"Gamble" card (`LaunchPoker`), the single end-of-turn betting round
covering every match launched that turn (`PlacePokerBet`), and each
match's own card-reveal + resolution (`PlayPokerCard`).

**Launch** happens during ACTION_PHASE, immediately after `ChooseActionType`
(`rules/economy.py::_handle_choose_action_type`) — but only when the
player holds a Preti "Gamble" card whose own `action_type` matches the
action (main or Link extra) just chosen for this round ("si associa ad
un'azione base", confirmed 2026-08-01). Accepting or declining
(`PassOptionalStep`) resumes target selection exactly where it was
interrupted, via `PlayerState.poker_launch_return_step`. Capped at 1
Gamble card per round (`gamble_cards_played_this_round`, independent of
the extra action's own per-turn cap) and 2 matches per turn
(`state.poker.matches_this_turn`).

**Betting** happens once, at the start of POKER_PHASE, for the whole
turn's batch of matches together: each player with at least one own
Gambler in the Den (in rotation order from `first_player_id`) chooses,
in one command, which of the open matches to stake a Chip on — up to as
many as they have Gamblers in the Den. `state.poker`'s `pending_bettor_*`
fields track whose turn it is.

**Reveal + resolution** then walks the matches in launch order; for
each one with at least one bettor, every bettor (same rotation order)
reveals one hand card — any *non*-Preti card (independent of the
Gamble-card limit): a Preti "Gamble" card has no `poker_symbols` of its
own to contribute (only a launch card's `banco_symbols` do), so
revealing one would short the hand to 3 symbols instead of 5 — to build
their personal 5-symbol hand: the match's shared 3-symbol banco plus
their own revealed card's 2 symbols. A match with no bettors just
fizzles. The same `pending_bettor_*` fields are reused, now scoped to
"who still needs to reveal for the match currently being resolved"
(`state.poker.resolving_match_index`).

Confirmed by the game designer (2026-08-01):
- Chips: `base_inventory.poker_chip_count` (0-3, chips currently banked
  in the Covo) only ever goes *up* on a win (capped at 3) and never
  down on a loss — a losing bet's Chip simply isn't banked, exactly
  representing "returns to where it was before". Betting is never
  gated by chip count (3 always suffices for the ≤2 matches that can
  ever exist); the real gate is Den Gambler count, per the rules text.
- Revealing a card to bet is independent of the "1 Gamble card per
  Round" launch limit.
- A launcher may also bet on their own match.
- If the Den is full when launching, the launch still happens (cashout
  + card discard), just without a new Gambler.
- Tie-break within the same hand-shape category: compare the dominant
  color first (the repeated group — the 4 in Poker, the Tripla in
  Full/Tris, the higher Coppia in Doppia Coppia, the Coppia in Coppia),
  then the remaining (non-dominant) symbols in colour-rank order.

PROVISIONAL calls (docs/rules/RULES_PENDING.md #13-15): "5 uguali" beats
"5 diversi" at the top category when they'd otherwise tie (more
repetitions of a dominant colour beats none); an unresolved full tie's
Chips become a colour-blind, player-agnostic jackpot
(`PokerState.pending_jackpot_chips`) credited to whoever wins the *next*
match launched by anyone; a losing Gambler that can't be arrested
(Jail genuinely full) just stays in the Den instead of blocking
resolution.
"""

from __future__ import annotations

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import LaunchPoker, PlacePokerBet, PlayPokerCard
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import (
    ActionType,
    ActiveStep,
    GamePhase,
    PawnRole,
    PokerSymbolColor,
)
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    DomainEvent,
    PokerBetsPlaced,
    PokerCardRevealed,
    PokerLaunched,
    PokerMatchResolved,
)
from dope_engine.domain.ids import CardId, ContactId, PlayerId
from dope_engine.domain.state import GameState, PokerMatchState, find_player
from dope_engine.rules import economy, jail, links, turn_flow
from dope_engine.rules.event_utils import emit as _emit

PRETI_CONTACT_ID = ContactId("preti")


def register_handlers(
    bus: CommandBus,
    *,
    banco_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]],
    poker_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]],
    card_contact_by_id: dict[CardId, ContactId],
    action_type_by_card_id: dict[CardId, ActionType | None],
) -> None:
    bus.register(
        LaunchPoker,
        lambda s, c: _handle_launch_poker(
            s, c, banco_symbols_by_card_id, card_contact_by_id, action_type_by_card_id
        ),
    )
    bus.register(
        PlacePokerBet, lambda s, c: _handle_place_poker_bet(s, c, card_contact_by_id)
    )
    bus.register(
        PlayPokerCard,
        lambda s, c: _handle_play_poker_card(s, c, poker_symbols_by_card_id, card_contact_by_id),
    )


def _validate_own_round(
    state: GameState, player_id: PlayerId, expected_step: ActiveStep
) -> DomainError | None:
    if state.phase != GamePhase.ACTION_PHASE:
        return wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value)
    if state.current_player_id != player_id:
        return wrong_player(str(state.current_player_id), str(player_id))
    if state.active_step != expected_step:
        return DomainError(
            code="wrong_active_step",
            message=f"Not waiting for that step (state is at '{state.active_step.value}').",
            details={"actual_step": state.active_step.value},
        )
    return None


# --- launch --------------------------------------------------------------


def _handle_launch_poker(
    state: GameState,
    command: LaunchPoker,
    banco_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]],
    card_contact_by_id: dict[CardId, ContactId],
    action_type_by_card_id: dict[CardId, ActionType | None],
) -> CommandOutcome:
    error = _validate_own_round(state, command.player_id, ActiveStep.WAITING_FOR_POKER_LAUNCH)
    if error is not None:
        return CommandFailure(error)

    player = find_player(state, command.player_id)
    card_id = command.card_id
    if card_id not in player.hand_card_ids:
        return CommandFailure(
            DomainError(
                code="card_not_in_hand",
                message=f"Card '{card_id}' is not in your hand.",
                details={},
            )
        )
    if card_contact_by_id.get(card_id) != PRETI_CONTACT_ID:
        return CommandFailure(
            DomainError(
                code="not_a_gamble_card",
                message=f"Card '{card_id}' is not a Preti Gamble card.",
                details={},
            )
        )
    # §D2 (confirmed 2026-08-01): only launchable alongside the action
    # this exact card's own action_type indicates — the same check
    # rules/economy.py::_player_can_launch_poker_for_action already made
    # before ever offering this step, repeated here since the client is
    # not trusted.
    if action_type_by_card_id.get(card_id) != player.pending_action_type:
        return CommandFailure(
            DomainError(
                code="card_action_type_mismatch",
                message=f"Card '{card_id}' doesn't match this round's action.",
                details={},
            )
        )
    if (
        player.gamble_cards_played_this_round
        >= state.configuration["poker_max_gamble_cards_per_round"]
    ):
        return CommandFailure(
            DomainError(
                code="gamble_limit_reached_this_round",
                message="Already played a Gamble card this round.",
                details={},
            )
        )
    if len(state.poker.matches_this_turn) >= state.configuration["poker_max_matches_per_turn"]:
        return CommandFailure(
            DomainError(
                code="poker_match_limit_reached_this_turn",
                message="Already launched the maximum Poker matches this turn.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    player.hand_card_ids.remove(card_id)
    state.decks.customer_decks_by_contact[PRETI_CONTACT_ID].discard_pile_card_ids.append(card_id)
    player.gamble_cards_played_this_round += 1
    player.money += state.configuration["poker_launch_cashout"]

    match_id = f"poker_t{state.turn_index}_{len(state.poker.matches_this_turn)}"
    match = PokerMatchState(
        match_id=match_id,
        launched_by_player_id=command.player_id,
        gamble_card_id=card_id,
        banco_symbols=banco_symbols_by_card_id[card_id],
        jackpot_chips=state.poker.pending_jackpot_chips,
    )
    state.poker.pending_jackpot_chips = 0
    state.poker.matches_this_turn.append(match)

    gambler_pawn_id = None
    if len(state.board.den_gambler_pawn_ids) < state.configuration["den_capacity"]:
        fresh = next(
            (pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE), None
        )
        if fresh is not None:
            pawn = state.pawns[fresh]
            pawn.role = PawnRole.GAMBLER
            pawn.location = PawnLocation.den()
            state.board.den_gambler_pawn_ids.append(fresh)
            gambler_pawn_id = fresh
            economy.draw_card(state, PRETI_CONTACT_ID, events, command.player_id)

    _emit(
        state,
        events,
        PokerLaunched,
        player_id=command.player_id,
        match_id=match_id,
        gamble_card_id=card_id,
        banco_symbols=match.banco_symbols,
        gambler_pawn_id=gambler_pawn_id,
    )

    return_step = player.poker_launch_return_step
    assert return_step is not None
    player.poker_launch_return_step = None
    state.active_step = return_step
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- POKER_PHASE entry + betting ------------------------------------------


def _own_gambler_count(state: GameState, player_id: PlayerId) -> int:
    return sum(
        1
        for pid in state.board.den_gambler_pawn_ids
        if state.pawns[pid].owner_player_id == player_id
    )


def _rotation_from_first_player(state: GameState) -> list[PlayerId]:
    start = state.player_order.index(state.first_player_id)
    return state.player_order[start:] + state.player_order[:start]


def enter_poker_phase(state: GameState, events: list[DomainEvent]) -> None:
    if not state.poker.matches_this_turn:
        turn_flow.finish_poker_phase(state, events)
        return

    bettor_order = [
        player_id for player_id in _rotation_from_first_player(state)
        if _own_gambler_count(state, player_id) > 0
    ]
    if not bettor_order:
        _start_match_resolution(state, events)
        return

    state.poker.pending_bettor_order = bettor_order
    state.poker.pending_bettor_index = 0
    state.active_step = ActiveStep.WAITING_FOR_POKER_BETS
    state.current_player_id = bettor_order[0]


def _handle_place_poker_bet(
    state: GameState, command: PlacePokerBet, card_contact_by_id: dict[CardId, ContactId]
) -> CommandOutcome:
    if state.phase != GamePhase.POKER_PHASE:
        return CommandFailure(wrong_phase(GamePhase.POKER_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(
            wrong_player(str(state.current_player_id), str(command.player_id))
        )
    if state.active_step != ActiveStep.WAITING_FOR_POKER_BETS:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message=f"Not waiting for Poker bets (state is at '{state.active_step.value}').",
                details={},
            )
        )

    open_match_ids = {m.match_id for m in state.poker.matches_this_turn}
    if len(set(command.match_ids)) != len(command.match_ids) or not set(
        command.match_ids
    ).issubset(open_match_ids):
        return CommandFailure(
            DomainError(
                code="invalid_bet_targets",
                message="Bet targets must be distinct, open Poker matches.",
                details={"match_ids": list(command.match_ids)},
            )
        )
    max_bets = _own_gambler_count(state, command.player_id)
    if len(command.match_ids) > max_bets:
        return CommandFailure(
            DomainError(
                code="not_enough_gamblers",
                message=f"Only {max_bets} own Gambler(s) in the Den to bet with.",
                details={"max_bets": max_bets},
            )
        )
    player = find_player(state, command.player_id)
    # A bettor reveals a distinct, non-Preti card per match they're
    # staked on (a Preti "Gamble" card has no `poker_symbols` to
    # contribute — see legal_actions.py::_play_poker_card_decision).
    # Validated here, up front, rather than risking a stuck
    # WAITING_FOR_POKER_CARD decision with more matches to reveal for
    # than eligible cards left.
    revealable_card_count = sum(
        1
        for card_id in player.hand_card_ids
        if card_contact_by_id.get(card_id) != PRETI_CONTACT_ID
    )
    if len(command.match_ids) > revealable_card_count:
        return CommandFailure(
            DomainError(
                code="not_enough_cards_to_reveal",
                message="Not enough non-Gamble hand cards to reveal one per match bet on.",
                details={"revealable_card_count": revealable_card_count},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    for match in state.poker.matches_this_turn:
        if match.match_id in command.match_ids:
            match.bets_by_player_id[command.player_id] = 1

    _emit(
        state,
        events,
        PokerBetsPlaced,
        player_id=command.player_id,
        match_ids=command.match_ids,
    )

    state.poker.pending_bettor_index += 1
    if state.poker.pending_bettor_index < len(state.poker.pending_bettor_order):
        state.current_player_id = state.poker.pending_bettor_order[
            state.poker.pending_bettor_index
        ]
    else:
        _start_match_resolution(state, events)

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- reveal + resolution ---------------------------------------------------


def _start_match_resolution(state: GameState, events: list[DomainEvent]) -> None:
    state.poker.resolving_match_index = 0
    state.poker.pending_bettor_order = []
    state.poker.pending_bettor_index = 0
    _advance_match_resolution(state, events)


def _advance_match_resolution(state: GameState, events: list[DomainEvent]) -> None:
    matches = state.poker.matches_this_turn
    while state.poker.resolving_match_index < len(matches):
        match = matches[state.poker.resolving_match_index]
        bettors = [
            player_id
            for player_id in _rotation_from_first_player(state)
            if player_id in match.bets_by_player_id
        ]
        if not bettors:
            state.poker.resolving_match_index += 1
            continue

        unrevealed = [p for p in bettors if p not in match.revealed_symbols_by_player_id]
        if unrevealed:
            state.poker.pending_bettor_order = bettors
            state.poker.pending_bettor_index = bettors.index(unrevealed[0])
            state.active_step = ActiveStep.WAITING_FOR_POKER_CARD
            state.current_player_id = unrevealed[0]
            return

        _resolve_match(state, match, bettors, events)
        state.poker.resolving_match_index += 1

    turn_flow.finish_poker_phase(state, events)


def _handle_play_poker_card(
    state: GameState,
    command: PlayPokerCard,
    poker_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]],
    card_contact_by_id: dict[CardId, ContactId],
) -> CommandOutcome:
    if state.phase != GamePhase.POKER_PHASE:
        return CommandFailure(wrong_phase(GamePhase.POKER_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(
            wrong_player(str(state.current_player_id), str(command.player_id))
        )
    if state.active_step != ActiveStep.WAITING_FOR_POKER_CARD:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message=f"Not waiting for a Poker card reveal (state is at "
                f"'{state.active_step.value}').",
                details={},
            )
        )

    matches = state.poker.matches_this_turn
    match = matches[state.poker.resolving_match_index]
    if command.match_id != match.match_id:
        return CommandFailure(
            DomainError(
                code="wrong_match",
                message=f"'{command.match_id}' is not the match currently resolving.",
                details={},
            )
        )

    player = find_player(state, command.player_id)
    if command.card_id not in player.hand_card_ids:
        return CommandFailure(
            DomainError(
                code="card_not_in_hand",
                message=f"Card '{command.card_id}' is not in your hand.",
                details={},
            )
        )
    if card_contact_by_id.get(command.card_id) == PRETI_CONTACT_ID:
        return CommandFailure(
            DomainError(
                code="cannot_reveal_gamble_card",
                message="A Preti Gamble card has no Poker symbols of its own to reveal.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    symbols = poker_symbols_by_card_id.get(command.card_id, ())
    player.hand_card_ids.remove(command.card_id)
    contact_id = card_contact_by_id[command.card_id]
    state.decks.customer_decks_by_contact[contact_id].discard_pile_card_ids.append(
        command.card_id
    )
    match.revealed_symbols_by_player_id[command.player_id] = symbols

    _emit(
        state,
        events,
        PokerCardRevealed,
        player_id=command.player_id,
        match_id=match.match_id,
        card_id=command.card_id,
        symbols=symbols,
    )

    _advance_match_resolution(state, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


# --- hand ranking ----------------------------------------------------------


def _color_with_count(counts: dict[PokerSymbolColor, int], target: int) -> PokerSymbolColor:
    return next(color for color, count in counts.items() if count == target)


def _hand_score(
    symbols: tuple[PokerSymbolColor, ...], rank_order: list[str], color_order: list[str]
) -> tuple[int, ...]:
    """Lower is better, matching both config lists' own ordering (index
    0 = best rank / best colour) — so `min()` across bettors' scores
    finds the winner(s). See the module docstring for the confirmed
    tie-break algorithm: dominant colour(s) first, then the rest."""
    color_idx = {PokerSymbolColor(c): i for i, c in enumerate(color_order)}
    counts: dict[PokerSymbolColor, int] = {}
    for symbol in symbols:
        counts[symbol] = counts.get(symbol, 0) + 1
    shape_counts = sorted(counts.values(), reverse=True)

    if shape_counts == [5]:
        shape = "five_same_or_diff"
        color_key: tuple[int, ...] = (-5, color_idx[_color_with_count(counts, 5)])
    elif shape_counts == [1, 1, 1, 1, 1]:
        # PROVISIONAL (RULES_PENDING.md #13): "5 diversi" always contains
        # every colour exactly once — there is no dominant colour to
        # rank by, and every rainbow hand is identical to every other.
        shape = "five_same_or_diff"
        color_key = (-1, 0)
    elif shape_counts == [4, 1]:
        shape = "poker"
        color_key = (
            color_idx[_color_with_count(counts, 4)],
            color_idx[_color_with_count(counts, 1)],
        )
    elif shape_counts == [3, 2]:
        shape = "full"
        color_key = (
            color_idx[_color_with_count(counts, 3)],
            color_idx[_color_with_count(counts, 2)],
        )
    elif shape_counts == [3, 1, 1]:
        shape = "tris"
        kickers = sorted(color_idx[c] for c, n in counts.items() if n == 1)
        color_key = (color_idx[_color_with_count(counts, 3)], *kickers)
    elif shape_counts == [2, 2, 1]:
        shape = "two_pair"
        pairs = sorted(color_idx[c] for c, n in counts.items() if n == 2)
        kicker = next(color_idx[c] for c, n in counts.items() if n == 1)
        color_key = (pairs[0], pairs[1], kicker)
    elif shape_counts == [2, 1, 1, 1]:
        shape = "pair"
        kickers = sorted(color_idx[c] for c, n in counts.items() if n == 1)
        color_key = (color_idx[_color_with_count(counts, 2)], *kickers)
    else:  # pragma: no cover - exactly 5 symbols from 5 colours has no other partition
        raise AssertionError(f"Unexpected Poker symbol-count pattern: {shape_counts}")

    return (rank_order.index(shape), *color_key)


def _resolve_match(
    state: GameState, match: PokerMatchState, bettors: list[PlayerId], events: list[DomainEvent]
) -> None:
    rank_order = state.configuration["poker_rank_order"]
    color_order = state.configuration["poker_color_tiebreak_order"]

    scores = {
        player_id: _hand_score(
            match.banco_symbols + match.revealed_symbols_by_player_id[player_id],
            rank_order,
            color_order,
        )
        for player_id in bettors
    }
    best = min(scores.values())
    top = [player_id for player_id in bettors if scores[player_id] == best]
    losers = [player_id for player_id in bettors if player_id not in top]

    cash_won = 0
    jackpot_carried = 0
    winner_id: PlayerId | None = None
    tied_ids: tuple[PlayerId, ...] = ()

    if len(top) == 1:
        winner_id = top[0]
        winner = find_player(state, winner_id)
        winner.poker_matches_won_count += 1  # Milestone 5: Job 3 / Raid 4
        cash_won = state.configuration["poker_win_cash_per_chip"] * (
            len(bettors) + match.jackpot_chips
        )
        winner.money += cash_won
        winner.base_inventory.poker_chip_count = min(3, winner.base_inventory.poker_chip_count + 1)

        winner_gambler = next(
            (
                pid
                for pid in state.board.den_gambler_pawn_ids
                if state.pawns[pid].owner_player_id == winner_id
            ),
            None,
        )
        if winner_gambler is not None:
            state.board.den_gambler_pawn_ids.remove(winner_gambler)
            links.insert_link(state, winner_id, winner_gambler, PRETI_CONTACT_ID, 1, events)
    else:
        # PROVISIONAL (RULES_PENDING.md #14): an unresolved full tie
        # keeps the tied bettors' Gamblers in the Den and their Chips
        # untouched (neither banked nor lost); the stake pool carries
        # forward to whichever match is launched next, by anyone.
        tied_ids = tuple(top)
        jackpot_carried = len(top) + match.jackpot_chips
        state.poker.pending_jackpot_chips += jackpot_carried

    for loser_id in losers:
        loser_gambler = next(
            (
                pid
                for pid in state.board.den_gambler_pawn_ids
                if state.pawns[pid].owner_player_id == loser_id
            ),
            None,
        )
        if loser_gambler is not None and jail.has_free_rat_slot(state):
            state.board.den_gambler_pawn_ids.remove(loser_gambler)
            jail.arrest_pawn(state, loser_gambler, events)

    _emit(
        state,
        events,
        PokerMatchResolved,
        match_id=match.match_id,
        winner_id=winner_id,
        tied_ids=tied_ids,
        loser_ids=tuple(losers),
        cash_won=cash_won,
        jackpot_carried=jackpot_carried,
    )
