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

from dope_engine.domain.ids import CardId, DecisionId, GameId, PlayerId


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
