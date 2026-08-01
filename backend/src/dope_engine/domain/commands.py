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
    """§C3. One Dope purchase per listed pawn, in its current Hood."""

    pawn_ids: tuple[PawnId, ...]


@dataclass(frozen=True)
class SellDope(Command):
    """§C4. One Dope sale per (pawn, dope_type) pair, at the Spot of the
    pawn's current Hood's Contact that accepts that Dope type."""

    sales: tuple[tuple[PawnId, DopeType], ...]


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
