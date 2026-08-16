"""Criminal/Gambler movement (RULES_CANONICAL.md §C2), extracted from
rules/economy.py because it's the one action that can interrupt itself:
moving a Criminal into a Hood that already has 4 there triggers a Rissa
(§D1) immediately, on *whichever* move in a Grit-bundled package reaches
that count — not necessarily the last one. `process_move_queue` is the
single place that both `economy.py`'s MoveCriminal handler and
`rules/brawl.py`'s "package resumes once the Rissa resolves" path call
into, so the trigger check only has to live in one place.

`rules/brawl.py` needs to call back into `process_move_queue` once a
Rissa resolves (to finish any moves that were still queued when it
interrupted), so the dependency here (`movement` -> `brawl`, to start
one) runs one-directional to avoid a circular import; `brawl.py` reaches
back into this module with a local import inside its own finishing
function instead of a top-of-file one.
"""

from __future__ import annotations

from dope_engine.application.command_bus import CommandFailure, CommandOutcome, CommandSuccess
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import PawnRole
from dope_engine.domain.errors import DomainError
from dope_engine.domain.events import (
    CriminalMoved,
    DomainEvent,
    GamblerBecameCriminal,
    PawnBecameGambler,
)
from dope_engine.domain.ids import DEN_ID, ContactId, HoodId, PawnId, PlayerId
from dope_engine.domain.state import GameState, PlayerState
from dope_engine.rules import turn_flow
from dope_engine.rules.economy import check_hood_cop_removal, draw_card
from dope_engine.rules.event_utils import emit as _emit


def process_move_queue(
    state: GameState,
    player_id: PlayerId,
    player: PlayerState,
    moves: list[tuple[PawnId, HoodId, ContactId | None]],
    events: list[DomainEvent],
    *,
    resuming: bool = False,
) -> CommandOutcome:
    """`resuming=True` (only ever passed by rules/brawl.py's own
    `_finish_brawl`, when it resumes a package a Rissa just interrupted)
    tolerates a queued move that's gone stale: a Rissa can reposition or
    remove *other* pawns of the very player whose package is paused —
    a defeated pawn of theirs sitting in that same Hood gets relocated
    or sent to base, invalidating a later queued move for it. Silently
    dropping that one move (instead of failing the whole resumption
    command) is the only sound option once it's not the fresh command
    being validated anymore; a *first-time* submission (resuming=False)
    still fails loudly on an illegal move, since that always means a
    bot/client bug — its options should never have included it."""
    while moves:
        pawn_id, destination, deck_contact_id = moves.pop(0)
        error = move_one_pawn(
            state, player_id, player, pawn_id, destination, deck_contact_id, events
        )
        if error is not None:
            if resuming:
                continue
            return CommandFailure(error)

        dest_hood = state.board.hoods.get(destination)
        trigger_count = state.configuration["brawl_trigger_criminal_count"]
        if dest_hood is not None and len(dest_hood.criminal_pawn_ids) >= trigger_count:
            from dope_engine.rules import brawl

            brawl.start_brawl(state, dest_hood, player_id, moves, events)
            state.event_log_cursor += len(events)
            return CommandSuccess(state=state, events=tuple(events))

    player.pending_action_type = None
    turn_flow.finish_action_or_extra(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def move_one_pawn(
    state: GameState,
    player_id: PlayerId,
    player: PlayerState,
    pawn_id: PawnId,
    destination: HoodId,
    deck_contact_id: ContactId | None,
    events: list[DomainEvent],
) -> DomainError | None:
    pawn = state.pawns.get(pawn_id)
    if pawn is None or pawn.owner_player_id != player_id:
        return DomainError(
            code="pawn_not_owned", message=f"Pawn '{pawn_id}' is not yours.", details={}
        )
    if pawn_id in player.moved_pawn_ids_this_turn:
        return DomainError(
            code="pawn_already_moved_this_turn",
            message=f"Pawn '{pawn_id}' already moved this turn.",
            details={},
        )

    if pawn.role == PawnRole.CRIMINAL:
        from_hood = state.board.hoods[pawn.location.hood_id]  # type: ignore[index]
        entering_den = destination == DEN_ID
        if entering_den:
            if len(state.board.den_gambler_pawn_ids) >= state.configuration["den_capacity"]:
                return DomainError(code="den_full", message="The Den is full.", details={})
            own_gamblers_in_den = sum(
                1
                for pid in state.board.den_gambler_pawn_ids
                if state.pawns[pid].owner_player_id == player_id
            )
            if own_gamblers_in_den >= state.configuration["den_capacity_per_player"]:
                return DomainError(
                    code="den_full_for_player",
                    message="You already have the maximum number of pawns in the Den.",
                    details={},
                )
            if deck_contact_id is None:
                return DomainError(
                    code="deck_choice_required",
                    message="Entering the Den requires choosing a deck to draw from.",
                    details={},
                )
        else:
            if destination not in from_hood.adjacent_hood_ids:
                return DomainError(
                    code="not_adjacent",
                    message=f"'{destination}' is not adjacent to '{from_hood.hood_id}'.",
                    details={},
                )
            dest_hood = state.board.hoods.get(destination)
            if dest_hood is None:
                return DomainError(
                    code="unknown_hood", message=f"Unknown Hood '{destination}'.", details={}
                )
            if not dest_hood.revealed:
                # Only a Brawl loser's relocation can reach an unrevealed
                # Hood (game designer, 2026-08-16) — never a normal move.
                return DomainError(
                    code="hood_not_revealed",
                    message=f"Hood '{destination}' is not revealed yet.",
                    details={},
                )
            if len(dest_hood.criminal_pawn_ids) >= dest_hood.capacity:
                return DomainError(
                    code="hood_capacity_exceeded",
                    message=f"Hood '{destination}' is full.",
                    details={},
                )
            if deck_contact_id is not None:
                return DomainError(
                    code="unexpected_deck_choice",
                    message="Deck choice only applies when entering the Den.",
                    details={},
                )

        from_hood.criminal_pawn_ids.remove(pawn_id)
        player.moved_pawn_ids_this_turn.append(pawn_id)

        if entering_den:
            pawn.role = PawnRole.GAMBLER
            pawn.location = PawnLocation.den()
            state.board.den_gambler_pawn_ids.append(pawn_id)
            _emit(state, events, PawnBecameGambler, player_id=player_id, pawn_id=pawn_id)
            draw_card(state, deck_contact_id, events, player_id)  # type: ignore[arg-type]
        else:
            pawn.location = PawnLocation.hood(destination)
            state.board.hoods[destination].criminal_pawn_ids.append(pawn_id)
            _emit(
                state,
                events,
                CriminalMoved,
                player_id=player_id,
                pawn_id=pawn_id,
                from_hood_id=from_hood.hood_id,
                to_hood_id=destination,
            )
            draw_card(state, state.board.hoods[destination].contact_id, events, player_id)

        check_hood_cop_removal(state, from_hood, events)
        return None

    if pawn.role == PawnRole.GAMBLER:
        if destination == DEN_ID:
            return DomainError(
                code="already_in_den", message="Pawn is already in the Den.", details={}
            )
        dest_hood = state.board.hoods.get(destination)
        if dest_hood is None:
            return DomainError(
                code="unknown_hood", message=f"Unknown Hood '{destination}'.", details={}
            )
        if not dest_hood.revealed:
            # Only a Brawl loser's relocation can reach an unrevealed
            # Hood (game designer, 2026-08-16) — never a normal move.
            return DomainError(
                code="hood_not_revealed",
                message=f"Hood '{destination}' is not revealed yet.",
                details={},
            )
        if len(dest_hood.criminal_pawn_ids) >= dest_hood.capacity:
            return DomainError(
                code="hood_capacity_exceeded", message=f"Hood '{destination}' is full.", details={}
            )
        if deck_contact_id is not None:
            return DomainError(
                code="unexpected_deck_choice",
                message="Deck choice only applies when entering the Den.",
                details={},
            )

        state.board.den_gambler_pawn_ids.remove(pawn_id)
        player.moved_pawn_ids_this_turn.append(pawn_id)
        pawn.role = PawnRole.CRIMINAL
        pawn.location = PawnLocation.hood(destination)
        dest_hood.criminal_pawn_ids.append(pawn_id)
        _emit(
            state,
            events,
            GamblerBecameCriminal,
            player_id=player_id,
            pawn_id=pawn_id,
            hood_id=destination,
        )
        draw_card(state, dest_hood.contact_id, events, player_id)
        return None

    return DomainError(
        code="pawn_cannot_move",
        message=f"Pawn '{pawn_id}' is not a Criminal or Gambler.",
        details={},
    )
