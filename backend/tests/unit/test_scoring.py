"""Milestone 5 (End Game Scoring) scenario tests: the money-track
tie-table worked example from RULES_CANONICAL.md §D6, Contact majority
(including the "tie awards nobody" case named by CLAUDE.md §17.2),
Chip/Skill point arithmetic, and the winner tie-break cascade (total
points -> clean REP count -> shared victory).
"""

from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import PawnRole
from dope_engine.domain.ids import GameId
from dope_engine.rules import scoring
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    """A fresh game already has 3 starting Criminals per player deployed
    (rules/setup.py::_place_starting_criminals) — irrelevant noise for
    these scoring tests, which want a clean, fully controlled slate."""
    state, events = create_initial_state(
        game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat
    )
    _reset_pawns_to_base(state)
    return state, events


def _reset_pawns_to_base(state) -> None:
    for hood in state.board.hoods.values():
        hood.criminal_pawn_ids.clear()
    for pawn in state.pawns.values():
        pawn.role = PawnRole.IN_BASE
        pawn.location = PawnLocation.base()
        pawn.contact_id = None
        pawn.link_level = None
        pawn.jail_slot = None


def _clear_board(state) -> None:
    for cell in state.jobs.board:
        cell.player_id = None
        cell.stained = False


def _give_cells(state, player_id, clean=0, stained=0) -> None:
    seat_index = next(p.seat_index for p in state.players if p.player_id == player_id)
    job_ids = [f"job_{i:02d}" for i in range(1, 10)]
    index = 0
    for _ in range(clean):
        cell = next(
            c
            for c in state.jobs.board
            if c.job_id == job_ids[index] and c.column_index == seat_index
        )
        cell.player_id = player_id
        cell.stained = False
        index += 1
    for _ in range(stained):
        cell = next(
            c
            for c in state.jobs.board
            if c.job_id == job_ids[index] and c.column_index == seat_index
        )
        cell.player_id = player_id
        cell.stained = True
        index += 1


# --- money-track points --------------------------------------------------


def test_money_track_worked_example_from_rules_canonical(game_data) -> None:
    """§D6 exact example: a lone 1st takes 4, a 2nd/3rd tie both take 2
    (the 3rd's value, not the 2nd's), the 4th takes 1."""
    state, _ = _new_game(game_data)
    _clear_board(state)
    p0, p1, p2, p3 = state.players
    p0.money = 100  # sole 1st
    p1.money = 50  # tied 2nd/3rd
    p2.money = 50  # tied 2nd/3rd
    p3.money = 10  # sole 4th

    final_score = scoring.compute_final_score(state)

    assert final_score.breakdown_by_player[p0.player_id].money_track_position_points == 4
    assert final_score.breakdown_by_player[p1.player_id].money_track_position_points == 2
    assert final_score.breakdown_by_player[p2.player_id].money_track_position_points == 2
    assert final_score.breakdown_by_player[p3.player_id].money_track_position_points == 1


def test_money_track_all_four_tied_take_the_worst_position_value(game_data) -> None:
    state, _ = _new_game(game_data)
    _clear_board(state)
    for player in state.players:
        player.money = 20

    final_score = scoring.compute_final_score(state)

    for player in state.players:
        assert final_score.breakdown_by_player[player.player_id].money_track_position_points == 1


# --- REP points ------------------------------------------------------------


def test_rep_points_count_clean_as_two_and_stained_as_one(game_data) -> None:
    state, _ = _new_game(game_data)
    _clear_board(state)
    player = state.players[0]
    _give_cells(state, player.player_id, clean=2, stained=3)

    final_score = scoring.compute_final_score(state)
    breakdown = final_score.breakdown_by_player[player.player_id]

    assert breakdown.clean_reputation_points == 4  # 2 clean x 2
    assert breakdown.stained_reputation_points == 3  # 3 stained x 1
    assert breakdown.tie_break_clean_reputation == 2


# --- Contact majority --------------------------------------------------


def test_contact_majority_tie_awards_no_point(game_data) -> None:
    """Named exactly by CLAUDE.md §17.2 as a required scenario test."""
    state, _ = _new_game(game_data)
    _clear_board(state)
    p0, p1 = state.players[0], state.players[1]
    contact_id = next(iter({h.contact_id for h in state.board.hoods.values()}))
    hood_id = next(h.hood_id for h in state.board.hoods.values() if h.contact_id == contact_id)

    pawn_a = state.pawns[p0.pawn_ids[0]]
    pawn_a.role = PawnRole.CRIMINAL
    pawn_a.location = PawnLocation.hood(hood_id)
    pawn_b = state.pawns[p1.pawn_ids[0]]
    pawn_b.role = PawnRole.CRIMINAL
    pawn_b.location = PawnLocation.hood(hood_id)

    majority_points = scoring._contact_majority_points(state)

    assert majority_points[p0.player_id] == 0
    assert majority_points[p1.player_id] == 0


def test_contact_majority_sole_leader_gets_the_point(game_data) -> None:
    state, _ = _new_game(game_data)
    _clear_board(state)
    p0 = state.players[0]
    contact_id = next(iter({h.contact_id for h in state.board.hoods.values()}))
    hood_id = next(h.hood_id for h in state.board.hoods.values() if h.contact_id == contact_id)

    pawn = state.pawns[p0.pawn_ids[0]]
    pawn.role = PawnRole.CRIMINAL
    pawn.location = PawnLocation.hood(hood_id)

    majority_points = scoring._contact_majority_points(state)
    per_contact = state.configuration["scoring"]["majority_points_per_contact"]

    assert majority_points[p0.player_id] == per_contact


def test_contact_majority_link_outweighs_a_single_criminal(game_data) -> None:
    state, _ = _new_game(game_data)
    _clear_board(state)
    p0, p1 = state.players[0], state.players[1]
    contact_id = next(iter({h.contact_id for h in state.board.hoods.values()}))
    hood_id = next(h.hood_id for h in state.board.hoods.values() if h.contact_id == contact_id)

    criminal = state.pawns[p0.pawn_ids[0]]
    criminal.role = PawnRole.CRIMINAL
    criminal.location = PawnLocation.hood(hood_id)

    link = state.pawns[p1.pawn_ids[0]]
    link.role = PawnRole.LINK
    link.contact_id = contact_id
    link.link_level = 1

    majority_points = scoring._contact_majority_points(state)
    per_contact = state.configuration["scoring"]["majority_points_per_contact"]

    assert majority_points[p1.player_id] == per_contact
    assert majority_points[p0.player_id] == 0


# --- Chip/Skill points ---------------------------------------------------


def test_chip_points_only_count_full_groups_of_three(game_data) -> None:
    state, _ = _new_game(game_data)
    _clear_board(state)
    player = state.players[0]
    player.base_inventory.poker_chip_count = 3

    final_score = scoring.compute_final_score(state)
    assert final_score.breakdown_by_player[player.player_id].base_chip_points == 1

    player.base_inventory.poker_chip_count = 2
    final_score = scoring.compute_final_score(state)
    assert final_score.breakdown_by_player[player.player_id].base_chip_points == 0


def test_skill_points_one_per_skill(game_data) -> None:
    from dope_engine.domain.ids import SkillId

    state, _ = _new_game(game_data)
    _clear_board(state)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_1"), SkillId("skill_manager_2")]

    final_score = scoring.compute_final_score(state)
    assert final_score.breakdown_by_player[player.player_id].skill_points == 2


# --- winner tie-break cascade --------------------------------------------


def test_winner_is_the_sole_highest_total(game_data) -> None:
    state, _ = _new_game(game_data)
    _clear_board(state)
    p0, p1, p2, p3 = state.players
    p0.money = 100
    p1.money = p2.money = p3.money = 0

    final_score = scoring.compute_final_score(state)
    assert final_score.winner_ids == (p0.player_id,)


def test_tied_totals_broken_by_clean_reputation_count(game_data) -> None:
    state, _ = _new_game(game_data)
    _clear_board(state)
    for player in state.players:
        player.money = 0  # all 4 tied on money -> same money_track_position_points
    p0, p1 = state.players[0], state.players[1]
    _give_cells(state, p0.player_id, clean=2)  # 2x2 = 4 REP points, 2 clean tokens
    _give_cells(state, p1.player_id, clean=1, stained=2)  # 1x2 + 2x1 = 4 REP points too

    final_score = scoring.compute_final_score(state)
    b0 = final_score.breakdown_by_player[p0.player_id]
    b1 = final_score.breakdown_by_player[p1.player_id]
    assert b0.total_points == b1.total_points
    assert b0.tie_break_clean_reputation > b1.tie_break_clean_reputation
    assert final_score.winner_ids == (p0.player_id,)  # more clean REP


def test_fully_tied_players_share_victory(game_data) -> None:
    state, _ = _new_game(game_data)
    _clear_board(state)
    for player in state.players:
        player.money = 0

    final_score = scoring.compute_final_score(state)
    assert set(final_score.winner_ids) == {p.player_id for p in state.players}
