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
from dope_engine.domain.content import CoveredHoodTileDefinition
from dope_engine.domain.enums import (
    ActionType,
    ControllerType,
    GamePhase,
    GameStatus,
    PokerSymbolColor,
)
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import CardId, ContactId, GameId, PlayerId, TileId
from dope_engine.domain.state import GameState, find_player
from dope_engine.rules import brawl, economy, officers, poker, setup, turn_flow
from dope_engine.rules.prices import PriceTracks


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
        self._price_tracks: PriceTracks = {
            dope_type: definition.price_track
            for dope_type, definition in game_data.dope_types.items()
        }
        self._link_extra_action_types: dict[ContactId, tuple[str, ...]] = {
            contact.contact_id: contact.link_extra_action_restricted_to
            for contact in game_data.contacts.contacts
        }
        self._card_contact_by_id: dict[CardId, ContactId] = {
            c.card_id: c.contact_id for c in game_data.customer_cards
        }
        card_contact_by_id = self._card_contact_by_id
        self._action_type_by_card_id: dict[CardId, ActionType | None] = {
            c.card_id: c.action_type for c in game_data.customer_cards
        }
        action_type_by_card_id = self._action_type_by_card_id
        gun_count_by_card_id: dict[CardId, int] = {
            c.card_id: c.gun_count for c in game_data.customer_cards
        }
        tile_by_id: dict[TileId, CoveredHoodTileDefinition] = {
            t.tile_id: t for t in game_data.board.covered_hood_tiles.tile_values
        }
        banco_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]] = {
            c.card_id: c.banco_symbols for c in game_data.customer_cards
        }
        poker_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]] = {
            c.card_id: c.poker_symbols for c in game_data.customer_cards
        }
        turn_flow.register_handlers(self._bus, card_contact_by_id=card_contact_by_id)
        economy.register_handlers(
            self._bus,
            price_tracks=self._price_tracks,
            card_contact_by_id=card_contact_by_id,
            link_extra_action_types=self._link_extra_action_types,
            action_type_by_card_id=action_type_by_card_id,
        )
        officers.register_handlers(self._bus, price_tracks=self._price_tracks)
        brawl.register_handlers(
            self._bus,
            gun_count_by_card_id=gun_count_by_card_id,
            card_contact_by_id=card_contact_by_id,
            tile_by_id=tile_by_id,
        )
        poker.register_handlers(
            self._bus,
            banco_symbols_by_card_id=banco_symbols_by_card_id,
            poker_symbols_by_card_id=poker_symbols_by_card_id,
            card_contact_by_id=card_contact_by_id,
            action_type_by_card_id=action_type_by_card_id,
        )

    def create_game(self, *, game_id: GameId, seed: int, human_seat: int) -> AdvanceResult:
        state, events = setup.create_initial_state(
            self._game_data, game_id=game_id, seed=seed, human_seat=human_seat
        )
        self._refresh_pending_decision(state)
        return AdvanceResult(state=state, events=tuple(events))

    def dispatch(self, state: GameState, command: Command) -> CommandOutcome:
        outcome = self._bus.dispatch(state, command)
        if isinstance(outcome, CommandSuccess):
            self._refresh_pending_decision(outcome.state)
        return outcome

    def _refresh_pending_decision(self, state: GameState) -> None:
        if state.phase in (GamePhase.ACTION_PHASE, GamePhase.POKER_PHASE):
            state.pending_decision = get_legal_decision(
                state,
                state.current_player_id,
                self._price_tracks,
                self._link_extra_action_types,
                self._card_contact_by_id,
                self._action_type_by_card_id,
            )
        else:
            state.pending_decision = None

    def view_for(self, state: GameState, player_id: PlayerId) -> PlayerGameView:
        return build_player_view(state, player_id, self._price_tracks)

    def advance(self, state: GameState, *, max_steps: int = 10_000) -> AdvanceResult:
        """Resolve bot turns until a human decision is pending or the
        game finishes (CLAUDE.md section 13, `/advance`)."""
        collected: list[DomainEvent] = []

        for _ in range(max_steps):
            if state.status == GameStatus.FINISHED:
                break
            if state.phase not in (GamePhase.ACTION_PHASE, GamePhase.POKER_PHASE):
                # Every phase besides these two is fully automatic and
                # already happened inside the last dispatch (see
                # rules/turn_flow.py cascades), so there is nothing left
                # to drive here. POKER_PHASE (§D2, Milestone 4) is the
                # one exception: betting and card-reveal are genuine
                # player decisions, same as ACTION_PHASE's own steps.
                break
            if state.pending_decision is None:
                # Guards against an inconsistent state — every real
                # decision point in the two phases above always
                # populates this (see rules/turn_flow.py::
                # _enter_grit_or_extra_action_offer and rules/poker.py).
                break

            current_player = find_player(state, state.current_player_id)
            if current_player.controller_type == ControllerType.HUMAN:
                break

            view = build_player_view(state, current_player.player_id, self._price_tracks)
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
