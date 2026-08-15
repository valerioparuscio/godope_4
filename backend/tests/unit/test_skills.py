"""Milestone 5 Stage 4 (Skill mechanical effects).

Stage 4a — "+1 Grinta sempre" bundle: Artisti-1 (buy/sell Dope),
Studenti-1 (move Criminal), Manager-1 (place Criminal), Politici-1
(corrupt/buy Officer).

Stage 4b — flat cost/price modifiers: Artisti-2 (buy Dope -1 / sell Dope
+1 per unit), Manager-2 (place Criminal costs $1 instead of $2),
Politici-2 (corrupt/buy Officer -$1).

Each Skill's own `effect` payload (data/skills.json) is read from
`state.configuration["skill_effect_by_id"]` identically by the option
generator (application/legal_actions.py) and the command validator/
mutator (rules/economy.py, rules/officers.py) — both sides are exercised
here, not just the pure `rules/skills.py` helpers.
"""

from dope_engine.application.command_bus import CommandBus, CommandFailure, CommandSuccess
from dope_engine.application.legal_actions import get_legal_decision
from dope_engine.domain.commands import (
    AssignBrawlGuns,
    BuyDope,
    BuyOfficer,
    ChooseActionType,
    ChooseBrawlLoserReward,
    EvolveSaleLink,
    LaunchPoker,
    PlaceCriminal,
    PlayBrawlCard,
    PlayMarketingCard,
    SellDope,
    SpendLinkForExtraAction,
)
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import ActionType, ActiveStep, DopeType, OfficerType, PawnRole
from dope_engine.domain.events import BrawlResolved
from dope_engine.domain.ids import ContactId, GameId, HoodId, OfficerId, SkillId
from dope_engine.rules import brawl, economy, links, officers, poker, skills, turn_flow
from dope_engine.rules.setup import create_initial_state

ARTISTI = ContactId("artisti")
BRAWL_HOOD = HoodId("hood_q2")


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


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
    officers.register_handlers(bus, price_tracks=price_tracks)
    return bus


def _enter_main_action(state, action_type, grit_value=1):
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = grit_value
    player.pending_action_type = action_type
    return player


# --- effective_action_count (pure) -----------------------------------------


def test_effective_action_count_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    count = skills.effective_action_count(state, player, ActionType.BUY_DOPE, 2)
    assert count == 2


def test_artisti_1_boosts_buy_and_sell_dope(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_1")]
    assert skills.effective_action_count(state, player, ActionType.BUY_DOPE, 2) == 3
    assert skills.effective_action_count(state, player, ActionType.SELL_DOPE, 1) == 2


def test_artisti_1_does_not_boost_unrelated_action_types(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_1")]
    assert skills.effective_action_count(state, player, ActionType.MOVE_CRIMINAL, 2) == 2
    assert skills.effective_action_count(state, player, ActionType.PLACE_CRIMINAL, 2) == 2


def test_studenti_1_boosts_move_criminal_only(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_studenti_1")]
    assert skills.effective_action_count(state, player, ActionType.MOVE_CRIMINAL, 1) == 2
    assert skills.effective_action_count(state, player, ActionType.BUY_DOPE, 1) == 1


def test_manager_1_boosts_place_criminal_only(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_manager_1")]
    assert skills.effective_action_count(state, player, ActionType.PLACE_CRIMINAL, 1) == 2
    assert skills.effective_action_count(state, player, ActionType.MOVE_CRIMINAL, 1) == 1


def test_politici_1_boosts_corrupt_and_buy_officer(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_politici_1")]
    assert skills.effective_action_count(state, player, ActionType.CORRUPT_OFFICER, 1) == 2
    assert skills.effective_action_count(state, player, ActionType.BUY_OFFICER, 1) == 2
    assert skills.effective_action_count(state, player, ActionType.SELL_DOPE, 1) == 1


def test_multiple_skills_boosting_the_same_action_type_stack(game_data) -> None:
    """Not explicitly ruled on, but the only reading consistent with each
    Skill being an independent permanent ability (§A10): two Skills that
    both boost the same action_type add up. Only one real Skill grants
    +1 Grit to buy_dope in the 15-skill set, so a synthetic second entry
    exercises the purely additive logic directly."""
    state, _ = _new_game(game_data)
    player = state.players[0]
    fake_skill_id = SkillId("skill_test_fake_extra_grit")
    state.configuration["skill_effect_by_id"][fake_skill_id] = {
        "type": "extra_grit",
        "action_types": ["buy_dope"],
        "amount": 1,
    }
    player.skill_ids = [SkillId("skill_artisti_1"), fake_skill_id]

    assert skills.effective_action_count(state, player, ActionType.BUY_DOPE, 1) == 3


# --- end-to-end: offer side + validation side agree -------------------


def test_manager_1_raises_the_max_target_count_end_to_end(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Confirmed by the game designer (2026-08-02): a package may use
    fewer than its (possibly Skill-boosted) max — Manager-1 raises the
    *ceiling* to 2, it doesn't force exactly 2."""
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.skill_ids = [SkillId("skill_manager_1")]
    player.money = 100

    decision = get_legal_decision(
        state, player.player_id, price_tracks, link_extra_action_types
    )
    assert decision is not None
    assert decision.decision_type == "place_criminal"
    assert decision.min_selections == 1
    assert decision.max_selections == 2  # base Grit 1 + Manager-1's +1

    hood_ids = tuple(o.payload["hood_id"] for o in decision.options[:2])
    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=hood_ids,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome


def test_manager_1_still_allows_using_fewer_than_the_boosted_max(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.skill_ids = [SkillId("skill_manager_1")]
    player.money = 100

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(HoodId("hood_q2"),),  # 1 of the 2 the Skill allows
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome


def test_place_criminal_rejects_more_than_the_boosted_max(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.skill_ids = [SkillId("skill_manager_1")]
    player.money = 100

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(HoodId("hood_q1"), HoodId("hood_q2"), HoodId("hood_q3")),  # 3 > max of 2
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_target_count"
    assert outcome.error.details["max"] == 2


def test_place_criminal_rejects_zero_targets(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.money = 100

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(),
        ),
    )

    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "wrong_target_count"
    assert outcome.error.details["min"] == 1


# --- Stage 4b: flat cost/price modifiers -------------------------------


def test_effective_cost_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    assert skills.effective_cost(state, player, ActionType.PLACE_CRIMINAL, 2) == 2


def test_manager_2_reduces_place_criminal_cost_by_one(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_manager_2")]
    assert skills.effective_cost(state, player, ActionType.PLACE_CRIMINAL, 2) == 1
    # Doesn't affect an unrelated action_type.
    assert skills.effective_cost(state, player, ActionType.BUY_OFFICER, 7) == 7


def test_politici_2_reduces_corrupt_and_buy_officer_cost_by_one(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_politici_2")]
    assert skills.effective_cost(state, player, ActionType.CORRUPT_OFFICER, 2) == 1
    assert skills.effective_cost(state, player, ActionType.BUY_OFFICER, 7) == 6


def test_effective_cost_never_goes_negative(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    state.configuration["skill_effect_by_id"][SkillId("skill_test_fake_cost")] = {
        "type": "cost_delta",
        "action_types": ["place_criminal"],
        "amount": -100,
    }
    player.skill_ids = [SkillId("skill_test_fake_cost")]
    assert skills.effective_cost(state, player, ActionType.PLACE_CRIMINAL, 2) == 0


def test_artisti_2_shifts_buy_and_sell_price(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_2")]
    assert skills.effective_trade_price(state, player, ActionType.BUY_DOPE, 5) == 4
    assert skills.effective_trade_price(state, player, ActionType.SELL_DOPE, 5) == 6


def test_effective_trade_price_never_goes_negative(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_2")]
    assert skills.effective_trade_price(state, player, ActionType.BUY_DOPE, 0) == 0


def test_manager_2_charges_the_discounted_cost_end_to_end(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.PLACE_CRIMINAL, grit_value=1)
    player.skill_ids = [SkillId("skill_manager_2")]
    starting_money = player.money

    outcome = bus.dispatch(
        state,
        PlaceCriminal(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            hood_ids=(HoodId("hood_q2"),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money == starting_money - 1  # $1, not the base $2


def test_politici_2_charges_the_discounted_cost_for_buy_officer_into_base(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.skill_ids = [SkillId("skill_politici_2")]
    player.money = 100
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = ActionType.BUY_OFFICER
    player.current_round_grit_value = 1

    hood_id = next(h.hood_id for h in state.board.hoods.values() if h.revealed)
    officer_id = OfficerId("officer_test_cop")
    from dope_engine.domain.entities import OfficerLocationType, OfficerState

    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.HOOD,
        hood_id=hood_id,
    )
    state.board.hoods[hood_id].cop_ids.append(officer_id)
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == "criminal")
    state.pawns[pawn_id].location = state.pawns[pawn_id].location.__class__.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)
    starting_money = player.money

    outcome = bus.dispatch(
        state,
        BuyOfficer(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            purchases=((pawn_id, officer_id, None),),
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player.player_id)
    assert new_player.money == starting_money - 6  # $6, not the base $7


# --- Stage 4c: single-off mechanics ------------------------------------


def _first_criminal_pawn_id(state, player):
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)


def _relocate_to_hood(state, pawn_id, hood_id):
    pawn = state.pawns[pawn_id]
    old_hood_id = pawn.location.hood_id
    state.board.hoods[old_hood_id].criminal_pawn_ids.remove(pawn_id)
    pawn.location = PawnLocation.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)


def _fresh_pawn(state, player_index):
    player = state.players[player_index]
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)


def _fresh_pawns(state, player_index, count):
    player = state.players[player_index]
    available = [pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE]
    return available[:count]


def _put_criminal(state, pawn_id, hood_id):
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.CRIMINAL
    pawn.location = PawnLocation.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)


def _brawl_bus(game_data, price_tracks, link_extra_action_types, gun_count_by_card_id=None):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    tile_by_id = {t.tile_id: t for t in game_data.board.covered_hood_tiles.tile_values}
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
    )
    brawl.register_handlers(
        bus,
        gun_count_by_card_id=gun_count_by_card_id or {},
        card_contact_by_id=card_contact_by_id,
        tile_by_id=tile_by_id,
    )
    return bus


def _declare_no_cards(bus, state, count):
    outcome = None
    for _ in range(count):
        current = state.current_player_id
        outcome = bus.dispatch(
            state,
            PlayBrawlCard(
                game_id=state.game_id,
                player_id=current,
                expected_revision=state.revision,
                card_id=None,
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state
    return state, outcome


def _poker_bus(game_data):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    banco_symbols_by_card_id = {c.card_id: c.banco_symbols for c in game_data.customer_cards}
    poker_symbols_by_card_id = {c.card_id: c.poker_symbols for c in game_data.customer_cards}
    poker.register_handlers(
        bus,
        banco_symbols_by_card_id=banco_symbols_by_card_id,
        poker_symbols_by_card_id=poker_symbols_by_card_id,
        card_contact_by_id=card_contact_by_id,
        action_type_by_card_id=action_type_by_card_id,
    )
    return bus


def _preti_card_id(game_data) -> str:
    return next(c.card_id for c in game_data.customer_cards if c.contact_id == "preti")


def _prepare_for_launch(game_data, state, player, card_id: str) -> None:
    action_type = next(c.action_type for c in game_data.customer_cards if c.card_id == card_id)
    player.pending_action_type = action_type
    player.poker_launch_return_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    state.active_step = ActiveStep.WAITING_FOR_POKER_LAUNCH
    state.current_player_id = player.player_id


def _extra_action_bus(game_data, price_tracks, link_extra_action_types):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    turn_flow.register_handlers(bus, card_contact_by_id=card_contact_by_id)
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
    )
    return bus


# --- Studenti-2: +1 Gun in Rissa ----------------------------------------


def test_extra_gun_bonus_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    assert skills.extra_gun_bonus(state, state.players[0]) == 0


def test_studenti_2_grants_a_bonus_gun(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_studenti_2")]
    assert skills.extra_gun_bonus(state, player) == 1


def test_studenti_2_adds_a_bonus_gun_to_force_end_to_end(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    artisti_cards = [c for c in game_data.customer_cards if c.contact_id == ARTISTI]
    card_a, card_b = artisti_cards[0].card_id, artisti_cards[1].card_id
    bus = _brawl_bus(
        game_data,
        price_tracks,
        link_extra_action_types,
        gun_count_by_card_id={card_a: 0, card_b: 0},
    )
    p0, p1 = state.players[0].player_id, state.players[1].player_id
    state.players[0].skill_ids = [SkillId("skill_studenti_2")]

    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 0), BRAWL_HOOD)
    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 1), BRAWL_HOOD)
    state.players[0].hand_card_ids.append(card_a)
    state.players[1].hand_card_ids.append(card_b)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[BRAWL_HOOD], p0, [], events)
    assert set(state.pending_brawl.participants) == {p0, p1}

    for _ in range(2):
        current = state.current_player_id
        card_id = card_a if current == p0 else card_b
        outcome = bus.dispatch(
            state,
            PlayBrawlCard(
                game_id=state.game_id,
                player_id=current,
                expected_revision=state.revision,
                card_id=card_id,
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state

    outcome = None
    for _ in range(2):
        current = state.current_player_id
        outcome = bus.dispatch(
            state,
            AssignBrawlGuns(
                game_id=state.game_id,
                player_id=current,
                expected_revision=state.revision,
                target_player_id=current,  # both self-target
            ),
        )
        assert isinstance(outcome, CommandSuccess), outcome
        state = outcome.state

    resolved = next(e for e in outcome.events if isinstance(e, BrawlResolved))
    assert resolved.force_by_player_id[p0] == 2 + 0 + 1  # 2 Criminals, 0 base Guns, +1 Studenti-2
    assert resolved.force_by_player_id[p1] == 2 + 0
    assert resolved.winner_id == p0
    assert resolved.loser_ids == (p1,)


def test_studenti_2_bonus_gun_applies_even_without_playing_a_card(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """Confirmed by the game designer (2026-08-02): every participant in
    the Hood always fights, so the bonus Gun is unconditional — not tied
    to whether the player played a card this Rissa (corrects the
    original card-linked implementation)."""
    state, _ = _new_game(game_data)
    bus = _brawl_bus(game_data, price_tracks, link_extra_action_types)
    p0, p1 = state.players[0].player_id, state.players[1].player_id
    state.players[0].skill_ids = [SkillId("skill_studenti_2")]

    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 0), BRAWL_HOOD)
    for _ in range(2):
        _put_criminal(state, _fresh_pawn(state, 1), BRAWL_HOOD)

    events: list = []
    brawl.start_brawl(state, state.board.hoods[BRAWL_HOOD], p0, [], events)
    assert set(state.pending_brawl.participants) == {p0, p1}

    state, outcome = _declare_no_cards(bus, state, 2)

    resolved = next(e for e in outcome.events if isinstance(e, BrawlResolved))
    assert resolved.force_by_player_id[p0] == 2 + 1  # 2 Criminals + Studenti-2, no card played
    assert resolved.force_by_player_id[p1] == 2
    assert resolved.winner_id == p0


# --- Preti-2: launch cashout override -----------------------------------


def test_poker_launch_cashout_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    assert skills.poker_launch_cashout(state, state.players[0], 3) == 3


def test_preti_2_overrides_the_cashout_amount(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_preti_2")]
    assert skills.poker_launch_cashout(state, player, 3) == 6


def test_preti_2_pays_six_dollars_end_to_end(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _poker_bus(game_data)
    player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == player_id)
    player.skill_ids = [SkillId("skill_preti_2")]
    card_id = _preti_card_id(game_data)
    player.hand_card_ids = [card_id]
    starting_money = player.money
    _prepare_for_launch(game_data, state, player, card_id)

    outcome = bus.dispatch(
        state,
        LaunchPoker(
            game_id=state.game_id,
            player_id=player_id,
            expected_revision=state.revision,
            card_id=card_id,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_player = next(p for p in outcome.state.players if p.player_id == player_id)
    assert new_player.money == starting_money + 6  # overridden, not the base cashout


# --- Preti-3: Gamble card usable with any action_type -------------------


def test_can_launch_poker_any_action_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    assert skills.can_launch_poker_any_action(state, state.players[0]) is False


def test_preti_3_enables_launching_regardless_of_action_type(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_preti_3")]
    assert skills.can_launch_poker_any_action(state, player) is True


def test_preti_3_bypasses_the_action_type_match_end_to_end(game_data) -> None:
    state, _ = _new_game(game_data)
    bus = _poker_bus(game_data)
    player_id = state.current_player_id
    player = next(p for p in state.players if p.player_id == player_id)
    card_id = _preti_card_id(game_data)
    player.hand_card_ids = [card_id]
    card_action_type = next(c.action_type for c in game_data.customer_cards if c.card_id == card_id)
    mismatched = next(at for at in ActionType if at != card_action_type)
    player.pending_action_type = mismatched
    player.poker_launch_return_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    state.active_step = ActiveStep.WAITING_FOR_POKER_LAUNCH
    state.current_player_id = player_id

    command = LaunchPoker(
        game_id=state.game_id,
        player_id=player_id,
        expected_revision=state.revision,
        card_id=card_id,
    )
    outcome = bus.dispatch(state, command)
    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "card_action_type_mismatch"

    player.skill_ids = [SkillId("skill_preti_3")]
    outcome = bus.dispatch(state, command)
    assert isinstance(outcome, CommandSuccess), outcome


# --- Politici-3: 2 Link extra actions per turn ---------------------------


def test_max_link_extra_actions_per_turn_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    assert skills.max_link_extra_actions_per_turn(state, state.players[0]) == 1


def test_politici_3_raises_the_limit_to_two(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_politici_3")]
    assert skills.max_link_extra_actions_per_turn(state, player) == 2


def test_politici_3_allows_a_second_link_extra_action_the_same_turn(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _extra_action_bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.skill_ids = [SkillId("skill_politici_3")]
    player.extra_actions_used_this_turn = 1  # already used the base 1
    link_pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    events: list = []
    links.insert_link(state, player.player_id, link_pawn_id, ContactId("manager"), 1, events)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    outcome = bus.dispatch(
        state,
        SpendLinkForExtraAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            pawn_id=link_pawn_id,
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome


def test_without_politici_3_a_second_link_extra_action_is_rejected(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _extra_action_bus(game_data, price_tracks, link_extra_action_types)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.extra_actions_used_this_turn = 1
    link_pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)

    events: list = []
    links.insert_link(state, player.player_id, link_pawn_id, ContactId("manager"), 1, events)
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION

    outcome = bus.dispatch(
        state,
        SpendLinkForExtraAction(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            pawn_id=link_pawn_id,
        ),
    )
    assert isinstance(outcome, CommandFailure)
    assert outcome.error.code == "extra_action_already_used"


# --- Artisti-3 / Studenti-3: Link evolves from a fresh Covo pawn --------


def test_sell_link_from_base_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    assert skills.sell_link_from_base(state, state.players[0]) is False


def test_artisti_3_enables_sell_link_from_base(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_artisti_3")]
    assert skills.sell_link_from_base(state, player) is True


def test_brawl_win_link_from_base_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    assert skills.brawl_win_link_from_base(state, state.players[0]) is False


def test_studenti_3_enables_brawl_win_link_from_base(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_studenti_3")]
    assert skills.brawl_win_link_from_base(state, player) is True


def test_artisti_3_evolves_a_fresh_covo_pawn_instead_of_the_seller(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _bus(game_data, price_tracks, link_extra_action_types)
    player = _enter_main_action(state, ActionType.SELL_DOPE, grit_value=1)
    player.skill_ids = [SkillId("skill_artisti_3")]
    pawn_id = _first_criminal_pawn_id(state, player)
    _relocate_to_hood(state, pawn_id, HoodId("hood_q1"))
    player.base_inventory.dope_counts[DopeType.POLPO] = 1
    fresh_pawn_id = next(
        pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )

    command = SellDope(
        game_id=state.game_id,
        player_id=player.player_id,
        expected_revision=state.revision,
        sales=((pawn_id, DopeType.POLPO),),
    )
    outcome = bus.dispatch(state, command)
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    # §A5 (corrected 2026-08-02): a single-unit sale's evolution is a
    # SI/NO choice now, not automatic.
    assert state.active_step == ActiveStep.WAITING_FOR_LINK_EVOLUTION_CHOICE

    outcome = bus.dispatch(
        state,
        EvolveSaleLink(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            evolve=True,
        ),
    )

    assert isinstance(outcome, CommandSuccess), outcome
    new_state = outcome.state
    seller = new_state.pawns[pawn_id]
    assert seller.role == PawnRole.CRIMINAL
    assert pawn_id in new_state.board.hoods[HoodId("hood_q1")].criminal_pawn_ids
    evolved = new_state.pawns[fresh_pawn_id]
    assert evolved.role == PawnRole.LINK
    assert evolved.contact_id == ARTISTI
    assert evolved.link_level == 1


def test_studenti_3_automatically_evolves_a_fresh_covo_pawn_on_brawl_win(
    game_data, price_tracks, link_extra_action_types
) -> None:
    state, _ = _new_game(game_data)
    bus = _brawl_bus(game_data, price_tracks, link_extra_action_types)
    p0 = state.players[0].player_id
    state.players[0].skill_ids = [SkillId("skill_studenti_3")]

    winner_pawn_1, winner_pawn_2 = _fresh_pawns(state, 0, 2)
    _put_criminal(state, winner_pawn_1, BRAWL_HOOD)
    _put_criminal(state, winner_pawn_2, BRAWL_HOOD)
    _put_criminal(state, _fresh_pawn(state, 1), BRAWL_HOOD)
    fresh_base_pawn_id = next(
        pid for pid in state.players[0].pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )

    events: list = []
    brawl.start_brawl(state, state.board.hoods[BRAWL_HOOD], p0, [], events)
    state, _ = _declare_no_cards(bus, state, 2)
    assert state.pending_brawl.winner_id == p0
    loser_id = state.pending_brawl.loser_ids[0]

    outcome = bus.dispatch(
        state,
        ChooseBrawlLoserReward(
            game_id=state.game_id,
            player_id=p0,
            expected_revision=state.revision,
            loser_player_id=loser_id,
            reward_type="money",
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state

    assert state.pending_brawl.link_evolution_done is True
    evolved = state.pawns[fresh_base_pawn_id]
    assert evolved.role == PawnRole.LINK
    assert evolved.contact_id == ARTISTI
    assert evolved.link_level == 1
    assert winner_pawn_1 in state.board.hoods[BRAWL_HOOD].criminal_pawn_ids
    assert winner_pawn_2 in state.board.hoods[BRAWL_HOOD].criminal_pawn_ids


# --- Manager-3: Stonk applies at both timings ---------------------------


def test_marketing_applies_both_timings_unaffected_without_the_skill(game_data) -> None:
    state, _ = _new_game(game_data)
    assert skills.marketing_applies_both_timings(state, state.players[0]) is False


def test_manager_3_enables_marketing_applies_both_timings(game_data) -> None:
    state, _ = _new_game(game_data)
    player = state.players[0]
    player.skill_ids = [SkillId("skill_manager_3")]
    assert skills.marketing_applies_both_timings(state, player) is True


def _marketing_bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id):
    bus = CommandBus()
    card_contact_by_id = {c.card_id: c.contact_id for c in game_data.customer_cards}
    action_type_by_card_id = {c.card_id: c.action_type for c in game_data.customer_cards}
    turn_flow.register_handlers(bus, card_contact_by_id=card_contact_by_id)
    economy.register_handlers(
        bus,
        price_tracks=price_tracks,
        card_contact_by_id=card_contact_by_id,
        link_extra_action_types=link_extra_action_types,
        action_type_by_card_id=action_type_by_card_id,
        stonk_count_by_card_id=stonk_count_by_card_id,
    )
    return bus


def test_manager_3_replays_a_before_marketing_allocation_after_the_package(
    game_data, price_tracks, link_extra_action_types
) -> None:
    """A Manager-3 owner who uses Marketing "before" the action gets
    those same allocations replayed automatically "after" the package
    (§A10, corrected 2026-08-02) — no new card, no new decision. A -1
    allocation used before therefore nets to a *lower* final price than
    a player without the Skill (who only gets the one "before" use):
    start 2 -> before -1 -> 1 -> package's own +1 -> 2 -> Manager-3
    replay -1 -> 1 (vs. 2 without the Skill, see test_marketing.py::
    test_buy_dope_does_not_offer_marketing_after_when_before_was_used)."""
    state, _ = _new_game(game_data)
    player = next(p for p in state.players if p.player_id == state.current_player_id)
    player.skill_ids = [SkillId("skill_manager_3")]
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.current_round_grit_value = 1
    player.pending_action_type = None
    card_id = game_data.customer_cards[0].card_id
    player.hand_card_ids.append(card_id)
    stonk_count_by_card_id = {card_id: 1}
    bus = _marketing_bus(game_data, price_tracks, link_extra_action_types, stonk_count_by_card_id)
    player.money = 100
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)
    hood = state.board.hoods[state.pawns[pawn_id].location.hood_id]
    dope_type = hood.dope_stack[-1]
    state.market.price_index_by_dope_type[dope_type] = 2

    outcome = bus.dispatch(
        state,
        ChooseActionType(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            action_type="buy_dope",
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.active_step == ActiveStep.WAITING_FOR_CARD_USAGE

    outcome = bus.dispatch(
        state,
        PlayMarketingCard(
            game_id=state.game_id,
            player_id=player.player_id,
            expected_revision=state.revision,
            card_id=card_id,
            allocations=((dope_type, -1),),
        ),
    )
    assert isinstance(outcome, CommandSuccess), outcome
    state = outcome.state
    assert state.market.price_index_by_dope_type[dope_type] == 1

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
    new_state = outcome.state
    assert new_state.active_step != ActiveStep.WAITING_FOR_CARD_USAGE
    assert new_state.market.price_index_by_dope_type[dope_type] == 1
    new_player = next(p for p in new_state.players if p.player_id == player.player_id)
    assert new_player.marketing_pre_allocations == ()
