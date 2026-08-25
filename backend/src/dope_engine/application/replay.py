"""Replay: reconstruct a game from its initial seed plus the sequence of
accepted commands (CLAUDE.md §16), distinct from `save_load.py`'s
whole-state snapshot. `GameService` records every accepted command in
memory (`GameService.dispatch`), keyed by `game_id`; this module turns
that history plus the game's own seed into a portable JSON envelope, and
can drive that envelope back through a fresh `GameService` to reconstruct
(and verify) the same game.

Known limitation: a game loaded via `POST /load`
(`adapters/http/app.py::load_game`) has no command history before the
load point — replaying it only covers commands accepted *after* the
load, not the whole original game. Recording a command sequence inside a
save file itself is a separate, not-yet-built feature (CLAUDE.md §16
mentions it as optional, "opzionalmente comandi ed eventi").
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from dope_engine.application.command_bus import CommandFailure
from dope_engine.application.data_loader import GameData
from dope_engine.domain.commands import Command
from dope_engine.domain.ids import GameId
from dope_engine.domain.serialization import from_json_dict, to_json_dict
from dope_engine.domain.state import GameState

# Every concrete Command subclass is a direct subclass of Command (domain/
# commands.py) — built from that instead of a hand-maintained name list so
# a newly-added command type is automatically replay-serializable with no
# extra step here.
_COMMAND_CLASS_BY_NAME: dict[str, type[Command]] = {
    cls.__name__: cls for cls in Command.__subclasses__()
}


class ReplayReconstructionError(RuntimeError):
    """A recorded command that was accepted the first time was rejected
    during reconstruction — proof of either non-determinism in the engine
    or a gap in what was recorded, not a normal/expected outcome. Raised,
    never returned, same "genuinely a bug" precedent as
    `domain.errors.InvariantViolation`/`SaveFormatError`."""


def _serialize_command(command: Command) -> dict[str, Any]:
    data = {f.name: to_json_dict(getattr(command, f.name)) for f in fields(command)}
    data["command_type"] = type(command).__name__
    return data


def export_replay(
    state: GameState,
    commands: list[Command],
    *,
    human_seat: int,
    human_nickname: str | None,
) -> dict[str, Any]:
    """Builds the portable replay envelope for `state`'s game — its
    initial seed/human seat plus every command accepted so far (in
    `GameService`'s own in-memory `_command_history`, threaded in by the
    caller). `human_seat`/`human_nickname` are the exact values passed to
    `create_game` at the start, captured there rather than read back off
    `state.players` — a live `controller_type` scan would break for a
    game whose every seat has since been forced to BOT (e.g. a bulk
    simulation test), even though the original human seat is still a
    perfectly well-defined, unchanging fact about the game."""
    return {
        "schema_version": state.schema_version,
        "rules_version": state.rules_version,
        "game_id": str(state.game_id),
        "seed": state.seed,
        "human_seat": human_seat,
        "human_nickname": human_nickname,
        "commands": [_serialize_command(c) for c in commands],
    }


def reconstruct_from_replay(game_data: GameData, replay: dict[str, Any]) -> GameState:
    """Recreates the initial state from `replay`'s seed/human_seat, then
    re-dispatches every recorded command through a fresh `GameService` in
    order. The bot policy passed to that service is never actually
    invoked (nothing here calls `advance()` — every command, human or
    bot-authored the first time, is replayed explicitly), so any
    `BotPolicy` works; `RandomLegalBot` is reused rather than adding a
    dedicated no-op implementation.

    Imports GameService/RandomLegalBot locally rather than at module
    level: GameService itself calls export_replay below, so a
    module-level import here would be circular."""
    from dope_engine.application.game_service import GameService
    from dope_engine.bots.random_legal import RandomLegalBot

    current_rules_version = game_data.config["rules_version"]
    if replay["rules_version"] != current_rules_version:
        # create_initial_state always stamps the *currently loaded*
        # rules_version regardless of what's passed in (rules/setup.py) —
        # so reconstruction would silently proceed under different rules
        # rather than failing outright. CLAUDE.md §3.2's determinism
        # guarantee only holds for a matching rules_version, so this is
        # surfaced as an explicit error instead.
        raise ReplayReconstructionError(
            f"Replay was recorded under rules_version '{replay['rules_version']}', but this "
            f"engine is running '{current_rules_version}'."
        )

    service = GameService(game_data, bot_policy=RandomLegalBot())
    result = service.create_game(
        game_id=GameId(replay["game_id"]),
        seed=replay["seed"],
        human_seat=replay["human_seat"],
        human_nickname=replay.get("human_nickname"),
    )
    state = result.state

    for index, command_dict in enumerate(replay["commands"]):
        command_type = command_dict["command_type"]
        command_cls = _COMMAND_CLASS_BY_NAME.get(command_type)
        if command_cls is None:
            raise ReplayReconstructionError(
                f"Unknown command_type '{command_type}' at index {index}."
            )
        command = from_json_dict(command_cls, command_dict)
        outcome = service.dispatch(state, command)
        if isinstance(outcome, CommandFailure):
            raise ReplayReconstructionError(
                f"Command {index} ({command_type}) was accepted originally but rejected "
                f"during replay: {outcome.error}"
            )
        state = outcome.state

    return state
