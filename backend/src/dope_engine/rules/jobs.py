"""Jobs (RULES_CANONICAL.md §A10): automatic completion detection, board
claim, and bonus banking.

Completion is checked by `check_and_queue_completions`, a
`CommandBus` post-success hook (see `application/command_bus.py`)
registered once in `application/game_service.py` so it runs after
*every* accepted command, per CLAUDE.md §11.12 ("Il backend deve
verificare automaticamente il completamento dei Job dopo ogni evento
potenzialmente rilevante"). It loops until a full pass finds nothing new
(a completion can itself reveal an already-satisfied next Job, or a
Link/2-cards bonus can complete another Job outright), then queues one
`PendingJobRewardEntry` per completion, in deterministic
(`player_order`, then tier) order, and pauses whatever step was
interrupted (`GameState.pending_job_reward`) — the same "stash and
resume" shape as `BrawlProgress`/`CorruptionProgress`.

Confirmed by the game designer (2026-08-01):
- The 4 board columns (Skill / Link / 2 cards / Nothing) are the *same*
  on every Job's row (`game_config.json::job_board_column_bonuses`), not
  a per-Job table: the first player to complete a given Job picks freely
  among all 4; later completers of that same Job (each player owns their
  own copy) pick among whatever's still free on that row. Since at most
  4 players can ever complete one job_id (each exactly once) and there
  are exactly 4 columns, a free column always exists.
- A Job listing 2 Contacts lets the completing player freely choose
  either one to bank the bonus at.
- Job 8 ("Abbi tutti i 10 Criminali fuori dal Covo") counts any pawn not
  `IN_BASE`, regardless of current role (Link/Gambler/Rat all count).
- Job 4 ("Abbi 3 Rats") is a snapshot check (Rats owned *right now*), not
  a cumulative count of Rats ever sent to Jail.

PROVISIONAL (docs/rules/RULES_PENDING.md): if the Link bonus has no free
IN_BASE pawn to send, or the Skill bonus's Contact pile is already
empty, the bonus silently grants nothing rather than blocking — the
same "can't happen, but if it does, degrade gracefully" precedent used
elsewhere (e.g. Poker's Jail-full Gambler-arrest fallback).

PROVISIONAL (docs/rules/RULES_PENDING.md): the TWO_CARDS bonus can push
its recipient over the 5-card hand limit at a moment with no interactive
discard step available to catch it — the post-success hook fires for any
player, after any command, in any phase, so the recipient may not be the
player about to reach their own end-of-turn discard check this
game-turn. Same gap and same fix as `rules/brawl.py::
_enforce_bystander_hand_limit`: auto-discard down to the limit, at
random, right when it happens (found by a 2000-seed bot-only sweep).
"""

from __future__ import annotations

from typing import Any

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import ChooseJobReward
from dope_engine.domain.content import JobDefinition
from dope_engine.domain.entities import LocationType
from dope_engine.domain.enums import ActiveStep, JobBonusType, PawnRole
from dope_engine.domain.errors import DomainError
from dope_engine.domain.events import (
    DomainEvent,
    JobBonusClaimed,
    JobCompleted,
    SkillDrawn,
)
from dope_engine.domain.ids import ContactId, JobId
from dope_engine.domain.state import (
    GameState,
    JobRewardProgress,
    PendingJobRewardEntry,
    PlayerState,
    find_player,
)
from dope_engine.rules import economy, links
from dope_engine.rules.event_utils import emit as _emit


def register_handlers(bus: CommandBus, *, job_by_id: dict[JobId, JobDefinition]) -> None:
    bus.register(ChooseJobReward, lambda s, c: _handle_choose_job_reward(s, c, job_by_id))


def register_post_success_hook(bus: CommandBus, *, job_by_id: dict[JobId, JobDefinition]) -> None:
    bus.register_post_success_hook(
        lambda s, events: check_and_queue_completions(s, events, job_by_id)
    )


# --- requirement predicates ------------------------------------------------


def _check_requirement(
    state: GameState, player: PlayerState, requirement: dict[str, Any]
) -> bool:
    req_type = requirement["type"]
    count = requirement.get("count", 0)

    if req_type == "win_brawls":
        return player.brawls_won_count >= count
    if req_type == "buy_officers":
        return player.officers_bought_count >= count
    if req_type == "win_poker_matches":
        return player.poker_matches_won_count >= count
    if req_type == "own_money":
        return player.money >= count
    if req_type == "own_rats":
        return _pawn_role_count(state, player, PawnRole.RAT) >= count
    if req_type == "own_links":
        return _pawn_role_count(state, player, PawnRole.LINK) >= count
    if req_type == "criminals_out_of_base":
        return sum(
            1 for pid in player.pawn_ids if state.pawns[pid].role != PawnRole.IN_BASE
        ) >= count
    if req_type == "criminals_in_distinct_hoods":
        hood_ids = {
            state.pawns[pid].location.hood_id
            for pid in player.pawn_ids
            if state.pawns[pid].role == PawnRole.CRIMINAL
            and state.pawns[pid].location.type == LocationType.HOOD
        }
        return len(hood_ids) >= count
    if req_type == "own_dope_in_base":
        dope_counts = player.base_inventory.dope_counts
        if requirement.get("at_least_one_per_type") and any(
            dope_counts.get(dt, 0) < 1 for dt in state.market.price_index_by_dope_type
        ):
            return False
        return sum(dope_counts.values()) >= count

    raise ValueError(f"Unknown Job requirement type '{req_type}'.")


def _pawn_role_count(state: GameState, player: PlayerState, role: PawnRole) -> int:
    return sum(1 for pid in player.pawn_ids if state.pawns[pid].role == role)


# --- completion detection ---------------------------------------------------


def check_and_queue_completions(
    state: GameState, events: list[DomainEvent], job_by_id: dict[JobId, JobDefinition]
) -> None:
    newly_queued: list[PendingJobRewardEntry] = []
    progressed = True
    while progressed:
        progressed = False
        for player in state.players:
            progress = state.jobs.progress_by_player[player.player_id]
            for tier in sorted(progress.revealed_job_id_by_tier):
                job_id = progress.revealed_job_id_by_tier[tier]
                if job_id is None:
                    continue
                job_def = job_by_id[job_id]
                if not _check_requirement(state, player, job_def.requirement):
                    continue

                pile = progress.tier_piles[tier]
                next_job_id = pile.pop(0) if pile else None
                progress.revealed_job_id_by_tier[tier] = next_job_id
                _emit(
                    state,
                    events,
                    JobCompleted,
                    player_id=player.player_id,
                    job_id=job_id,
                    tier=tier,
                    next_job_id=next_job_id,
                )
                newly_queued.append(
                    PendingJobRewardEntry(player_id=player.player_id, job_id=job_id, tier=tier)
                )
                progressed = True

    if not newly_queued:
        return

    if state.pending_job_reward is None:
        state.pending_job_reward = JobRewardProgress(
            queue=newly_queued,
            resume_player_id=state.current_player_id,
            resume_active_step=state.active_step,
        )
        state.current_player_id = newly_queued[0].player_id
        state.active_step = ActiveStep.WAITING_FOR_JOB_REWARD
    else:
        state.pending_job_reward.queue.extend(newly_queued)


# --- claiming the bonus ------------------------------------------------


def _handle_choose_job_reward(
    state: GameState,
    command: ChooseJobReward,
    job_by_id: dict[JobId, JobDefinition],
) -> CommandOutcome:
    progress = state.pending_job_reward
    if (
        state.active_step != ActiveStep.WAITING_FOR_JOB_REWARD
        or progress is None
        or not progress.queue
    ):
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message="Not waiting for a Job reward choice.",
                details={"actual_step": state.active_step.value},
            )
        )
    entry = progress.queue[0]
    if entry.player_id != command.player_id:
        return CommandFailure(
            DomainError(
                code="wrong_player",
                message=f"Command issued by '{command.player_id}', but "
                f"it is '{entry.player_id}'s Job reward to claim.",
                details={"expected_player_id": entry.player_id},
            )
        )

    job_def = job_by_id[entry.job_id]
    columns_per_row = state.configuration["job_board_columns_per_row"]
    if not 0 <= command.column_index < columns_per_row:
        return CommandFailure(
            DomainError(
                code="invalid_column",
                message=f"Column {command.column_index} is out of range.",
                details={"columns_per_row": columns_per_row},
            )
        )
    cell = next(
        c
        for c in state.jobs.board
        if c.job_id == entry.job_id and c.column_index == command.column_index
    )
    if cell.player_id is not None:
        return CommandFailure(
            DomainError(
                code="column_already_claimed",
                message=f"Column {command.column_index} on Job '{entry.job_id}' is "
                f"already claimed.",
                details={},
            )
        )

    if len(job_def.contact_ids) > 1:
        if command.contact_id not in job_def.contact_ids:
            return CommandFailure(
                DomainError(
                    code="invalid_contact",
                    message=f"'{command.contact_id}' is not one of Job "
                    f"'{entry.job_id}''s Contacts.",
                    details={"allowed_contact_ids": job_def.contact_ids},
                )
            )
        contact_id: ContactId = command.contact_id
    else:
        contact_id = job_def.contact_ids[0]

    state.revision += 1
    events: list[DomainEvent] = []
    player = find_player(state, command.player_id)

    cell.player_id = command.player_id
    bonus_type = JobBonusType(state.configuration["job_board_column_bonuses"][command.column_index])

    skill_id = None
    link_pawn_id = None
    drawn_card_ids: tuple = ()

    if bonus_type == JobBonusType.SKILL:
        pile = state.skills.remaining_by_contact.get(contact_id, [])
        if pile:
            skill_id = pile.pop(0)
            player.skill_ids.append(skill_id)
            _emit(
                state,
                events,
                SkillDrawn,
                player_id=player.player_id,
                contact_id=contact_id,
                skill_id=skill_id,
            )
    elif bonus_type == JobBonusType.LINK:
        fresh_pawn_id = next(
            (pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE), None
        )
        if fresh_pawn_id is not None:
            link_pawn_id = fresh_pawn_id
            links.insert_link(state, player.player_id, fresh_pawn_id, contact_id, 1, events)
    elif bonus_type == JobBonusType.TWO_CARDS:
        drawn_card_ids = (
            economy.draw_card(state, contact_id, events, player.player_id),
            economy.draw_card(state, contact_id, events, player.player_id),
        )

    _emit(
        state,
        events,
        JobBonusClaimed,
        player_id=player.player_id,
        job_id=entry.job_id,
        column_index=command.column_index,
        bonus_type=bonus_type.value,
        contact_id=contact_id,
        skill_id=skill_id,
        link_pawn_id=link_pawn_id,
        drawn_card_ids=drawn_card_ids,
    )

    progress.queue.pop(0)
    if progress.queue:
        state.current_player_id = progress.queue[0].player_id
    else:
        assert progress.resume_player_id is not None
        assert progress.resume_active_step is not None
        state.current_player_id = progress.resume_player_id
        state.active_step = progress.resume_active_step
        state.pending_job_reward = None

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))
