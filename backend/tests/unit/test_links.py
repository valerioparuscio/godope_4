from dope_engine.domain.enums import PawnRole
from dope_engine.domain.ids import ContactId, GameId, PawnId
from dope_engine.rules import links
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def test_insert_link_at_level_one_sets_role_and_level(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    pawn_id = player.pawn_ids[0]
    contact_id = ContactId("artisti")
    events: list = []

    links.insert_link(state, player.player_id, pawn_id, contact_id, 1, events)

    pawn = state.pawns[pawn_id]
    assert pawn.role == PawnRole.LINK
    assert pawn.contact_id == contact_id
    assert pawn.link_level == 1
    assert any(type(e).__name__ == "PawnBecameLink" for e in events)


def test_insert_link_shifts_existing_occupants_right(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    contact_id = ContactId("artisti")
    pawn_a, pawn_b = player.pawn_ids[0], player.pawn_ids[1]
    events: list = []

    links.insert_link(state, player.player_id, pawn_a, contact_id, 1, events)
    links.insert_link(state, player.player_id, pawn_b, contact_id, 1, events)

    assert state.pawns[pawn_b].link_level == 1
    assert state.pawns[pawn_a].link_level == 2
    assert any(type(e).__name__ == "LinkLevelChanged" for e in events)


def test_insert_link_at_level_three_ejects_existing_level_three_occupant(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    contact_id = ContactId("artisti")
    pawn_a, pawn_b = player.pawn_ids[0], player.pawn_ids[1]
    events: list = []

    links.insert_link(state, player.player_id, pawn_a, contact_id, 3, events)
    links.insert_link(state, player.player_id, pawn_b, contact_id, 3, events)

    assert state.pawns[pawn_b].link_level == 3
    ejected = state.pawns[pawn_a]
    assert ejected.role == PawnRole.IN_BASE
    assert ejected.contact_id is None
    assert ejected.link_level is None
    assert any(type(e).__name__ == "LinkPawnReturnedToBase" for e in events)


def test_insert_link_at_level_two_does_not_touch_level_one(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    contact_id = ContactId("artisti")
    pawn_a, pawn_b = player.pawn_ids[0], player.pawn_ids[1]
    events: list = []

    links.insert_link(state, player.player_id, pawn_a, contact_id, 1, events)
    links.insert_link(state, player.player_id, pawn_b, contact_id, 2, events)

    assert state.pawns[pawn_a].link_level == 1
    assert state.pawns[pawn_b].link_level == 2


def test_contact_links_reports_occupied_levels(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    contact_id = ContactId("artisti")
    pawn_a = player.pawn_ids[0]
    events: list = []

    links.insert_link(state, player.player_id, pawn_a, contact_id, 2, events)

    occupied = links.contact_links(state, player.player_id, contact_id)
    assert occupied == {2: PawnId(pawn_a)}
