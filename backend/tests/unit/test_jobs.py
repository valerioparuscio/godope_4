"""Milestone 5 (Jobs) scenario tests: the 9 requirement predicates,
completion -> discard -> reveal-next, claiming each of the 4 board
bonuses (including Skill-pile exhaustion), multiple simultaneous
completions in one command, resuming an interrupted step, and rejecting
an already-claimed column without mutating anything.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import ChooseJobReward, ChooseSkillToDiscard, PlaceCriminal
from dope_engine.domain.entities import OfficerLocationType, OfficerState, PawnLocation
from dope_engine.domain.enums import ActiveStep, DopeType, OfficerType, PawnRole
from dope_engine.domain.ids import GameId, JobId, OfficerId
from dope_engine.rules import economy, jobs
from dope_engine.rules.setup import create_initial_state


def _job_by_id(game_data):
    return {j.job_id: j for j in game_data.jobs}


def _bus(game_data, price_tracks, link_extra_action_types, action_type_by_card_id):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    job_by_id = _job_by_id(game_data)
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
    )
    jobs.register_handlers(bus, job_by_id=job_by_id)
    jobs.register_post_success_hook(bus, job_by_id=job_by_id)
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _set_revealed_job(state, game_data, player_id, job_id: str) -> None:
    """Force a specific Job to be the one currently revealed for its
    tier, for deterministic test setup (a fresh game's own reveal is
    seed-derived and not otherwise convenient to target). Also strips
    `job_id` out of that tier's own pile: a real player's pile+revealed
    is always a partition of the tier's 3 distinct Jobs, and leaving a
    stale duplicate in the pile would let the same Job reappear when the
    pile is later popped."""
    job_def = next(j for j in game_data.jobs if j.job_id == job_id)
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_def.tier] = JobId(job_id)
    progress.tier_piles[job_def.tier] = [
        jid for jid in progress.tier_piles[job_def.tier] if jid != job_id
    ]


def _action_type_by_card_id(game_data):
    return {c.card_id: c.action_type for c in game_data.customer_cards}


# --- requirement predicates -------------------------------------------------


def test_win_brawls_requirement(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "win_brawls")
    assert not jobs._check_requirement(state, player, job.requirement)
    player.brawls_won_count = job.requirement["count"]
    assert jobs._check_requirement(state, player, job.requirement)


def test_own_officers_requirement_is_a_snapshot_not_a_cumulative_count(game_data) -> None:
    """Reversed 2026-08-23 (RULES_CANONICAL.md §A10): "Abbi 1 Cop/Fed"
    counts Cops/Feds owned *right now* in the Covo, not how many were
    ever bought — a Cop bought from an opponent and then lost again no
    longer counts, same "snapshot, not cumulative" shape as Job 4's own
    "Abbi 3 Rats" (test_own_rats_requirement_is_a_snapshot_not_a_cumulative_count)."""
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_officers")
    assert not jobs._check_requirement(state, player, job.requirement)
    officer_id = OfficerId("officer_test_cop")
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.BASE,
        owner_player_id=player.player_id,
    )
    assert jobs._check_requirement(state, player, job.requirement)


def test_win_poker_matches_requirement(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "win_poker_matches")
    player.poker_matches_won_count = job.requirement["count"] - 1
    assert not jobs._check_requirement(state, player, job.requirement)
    player.poker_matches_won_count = job.requirement["count"]
    assert jobs._check_requirement(state, player, job.requirement)


def test_own_money_requirement(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_money")
    player.money = job.requirement["count"] - 1
    assert not jobs._check_requirement(state, player, job.requirement)
    player.money = job.requirement["count"]
    assert jobs._check_requirement(state, player, job.requirement)


def test_own_rats_requirement_is_a_snapshot_not_a_cumulative_count(game_data) -> None:
    """Confirmed 2026-08-01: "Abbi 3 Rats" counts Rats owned *right now*,
    not how many were ever sent to Jail — a Rat that already escaped no
    longer counts."""
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_rats")
    pawn_ids = player.pawn_ids[: job.requirement["count"]]
    for pid in pawn_ids:
        state.pawns[pid].role = PawnRole.RAT
    assert jobs._check_requirement(state, player, job.requirement)

    # One Rat escapes back to base: the requirement is no longer met.
    state.pawns[pawn_ids[0]].role = PawnRole.IN_BASE
    assert not jobs._check_requirement(state, player, job.requirement)


def test_own_links_requirement(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_links")
    for pid in player.pawn_ids[: job.requirement["count"] - 1]:
        state.pawns[pid].role = PawnRole.LINK
    assert not jobs._check_requirement(state, player, job.requirement)
    extra_pid = player.pawn_ids[job.requirement["count"] - 1]
    state.pawns[extra_pid].role = PawnRole.LINK
    assert jobs._check_requirement(state, player, job.requirement)


def test_criminals_in_distinct_hoods_requirement(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "criminals_in_distinct_hoods")
    hood_ids = list(state.board.hoods.keys())[: job.requirement["count"]]
    for pid, hood_id in zip(player.pawn_ids, hood_ids, strict=False):
        state.pawns[pid].role = PawnRole.CRIMINAL
        state.pawns[pid].location = PawnLocation.hood(hood_id)
    assert jobs._check_requirement(state, player, job.requirement)

    # Same distinct-hood count, but not enough pawns actually deployed.
    state.pawns[player.pawn_ids[0]].role = PawnRole.IN_BASE
    state.pawns[player.pawn_ids[0]].location = PawnLocation.base()
    assert not jobs._check_requirement(state, player, job.requirement)


def test_criminals_out_of_base_requirement_counts_any_non_base_role(game_data) -> None:
    """Confirmed 2026-08-01: Link/Gambler/Rat pawns count too, not only
    ones still literally in Criminal role."""
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "criminals_out_of_base")
    roles = [PawnRole.CRIMINAL, PawnRole.LINK, PawnRole.GAMBLER, PawnRole.RAT]
    for i, pid in enumerate(player.pawn_ids[: job.requirement["count"]]):
        state.pawns[pid].role = roles[i % len(roles)]
    assert jobs._check_requirement(state, player, job.requirement)


def test_own_dope_in_base_requirement_needs_one_of_each_type(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_dope_in_base")
    assert job.requirement.get("at_least_one_per_type") is True

    # Enough total, but missing one type entirely.
    player.base_inventory.dope_counts = {DopeType.CAMALEONTE: job.requirement["count"]}
    assert not jobs._check_requirement(state, player, job.requirement)

    player.base_inventory.dope_counts = dict.fromkeys(DopeType, 1)
    assert jobs._check_requirement(state, player, job.requirement)


# --- completion detection ----------------------------------------------


def test_completion_discards_and_reveals_next_job_of_same_tier(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == player_id)
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_money")
    _set_revealed_job(state, game_data, player_id, job.job_id)
    progress = state.jobs.progress_by_player[player_id]
    pile_before = list(progress.tier_piles[job.tier])
    player.money = job.requirement["count"]

    events: list = []
    job_by_id = _job_by_id(game_data)
    jobs.check_and_queue_completions(state, events, job_by_id)

    assert progress.revealed_job_id_by_tier[job.tier] != job.job_id
    if pile_before:
        assert progress.revealed_job_id_by_tier[job.tier] == pile_before[0]
        assert progress.tier_piles[job.tier] == pile_before[1:]
    completed = next(e for e in events if type(e).__name__ == "JobCompleted")
    assert completed.job_id == job.job_id
    assert completed.player_id == player_id
    assert state.active_step == ActiveStep.WAITING_FOR_JOB_REWARD
    assert state.current_player_id == player_id
    assert state.pending_job_reward is not None
    assert state.pending_job_reward.queue[0].job_id == job.job_id


def test_satisfying_a_job_not_currently_revealed_does_not_complete_it(game_data) -> None:
    """Verified per the game designer (2026-08-15): a Job only completes
    if it's currently one of the player's 3 revealed cards (1 per tier) —
    satisfying its requirement while some *other* Job of that tier is
    revealed instead never banks it. Once that tier's revealed Job later
    becomes this one (by completing the currently-revealed one, or — as
    tested here — by directly forcing it for a deterministic scenario),
    the very same still-true condition is re-checked and completes it."""
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == player_id)
    target_job = next(
        j for j in game_data.jobs if j.requirement["type"] == "criminals_in_distinct_hoods"
    )
    other_job = next(
        j for j in game_data.jobs if j.tier == target_job.tier and j.job_id != target_job.job_id
    )
    _set_revealed_job(state, game_data, player_id, other_job.job_id)

    hood_ids = list(state.board.hoods.keys())[: target_job.requirement["count"]]
    for pid, hood_id in zip(player.pawn_ids, hood_ids, strict=False):
        state.pawns[pid].role = PawnRole.CRIMINAL
        state.pawns[pid].location = PawnLocation.hood(hood_id)
    assert jobs._check_requirement(state, player, target_job.requirement)

    job_by_id = _job_by_id(game_data)
    events: list = []
    jobs.check_and_queue_completions(state, events, job_by_id)

    assert state.pending_job_reward is None
    assert not any(
        type(e).__name__ == "JobCompleted" and e.job_id == target_job.job_id for e in events
    )
    progress = state.jobs.progress_by_player[player_id]
    assert progress.revealed_job_id_by_tier[target_job.tier] == other_job.job_id

    # The condition is still true; once this tier's revealed Job becomes
    # the target one, it must be picked up without any further change.
    _set_revealed_job(state, game_data, player_id, target_job.job_id)
    later_events: list = []
    jobs.check_and_queue_completions(state, later_events, job_by_id)

    assert state.pending_job_reward is not None
    completed = next(e for e in later_events if type(e).__name__ == "JobCompleted")
    assert completed.job_id == target_job.job_id
    assert completed.player_id == player_id


def test_multiple_players_completing_the_same_job_queue_in_player_order(game_data) -> None:
    state, _ = _new_game(game_data)
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_money")
    for player in state.players:
        _set_revealed_job(state, game_data, player.player_id, job.job_id)
        player.money = job.requirement["count"]

    events: list = []
    job_by_id = _job_by_id(game_data)
    jobs.check_and_queue_completions(state, events, job_by_id)

    assert state.pending_job_reward is not None
    queued_players = [e.player_id for e in state.pending_job_reward.queue]
    assert queued_players == state.player_order
    completed_events = [e for e in events if type(e).__name__ == "JobCompleted"]
    assert len(completed_events) == 4


def test_check_and_queue_completions_pauses_and_stashes_resume_point(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == player_id)
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_money")
    _set_revealed_job(state, game_data, player_id, job.job_id)
    player.money = job.requirement["count"]

    # Simulate this completion firing mid-way through an unrelated step.
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    other_player_id = state.player_order[1]
    state.current_player_id = other_player_id

    events: list = []
    job_by_id = _job_by_id(game_data)
    jobs.check_and_queue_completions(state, events, job_by_id)

    assert state.pending_job_reward is not None
    assert state.pending_job_reward.resume_player_id == other_player_id
    assert state.pending_job_reward.resume_active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    assert state.current_player_id == player_id
    assert state.active_step == ActiveStep.WAITING_FOR_JOB_REWARD


# --- claiming the bonus -----------------------------------------------


def _complete_one_job(state, game_data, player_id, requirement_type):
    job = next(j for j in game_data.jobs if j.requirement["type"] == requirement_type)
    _set_revealed_job(state, game_data, player_id, job.job_id)
    player = next(p for p in state.players if p.player_id == player_id)
    if requirement_type == "own_money":
        player.money = job.requirement["count"]
    else:  # pragma: no cover - only own_money used by these tests
        raise NotImplementedError
    events: list = []
    job_by_id = _job_by_id(game_data)
    jobs.check_and_queue_completions(state, events, job_by_id)
    return job


def test_claim_link_bonus_creates_level_one_link_from_a_fresh_base_pawn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = _complete_one_job(state, game_data, player_id, "own_money")
    link_column = state.configuration["job_board_column_bonuses"].index("link")

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=link_column,
            contact_id=job.contact_ids[0] if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    cell = next(
        c for c in new_state.jobs.board if c.job_id == job.job_id and c.column_index == link_column
    )
    assert cell.player_id == player_id
    link_pawns = [
        pid
        for pid in next(p for p in new_state.players if p.player_id == player_id).pawn_ids
        if new_state.pawns[pid].role == PawnRole.LINK
    ]
    assert len(link_pawns) == 1
    assert new_state.pawns[link_pawns[0]].link_level == 1


def test_claim_two_cards_bonus_draws_two_cards(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("two_cards")
    player = next(p for p in state.players if p.player_id == player_id)
    hand_before = len(player.hand_card_ids)

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=job.contact_ids[0] if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player_id)
    assert len(new_player.hand_card_ids) == hand_before + 2


def test_claim_skill_bonus_grants_a_skill_and_shrinks_the_pile(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("skill")
    contact_id = job.contact_ids[0]
    pile_before = len(state.skills.remaining_by_contact[contact_id])

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=contact_id if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    new_player = next(p for p in new_state.players if p.player_id == player_id)
    assert len(new_player.skill_ids) == 1
    assert len(new_state.skills.remaining_by_contact[contact_id]) == pile_before - 1


def test_claim_skill_bonus_with_exhausted_pile_grants_nothing(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("skill")
    contact_id = job.contact_ids[0]
    state.skills.remaining_by_contact[contact_id] = []

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=contact_id if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player_id)
    assert new_player.skill_ids == []


def _give_player_a_skill(
    state, game_data, player_id, *, origin_job_id, origin_column, other_columns_claimed=()
):
    """Directly grants one Skill (bypassing the normal claim flow) with a
    tracked origin cell — mirrors the bookkeeping
    _handle_choose_job_reward's own SKILL branch does, for tests that
    need a player already sitting at the cap. `other_columns_claimed`
    pre-fills some of the origin row's *other* columns with an arbitrary
    other player, to test the "no free column left to relocate to" case."""
    player = next(p for p in state.players if p.player_id == player_id)
    skill_id = next(s.skill_id for s in game_data.skills if s.skill_id not in player.skill_ids)
    player.skill_ids.append(skill_id)
    player.skill_source_by_id[skill_id] = (origin_job_id, origin_column)
    origin_cell = next(
        c for c in state.jobs.board if c.job_id == origin_job_id and c.column_index == origin_column
    )
    origin_cell.player_id = player_id
    other_player_id = next(p.player_id for p in state.players if p.player_id != player_id)
    for column in other_columns_claimed:
        cell = next(
            c for c in state.jobs.board if c.job_id == origin_job_id and c.column_index == column
        )
        cell.player_id = other_player_id
    return skill_id


def test_claiming_a_skill_bonus_records_its_origin_cell(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("skill")

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=job.contact_ids[0] if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player_id)
    (skill_id,) = new_player.skill_ids
    assert new_player.skill_source_by_id[skill_id] == (job.job_id, column)


def test_skill_column_offers_the_discard_subflow_at_the_cap(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """A player already holding skill_cap (3) Skills, at least one of
    which has a free column elsewhere on its own row, still gets the
    SKILL column offered — claiming it pauses at
    WAITING_FOR_SKILL_DISCARD_CHOICE instead of granting immediately."""
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    other_jobs = [j.job_id for j in game_data.jobs][:3]
    for i, origin_job_id in enumerate(other_jobs):
        _give_player_a_skill(
            state, game_data, player_id, origin_job_id=origin_job_id, origin_column=i
        )
    assert state.configuration["skill_cap"] == 3

    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("skill")
    contact_id = job.contact_ids[0]

    decision = get_legal_decision(
        state,
        player_id,
        price_tracks,
        link_extra_action_types,
        job_by_id=_job_by_id(game_data),
    )
    assert decision is not None
    assert any(o.payload["column_index"] == column for o in decision.options)

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=contact_id if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.active_step == ActiveStep.WAITING_FOR_SKILL_DISCARD_CHOICE
    new_player = next(p for p in new_state.players if p.player_id == player_id)
    assert len(new_player.skill_ids) == 3  # not granted yet
    assert new_state.pending_job_reward is not None
    assert new_state.pending_job_reward.stalled_column_index == column


def test_choose_skill_to_discard_relocates_rep_and_grants_the_new_skill(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    other_jobs = [j.job_id for j in game_data.jobs][:3]
    skill_ids = [
        _give_player_a_skill(state, game_data, player_id, origin_job_id=job_id, origin_column=0)
        for job_id in other_jobs
    ]
    discarded_skill_id, origin_job_id = skill_ids[0], other_jobs[0]
    # Stain the origin cell to confirm the stain travels with the token.
    origin_cell = next(
        c for c in state.jobs.board if c.job_id == origin_job_id and c.column_index == 0
    )
    origin_cell.stained = True

    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("skill")
    contact_id = job.contact_ids[0]
    claim_outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=contact_id if len(job.contact_ids) > 1 else None,
        ),
    )
    assert isinstance(claim_outcome, CommandSuccess), claim_outcome
    state = claim_outcome.state
    assert state.active_step == ActiveStep.WAITING_FOR_SKILL_DISCARD_CHOICE

    outcome = bus.dispatch(
        state,
        ChooseSkillToDiscard(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            skill_id=discarded_skill_id,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    new_player = next(p for p in new_state.players if p.player_id == player_id)
    assert len(new_player.skill_ids) == 3  # bumped one, gained one
    assert discarded_skill_id not in new_player.skill_ids
    assert discarded_skill_id not in new_player.skill_source_by_id

    new_origin_cell = next(
        c for c in new_state.jobs.board if c.job_id == origin_job_id and c.column_index == 0
    )
    assert new_origin_cell.player_id is None
    assert new_origin_cell.stained is False
    relocated_cells = [
        c
        for c in new_state.jobs.board
        if c.job_id == origin_job_id and c.column_index != 0 and c.player_id == player_id
    ]
    assert len(relocated_cells) == 1
    assert relocated_cells[0].stained is True

    # The current Job's own SKILL column is now actually claimed.
    current_cell = next(
        c for c in new_state.jobs.board if c.job_id == job.job_id and c.column_index == column
    )
    assert current_cell.player_id == player_id
    assert new_state.active_step != ActiveStep.WAITING_FOR_SKILL_DISCARD_CHOICE
    assert new_state.pending_job_reward is None


def test_skill_column_not_offered_when_no_skill_is_discardable(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """All 3 held Skills' origin rows are fully claimed (no column left
    to relocate to) — the SKILL column must not be offered at all."""
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    columns_per_row = state.configuration["job_board_columns_per_row"]
    other_jobs = [j.job_id for j in game_data.jobs][:3]
    for origin_job_id in other_jobs:
        _give_player_a_skill(
            state,
            game_data,
            player_id,
            origin_job_id=origin_job_id,
            origin_column=0,
            other_columns_claimed=range(1, columns_per_row),
        )

    _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("skill")

    decision = get_legal_decision(
        state,
        player_id,
        price_tracks,
        link_extra_action_types,
        job_by_id=_job_by_id(game_data),
    )
    assert decision is not None
    assert all(o.payload["column_index"] != column for o in decision.options)


def test_choose_skill_to_discard_rejects_a_non_discardable_skill(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    columns_per_row = state.configuration["job_board_columns_per_row"]
    other_jobs = [j.job_id for j in game_data.jobs][:3]
    skill_ids = []
    for i, origin_job_id in enumerate(other_jobs):
        # Only the *first* Skill (index 0) is left discardable.
        blocked = () if i == 0 else range(1, columns_per_row)
        skill_ids.append(
            _give_player_a_skill(
                state,
                game_data,
                player_id,
                origin_job_id=origin_job_id,
                origin_column=0,
                other_columns_claimed=blocked,
            )
        )

    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("skill")
    contact_id = job.contact_ids[0]
    claim_outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=contact_id if len(job.contact_ids) > 1 else None,
        ),
    )
    assert isinstance(claim_outcome, CommandSuccess), claim_outcome
    state = claim_outcome.state

    outcome = bus.dispatch(
        state,
        ChooseSkillToDiscard(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            skill_id=skill_ids[1],  # the non-discardable one
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "skill_not_discardable"


def test_claim_none_bonus_does_nothing_but_still_claims_the_column(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("none")

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=job.contact_ids[0] if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    cell = next(
        c for c in new_state.jobs.board if c.job_id == job.job_id and c.column_index == column
    )
    assert cell.player_id == player_id
    # No side effects: back to the resumed step, nothing pending.
    assert new_state.pending_job_reward is None


def test_claiming_reward_resumes_the_interrupted_step(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_money")
    _set_revealed_job(state, game_data, player_id, job.job_id)
    player = next(p for p in state.players if p.player_id == player_id)
    player.money = job.requirement["count"]
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS

    events: list = []
    job_by_id = _job_by_id(game_data)
    jobs.check_and_queue_completions(state, events, job_by_id)
    assert state.active_step == ActiveStep.WAITING_FOR_JOB_REWARD

    column = state.configuration["job_board_column_bonuses"].index("none")
    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=job.contact_ids[0] if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    assert outcome.state.current_player_id == player_id
    assert outcome.state.pending_job_reward is None


def test_choose_job_reward_rejects_already_claimed_column_without_mutating_state(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("none")
    cell = next(c for c in state.jobs.board if c.job_id == job.job_id and c.column_index == column)
    cell.player_id = state.player_order[1]  # pretend someone else already has it

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=job.contact_ids[0] if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "column_already_claimed"
    # The original state object handed to dispatch() must be untouched —
    # the command bus only ever mutates its own deep copy.
    assert state.pending_job_reward is not None
    assert state.pending_job_reward.queue[0].job_id == job.job_id


def test_choose_job_reward_wrong_player_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    # A genuinely different player than whoever completes the Job below —
    # not hardcoded to player_order[1], which can coincide with
    # current_player_id depending on the seed's own first-player draw.
    other_player_id = next(pid for pid in state.player_order if pid != player_id)
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = _complete_one_job(state, game_data, player_id, "own_money")
    column = state.configuration["job_board_column_bonuses"].index("none")

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=other_player_id,
            expected_revision=state.revision,
            column_index=column,
            contact_id=job.contact_ids[0] if len(job.contact_ids) > 1 else None,
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_player"


def test_place_criminal_triggers_job_completion_via_post_success_hook(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """End-to-end: a normal economy command's post-success hook detects
    and queues the completion, without any Job-specific code in
    economy.py itself."""
    state, _ = _new_game(game_data)
    player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == player_id)
    bus = _bus(game_data, price_tracks, link_extra_action_types, _action_type_by_card_id(game_data))
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_money")
    _set_revealed_job(state, game_data, player_id, job.job_id)
    player.money = job.requirement["count"] + 10  # stays above the threshold after paying $2
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = None
    from dope_engine.domain.enums import ActionType

    player.pending_action_type = ActionType.PLACE_CRIMINAL
    player.current_round_grit_value = 1
    hood_id = next(h.hood_id for h in state.board.hoods.values() if h.revealed and h.capacity > 0)

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            hood_ids=(hood_id,),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.active_step == ActiveStep.WAITING_FOR_JOB_REWARD
    assert outcome.state.pending_job_reward is not None
    assert outcome.state.pending_job_reward.queue[0].job_id == job.job_id
