"""Domain events: what actually happened, for animations, replay and logs.

`DomainEvent` is the common envelope; concrete rule events (CardPlayed,
DopeBought, BrawlResolved, ...) are added milestone by milestone,
alongside the rule module that produces them, rather than all at once
here.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.enums import DopeType, OfficerType, PokerSymbolColor
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    EventId,
    GameId,
    HoodId,
    JobId,
    OfficerId,
    PawnId,
    PlayerId,
    RaidCardId,
    SkillId,
    SpotId,
)


@dataclass(frozen=True)
class DomainEvent:
    event_id: EventId
    game_id: GameId
    revision: int


@dataclass(frozen=True)
class GameStarted(DomainEvent):
    seed: int
    rules_version: str
    player_ids: tuple[PlayerId, ...]


@dataclass(frozen=True)
class TurnStarted(DomainEvent):
    turn_index: int
    first_player_id: PlayerId


@dataclass(frozen=True)
class RaidRevealed(DomainEvent):
    turn_index: int
    raid_card_id: RaidCardId


@dataclass(frozen=True)
class GritActionChosen(DomainEvent):
    player_id: PlayerId
    grit_value: int


@dataclass(frozen=True)
class MainActionPassed(DomainEvent):
    """The player had no legal action-type to spend this round's Grit
    marker on (or chose to decline it)."""

    player_id: PlayerId


@dataclass(frozen=True)
class CardsDiscarded(DomainEvent):
    player_id: PlayerId
    card_ids: tuple[CardId, ...]


@dataclass(frozen=True)
class ActionTypeChosen(DomainEvent):
    player_id: PlayerId
    action_type: str


@dataclass(frozen=True)
class CardDrawn(DomainEvent):
    player_id: PlayerId
    contact_id: ContactId
    card_id: CardId


@dataclass(frozen=True)
class CriminalPlaced(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    hood_id: HoodId


@dataclass(frozen=True)
class CriminalMoved(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    from_hood_id: HoodId | None
    to_hood_id: HoodId


@dataclass(frozen=True)
class PawnBecameGambler(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId


@dataclass(frozen=True)
class GamblerBecameCriminal(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    hood_id: HoodId


@dataclass(frozen=True)
class DopeBought(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    hood_id: HoodId
    dope_type: DopeType
    price_paid: int


@dataclass(frozen=True)
class DopeSold(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    spot_id: SpotId
    dope_type: DopeType
    price_received: int


@dataclass(frozen=True)
class DopeLostToOverflow(DomainEvent):
    player_id: PlayerId
    dope_type: DopeType


@dataclass(frozen=True)
class PriceChanged(DomainEvent):
    dope_type: DopeType
    steps: int
    new_index: int


@dataclass(frozen=True)
class MarketCrashed(DomainEvent):
    pass


@dataclass(frozen=True)
class MarketingCardPlayed(DomainEvent):
    player_id: PlayerId
    card_id: CardId
    allocations: tuple[tuple[DopeType, int], ...]
    is_pre: bool


@dataclass(frozen=True)
class HoodRestocked(DomainEvent):
    hood_id: HoodId
    dope_type: DopeType
    count: int


@dataclass(frozen=True)
class CopEnteredHood(DomainEvent):
    officer_id: OfficerId
    hood_id: HoodId


@dataclass(frozen=True)
class SpotCleared(DomainEvent):
    spot_id: SpotId


@dataclass(frozen=True)
class FedEnteredSpot(DomainEvent):
    officer_id: OfficerId
    spot_id: SpotId


@dataclass(frozen=True)
class OfficerReturnedToReserve(DomainEvent):
    officer_id: OfficerId
    officer_type: OfficerType


@dataclass(frozen=True)
class ActionRoundEnded(DomainEvent):
    turn_index: int
    action_round_index: int
    player_id: PlayerId


@dataclass(frozen=True)
class PokerLaunched(DomainEvent):
    player_id: PlayerId
    match_id: str
    gamble_card_id: CardId
    banco_symbols: tuple[PokerSymbolColor, ...]
    gambler_pawn_id: PawnId | None


@dataclass(frozen=True)
class PokerBetsPlaced(DomainEvent):
    player_id: PlayerId
    match_ids: tuple[str, ...]


@dataclass(frozen=True)
class PokerCardRevealed(DomainEvent):
    player_id: PlayerId
    match_id: str
    card_id: CardId
    symbols: tuple[PokerSymbolColor, ...]


@dataclass(frozen=True)
class PokerSymbolsChosen(DomainEvent):
    """§A10 Preti-1: emitted once a 2-card reveal's follow-up
    `ChoosePokerSymbols` picks which 2 of the 4 revealed symbols make it
    into the final hand (see `PokerCardRevealed`, emitted once per
    revealed card beforehand)."""

    player_id: PlayerId
    match_id: str
    chosen_symbols: tuple[PokerSymbolColor, PokerSymbolColor]


@dataclass(frozen=True)
class PokerMatchResolved(DomainEvent):
    match_id: str
    winner_id: PlayerId | None
    tied_ids: tuple[PlayerId, ...]
    loser_ids: tuple[PlayerId, ...]
    cash_won: int
    jackpot_carried: int
    top_hand_shape: str | None
    arrested_loser_ids: tuple[PlayerId, ...]
    winner_evolved_to_link: bool


@dataclass(frozen=True)
class PokerPhaseResolved(DomainEvent):
    turn_index: int


@dataclass(frozen=True)
class ShowdownPhaseResolved(DomainEvent):
    turn_index: int


@dataclass(frozen=True)
class TurnEnded(DomainEvent):
    turn_index: int


@dataclass(frozen=True)
class FinalScoreCalculated(DomainEvent):
    winner_ids: tuple[PlayerId, ...]


@dataclass(frozen=True)
class GameFinished(DomainEvent):
    turn_index: int
    winner_ids: tuple[PlayerId, ...]


@dataclass(frozen=True)
class PawnBecameLink(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    contact_id: ContactId
    link_level: int


@dataclass(frozen=True)
class LinkLevelChanged(DomainEvent):
    """An existing Link shifted to a new level (cascaded by another Link
    being inserted at or below it — RULES_CANONICAL.md §A5)."""

    player_id: PlayerId
    pawn_id: PawnId
    contact_id: ContactId
    new_link_level: int


@dataclass(frozen=True)
class LinkPawnReturnedToBase(DomainEvent):
    """A Link fell off the end of its Contact's track (level > 3) and
    returned to its owner's Covo as a free pawn."""

    player_id: PlayerId
    pawn_id: PawnId


@dataclass(frozen=True)
class LinkSpentForExtraAction(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    contact_id: ContactId
    link_level: int


@dataclass(frozen=True)
class OfficerCorruptionStarted(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    officer_id: OfficerId
    officer_type: OfficerType


@dataclass(frozen=True)
class CorruptionActionApplied(DomainEvent):
    player_id: PlayerId
    officer_id: OfficerId
    action: str


@dataclass(frozen=True)
class OfficerCorruptionResolved(DomainEvent):
    player_id: PlayerId
    officer_id: OfficerId


@dataclass(frozen=True)
class QueuedCorruptionSkipped(DomainEvent):
    """A later officer in a Grit-N corruption package (§C5) never got its
    own turn: the pawn queued to corrupt it lost the presence/funds needed
    by the time the earlier officer(s) in the package finished — e.g. that
    earlier officer's own "arrest" action jailed the very pawn queued next
    (rules/officers.py::_finish_corruption). Surfaced as an event, not
    just silently finishing the action, so the player can see why (§15.1:
    errors must be explained, not hidden)."""

    player_id: PlayerId
    officer_id: OfficerId
    reason_code: str


@dataclass(frozen=True)
class OfficerMoved(DomainEvent):
    officer_id: OfficerId
    hood_id: HoodId | None = None
    spot_id: SpotId | None = None


@dataclass(frozen=True)
class PawnArrested(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    jail_slot_index: int


@dataclass(frozen=True)
class DopeConfiscated(DomainEvent):
    dope_type: DopeType
    jail_slot_index: int


@dataclass(frozen=True)
class JailEscapeTriggered(DomainEvent):
    """The 6th Rat filled the Jail (RULES_CANONICAL.md §A1): the 5 other
    Rats return to their Covo with any Dope in their slot, and the 6th
    (the one that triggered the escape) evolves directly into a Politici
    Link instead."""

    triggering_pawn_id: PawnId


@dataclass(frozen=True)
class RatReturnedToBase(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    recovered_dope_type: DopeType | None


@dataclass(frozen=True)
class OfficerBought(DomainEvent):
    buyer_player_id: PlayerId
    seller_player_id: PlayerId | None
    officer_id: OfficerId
    price: int


@dataclass(frozen=True)
class BrawlStarted(DomainEvent):
    hood_id: HoodId
    triggering_player_id: PlayerId
    participant_ids: tuple[PlayerId, ...]


@dataclass(frozen=True)
class BrawlCardDeclared(DomainEvent):
    """Public the instant it happens (a card is visibly placed face-down
    or the player visibly passes) — only the card's *identity* is hidden
    until BrawlGunsAssigned reveals it."""

    player_id: PlayerId
    played_a_card: bool


@dataclass(frozen=True)
class BrawlGunsAssigned(DomainEvent):
    player_id: PlayerId
    card_id: CardId
    gun_count: int
    target_player_id: PlayerId


@dataclass(frozen=True)
class BrawlResolved(DomainEvent):
    hood_id: HoodId
    force_by_player_id: dict[PlayerId, int]
    winner_id: PlayerId | None
    loser_ids: tuple[PlayerId, ...]
    pawn_count_by_player_id: dict[PlayerId, int]
    gun_total_by_player_id: dict[PlayerId, int]


@dataclass(frozen=True)
class BrawlLoserRewardChosen(DomainEvent):
    winner_id: PlayerId
    loser_id: PlayerId
    reward_type: str
    stolen_card_id: CardId | None


@dataclass(frozen=True)
class PawnDefeatedInBrawl(DomainEvent):
    player_id: PlayerId
    pawn_id: PawnId
    destination_hood_id: HoodId | None


@dataclass(frozen=True)
class CoveredHoodRevealed(DomainEvent):
    hood_id: HoodId
    dope_type: DopeType
    count: int
    adds_cop: bool


@dataclass(frozen=True)
class JobCompleted(DomainEvent):
    """A Job's requirement was met (checked automatically after every
    accepted command — CLAUDE.md §11.12): the card is discarded and the
    next same-tier one from the player's own pile revealed in the same
    instant, unconditionally. Claiming the board bonus is a separate,
    player-decided step (`ChooseJobReward`, `JobBonusClaimed`)."""

    player_id: PlayerId
    job_id: JobId
    tier: int
    next_job_id: JobId | None


@dataclass(frozen=True)
class JobBonusClaimed(DomainEvent):
    player_id: PlayerId
    job_id: JobId
    column_index: int
    bonus_type: str
    contact_id: ContactId
    skill_id: SkillId | None
    link_pawn_id: PawnId | None
    drawn_card_ids: tuple[CardId, ...]


@dataclass(frozen=True)
class SkillDrawn(DomainEvent):
    player_id: PlayerId
    contact_id: ContactId
    skill_id: SkillId


@dataclass(frozen=True)
class SkillEffectApplied(DomainEvent):
    """Emitted once, at the exact point a command's resolution actually
    used an owned Skill's effect (RULES_CANONICAL.md §A10) — not merely
    whenever the player happens to own it. Frontend-only signal (drives
    the 1-second skill-card popup); no rule reads this event back."""

    player_id: PlayerId
    skill_id: SkillId


@dataclass(frozen=True)
class RaidFirstPlayerChosen(DomainEvent):
    chooser_player_id: PlayerId
    chosen_first_player_id: PlayerId


@dataclass(frozen=True)
class RaidResolved(DomainEvent):
    raid_card_id: RaidCardId
    escaping_team: tuple[PlayerId, ...]
    caught_team: tuple[PlayerId, ...]
    stain_count_applied: dict[PlayerId, int]
    escape_criterion: str
    escaping_team_total: int
    caught_team_total: int


@dataclass(frozen=True)
class ReputationStained(DomainEvent):
    player_id: PlayerId
    job_id: JobId
    column_index: int
    new_stain_total: int
