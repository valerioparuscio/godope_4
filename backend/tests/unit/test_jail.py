from dope_engine.domain.enums import DopeType, PawnRole
from dope_engine.domain.ids import GameId
from dope_engine.rules import jail
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def test_arrest_pawn_fills_first_free_slot_and_becomes_rat(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    pawn_id = player.pawn_ids[0]
    events: list = []

    jail.arrest_pawn(state, pawn_id, events)

    pawn = state.pawns[pawn_id]
    assert pawn.role == PawnRole.RAT
    assert pawn.jail_slot == 0
    assert state.jail.slots[0].rat_pawn_id == pawn_id
    assert any(type(e).__name__ == "PawnArrested" for e in events)


def test_arrest_pawn_that_was_a_link_clears_link_fields(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    pawn_id = player.pawn_ids[0]
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.LINK
    from dope_engine.domain.ids import ContactId

    pawn.contact_id = ContactId("artisti")
    pawn.link_level = 2
    events: list = []

    jail.arrest_pawn(state, pawn_id, events)

    assert pawn.role == PawnRole.RAT
    assert pawn.contact_id is None
    assert pawn.link_level is None


def test_confiscate_dope_fills_first_free_confiscation_slot(game_data) -> None:
    state, _ = _new_game(game_data)
    events: list = []

    jail.confiscate_dope(state, DopeType.RANA, events)

    assert state.jail.slots[0].confiscated_dope_type == DopeType.RANA
    assert any(type(e).__name__ == "DopeConfiscated" for e in events)


def test_has_free_rat_slot_and_confiscation_slot_track_independently(game_data) -> None:
    state, _ = _new_game(game_data)
    assert jail.has_free_rat_slot(state)
    assert jail.has_free_confiscation_slot(state)

    events: list = []
    for _ in range(6):
        jail.confiscate_dope(state, DopeType.RANA, events)
    assert not jail.has_free_confiscation_slot(state)
    assert jail.has_free_rat_slot(state)


def test_sixth_rat_triggers_evasion_and_returns_other_five_to_base(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    pawn_ids = player.pawn_ids[:6]
    events: list = []

    for pawn_id in pawn_ids[:5]:
        jail.arrest_pawn(state, pawn_id, events)

    assert all(state.pawns[pid].role == PawnRole.RAT for pid in pawn_ids[:5])

    jail.arrest_pawn(state, pawn_ids[5], events)

    assert any(type(e).__name__ == "JailEscapeTriggered" for e in events)
    for pawn_id in pawn_ids[:5]:
        pawn = state.pawns[pawn_id]
        assert pawn.role == PawnRole.IN_BASE
        assert pawn.jail_slot is None

    trigger_pawn = state.pawns[pawn_ids[5]]
    assert trigger_pawn.role == PawnRole.LINK
    assert trigger_pawn.contact_id == "politici"
    assert trigger_pawn.link_level == 1

    for slot in state.jail.slots:
        assert slot.rat_pawn_id is None


def test_evasion_recovers_confiscated_dope_to_owner_base(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    pawn_ids = player.pawn_ids[:6]
    events: list = []
    starting_rana = player.base_inventory.dope_counts.get(DopeType.RANA, 0)

    for i, pawn_id in enumerate(pawn_ids):
        if i < 5:
            state.jail.slots[i].confiscated_dope_type = DopeType.RANA
        jail.arrest_pawn(state, pawn_id, events)

    assert player.base_inventory.dope_counts.get(DopeType.RANA, 0) >= starting_rana
    assert any(type(e).__name__ == "RatReturnedToBase" for e in events)
