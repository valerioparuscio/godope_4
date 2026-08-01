"""Milestone 4 (Rissa) scenario tests: trigger, mid-package pause/resume,
Force calculation (Criminals + Links, Gun self-add/other-subtract),
tie-break, participant eligibility, and the 3 reward sub-steps.

`hood_q2` (Contact "artisti", unrevealed at game start) is used as the
Rissa Hood throughout: it starts genuinely empty (starter Criminals only
ever land on *revealed* Hoods, see rules/setup.py::_place_starting_criminals),
so pre-placing exactly the Criminals a scenario needs gives an exact,
predictable count. `hood_q1` (also "artisti", revealed, adjacent to
hood_q2) is used as a mover's origin.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import (
    AssignBrawlGuns,
    ChooseBrawlLinkEvolution,
    ChooseBrawlLoserReward,
    ChooseBrawlRelocationDestination,
    MoveCriminal,
    PlayBrawlCard,
)
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, PawnRole
from dope_engine.domain.events import BrawlResolved
from dope_engine.domain.ids import ContactId, GameId, HoodId
from dope_engine.rules import brawl, economy, turn_flow
from dope_engine.rules.setup import create_initial_state

ARTISTI = ContactId("artisti")
HOOD = HoodId("hood_q2")
ORIGIN_HOOD = HoodId("hood_q1")


def _bus(game_data, price_tracks, link_extra_action_types, gun_count_by_card_id=None):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    tile_by_id = {t.tile_id: t for t in game_data.board.covered_hood_tiles.tile_values}
    turn_flow.register_handlers(bus, card_contact_by_id=card_contact_by_id)
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
    )
    brawl.register_handlers(
        bus,
        gun_count_by_card_id=gun_count_by_card_id or {},
        card_contact_by_id=card_contact_by_id,
        tile_by_id=tile_by_id,
    )
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _fresh_pawn(state, player_index):
    player = state.players[player_index]
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)


def _fresh_pawns(state, player_index, count):
    """`count` *distinct* still-available pawn ids for this player, all
    resolved against the same state snapshot — unlike calling
    `_fresh_pawn` several times before placing any of them (which would
    return the same id every time, since none of the earlier calls have
    changed anyone's role yet)."""
    player = state.players[player_index]
    available = [pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE]
    return available[:count]


def _put_criminal(state, pawn_id, hood_id):
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.CRIMINAL
    pawn.location = PawnLocation.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)


def _put_link(state, pawn_id, contact_id, level):
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.LINK
    pawn.contact_id = contact_id
    pawn.link_level = level
    pawn.location = PawnLocation.link(contact_id)


def _enter_main_action(state, action_type, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    player.pending_action_type = action_type
    return player


def _declare_no_cards(bus, state, count):
    outcome = None
    for _ in range(count):
        current = state.current_player_id
        outcome = bus.dispatch(
            state,
            PlayBrawlCard(
                game_id=state.game_id,
                player_id=current,
                expected_revision=state.revision,
                card_id=None,
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state
    return state, outcome


# --- trigger -----------------------------------------------------------


def test_fifth_criminal_via_move_starts_multi_participant_brawl(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0, p1, p2 = (state.players[i].player_id for i in range(3))

    for _ in range(3):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    _put_criminal(state, _fresh_pawn(state, 2), HOOD)

    mover_pawn = _fresh_pawn(state, 1)
    _put_criminal(state, mover_pawn, ORIGIN_HOOD)
    state.current_player_id = p1
    _enter_main_action(state, ActionType.MOVE_CRIMINAL, grit_value=1)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=p1,
        expected_revision=state.revision,
        moves=((mover_pawn, HOOD, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.pending_brawl is not None
    progress = new_state.pending_brawl
    assert progress.hood_id == HOOD
    assert set(progress.participants) == {p0, p1, p2}
    assert new_state.active_step == ActiveStep.WAITING_FOR_BRAWL_CARD
    assert "BrawlStarted" in [type(e).__name__ for e in outcome.events]


def test_single_participant_brawl_auto_resolves_without_subflow(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0 = state.players[0].player_id

    for _ in range(4):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    mover_pawn = _fresh_pawn(state, 0)
    _put_criminal(state, mover_pawn, ORIGIN_HOOD)
    state.current_player_id = p0
    _enter_main_action(state, ActionType.MOVE_CRIMINAL, grit_value=1)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=p0,
        expected_revision=state.revision,
        moves=((mover_pawn, HOOD, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.pending_brawl is None
    assert new_state.active_step != ActiveStep.WAITING_FOR_BRAWL_CARD
    assert len(new_state.board.hoods[HOOD].cop_ids) == 1
    resolved = next(e for e in outcome.events if isinstance(e, BrawlResolved))
    assert resolved.winner_id == p0
    assert resolved.loser_ids == ()


def test_only_players_with_physical_criminal_participate(game_data) -> None:
    state, _ = _new_game(game_data)
    hood = state.board.hoods[HOOD]

    for _ in range(3):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    link_pawn = _fresh_pawn(state, 1)
    _put_link(state, link_pawn, ARTISTI, 1)

    participants = brawl.compute_participants(state, hood)

    assert participants == {state.players[0].player_id}


# --- pause/resume across a multi-move package ---------------------------


def test_brawl_pauses_mid_package_and_resumes_after_resolution(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0, p1, p2 = (state.players[i].player_id for i in range(3))

    for _ in range(3):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    _put_criminal(state, _fresh_pawn(state, 2), HOOD)

    pawn_a, pawn_b = _fresh_pawns(state, 1, 2)
    _put_criminal(state, pawn_a, ORIGIN_HOOD)
    _put_criminal(state, pawn_b, ORIGIN_HOOD)

    state.current_player_id = p1
    _enter_main_action(state, ActionType.MOVE_CRIMINAL, grit_value=2)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=p1,
        expected_revision=state.revision,
        moves=((pawn_a, HOOD, None), (pawn_b, HoodId("hood_q3"), None)),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.pending_brawl is not None
    assert state.pending_brawl.remaining_moves == [(pawn_b, HoodId("hood_q3"), None)]
    assert state.active_step == ActiveStep.WAITING_FOR_BRAWL_CARD
    # pawn_b's move hasn't happened yet — still in the origin Hood.
    assert pawn_b in state.board.hoods[ORIGIN_HOOD].criminal_pawn_ids

    state, _ = _declare_no_cards(bus, state, 3)
    progress = state.pending_brawl
    assert progress.winner_id == p0
    assert set(progress.loser_ids) == {p1, p2}

    for loser_id in list(progress.loser_ids):
        outcome = bus.dispatch(
            state,
            ChooseBrawlLoserReward(
                game_id=state.game_id,
                player_id=p0,
                expected_revision=state.revision,
                loser_player_id=loser_id,
                reward_type="money",
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseBrawlLinkEvolution(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            pawn_id=None,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    dest = next(hid for hid, h in state.board.hoods.items() if not h.revealed and hid != HOOD)
    outcome = bus.dispatch(
        state,
        ChooseBrawlRelocationDestination(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            hood_id=dest,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    # The Rissa is fully resolved and the paused package resumed: pawn_b
    # completed its own queued move to hood_q3.
    assert state.pending_brawl is None
    assert pawn_b not in state.board.hoods[ORIGIN_HOOD].criminal_pawn_ids
    assert pawn_b in state.board.hoods[HoodId("hood_q3")].criminal_pawn_ids
    assert state.pawns[pawn_b].location.hood_id == HoodId("hood_q3")


# --- Force: Criminals + Links, Gun self-add/other-subtract -------------


def test_gun_assignment_self_adds_and_other_subtracts_force(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    artisti_cards = [c for c in game_data.customer_cards if c.contact_id == ARTISTI]
    card_a, card_b = artisti_cards[0].card_id, artisti_cards[1].card_id
    bus = _bus(
        game_data,
        price_tracks,
        link_extra_action_types,
        gun_count_by_card_id={card_a: 3, card_b: 1},
    )
    p0, p1 = state.players[0].player_id, state.players[1].player_id

    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 1), HOOD)
    state.players[0].hand_card_ids.append(card_a)
    state.players[1].hand_card_ids.append(card_b)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p0, [], events)
    assert set(state.pending_brawl.participants) == {p0, p1}

    for _ in range(2):
        current = state.current_player_id
        card_id = card_a if current == p0 else card_b
        outcome = bus.dispatch(
            state,
            PlayBrawlCard(
                game_id=state.game_id,
                player_id=current,
                expected_revision=state.revision,
                card_id=card_id,
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state

    outcome = None
    for _ in range(2):
        current = state.current_player_id
        target = current if current == p0 else p0  # p0 buffs self; p1 attacks p0
        outcome = bus.dispatch(
            state,
            AssignBrawlGuns(
                game_id=state.game_id,
                player_id=current,
                expected_revision=state.revision,
                target_player_id=target,
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state

    resolved = next(e for e in outcome.events if isinstance(e, BrawlResolved))
    assert resolved.force_by_player_id[p0] == 2 + 3 - 1
    assert resolved.force_by_player_id[p1] == 2
    assert resolved.winner_id == p0
    assert resolved.loser_ids == (p1,)


def test_link_at_hoods_contact_adds_to_participating_players_force(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0, p1 = state.players[0].player_id, state.players[1].player_id

    _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    _put_link(state, _fresh_pawn(state, 0), ARTISTI, 2)
    for _ in range(3):
        _put_criminal(state, _fresh_pawn(state, 1), HOOD)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p1, [], events)
    assert set(state.pending_brawl.participants) == {p0, p1}

    state, outcome = _declare_no_cards(bus, state, 2)

    resolved = next(e for e in outcome.events if isinstance(e, BrawlResolved))
    assert resolved.force_by_player_id[p0] == 1 + 1  # 1 Criminal + 1 Link
    assert resolved.force_by_player_id[p1] == 3


def test_tie_break_falls_back_to_seat_rotation_from_first_player(
    game_data, price_tracks, link_extra_action_types
) -> None:
    # The triggering player (p0) is deliberately *not* part of the tied
    # top-Force group (p1 v p2), so `_break_tie_for_winner`'s 2nd
    # criterion ("il giocatore che ha innescato la Rissa") can't resolve
    # it either — only seat rotation from `first_player_id` can.
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0, p1, p2 = (state.players[i].player_id for i in range(3))

    mover_pawn = _fresh_pawn(state, 0)
    _put_criminal(state, mover_pawn, HOOD)
    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 1), HOOD)
    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 2), HOOD)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p0, [], events)
    assert set(state.pending_brawl.participants) == {p0, p1, p2}
    state, outcome = _declare_no_cards(bus, state, 3)

    resolved = next(e for e in outcome.events if isinstance(e, BrawlResolved))
    assert resolved.force_by_player_id[p0] == 1
    assert resolved.force_by_player_id[p1] == 2
    assert resolved.force_by_player_id[p2] == 2
    start = state.player_order.index(state.first_player_id)
    rotation = state.player_order[start:] + state.player_order[:start]
    expected_winner = next(pid for pid in rotation if pid in (p1, p2))
    assert resolved.winner_id == expected_winner


# --- reward: money/card, Link evolution, relocation ---------------------


def test_single_defeated_pawn_relocated_others_stay_in_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0, p1 = state.players[0].player_id, state.players[1].player_id

    for _ in range(3):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    loser_pawns = _fresh_pawns(state, 1, 2)
    for pawn_id in loser_pawns:
        _put_criminal(state, pawn_id, HOOD)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p0, [], events)
    state, _ = _declare_no_cards(bus, state, 2)
    assert state.pending_brawl.winner_id == p0
    assert state.pending_brawl.loser_ids == [p1]

    outcome = bus.dispatch(
        state,
        ChooseBrawlLoserReward(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            loser_player_id=p1,
            reward_type="money",
        ),
    )
    state = outcome.state
    outcome = bus.dispatch(
        state,
        ChooseBrawlLinkEvolution(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            pawn_id=None,
        ),
    )
    state = outcome.state

    dest = next(hid for hid, h in state.board.hoods.items() if not h.revealed and hid != HOOD)
    loser_hand_before = len(next(p for p in state.players if p.player_id == p1).hand_card_ids)
    outcome = bus.dispatch(
        state,
        ChooseBrawlRelocationDestination(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            hood_id=dest,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    remaining_in_hood = [
        pid for pid in state.board.hoods[HOOD].criminal_pawn_ids if pid in loser_pawns
    ]
    moved = [pid for pid in loser_pawns if pid not in state.board.hoods[HOOD].criminal_pawn_ids]
    assert len(remaining_in_hood) == 1
    assert len(moved) == 1
    assert state.pawns[moved[0]].role == PawnRole.CRIMINAL
    assert state.pawns[moved[0]].location.hood_id == dest
    assert moved[0] in state.board.hoods[dest].criminal_pawn_ids
    assert state.board.hoods[dest].revealed is True

    loser_hand_after = len(next(p for p in state.players if p.player_id == p1).hand_card_ids)
    assert loser_hand_after == loser_hand_before + 1  # drew a card on arrival


def test_reward_money_and_card_are_independent_per_loser(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0 = state.players[0].player_id

    for _ in range(3):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    _put_criminal(state, _fresh_pawn(state, 1), HOOD)
    _put_criminal(state, _fresh_pawn(state, 2), HOOD)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p0, [], events)
    state, _ = _declare_no_cards(bus, state, 3)
    loser_a, loser_b = state.pending_brawl.loser_ids

    card_id = game_data.customer_cards[0].card_id
    player_a = next(p for p in state.players if p.player_id == loser_a)
    player_b = next(p for p in state.players if p.player_id == loser_b)
    player_a.hand_card_ids = [card_id]
    player_b.money = 1
    winner_money_before = next(p for p in state.players if p.player_id == p0).money

    outcome = bus.dispatch(
        state,
        ChooseBrawlLoserReward(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            loser_player_id=loser_a,
            reward_type="card",
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseBrawlLoserReward(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            loser_player_id=loser_b,
            reward_type="money",
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    winner_after = next(p for p in state.players if p.player_id == p0)
    loser_a_after = next(p for p in state.players if p.player_id == loser_a)
    loser_b_after = next(p for p in state.players if p.player_id == loser_b)

    assert card_id in winner_after.hand_card_ids
    assert loser_a_after.hand_card_ids == []
    assert winner_after.money == winner_money_before + 1  # clamped to loser_b's $1
    assert loser_b_after.money == 0


def test_link_evolution_reward_creates_link_and_removes_pawn_from_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0 = state.players[0].player_id

    winner_pawn_1, winner_pawn_2 = _fresh_pawns(state, 0, 2)
    _put_criminal(state, winner_pawn_1, HOOD)
    _put_criminal(state, winner_pawn_2, HOOD)
    _put_criminal(state, _fresh_pawn(state, 1), HOOD)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p0, [], events)
    state, _ = _declare_no_cards(bus, state, 2)
    assert state.pending_brawl.winner_id == p0
    loser_id = state.pending_brawl.loser_ids[0]

    outcome = bus.dispatch(
        state,
        ChooseBrawlLoserReward(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            loser_player_id=loser_id,
            reward_type="money",
        ),
    )
    state = outcome.state

    outcome = bus.dispatch(
        state,
        ChooseBrawlLinkEvolution(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            pawn_id=winner_pawn_1,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    pawn = state.pawns[winner_pawn_1]
    assert pawn.role == PawnRole.LINK
    assert pawn.contact_id == ARTISTI
    assert pawn.link_level == 1
    assert winner_pawn_1 not in state.board.hoods[HOOD].criminal_pawn_ids
    assert winner_pawn_2 in state.board.hoods[HOOD].criminal_pawn_ids


def test_brawl_step_rejects_wrong_player(game_data, price_tracks, link_extra_action_types) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    p0, p1 = state.players[0].player_id, state.players[1].player_id

    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 0), HOOD)
    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 1), HOOD)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[HOOD], p0, [], events)
    wrong_player = p1 if state.current_player_id == p0 else p0

    outcome = bus.dispatch(
        state,
        PlayBrawlCard(
            game_id=state.game_id,
            player_id=wrong_player,
            expected_revision=state.revision,
            card_id=None,
        ),
    )
    assert isinstance(outcome, CommandFailure)
