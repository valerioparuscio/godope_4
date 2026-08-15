"""Base envelope for player-issued commands.

Every command names the game and revision it targets so the command bus
can reject stale or duplicate submissions (see application/command_bus.py).
Economic/rule commands (PlaceCriminal, BuyDope, ...) are added alongside
the rule module that handles them, starting with Milestone 2. Milestone 1
only needs the envelope plus the generic turn-flow commands below —
enough to move a game through phases/rounds without any economic action
existing yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dope_engine.domain.enums import DopeType
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    DecisionId,
    GameId,
    HoodId,
    OfficerId,
    PawnId,
    PlayerId,
)


@dataclass(frozen=True)
class Command:
    game_id: GameId
    player_id: PlayerId
    expected_revision: int
    # kw_only so concrete subclasses can add required positional fields
    # after this optional one without violating dataclass field ordering.
    decision_id: DecisionId | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class ChooseGritAction(Command):
    """Assign one of the player's still-available Grit markers (1/2/3) to
    the current round (RULES_CANONICAL.md §B2)."""

    grit_value: int


@dataclass(frozen=True)
class PassOptionalStep(Command):
    """Decline an optional step that offers nothing mandatory: the main
    action itself in Milestone 1 (no economic action exists yet), or a
    hand discard when nothing is over the limit."""


@dataclass(frozen=True)
class DiscardCards(Command):
    """Discard down to the hand-size limit (RULES_CANONICAL.md §A9)."""

    card_ids: tuple[CardId, ...]


@dataclass(frozen=True)
class ChooseActionType(Command):
    """Step 1 of the main action (RULES_CANONICAL.md §B2): pick which of
    the 6 base actions this round's Grit marker will be spent on. Step 2
    is one of the concrete commands below, choosing exactly as many
    targets as the Grit value."""

    action_type: str


@dataclass(frozen=True)
class PlaceCriminal(Command):
    """§C1. One target Hood per Criminal placed; the specific IN_BASE
    pawns used are assigned deterministically by the handler since they
    are interchangeable before placement."""

    hood_ids: tuple[HoodId, ...]


@dataclass(frozen=True)
class MoveCriminal(Command):
    """§C2. Each move is (pawn_id, destination_hood_id, den_deck_contact_id):
    the third element must be set (the Contact deck to draw from) only
    when destination is the Den (`domain.ids.DEN_ID`), else it must be
    `None` — every other move draws automatically from the destination
    Hood's own Contact deck."""

    moves: tuple[tuple[PawnId, HoodId, ContactId | None], ...]


@dataclass(frozen=True)
class BuyDope(Command):
    """§C3. One Dope purchase per (pawn, hood) pair. A Criminal's hood_id
    is always its own current location (redundant but harmless — kept
    explicit rather than re-deriving it, so the same shape covers a Link
    too). A Link counts as presence in both of its Contact's Hoods (game
    designer, 2026-08-15), each with its own independent stock/price, so
    hood_id is what disambiguates *which* one a given purchase targets —
    unlike SellDope's `sales` below, whose Spots are Contact- not
    Hood-scoped and so never need this."""

    purchases: tuple[tuple[PawnId, HoodId], ...]


@dataclass(frozen=True)
class SellDope(Command):
    """§C4. One Dope sale per (pawn, dope_type) pair, at the Spot of the
    pawn's current Hood's Contact that accepts that Dope type."""

    sales: tuple[tuple[PawnId, DopeType], ...]


@dataclass(frozen=True)
class EvolveSaleLink(Command):
    """§C4/§A5 (corrected 2026-08-02): resolve the currently-queued
    single-unit-sale Link evolution offer
    (`ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE`,
    `PlayerState.pending_sale_link_evolutions[0]`) with an explicit
    SI/NO — a real binary choice, not a skippable optional step, so
    both directions go through this one command instead of pairing with
    `PassOptionalStep`."""

    evolve: bool


@dataclass(frozen=True)
class PlayMarketingCard(Command):
    """§D3 Marketing (corrected 2026-08-02): discard a hand card to
    spend its Stonk symbols shifting prices either *before* the whole
    Buy/Sell action (offered right after `ChooseActionType`, any Dope
    type — the package doesn't exist yet) or *after* it has fully
    resolved, including its own automatic price step (offered at the
    tail of `BuyDope`/`SellDope`, restricted to the Dope types the
    package actually handled). Both are offered at the same
    `ActiveStep.WAITING_FOR_CARD_USAGE`; which one is active is tracked
    by `PlayerState.marketing_offer_is_pre`. A normal player gets one or
    the other, not both; a Manager-3 owner who used "before" gets the
    same allocations automatically replayed "after" for free (see
    `rules/skills.py::marketing_applies_both_timings`), no second
    `PlayMarketingCard`. Each allocation is (dope_type, delta), delta
    `+1` or `-1`. `PassOptionalStep` covers declining."""

    card_id: CardId
    allocations: tuple[tuple[DopeType, int], ...]


@dataclass(frozen=True)
class ChooseMarketingCard(Command):
    """§D3 Marketing (game designer, 2026-08-15): with more than one
    hand card carrying Stonk symbols, the player picks which one to
    play — the engine no longer auto-picks the highest-Stonk card.
    Resolves the `ActiveStep.WAITING_FOR_CARD_USAGE` sub-step ahead of
    `PlayMarketingCard`'s own Stonk-allocation choice, only offered when
    there's a genuine choice (2+ eligible cards); with exactly one
    eligible card this sub-step is skipped entirely, same as before.
    `PassOptionalStep` covers declining Marketing outright."""

    card_id: CardId


@dataclass(frozen=True)
class CorruptOfficer(Command):
    """§C5. One corruption started per (corruptor pawn, officer) pair.
    Only the first pair is applied by this command — corrupting an
    officer takes 2 further sequential sub-decisions (see
    ChooseCorruptionAction) before the next pair in the package starts."""

    corruptions: tuple[tuple[PawnId, OfficerId], ...]


@dataclass(frozen=True)
class ChooseCorruptionAction(Command):
    """One of a corruption's 2 required *different* actions
    (RULES_CANONICAL.md §C5): `action` is "move" | "arrest" | "confiscate",
    or the PROVISIONAL "skip" sentinel (rules/officers.py module
    docstring) for the rare case where the 2nd action has no legal
    target at all — only legal once at least 1 real action was taken.
    `target_id` is a HoodId/SpotId for "move", a PawnId for a Cop's
    "arrest" (Fed arrest targets the Contact's lowest-level Link
    automatically, no target needed), and unused for "confiscate"/"skip"."""

    action: str
    target_id: str | None = None


@dataclass(frozen=True)
class BuyOfficer(Command):
    """§C6. One purchase per (buyer pawn, officer, destination) triple:
    direction (onto the map vs. into the buyer's Covo) is derived from
    the officer's current location, not chosen explicitly. `destination`
    is a HoodId/SpotId and is only meaningful (required) when buying an
    officer *out of* a Covo onto the map — a Link's presence spans every
    Hood/Spot of its Contact, and a Contact can have more than one Spot,
    so the destination can't always be inferred from the buyer alone;
    it's ignored (pass None) when buying a map officer into the buyer's
    own Covo, since that destination is implicitly the Covo itself."""

    purchases: tuple[tuple[PawnId, OfficerId, str | None], ...]


@dataclass(frozen=True)
class SpendLinkForExtraAction(Command):
    """§A5. Spends a Link pawn for an extra action outside the round's
    Grit-driven main action (at most once per turn); the Link's level
    becomes the extra action's Grit-equivalent value (how many pawns
    perform it) and the allowed action type(s) are restricted to its
    Contact's `link_extra_action_restricted_to` list."""

    pawn_id: PawnId


@dataclass(frozen=True)
class PlayBrawlCard(Command):
    """§D1 declare step: play one hand card face-down for this Rissa's
    Gun-assignment phase, or pass (card_id=None). Whether a card was
    played is public immediately; its identity stays hidden until
    AssignBrawlGuns reveals it."""

    card_id: CardId | None = None


@dataclass(frozen=True)
class AssignBrawlGuns(Command):
    """§D1 reveal step: reveal this player's declared card and send all
    of its Gun symbols to `target_player_id` (self, or one other
    participant — never split across several)."""

    target_player_id: PlayerId


@dataclass(frozen=True)
class ChooseBrawlLoserReward(Command):
    """One of the winner's reward choices, decided independently per
    defeated participant (RULES_CANONICAL.md §D1, confirmed 2026-08-01):
    `reward_type` is "money" (steal $2) or "card" (steal 1 random card —
    hands are hidden, so the winner can't pick which one)."""

    loser_player_id: PlayerId
    reward_type: str


@dataclass(frozen=True)
class ChooseBrawlLinkEvolution(Command):
    """§A5 optional reward: the winner may send one of their own
    Criminals still in the Rissa's Hood to become a level-1 Link of that
    Hood's Contact. `pawn_id=None` declines."""

    pawn_id: PawnId | None = None


@dataclass(frozen=True)
class ChooseBrawlRelocationDestination(Command):
    """Where the defeated Criminals are sent (§D1/§F3): the id of an
    unrevealed Hood to reveal and send them to, or `None` for the Covo
    when no Hood is still unrevealed. The winner chooses (confirmed
    2026-08-01) when more than one unrevealed Hood is available."""

    hood_id: HoodId | None = None


@dataclass(frozen=True)
class LaunchPoker(Command):
    """§D2 (corrected 2026-08-01): play a Preti Gamble card (`card_id`) to
    launch a Poker match — only offered right after `ChooseActionType`,
    and only when the card's own `action_type` matches the action (main
    or Link extra) just chosen for this round. Declining the offer
    entirely is `PassOptionalStep`, not this command. Capped at 1 per
    round (`player.gamble_cards_played_this_round`) and 2 matches per turn
    (`state.poker.matches_this_turn`)."""

    card_id: CardId


@dataclass(frozen=True)
class PlacePokerBet(Command):
    """§D2 end-of-turn betting round: stake 1 Chip on each of the given
    open matches (0 to as many Gamblers this player has in the Den, up
    to the 2 that can ever exist). An empty tuple is a legal "sit this
    turn's Poker out" — no separate pass command exists for this step."""

    match_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChooseJobReward(Command):
    """§A10: bank the bonus of a just-completed Job by claiming one of
    the still-free columns on its shared board row (`column_index`).
    `contact_id` is required only when the Job lists 2 Contacts (job
    designer confirmed 2026-08-01: the completing player picks freely
    between them); otherwise it must be omitted/`None`. No PassOptionalStep
    exists for this step — a just-completed Job always has at least one
    free column left for whoever is completing it (the confirmed board
    rule: the first player to complete a Job picks any of its 4 columns,
    each later completer of the same Job picks among what's left)."""

    column_index: int
    contact_id: ContactId | None = None


@dataclass(frozen=True)
class ChooseRaidFirstPlayer(Command):
    """§D4: the player with the highest-level Preti Link decides the
    round's first player — and, by extension ("quindi le squadre"), the
    Raid teams too, since they're derived from the game's own turn
    rotation order starting at `first_player_id`. Offered at `TIP_OFF`,
    right after the turn's Raid card is revealed; only offered at all
    when at least one player currently holds a Preti Link (otherwise
    `first_player_id` stays unchanged, per the documented fallback)."""

    chosen_first_player_id: PlayerId


@dataclass(frozen=True)
class StainReputationForMoney(Command):
    """§D5: a player with `stain_rep_for_cash.money_threshold` dollars or
    fewer may voluntarily flip one of their own clean REP tokens (a Job
    board cell) to stain it, in exchange for
    `stain_rep_for_cash.cash_gained` dollars. Offered at the same two
    per-round points as a Link's extra action (`rules/turn_flow.py`),
    always declinable via PassOptionalStep."""


@dataclass(frozen=True)
class PlayPokerCard(Command):
    """§D2 reveal step: a bettor on `match_id` reveals one hand card —
    any *non*-Preti card (independent of the 1-Gamble-card-per-round
    launch limit; a Preti card has no `poker_symbols` of its own) — to
    contribute its 2 Poker symbols to their personal 5-symbol hand (the
    match's shared 3-symbol banco, plus these 2)."""

    match_id: str
    card_id: CardId
