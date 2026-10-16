
from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.domain.commands import (
    BuyDope,
    ChooseActionType,
    MoveCriminal,
    PlaceCriminal,
    SellDope,
)
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, PawnRole
from dope_engine.domain.ids import (
    DEN_ID,
    JAIL_ID,
    ContactId,
    GameId,
    HoodId,
    OfficerId,
    SpotId,
)
from dope_engine.rules import customer_cards, economy, movement
from dope_engine.rules.setup import create_initial_state


def _bus(game_data, price_tracks, link_extra_action_types):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
    )
    return bus


def _bus_with_boosts(game_data, price_tracks, link_extra_action_types):
    """Like `_bus`, plus `customer_cards.register_handlers` — needed only
    by tests that dispatch `PlayCustomerCardBoost` itself (e.g. cards
    052/056's Grit-3/has-Dope eligibility gate); every other boost test
    in this file sets `player.active_card_boost` directly instead,
    bypassing that command entirely (established convention — the boost
    *application* command is tested end to end via
    `tests/integration/test_http_app.py`'s full random playthrough)."""
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    card_effect_by_id = {c.card_id: c.effect for c in game_data.customer_cards}
    customer_cards.register_handlers(
        bus,
        card_effect_by_id=card_effect_by_id,
        action_type_by_card_id=action_type_by_card_id,
        card_contact_by_id=card_contact_by_id,
    )
    return bus


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _enter_main_action(state, action_type, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    player.pending_action_type = action_type
    return player


def _first_criminal_pawn_id(state, player):
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)


def _relocate_to_hood(state, pawn_id, hood_id):
    pawn = state.pawns[pawn_id]
    old_hood_id = pawn.location.hood_id
    state.board.hoods[old_hood_id].criminal_pawn_ids.remove(pawn_id)
    pawn.location = PawnLocation.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)


# --- ChooseActionType: no repeat per turn (confirmed 2026-08-02) -------


def _enter_choose_action_type(state, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    return player


def test_choose_action_type_rejects_a_type_already_used_this_turn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_choose_action_type(state)
    player.action_types_used_this_turn = [ActionType.PLACE_CRIMINAL]

    outcome = bus.dispatch(
        state,
        ChooseActionType(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action_type="place_criminal",
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "action_type_already_used_this_turn"


def test_choose_action_type_records_the_type_as_used_this_turn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_choose_action_type(state)

    outcome = bus.dispatch(
        state,
        ChooseActionType(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action_type="place_criminal",
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.action_types_used_this_turn == [ActionType.PLACE_CRIMINAL]


# --- PlaceCriminal -----------------------------------------------------


def test_place_criminal_charges_cost_moves_pawn_and_draws_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    starting_money = player.money
    starting_hand_size = len(player.hand_card_ids)
    hood = state.board.hoods[HoodId("hood_q2")]
    hood.revealed = True
    starting_criminal_count = len(hood.criminal_pawn_ids)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    new_hood = outcome.state.board.hoods[HoodId("hood_q2")]
    assert new_player.money == starting_money - state.configuration["costs"]["place_criminal"]
    assert len(new_hood.criminal_pawn_ids) == starting_criminal_count + 1
    assert len(new_player.hand_card_ids) == starting_hand_size + 1
    assert new_player.pending_action_type is None


def test_bonus_card_draw_per_unit_cards_carry_count_1_not_2(game_data) -> None:
    """Data-level guard for the same bug the 2 command-level tests below
    prove at the code level: `effect.count` for every card using this
    effect type (029/031/046/050, all "1 extra draw on top of the always
    -on normal one" per the card text's own printed "2 carte TOTALI")
    must be 1, not 2 — the code side (`count` extra draws) was always
    correct; only the data was wrong."""
    checked = 0
    for card in game_data.customer_cards:
        if card.effect is not None and card.effect.get("type") == "bonus_card_draw_per_unit":
            assert card.effect["count"] == 1, (card.card_id, card.effect)
            checked += 1
    assert checked >= 1


def test_cards_046_050_draw_2_cards_total_not_3(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Cards 046/050 "MAKE FRIENDS" ("prendi 2 carte per ogni criminale
    piazzato" — confirmed by the user, 2026-09-02: 2 *total* per pawn
    placed, not 2 on top of the normal draw. `data/customer_cards.json`'s
    own `effect.count` used to be 2 — added to the 1 normal draw every
    placement already does, that gave 3 total instead of the card's own
    printed 2. `count` is now 1 (the *extra* draws beyond the always-on
    normal one)."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.active_card_boost = {
        "type": "bonus_card_draw_per_unit",
        "count": 1,
        "action_types": ["place_criminal"],
    }
    starting_hand_size = len(player.hand_card_ids)
    hood = state.board.hoods[HoodId("hood_q2")]
    hood.revealed = True

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert len(new_player.hand_card_ids) == starting_hand_size + 2


def test_card_041_doubles_place_criminal_targets_and_skips_the_draw(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Card 041 "REINFORCE" ("piazzi 2 per ogni Grinta, ma non peschi
    carte") — `place_double_no_draw` doubles the Grit-2 target count to 4
    via `skills.py::effective_action_count` (shared by both the option
    generator and this command's own `_validate_action_targets`), and
    `_handle_place_criminal` skips every one of those 4 placements' own
    normal card draw entirely."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=2)
    player.active_card_boost = {
        "type": "place_double_no_draw",
        "multiplier": 2,
        "action_types": ["place_criminal"],
    }
    starting_money = player.money
    starting_hand_size = len(player.hand_card_ids)
    hood_a, hood_b = state.board.hoods[HoodId("hood_q1")], state.board.hoods[HoodId("hood_q2")]
    hood_a.revealed = True
    hood_b.revealed = True

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(hood_a.hood_id, hood_a.hood_id, hood_b.hood_id, hood_b.hood_id),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    cost_each = state.configuration["costs"]["place_criminal"]
    assert new_player.money == starting_money - cost_each * 4
    assert len(new_player.hand_card_ids) == starting_hand_size
    new_hood_a = outcome.state.board.hoods[hood_a.hood_id]
    new_hood_b = outcome.state.board.hoods[hood_b.hood_id]
    assert len(new_hood_a.criminal_pawn_ids) == len(hood_a.criminal_pawn_ids) + 2
    assert len(new_hood_b.criminal_pawn_ids) == len(hood_b.criminal_pawn_ids) + 2


def test_without_card_041_grit_2_place_criminal_caps_at_two_targets(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=2)
    hood = state.board.hoods[HoodId("hood_q1")]
    hood.revealed = True

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(hood.hood_id, hood.hood_id, hood.hood_id),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_target_count"


def test_place_criminal_rejects_insufficient_funds(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.money = 0

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "insufficient_funds"


def test_place_criminal_rejects_hood_capacity_exceeded(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    hood = state.board.hoods[HoodId("hood_q2")]
    hood.revealed = True
    hood.criminal_pawn_ids = [f"filler_{i}" for i in range(hood.capacity)]

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "hood_capacity_exceeded"


def test_place_criminal_never_brings_hood_to_rissa_trigger_count(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Placing (unlike Moving) must never itself bring a Hood to its Rissa
    trigger count (docs/rules/RULE_CHANGELOG.md, 2026-07-31): a Hood one
    short of that count must still reject a further placement, even
    though raw capacity (5) is not yet reached."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    hood = state.board.hoods[HoodId("hood_q2")]
    hood.revealed = True
    trigger_count = state.configuration["brawl_trigger_criminal_count"]
    hood.criminal_pawn_ids = [f"filler_{i}" for i in range(trigger_count - 1)]
    assert len(hood.criminal_pawn_ids) < hood.capacity

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(HoodId("hood_q2"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "hood_capacity_exceeded"


def test_place_criminal_rejects_unrevealed_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Game designer (2026-08-16): an unrevealed Hood can only ever be
    reached via a Brawl loser's relocation, never a normal placement —
    it becomes placeable/movable only once that reveals it
    (rules/brawl.py sets hood.revealed = True)."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    unrevealed = next(h for h in state.board.hoods.values() if not h.revealed)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(unrevealed.hood_id,),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "hood_not_revealed"


def test_cards_043_045_can_place_a_criminal_straight_into_jail(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Cards 043/045 "RAT" ("un criminale puoi piazzarlo in prigione",
    game designer, 2026-08-31): `place_to_jail` sends a Covo pawn
    straight to a Jail slot as a Rat via the `JAIL_ID` sentinel (mirrors
    `DEN_ID`'s own always-a-valid-Hood-shaped-target pattern) — no Hood
    stop, still charged the normal placement cost."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.active_card_boost = {"type": "place_to_jail"}
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    starting_money = player.money

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(JAIL_ID,),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.pawns[pawn_id].role == PawnRole.RAT
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.money == starting_money - state.configuration["costs"]["place_criminal"]


def test_without_cards_043_045_placing_into_jail_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(JAIL_ID,),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "unknown_hood"


def test_cards_048_055_can_place_up_to_two_criminals_in_den(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Cards 048/055 "GO GAMBLE" ("puoi piazzare fino a due pedine nel
    Den", game designer, 2026-08-31): `PlaceCriminal` can normally never
    target the Den at all (only `MoveCriminal` can) — `place_in_den`
    reaches it directly from the Covo, same Gambler/draw effects as
    `MoveCriminal`'s own `DEN_ID` branch."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=2)
    player.active_card_boost = {"type": "place_in_den"}
    pawn_ids = [pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE][:2]

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID, DEN_ID),
        den_deck_contact_ids=(ContactId("artisti"), ContactId("artisti")),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    for pawn_id in pawn_ids:
        assert new_state.pawns[pawn_id].role == PawnRole.GAMBLER
        assert pawn_id in new_state.board.den_gambler_pawn_ids


def test_cards_048_055_den_placements_capped_at_two(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=3)
    player.active_card_boost = {"type": "place_in_den"}

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID, DEN_ID, DEN_ID),
        den_deck_contact_ids=(ContactId("artisti"),) * 3,
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "unknown_hood"


def test_without_cards_048_055_042_057_placing_into_den_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID,),
        den_deck_contact_ids=(ContactId("artisti"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "unknown_hood"


def test_place_criminal_into_den_missing_deck_choice_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.active_card_boost = {"type": "place_in_den"}

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID,),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "deck_choice_required"


def test_place_criminal_into_den_rejected_when_globally_full(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.active_card_boost = {"type": "place_in_den"}
    # Filled to global capacity (6) using other players' own pawns, 2 each
    # (den_capacity_per_player) so none of them individually trips the
    # per-player cap first — this must resolve to "den_full", not
    # "den_full_for_player".
    other_players = [p for p in state.players if p.player_id != player.player_id]
    for other in other_players:
        criminal_pawn_ids = [
            pid for pid in other.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
        ]
        for pawn_id in criminal_pawn_ids[:2]:
            pawn = state.pawns[pawn_id]
            state.board.hoods[pawn.location.hood_id].criminal_pawn_ids.remove(pawn_id)
            pawn.role = PawnRole.GAMBLER
            pawn.location = PawnLocation.den()
            state.board.den_gambler_pawn_ids.append(pawn_id)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID,),
        den_deck_contact_ids=(ContactId("artisti"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "den_full"


def test_place_criminal_into_den_rejected_at_per_player_cap(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.active_card_boost = {"type": "place_in_den"}
    criminal_pawn_ids = [
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
    ]
    for pawn_id in criminal_pawn_ids[:2]:
        pawn = state.pawns[pawn_id]
        state.board.hoods[pawn.location.hood_id].criminal_pawn_ids.remove(pawn_id)
        pawn.role = PawnRole.GAMBLER
        pawn.location = PawnLocation.den()
        state.board.den_gambler_pawn_ids.append(pawn_id)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID,),
        den_deck_contact_ids=(ContactId("artisti"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "den_full_for_player"


def test_cards_042_057_place_in_den_evicts_an_enemy_gambler(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Cards 042/057 "NO GAMBLE" ("piazza una pedina nel Den e rimuovi
    una pedina nemica", game designer, 2026-08-31): automatic/best-effort
    eviction of an opposing Gambler from the Den — no separate decision,
    same "secondary automatic effect" pattern as `self_arrest_after_action`
    / `arrest_extra_target` / `confiscate_extra_unit`."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.active_card_boost = {"type": "place_in_den_evict_enemy"}
    enemy = next(p for p in state.players if p.player_id != player.player_id)
    enemy_pawn_id = next(
        pid for pid in enemy.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
    )
    enemy_pawn = state.pawns[enemy_pawn_id]
    state.board.hoods[enemy_pawn.location.hood_id].criminal_pawn_ids.remove(enemy_pawn_id)
    enemy_pawn.role = PawnRole.GAMBLER
    enemy_pawn.location = PawnLocation.den()
    state.board.den_gambler_pawn_ids.append(enemy_pawn_id)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID,),
        den_deck_contact_ids=(ContactId("artisti"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert enemy_pawn_id not in new_state.board.den_gambler_pawn_ids
    assert new_state.pawns[enemy_pawn_id].role == PawnRole.IN_BASE


def test_cards_042_057_place_in_den_evict_is_noop_without_an_enemy_gambler(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    player.active_card_boost = {"type": "place_in_den_evict_enemy"}
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID,),
        den_deck_contact_ids=(ContactId("artisti"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.pawns[pawn_id].role == PawnRole.GAMBLER


def test_cards_042_057_den_placements_capped_at_one(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=2)
    player.active_card_boost = {"type": "place_in_den_evict_enemy"}

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(DEN_ID, DEN_ID),
        den_deck_contact_ids=(ContactId("artisti"), ContactId("artisti")),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "unknown_hood"


def test_without_card_044_051_place_criminal_stays_capped_by_grit(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    presence_hoods = list(
        {
            state.pawns[pid].location.hood_id
            for pid in player.pawn_ids
            if state.pawns[pid].role == PawnRole.CRIMINAL
        }
    )

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=tuple(presence_hoods[:2]),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_target_count"


def _enter_card_boost_step(state, card_id, action_type, grit_value):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.pending_action_type = action_type
    player.current_round_grit_value = grit_value
    player.card_boost_return_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    state.active_step = ActiveStep.WAITING_FOR_CARD_BOOST
    if card_id not in player.hand_card_ids:
        player.hand_card_ids.append(card_id)
    return player


def test_cards_053_058_shortcut_places_the_first_pawn_as_a_link(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Cards 053/058 "SHORTCUT" (game designer, 2026-08-31, confirmed:
    creates a *new* level-1 Link at the chosen Hood's own Contact) — "un
    criminale" (singular) means only the *first* target in the package
    takes the shortcut; the rest still place as normal Criminals."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=2)
    player.active_card_boost = {"type": "shortcut_place_as_link"}
    revealed_hoods = [hid for hid, h in state.board.hoods.items() if h.revealed]
    hood_a, hood_b = revealed_hoods[0], revealed_hoods[1]

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(hood_a, hood_b),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    first_pawn_id = next(
        pid
        for pid in player.pawn_ids
        if new_state.pawns[pid].role == PawnRole.LINK
        and new_state.pawns[pid].contact_id == new_state.board.hoods[hood_a].contact_id
    )
    first_pawn = new_state.pawns[first_pawn_id]
    assert first_pawn.link_level == 1
    assert first_pawn_id not in new_state.board.hoods[hood_a].criminal_pawn_ids
    second_criminals = new_state.board.hoods[hood_b].criminal_pawn_ids
    assert any(new_state.pawns[pid].owner_player_id == player.player_id for pid in second_criminals)


def test_without_cards_053_058_placement_never_creates_a_link(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL)
    revealed_hood = next(hid for hid, h in state.board.hoods.items() if h.revealed)

    command = PlaceCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        hood_ids=(revealed_hood,),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert not any(new_state.pawns[pid].role == PawnRole.LINK for pid in player.pawn_ids)


# --- MoveCriminal --------------------------------------------------------


def test_move_criminal_to_adjacent_hood_marks_moved_and_draws_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)
    from_hood_id = state.pawns[pawn_id].location.hood_id
    to_hood_id = state.board.hoods[from_hood_id].adjacent_hood_ids[0]

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, to_hood_id, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_state = outcome.state
    assert new_state.pawns[pawn_id].location.hood_id == to_hood_id
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert pawn_id in new_player.moved_pawn_ids_this_turn
    assert pawn_id not in new_state.board.hoods[from_hood_id].criminal_pawn_ids
    assert pawn_id in new_state.board.hoods[to_hood_id].criminal_pawn_ids


def test_cards_029_031_draw_2_cards_total_not_3(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Cards 029/031 "SWEET"/"MAKE FRIENDS" ("pesca due carte per ogni
    piazza in cui ti muovi" — confirmed by the user, 2026-09-02: 2
    *total* per Hood moved into, same off-by-one bug as 046/050 above —
    `count` is now 1 (extra beyond the always-on normal draw)."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    player.active_card_boost = {
        "type": "bonus_card_draw_per_unit",
        "count": 1,
        "action_types": ["move_criminal"],
    }
    starting_hand_size = len(player.hand_card_ids)
    pawn_id = _first_criminal_pawn_id(state, player)
    from_hood_id = state.pawns[pawn_id].location.hood_id
    to_hood_id = state.board.hoods[from_hood_id].adjacent_hood_ids[0]

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, to_hood_id, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert len(new_player.hand_card_ids) == starting_hand_size + 2


def test_move_criminal_rejects_non_adjacent_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)
    from_hood_id = state.pawns[pawn_id].location.hood_id
    non_adjacent = next(
        hid
        for hid in state.board.hoods
        if hid != from_hood_id and hid not in state.board.hoods[from_hood_id].adjacent_hood_ids
    )

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, non_adjacent, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "not_adjacent"


def test_card_033_can_move_a_criminal_from_any_hood_straight_into_jail(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Card 033 "MANEUVER" ("muovi un criminale da un quartiere qualunque
    in prigione", game designer, 2026-08-31): `move_to_jail` self-arrests
    via the `JAIL_ID` sentinel — no adjacency check (the whole point of
    "quartiere qualunque"), no card draw."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    player.active_card_boost = {"type": "move_to_jail"}
    pawn_id = _first_criminal_pawn_id(state, player)
    from_hood_id = state.pawns[pawn_id].location.hood_id
    starting_hand_size = len(player.hand_card_ids)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, JAIL_ID, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    assert new_state.pawns[pawn_id].role == PawnRole.RAT
    assert pawn_id not in new_state.board.hoods[from_hood_id].criminal_pawn_ids
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert pawn_id in new_player.moved_pawn_ids_this_turn
    assert len(new_player.hand_card_ids) == starting_hand_size


def test_without_card_033_moving_into_jail_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, JAIL_ID, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "unknown_hood"


def test_move_criminal_into_den_without_deck_choice_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, DEN_ID, None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "deck_choice_required"


def test_move_criminal_into_den_becomes_gambler(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)
    from_hood_id = state.pawns[pawn_id].location.hood_id

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, DEN_ID, ContactId("artisti")),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_state = outcome.state
    assert new_state.pawns[pawn_id].role == PawnRole.GAMBLER
    assert pawn_id in new_state.board.den_gambler_pawn_ids
    assert pawn_id not in new_state.board.hoods[from_hood_id].criminal_pawn_ids


def test_move_criminal_into_den_rejected_at_per_player_cap(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Decision (2026-08-15): a player can never have more than 2 of
    their own pawns in the Den at once, even though the Den's own global
    capacity (6) has room for more from other players."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    criminal_pawn_ids = [
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL
    ]
    first_id, second_id, third_id = criminal_pawn_ids[:3]
    for pawn_id in (first_id, second_id):
        pawn = state.pawns[pawn_id]
        state.board.hoods[pawn.location.hood_id].criminal_pawn_ids.remove(pawn_id)
        pawn.role = PawnRole.GAMBLER
        pawn.location = PawnLocation.den()
        state.board.den_gambler_pawn_ids.append(pawn_id)

    outcome = bus.dispatch(
        state,
        MoveCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            moves=((third_id, DEN_ID, ContactId("artisti")),),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "den_full_for_player"


def test_cards_032_036_double_den_draw_draws_from_two_chosen_decks(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Cards 032/036 "PLAY!!" ("se vai nel Den, peschi 2 carte a scelta",
    game designer, 2026-08-31, confirmed 2 independently-chosen decks):
    both `deck_contact_id` and `extra_den_deck_contact_ids` draws land in
    hand, from the 2 different Contacts asked for."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    player.active_card_boost = {"type": "double_den_draw", "action_types": ["move_criminal"]}
    pawn_id = _first_criminal_pawn_id(state, player)
    artisti_draw_pile_before = len(
        state.decks.customer_decks_by_contact[ContactId("artisti")].draw_pile_card_ids
    )
    studenti_draw_pile_before = len(
        state.decks.customer_decks_by_contact[ContactId("studenti")].draw_pile_card_ids
    )

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, DEN_ID, ContactId("artisti")),),
        extra_den_deck_contact_ids=(ContactId("studenti"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert len(new_player.hand_card_ids) == len(player.hand_card_ids) + 2
    assert (
        len(new_state.decks.customer_decks_by_contact[ContactId("artisti")].draw_pile_card_ids)
        == artisti_draw_pile_before - 1
    )
    assert (
        len(new_state.decks.customer_decks_by_contact[ContactId("studenti")].draw_pile_card_ids)
        == studenti_draw_pile_before - 1
    )


def test_cards_032_036_double_den_draw_requires_the_second_deck_choice(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    player.active_card_boost = {"type": "double_den_draw", "action_types": ["move_criminal"]}
    pawn_id = _first_criminal_pawn_id(state, player)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, DEN_ID, ContactId("artisti")),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "deck_choice_required"


def test_without_card_032_036_a_second_deck_choice_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    pawn_id = _first_criminal_pawn_id(state, player)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((pawn_id, DEN_ID, ContactId("artisti")),),
        extra_den_deck_contact_ids=(ContactId("studenti"),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "unexpected_deck_choice"


def test_move_one_pawn_rejects_a_second_deck_choice_off_the_den(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Defense in depth (CLAUDE.md §10) at the lower-level function
    itself: `rules/economy.py::_handle_move_criminal` only ever zips
    `extra_den_deck_contact_ids` onto a `DEN_ID` move in the first place,
    so this path isn't reachable through the public `MoveCriminal`
    command — call `movement.move_one_pawn` directly instead, the same
    way it's actually invoked from `process_move_queue`."""
    state, _ = _new_game(game_data)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    player.active_card_boost = {"type": "double_den_draw", "action_types": ["move_criminal"]}
    pawn_id = _first_criminal_pawn_id(state, player)
    to_hood_id = state.board.hoods[state.pawns[pawn_id].location.hood_id].adjacent_hood_ids[0]

    error = movement.move_one_pawn(
        state,
        player.player_id,
        player,
        pawn_id,
        to_hood_id,
        None,
        [],
        ContactId("studenti"),
    )

    assert error is not None
    assert error.code == "unexpected_deck_choice"


def _put_link(state, pawn_id, contact_id, level):
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.LINK
    pawn.contact_id = contact_id
    pawn.link_level = level
    pawn.location = PawnLocation.link(contact_id)


def test_without_cards_034_035_a_link_cannot_be_moved(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.MOVE_CRIMINAL)
    link_pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
    _put_link(state, link_pawn_id, ContactId("artisti"), 2)

    command = MoveCriminal(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        moves=((link_pawn_id, HoodId("hood_q3"), None),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "pawn_cannot_move"


# --- BuyDope --------------------------------------------------------------


def test_buy_dope_deducts_money_and_adds_to_base_inventory(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_count = player.base_inventory.dope_counts.get(dope_type, 0)
    starting_stock = len(hood.dope_stack)

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood.hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money < 100
    assert new_player.base_inventory.dope_counts.get(dope_type, 0) == starting_count + 1
    new_hood = outcome.state.board.hoods[hood.hood_id]
    assert len(new_hood.dope_stack) == starting_stock - 1


def test_buy_dope_rejects_purchase_that_would_exceed_base_cap(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """§11.4/RULES_PENDING.md #26 (resolved by the game designer,
    2026-08-23): the Covo's 3-per-type cap blocks the purchase outright
    instead of letting it happen and discarding the Dope afterward — a
    behavior change from the earlier DopeLostToOverflow event, which no
    longer fires from Buy Dope (still used by Jail Escape recovery,
    untouched)."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    starting_stock = len(hood.dope_stack)
    starting_money = player.money
    player.base_inventory.dope_counts[dope_type] = 3

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood.hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "base_inventory_full"
    # Rejected atomically — the original (unmutated) state is untouched.
    assert player.base_inventory.dope_counts[dope_type] == 3
    assert player.money == starting_money
    assert len(hood.dope_stack) == starting_stock


def test_card_017_lets_a_criminal_buy_at_an_adjacent_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Card 017 "EXPRESS" ("acquista in un quartiere adiacente") —
    `adjacent_hood_presence` extends `has_presence_at_hood` to a board-
    adjacent Hood, any Contact, on top of the Criminal's own Hood."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    player.active_card_boost = {"type": "adjacent_hood_presence"}
    pawn_id = _first_criminal_pawn_id(state, player)
    own_hood_id = state.pawns[pawn_id].location.hood_id
    adjacent_hood_id = state.board.hoods[own_hood_id].adjacent_hood_ids[0]
    adjacent_hood = state.board.hoods[adjacent_hood_id]
    dope_type = adjacent_hood.dope_stack[-1]
    starting_count = player.base_inventory.dope_counts.get(dope_type, 0)

    outcome = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, adjacent_hood_id),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.base_inventory.dope_counts.get(dope_type, 0) == starting_count + 1


def test_without_card_017_a_criminal_cannot_buy_at_an_adjacent_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    own_hood_id = state.pawns[pawn_id].location.hood_id
    adjacent_hood_id = state.board.hoods[own_hood_id].adjacent_hood_ids[0]

    outcome = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, adjacent_hood_id),),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "pawn_not_eligible"


def test_buy_dope_restocks_hood_and_spawns_cop_when_emptied(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    hood.dope_stack = [dope_type]
    state.market.supply_remaining_by_dope_type[dope_type] = 10

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood.hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_hood = outcome.state.board.hoods[hood.hood_id]
    assert len(new_hood.dope_stack) == 3
    assert len(new_hood.cop_ids) == 1
    assert "HoodRestocked" in [type(e).__name__ for e in outcome.events]
    assert "CopEnteredHood" in [type(e).__name__ for e in outcome.events]


def test_buy_dope_rejects_hood_blocked_by_cop(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    hood.cop_ids = [OfficerId("officer_test")]

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood.hood_id),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "hood_blocked_by_cop"


def test_buy_dope_rejects_duplicate_pawn(game_data, price_tracks, link_extra_action_types) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE, grit_value=2)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood_id = state.pawns[pawn_id].location.hood_id

    command = BuyDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        purchases=((pawn_id, hood_id), (pawn_id, hood_id)),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "duplicate_pawn_in_targets"


# --- SellDope -------------------------------------------------------------


def test_sell_dope_adds_money_and_removes_from_base_inventory(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    starting_money = player.money

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money > starting_money
    assert new_player.base_inventory.dope_counts[DopeType.POLPO] == 0
    spot = outcome.state.board.spots[SpotId("spot_artisti_2")]
    assert spot.sold_dope_tokens == [DopeType.POLPO]


def test_sell_dope_clears_spot_and_spawns_fed_when_full(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    spot = state.board.spots[SpotId("spot_artisti_2")]
    spot.sold_dope_tokens = [DopeType.POLPO, DopeType.POLPO]

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    new_spot = outcome.state.board.spots[SpotId("spot_artisti_2")]
    assert new_spot.sold_dope_tokens == []
    assert len(new_spot.fed_ids) == 1
    assert "SpotCleared" in [type(e).__name__ for e in outcome.events]
    assert "FedEnteredSpot" in [type(e).__name__ for e in outcome.events]


def test_sell_dope_succeeds_despite_cop_in_hood(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """A Cop in the Hood only blocks Buying there (§C3) — Selling is
    blocked exclusively by a Fed at the target Spot (§C4), never by a Cop
    in the Hood the seller is standing in."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    hood = state.board.hoods[HoodId("hood_q1")]
    hood.cop_ids = [OfficerId("officer_test")]

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess)
    spot = outcome.state.board.spots[SpotId("spot_artisti_2")]
    assert spot.sold_dope_tokens == [DopeType.POLPO]


def test_sell_dope_rejects_spot_blocked_by_fed(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    spot = state.board.spots[SpotId("spot_artisti_2")]
    spot.fed_ids = [OfficerId("officer_test")]

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "spot_blocked_by_fed"


def test_sell_dope_rejects_dope_type_not_accepted(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.RANA] = 1

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.RANA),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "dope_type_not_accepted"


def test_sell_dope_rejects_no_dope_to_sell(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 0

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "no_dope_to_sell"


def test_sell_dope_package_of_two_grants_link_at_level_two(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE, grit_value=2)
    pawn_ids = [pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL][:2]
    for pawn_id in pawn_ids:
        _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 2

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=tuple((pawn_id, DopeType.POLPO) for pawn_id in pawn_ids),
    )
    outcome = bus.dispatch(state, command)

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    evolved_pawn = new_state.pawns[pawn_ids[0]]
    assert evolved_pawn.role == PawnRole.LINK
    assert evolved_pawn.contact_id == ContactId("artisti")
    assert evolved_pawn.link_level == 2
    other_pawn = new_state.pawns[pawn_ids[1]]
    assert other_pawn.role == PawnRole.CRIMINAL
    assert "PawnBecameLink" in [type(e).__name__ for e in outcome.events]


def test_card_007_lets_one_pawn_buy_up_to_three_units(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Card 007 "HARD ACQUIRE" ("acquisti fino a 3 merci con un
    criminale") — `repeat_pawn_target` lifts the "each pawn buys at most
    once" limit up to `max_repeats`, still capped at `grit_value` total."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE, grit_value=3)
    player.money = 100
    player.active_card_boost = {"type": "repeat_pawn_target", "max_repeats": 3}
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    hood.dope_stack = [hood.dope_type] * 3
    dope_type = hood.dope_type
    starting_count = player.base_inventory.dope_counts.get(dope_type, 0)

    outcome = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, hood.hood_id), (pawn_id, hood.hood_id), (pawn_id, hood.hood_id)),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.base_inventory.dope_counts.get(dope_type, 0) == starting_count + 3


def test_without_card_007_the_same_pawn_cannot_buy_twice(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE, grit_value=3)
    player.money = 100
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    hood.dope_stack = [hood.dope_type] * 3

    outcome = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, hood.hood_id), (pawn_id, hood.hood_id)),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "duplicate_pawn_in_targets"


def test_card_015_lets_one_pawn_sell_three_units_for_a_level_three_link(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Card 015 "HARD VEND" ("vendi fino a 3 merci con un criminale") —
    `repeat_pawn_target` on the Sell side; the resulting package-sale
    Link must still land at level 3 (one per unit sold), not level 1
    (a bug this exposed in `_handle_sell_dope`'s own pawn-reordering,
    which used to drop every repeated occurrence of the chosen pawn)."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE, grit_value=3)
    player.active_card_boost = {"type": "repeat_pawn_target", "max_repeats": 3}
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 3

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((pawn_id, DopeType.POLPO), (pawn_id, DopeType.POLPO), (pawn_id, DopeType.POLPO)),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    evolved_pawn = outcome.state.pawns[pawn_id]
    assert evolved_pawn.role == PawnRole.LINK
    assert evolved_pawn.link_level == 3
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.base_inventory.dope_counts.get(DopeType.POLPO, 0) == 0


def test_card_012_lets_a_criminal_sell_at_an_adjacent_hoods_contact(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Card 012 "DELIVERY" ("vendi in un quartiere adiacente") —
    `adjacent_hood_presence` extends selling reach to an adjacent Hood's
    Contact, using the explicit `explicit_spots` triple
    (RULES_PENDING.md #26) since the pawn's own Hood/Contact alone no
    longer determines the Spot."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    player.active_card_boost = {"type": "adjacent_hood_presence"}
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    own_hood = state.board.hoods[HoodId("hood_q1")]
    adjacent_contact_id = next(
        state.board.hoods[hid].contact_id
        for hid in own_hood.adjacent_hood_ids
        if state.board.hoods[hid].contact_id != own_hood.contact_id
    )
    target_spot = next(s for s in state.board.spots.values() if s.contact_id == adjacent_contact_id)
    player.base_inventory.dope_counts[target_spot.accepted_dope_type] = 1
    starting_money = player.money

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((pawn_id, target_spot.accepted_dope_type),),
            explicit_spots=((pawn_id, target_spot.accepted_dope_type, target_spot.spot_id),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money > starting_money
    assert new_player.base_inventory.dope_counts.get(target_spot.accepted_dope_type, 0) == 0
    new_spot = outcome.state.board.spots[target_spot.spot_id]
    assert new_spot.sold_dope_tokens == [target_spot.accepted_dope_type]


def test_without_card_012_a_criminal_cannot_sell_at_an_adjacent_hoods_contact(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    own_hood = state.board.hoods[HoodId("hood_q1")]
    adjacent_contact_id = next(
        state.board.hoods[hid].contact_id
        for hid in own_hood.adjacent_hood_ids
        if state.board.hoods[hid].contact_id != own_hood.contact_id
    )
    target_spot = next(s for s in state.board.spots.values() if s.contact_id == adjacent_contact_id)
    player.base_inventory.dope_counts[target_spot.accepted_dope_type] = 1

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((pawn_id, target_spot.accepted_dope_type),),
            explicit_spots=((pawn_id, target_spot.accepted_dope_type, target_spot.spot_id),),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "pawn_not_eligible"


def test_card_012_explicit_spot_disambiguates_two_contacts_accepting_the_same_type(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """The scenario `explicit_spots` exists for: the pawn's own Contact
    and an adjacent Hood's Contact both happen to accept the same Dope
    type here (forced for the test), so `dope_type` alone can no longer
    tell which Spot was meant — the command must route to the Spot named
    explicitly, not whichever `_find_spot` would pick by scanning."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    player.active_card_boost = {"type": "adjacent_hood_presence"}
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    own_hood = state.board.hoods[HoodId("hood_q1")]
    own_contact_id = own_hood.contact_id
    adjacent_contact_id = next(
        state.board.hoods[hid].contact_id
        for hid in own_hood.adjacent_hood_ids
        if state.board.hoods[hid].contact_id != own_contact_id
    )
    own_spot = next(s for s in state.board.spots.values() if s.contact_id == own_contact_id)
    adjacent_spot = next(
        s for s in state.board.spots.values() if s.contact_id == adjacent_contact_id
    )
    # Force both Spots to accept the same Dope type, so `dope_type` alone
    # is genuinely ambiguous between them.
    adjacent_spot.accepted_dope_type = own_spot.accepted_dope_type
    player.base_inventory.dope_counts[own_spot.accepted_dope_type] = 1

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((pawn_id, own_spot.accepted_dope_type),),
            explicit_spots=((pawn_id, own_spot.accepted_dope_type, adjacent_spot.spot_id),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    assert outcome.state.board.spots[adjacent_spot.spot_id].sold_dope_tokens == [
        own_spot.accepted_dope_type
    ]
    assert outcome.state.board.spots[own_spot.spot_id].sold_dope_tokens == []


def test_ignore_officer_block_lets_a_package_buy_in_a_hood_with_a_cop(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Card 03 "DIRTY BADGE" (game designer, 2026-10-15): the Cop block is ignored."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.BUY_DOPE)
    player.money = 100
    player.active_card_boost = {"type": "ignore_officer_block", "action_types": ["buy_dope"]}
    pawn_id = _first_criminal_pawn_id(state, player)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    hood.cop_ids = [OfficerId("officer_test")]
    hood.dope_stack = [DopeType.RANA]
    rana_before = player.base_inventory.dope_counts.get(DopeType.RANA, 0)

    outcome = bus.dispatch(
        state,
        BuyDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, hood.hood_id),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    bought_by = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert bought_by.base_inventory.dope_counts[DopeType.RANA] == rana_before + 1


def test_ignore_officer_block_lets_a_package_sell_at_a_spot_with_a_fed(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Card 10 "DIRTY DEAL" (game designer, 2026-10-15): the Fed block is ignored."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE)
    player.active_card_boost = {"type": "ignore_officer_block", "action_types": ["sell_dope"]}
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    spot = state.board.spots[SpotId("spot_artisti_2")]
    spot.fed_ids = [OfficerId("officer_test")]

    outcome = bus.dispatch(
        state,
        SellDope(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            sales=((pawn_id, DopeType.POLPO),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
