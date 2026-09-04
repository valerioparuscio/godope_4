from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.application.views import build_player_view
from dope_engine.domain.enums import ActiveStep
from dope_engine.domain.ids import CardId, GameId, HoodId, RaidCardId
from dope_engine.domain.state import (
    LastBrawlOutcome,
    LastPokerMatchOutcome,
    LastRaidOutcome,
    PokerMatchState,
)
from dope_engine.rules.setup import create_initial_state


def test_view_hides_other_players_hand_contents(game_data, price_tracks) -> None:
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    viewer_id = state.player_order[0]
    other_id = state.player_order[1]
    viewer_state = next(p for p in state.players if p.player_id == viewer_id)
    other_state = next(p for p in state.players if p.player_id == other_id)

    view = build_player_view(state, viewer_id, price_tracks)

    assert view.own_hand_card_ids == tuple(viewer_state.hand_card_ids)
    other_public = next(p for p in view.players if p.player_id == other_id)
    assert not hasattr(other_public, "hand_card_ids")
    assert other_public.hand_card_count == len(other_state.hand_card_ids)


def test_view_only_exposes_pending_decision_to_its_own_player(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION  # skip the §D2 Poker-launch offer

    state.pending_decision = get_legal_decision(
        state, state.current_player_id, price_tracks, link_extra_action_types
    )
    other_id = next(p for p in state.player_order if p != state.current_player_id)

    own_view = build_player_view(state, state.current_player_id, price_tracks)
    other_view = build_player_view(state, other_id, price_tracks)

    assert own_view.pending_decision is not None
    assert other_view.pending_decision is None


def test_view_exposes_current_prices_and_board_state(game_data, price_tracks) -> None:
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)

    view = build_player_view(state, state.current_player_id, price_tracks)

    assert set(view.current_price_by_dope_type) == set(price_tracks)
    assert len(view.hoods) == len(state.board.hoods)
    assert len(view.spots) == len(state.board.spots)
    assert len(view.pawns) == len(state.pawns)
    # The board's bank-supply counter (game designer, 2026-08-23) mirrors
    # MarketState.supply_remaining_by_dope_type verbatim.
    assert view.supply_remaining_by_dope_type == state.market.supply_remaining_by_dope_type


def test_view_exposes_the_launched_poker_match_card(game_data, price_tracks) -> None:
    """§D2: a launched Gamble card is public the moment it's played, so
    the frontend can show it (e.g. in the board's Gamble panel) without
    waiting for the match to resolve. At most one match can be open at a
    time (2026-09-04 redesign: one shared Gamble slot per round)."""
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    state.poker.current_match = PokerMatchState(
        match_id="poker_t1_r1",
        launched_by_player_id=state.current_player_id,
        gamble_card_id=CardId("card_081"),
        banco_symbols=(),
    )

    view = build_player_view(state, state.current_player_id, price_tracks)

    assert view.poker_launched_card_id == CardId("card_081")


def test_view_exposes_the_last_resolved_raid_outcome(game_data, price_tracks) -> None:
    """A Raid resolves automatically at end of turn with no player
    decision, so a client can only learn who won by this view field —
    there's no command response moment to catch it from."""
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    escaping = (state.player_order[0], state.player_order[3])
    caught = (state.player_order[1], state.player_order[2])
    state.raids.last_outcome = LastRaidOutcome(
        raid_card_id=RaidCardId("raid_01"),
        escaping_team=escaping,
        caught_team=caught,
        escape_criterion="most_links_with_contacts",
        escaping_team_total=3,
        caught_team_total=1,
        stain_count_applied={caught[0]: 1, caught[1]: 1},
    )

    view = build_player_view(state, state.current_player_id, price_tracks)

    assert view.last_raid_outcome is not None
    assert view.last_raid_outcome.raid_card_id == RaidCardId("raid_01")
    assert view.last_raid_outcome.escaping_team == escaping
    assert view.last_raid_outcome.caught_team == caught
    assert view.last_raid_outcome.escape_criterion == "most_links_with_contacts"
    assert view.last_raid_outcome.escaping_team_total == 3
    assert view.last_raid_outcome.caught_team_total == 1


def test_view_exposes_the_last_resolved_brawl_outcome(game_data, price_tracks) -> None:
    """Same reasoning as the Raid outcome above: a Brawl can resolve
    mid-package (e.g. interrupting a bot's own MoveCriminal) with no
    player-facing command response to carry the result, so a client can
    only learn "who won" from this view field."""
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    winner = state.player_order[0]
    losers = (state.player_order[1], state.player_order[2])
    state.last_brawl_outcome = LastBrawlOutcome(
        hood_id=HoodId("hood_q1"),
        winner_id=winner,
        loser_ids=losers,
        force_by_player_id={winner: 5, losers[0]: 3, losers[1]: 3},
        pawn_count_by_player_id={winner: 5, losers[0]: 3, losers[1]: 3},
        gun_total_by_player_id={winner: 0, losers[0]: 0, losers[1]: 0},
    )

    view = build_player_view(state, state.current_player_id, price_tracks)

    assert view.last_brawl_outcome is not None
    assert view.last_brawl_outcome.hood_id == HoodId("hood_q1")
    assert view.last_brawl_outcome.winner_id == winner
    assert view.last_brawl_outcome.loser_ids == losers
    assert view.last_brawl_outcome.force_by_player_id[winner] == 5


def test_view_exposes_the_last_resolved_poker_outcome(game_data, price_tracks) -> None:
    """Same reasoning as the Raid/Brawl outcomes above: a Poker match
    resolves automatically at round end with no player-facing command
    response to carry the result, so a client can only learn "who won"
    from this view field. Singular (2026-09-04 redesign: at most one
    match can ever be open, so there's never a batch to recap)."""
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    winner = state.player_order[0]
    loser = state.player_order[1]
    state.poker.last_outcome = LastPokerMatchOutcome(
        match_id="poker_t1_r1",
        winner_id=winner,
        tied_ids=(),
        loser_ids=(loser,),
        cash_won=6,
        jackpot_carried=0,
        hands_by_player_id={},
        top_hand_shape="tris",
        arrested_loser_ids=(loser,),
        winner_evolved_to_link=True,
    )

    view = build_player_view(state, state.current_player_id, price_tracks)

    assert view.last_poker_outcome is not None
    assert view.last_poker_outcome.winner_id == winner
    assert view.last_poker_outcome.cash_won == 6
