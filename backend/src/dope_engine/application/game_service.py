"""Ties the pieces together into the one API a transport adapter (HTTP,
or a debug CLI) needs: create a game, dispatch a player's command, and
advance bots/automatic phases until a human decision or game end.

This is the layer CLAUDE.md section 13's endpoints sit directly on top
of; nothing here is HTTP-specific.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.application.data_loader import GameData
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.application.views import PlayerGameView, build_player_view
from dope_engine.bots.base import BotPolicy
from dope_engine.domain.commands import Command
from dope_engine.domain.enums import ControllerType, GamePhase, GameStatus
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import GameId, PlayerId
from dope_engine.domain.state import GameState, find_player
from dope_engine.rules import setup, turn_flow


class IllegalBotCommandError(RuntimeError):
    """A BotPolicy produced a command the command bus rejected — a bot
    bug, since bots must only ever choose among get_legal_decision's
    options."""


@dataclass(frozen=True)
class AdvanceResult:
    state: GameState
    events: tuple[DomainEvent, ...]


class GameService:
    def __init__(self, game_data: GameData, *, bot_policy: BotPolicy) -> None:
        self._game_data = game_data
        self._bot_policy = bot_policy
        self._bus = CommandBus()
        card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
        turn_flow.register_handlers(self._bus, card_contact_by_id=card_contact_by_id)

    def create_game(self, *, game_id: GameId, seed: int, human_seat: int) -> AdvanceResult:
        state, events = setup.create_initial_state(
            self._game_data, game_id=game_id, seed=seed, human_seat=human_seat
        )
        _refresh_pending_decision(state)
        return AdvanceResult(state=state, events=tuple(events))

    def dispatch(self, state: GameState, command: Command) -> CommandOutcome:
        outcome = self._bus.dispatch(state, command)
        if isinstance(outcome, CommandSuccess):
            _refresh_pending_decision(outcome.state)
        return outcome

    def view_for(self, state: GameState, player_id: PlayerId) -> PlayerGameView:
        return build_player_view(state, player_id)

    def advance(self, state: GameState, *, max_steps: int = 10_000) -> AdvanceResult:
        """Resolve bot turns until a human decision is pending or the
        game finishes (CLAUDE.md section 13, `/advance`)."""
        collected: list[DomainEvent] = []

        for _ in range(max_steps):
            if state.status == GameStatus.FINISHED:
                break
            if state.phase != GamePhase.ACTION_PHASE or state.pending_decision is None:
                # Milestone 1: every non-ACTION_PHASE transition is fully
                # automatic and already happened inside the last dispatch
                # (see rules/turn_flow.py cascades), so there is nothing
                # left to drive here — this branch only guards against
                # an inconsistent state.
                break

            current_player = find_player(state, state.current_player_id)
            if current_player.controller_type == ControllerType.HUMAN:
                break

            view = build_player_view(state, current_player.player_id)
            command = self._bot_policy.choose(view, state.pending_decision)
            outcome = self.dispatch(state, command)
            if isinstance(outcome, CommandFailure):
                raise IllegalBotCommandError(
                    f"Bot for player '{current_player.player_id}' produced an illegal "
                    f"command: {outcome.error}"
                )
            state = outcome.state
            collected.extend(outcome.events)

        return AdvanceResult(state=state, events=tuple(collected))


def _refresh_pending_decision(state: GameState) -> None:
    if state.phase == GamePhase.ACTION_PHASE:
        state.pending_decision = get_legal_decision(state, state.current_player_id)
    else:
        state.pending_decision = None
