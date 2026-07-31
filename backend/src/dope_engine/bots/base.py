"""BotPolicy protocol (CLAUDE.md section 14.1): a bot only ever sees a
`PlayerGameView` and a `PendingDecision` — the same inputs a human
frontend gets — and returns a fully-formed `Command` ready for the
command bus. It must never invent an option `get_legal_decision` did not
offer.
"""

from __future__ import annotations

from typing import Protocol

from dope_engine.application.views import PlayerGameView
from dope_engine.domain.commands import Command
from dope_engine.domain.decisions import PendingDecision


class BotPolicy(Protocol):
    def choose(self, view: PlayerGameView, decision: PendingDecision) -> Command: ...
