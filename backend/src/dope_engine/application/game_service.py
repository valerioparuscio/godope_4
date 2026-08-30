"""Ties the pieces together into the one API a transport adapter (HTTP,
or a debug CLI) needs: create a game, dispatch a player's command, and
advance bots/automatic phases until a human decision or game end.

This is the layer CLAUDE.md section 13's endpoints sit directly on top
of; nothing here is HTTP-specific.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
from dope_engine.domain.content import CoveredHoodTileDefinition, JobDefinition
from dope_engine.domain.enums import (
    ActionType,
    ActiveStep,
    ControllerType,
    GamePhase,
    GameStatus,
    PokerSymbolColor,
)
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import CardId, ContactId, GameId, JobId, PlayerId, TileId
from dope_engine.domain.state import GameState, find_player
from dope_engine.rules import (
    brawl,
    customer_cards,
    economy,
    jobs,
    officers,
    poker,
    setup,
    turn_flow,
)
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
        # The default when a game doesn't specify its own — bot_policy is
        # otherwise per-game state now (_bot_policy_by_game_id below),
        # selectable at create_game() time (CreateGameRequest.bot_policy,
        # "basi per bot più intelligenti", 2026-08-25) rather than fixed
        # once for the whole process.
        self._default_bot_policy = bot_policy
        self._bot_policy_by_game_id: dict[GameId, BotPolicy] = {}
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
        self._job_by_id: dict[JobId, JobDefinition] = {j.job_id: j for j in game_data.jobs}
        job_by_id = self._job_by_id
        # Every accepted command, in order, per game_id — for Replay
        # (application/replay.py::export_replay), populated in dispatch()
        # below since that's the one chokepoint both a human's direct
        # command and every bot command during advance() funnel through.
        # In-memory only, same lifecycle as adapters/http/app.py's own
        # `_games` dict — see replay.py's own module docstring for the
        # save/load interaction this doesn't cover.
        self._command_history: dict[GameId, list[Command]] = {}
        # Captured at create_game() time rather than read back off
        # state.players later — see replay.py::export_replay's own
        # docstring for why a live controller_type scan isn't safe here.
        self._human_info_by_game_id: dict[GameId, tuple[int, str | None]] = {}
        stonk_count_by_card_id: dict[CardId, int] = {
            c.card_id: c.stonk_count for c in game_data.customer_cards
        }
        self._stonk_count_by_card_id = stonk_count_by_card_id
        self._card_effect_by_id: dict[CardId, dict[str, Any] | None] = {
            c.card_id: c.effect for c in game_data.customer_cards
        }
        card_effect_by_id = self._card_effect_by_id
        turn_flow.register_handlers(
            self._bus,
            card_contact_by_id=card_contact_by_id,
            stonk_count_by_card_id=stonk_count_by_card_id,
            action_type_by_card_id=action_type_by_card_id,
            card_effect_by_id=card_effect_by_id,
        )
        economy.register_handlers(
            self._bus,
            price_tracks=self._price_tracks,
            card_contact_by_id=card_contact_by_id,
            link_extra_action_types=self._link_extra_action_types,
            action_type_by_card_id=action_type_by_card_id,
            stonk_count_by_card_id=stonk_count_by_card_id,
            card_effect_by_id=card_effect_by_id,
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
            stonk_count_by_card_id=stonk_count_by_card_id,
            card_effect_by_id=card_effect_by_id,
        )
        jobs.register_handlers(self._bus, job_by_id=job_by_id)
        jobs.register_post_success_hook(self._bus, job_by_id=job_by_id)
        customer_cards.register_handlers(
            self._bus,
            card_effect_by_id=card_effect_by_id,
            action_type_by_card_id=action_type_by_card_id,
            card_contact_by_id=card_contact_by_id,
        )

    def create_game(
        self,
        *,
        game_id: GameId,
        seed: int,
        human_seat: int,
        human_nickname: str | None = None,
        bot_policy: BotPolicy | None = None,
    ) -> AdvanceResult:
        state, events = setup.create_initial_state(
            self._game_data,
            game_id=game_id,
            seed=seed,
            human_seat=human_seat,
            human_nickname=human_nickname,
        )
        self._command_history[game_id] = []
        self._human_info_by_game_id[game_id] = (human_seat, human_nickname)
        if bot_policy is not None:
            self._bot_policy_by_game_id[game_id] = bot_policy
        self._refresh_pending_decision(state)
        return AdvanceResult(state=state, events=tuple(events))

    def dispatch(self, state: GameState, command: Command) -> CommandOutcome:
        outcome = self._bus.dispatch(state, command)
        if isinstance(outcome, CommandSuccess):
            self._refresh_pending_decision(outcome.state)
            self._command_history.setdefault(outcome.state.game_id, []).append(command)
        return outcome

    def export_replay(self, state: GameState) -> dict[str, Any]:
        """Current game/seed + every command accepted so far, as a
        portable JSON envelope (application/replay.py::export_replay) —
        see that module's own docstring for the exact shape and the
        save/load interaction it doesn't cover."""
        from dope_engine.application.replay import export_replay

        human_info = self._human_info_by_game_id.get(state.game_id)
        if human_info is None:
            # A game loaded via /load never went through create_game(), so
            # it has no recorded human_seat/nickname here — fall back to
            # reading the live state (still correct for any normal,
            # just-loaded game; a game with no HUMAN player left at all,
            # e.g. a bulk simulation that force-BOTs every seat, has no
            # meaningful "human seat" left to report either way).
            human = next(
                (p for p in state.players if p.controller_type == ControllerType.HUMAN), None
            )
            human_info = (human.seat_index, human.display_name) if human else (0, None)
        human_seat, human_nickname = human_info
        return export_replay(
            state,
            self._command_history.get(state.game_id, []),
            human_seat=human_seat,
            human_nickname=human_nickname,
        )

    def _refresh_pending_decision(self, state: GameState) -> None:
        # WAITING_FOR_JOB_REWARD can be pending outside the three normal
        # phases too (see `get_legal_decision`'s own docstring note on
        # this) — a Job completed by the last turn's own Poker/Raid
        # outcome leaves `state.phase` at SHOWDOWN_PHASE by the time this
        # runs, but the reward is still real and must still be exposed.
        active_phases = (GamePhase.TIP_OFF, GamePhase.ACTION_PHASE, GamePhase.POKER_PHASE)
        if state.phase in active_phases or state.active_step == ActiveStep.WAITING_FOR_JOB_REWARD:
            state.pending_decision = get_legal_decision(
                state,
                state.current_player_id,
                self._price_tracks,
                self._link_extra_action_types,
                self._card_contact_by_id,
                self._action_type_by_card_id,
                self._job_by_id,
                self._stonk_count_by_card_id,
                self._card_effect_by_id,
            )
        else:
            state.pending_decision = None

    def view_for(self, state: GameState, player_id: PlayerId) -> PlayerGameView:
        return build_player_view(state, player_id, self._price_tracks)

    def advance(
        self,
        state: GameState,
        *,
        max_steps: int = 10_000,
        single_player_segment: bool = False,
    ) -> AdvanceResult:
        """Resolve bot turns until a human decision is pending or the
        game finishes (CLAUDE.md section 13, `/advance`).

        `single_player_segment=True` (2026-08-16) also stops as soon as
        `current_player_id` changes away from whoever it was when this
        call started — i.e. resolves *one* bot's own turn-segment
        (however many commands that took) instead of the whole cascade,
        so a client can call this repeatedly and render/narrate each
        bot's segment before asking for the next one, rather than the
        board jumping straight to the fully-resolved end state (game
        designer: "se tre bot di fila piazzano non vorrei vedere
        comparire tutte le pedine alla fine, ma dopo ogni singolo bot")."""
        collected: list[DomainEvent] = []
        segment_player_id = state.current_player_id if single_player_segment else None
        bot_policy = self._bot_policy_by_game_id.get(state.game_id, self._default_bot_policy)

        for _ in range(max_steps):
            if state.status == GameStatus.FINISHED:
                break
            active_phases = (GamePhase.TIP_OFF, GamePhase.ACTION_PHASE, GamePhase.POKER_PHASE)
            if (
                state.phase not in active_phases
                and state.active_step != ActiveStep.WAITING_FOR_JOB_REWARD
            ):
                # Every phase besides these three is fully automatic and
                # already happened inside the last dispatch (see
                # rules/turn_flow.py cascades), so there is nothing left
                # to drive here. POKER_PHASE (§D2, Milestone 4) and
                # TIP_OFF's Raid first-player choice (§D4, Milestone 5)
                # are the exceptions: genuine player decisions, same as
                # ACTION_PHASE's own steps. WAITING_FOR_JOB_REWARD is a
                # further exception (2026-08-17): it can be pending at
                # SHOWDOWN_PHASE too, right at the last turn's end, when
                # its own Poker/Raid resolution completes a Job — that
                # reward must still resolve (a bot claims it here, a human
                # sees it via `pending_decision`) before the game can
                # finalize (`rules/turn_flow.py::finalize_game_if_ready`).
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
            if (
                single_player_segment
                and segment_player_id is not None
                and state.current_player_id != segment_player_id
            ):
                break

            view = build_player_view(state, current_player.player_id, self._price_tracks)
            command = bot_policy.choose(view, state.pending_decision)
            outcome = self.dispatch(state, command)
            if isinstance(outcome, CommandFailure):
                raise IllegalBotCommandError(
                    f"Bot for player '{current_player.player_id}' produced an illegal "
                    f"command: {outcome.error}"
                )
            state = outcome.state
            collected.extend(outcome.events)

        return AdvanceResult(state=state, events=tuple(collected))
