"""Milestone 5 (Retate) scenario tests: the 7 escape-criterion functions,
team split/tie handling, REP staining (including partial staining and
occurrence scaling), the "highest Preti Link chooses first player"
Tip-off pause, and StainReputationForMoney's eligibility gating.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import ChooseRaidFirstPlayer, StainReputationForMoney
from dope_engine.domain.enums import ActiveStep, GamePhase, PawnRole
from dope_engine.domain.ids import ContactId, GameId, RaidCardId
from dope_engine.rules import links, raids, turn_flow
from dope_engine.rules.setup import create_initial_state

PRETI = ContactId("preti")


def _bus(game_data):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    turn_flow.register_handlers(bus, card_contact_by_id=card_contact_by_id)
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _raid_card_with_criterion(game_data, criterion: str) -> str:
    return next(r.raid_card_id for r in game_data.raids if r.escape_criterion == criterion)


_CELL_SOURCE_JOB_IDS = [f"job_{i:02d}" for i in range(1, 10)]


def _give_clean_cells(state, player_id, count) -> None:
    """Claims `count` distinct clean board cells for `player_id`, one
    column per Job row (job_01, job_02, ...), each at this player's own
    `seat_index` column — every player uses a different column on the
    same rows, so calling this for all 4 players never collides."""
    seat_index = next(p.seat_index for p in state.players if p.player_id == player_id)
    for job_id in _CELL_SOURCE_JOB_IDS[:count]:
        cell = next(
            c for c in state.jobs.board if c.job_id == job_id and c.column_index == seat_index
        )
        cell.player_id = player_id
        cell.stained = False


# --- criterion functions -----------------------------------------------


def test_most_links_with_contacts(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    pawn_id = player.pawn_ids[0]
    state.pawns[pawn_id].role = PawnRole.LINK
    assert raids._ESCAPE_CRITERION_FUNCS["most_links_with_contacts"](state, player.player_id) == 1


def test_most_criminals_in_jail(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    state.pawns[player.pawn_ids[0]].role = PawnRole.RAT
    state.pawns[player.pawn_ids[1]].role = PawnRole.RAT
    assert raids._ESCAPE_CRITERION_FUNCS["most_criminals_in_jail"](state, player.player_id) == 2


def test_least_dope_value(game_data) -> None:
    from dope_engine.domain.enums import DopeType

    state, _ = _new_game(game_data)
    player = state.players[0]
    player.base_inventory.dope_counts = {DopeType.CAMALEONTE: 2}
    price = state.configuration["price_track_by_dope_type"][DopeType.CAMALEONTE][
        state.market.price_index_by_dope_type[DopeType.CAMALEONTE]
    ]
    assert raids._ESCAPE_CRITERION_FUNCS["least_dope_value"](state, player.player_id) == price * 2


def test_most_poker_wins(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.poker_matches_won_count = 3
    assert raids._ESCAPE_CRITERION_FUNCS["most_poker_wins"](state, player.player_id) == 3


def test_most_cops_bought_counts_cops_and_feds_together(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.officers_bought_count = 4
    assert raids._ESCAPE_CRITERION_FUNCS["most_cops_bought"](state, player.player_id) == 4


def test_most_money(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.money = 42
    assert raids._ESCAPE_CRITERION_FUNCS["most_money"](state, player.player_id) == 42


def test_most_criminals_in_hoods(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    # Starter Criminals already placed 3 pawns for player 0 at setup.
    deployed = sum(
        1
        for pid in player.pawn_ids
        if state.pawns[pid].role == PawnRole.CRIMINAL
    )
    actual = raids._ESCAPE_CRITERION_FUNCS["most_criminals_in_hoods"](state, player.player_id)
    assert actual == deployed


# --- resolve_raid: team split, tie, staining ----------------------------


def test_resolve_raid_higher_sum_team_escapes_lower_sum_team_is_stained(game_data) -> None:
    state, _ = _new_game(game_data)
    order = raids._rotation_order(state)
    state.raids.current_turn_card_id = RaidCardId(
        _raid_card_with_criterion(game_data, "most_money")
    )
    for pid in order:
        player = next(p for p in state.players if p.player_id == pid)
        player.money = 0
        _give_clean_cells(state, pid, 3)
    # Team A = order[0]+order[3], Team B = order[1]+order[2].
    next(p for p in state.players if p.player_id == order[0]).money = 100

    events: list = []
    raids.resolve_raid(state, events)

    resolved = next(e for e in events if type(e).__name__ == "RaidResolved")
    assert set(resolved.escaping_team) == {order[0], order[3]}
    assert set(resolved.caught_team) == {order[1], order[2]}
    for pid in (order[1], order[2]):
        player = next(p for p in state.players if p.player_id == pid)
        stained = [c for c in state.jobs.board if c.player_id == pid and c.stained]
        assert len(stained) == 1  # 1st occurrence stains 1
    for pid in (order[0], order[3]):
        player = next(p for p in state.players if p.player_id == pid)
        stained = [c for c in state.jobs.board if c.player_id == pid and c.stained]
        assert len(stained) == 0
    assert state.raids.lost_occurrences_count == 1


def test_resolve_raid_least_dope_value_lower_sum_team_escapes(game_data) -> None:
    from dope_engine.domain.enums import DopeType

    state, _ = _new_game(game_data)
    order = raids._rotation_order(state)
    state.raids.current_turn_card_id = RaidCardId(
        _raid_card_with_criterion(game_data, "least_dope_value")
    )
    for pid in order:
        player = next(p for p in state.players if p.player_id == pid)
        player.base_inventory.dope_counts = {}
        _give_clean_cells(state, pid, 3)
    next(p for p in state.players if p.player_id == order[0]).base_inventory.dope_counts = {
        DopeType.CAMALEONTE: 3
    }

    events: list = []
    raids.resolve_raid(state, events)

    resolved = next(e for e in events if type(e).__name__ == "RaidResolved")
    # Team A (order[0]+order[3]) has strictly more Dope value, so it
    # loses this criterion (lower value escapes).
    assert set(resolved.escaping_team) == {order[1], order[2]}
    assert set(resolved.caught_team) == {order[0], order[3]}


def test_resolve_raid_exact_tie_catches_all_four(game_data) -> None:
    state, _ = _new_game(game_data)
    order = raids._rotation_order(state)
    state.raids.current_turn_card_id = RaidCardId(
        _raid_card_with_criterion(game_data, "most_money")
    )
    for pid in order:
        player = next(p for p in state.players if p.player_id == pid)
        player.money = 5
        _give_clean_cells(state, pid, 3)

    events: list = []
    raids.resolve_raid(state, events)

    resolved = next(e for e in events if type(e).__name__ == "RaidResolved")
    assert resolved.escaping_team == ()
    assert set(resolved.caught_team) == set(order)
    for pid in order:
        stained = [c for c in state.jobs.board if c.player_id == pid and c.stained]
        assert len(stained) == 1


def test_resolve_raid_stains_partially_when_not_enough_clean_tokens(game_data) -> None:
    state, _ = _new_game(game_data)
    order = raids._rotation_order(state)
    state.raids.current_turn_card_id = RaidCardId(
        _raid_card_with_criterion(game_data, "most_money")
    )
    state.raids.lost_occurrences_count = 1  # 2nd occurrence -> stain 2
    for pid in order:
        player = next(p for p in state.players if p.player_id == pid)
        player.money = 0
    next(p for p in state.players if p.player_id == order[0]).money = 100
    # The caught players (order[1], order[2]) only get 1 clean cell each.
    _give_clean_cells(state, order[1], 1)
    _give_clean_cells(state, order[2], 1)

    events: list = []
    raids.resolve_raid(state, events)

    resolved = next(e for e in events if type(e).__name__ == "RaidResolved")
    assert resolved.stain_count_applied[order[1]] == 1
    assert resolved.stain_count_applied[order[2]] == 1


def test_resolve_raid_occurrence_count_scales_stain_amount(game_data) -> None:
    state, _ = _new_game(game_data)
    order = raids._rotation_order(state)
    state.raids.current_turn_card_id = RaidCardId(
        _raid_card_with_criterion(game_data, "most_money")
    )
    state.raids.lost_occurrences_count = 2  # 3rd occurrence -> stain 3
    for pid in order:
        player = next(p for p in state.players if p.player_id == pid)
        player.money = 0
        _give_clean_cells(state, pid, 3)
    next(p for p in state.players if p.player_id == order[0]).money = 100

    events: list = []
    raids.resolve_raid(state, events)

    resolved = next(e for e in events if type(e).__name__ == "RaidResolved")
    assert resolved.stain_count_applied[order[1]] == 3
    assert resolved.stain_count_applied[order[2]] == 3
    assert state.raids.lost_occurrences_count == 3


def test_resolve_raid_with_no_current_card_is_a_no_op(game_data) -> None:
    state, _ = _new_game(game_data)
    state.raids.current_turn_card_id = None
    events: list = []
    raids.resolve_raid(state, events)
    assert events == []
    assert state.raids.lost_occurrences_count == 0


# --- Tip-off: choosing the Raid's first player --------------------------


def test_no_preti_link_leaves_first_player_unchanged(game_data) -> None:
    state, _ = _new_game(game_data)
    assert state.phase == GamePhase.ACTION_PHASE
    assert state.active_step != ActiveStep.WAITING_FOR_RAID_RESOLUTION


def test_highest_preti_link_owner_is_offered_the_choice(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    chooser_id = state.players[1].player_id
    link_pawn_id = next(
        pid for pid in state.players[1].pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    events: list = []
    links.insert_link(state, chooser_id, link_pawn_id, PRETI, 2, events)

    # Re-run Tip-off for a new turn to exercise the pause.
    state.turn_index = 2
    events2: list = []
    turn_flow.start_tip_off(state, events2)

    assert state.phase == GamePhase.TIP_OFF
    assert state.active_step == ActiveStep.WAITING_FOR_RAID_RESOLUTION
    assert state.current_player_id == chooser_id

    outcome = bus.dispatch(
        state,
        ChooseRaidFirstPlayer(
            game_id=state.game_id,
            player_id=chooser_id,
            expected_revision=state.revision,
            chosen_first_player_id=state.players[2].player_id,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.first_player_id == state.players[2].player_id
    assert new_state.phase == GamePhase.ACTION_PHASE
    assert new_state.active_step in (
        ActiveStep.WAITING_FOR_GRIT_ACTION,
        ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION,
        ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER,
    )


def test_choose_raid_first_player_rejects_wrong_player(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    chooser_id = state.players[1].player_id
    link_pawn_id = next(
        pid for pid in state.players[1].pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    events: list = []
    links.insert_link(state, chooser_id, link_pawn_id, PRETI, 1, events)
    state.turn_index = 2
    turn_flow.start_tip_off(state, [])

    outcome = bus.dispatch(
        state,
        ChooseRaidFirstPlayer(
            game_id=state.game_id,
            player_id=state.players[0].player_id,
            expected_revision=state.revision,
            chosen_first_player_id=state.players[0].player_id,
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_player"


# --- StainReputationForMoney ---------------------------------------------


def test_stain_reputation_for_money_requires_low_money_and_a_clean_token(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.players[0].player_id
    threshold = state.configuration["stain_rep_for_cash"]["money_threshold"]

    assert raids.player_can_stain_for_cash(state, player_id) is False  # no clean cell yet

    _give_clean_cells(state, player_id, 1)
    assert raids.player_can_stain_for_cash(state, player_id) is False  # money too high

    next(p for p in state.players if p.player_id == player_id).money = threshold
    assert raids.player_can_stain_for_cash(state, player_id) is True


def test_stain_reputation_for_money_pays_cash_and_stains_a_token(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == player_id)
    threshold = state.configuration["stain_rep_for_cash"]["money_threshold"]
    cash_gained = state.configuration["stain_rep_for_cash"]["cash_gained"]
    player.money = threshold
    _give_clean_cells(state, player_id, 1)
    state.active_step = ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER
    state.current_player_id = player_id

    outcome = bus.dispatch(
        state,
        StainReputationForMoney(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player_id)
    assert new_player.money == threshold + cash_gained
    stained = [c for c in outcome.state.jobs.board if c.player_id == player_id and c.stained]
    assert len(stained) == 1
    assert outcome.state.active_step != ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER


def test_stain_reputation_for_money_rejects_when_not_eligible(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == player_id)
    player.money = 999  # far above the threshold
    state.active_step = ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER
    state.current_player_id = player_id

    outcome = bus.dispatch(
        state,
        StainReputationForMoney(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "cannot_stain_for_cash"
