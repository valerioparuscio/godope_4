"""End-of-game scoring (RULES_CANONICAL.md §D6, CLAUDE.md §11.14).

`compute_final_score` is called once, automatically, from
`rules/turn_flow.py::_end_turn` when the configured number of turns is
reached — no player command triggers it, mirroring how `rules/raids.py::
resolve_raid` runs automatically at Showdown.

Confirmed by the game designer / already-decided in RULES_CANONICAL.md:
- Money-track points: rank players by money descending; a tied group
  all takes the point value of the *worst* (highest-numbered) position
  in the range they occupy, not the best — worked example in §D6:
  a lone 1st takes 4, a 2nd/3rd tie both take 2 (the 3rd's value), the
  4th takes 1.
- REP points: 2 per clean (unstained) token, 1 per stained — the tokens
  themselves are the Job board's own "R" cells (§A10/§D5), not a
  separate pool.
- Contact majority: 1 point per Contact where exactly one player has
  strictly the highest weighted presence (Criminal=1, Link=2); a tie at
  the top awards nobody. Every Contact has at least one ordinary Hood,
  so the full set of Contacts is read straight off the board rather than
  needing GameData threaded in (same "read what's already reachable
  from state" preference as rules/raids.py).
- Chip points: 1 point per full group of 3 Chips in the Covo, counting
  Dope units (all 4 types) + Cops/Feds owned + Poker Chips together
  ("anche miste" — §A7/RULES_CANONICAL.md line 70-73 already treats these
  three as the same "Chip" category for the Covo's own 3-per-type cap;
  designer's clarification, 2026-08-27, applies that same category to
  this scoring line too — an earlier pass only counted Poker Chips).
- Skill points: 1 per owned Skill.
- Winner(s): highest total; ties broken by clean REP *count* (not
  points); a further tie is a shared victory (`FinalScoreState.winner_ids`
  can have more than one entry).
"""

from __future__ import annotations

from dope_engine.domain.entities import LocationType, OfficerLocationType
from dope_engine.domain.enums import PawnRole
from dope_engine.domain.ids import PlayerId
from dope_engine.domain.scoring import FinalScoreBreakdown, FinalScoreState
from dope_engine.domain.state import GameState, PlayerState


def _money_track_points(
    players: list[PlayerState], points_by_rank: list[int]
) -> dict[PlayerId, int]:
    ranked = sorted(players, key=lambda p: p.money, reverse=True)
    points: dict[PlayerId, int] = {}
    i = 0
    while i < len(ranked):
        j = i
        while j + 1 < len(ranked) and ranked[j + 1].money == ranked[i].money:
            j += 1
        awarded = points_by_rank[j]
        for k in range(i, j + 1):
            points[ranked[k].player_id] = awarded
        i = j + 1
    return points


def _clean_and_stained_counts(state: GameState, player_id: PlayerId) -> tuple[int, int]:
    owned = [c for c in state.jobs.board if c.player_id == player_id]
    clean = sum(1 for c in owned if not c.stained)
    stained = sum(1 for c in owned if c.stained)
    return clean, stained


def _contact_majority_points(state: GameState) -> dict[PlayerId, int]:
    weight_criminal = state.configuration["scoring"]["majority_weight_criminal"]
    weight_link = state.configuration["scoring"]["majority_weight_link"]
    points_per_contact = state.configuration["scoring"]["majority_points_per_contact"]

    # Every Contact has at least one ordinary Hood (data/board.json), so
    # scanning the board's own Hoods already yields the full Contact set.
    contact_ids = {hood.contact_id for hood in state.board.hoods.values()}
    hood_contact_by_id = {hood_id: hood.contact_id for hood_id, hood in state.board.hoods.items()}

    points: dict[PlayerId, int] = {player.player_id: 0 for player in state.players}
    for contact_id in contact_ids:
        presence: dict[PlayerId, int] = {player.player_id: 0 for player in state.players}
        for pawn in state.pawns.values():
            if pawn.role == PawnRole.CRIMINAL and pawn.location.type == LocationType.HOOD:
                hood_id = pawn.location.hood_id
                if hood_id is not None and hood_contact_by_id.get(hood_id) == contact_id:
                    presence[pawn.owner_player_id] += weight_criminal
            elif pawn.role == PawnRole.LINK and pawn.contact_id == contact_id:
                presence[pawn.owner_player_id] += weight_link

        top = max(presence.values())
        if top == 0:
            continue
        leaders = [pid for pid, value in presence.items() if value == top]
        if len(leaders) == 1:
            points[leaders[0]] += points_per_contact
    return points


def _base_chip_count(state: GameState, player_id: PlayerId) -> int:
    """Dope units (all 4 types) + Cops/Feds owned + Poker Chips, all in the
    Covo — the same combined "Chip" category §A7 already uses for the
    Covo's own 3-per-type cap (RULES_CANONICAL.md line 70-73). Not
    `rules.officers.officer_count_in_base` directly: that module imports
    `rules.turn_flow`, which itself imports this module — importing it
    here would cycle."""
    player = next(p for p in state.players if p.player_id == player_id)
    dope_count = sum(player.base_inventory.dope_counts.values())
    officer_count = sum(
        1
        for officer in state.board.officers.values()
        if officer.location_type == OfficerLocationType.BASE
        and officer.owner_player_id == player_id
    )
    return dope_count + officer_count + player.base_inventory.poker_chip_count


def compute_final_score(state: GameState) -> FinalScoreState:
    scoring_config = state.configuration["scoring"]
    money_points = _money_track_points(state.players, scoring_config["money_track_points_by_rank"])
    majority_points = _contact_majority_points(state)

    breakdown_by_player: dict[PlayerId, FinalScoreBreakdown] = {}
    for player in state.players:
        clean_count, stained_count = _clean_and_stained_counts(state, player.player_id)
        clean_points = clean_count * scoring_config["clean_rep_points"]
        stained_points = stained_count * scoring_config["stained_rep_points"]
        chip_points = (_base_chip_count(state, player.player_id) // 3) * scoring_config[
            "chip_points_per_3_chips"
        ]
        skill_points = len(player.skill_ids) * scoring_config["skill_points_per_skill"]
        money_track_points = money_points[player.player_id]
        contact_points = majority_points[player.player_id]

        total = (
            money_track_points
            + clean_points
            + stained_points
            + contact_points
            + chip_points
            + skill_points
        )
        breakdown_by_player[player.player_id] = FinalScoreBreakdown(
            money_track_position_points=money_track_points,
            clean_reputation_points=clean_points,
            stained_reputation_points=stained_points,
            contact_majority_points=contact_points,
            base_chip_points=chip_points,
            skill_points=skill_points,
            total_points=total,
            tie_break_clean_reputation=clean_count,
        )

    best_total = max(b.total_points for b in breakdown_by_player.values())
    leaders = [pid for pid, b in breakdown_by_player.items() if b.total_points == best_total]
    if len(leaders) > 1:
        best_clean = max(breakdown_by_player[pid].tie_break_clean_reputation for pid in leaders)
        leaders = [
            pid
            for pid in leaders
            if breakdown_by_player[pid].tie_break_clean_reputation == best_clean
        ]

    return FinalScoreState(breakdown_by_player=breakdown_by_player, winner_ids=tuple(leaders))
