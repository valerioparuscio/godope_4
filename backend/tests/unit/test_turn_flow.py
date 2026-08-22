from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import ChooseGritAction, PassOptionalStep
from dope_engine.domain.enums import ActiveStep, GamePhase, GameStatus, PawnRole
from dope_engine.domain.ids import ContactId, GameId
from dope_engine.domain.invariants import validate_invariants
from dope_engine.rules import links
from dope_engine.rules.setup import create_initial_state
from dope_engine.rules.turn_flow import register_handlers


def _bus(game_data):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    register_handlers(bus, card_contact_by_id=card_contact_by_id)
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _grit(state, player_id, value):
    return ChooseGritAction(
        game_id=state.game_id,
        player_id=player_id,
        expected_revision=state.revision,
        grit_value=value,
    )


def _pass(state, player_id):
    return PassOptionalStep(
        game_id=state.game_id, player_id=player_id, expected_revision=state.revision
    )


def test_game_boots_directly_into_action_phase(game_data) -> None:
    state, events = _new_game(game_data)

    assert state.phase is GamePhase.ACTION_PHASE
    # §D2 (confirmed 2026-08-01): the Poker-launch offer is no longer a
    # "prima" step ahead of Grit — it only fires from
    # rules/economy.py::_handle_choose_action_type, once the round's
    # action_type is actually chosen and a matching Preti card is held.
    # A fresh round therefore still starts at the Grit pick.
    assert state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION
    assert state.turn_index == 1
    assert state.action_round_index == 1
    assert state.current_player_id == state.first_player_id
    event_types = [type(e).__name__ for e in events]
    assert event_types == ["GameStarted", "RaidRevealed", "TurnStarted"]


def test_choose_grit_action_then_pass_advances_to_next_player(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    first_player = state.current_player_id
    assert state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION

    outcome = bus.dispatch(state, _grit(state, first_player, 2))
    assert isinstance(outcome, CommandSuccess)
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player = next(p for p in state.players if p.player_id == first_player)
    assert 2 not in player.available_grit_values

    outcome = bus.dispatch(state, _pass(state, first_player))
    assert isinstance(outcome, CommandSuccess)
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION
    assert state.current_player_id != first_player


def test_hand_limit_is_checked_after_every_round_not_just_the_last(game_data) -> None:
    """RULES_PENDING.md #12/#17 REVERSED (game designer, 2026-08-15): the
    5-card limit is now enforced at the end of *every* round (up to 9 per
    player per game — 3 turns x 3 rounds), not only a player's 3rd/last
    round of the turn as the 2026-08-01 decision this supersedes had it."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    first_player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == first_player_id)
    player.hand_card_ids = ["card_001", "card_002", "card_003", "card_004", "card_005", "card_006"]
    assert state.action_round_index == 1

    outcome = bus.dispatch(state, _grit(state, first_player_id, player.available_grit_values[0]))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    outcome = bus.dispatch(state, _pass(state, first_player_id))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    assert state.action_round_index == 1
    assert state.current_player_id == first_player_id
    assert state.active_step is ActiveStep.WAITING_FOR_HAND_DISCARD


def test_wrong_player_is_rejected(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    other_player = next(p for p in state.player_order if p != state.current_player_id)

    outcome = bus.dispatch(state, _grit(state, other_player, 1))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_player"


def test_unavailable_grit_value_is_rejected(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id

    outcome = bus.dispatch(state, _grit(state, player_id, 9))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "grit_value_unavailable"


def test_wrong_step_is_rejected(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    player_id = state.current_player_id
    assert state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION

    outcome = bus.dispatch(state, _pass(state, player_id))

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_active_step"


def test_full_game_reaches_finished_deterministically(game_data) -> None:
    """Registers `rules/jobs.py`'s handlers/hook too (unlike the shared
    `_bus()` other tests in this file use) — 2026-08-17: `_end_turn` no
    longer finalizes the game directly once the last turn ends, it only
    sets `GameState.pending_game_end`; finalizing now happens from
    `rules/jobs.py`'s own post-success hook once nothing is left to
    complete, so this game-completing test needs that hook present or
    the game would never actually reach FINISHED. No Job ever completes
    in this grit-only/no-economy scenario (every requirement needs an
    action this bus doesn't even register a handler for), so this is a
    pure no-op hook here and the step count is unaffected."""
    from dope_engine.rules import jobs

    def run(seed: int) -> tuple:
        state, _ = _new_game(game_data, seed=seed)
        bus = _bus(game_data)
        job_by_id = {j.job_id: j for j in game_data.jobs}
        jobs.register_handlers(bus, job_by_id=job_by_id)
        jobs.register_post_success_hook(bus, job_by_id=job_by_id)
        steps = 0
        while state.status is not GameStatus.FINISHED and steps < 500:
            steps += 1
            player_id = state.current_player_id
            if state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION:
                player = next(p for p in state.players if p.player_id == player_id)
                command = _grit(state, player_id, player.available_grit_values[0])
            else:
                command = _pass(state, player_id)
            outcome = bus.dispatch(state, command)
            assert isinstance(outcome, CommandSuccess), outcome
            state = outcome.state
            validate_invariants(state)
        return state, steps

    state_a, steps_a = run(seed=42)
    state_b, steps_b = run(seed=42)

    assert state_a.status is GameStatus.FINISHED
    assert state_a.phase is GamePhase.FINISHED
    assert state_a.turn_index == 3
    # 3 turns x 4 players x 3 rounds x 2 commands each: grit, decline the
    # post-main offer down to round-end. (This bus doesn't register
    # rules/economy.py, so ChooseActionType — the only thing that can
    # ever trigger the Poker-launch offer — never happens.)
    assert steps_a == 72
    assert steps_a == steps_b
    assert state_a == state_b
    # Milestone 5 (Stage 3): the phase sequence passes through
    # END_GAME_SCORING (rules/turn_flow.py::_end_turn) before FINISHED,
    # computing a real final_score along the way.
    assert state_a.final_score is not None
    assert len(state_a.final_score.winner_ids) >= 1


def test_job_completed_by_the_last_turns_own_outcome_resolves_before_scoring(
    game_data,
) -> None:
    """Bug (game designer, 2026-08-17): a Job only satisfiable by the last
    turn's own outcome (e.g. a Poker win, a Raid escape) used to never get
    a chance to complete — `_end_turn` computed the final score and
    finished the game synchronously, before `rules/jobs.py`'s
    post-success hook (which runs *after* the whole command, including
    `_end_turn`) ever ran. Reproduced here without Poker/Raids
    specifically: force `win_brawls` count 1 (job_01, tier 1) already
    satisfied and freshly revealed on the very last step of the game —
    the game must *not* jump straight to FINISHED, must offer
    WAITING_FOR_JOB_REWARD instead, and only finish (with the bonus
    already banked) once that reward is claimed."""
    from dope_engine.domain.commands import ChooseJobReward
    from dope_engine.domain.ids import JobId
    from dope_engine.rules import jobs

    state, _ = _new_game(game_data, seed=42)
    bus = _bus(game_data)
    job_by_id = {j.job_id: j for j in game_data.jobs}
    jobs.register_handlers(bus, job_by_id=job_by_id)
    jobs.register_post_success_hook(bus, job_by_id=job_by_id)

    # Replay the exact same 71 steps the deterministic test above proved
    # reach the last turn's final command, then intercept right before it.
    for _ in range(71):
        player_id = state.current_player_id
        if state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION:
            player = next(p for p in state.players if p.player_id == player_id)
            command = _grit(state, player_id, player.available_grit_values[0])
        else:
            command = _pass(state, player_id)
        outcome = bus.dispatch(state, command)
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state
    assert state.status is not GameStatus.FINISHED

    final_player_id = state.current_player_id
    final_player = next(p for p in state.players if p.player_id == final_player_id)
    final_player.brawls_won_count = 1
    progress = state.jobs.progress_by_player[final_player_id]
    # Force-revealing job_01 as the *current* tier-1 job needs job_01 gone
    # from the tier's own remaining pile too — otherwise, once completed,
    # `check_and_queue_completions` pops the pile's front for the *next*
    # reveal and can draw job_01 right back out again (still sitting there
    # unconsumed), completing it a second time.
    tier_1_pile = progress.tier_piles[1]
    if JobId("job_01") in tier_1_pile:
        tier_1_pile.remove(JobId("job_01"))
    progress.revealed_job_id_by_tier[1] = JobId("job_01")
    free_column = next(
        c.column_index
        for c in state.jobs.board
        if c.job_id == "job_01" and c.player_id is None
    )

    final_command = (
        _grit(state, final_player_id, final_player.available_grit_values[0])
        if state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION
        else _pass(state, final_player_id)
    )
    outcome = bus.dispatch(state, final_command)
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    # Not finished yet — the freshly-completed Job's reward is pending.
    assert state.status is not GameStatus.FINISHED
    assert state.active_step == ActiveStep.WAITING_FOR_JOB_REWARD
    assert state.pending_job_reward is not None
    assert state.pending_job_reward.queue[0].job_id == "job_01"
    assert state.pending_job_reward.queue[0].player_id == final_player_id
    assert state.final_score is None

    outcome = bus.dispatch(
        state,
        ChooseJobReward(
            game_id=state.game_id,
            player_id=final_player_id,
            expected_revision=state.revision,
            column_index=free_column,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    # Claim whatever else the same hook pass also queued (this scenario's
    # own forced mutation can coincidentally satisfy more than just
    # job_01 — the exact count isn't the point of this test) until the
    # game actually finishes.
    guard = 0
    while state.pending_job_reward is not None and guard < 20:
        guard += 1
        entry = state.pending_job_reward.queue[0]
        entry_job = job_by_id[entry.job_id]
        entry_column = next(
            c.column_index
            for c in state.jobs.board
            if c.job_id == entry.job_id and c.player_id is None
        )
        outcome = bus.dispatch(
            state,
            ChooseJobReward(
                game_id=state.game_id,
                player_id=entry.player_id,
                expected_revision=state.revision,
                column_index=entry_column,
                contact_id=entry_job.contact_ids[0] if len(entry_job.contact_ids) > 1 else None,
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state

    assert state.status is GameStatus.FINISHED
    assert state.phase is GamePhase.FINISHED
    assert state.final_score is not None
    validate_invariants(state)


def test_next_player_with_unused_link_is_offered_extra_action_before_grit(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data)
    first_player_id = state.current_player_id
    start = state.player_order.index(first_player_id)
    rotation = state.player_order[start:] + state.player_order[:start]
    second_player_id = rotation[1]
    second_player = next(p for p in state.players if p.player_id == second_player_id)
    link_pawn_id = next(
        pid for pid in second_player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    links.insert_link(state, second_player_id, link_pawn_id, ContactId("manager"), 1, [])

    outcome = bus.dispatch(state, _grit(state, first_player_id, 1))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    outcome = bus.dispatch(state, _pass(state, first_player_id))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    assert state.current_player_id == second_player_id
    assert state.active_step is ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    outcome = bus.dispatch(state, _pass(state, second_player_id))
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step is ActiveStep.WAITING_FOR_GRIT_ACTION
    new_second_player = next(p for p in state.players if p.player_id == second_player_id)
    assert new_second_player.extra_actions_used_this_round == 0
