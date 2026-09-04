import copy

import pytest

from dope_engine.domain.errors import InvariantViolation
from dope_engine.domain.ids import GameId
from dope_engine.domain.invariants import validate_invariants
from dope_engine.rules.setup import create_initial_state


@pytest.fixture()
def state(game_data):
    s, _events = create_initial_state(game_data, game_id=GameId("g"), seed=42, human_seat=0)
    return s


def test_fresh_state_has_no_violations(state) -> None:
    validate_invariants(state)  # must not raise


def test_hood_capacity_violation_is_detected(state) -> None:
    broken = copy.deepcopy(state)
    hood = next(iter(broken.board.hoods.values()))
    hood.criminal_pawn_ids = list(broken.pawns.keys())[:6]  # more than capacity=5

    with pytest.raises(InvariantViolation, match="hood_capacity_exceeded"):
        validate_invariants(broken)


def test_duplicate_pawn_id_is_detected(state) -> None:
    broken = copy.deepcopy(state)
    duplicated = broken.players[0].pawn_ids[0]
    broken.players[1].pawn_ids.append(duplicated)

    with pytest.raises(InvariantViolation, match="duplicate_pawn_id"):
        validate_invariants(broken)


def test_base_dope_overflow_is_detected(state) -> None:
    broken = copy.deepcopy(state)
    from dope_engine.domain.enums import DopeType

    broken.players[0].base_inventory.dope_counts[DopeType.RANA] = 4

    with pytest.raises(InvariantViolation, match="base_dope_overflow"):
        validate_invariants(broken)


def test_base_poker_chip_overflow_is_detected(state) -> None:
    broken = copy.deepcopy(state)
    broken.players[0].base_inventory.poker_chip_count = 4

    with pytest.raises(InvariantViolation, match="base_poker_chip_overflow"):
        validate_invariants(broken)


def test_current_player_not_in_order_is_detected(state) -> None:
    from dope_engine.domain.ids import PlayerId

    broken = copy.deepcopy(state)
    broken.current_player_id = PlayerId("player_999")

    with pytest.raises(InvariantViolation, match="current_player_not_in_order"):
        validate_invariants(broken)


def test_hand_size_overflow_is_never_flagged(state) -> None:
    """Confirmed by the game designer (2026-08-02): the 5-card limit is
    checked only at the end of a player's own turn — a bystander who
    picks up a card from another player's Rissa/Job simply holds onto
    the overflow until their own next such check, even across phases.
    There is no reliable state-sampling point where "everyone must be
    <=5" holds, so this is never flagged as a structural violation."""
    from dope_engine.domain.enums import GamePhase

    broken = copy.deepcopy(state)
    broken.phase = GamePhase.SHOWDOWN_PHASE
    broken.players[0].hand_card_ids = ["c1", "c2", "c3", "c4", "c5", "c6"]

    validate_invariants(broken)  # must not raise


def test_pawn_hood_index_mismatch_is_detected(state) -> None:
    broken = copy.deepcopy(state)
    hood = next(h for h in broken.board.hoods.values() if h.criminal_pawn_ids)
    pawn_id = hood.criminal_pawn_ids[0]
    # Pawn still says it's in this hood, but the index no longer agrees.
    hood.criminal_pawn_ids.remove(pawn_id)

    with pytest.raises(InvariantViolation, match="pawn_hood_index_mismatch"):
        validate_invariants(broken)
