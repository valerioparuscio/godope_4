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
    LinkBecameCriminal,
    PawnBecameGambler,
)
from dope_engine.domain.ids import DEN_ID, JAIL_ID, ContactId, HoodId, PawnId, PlayerId
from dope_engine.domain.state import (
    GameState,
    PawnState,
    PlayerState,
    hoods_within_two_steps,
    max_pawns_per_player_per_hood,
    own_pawns_in_hood,
)
from dope_engine.rules import jail, links, move_followups, turn_flow
from dope_engine.rules.economy import check_hood_cop_removal, draw_card
from dope_engine.rules.event_utils import emit as _emit


def process_move_queue(
    state: GameState,
    player_id: PlayerId,
    player: PlayerState,
    moves: list[tuple[PawnId, HoodId, ContactId | None, ContactId | None]],
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
    bot/client bug — its options should never have included it.

    Each queued move is a 4-tuple (pawn_id, destination, deck_contact_id,
    extra_deck_contact_id) — the last element is cards 032/036's own
    second Den deck choice (`MoveCriminal.extra_den_deck_contact_ids`,
    zipped onto the matching `DEN_ID` moves once in
    `rules/economy.py::_handle_move_criminal`, before this queue is
    built), carried on the move itself rather than as a separate parallel
    counter so it survives a Brawl pausing/resuming the package unchanged
    (`rules/brawl.py::BrawlProgress.remaining_moves` stashes whatever's
    left of this same queue, verbatim)."""
    while moves:
        pawn_id, destination, deck_contact_id, extra_deck_contact_id = moves.pop(0)
        error = move_one_pawn(
            state,
            player_id,
            player,
            pawn_id,
            destination,
            deck_contact_id,
            events,
            extra_deck_contact_id,
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
    if not move_followups.begin(state, player):
        turn_flow.finish_action_or_extra(state, player, events)
    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def _draw_bonus_cards_for_move_boost(
    state: GameState,
    player: PlayerState,
    contact_id: ContactId,
    events: list[DomainEvent],
    *,
    entered_new_hood: bool = False,
) -> None:
    """Cards 029/031 "SWEET"/"MAKE FRIENDS" ("pesca due carte per ogni
    piazza in cui ti muovi" — 2 *total*, confirmed by the user,
    2026-09-02: `count` is additional draws on top of the one normal
    draw every move already does just above each call site, not the
    full total — same off-by-one `data/customer_cards.json` bug fixed
    for place_criminal's cards 046/050) — same `bonus_card_draw_per_unit`
    effect type as those, triggered here at every one of
    `move_one_pawn`'s own three normal-draw call sites (Hood move, Den
    entry, Gambler-to-Criminal exit) instead of just the plain Hood-move
    case, since the card offers per `move_criminal` itself, not per
    destination kind."""
    boost = player.active_card_boost
    if boost is None:
        return
    # Card 40 "MAKE FRIENDS" (game designer, 2026-10-15): entering a Hood where the player has
    # no Criminal yet draws 2 cards in total (`count` extra on top of the normal draw) instead
    # of 1, for every such movement.
    if boost["type"] == "bonus_card_draw_new_hood" and not entered_new_hood:
        return
    if boost["type"] not in ("bonus_card_draw_per_unit", "bonus_card_draw_new_hood"):
        return
    for _ in range(boost["count"]):
        draw_card(state, contact_id, events, player.player_id)


def _split_link_into_criminal(
    state: GameState,
    player_id: PlayerId,
    player: PlayerState,
    pawn: PawnState,
    destination: HoodId,
    deck_contact_id: ContactId | None,
    events: list[DomainEvent],
) -> DomainError | None:
    """Card 31 "SPLIT" (game designer, 2026-10-15): one of the player's Links goes back to
    being a Criminal in a Hood of its own Contact (the player's choice), like any other
    move: it draws that Hood's card and may trigger a Rissa."""
    dest_hood = state.board.hoods.get(destination)
    if dest_hood is None or dest_hood.contact_id != pawn.contact_id:
        return DomainError(
            code="not_a_hood_of_the_contact",
            message="A Link can only come back to a Hood of its own Contact.",
            details={},
        )
    if deck_contact_id is not None:
        return DomainError(
            code="unexpected_deck_choice",
            message="Deck choice only applies when entering the Den.",
            details={},
        )
    if not dest_hood.revealed:
        return DomainError(
            code="hood_not_revealed",
            message=f"Hood '{destination}' is not revealed yet.",
            details={},
        )
    if len(dest_hood.criminal_pawn_ids) >= dest_hood.capacity:
        return DomainError(
            code="hood_capacity_exceeded", message=f"Hood '{destination}' is full.", details={}
        )
    if own_pawns_in_hood(state, player_id, destination) >= max_pawns_per_player_per_hood(
        state.configuration
    ):
        return DomainError(
            code="player_hood_limit_exceeded",
            message=f"Hood '{destination}' already has the most pawns one player may have.",
            details={},
        )
    contact_id = pawn.contact_id
    assert contact_id is not None
    entered_new_hood = own_pawns_in_hood(state, player_id, destination) == 0
    player.moved_pawn_ids_this_turn.append(pawn.pawn_id)
    pawn.role = PawnRole.CRIMINAL
    pawn.contact_id = None
    pawn.link_level = None
    pawn.location = PawnLocation.hood(destination)
    dest_hood.criminal_pawn_ids.append(pawn.pawn_id)
    _emit(
        state,
        events,
        LinkBecameCriminal,
        player_id=player_id,
        pawn_id=pawn.pawn_id,
        contact_id=contact_id,
        hood_id=destination,
    )
    links.check_spot_fed_removal_for_contact(state, contact_id, events)
    draw_card(state, dest_hood.contact_id, events, player_id)
    _draw_bonus_cards_for_move_boost(
        state, player, dest_hood.contact_id, events, entered_new_hood=entered_new_hood
    )
    move_followups.note_entered_hood(state, player, destination)
    return None


def move_one_pawn(
    state: GameState,
    player_id: PlayerId,
    player: PlayerState,
    pawn_id: PawnId,
    destination: HoodId,
    deck_contact_id: ContactId | None,
    events: list[DomainEvent],
    extra_deck_contact_id: ContactId | None = None,
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

        # Card 033 "MANEUVER" ("muovi un criminale da un quartiere
        # qualunque in prigione", game designer, 2026-08-31): the
        # destination sentinel `JAIL_ID` (mirrors `DEN_ID`'s own
        # always-valid special-Hood pattern, but only legal at all when
        # this specific boost is active — normal moves can never target
        # it). Self-arrest, not a relocation: no adjacency/capacity
        # check, no card draw, and it never contributes to a Rissa the
        # way arriving in a real Hood would (`process_move_queue` only
        # checks `state.board.hoods.get(destination)`, which is `None`
        # for this sentinel, so that check already no-ops here).
        boost = player.active_card_boost
        if destination == JAIL_ID:
            if boost is None or boost["type"] != "move_to_jail":
                return DomainError(
                    code="unknown_hood", message=f"Unknown Hood '{destination}'.", details={}
                )
            from_hood.criminal_pawn_ids.remove(pawn_id)
            player.moved_pawn_ids_this_turn.append(pawn_id)
            jail.arrest_pawn(state, pawn_id, events)
            check_hood_cop_removal(state, from_hood, events)
            return None

        entering_den = destination == DEN_ID
        if entering_den:
            # Card 32 "SEAT SWAP": with a full Den the entry is still possible when there is
            # an opposing Gambler to swap with (the swap is then mandatory).
            swap_possible = (
                boost is not None
                and boost["type"] == "den_seat_swap"
                and bool(
                    move_followups.enemy_gamblers_swappable(state, player, from_hood.hood_id)
                )
            )
            if (
                len(state.board.den_gambler_pawn_ids) >= state.configuration["den_capacity"]
                and not swap_possible
            ):
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
            # Cards 032/036 "PLAY!!" ("se vai nel Den, peschi 2 carte a
            # scelta", game designer, 2026-08-31: confirmed 2 independent
            # deck choices, not the same deck drawn twice): a *second*
            # deck choice is required only while this boost is active —
            # `_draw_bonus_cards_for_move_boost`'s own `bonus_card_draw_
            # per_unit` (cards 029/031) always redraws from the *same*
            # deck as the entry itself, so it can't cover this case.
            double_den_draw = boost is not None and boost["type"] == "double_den_draw"
            if double_den_draw and extra_deck_contact_id is None:
                return DomainError(
                    code="deck_choice_required",
                    message="This boost requires choosing a second deck to draw from.",
                    details={},
                )
            if not double_den_draw and extra_deck_contact_id is not None:
                return DomainError(
                    code="unexpected_deck_choice",
                    message="A second deck choice only applies with the PLAY!! boost.",
                    details={},
                )
        else:
            if extra_deck_contact_id is not None:
                return DomainError(
                    code="unexpected_deck_choice",
                    message="A second deck choice only applies when entering the Den.",
                    details={},
                )
            long_way = boost is not None and boost["type"] == "move_distance_2"
            # Card 94 "RIOT" (game designer, 2026-10-16): the free move after a corruption
            # may start from any Hood.
            anywhere = boost is not None and boost["type"] == "corrupt_move_anywhere"
            reachable = (
                list(state.board.hoods)
                if anywhere
                else hoods_within_two_steps(state, from_hood.hood_id)
                if long_way
                else from_hood.adjacent_hood_ids
            )
            if destination not in reachable:
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
            if own_pawns_in_hood(state, pawn.owner_player_id, destination) >= (
                max_pawns_per_player_per_hood(state.configuration)
            ):
                return DomainError(
                    code="player_hood_limit_exceeded",
                    message=f"Hood '{destination}' already has the most pawns one player may have.",
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
            move_followups.note_den_entry(state, player, pawn_id, from_hood.hood_id)
            draw_card(state, deck_contact_id, events, player_id)  # type: ignore[arg-type]
            _draw_bonus_cards_for_move_boost(state, player, deck_contact_id, events)  # type: ignore[arg-type]
            if extra_deck_contact_id is not None:
                draw_card(state, extra_deck_contact_id, events, player_id)
        else:
            entered_new_hood = own_pawns_in_hood(state, player_id, destination) == 0
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
            dest_contact_id = state.board.hoods[destination].contact_id
            draw_card(state, dest_contact_id, events, player_id)
            _draw_bonus_cards_for_move_boost(
                state, player, dest_contact_id, events, entered_new_hood=entered_new_hood
            )
            move_followups.note_entered_hood(state, player, destination)

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
        if own_pawns_in_hood(state, pawn.owner_player_id, destination) >= (
            max_pawns_per_player_per_hood(state.configuration)
        ):
            return DomainError(
                code="player_hood_limit_exceeded",
                message=f"Hood '{destination}' already has the most pawns one player may have.",
                details={},
            )
        if deck_contact_id is not None:
            return DomainError(
                code="unexpected_deck_choice",
                message="Deck choice only applies when entering the Den.",
                details={},
            )

        entered_new_hood = own_pawns_in_hood(state, player_id, destination) == 0
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
        _draw_bonus_cards_for_move_boost(
            state, player, dest_hood.contact_id, events, entered_new_hood=entered_new_hood
        )
        move_followups.note_entered_hood(state, player, destination)
        return None

    if pawn.role == PawnRole.LINK:
        # Cards 034/035 "REPOSITION" ("puoi muovere i criminali da un
        # Gancio ad uno vicino", game designer, 2026-08-31, clarified:
        # the *Link itself* moves to an adjacent Contact, not a
        # Criminal — a Link has no single "current Hood" to move from,
        # so adjacency is checked across *both* of its own Contact's
        # Hoods against the destination Hood, which only identifies the
        # target Contact (a Link gives presence at both of that
        # Contact's Hoods regardless of which one is named here).
        boost = player.active_card_boost
        if boost is not None and boost["type"] == "link_to_criminal":
            return _split_link_into_criminal(
                state, player_id, player, pawn, destination, deck_contact_id, events
            )
        if boost is None or boost["type"] != "link_reposition":
            return DomainError(
                code="pawn_cannot_move",
                message=f"Pawn '{pawn_id}' is not a Criminal or Gambler.",
                details={},
            )
        if deck_contact_id is not None or extra_deck_contact_id is not None:
            return DomainError(
                code="unexpected_deck_choice",
                message="Deck choice does not apply to repositioning a Link.",
                details={},
            )
        dest_hood = state.board.hoods.get(destination)
        if dest_hood is None:
            return DomainError(
                code="unknown_hood", message=f"Unknown Hood '{destination}'.", details={}
            )
        new_contact_id = dest_hood.contact_id
        if new_contact_id == pawn.contact_id:
            return DomainError(
                code="already_at_contact",
                message="The Link is already at this Contact.",
                details={},
            )
        old_contact_hood_ids = [
            hid for hid, h in state.board.hoods.items() if h.contact_id == pawn.contact_id
        ]
        adjacent_hood_ids = {
            adj_id
            for hid in old_contact_hood_ids
            for adj_id in state.board.hoods[hid].adjacent_hood_ids
        }
        if destination not in adjacent_hood_ids:
            return DomainError(
                code="not_adjacent",
                message=f"'{destination}' is not adjacent to the Link's own Contact.",
                details={},
            )
        player.moved_pawn_ids_this_turn.append(pawn_id)
        assert pawn.link_level is not None
        links.insert_link(state, player_id, pawn_id, new_contact_id, pawn.link_level, events)
        return None

    return DomainError(
        code="pawn_cannot_move",
        message=f"Pawn '{pawn_id}' is not a Criminal or Gambler.",
        details={},
    )
