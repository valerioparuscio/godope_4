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


def test_insert_link_does_not_eject_a_level_three_occupant_across_a_gap(game_data) -> None:
    """Bug (game designer, 2026-08-17): with only level 1 and level 3
    occupied (level 2 free), inserting a new Link at level 1 must shift
    the level-1 occupant up to the now-adjacent level 2, but must *not*
    touch the level-3 occupant at all — nothing is pushing into level 3
    since level 2 was empty."""
    state, _ = _new_game(game_data)
    player = state.players[0]
    contact_id = ContactId("artisti")
    pawn_a, pawn_b, pawn_c = player.pawn_ids[0], player.pawn_ids[1], player.pawn_ids[2]
    events: list = []

    links.insert_link(state, player.player_id, pawn_a, contact_id, 1, events)
    links.insert_link(state, player.player_id, pawn_c, contact_id, 3, events)
    events.clear()

    links.insert_link(state, player.player_id, pawn_b, contact_id, 1, events)

    assert state.pawns[pawn_b].link_level == 1
    assert state.pawns[pawn_a].link_level == 2
    assert state.pawns[pawn_c].role == PawnRole.LINK
    assert state.pawns[pawn_c].link_level == 3
    assert not any(type(e).__name__ == "LinkPawnReturnedToBase" for e in events)


def test_contact_links_reports_occupied_levels(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    contact_id = ContactId("artisti")
    pawn_a = player.pawn_ids[0]
    events: list = []

    links.insert_link(state, player.player_id, pawn_a, contact_id, 2, events)

    occupied = links.contact_links(state, contact_id)
    assert occupied == {2: PawnId(pawn_a)}


def test_link_slots_are_shared_across_players_not_per_player(game_data) -> None:
    """§A5 (corrected 2026-08-01): the 3 Link slots per Contact are a
    single shared track across the whole game, not one independent track
    per player — confirmed by the game designer after
    rules/officers.py::_lowest_level_link_at_contact turned out to already
    assume global level uniqueness (no owner filter, no tie-break)."""
    state, _ = _new_game(game_data)
    player_a, player_b = state.players[0], state.players[1]
    contact_id = ContactId("artisti")
    pawn_a = player_a.pawn_ids[0]
    pawn_b = player_b.pawn_ids[0]
    events: list = []

    links.insert_link(state, player_a.player_id, pawn_a, contact_id, 1, events)
    # player_b inserting at the same level 1 must shift player_a's own
    # pawn up to level 2, exactly as if it were player_b's own occupant.
    links.insert_link(state, player_b.player_id, pawn_b, contact_id, 1, events)

    assert state.pawns[pawn_b].link_level == 1
    assert state.pawns[pawn_b].owner_player_id == player_b.player_id
    assert state.pawns[pawn_a].link_level == 2
    assert state.pawns[pawn_a].owner_player_id == player_a.player_id
    level_changed = next(e for e in events if type(e).__name__ == "LinkLevelChanged")
    assert level_changed.player_id == player_a.player_id  # the occupant's own owner


def test_insert_link_ejects_a_different_players_level_three_occupant_to_their_own_base(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    player_a, player_b = state.players[0], state.players[1]
    contact_id = ContactId("artisti")
    pawn_a = player_a.pawn_ids[0]
    pawn_b = player_b.pawn_ids[0]
    events: list = []

    links.insert_link(state, player_a.player_id, pawn_a, contact_id, 3, events)
    links.insert_link(state, player_b.player_id, pawn_b, contact_id, 3, events)

    assert state.pawns[pawn_b].link_level == 3
    ejected = state.pawns[pawn_a]
    assert ejected.role == PawnRole.IN_BASE
    assert ejected.owner_player_id == player_a.player_id
    returned = next(e for e in events if type(e).__name__ == "LinkPawnReturnedToBase")
    assert returned.player_id == player_a.player_id  # returned to its own owner, not player_b
