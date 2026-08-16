"""Rissa/Brawl (RULES_CANONICAL.md §D1): triggered by rules/movement.py
the instant a Move brings the 5th Criminal into a Hood — never by
Placement (rules/economy.py caps Placement below that count).

A genuine 3-phase interactive sub-flow, since each phase needs to see
the *outcome* of the previous one before the next can be offered:
declare (ActiveStep.WAITING_FOR_BRAWL_CARD — each participant, in turn,
plays one hand card face-down or passes), reveal (WAITING_FOR_
BRAWL_ASSIGNMENT — same order, each participant with a played card
reveals it and sends all its Gun symbols to one target), reward
(WAITING_FOR_BRAWL_REWARD — the winner resolves 3 things in sequence for
each defeated participant: money-or-card, an optional Link evolution of
their own, and where the defeated Criminals go). `state.pending_brawl`
(a `BrawlProgress`) tracks which of these sub-steps is active; nothing
about it is exposed in a player's GameView beyond what's already public
(a played-but-not-yet-revealed card's *identity* stays hidden, same as
any other hand card).

Confirmed by the game designer (2026-08-01, RULES_CANONICAL.md §D1):
- A revealed card's Guns all go to one target (self or one opponent),
  never split.
- The winner's money-vs-card choice is independent per defeated
  participant.
- The winner picks which unrevealed Hood the defeated Criminals go to.
- The final tie-break ("il primo giocatore, o seguenti") is seat
  rotation from `first_player_id`.
- Exactly *one* Criminal per defeated participant is sent away, even if
  they have more than one of their own physically in the Hood
  contributing to their Force — the rest stay put.
- Only players with at least one physical Criminal in the Hood
  participate. A Link at the Hood's Contact adds to an
  *already-participating* player's Force — all 3 levels' worth, if a
  player holds Links at more than one level there — but never makes a
  Link-only player (no Criminal there) a participant on its own
  (`compute_participants`). A card's own Guns range 0-4 depending on
  which card is played; there's no fixed per-Rissa Gun total.

One PROVISIONAL call remains (docs/rules/RULES_PENDING.md): a stolen
card is picked at random rather than chosen by the winner, since hands
are hidden information the winner has no in-fiction way to see into.

Confirmed by the game designer (2026-08-02): the 5-card hand limit is
checked *only* at the end of a player's own turn, full stop — a
"bystander" (any Rissa participant other than `resume_player_id`) who
receives a reward or relocation card mid-turn simply holds onto the
overflow until their own next end-of-turn check, even across phases.
No auto-discard for anyone but the acting player at their own turn's
end.

Known gap, not yet handled: relocating a defeated Criminal into a
just-revealed Hood does not itself re-check for a *new* Rissa there —
with the one-Criminal-per-loser rule above and only 4 players in the
game, at most 3 losers (and so at most 3 Criminals) can ever converge
on one freshly revealed (and therefore empty) Hood in a single
resolution, safely under its capacity; a nested trigger is still
deliberately not attempted (would need a stack of pending Brawls), and
the capacity check on the relocation itself is kept only as a
defensive fallback.
"""

from __future__ import annotations

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import (
    AssignBrawlGuns,
    ChooseBrawlLinkEvolution,
    ChooseBrawlLoserReward,
    ChooseBrawlRelocationDestination,
    PlayBrawlCard,
)
from dope_engine.domain.content import CoveredHoodTileDefinition
from dope_engine.domain.entities import HoodState, PawnLocation
from dope_engine.domain.enums import ActiveStep, GamePhase, PawnRole
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import (
    BrawlCardDeclared,
    BrawlGunsAssigned,
    BrawlLoserRewardChosen,
    BrawlResolved,
    BrawlStarted,
    CoveredHoodRevealed,
    DomainEvent,
    PawnDefeatedInBrawl,
)
from dope_engine.domain.ids import CardId, ContactId, HoodId, PawnId, PlayerId, TileId
from dope_engine.domain.rng import GameRandom
from dope_engine.domain.state import (
    BrawlProgress,
    GameState,
    LastBrawlOutcome,
    PlayerState,
    find_player,
)
from dope_engine.rules import economy, links, skills, turn_flow
from dope_engine.rules.event_utils import emit as _emit


def register_handlers(
    bus: CommandBus,
    *,
    gun_count_by_card_id: dict[CardId, int],
    card_contact_by_id: dict[CardId, ContactId],
    tile_by_id: dict[TileId, CoveredHoodTileDefinition],
) -> None:
    bus.register(PlayBrawlCard, lambda s, c: _handle_play_brawl_card(s, c, gun_count_by_card_id))
    bus.register(
        AssignBrawlGuns,
        lambda s, c: _handle_assign_brawl_guns(s, c, gun_count_by_card_id, card_contact_by_id),
    )
    bus.register(ChooseBrawlLoserReward, _handle_choose_brawl_loser_reward)
    bus.register(ChooseBrawlLinkEvolution, _handle_choose_brawl_link_evolution)
    bus.register(
        ChooseBrawlRelocationDestination,
        lambda s, c: _handle_choose_brawl_relocation_destination(s, c, tile_by_id),
    )


# --- starting a Rissa -------------------------------------------------


def compute_participants(state: GameState, hood: HoodState) -> set[PlayerId]:
    """§D1 (confirmed by the game designer): only players with at least
    one physical Criminal in this Hood participate. A Link at the
    Hood's Contact adds to an *already-participating* player's Force
    (see `_force_by_player`) — it never makes a player who has no
    Criminal here a participant on its own."""
    return {state.pawns[pid].owner_player_id for pid in hood.criminal_pawn_ids}


def _declaration_order(
    state: GameState, participants: set[PlayerId], triggering_player_id: PlayerId
) -> list[PlayerId]:
    start = state.player_order.index(triggering_player_id)
    rotation = state.player_order[start + 1 :] + state.player_order[: start + 1]
    return [player_id for player_id in rotation if player_id in participants]


def start_brawl(
    state: GameState,
    hood: HoodState,
    resume_player_id: PlayerId,
    remaining_moves: list[tuple[PawnId, HoodId, ContactId | None]],
    events: list[DomainEvent],
) -> None:
    participants = compute_participants(state, hood)
    order = _declaration_order(state, participants, resume_player_id)
    progress = BrawlProgress(
        hood_id=hood.hood_id,
        triggering_player_id=resume_player_id,
        participants=order,
        resume_player_id=resume_player_id,
        remaining_moves=list(remaining_moves),
    )
    state.pending_brawl = progress
    _emit(
        state,
        events,
        BrawlStarted,
        hood_id=hood.hood_id,
        triggering_player_id=resume_player_id,
        participant_ids=tuple(order),
    )

    if len(order) <= 1:
        # No opponent to fight: the sole participant wins by default,
        # nothing to declare/assign/reward.
        progress.winner_id = order[0] if order else None
        _emit(
            state,
            events,
            BrawlResolved,
            hood_id=hood.hood_id,
            force_by_player_id={},
            winner_id=progress.winner_id,
            loser_ids=(),
        )
        state.last_brawl_outcome = LastBrawlOutcome(
            hood_id=hood.hood_id,
            winner_id=progress.winner_id,
            loser_ids=(),
            force_by_player_id={},
        )
        _finish_brawl(state, progress, events)
        return

    state.active_step = ActiveStep.WAITING_FOR_BRAWL_CARD
    state.current_player_id = order[0]


def _continue(state: GameState, events: list[DomainEvent]) -> CommandOutcome:
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _validate_brawl_step(
    state: GameState, player_id: PlayerId, expected_step: ActiveStep
) -> DomainError | None:
    if state.phase != GamePhase.ACTION_PHASE:
        return wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value)
    if state.current_player_id != player_id:
        return wrong_player(str(state.current_player_id), str(player_id))
    if state.active_step != expected_step or state.pending_brawl is None:
        return DomainError(
            code="wrong_active_step",
            message=f"Not waiting for that Rissa step (state is at '{state.active_step.value}').",
            details={"actual_step": state.active_step.value},
        )
    return None


# --- declare step -----------------------------------------------------


def _handle_play_brawl_card(
    state: GameState, command: PlayBrawlCard, gun_count_by_card_id: dict[CardId, int]
) -> CommandOutcome:
    error = _validate_brawl_step(state, command.player_id, ActiveStep.WAITING_FOR_BRAWL_CARD)
    if error is not None:
        return CommandFailure(error)

    progress = state.pending_brawl
    assert progress is not None
    player = find_player(state, command.player_id)
    if command.card_id is not None and command.card_id not in player.hand_card_ids:
        return CommandFailure(
            DomainError(
                code="card_not_in_hand",
                message=f"Card '{command.card_id}' is not in your hand.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    if command.card_id is not None:
        player.hand_card_ids.remove(command.card_id)
    progress.played_card_id_by_player[command.player_id] = command.card_id
    _emit(
        state,
        events,
        BrawlCardDeclared,
        player_id=command.player_id,
        played_a_card=command.card_id is not None,
    )

    progress.declare_index += 1
    if progress.declare_index < len(progress.participants):
        state.current_player_id = progress.participants[progress.declare_index]
        return _continue(state, events)
    return _advance_assignment_or_resolve(state, progress, events, gun_count_by_card_id)


# --- reveal step --------------------------------------------------------


def _advance_assignment_or_resolve(
    state: GameState,
    progress: BrawlProgress,
    events: list[DomainEvent],
    gun_count_by_card_id: dict[CardId, int],
) -> CommandOutcome:
    while progress.assign_index < len(progress.participants):
        candidate = progress.participants[progress.assign_index]
        if progress.played_card_id_by_player.get(candidate) is not None:
            state.active_step = ActiveStep.WAITING_FOR_BRAWL_ASSIGNMENT
            state.current_player_id = candidate
            return _continue(state, events)
        progress.assign_index += 1
    return _resolve_forces_and_start_reward(state, progress, events, gun_count_by_card_id)


def _handle_assign_brawl_guns(
    state: GameState,
    command: AssignBrawlGuns,
    gun_count_by_card_id: dict[CardId, int],
    card_contact_by_id: dict[CardId, ContactId],
) -> CommandOutcome:
    error = _validate_brawl_step(state, command.player_id, ActiveStep.WAITING_FOR_BRAWL_ASSIGNMENT)
    if error is not None:
        return CommandFailure(error)

    progress = state.pending_brawl
    assert progress is not None
    if command.target_player_id not in progress.participants:
        return CommandFailure(
            DomainError(
                code="invalid_brawl_target",
                message=f"'{command.target_player_id}' is not a Rissa participant.",
                details={},
            )
        )

    card_id = progress.played_card_id_by_player[command.player_id]
    assert card_id is not None

    state.revision += 1
    events: list[DomainEvent] = []

    progress.assigned_target_by_player[command.player_id] = command.target_player_id
    contact_id = card_contact_by_id[card_id]
    state.decks.customer_decks_by_contact[contact_id].discard_pile_card_ids.append(card_id)
    _emit(
        state,
        events,
        BrawlGunsAssigned,
        player_id=command.player_id,
        card_id=card_id,
        gun_count=gun_count_by_card_id.get(card_id, 0),
        target_player_id=command.target_player_id,
    )

    progress.assign_index += 1
    return _advance_assignment_or_resolve(state, progress, events, gun_count_by_card_id)


# --- force + winner/loser determination ----------------------------------


def _force_by_player(
    state: GameState, progress: BrawlProgress, gun_count_by_card_id: dict[CardId, int]
) -> dict[PlayerId, int]:
    hood = state.board.hoods[progress.hood_id]
    force: dict[PlayerId, int] = {}
    for player_id in progress.participants:
        criminal_count = sum(
            1 for pid in hood.criminal_pawn_ids if state.pawns[pid].owner_player_id == player_id
        )
        link_count = sum(
            1
            for pawn in state.pawns.values()
            if pawn.role == PawnRole.LINK
            and pawn.contact_id == hood.contact_id
            and pawn.owner_player_id == player_id
        )
        # §A10 Studenti-2 (corrected 2026-08-02): every participant in
        # this Hood always fights, whether or not they played a card
        # this Rissa — the bonus Gun is unconditional, not tied to the
        # card-assignment mechanism.
        bonus_gun = skills.extra_gun_bonus(state, find_player(state, player_id))
        force[player_id] = criminal_count + link_count + bonus_gun

    for assigner, target in progress.assigned_target_by_player.items():
        if target is None:
            continue
        card_id = progress.played_card_id_by_player[assigner]
        assert card_id is not None
        guns = _effective_guns(card_id, gun_count_by_card_id)
        if target == assigner:
            force[target] += guns
        else:
            force[target] -= guns
    return force


def _effective_guns(card_id: CardId | None, gun_count_by_card_id: dict[CardId, int]) -> int:
    if card_id is None:
        return 0
    return gun_count_by_card_id.get(card_id, 0)


def _guns_played(
    progress: BrawlProgress,
    player_id: PlayerId,
    gun_count_by_card_id: dict[CardId, int],
) -> int:
    card_id = progress.played_card_id_by_player.get(player_id)
    return _effective_guns(card_id, gun_count_by_card_id)


def _break_tie_for_winner(
    state: GameState,
    progress: BrawlProgress,
    tied: list[PlayerId],
    gun_count_by_card_id: dict[CardId, int],
) -> PlayerId:
    if len(tied) == 1:
        return tied[0]

    min_guns = min(_guns_played(progress, p, gun_count_by_card_id) for p in tied)
    tied = [p for p in tied if _guns_played(progress, p, gun_count_by_card_id) == min_guns]
    if len(tied) == 1:
        return tied[0]

    if progress.triggering_player_id in tied:
        return progress.triggering_player_id

    start = state.player_order.index(state.first_player_id)
    rotation = state.player_order[start:] + state.player_order[:start]
    for player_id in rotation:
        if player_id in tied:
            return player_id
    return tied[0]  # unreachable: rotation always covers every player_order entry


def _resolve_forces_and_start_reward(
    state: GameState,
    progress: BrawlProgress,
    events: list[DomainEvent],
    gun_count_by_card_id: dict[CardId, int],
) -> CommandOutcome:
    force = _force_by_player(state, progress, gun_count_by_card_id)
    max_force = max(force.values())
    top = [p for p in progress.participants if force[p] == max_force]
    winner_id = _break_tie_for_winner(state, progress, top, gun_count_by_card_id)

    remaining = [p for p in progress.participants if p != winner_id]
    loser_ids: list[PlayerId] = []
    if remaining:
        min_force = min(force[p] for p in remaining)
        loser_ids = [p for p in remaining if force[p] == min_force]

    progress.winner_id = winner_id
    progress.loser_ids = loser_ids
    _emit(
        state,
        events,
        BrawlResolved,
        hood_id=progress.hood_id,
        force_by_player_id=dict(force),
        winner_id=winner_id,
        loser_ids=tuple(loser_ids),
    )
    state.last_brawl_outcome = LastBrawlOutcome(
        hood_id=progress.hood_id,
        winner_id=winner_id,
        loser_ids=tuple(loser_ids),
        force_by_player_id=dict(force),
    )

    if not loser_ids:
        return _finish_brawl(state, progress, events)

    state.active_step = ActiveStep.WAITING_FOR_BRAWL_REWARD
    state.current_player_id = winner_id
    return _continue(state, events)


# --- reward step ----------------------------------------------------------


def _handle_choose_brawl_loser_reward(
    state: GameState, command: ChooseBrawlLoserReward
) -> CommandOutcome:
    error = _validate_brawl_step(state, command.player_id, ActiveStep.WAITING_FOR_BRAWL_REWARD)
    if error is not None:
        return CommandFailure(error)

    progress = state.pending_brawl
    assert progress is not None
    if progress.reward_loser_index >= len(progress.loser_ids):
        return CommandFailure(
            DomainError(code="no_pending_loser_reward", message="No reward is pending.", details={})
        )
    expected_loser = progress.loser_ids[progress.reward_loser_index]
    if command.loser_player_id != expected_loser:
        return CommandFailure(
            DomainError(
                code="wrong_loser_target",
                message=f"Expected a reward choice for '{expected_loser}'.",
                details={},
            )
        )
    if command.reward_type not in ("money", "card"):
        return CommandFailure(
            DomainError(
                code="unknown_reward_type",
                message=f"'{command.reward_type}' is not a valid reward type.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    winner = find_player(state, progress.winner_id)  # type: ignore[arg-type]
    loser = find_player(state, expected_loser)
    stolen_card_id: CardId | None = None
    if command.reward_type == "money":
        amount = min(2, loser.money)
        loser.money -= amount
        winner.money += amount
    elif loser.hand_card_ids:
        rng = GameRandom.from_state(state.rng_state)
        stolen_card_id = rng.choice(loser.hand_card_ids)
        state.rng_state = rng.get_state()
        loser.hand_card_ids.remove(stolen_card_id)
        winner.hand_card_ids.append(stolen_card_id)

    _emit(
        state,
        events,
        BrawlLoserRewardChosen,
        winner_id=progress.winner_id,
        loser_id=expected_loser,
        reward_type=command.reward_type,
        stolen_card_id=stolen_card_id,
    )

    progress.reward_loser_index += 1
    if progress.reward_loser_index >= len(progress.loser_ids) and skills.brawl_win_link_from_base(
        state, winner
    ):
        _auto_apply_brawl_link_from_base(state, progress, winner, events)
    return _continue(state, events)


def _auto_apply_brawl_link_from_base(
    state: GameState, progress: BrawlProgress, winner: PlayerState, events: list[DomainEvent]
) -> None:
    """§A10 Studenti-3: replaces `_handle_choose_brawl_link_evolution`'s
    player choice with an automatic evolution of a fresh Covo pawn — no
    Hood Criminal is removed. Fallback (confirmed by the game designer,
    2026-08-02): with no free Covo pawn, falls back to the normal
    winner's-choice flow instead of skipping — leaving
    `link_evolution_done` False here means `_brawl_reward_decision`
    naturally offers `ChooseBrawlLinkEvolution` next, exactly as it
    would for a player without the Skill."""
    hood = state.board.hoods[progress.hood_id]
    fresh = next(
        (pid for pid in winner.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE), None
    )
    if fresh is None:
        return
    links.insert_link(state, winner.player_id, fresh, hood.contact_id, 1, events)
    economy.check_hood_cop_removal(state, hood, events)
    progress.link_evolution_done = True


def _handle_choose_brawl_link_evolution(
    state: GameState, command: ChooseBrawlLinkEvolution
) -> CommandOutcome:
    error = _validate_brawl_step(state, command.player_id, ActiveStep.WAITING_FOR_BRAWL_REWARD)
    if error is not None:
        return CommandFailure(error)

    progress = state.pending_brawl
    assert progress is not None
    if progress.reward_loser_index < len(progress.loser_ids):
        return CommandFailure(
            DomainError(
                code="loser_rewards_not_done",
                message="Resolve every defeated participant's reward first.",
                details={},
            )
        )
    if progress.link_evolution_done:
        return CommandFailure(
            DomainError(
                code="link_evolution_already_decided", message="Already decided.", details={}
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    if command.pawn_id is not None:
        hood = state.board.hoods[progress.hood_id]
        pawn = state.pawns.get(command.pawn_id)
        eligible = (
            pawn is not None
            and pawn.owner_player_id == progress.winner_id
            and pawn.role == PawnRole.CRIMINAL
            and command.pawn_id in hood.criminal_pawn_ids
        )
        if not eligible:
            return CommandFailure(
                DomainError(
                    code="invalid_pawn",
                    message=f"'{command.pawn_id}' is not your Criminal in this Hood.",
                    details={},
                )
            )
        hood.criminal_pawn_ids.remove(command.pawn_id)
        links.insert_link(state, progress.winner_id, command.pawn_id, hood.contact_id, 1, events)  # type: ignore[arg-type]
        economy.check_hood_cop_removal(state, hood, events)

    progress.link_evolution_done = True
    return _continue(state, events)


def _handle_choose_brawl_relocation_destination(
    state: GameState,
    command: ChooseBrawlRelocationDestination,
    tile_by_id: dict[TileId, CoveredHoodTileDefinition],
) -> CommandOutcome:
    error = _validate_brawl_step(state, command.player_id, ActiveStep.WAITING_FOR_BRAWL_REWARD)
    if error is not None:
        return CommandFailure(error)

    progress = state.pending_brawl
    assert progress is not None
    if progress.reward_loser_index < len(progress.loser_ids) or not progress.link_evolution_done:
        return CommandFailure(
            DomainError(code="wrong_reward_sub_step", message="Not this sub-step yet.", details={})
        )
    if progress.relocation_done:
        return CommandFailure(
            DomainError(code="relocation_already_decided", message="Already decided.", details={})
        )

    unrevealed_hood_ids = {hid for hid, h in state.board.hoods.items() if not h.revealed}
    if command.hood_id is not None:
        if command.hood_id not in unrevealed_hood_ids:
            return CommandFailure(
                DomainError(
                    code="invalid_relocation_destination",
                    message=f"'{command.hood_id}' is not an unrevealed Hood.",
                    details={},
                )
            )
    elif unrevealed_hood_ids:
        return CommandFailure(
            DomainError(
                code="destination_required",
                message="An unrevealed Hood is available; a destination must be chosen.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    hood = state.board.hoods[progress.hood_id]
    dest_hood = state.board.hoods.get(command.hood_id) if command.hood_id is not None else None
    for loser_id in progress.loser_ids:
        # §D1 (confirmed by the game designer): exactly *one* of the
        # loser's Criminals in this Hood is sent away, even if they have
        # more than one there contributing to their Force — the rest
        # stay put. Deterministic pick: first in the Hood's own pawn
        # order, same tie-break style already used elsewhere (e.g.
        # economy.py's package-sale Link choice) when the rules don't
        # say which specific pawn.
        pawn_id = next(
            (
                pid
                for pid in hood.criminal_pawn_ids
                if state.pawns[pid].owner_player_id == loser_id
            ),
            None,
        )
        if pawn_id is None:
            continue
        hood.criminal_pawn_ids.remove(pawn_id)
        pawn = state.pawns[pawn_id]
        # A fresh unrevealed Hood starts empty, and with only 4 players
        # in the game at most 3 losers can ever exist (4 participants
        # max, 1 winner), so this can't actually overflow the
        # 5-criminal capacity under the single-pawn-per-loser rule above
        # — kept as a defensive safety net rather than assumed
        # impossible, same "overflow is lost, the action still happens"
        # precedent as a full Covo (2026-07-30, point 10).
        relocated = dest_hood is not None and len(dest_hood.criminal_pawn_ids) < dest_hood.capacity
        if relocated:
            _relocate_pawn_to_hood(state, pawn_id, command.hood_id, events, tile_by_id)  # type: ignore[arg-type]
        else:
            pawn.role = PawnRole.IN_BASE
            pawn.location = PawnLocation.base()
            _emit(
                state,
                events,
                PawnDefeatedInBrawl,
                player_id=loser_id,
                pawn_id=pawn_id,
                destination_hood_id=None,
            )
    economy.check_hood_cop_removal(state, hood, events)
    progress.relocation_done = True
    return _finish_brawl(state, progress, events)


def _relocate_pawn_to_hood(
    state: GameState,
    pawn_id: PawnId,
    hood_id: HoodId,
    events: list[DomainEvent],
    tile_by_id: dict[TileId, CoveredHoodTileDefinition],
) -> None:
    hood = state.board.hoods[hood_id]
    if not hood.revealed:
        _reveal_covered_hood(state, hood, events, tile_by_id)
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.CRIMINAL
    pawn.location = PawnLocation.hood(hood_id)
    hood.criminal_pawn_ids.append(pawn_id)
    owner_id = pawn.owner_player_id
    _emit(
        state,
        events,
        PawnDefeatedInBrawl,
        player_id=owner_id,
        pawn_id=pawn_id,
        destination_hood_id=hood_id,
    )
    economy.draw_card(state, hood.contact_id, events, owner_id)


def _reveal_covered_hood(
    state: GameState,
    hood: HoodState,
    events: list[DomainEvent],
    tile_by_id: dict[TileId, CoveredHoodTileDefinition],
) -> None:
    tile_id, dope_type = state.board.covered_hood_tile_assignment[hood.hood_id]
    tile = tile_by_id[tile_id]
    available = state.market.supply_remaining_by_dope_type.get(dope_type, 0)
    count = min(tile.dope_count, available)

    hood.revealed = True
    hood.dope_type = dope_type
    hood.dope_stack = [dope_type] * count
    state.market.supply_remaining_by_dope_type[dope_type] = available - count
    _emit(
        state,
        events,
        CoveredHoodRevealed,
        hood_id=hood.hood_id,
        dope_type=dope_type,
        count=count,
        adds_cop=tile.adds_cop,
    )
    if tile.adds_cop:
        economy.spawn_cop(state, hood, events)


def _finish_brawl(
    state: GameState, progress: BrawlProgress, events: list[DomainEvent]
) -> CommandOutcome:
    hood = state.board.hoods[progress.hood_id]
    economy.spawn_cop(state, hood, events)

    if progress.winner_id is not None:
        # Milestone 5's Job 1 ("Vinci 1 Rissa") needs a cumulative count,
        # not derivable from board state — the single-participant fast
        # path above and the real force-comparison path both funnel
        # through here with `winner_id` already set.
        find_player(state, progress.winner_id).brawls_won_count += 1

    resume_player_id = progress.resume_player_id
    remaining_moves = progress.remaining_moves
    state.pending_brawl = None
    state.current_player_id = resume_player_id
    player = find_player(state, resume_player_id)

    if remaining_moves:
        from dope_engine.rules import movement

        return movement.process_move_queue(
            state, resume_player_id, player, remaining_moves, events, resuming=True
        )

    player.pending_action_type = None
    turn_flow.finish_action_or_extra(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))
