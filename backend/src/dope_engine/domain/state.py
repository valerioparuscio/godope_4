"""The authoritative GameState tree (CLAUDE.md section 7).

Every nested structure here is a plain (mutable) dataclass, deliberately
not frozen: rule handlers build the next state by deep-copying the
current one (see application/command_bus.py) and mutating the copy, so
a rejected command never leaves partial changes on the original.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dope_engine.domain.decisions import PendingDecision
from dope_engine.domain.entities import (
    BaseInventory,
    DeckState,
    HoodState,
    JailSlot,
    OfficerState,
    PawnState,
    SalesSpotState,
)
from dope_engine.domain.enums import (
    ActionType,
    ActiveStep,
    ControllerType,
    DopeType,
    GamePhase,
    GameStatus,
    PokerSymbolColor,
)
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    GameId,
    HoodId,
    JobId,
    OfficerId,
    PawnId,
    PlayerId,
    RaidCardId,
    SkillId,
    SpotId,
    TileId,
)
from dope_engine.domain.rng import RngState
from dope_engine.domain.scoring import FinalScoreState


@dataclass
class PlayerState:
    player_id: PlayerId
    seat_index: int
    controller_type: ControllerType
    display_name: str
    money: int
    hand_card_ids: list[CardId] = field(default_factory=list)
    base_inventory: BaseInventory = field(default_factory=BaseInventory)
    pawn_ids: list[PawnId] = field(default_factory=list)
    skill_ids: list[SkillId] = field(default_factory=list)
    available_grit_values: list[int] = field(default_factory=lambda: [1, 2, 3])
    moved_pawn_ids_this_turn: list[PawnId] = field(default_factory=list)
    # §A10 Politici-3 (Milestone 5): normally capped at 1 per turn (§A5);
    # a count rather than a bool so `rules/skills.py::
    # max_link_extra_actions_per_turn`'s boosted limit can be compared
    # against it directly.
    extra_actions_used_this_turn: int = 0
    gamble_cards_played_this_round: int = 0
    # Ephemeral, main-action sub-step bookkeeping (RULES_CANONICAL.md §B2):
    # None while choosing *which* action type to spend this round's Grit
    # on; set to that choice while choosing the actual targets. The Grit
    # value itself (how many targets are required) is cached here too,
    # since ChooseGritAction removes it from available_grit_values. The
    # same two fields double up for a Link's extra action (§A5): its
    # level stands in for current_round_grit_value, and
    # extra_action_link_pawn_id (below) marks that this pending
    # action/target resolution belongs to that spent Link, not the
    # round's own Grit marker.
    pending_action_type: ActionType | None = None
    current_round_grit_value: int | None = None
    extra_action_link_pawn_id: PawnId | None = None
    # The spent Link's Contact, cached at spend time: the pawn itself
    # returns to the Covo *immediately* when spent (§A5, confirmed
    # 2026-08-01, so it can't be affected by its own extra action), so
    # its own `contact_id` is already cleared by the time
    # legal_actions.py needs to know which action types this extra
    # action is restricted to.
    extra_action_contact_id: ContactId | None = None
    # Which of the extra action's 2 offer points (RULES_CANONICAL.md §B2
    # "prima o dopo l'azione principale") is currently active — set by
    # rules/turn_flow.py's `_enter_grit_or_extra_action_offer` (False,
    # "prima") or `proceed_after_main_action` (True, "dopo"); read by
    # `finish_action_or_extra` to resume in the right place.
    extra_action_from_post_main: bool = False
    # Mirrors extra_action_from_post_main, for the sibling
    # WAITING_FOR_STAIN_FOR_CASH_OFFER offer point (§D5, Milestone 5):
    # which of the two per-round offer points is currently active, so
    # declining/completing resumes at the right place.
    stain_offer_from_post_main: bool = False
    # §D2 (confirmed 2026-08-01): a Poker match can only be launched
    # with a Preti card whose own `action_type` matches the action
    # (main or extra) the player just committed to for this round —
    # "si associa ad un'azione base". The offer is therefore made right
    # after `ChooseActionType` (`rules/economy.py::
    # _handle_choose_action_type`), which stashes whichever step it
    # interrupted here (`WAITING_FOR_MAIN_ACTION_TARGETS` or
    # `WAITING_FOR_LINK_EXTRA_ACTION`) so accepting or declining the
    # launch (`rules/poker.py`) can resume target selection exactly
    # where it left off.
    poker_launch_return_step: ActiveStep | None = None
    # Cumulative, game-long counters (Milestone 5): not derivable from the
    # current board/pawn snapshot, needed by Job requirements
    # (`win_brawls`, `win_poker_matches`, `buy_officers` in data/jobs.json)
    # and Raid escape criteria (`most_poker_wins`, `most_cops_bought` in
    # data/raids.json — confirmed 2026-08-01 to count Cops and Feds
    # together, same pool as the Job's `buy_officers`).
    brawls_won_count: int = 0
    poker_matches_won_count: int = 0
    # §D3 Marketing (corrected 2026-08-02): "prima o dopo lo svolgimento
    # dell'azione" means before or after the *whole* Buy/Sell action, not
    # just its own automatic price step — offered right after
    # `ChooseActionType` ("before", any Dope type, mirrors
    # `poker_launch_return_step`'s stash-and-resume pattern) or at the
    # tail of `BuyDope`/`SellDope` ("after", restricted to the Dope
    # types the package handled). Both share
    # `ActiveStep.WAITING_FOR_CARD_USAGE`; `marketing_offer_is_pre`
    # distinguishes which one is currently active.
    marketing_pre_return_step: ActiveStep | None = None
    marketing_offer_is_pre: bool = False
    marketing_eligible_dope_types: list[DopeType] = field(default_factory=list)
    # Remembers a "before" use's allocations so Manager-3
    # (`rules/skills.py::marketing_applies_both_timings`) can replay them
    # "after" automatically, without a second card. Cleared once
    # consumed (replayed) or once the action ends without Manager-3.
    marketing_pre_allocations: tuple[tuple[DopeType, int], ...] = ()
    # §C4/§A5 (corrected 2026-08-02): queued single-unit-sale Link
    # evolution choices still to resolve from the just-completed SellDope
    # package (see PendingSaleLinkEvolution).
    pending_sale_link_evolutions: list[PendingSaleLinkEvolution] = field(default_factory=list)
    # The completed SellDope package's own (signed, per dope_type)
    # automatic price step, stashed while `pending_sale_link_evolutions`
    # drains — applied once the queue is empty (economy.py).
    pending_sale_price_steps: dict[DopeType, int] = field(default_factory=dict)
    officers_bought_count: int = 0


@dataclass
class BoardState:
    hoods: dict[HoodId, HoodState] = field(default_factory=dict)
    spots: dict[SpotId, SalesSpotState] = field(default_factory=dict)
    officers: dict[OfficerId, OfficerState] = field(default_factory=dict)
    den_gambler_pawn_ids: list[PawnId] = field(default_factory=list)
    officer_seq: int = 0
    # Hidden setup info (RULES_CANONICAL.md §F3): which round tile and
    # Dope type each covered Hood will reveal once a defeated Criminal is
    # sent there. Not exposed to any player-facing GameView until that
    # Hood is actually revealed.
    covered_hood_tile_assignment: dict[HoodId, tuple[TileId, DopeType]] = field(
        default_factory=dict
    )


@dataclass
class MarketState:
    price_index_by_dope_type: dict[DopeType, int] = field(default_factory=dict)
    supply_remaining_by_dope_type: dict[DopeType, int] = field(default_factory=dict)


@dataclass
class JailState:
    slots: list[JailSlot] = field(default_factory=list)


@dataclass
class DecksState:
    customer_decks_by_contact: dict[ContactId, DeckState] = field(default_factory=dict)


@dataclass
class PlayerJobProgress:
    tier_piles: dict[int, list[JobId]] = field(default_factory=dict)
    revealed_job_id_by_tier: dict[int, JobId | None] = field(default_factory=dict)


@dataclass
class JobBoardCell:
    job_id: JobId
    column_index: int
    player_id: PlayerId | None = None
    stained: bool = False


@dataclass
class JobsState:
    progress_by_player: dict[PlayerId, PlayerJobProgress] = field(default_factory=dict)
    board: list[JobBoardCell] = field(default_factory=list)


@dataclass
class RaidsState:
    selected_card_ids: tuple[RaidCardId, ...] = ()
    current_turn_card_id: RaidCardId | None = None
    lost_occurrences_count: int = 0


@dataclass
class SkillsState:
    """One shuffled draw pile per Contact (3 Skills each, §A10), consumed
    as the `SKILL` Job-board bonus is claimed. Built once at setup by
    `rules/setup.py::_build_skills_state`; not exposed to any player's
    hidden information since the *contents* of an unclaimed pile are
    irrelevant (drawing is random, not a meaningful hidden choice)."""

    remaining_by_contact: dict[ContactId, list[SkillId]] = field(default_factory=dict)


@dataclass
class PendingSaleLinkEvolution:
    """§C4/§A5 (corrected 2026-08-02): a single-unit Dope sale's Link
    evolution is the selling player's own SI/NO choice (package sales of
    2-3 units stay automatic, per §C4's "si prende" text) — one entry
    per Spot sold to with exactly 1 unit in the same `SellDope` package,
    queued on `PlayerState.pending_sale_link_evolutions` and resolved
    one at a time at `ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE`
    (`rules/economy.py`)."""

    spot_id: SpotId
    pawn_id: PawnId
    contact_id: ContactId


@dataclass
class PendingJobRewardEntry:
    player_id: PlayerId
    job_id: JobId
    tier: int


@dataclass
class JobRewardProgress:
    """Tracks one or more Job completions queued by a single accepted
    command (RULES_CANONICAL.md §A10 — completion is auto-detected after
    *every* command, and more than one Job can complete off one command,
    e.g. a package Buy/Sell or a Jail Evasion returning Dope to several
    players' Covos at once). Pauses whatever flow was interrupted
    (`resume_player_id`/`resume_active_step`) exactly like
    `BrawlProgress`/`CorruptionProgress` already do, resumed once the
    queue drains — see rules/jobs.py."""

    queue: list[PendingJobRewardEntry] = field(default_factory=list)
    resume_player_id: PlayerId | None = None
    resume_active_step: ActiveStep | None = None


@dataclass
class PokerMatchState:
    match_id: str
    launched_by_player_id: PlayerId
    gamble_card_id: CardId
    banco_symbols: tuple[PokerSymbolColor, ...]
    bets_by_player_id: dict[PlayerId, int] = field(default_factory=dict)
    jackpot_chips: int = 0
    revealed_symbols_by_player_id: dict[PlayerId, tuple[PokerSymbolColor, ...]] = field(
        default_factory=dict
    )


@dataclass
class PokerState:
    """§D2: `matches_this_turn` accumulates every match launched during
    the current turn's ACTION_PHASE (rules/poker.py::_handle_launch_poker),
    then the whole batch is bet on and resolved together during
    POKER_PHASE (rules/poker.py::enter_poker_phase). The `pending_*`
    fields are transient progress markers reused across two different
    round-robin sub-steps of that same phase: first "who still needs to
    place a bet" (all matches at once), then, per match in launch order,
    "which of that match's bettors still needs to reveal a card".
    `pending_jackpot_chips` carries an unresolved full tie's stakes
    (RULES_PENDING.md #14) forward to whichever match is launched next,
    by anyone — it isn't tied to the specific players who tied."""

    matches_this_turn: list[PokerMatchState] = field(default_factory=list)
    pending_bettor_order: list[PlayerId] = field(default_factory=list)
    pending_bettor_index: int = 0
    resolving_match_index: int = 0
    pending_jackpot_chips: int = 0


@dataclass
class CorruptionProgress:
    """Tracks a CorruptOfficer package across its sequential per-officer
    sub-decisions (RULES_CANONICAL.md §C5: each corruption needs exactly
    2 *different* follow-up actions before the next officer in the
    package can start) — see rules/officers.py."""

    player_id: PlayerId
    corruptor_pawn_id: PawnId
    officer_id: OfficerId
    actions_taken: list[str] = field(default_factory=list)
    remaining_queue: list[tuple[PawnId, OfficerId]] = field(default_factory=list)


@dataclass
class BrawlProgress:
    """Tracks a Rissa (RULES_CANONICAL.md §D1) across its 3 sequential
    sub-phases — declare (ActiveStep.WAITING_FOR_BRAWL_CARD), reveal
    (WAITING_FOR_BRAWL_ASSIGNMENT), reward (WAITING_FOR_BRAWL_REWARD) —
    see rules/brawl.py. Rissa can interrupt a MoveCriminal package
    mid-way (the 5th Criminal can arrive on any move in the package, not
    just the last), so `remaining_moves` stashes whatever moves hadn't
    been processed yet, resumed once the Rissa fully resolves."""

    hood_id: HoodId
    triggering_player_id: PlayerId
    participants: list[PlayerId]
    resume_player_id: PlayerId
    remaining_moves: list[tuple[PawnId, HoodId, ContactId | None]] = field(default_factory=list)
    declare_index: int = 0
    played_card_id_by_player: dict[PlayerId, CardId | None] = field(default_factory=dict)
    assign_index: int = 0
    assigned_target_by_player: dict[PlayerId, PlayerId | None] = field(default_factory=dict)
    winner_id: PlayerId | None = None
    loser_ids: list[PlayerId] = field(default_factory=list)
    reward_loser_index: int = 0
    link_evolution_done: bool = False
    relocation_done: bool = False


@dataclass
class GameState:
    schema_version: int
    rules_version: str
    game_id: GameId
    revision: int
    rng_state: RngState
    status: GameStatus
    configuration: dict[str, Any]
    players: list[PlayerState]
    player_order: list[PlayerId]
    first_player_id: PlayerId
    current_player_id: PlayerId
    turn_index: int
    action_round_index: int
    phase: GamePhase
    active_step: ActiveStep
    pawns: dict[PawnId, PawnState]
    board: BoardState
    market: MarketState
    jail: JailState
    decks: DecksState
    jobs: JobsState
    raids: RaidsState
    poker: PokerState
    skills: SkillsState
    pending_decision: PendingDecision | None
    event_log_cursor: int
    pending_corruption: CorruptionProgress | None = None
    pending_brawl: BrawlProgress | None = None
    pending_job_reward: JobRewardProgress | None = None
    final_score: FinalScoreState | None = None


def find_player(state: GameState, player_id: PlayerId) -> PlayerState:
    for player in state.players:
        if player.player_id == player_id:
            return player
    raise KeyError(f"No player '{player_id}' in game '{state.game_id}'.")
