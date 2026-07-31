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
from dope_engine.domain.ids import CardId, ContactId, DecisionId, GameId, HoodId, PawnId, PlayerId


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
