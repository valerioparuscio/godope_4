"""Typed domain errors.

A `DomainError` represents an ordinary illegal-command outcome (wrong
player, insufficient funds, stale revision, ...): something the command
bus *returns* as part of a `CommandOutcome`, never raises. Raising a
Python exception is reserved for genuine bugs (an invariant violation, a
malformed save file) that should abort loudly rather than be handled as
a normal rejected move.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DomainError:
    code: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)


def revision_mismatch(expected: int, actual: int) -> DomainError:
    return DomainError(
        code="revision_mismatch",
        message=f"Command targets revision {expected}, but state is at revision {actual}.",
        details={"expected_revision": expected, "actual_revision": actual},
    )


def unknown_command(command_type: str) -> DomainError:
    return DomainError(
        code="unknown_command",
        message=f"No handler registered for command type '{command_type}'.",
        details={"command_type": command_type},
    )


def wrong_player(expected: str, actual: str) -> DomainError:
    return DomainError(
        code="wrong_player",
        message=f"Command issued by '{actual}', but it is '{expected}'s turn to act.",
        details={"expected_player_id": expected, "actual_player_id": actual},
    )


def wrong_phase(expected: str, actual: str) -> DomainError:
    return DomainError(
        code="wrong_phase",
        message=f"Command requires phase '{expected}', but game is in phase '{actual}'.",
        details={"expected_phase": expected, "actual_phase": actual},
    )


class InvariantViolation(Exception):
    """Raised by validate_invariants when the state model itself is broken.

    Unlike DomainError, this is a programming-error signal (a bug in the
    engine let an inconsistent state through) and is expected to be
    raised, not returned.
    """
