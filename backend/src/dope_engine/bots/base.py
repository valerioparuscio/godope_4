"""BotPolicy protocol (CLAUDE.md section 14.1): a bot only ever sees a
`PlayerGameView` and a `PendingDecision` — the same inputs a human
frontend gets — and returns a fully-formed `Command` ready for the
command bus. It must never invent an option `get_legal_decision` did not
offer.

`choose()` also receives an optional `simulate` (2026-09-27, "ragiona su
come migliorare i bot... concentrati sull'ottimizzazione delle scelte
del singolo bot come se giocasse da solo", game designer — self-focused
look-ahead, deliberately *not* modeling what other players might do) —
a closure `GameService.advance()` builds fresh for each bot call, from
the real live `GameState` it already has in scope there. Calling it with
a sequence of hypothetical `Command`s applies them in order against a
private deep copy (the same deep-copy safety `CommandBus.dispatch`
already guarantees for every *real* command, CLAUDE.md section 19) and
returns the resulting `PlayerGameView` for the *same* player who's
choosing — never a raw `GameState`, and never another player's view, so
a bot simulating its own candidate move still can't peek at hidden
information (opponents' hands, deck order) any more than it legitimately
could by actually taking that action for real. Returns `None` if any
command in the sequence is illegal against the simulated state.

Optional (defaults to `None`) so `RandomLegalBot` and any test building
a `BotPolicy` by hand can ignore it entirely — only `HeuristicBot`'s
`choose_action_type` branch uses it so far (`bots/scoring.py::
score_action_type_by_simulation`)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from dope_engine.application.views import PlayerGameView
from dope_engine.domain.commands import Command
from dope_engine.domain.decisions import PendingDecision

SimulateFn = Callable[[Sequence[Command]], "PlayerGameView | None"]


class BotPolicy(Protocol):
    def choose(
        self,
        view: PlayerGameView,
        decision: PendingDecision,
        simulate: SimulateFn | None = None,
    ) -> Command: ...
