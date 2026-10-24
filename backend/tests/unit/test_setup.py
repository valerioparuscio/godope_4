import pytest

from dope_engine.domain.enums import ControllerType, PawnRole
from dope_engine.domain.ids import GameId
from dope_engine.domain.invariants import validate_invariants
from dope_engine.rules.setup import create_initial_state


def test_create_initial_state_is_deterministic(game_data) -> None:
    state_a, events_a = create_initial_state(game_data, game_id=GameId("g"), seed=42, human_seat=0)
    state_b, events_b = create_initial_state(game_data, game_id=GameId("g"), seed=42, human_seat=0)

    assert state_a == state_b
    assert events_a == events_b


def test_different_seed_gives_different_state(game_data) -> None:
    state_a, _ = create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0)
    state_b, _ = create_initial_state(game_data, game_id=GameId("g"), seed=2, human_seat=0)

    assert state_a != state_b


def test_initial_state_satisfies_invariants(game_data) -> None:
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=42, human_seat=0)
    validate_invariants(state)  # must not raise


def test_setup_matches_documented_rules(game_data) -> None:
    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=42, human_seat=2)

    assert len(state.players) == 4
    for player in state.players:
        assert player.money == 15
        assert len(player.pawn_ids) == 10
        assert len(player.hand_card_ids) == 3
        assert sum(player.base_inventory.dope_counts.values()) == 2

    human_players = [p for p in state.players if p.controller_type is ControllerType.HUMAN]
    assert len(human_players) == 1
    assert human_players[0].seat_index == 2

    criminals = [p for p in state.pawns.values() if p.role is PawnRole.CRIMINAL]
    assert len(criminals) == 4 * 3  # 3 per player at setup

    revealed_hoods = [h for h in state.board.hoods.values() if h.revealed]
    covered_hoods = [h for h in state.board.hoods.values() if not h.revealed]
    assert len(revealed_hoods) == 5
    assert len(covered_hoods) == 5
    for hood in revealed_hoods:
        assert len(hood.dope_stack) == 3
    for hood in covered_hoods:
        assert hood.dope_stack == []
        assert hood.hood_id in state.board.covered_hood_tile_assignment

    assert state.first_player_id in state.player_order
    assert state.turn_index == 1
    assert len(state.raids.selected_card_ids) == 3
    assert len(set(state.raids.selected_card_ids)) == 3  # no duplicates

    # Dope conservation: bank + hoods + bases must equal total supply.
    for dope_type, definition in game_data.dope_types.items():
        in_hoods = sum(h.dope_stack.count(dope_type) for h in state.board.hoods.values())
        in_bases = sum(p.base_inventory.dope_counts.get(dope_type, 0) for p in state.players)
        bank = state.market.supply_remaining_by_dope_type[dope_type]
        assert bank + in_hoods + in_bases == definition.total_supply


def test_invalid_human_seat_raises(game_data) -> None:
    with pytest.raises(ValueError):
        create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=4)


# --- explicit seats (multiplayer) ----------------------------------------


def test_solo_shorthand_and_explicit_seats_build_the_same_game(game_data) -> None:
    from dope_engine.rules.setup import SeatConfig

    solo, solo_events = create_initial_state(
        game_data, game_id=GameId("g"), seed=7, human_seat=2, human_nickname="Marco"
    )
    explicit, explicit_events = create_initial_state(
        game_data,
        game_id=GameId("g"),
        seed=7,
        seats=[
            SeatConfig(ControllerType.BOT),
            SeatConfig(ControllerType.BOT),
            SeatConfig(ControllerType.HUMAN, "Marco"),
            SeatConfig(ControllerType.BOT),
        ],
    )

    assert solo == explicit
    assert solo_events == explicit_events


@pytest.mark.parametrize("humans", [1, 2, 3, 4])
def test_any_number_of_human_seats_is_supported(game_data, humans) -> None:
    from dope_engine.rules.setup import SeatConfig

    seats = [
        SeatConfig(ControllerType.HUMAN, f"Human {i}")
        if i < humans
        else SeatConfig(ControllerType.BOT, f"Bot {i + 1}")
        for i in range(4)
    ]

    state, _ = create_initial_state(game_data, game_id=GameId("g"), seed=3, seats=seats)

    validate_invariants(state)
    assert [p.controller_type for p in state.players] == [s.controller_type for s in seats]
    assert [p.display_name for p in state.players] == [s.name for s in seats]


def test_unnamed_seats_keep_the_default_player_names(game_data) -> None:
    from dope_engine.rules.setup import SeatConfig

    state, _ = create_initial_state(
        game_data,
        game_id=GameId("g"),
        seed=3,
        seats=[SeatConfig(ControllerType.HUMAN), *[SeatConfig(ControllerType.BOT)] * 3],
    )

    names = [p.display_name for p in state.players]
    assert names == ["Player 1", "Player 2", "Player 3", "Player 4"]


def test_the_seat_layout_does_not_change_the_dealt_game(game_data) -> None:
    """Who controls a seat is not a game mechanic: same seed, same cards, same everything else."""
    from dope_engine.rules.setup import SeatConfig

    all_bots, _ = create_initial_state(
        game_data, game_id=GameId("g"), seed=11, seats=[SeatConfig(ControllerType.BOT)] * 4
    )
    all_humans, _ = create_initial_state(
        game_data, game_id=GameId("g"), seed=11, seats=[SeatConfig(ControllerType.HUMAN)] * 4
    )

    for bot_player, human_player in zip(all_bots.players, all_humans.players, strict=True):
        assert bot_player.hand_card_ids == human_player.hand_card_ids
        assert bot_player.base_inventory == human_player.base_inventory
    assert all_bots.first_player_id == all_humans.first_player_id
    assert all_bots.decks == all_humans.decks


def test_wrong_number_of_seats_is_rejected(game_data) -> None:
    from dope_engine.rules.setup import SeatConfig

    with pytest.raises(ValueError, match="exactly 4 seats"):
        create_initial_state(
            game_data, game_id=GameId("g"), seed=1, seats=[SeatConfig(ControllerType.BOT)] * 3
        )


def test_seats_and_human_seat_cannot_be_mixed_and_one_is_required(game_data) -> None:
    from dope_engine.rules.setup import SeatConfig

    seats = [SeatConfig(ControllerType.BOT)] * 4
    with pytest.raises(ValueError, match="not both"):
        create_initial_state(game_data, game_id=GameId("g"), seed=1, human_seat=0, seats=seats)
    with pytest.raises(ValueError, match="either"):
        create_initial_state(game_data, game_id=GameId("g"), seed=1)
