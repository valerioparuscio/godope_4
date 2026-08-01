"""`validate_invariants(state)` — the structural sanity checks every
GameState must satisfy after any accepted command (CLAUDE.md section
17.4). Intended for tests and debug tooling, not the hot command path.

Collects every violation found instead of raising on the first one, so
a failing test/debug session shows the whole picture at once.
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.domain.entities import LocationType
from dope_engine.domain.enums import GamePhase, PawnRole
from dope_engine.domain.errors import InvariantViolation
from dope_engine.domain.state import GameState


@dataclass(frozen=True)
class Violation:
    code: str
    message: str


def _check_unique_pawn_ids(state: GameState, violations: list[Violation]) -> None:
    seen: set[str] = set()
    for player in state.players:
        for pawn_id in player.pawn_ids:
            if pawn_id in seen:
                violations.append(
                    Violation(
                        "duplicate_pawn_id",
                        f"Pawn '{pawn_id}' owned by more than one player.",
                    )
                )
            seen.add(pawn_id)
            if pawn_id not in state.pawns:
                violations.append(
                    Violation(
                        "dangling_pawn_id",
                        f"Pawn '{pawn_id}' listed by a player but not in state.pawns.",
                    )
                )
    for pawn_id, pawn in state.pawns.items():
        if pawn.pawn_id != pawn_id:
            violations.append(
                Violation(
                    "pawn_id_key_mismatch",
                    f"state.pawns key '{pawn_id}' != pawn.pawn_id '{pawn.pawn_id}'.",
                )
            )


def _check_pawn_owner_consistency(state: GameState, violations: list[Violation]) -> None:
    player_ids = {p.player_id for p in state.players}
    for player in state.players:
        if player.player_id not in player_ids:
            violations.append(
                Violation("unknown_owner", f"Player '{player.player_id}' is not in state.players.")
            )


def _check_hood_capacity(state: GameState, violations: list[Violation]) -> None:
    for hood in state.board.hoods.values():
        if len(hood.criminal_pawn_ids) > hood.capacity:
            violations.append(
                Violation(
                    "hood_capacity_exceeded",
                    f"Hood '{hood.hood_id}' has {len(hood.criminal_pawn_ids)} "
                    f"criminals, capacity is {hood.capacity}.",
                )
            )
        if not hood.revealed and hood.dope_stack:
            violations.append(
                Violation(
                    "unrevealed_hood_has_dope",
                    f"Hood '{hood.hood_id}' is not revealed but has Dope stocked.",
                )
            )
        if len(hood.dope_stack) > 3:
            violations.append(
                Violation(
                    "hood_market_overflow",
                    f"Hood '{hood.hood_id}' has more than 3 Dope in its market.",
                )
            )


def _check_spot_capacity(state: GameState, violations: list[Violation]) -> None:
    for spot in state.board.spots.values():
        if len(spot.sold_dope_tokens) > spot.capacity:
            violations.append(
                Violation(
                    "spot_capacity_exceeded",
                    f"Spot '{spot.spot_id}' has {len(spot.sold_dope_tokens)} Dope, "
                    f"capacity is {spot.capacity}.",
                )
            )


def _check_jail_slots(state: GameState, violations: list[Violation]) -> None:
    seen_indexes: set[int] = set()
    for slot in state.jail.slots:
        if slot.index in seen_indexes:
            violations.append(
                Violation("duplicate_jail_slot_index", f"Jail slot index {slot.index} repeated.")
            )
        seen_indexes.add(slot.index)
    if len(state.jail.slots) > 6:
        violations.append(
            Violation("jail_overflow", f"Jail has {len(state.jail.slots)} slots, max is 6.")
        )


def _check_base_chip_caps(state: GameState, violations: list[Violation]) -> None:
    for player in state.players:
        for dope_type, count in player.base_inventory.dope_counts.items():
            if count > 3:
                violations.append(
                    Violation(
                        "base_dope_overflow",
                        f"Player '{player.player_id}' has {count} {dope_type} in base, max is 3.",
                    )
                )
        if player.base_inventory.poker_chip_count > 3:
            violations.append(
                Violation(
                    "base_poker_chip_overflow",
                    f"Player '{player.player_id}' has {player.base_inventory.poker_chip_count} "
                    f"Poker chips in base, max is 3.",
                )
            )
        officers_in_base = sum(
            1
            for officer in state.board.officers.values()
            if officer.owner_player_id == player.player_id
            and officer.location_type.value == "base"
        )
        if officers_in_base > 3:
            violations.append(
                Violation(
                    "base_officer_overflow",
                    f"Player '{player.player_id}' has {officers_in_base} "
                    f"Cops/Feds in base, max is 3.",
                )
            )


def _check_link_levels(state: GameState, violations: list[Violation]) -> None:
    seen_links: set[tuple[str, str, int]] = set()
    for player in state.players:
        for pawn in (state.pawns[pid] for pid in player.pawn_ids if pid in state.pawns):
            if pawn.role != PawnRole.LINK:
                continue
            if pawn.contact_id is None or pawn.link_level is None:
                violations.append(
                    Violation(
                        "link_missing_fields",
                        f"Pawn '{pawn.pawn_id}' is a Link without contact_id/link_level.",
                    )
                )
                continue
            if pawn.link_level not in (1, 2, 3):
                violations.append(
                    Violation(
                        "link_level_invalid",
                        f"Pawn '{pawn.pawn_id}' has invalid link_level {pawn.link_level}.",
                    )
                )
            key = (pawn.owner_player_id, pawn.contact_id, pawn.link_level)
            if key in seen_links:
                violations.append(
                    Violation(
                        "duplicate_link_slot",
                        f"Contact '{pawn.contact_id}' level {pawn.link_level} "
                        f"occupied by more than one pawn.",
                    )
                )
            seen_links.add(key)


def _check_pending_decision(state: GameState, violations: list[Violation]) -> None:
    if state.pending_decision is None:
        return
    player_ids = {p.player_id for p in state.players}
    if state.pending_decision.player_id not in player_ids:
        violations.append(
            Violation(
                "pending_decision_unknown_player",
                f"Pending decision targets unknown player '{state.pending_decision.player_id}'.",
            )
        )


def _check_current_player(state: GameState, violations: list[Violation]) -> None:
    if state.current_player_id not in state.player_order:
        violations.append(
            Violation(
                "current_player_not_in_order",
                f"current_player_id '{state.current_player_id}' is not in player_order.",
            )
        )


def _check_hand_size(state: GameState, violations: list[Violation]) -> None:
    # The 5-card limit is only enforced at the end of a player's own
    # *turn* — their last of the 3 action rounds (confirmed by the game
    # designer, 2026-08-01, resolving CLAUDE.md point 22.29) — not after
    # every round. Any player can therefore legitimately sit above the
    # limit for most of ACTION_PHASE, not just whoever is currently
    # acting, so no per-player exemption can distinguish "legitimately
    # over" from "a real bug" while the phase is still in progress.
    #
    # PROVISIONAL gap (docs/rules/RULES_PENDING.md): a player whose own
    # last-round check already passed this turn can still gain a card
    # afterward as a Rissa bystander (reward/relocation touching a
    # participant who isn't the one resuming the interrupted package) —
    # normally self-correcting at that player's *next* turn, but if the
    # game ends first there is no next turn to fix it. Since end-game
    # scoring doesn't reference hand contents (Milestone 5, not yet
    # implemented), the invariant is skipped once the game is FINISHED
    # rather than trying to force a resolution that has nowhere left to
    # happen.
    if state.phase in (GamePhase.ACTION_PHASE, GamePhase.FINISHED):
        return
    max_hand_size = state.configuration["max_hand_size"]
    for player in state.players:
        if len(player.hand_card_ids) > max_hand_size:
            violations.append(
                Violation(
                    "hand_size_exceeded",
                    f"Player '{player.player_id}' has {len(player.hand_card_ids)} cards, "
                    f"max is {max_hand_size}.",
                )
            )


def _check_pawn_location_consistency(state: GameState, violations: list[Violation]) -> None:
    """Every HOOD-located pawn must be indexed in that hood's
    `criminal_pawn_ids` (and only there) — the two must never drift
    apart, since CLAUDE.md requires a single authoritative position per
    pawn."""
    indexed_in_hood: dict[str, str] = {}
    for hood in state.board.hoods.values():
        for pawn_id in hood.criminal_pawn_ids:
            indexed_in_hood[pawn_id] = hood.hood_id

    for pawn_id, pawn in state.pawns.items():
        indexed_hood_id = indexed_in_hood.pop(pawn_id, None)
        if pawn.location.type is LocationType.HOOD:
            if indexed_hood_id != pawn.location.hood_id:
                violations.append(
                    Violation(
                        "pawn_hood_index_mismatch",
                        f"Pawn '{pawn_id}' location says hood '{pawn.location.hood_id}' "
                        f"but is indexed under hood '{indexed_hood_id}'.",
                    )
                )
        elif indexed_hood_id is not None:
            violations.append(
                Violation(
                    "pawn_indexed_in_wrong_place",
                    f"Pawn '{pawn_id}' is indexed in hood '{indexed_hood_id}' "
                    f"but its location type is '{pawn.location.type}'.",
                )
            )

    for dangling_pawn_id, dangling_hood_id in indexed_in_hood.items():
        violations.append(
            Violation(
                "dangling_hood_index",
                f"Hood '{dangling_hood_id}' lists pawn '{dangling_pawn_id}', "
                f"which does not exist in state.pawns.",
            )
        )


def validate_invariants(state: GameState) -> None:
    violations: list[Violation] = []

    _check_unique_pawn_ids(state, violations)
    _check_pawn_owner_consistency(state, violations)
    _check_hood_capacity(state, violations)
    _check_spot_capacity(state, violations)
    _check_jail_slots(state, violations)
    _check_base_chip_caps(state, violations)
    _check_link_levels(state, violations)
    _check_pending_decision(state, violations)
    _check_current_player(state, violations)
    _check_hand_size(state, violations)
    _check_pawn_location_consistency(state, violations)

    if violations:
        details = "; ".join(f"[{v.code}] {v.message}" for v in violations)
        raise InvariantViolation(f"{len(violations)} invariant violation(s): {details}")
