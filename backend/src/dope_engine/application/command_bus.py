"""Generic command dispatch: revision/game_id checks are centralized
here so no rule handler has to remember them; the handler itself only
ever sees a private deep copy of the state, so a rejected command can
never leak a partial mutation back to the caller (CLAUDE.md section 19).

Concrete handlers (PlaceCriminal, BuyDope, ...) are registered by the
rule modules that implement them, starting in Milestone 1/2 — this
module only owns the dispatch mechanism.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from dope_engine.domain.commands import Command
from dope_engine.domain.errors import DomainError, revision_mismatch, unknown_command
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.state import GameState


@dataclass(frozen=True)
class CommandSuccess:
    state: GameState
    events: tuple[DomainEvent, ...]


@dataclass(frozen=True)
class CommandFailure:
    error: DomainError


CommandOutcome = CommandSuccess | CommandFailure

# A handler receives its own private deep copy of the state (already
# revision/game_id-checked) and either mutates it into the next state +
# returns CommandSuccess (bumping `state.revision` itself), or returns
# CommandFailure without having mutated anything observable by the caller.
CommandHandler = Callable[[GameState, Command], CommandOutcome]

C = TypeVar("C", bound=Command)


class CommandBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Command], CommandHandler] = {}

    def register(
        self, command_type: type[C], handler: Callable[[GameState, C], CommandOutcome]
    ) -> None:
        # Keyed dispatch in `dispatch()` guarantees a handler registered
        # for `command_type` is only ever called with an instance of
        # that exact type, so this narrowing is safe even though the
        # dict's declared value type is the wider CommandHandler.
        self._handlers[command_type] = handler  # type: ignore[assignment]

    def dispatch(self, state: GameState, command: Command) -> CommandOutcome:
        if command.game_id != state.game_id:
            return CommandFailure(
                DomainError(
                    code="wrong_game",
                    message=(
                        f"Command targets game '{command.game_id}', "
                        f"state is game '{state.game_id}'."
                    ),
                    details={"command_game_id": command.game_id, "state_game_id": state.game_id},
                )
            )

        if command.expected_revision != state.revision:
            return CommandFailure(revision_mismatch(command.expected_revision, state.revision))

        handler = self._handlers.get(type(command))
        if handler is None:
            return CommandFailure(unknown_command(type(command).__name__))

        working_copy = copy.deepcopy(state)
        return handler(working_copy, command)
