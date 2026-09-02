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
    OfficerLocationType,
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
    # Which Job-board cell (job_id, column_index) earned each Skill —
    # game designer, 2026-08-27: a player already holding 3 Skills (the
    # cap) can still claim a 4th by discarding one of the 3, but doing so
    # must relocate *that Skill's own* REP token to another free column
    # on its own row (freeing the Skill column there back up) — needs
    # this to find that original cell again. See rules/jobs.py::
    # _handle_choose_job_reward's SKILL branch and
    # _handle_choose_skill_to_discard.
    skill_source_by_id: dict[SkillId, tuple[JobId, int]] = field(default_factory=dict)
    available_grit_values: list[int] = field(default_factory=lambda: [1, 2, 3])
    moved_pawn_ids_this_turn: list[PawnId] = field(default_factory=list)
    # Confirmed by the game designer (2026-08-02): a base Grit round's
    # action_type can never repeat within the same turn (e.g. not
    # PLACE_CRIMINAL in round 1 and again in round 3) — Link extra actions
    # (§A5) are a separate mechanic and not restricted by this. Reset once
    # per turn in rules/turn_flow.py::_start_action_phase.
    action_types_used_this_turn: list[ActionType] = field(default_factory=list)
    # §A5 (2026-08-17 decision, supersedes the 2026-08-01 "once per whole
    # turn" version): normally capped at 1 per *round* (so up to 3 per
    # turn, 9 per game), reset in `rules/turn_flow.py::_start_new_round`
    # — §A10 Politici-3 boosts this same per-round cap (`rules/skills.py::
    # max_link_extra_actions_per_round`). A count rather than a bool so
    # the boosted limit can be compared against it directly.
    extra_actions_used_this_round: int = 0
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
    # Which pawns have already corrupted an officer within the *current*
    # CORRUPT_OFFICER action instance (main or extra action) — reset
    # whenever a fresh action_type is chosen (rules/economy.py::
    # _handle_choose_action_type), appended to as each corruption starts
    # (rules/officers.py::_start_corruption). Needed because Grit N now
    # corrupts up to N *different* officers one at a time, deciding after
    # each whether to spend more of the same Grit on another (game
    # designer, 2026-08-16 bug report: committing to all N officers
    # upfront, before knowing how many of each one's 1-3 actions would be
    # used, didn't match how a player actually wants to play it) — see
    # rules/officers.py::_finish_corruption.
    corrupted_pawn_ids_this_action: list[PawnId] = field(default_factory=list)
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
    # §D3 Marketing (2026-08-17 decision: "before" the whole Buy/Sell
    # action only, never after — superseded the earlier 2026-08-02
    # "before or after" version once playtesting showed "after" never
    # made sense to reach for once the package's own price step had
    # already moved the price) — offered right after `ChooseActionType`,
    # any Dope type, mirroring `poker_launch_return_step`'s
    # stash-and-resume pattern (`ActiveStep.WAITING_FOR_CARD_USAGE`).
    # `marketing_offer_is_pre` stays True for the offer's whole duration;
    # kept as an explicit flag (rather than inferred from context) for
    # symmetry with this state machine's other offer-point markers.
    marketing_pre_return_step: ActiveStep | None = None
    marketing_offer_is_pre: bool = False
    # Which hand card the player committed to for the current Marketing
    # offer (game designer, 2026-08-15: a real choice among every
    # eligible card, not an auto-pick of the highest-Stonk one) — set by
    # `ChooseMarketingCard`, only when 2+ cards qualified in the first
    # place (with exactly one, `_marketing_decision` uses it directly,
    # no sub-step). Cleared once the offer resolves either way (played or
    # declined), so it never leaks into a later Marketing offer.
    marketing_chosen_card_id: CardId | None = None
    # Remembers a "before" use's allocations so Manager-3
    # (`rules/skills.py::marketing_applies_both_timings`) can replay them
    # "after" automatically, without a second card. Cleared once
    # consumed (replayed) or once the action ends without Manager-3.
    marketing_pre_allocations: tuple[tuple[DopeType, int], ...] = ()
    # Customer Card boosts (game designer, 2026-08-27): a hand card whose
    # own printed action_type matches the round's committed action can be
    # played to apply its `data/customer_cards.json::effect` to that one
    # action instance, then it's discarded. Same offer-point/stash-resume
    # shape as Marketing/Poker-launch above, chained after both of them
    # (see rules/customer_cards.py's module docstring for the full
    # ordering) — `card_boost_return_step` is the resume point,
    # `ActiveStep.WAITING_FOR_CARD_BOOST` the offer's own active_step.
    card_boost_return_step: ActiveStep | None = None
    # The played card's own effect dict (e.g. {"type": "cost_delta",
    # "amount": -1}), shaped identically to a Skill's own
    # `skill_effect_by_id` entry so `rules/skills.py::_effects_of_type`
    # can fold it into the exact same effective_cost/effective_action_count/
    # effective_trade_price lookups Skills already use — a card boost is
    # mechanically just a one-shot, one-action Skill. Cleared by
    # `rules/turn_flow.py::finish_action_or_extra`, the same shared tail
    # every action-type handler already calls once its own instance
    # (a whole multi-step Corruption package included) is fully done.
    active_card_boost: dict[str, Any] | None = None
    # §C4/§A5 (corrected 2026-08-02): queued single-unit-sale Link
    # evolution choices still to resolve from the just-completed SellDope
    # package (see PendingSaleLinkEvolution).
    pending_sale_link_evolutions: list[PendingSaleLinkEvolution] = field(default_factory=list)
    # The completed SellDope package's own (signed, per dope_type)
    # automatic price step, stashed while `pending_sale_link_evolutions`
    # drains — applied once the queue is empty (economy.py).
    pending_sale_price_steps: dict[DopeType, int] = field(default_factory=dict)
    # Cards 001/005 "TRY AGAIN"/"HIGH HIGH" ("manda in prigione un tuo
    # criminale che ha acquistato/venduto"): the first pawn (command
    # order) of a just-submitted Buy/Sell package, stashed by
    # `_handle_buy_dope`/`_handle_sell_dope` and consumed by
    # `_finish_buy_or_sell_package` (economy.py) — needed because a Sell
    # package can be interrupted by `WAITING_FOR_LINK_EVOLUTION_CHOICE`
    # before that shared tail actually runs, so the pawn can't just be a
    # local variable. Unconditional (cheap to stash even when no
    # self_arrest_after_action boost is active — the consumer is the one
    # that checks `active_card_boost`).
    pending_self_arrest_pawn_id: PawnId | None = None


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
class LastRaidOutcome:
    """The most recently resolved Raid's public result (RaidResolved's own
    payload, kept around so a client can show "who won" — resolution
    happens automatically at end of turn, with no player decision, so
    there's otherwise no moment a client could catch it from a command
    response alone).

    `escape_criterion`/`escaping_team_total`/`caught_team_total` (game
    designer, 2026-08-17 — "vorrei un resoconto numerico, es Retata +
    RATS, vincono blu e giallo con 3 rats vs 2 rats"): `rules/raids.py::
    resolve_raid` already computes each team's sum under the card's own
    criterion to decide who escapes — these three fields just carry that
    same number through instead of discarding it, so a client can show
    *how much* a team won by, not just who won."""

    raid_card_id: RaidCardId
    escaping_team: tuple[PlayerId, ...]
    caught_team: tuple[PlayerId, ...]
    escape_criterion: str
    escaping_team_total: int
    caught_team_total: int
    # Added for the blocking result modal (game designer, 2026-08-23) —
    # `RaidResolved` already carried this per-player REP-stain count;
    # this just keeps it around the same way the other fields above are,
    # for a client recap popup outside a command response.
    stain_count_applied: dict[PlayerId, int]


@dataclass
class RaidsState:
    selected_card_ids: tuple[RaidCardId, ...] = ()
    current_turn_card_id: RaidCardId | None = None
    lost_occurrences_count: int = 0
    last_outcome: LastRaidOutcome | None = None


@dataclass
class LastBrawlOutcome:
    """Same purpose as `LastRaidOutcome` (BrawlResolved's own payload,
    kept around for a client recap popup — designer's request,
    2026-08-16) — a Rissa can resolve mid-package (e.g. interrupting a
    bot's MoveCriminal package) with no player-facing command response
    of its own to carry the result."""

    hood_id: HoodId
    winner_id: PlayerId | None
    loser_ids: tuple[PlayerId, ...]
    force_by_player_id: dict[PlayerId, int]
    # Added for the blocking result modal (game designer, 2026-08-23) —
    # `force_by_player_id` alone only ever carried the final summed
    # total; the popup wants the breakdown that total comes from, split
    # the same way `rules/brawl.py::_force_by_player` computes it:
    # physical presence (Criminals + Links in the Hood) versus every Gun
    # adjustment (a Skill's own bonus, plus a played card's Guns —
    # positive if assigned to self, negative if given away to someone
    # else). `pawn_count + gun_total == force_by_player_id` for every
    # participant, always.
    pawn_count_by_player_id: dict[PlayerId, int]
    gun_total_by_player_id: dict[PlayerId, int]


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
    # Set only while resolving the head-of-queue entry's own column choice
    # a further step away from actually granting anything: the SKILL
    # column at the 3-Skill cap (game designer, 2026-08-27) — the column/
    # Contact already chosen for *this* completion, stashed so
    # ActiveStep.WAITING_FOR_SKILL_DISCARD_CHOICE can grant the new Skill
    # once `ChooseSkillToDiscard` says which of the 3 held ones to bump —
    # or Job 8's own column 2 override (2026-09-02), stashed the same way
    # so ActiveStep.WAITING_FOR_JOB_BONUS_ALTERNATIVE_CHOICE can grant $3
    # or 2 cards once `ChooseJobBonusAlternative` says which.
    stalled_column_index: int | None = None
    stalled_contact_id: ContactId | None = None


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
class LastPokerMatchOutcome:
    """Same purpose as `LastRaidOutcome` (PokerMatchResolved's own
    payload, kept around for a client recap popup — designer's request,
    2026-08-16). `PokerState.last_outcomes` collects every match resolved
    during the current POKER_PHASE (up to `poker_max_matches_per_turn`),
    reset at the start of the next one — so a client can recap "how
    Poker went this turn" as a single batch instead of one popup per
    match."""

    match_id: str
    winner_id: PlayerId | None
    tied_ids: tuple[PlayerId, ...]
    loser_ids: tuple[PlayerId, ...]
    cash_won: int
    jackpot_carried: int
    # Added for the blocking result modal (game designer, 2026-08-23:
    # "un popup centrale... es pawn blu vince il poker con un full,
    # xxxOO") — every bettor's own final 5-symbol hand (banco's 3 +
    # their own revealed 2), the winning/tied shape category
    # (`rules/poker.py::_hand_score`'s own `shape` string — "full",
    # "poker", "tris", "two_pair", "pair", "five_different"), and which
    # losers actually got arrested (a loser's Gambler stays in the Den,
    # unarrested, if the Jail happened to be full — CLAUDE.md's own
    # PROVISIONAL note in the module docstring above `_resolve_match`).
    hands_by_player_id: dict[PlayerId, tuple[PokerSymbolColor, ...]]
    top_hand_shape: str | None
    arrested_loser_ids: tuple[PlayerId, ...]
    winner_evolved_to_link: bool


@dataclass
class PendingPokerSymbolChoice:
    """§A10 Preti-1 "Puoi giocare 2 carte per ogni Poker (scegli 2
    simboli)": a bettor with this Skill can reveal *two* hand cards
    instead of one — `_handle_play_poker_card` discards both immediately
    (same as the normal single-card case) and stashes their combined 4
    symbols here, pausing at `ActiveStep.WAITING_FOR_POKER_SYMBOL_CHOICE`
    for a second, separate command (`ChoosePokerSymbols`) to pick which 2
    of those 4 actually go into the player's final 5-symbol hand — the
    other 2 are simply not used. Revealing only *one* card, even with the
    Skill (it's optional per the card text, "puoi"), skips this step
    entirely and behaves exactly like a normal reveal."""

    match_id: str
    player_id: PlayerId
    available_symbols: tuple[PokerSymbolColor, ...]


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
    by anyone — it isn't tied to the specific players who tied.
    `pending_symbol_choice` is a further, optional sub-step of the reveal
    round-robin above, only entered for a Preti-1 owner who reveals 2
    cards at once (see `PendingPokerSymbolChoice`)."""

    matches_this_turn: list[PokerMatchState] = field(default_factory=list)
    pending_bettor_order: list[PlayerId] = field(default_factory=list)
    pending_bettor_index: int = 0
    resolving_match_index: int = 0
    pending_jackpot_chips: int = 0
    last_outcomes: tuple[LastPokerMatchOutcome, ...] = ()
    pending_symbol_choice: PendingPokerSymbolChoice | None = None


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
    remaining_moves: list[tuple[PawnId, HoodId, ContactId | None, ContactId | None]] = field(
        default_factory=list
    )
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
    seed: int
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
    last_brawl_outcome: LastBrawlOutcome | None = None
    # Set by `rules/turn_flow.py::_end_turn` once the *last* turn ends,
    # instead of computing the final score immediately — the last turn's
    # own Poker/Raid resolution can itself complete a Job (2026-08-17 bug
    # report: "falli completare prima del calcolo finale"), which needs
    # an interactive WAITING_FOR_JOB_REWARD round-trip exactly like any
    # other Job completion. `rules/turn_flow.py::finalize_game_if_ready`
    # (called from `rules/jobs.py`'s post-success hook once its own
    # completion queue drains, not just from `_end_turn` itself) computes
    # the score and marks the game FINISHED only once this is set *and*
    # no Job reward is left pending — so a Job that only became
    # completable on the very last turn still counts before scoring.
    pending_game_end: bool = False


def find_player(state: GameState, player_id: PlayerId) -> PlayerState:
    for player in state.players:
        if player.player_id == player_id:
            return player
    raise KeyError(f"No player '{player_id}' in game '{state.game_id}'.")


def officer_count_in_base(state: GameState, player_id: PlayerId) -> int:
    """A pure state query, not a `rules/officers.py` function: it needs to
    be reachable from `rules/jobs.py` (Job 2's "own_officers" requirement)
    without `rules/jobs.py` importing `rules/officers.py`, which imports
    `rules/jail.py`, which (2026-08-27 fix) now imports `rules/jobs.py`
    itself — that loop would otherwise be circular. `rules/officers.py`
    calls this too, for its own `base_officer_cap_reached` check."""
    return sum(
        1
        for officer in state.board.officers.values()
        if officer.location_type == OfficerLocationType.BASE
        and officer.owner_player_id == player_id
    )
