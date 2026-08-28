"""Retate (RULES_CANONICAL.md §D4/§D5): end-of-turn team evaluation and
REP staining, plus the shared "flip one clean REP token" mechanic reused
by the mandatory Raid outcome and the voluntary
`StainReputationForMoney` action (both just flip an already-placed Job
board cell — RULES_CANONICAL.md §D5 confirms there is no separate REP
token pool, the "R" tokens *are* the Job board cells).

`resolve_raid` is called automatically from `rules/turn_flow.py::
_enter_showdown_phase` at the end of every turn — no player command
triggers it. It reads the current turn's Raid card's `escape_criterion`
and the full per-Dope-type price tracks from `state.configuration`
(`raid_escape_criterion_by_raid_card_id` / `price_track_by_dope_type`,
both populated once at setup by `rules/setup.py`) rather than having
them threaded in as parameters — the alternative would have meant
threading two lookup dicts through the entire ACTION_PHASE/POKER_PHASE
round-advance call graph in `rules/turn_flow.py` and `rules/poker.py`
just to reach this one call site at the very end of it, since this
function is reached through many different paths (any way a turn's last
round can end). `state.configuration` is already how every other piece
of static, load-time game content reaches arbitrary rule code (the whole
of `data/game_config.json` already lives there); adding these two
derived, read-only lookups follows the same precedent instead of
inventing a second threading mechanism.

The team split ("il primo e il quarto giocatore vs il secondo e il
terzo") uses the *game's* `first_player_id`/rotation order directly,
not a separate "Raid first player" concept — RULES_CANONICAL.md §D4's
"decide il primo giocatore e **quindi** le squadre" reads as one and the
same choice, confirmed by `rules/turn_flow.py::_handle_choose_raid_first_player`
actually setting `state.first_player_id`.
"""

from __future__ import annotations

from collections.abc import Callable

from dope_engine.domain.entities import LocationType
from dope_engine.domain.enums import PawnRole
from dope_engine.domain.events import DomainEvent, RaidResolved, ReputationStained
from dope_engine.domain.ids import PlayerId
from dope_engine.domain.state import GameState, LastRaidOutcome, find_player, officer_count_in_base
from dope_engine.rules.event_utils import emit as _emit


def _most_links_with_contacts(state: GameState, player_id: PlayerId) -> int:
    player = find_player(state, player_id)
    return sum(1 for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.LINK)


def _most_criminals_in_jail(state: GameState, player_id: PlayerId) -> int:
    player = find_player(state, player_id)
    return sum(1 for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.RAT)


def _least_dope_value(state: GameState, player_id: PlayerId) -> int:
    player = find_player(state, player_id)
    total = 0
    for dope_type, count in player.base_inventory.dope_counts.items():
        track = state.configuration["price_track_by_dope_type"][dope_type]
        price = track[state.market.price_index_by_dope_type[dope_type]]
        total += price * count
    return total


def _most_poker_wins(state: GameState, player_id: PlayerId) -> int:
    return find_player(state, player_id).poker_matches_won_count


def _most_cops_bought(state: GameState, player_id: PlayerId) -> int:
    # Confirmed 2026-08-01, reversed 2026-08-23 alongside Job 2 (same
    # rules-designer report and decision — RULES_CANONICAL.md §A10):
    # this counts Cops and Feds together, still the same pool as Job 2
    # ("Abbi 1 Cop/Fed"), but now live possession (in this player's own
    # Covo right now) instead of a cumulative "ever bought" counter.
    return officer_count_in_base(state, player_id)


def _most_money(state: GameState, player_id: PlayerId) -> int:
    return find_player(state, player_id).money


def _most_criminals_in_hoods(state: GameState, player_id: PlayerId) -> int:
    player = find_player(state, player_id)
    return sum(
        1
        for pid in player.pawn_ids
        if state.pawns[pid].role == PawnRole.CRIMINAL
        and state.pawns[pid].location.type == LocationType.HOOD
    )


_ESCAPE_CRITERION_FUNCS: dict[str, Callable[[GameState, PlayerId], int]] = {
    "most_links_with_contacts": _most_links_with_contacts,
    "most_criminals_in_jail": _most_criminals_in_jail,
    "least_dope_value": _least_dope_value,
    "most_poker_wins": _most_poker_wins,
    "most_cops_bought": _most_cops_bought,
    "most_money": _most_money,
    "most_criminals_in_hoods": _most_criminals_in_hoods,
}
# Every criterion means "highest sum escapes" except this one.
_LOWEST_WINS_CRITERIA = {"least_dope_value"}


def stain_one_clean_token(state: GameState, player_id: PlayerId, events: list[DomainEvent]) -> bool:
    """Flips the first still-clean Job board cell owned by `player_id`
    (RULES_CANONICAL.md §D5: which specific cell is inconsequential,
    every clean cell is worth the same 2 points — same "pick arbitrarily
    when provably indifferent" precedent used elsewhere, e.g. package
    sale's pawn choice). Returns False (no-op) if the player owns no
    clean cell to flip — §D4 confirmed: "semplicemente non macchia
    quelli che non può"."""
    cell = next((c for c in state.jobs.board if c.player_id == player_id and not c.stained), None)
    if cell is None:
        return False
    cell.stained = True
    new_stain_total = sum(1 for c in state.jobs.board if c.player_id == player_id and c.stained)
    _emit(
        state,
        events,
        ReputationStained,
        player_id=player_id,
        job_id=cell.job_id,
        column_index=cell.column_index,
        new_stain_total=new_stain_total,
    )
    return True


def player_can_stain_for_cash(state: GameState, player_id: PlayerId) -> bool:
    config = state.configuration["stain_rep_for_cash"]
    player = find_player(state, player_id)
    if player.money > config["money_threshold"]:
        return False
    return any(c.player_id == player_id and not c.stained for c in state.jobs.board)


def _rotation_order(state: GameState) -> list[PlayerId]:
    start = state.player_order.index(state.first_player_id)
    return state.player_order[start:] + state.player_order[:start]


def resolve_raid(state: GameState, events: list[DomainEvent]) -> None:
    raid_card_id = state.raids.current_turn_card_id
    if raid_card_id is None:
        return

    criterion = state.configuration["raid_escape_criterion_by_raid_card_id"][raid_card_id]
    criterion_fn = _ESCAPE_CRITERION_FUNCS[criterion]
    lower_wins = criterion in _LOWEST_WINS_CRITERIA

    order = _rotation_order(state)
    team_a = (order[0], order[3])  # 1st + 4th
    team_b = (order[1], order[2])  # 2nd + 3rd
    sum_a = sum(criterion_fn(state, pid) for pid in team_a)
    sum_b = sum(criterion_fn(state, pid) for pid in team_b)

    if sum_a == sum_b:
        # §D4 confirmed: an exact tie means nobody escapes. Both totals
        # are the same value here by definition, so either one describes
        # both sides — there's no single "the caught team's total" when
        # all 4 players end up caught together.
        escaped: tuple[PlayerId, ...] = ()
        caught: tuple[PlayerId, ...] = team_a + team_b
        escaped_total, caught_total = sum_a, sum_a
    elif (sum_a < sum_b) == lower_wins:
        escaped, caught = team_a, team_b
        escaped_total, caught_total = sum_a, sum_b
    else:
        escaped, caught = team_b, team_a
        escaped_total, caught_total = sum_b, sum_a

    occurrences = state.configuration["raid_stain_counts_by_occurrence"]
    occurrence_index = state.raids.lost_occurrences_count
    stain_count = (
        occurrences[occurrence_index] if occurrence_index < len(occurrences) else occurrences[-1]
    )

    stain_totals: dict[PlayerId, int] = {}
    for player_id in caught:
        applied = 0
        for _ in range(stain_count):
            if not stain_one_clean_token(state, player_id, events):
                break
            applied += 1
        stain_totals[player_id] = applied

    state.raids.lost_occurrences_count += 1
    state.raids.last_outcome = LastRaidOutcome(
        raid_card_id=raid_card_id,
        escaping_team=escaped,
        caught_team=caught,
        escape_criterion=criterion,
        escaping_team_total=escaped_total,
        caught_team_total=caught_total,
        stain_count_applied=dict(stain_totals),
    )
    _emit(
        state,
        events,
        RaidResolved,
        raid_card_id=raid_card_id,
        escaping_team=escaped,
        caught_team=caught,
        stain_count_applied=stain_totals,
        escape_criterion=criterion,
        escaping_team_total=escaped_total,
        caught_team_total=caught_total,
    )
