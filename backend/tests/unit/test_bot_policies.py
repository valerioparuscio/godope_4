""" "Basi per bot più intelligenti" (2026-08-25): the shared, key-driven
option pickers (`bots/option_picking.py`) and the simple heuristics they
can be ordered by (`bots/scoring.py`). `hood_q1`/`hood_q2` are both
Contact "artisti" (`hood_q1` revealed at game start, `hood_q2` starts
empty/unrevealed) — same fixture pair `test_brawl.py` uses, for the same
reason: pre-placing exactly the Criminals a scenario needs gives an
exact, predictable count."""

import random

from dope_engine.application.views import build_player_view
from dope_engine.bots.option_picking import pick_buy_dope_options, pick_place_criminal_options
from dope_engine.bots.policies import HeuristicBot
from dope_engine.bots.scoring import (
    DEFAULT_WEIGHTS,
    score_action_type,
    score_option,
    score_play_poker_card_option,
    score_spend_link_for_extra_action_option,
)
from dope_engine.domain.commands import (
    AssignBrawlGuns,
    ChooseActionType,
    ChooseBrawlLinkEvolution,
    ChooseMarketingCard,
    EvolveSaleLink,
    PassOptionalStep,
    PlayBrawlCard,
    PlayPokerCard,
    SellDope,
    SpendLinkForExtraAction,
)
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.entities import PawnLocation
from dope_engine.domain.enums import DopeType, PawnRole, PokerSymbolColor
from dope_engine.domain.ids import DEN_ID, ContactId, GameId, HoodId, JobId, RaidCardId
from dope_engine.domain.state import PokerMatchState
from dope_engine.rules.setup import create_initial_state

ARTISTI = ContactId("artisti")
HOOD_1 = HoodId("hood_q1")
HOOD_2 = HoodId("hood_q2")


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _price_tracks(game_data):
    return {dope_type: d.price_track for dope_type, d in game_data.dope_types.items()}


def _fresh_pawn(state, player_index):
    player = state.players[player_index]
    return next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)


def _put_criminal(state, pawn_id, hood_id):
    pawn = state.pawns[pawn_id]
    pawn.role = PawnRole.CRIMINAL
    pawn.location = PawnLocation.hood(hood_id)
    state.board.hoods[hood_id].criminal_pawn_ids.append(pawn_id)


def _decision(player_id, decision_type, options, max_selections=1) -> PendingDecision:
    return PendingDecision(
        decision_id="decision_test",
        player_id=player_id,
        decision_type=decision_type,
        prompt_key="decision.test.prompt",
        options=tuple(options),
        min_selections=1,
        max_selections=max_selections,
    )


def test_key_reorders_buy_dope_pick_while_respecting_budget(game_data) -> None:
    state, _ = _new_game(game_data)
    state.board.hoods[HOOD_1].dope_stack = [DopeType.RANA, DopeType.RANA, DopeType.RANA]
    view = build_player_view(state, state.player_order[0], _price_tracks(game_data))

    options = [
        DecisionOption(
            option_id=f"buy_{i}",
            label_key="decision.buy_dope.option",
            payload={
                "pawn_id": f"fake_pawn_{i}",
                "hood_id": HOOD_1,
                "dope_type": "rana",
                "price": price,
            },
        )
        for i, price in enumerate([5, 1, 9])
    ]
    decision = _decision(state.player_order[0], "buy_dope", options)

    cheapest_first = pick_buy_dope_options(decision, 1, random.Random(1), view)
    priciest_first = pick_buy_dope_options(
        decision, 1, random.Random(1), view, key=lambda o: -o.payload["price"]
    )

    assert cheapest_first == ("buy_1",)  # price=1
    assert priciest_first == ("buy_2",)  # price=9


def test_score_option_sell_dope_prefers_higher_price(game_data) -> None:
    state, _ = _new_game(game_data)
    view = build_player_view(state, state.player_order[0], _price_tracks(game_data))
    prices = view.current_price_by_dope_type
    dope_high = max(prices, key=lambda dt: prices[dt])
    dope_low = min(prices, key=lambda dt: prices[dt])
    assert prices[dope_high] > prices[dope_low]

    spot_id = view.spots[0].spot_id

    def option(dope_type):
        return DecisionOption(
            option_id="sell",
            label_key="decision.sell_dope.option",
            payload={"pawn_id": "fake_pawn", "spot_id": spot_id, "dope_type": dope_type.value},
        )

    decision_high = _decision(state.player_order[0], "sell_dope", [option(dope_high)])
    decision_low = _decision(state.player_order[0], "sell_dope", [option(dope_low)])

    score_high = score_option(decision_high.options[0], decision_high, view)
    score_low = score_option(decision_low.options[0], decision_low, view)
    assert score_high > score_low


def test_score_option_move_criminal_penalizes_triggering_a_rissa(game_data) -> None:
    state, _ = _new_game(game_data)
    mover_id = state.player_order[0]
    # hood_q2 starts empty/unrevealed — reveal it and pre-place 4 other
    # players' Criminals so this player's own move into it would be the
    # 5th (RULES_CANONICAL.md §D1's trigger count, capacity=5).
    state.board.hoods[HOOD_2].revealed = True
    for i, player_id in enumerate(state.player_order):
        if player_id == mover_id:
            continue
        pawn_id = next(
            pid for pid in state.players[i].pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
        )
        _put_criminal(state, pawn_id, HOOD_2)
    # A 4th criminal is needed to reach capacity-1 (3 opponents were
    # placed above); who owns it doesn't matter — the Rissa-trigger check
    # only counts total criminals in the Hood, not per-owner — so reusing
    # one of the mover's own spare pawns is fine.
    extra_pawn_id = _fresh_pawn(state, 0)
    _put_criminal(state, extra_pawn_id, HOOD_2)
    assert len(state.board.hoods[HOOD_2].criminal_pawn_ids) == 4

    view = build_player_view(state, mover_id, _price_tracks(game_data))

    def move_option(destination):
        return DecisionOption(
            option_id="move",
            label_key="decision.move_criminal.option",
            payload={
                "pawn_id": "fake_pawn",
                "destination_hood_id": destination,
                "deck_contact_id": None,
            },
        )

    crowded = _decision(mover_id, "move_criminal", [move_option(HOOD_2)])
    safe = _decision(mover_id, "move_criminal", [move_option(HOOD_1)])

    score_crowded = score_option(crowded.options[0], crowded, view)
    score_safe = score_option(safe.options[0], safe, view)
    assert score_crowded < score_safe


def test_score_option_majority_bonus(game_data) -> None:
    state, _ = _new_game(game_data)
    seat0 = state.player_order[0]

    # seat0 gets strict majority at ARTISTI (hood_q1/hood_q2): 2 Criminals
    # vs seat1's 1. hood_q2 needs revealing first (starts unrevealed).
    state.board.hoods[HOOD_2].revealed = True
    p0_pawn_a = _fresh_pawn(state, 0)
    _put_criminal(state, p0_pawn_a, HOOD_1)
    p0_pawn_b = next(
        pid for pid in state.players[0].pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
    )
    _put_criminal(state, p0_pawn_b, HOOD_2)
    p1_pawn = _fresh_pawn(state, 1)
    _put_criminal(state, p1_pawn, HOOD_1)

    view = build_player_view(state, seat0, _price_tracks(game_data))

    # A Contact seat0 has no presence at all, for the control comparison.
    other_contact_hood = next(h for h in view.hoods if h.contact_id != ARTISTI and h.revealed)

    majority_option = DecisionOption(
        option_id="place_majority",
        label_key="decision.place_criminal.option",
        payload={"hood_id": HOOD_1},
    )
    no_presence_option = DecisionOption(
        option_id="place_none",
        label_key="decision.place_criminal.option",
        payload={"hood_id": other_contact_hood.hood_id},
    )

    decision_majority = _decision(seat0, "place_criminal", [majority_option])
    decision_none = _decision(seat0, "place_criminal", [no_presence_option])

    score_majority = score_option(majority_option, decision_majority, view)
    score_none = score_option(no_presence_option, decision_none, view)
    assert score_majority > score_none


def test_pick_place_criminal_options_dedups_den_by_slot_index() -> None:
    """Cards 048/055/042/057: `_place_criminal_options` offers one
    `place_criminal` option per (Den slot, deck-choice) pair so the
    player can pick which Contact deck to draw from — several *different*
    options can represent the *same* real Den slot. A plain random sample
    across the raw option list (as bots used before this picker existed)
    could select 2 deck-choice variants of the same slot, requesting more
    real Den placements than actually fit (`tools/run_full_test_game.py`
    bot sweep, 2026-08-31: 'den_full'/'unknown_hood' failures). Only 1
    real Den slot is offered here (2 deck-choice variants of the same
    `den_slot_index=0`) alongside 2 real, independent Hood options — a
    correct pick of 2 must take exactly one Den variant plus one Hood
    option, never both Den variants."""
    den_a = DecisionOption(
        option_id="place_den_0_artisti",
        label_key="decision.place_criminal.option",
        payload={"hood_id": DEN_ID, "deck_contact_id": "artisti", "den_slot_index": 0},
    )
    den_b = DecisionOption(
        option_id="place_den_0_studenti",
        label_key="decision.place_criminal.option",
        payload={"hood_id": DEN_ID, "deck_contact_id": "studenti", "den_slot_index": 0},
    )
    hood_option = DecisionOption(
        option_id="place_hood_q1_0",
        label_key="decision.place_criminal.option",
        payload={"hood_id": HOOD_1},
    )
    decision = _decision(
        "player_0", "place_criminal", [den_a, den_b, hood_option], max_selections=2
    )

    for seed in range(20):
        picked = pick_place_criminal_options(decision, 2, random.Random(seed))
        den_picks = [
            oid for oid in picked if oid in ("place_den_0_artisti", "place_den_0_studenti")
        ]
        assert len(den_picks) <= 1, picked
        assert len(picked) == 2


# --- "always play/take, rarely hold back" heuristics (2026-09-18) ---------
# These decision types used to fall through to HeuristicBot's generic
# uniform-random branch — a literal coinflip on whether to act at all,
# even when acting was obviously free value (game designer: "raramente
# conviene conservare una carta").


def test_heuristic_bot_always_evolves_a_sale_link(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    view = build_player_view(state, player_id, _price_tracks(game_data))
    options = (
        DecisionOption(
            option_id="evolve_sale_link_yes",
            label_key="decision.evolve_sale_link.yes",
            payload={"evolve": True},
        ),
        DecisionOption(
            option_id="evolve_sale_link_no",
            label_key="decision.evolve_sale_link.no",
            payload={"evolve": False},
        ),
    )
    bot = HeuristicBot()
    # Across many decision_ids (each reseeds HeuristicBot's internal rng
    # differently) — a real coinflip would pick "no" roughly half the time.
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="evolve_sale_link",
            prompt_key="decision.evolve_sale_link.prompt",
            options=options,
            min_selections=1,
            max_selections=1,
            can_pass=False,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, EvolveSaleLink)
        assert command.evolve is True


def test_heuristic_bot_always_takes_a_brawl_link_evolution_when_offered(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    view = build_player_view(state, player_id, _price_tracks(game_data))
    options = (
        DecisionOption(
            option_id="brawl_link_pawn1",
            label_key="decision.choose_brawl_link_evolution.option",
            payload={"pawn_id": "pawn1"},
        ),
    )
    bot = HeuristicBot()
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="choose_brawl_link_evolution",
            prompt_key="decision.choose_brawl_link_evolution.prompt",
            options=options,
            min_selections=0,
            max_selections=1,
            can_pass=True,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, ChooseBrawlLinkEvolution)
        assert command.pawn_id == "pawn1"


def test_heuristic_bot_plays_the_highest_gun_brawl_card(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    view = build_player_view(state, player_id, _price_tracks(game_data))
    options = (
        DecisionOption(
            option_id="brawl_card_low",
            label_key="decision.play_brawl_card.option",
            payload={"card_id": "card_low"},
        ),
        DecisionOption(
            option_id="brawl_card_high",
            label_key="decision.play_brawl_card.option",
            payload={"card_id": "card_high"},
        ),
    )
    decision = PendingDecision(
        decision_id="decision_test",
        player_id=player_id,
        decision_type="play_brawl_card",
        prompt_key="decision.play_brawl_card.prompt",
        options=options,
        min_selections=0,
        max_selections=1,
        can_pass=True,
    )
    bot = HeuristicBot(gun_count_by_card_id={"card_low": 1, "card_high": 4})

    command = bot.choose(view, decision)

    assert isinstance(command, PlayBrawlCard)
    assert command.card_id == "card_high"


def test_heuristic_bot_assigns_brawl_guns_to_self(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    other_id = state.player_order[1]
    view = build_player_view(state, player_id, _price_tracks(game_data))
    options = (
        DecisionOption(
            option_id="brawl_target_other",
            label_key="decision.assign_brawl_guns.option",
            payload={"target_player_id": other_id},
        ),
        DecisionOption(
            option_id="brawl_target_self",
            label_key="decision.assign_brawl_guns.option",
            payload={"target_player_id": player_id},
        ),
    )
    bot = HeuristicBot()
    # Across many decision_ids — a plain random pick between self/other
    # would land on "other" roughly half the time.
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="assign_brawl_guns",
            prompt_key="decision.assign_brawl_guns.prompt",
            options=options,
            min_selections=1,
            max_selections=1,
            can_pass=False,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, AssignBrawlGuns)
        assert command.target_player_id == player_id


def test_heuristic_bot_chooses_the_richest_marketing_card(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    view = build_player_view(state, player_id, _price_tracks(game_data))
    options = (
        DecisionOption(
            option_id="mkt_card_a",
            label_key="decision.choose_marketing_card.option",
            payload={"card_id": "card_a", "stonk_count": 1},
        ),
        DecisionOption(
            option_id="mkt_card_b",
            label_key="decision.choose_marketing_card.option",
            payload={"card_id": "card_b", "stonk_count": 3},
        ),
    )
    bot = HeuristicBot()
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="choose_marketing_card",
            prompt_key="decision.choose_marketing_card.prompt",
            options=options,
            min_selections=0,
            max_selections=1,
            can_pass=True,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, ChooseMarketingCard)
        assert command.card_id == "card_b"


# --- Job/Raid awareness (2026-09-18) ---------------------------------------


def test_score_option_favors_buying_a_dope_type_the_covo_has_zero_of_toward_job_05(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    job_05 = next(j for j in game_data.jobs if j.job_id == "job_05")
    assert job_05.requirement["type"] == "own_dope_in_base"
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_05.tier] = JobId("job_05")

    player = next(p for p in state.players if p.player_id == player_id)
    player.base_inventory.dope_counts[DopeType.POLPO] = 1  # already held, 1 of 4 needed
    # RANA held at 0 — buying it also satisfies "almeno una per tipo".

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}

    def buy_option(dope_type):
        return DecisionOption(
            option_id="buy",
            label_key="decision.buy_dope.option",
            payload={
                "pawn_id": "fake_pawn",
                "hood_id": HOOD_1,
                "dope_type": dope_type.value,
                "price": 3,
            },
        )

    decision_new_type = _decision(player_id, "buy_dope", [buy_option(DopeType.RANA)])
    decision_held_type = _decision(player_id, "buy_dope", [buy_option(DopeType.POLPO)])

    score_new_type = score_option(
        decision_new_type.options[0], decision_new_type, view, job_by_id=job_by_id
    )
    score_held_type = score_option(
        decision_held_type.options[0], decision_held_type, view, job_by_id=job_by_id
    )
    assert score_new_type > score_held_type


def test_score_option_least_dope_value_raid_penalizes_buying_and_rewards_selling(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    raid_03 = next(r for r in game_data.raids if r.raid_card_id == "raid_03")
    assert raid_03.escape_criterion == "least_dope_value"
    state.raids.current_turn_card_id = RaidCardId("raid_03")

    view = build_player_view(state, player_id, _price_tracks(game_data))
    raid_by_id = {r.raid_card_id: r for r in game_data.raids}

    buy_decision = _decision(
        player_id,
        "buy_dope",
        [
            DecisionOption(
                option_id="buy",
                label_key="decision.buy_dope.option",
                payload={
                    "pawn_id": "fake_pawn",
                    "hood_id": HOOD_1,
                    "dope_type": "rana",
                    "price": 3,
                },
            )
        ],
    )
    score_with_raid = score_option(
        buy_decision.options[0], buy_decision, view, raid_by_id=raid_by_id
    )
    score_without_raid = score_option(buy_decision.options[0], buy_decision, view)
    assert score_with_raid < score_without_raid

    sell_decision = _decision(
        player_id,
        "sell_dope",
        [
            DecisionOption(
                option_id="sell",
                label_key="decision.sell_dope.option",
                payload={
                    "pawn_id": "fake_pawn",
                    "spot_id": view.spots[0].spot_id,
                    "dope_type": "rana",
                },
            )
        ],
    )
    sell_score_with_raid = score_option(
        sell_decision.options[0], sell_decision, view, raid_by_id=raid_by_id
    )
    sell_score_without_raid = score_option(sell_decision.options[0], sell_decision, view)
    assert sell_score_with_raid > sell_score_without_raid


# --- choose_action_type awareness (2026-09-23) -----------------------------
# The dominant lever: choosing WHICH action type to spend Grit on, not just
# picking well among a type's own targets. Game designer's own diagnosis of
# a ~25-vs-4/5 point gap against a human.


def test_score_action_type_favors_a_type_useful_to_more_revealed_jobs(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]

    # Job 5 (own_dope_in_base, count=4) only helps buy_dope.
    # Job 6 (own_links, count=4) and Job 9 (own_money, count=30) both
    # help sell_dope — so sell_dope should outscore buy_dope once both
    # are revealed and unmet.
    for job_id in ("job_05", "job_06", "job_09"):
        job_def = next(j for j in game_data.jobs if j.job_id == job_id)
        progress = state.jobs.progress_by_player[player_id]
        progress.revealed_job_id_by_tier[job_def.tier] = JobId(job_id)

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}

    score_sell = score_action_type("sell_dope", view, player_id, job_by_id, None, DEFAULT_WEIGHTS)
    score_buy = score_action_type("buy_dope", view, player_id, job_by_id, None, DEFAULT_WEIGHTS)

    assert score_sell > score_buy


def test_heuristic_bot_chooses_the_action_type_that_helps_more_active_jobs(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]

    for job_id in ("job_05", "job_06", "job_09"):
        job_def = next(j for j in game_data.jobs if j.job_id == job_id)
        progress = state.jobs.progress_by_player[player_id]
        progress.revealed_job_id_by_tier[job_def.tier] = JobId(job_id)

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}
    bot = HeuristicBot(job_by_id=job_by_id)

    options = (
        DecisionOption(
            option_id="action_type_buy_dope",
            label_key="decision.choose_action_type.option",
            payload={"action_type": "buy_dope"},
        ),
        DecisionOption(
            option_id="action_type_sell_dope",
            label_key="decision.choose_action_type.option",
            payload={"action_type": "sell_dope"},
        ),
    )
    # Across many decision_ids (different shuffle/tie-break seeds) — the
    # scored preference for sell_dope (2 active Jobs) over buy_dope (1)
    # must never flip just because the shuffle order changed.
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="choose_action_type",
            prompt_key="decision.choose_action_type.prompt",
            options=options,
            min_selections=1,
            max_selections=1,
            can_pass=False,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, ChooseActionType)
        assert command.action_type == "sell_dope"


# --- committed-Job concentration (2026-09-23) ------------------------------
# "un job raramente viene raggiunto con una sola azione... forse è
# necessario avere un minimo di visione dei 2 o 3 turni successivi" — rather
# than spreading a flat bonus evenly across every revealed Job, concentrate
# it on whichever one the player is proportionally closest to finishing.


def test_score_action_type_favors_the_job_closest_to_completion(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]

    # job_02 (tier 1, own_officers, count=1) stays untouched: 0/1 = 0%.
    # job_05 (tier 2, own_dope_in_base, count=4) is 3/4 = 75% done, so it
    # should be the committed Job even though job_progress_bonus alone
    # would treat both revealed Jobs identically.
    job_02 = next(j for j in game_data.jobs if j.job_id == "job_02")
    job_05 = next(j for j in game_data.jobs if j.job_id == "job_05")
    assert job_02.requirement["type"] == "own_officers"
    assert job_05.requirement["type"] == "own_dope_in_base"
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_02.tier] = JobId("job_02")
    progress.revealed_job_id_by_tier[job_05.tier] = JobId("job_05")

    player = next(p for p in state.players if p.player_id == player_id)
    player.base_inventory.dope_counts.clear()
    player.base_inventory.dope_counts[DopeType.POLPO] = 2
    player.base_inventory.dope_counts[DopeType.RANA] = 1

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}

    score_buy_dope = score_action_type(
        "buy_dope", view, player_id, job_by_id, None, DEFAULT_WEIGHTS
    )
    score_buy_officer = score_action_type(
        "buy_officer", view, player_id, job_by_id, None, DEFAULT_WEIGHTS
    )

    assert score_buy_dope == DEFAULT_WEIGHTS.committed_job_bonus
    assert score_buy_officer == DEFAULT_WEIGHTS.job_progress_bonus
    assert score_buy_dope > score_buy_officer


def test_heuristic_bot_chooses_the_action_type_for_the_job_closest_to_completion(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    job_02 = next(j for j in game_data.jobs if j.job_id == "job_02")
    job_05 = next(j for j in game_data.jobs if j.job_id == "job_05")
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_02.tier] = JobId("job_02")
    progress.revealed_job_id_by_tier[job_05.tier] = JobId("job_05")

    player = next(p for p in state.players if p.player_id == player_id)
    player.base_inventory.dope_counts.clear()
    player.base_inventory.dope_counts[DopeType.POLPO] = 2
    player.base_inventory.dope_counts[DopeType.RANA] = 1

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}
    bot = HeuristicBot(job_by_id=job_by_id)

    options = (
        DecisionOption(
            option_id="action_type_buy_officer",
            label_key="decision.choose_action_type.option",
            payload={"action_type": "buy_officer"},
        ),
        DecisionOption(
            option_id="action_type_buy_dope",
            label_key="decision.choose_action_type.option",
            payload={"action_type": "buy_dope"},
        ),
    )
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="choose_action_type",
            prompt_key="decision.choose_action_type.prompt",
            options=options,
            min_selections=1,
            max_selections=1,
            can_pass=False,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, ChooseActionType)
        assert command.action_type == "buy_dope"


# --- spend_link_for_extra_action awareness (2026-09-23) --------------------
# Previously a plain coinflip (rng.randint(0, 1) on whether to act at all).
# Spending a Link isn't free — it permanently demotes that Link back to a
# plain Covo pawn — so it should only happen when the unlocked action type
# is actually worth more than that opportunity cost.

_LINK_EXTRA_ACTION_TYPES = {"artisti": ("buy_dope",), "studenti": ("move_criminal",)}


def test_score_spend_link_prefers_the_link_whose_action_helps_the_committed_job(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    job_05 = next(j for j in game_data.jobs if j.job_id == "job_05")
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_05.tier] = JobId("job_05")

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}

    score_artisti_link = score_spend_link_for_extra_action_option(
        {"pawn_id": "pawn_a", "contact_id": "artisti", "link_level": 1},
        view,
        player_id,
        job_by_id,
        None,
        _LINK_EXTRA_ACTION_TYPES,
        DEFAULT_WEIGHTS,
    )
    score_studenti_link = score_spend_link_for_extra_action_option(
        {"pawn_id": "pawn_b", "contact_id": "studenti", "link_level": 1},
        view,
        player_id,
        job_by_id,
        None,
        _LINK_EXTRA_ACTION_TYPES,
        DEFAULT_WEIGHTS,
    )
    assert score_artisti_link > score_studenti_link
    assert score_artisti_link >= 0.0


def test_score_spend_link_goes_negative_when_it_would_undercut_an_unmet_own_links_job(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    job_06 = next(j for j in game_data.jobs if j.job_id == "job_06")
    assert job_06.requirement["type"] == "own_links"
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_06.tier] = JobId("job_06")

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}

    # Neither Link's Contact unlocks anything that helps job_06 (which
    # needs sell_dope), so spending either one only pays the opportunity
    # cost with nothing in return.
    score = score_spend_link_for_extra_action_option(
        {"pawn_id": "pawn_b", "contact_id": "studenti", "link_level": 1},
        view,
        player_id,
        job_by_id,
        None,
        _LINK_EXTRA_ACTION_TYPES,
        DEFAULT_WEIGHTS,
    )
    assert score < 0.0


def test_heuristic_bot_declines_to_spend_a_link_that_would_undercut_an_unmet_own_links_job(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    job_06 = next(j for j in game_data.jobs if j.job_id == "job_06")
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_06.tier] = JobId("job_06")

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}
    bot = HeuristicBot(job_by_id=job_by_id, link_extra_action_types=_LINK_EXTRA_ACTION_TYPES)

    options = (
        DecisionOption(
            option_id="spend_link_studenti",
            label_key="decision.spend_link_for_extra_action.option",
            payload={"pawn_id": "pawn_b", "contact_id": "studenti", "link_level": 1},
        ),
    )
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="spend_link_for_extra_action",
            prompt_key="decision.spend_link_for_extra_action.prompt",
            options=options,
            min_selections=0,
            max_selections=1,
            can_pass=True,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, PassOptionalStep)


def test_heuristic_bot_spends_a_link_whose_action_helps_an_unmet_job(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    job_05 = next(j for j in game_data.jobs if j.job_id == "job_05")
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_05.tier] = JobId("job_05")

    view = build_player_view(state, player_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}
    bot = HeuristicBot(job_by_id=job_by_id, link_extra_action_types=_LINK_EXTRA_ACTION_TYPES)

    options = (
        DecisionOption(
            option_id="spend_link_artisti",
            label_key="decision.spend_link_for_extra_action.option",
            payload={"pawn_id": "pawn_a", "contact_id": "artisti", "link_level": 1},
        ),
        DecisionOption(
            option_id="spend_link_studenti",
            label_key="decision.spend_link_for_extra_action.option",
            payload={"pawn_id": "pawn_b", "contact_id": "studenti", "link_level": 1},
        ),
    )
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="spend_link_for_extra_action",
            prompt_key="decision.spend_link_for_extra_action.prompt",
            options=options,
            min_selections=0,
            max_selections=1,
            can_pass=True,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, SpendLinkForExtraAction)
        assert command.pawn_id == "pawn_a"


# --- deliberate Rissa/Poker for a Job that needs it (2026-09-23) -----------
# "rissa with at least 2 guns in the cards, or poker with at least a card to
# get a couple or a tris must be played if needed for jobs" — 2 of the 3
# Jobs no action type can ever advance (win_brawls, own_poker_chips) become
# reachable this way instead of purely incidental.


def _crowded_move_decision(mover_id, destination) -> PendingDecision:
    option = DecisionOption(
        option_id="move",
        label_key="decision.move_criminal.option",
        payload={
            "pawn_id": "fake_pawn",
            "destination_hood_id": destination,
            "deck_contact_id": None,
        },
    )
    return _decision(mover_id, "move_criminal", [option])


def _crowd_hood_q2(state, mover_id) -> None:
    state.board.hoods[HOOD_2].revealed = True
    for i, player_id in enumerate(state.player_order):
        if player_id == mover_id:
            continue
        pawn_id = next(
            pid for pid in state.players[i].pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE
        )
        _put_criminal(state, pawn_id, HOOD_2)
    extra_pawn_id = _fresh_pawn(state, 0)
    _put_criminal(state, extra_pawn_id, HOOD_2)


def test_score_option_move_criminal_favors_a_rissa_when_win_brawls_job_has_a_strong_hand(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    mover_id = state.player_order[0]
    _crowd_hood_q2(state, mover_id)

    job_01 = next(j for j in game_data.jobs if j.job_id == "job_01")
    assert job_01.requirement["type"] == "win_brawls"
    progress = state.jobs.progress_by_player[mover_id]
    progress.revealed_job_id_by_tier[job_01.tier] = JobId("job_01")
    mover_player = next(p for p in state.players if p.player_id == mover_id)
    mover_player.hand_card_ids.append("card_strong")

    view = build_player_view(state, mover_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}
    decision = _crowded_move_decision(mover_id, HOOD_2)

    score_baseline = score_option(decision.options[0], decision, view)
    score_with_job_and_card = score_option(
        decision.options[0],
        decision,
        view,
        job_by_id=job_by_id,
        gun_count_by_card_id={"card_strong": 3},
    )
    assert score_with_job_and_card > score_baseline
    assert score_with_job_and_card > 0  # the penalty flips into a bonus


def test_score_option_move_criminal_still_avoids_a_rissa_without_a_strong_card(
    game_data,
) -> None:
    state, _ = _new_game(game_data)
    mover_id = state.player_order[0]
    _crowd_hood_q2(state, mover_id)

    job_01 = next(j for j in game_data.jobs if j.job_id == "job_01")
    progress = state.jobs.progress_by_player[mover_id]
    progress.revealed_job_id_by_tier[job_01.tier] = JobId("job_01")
    # No 2+-Gun card in hand — the Job alone isn't enough.

    view = build_player_view(state, mover_id, _price_tracks(game_data))
    job_by_id = {j.job_id: j for j in game_data.jobs}
    decision = _crowded_move_decision(mover_id, HOOD_2)

    score = score_option(
        decision.options[0], decision, view, job_by_id=job_by_id, gun_count_by_card_id={}
    )
    assert score < 0


def test_score_play_poker_card_prefers_keeping_the_hand_diverse(game_data) -> None:
    """This game's own `poker_rank_order` (data/game_config.json) puts
    "five_different" — no repeated colour at all — *first* (best), the
    opposite of real-world poker; a card that repeats one of the banco's
    3 colours instead produces "pair", ranked last (2026-09-24 bug fix:
    an earlier version of this scorer had this backwards)."""
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    state.poker.current_match = PokerMatchState(
        match_id="match_test",
        launched_by_player_id=player_id,
        gamble_card_id="card_launch",
        banco_symbols=(PokerSymbolColor.ROSA, PokerSymbolColor.VERDE, PokerSymbolColor.AZZURRO),
    )
    view = build_player_view(state, player_id, _price_tracks(game_data))

    poker_symbols_by_card_id = {
        "card_pair": (PokerSymbolColor.ROSA, PokerSymbolColor.GRIGIO),  # repeats banco's ROSA
        "card_diverse": (PokerSymbolColor.ARANCIONE, PokerSymbolColor.GRIGIO),  # all 5 distinct
    }
    banco_symbols_by_card_id = {
        "card_launch": (PokerSymbolColor.ROSA, PokerSymbolColor.VERDE, PokerSymbolColor.AZZURRO),
    }
    poker_rank_order = list(game_data.config["poker_rank_order"])

    score_pair = score_play_poker_card_option(
        "card_pair", view, poker_symbols_by_card_id, banco_symbols_by_card_id, poker_rank_order
    )
    score_diverse = score_play_poker_card_option(
        "card_diverse", view, poker_symbols_by_card_id, banco_symbols_by_card_id, poker_rank_order
    )
    assert score_diverse > score_pair


def test_heuristic_bot_reveals_the_poker_card_that_keeps_the_hand_diverse(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    state.poker.current_match = PokerMatchState(
        match_id="match_test",
        launched_by_player_id=player_id,
        gamble_card_id="card_launch",
        banco_symbols=(PokerSymbolColor.ROSA, PokerSymbolColor.VERDE, PokerSymbolColor.AZZURRO),
    )
    view = build_player_view(state, player_id, _price_tracks(game_data))

    poker_symbols_by_card_id = {
        "card_pair": (PokerSymbolColor.ROSA, PokerSymbolColor.GRIGIO),
        "card_diverse": (PokerSymbolColor.ARANCIONE, PokerSymbolColor.GRIGIO),
    }
    banco_symbols_by_card_id = {
        "card_launch": (PokerSymbolColor.ROSA, PokerSymbolColor.VERDE, PokerSymbolColor.AZZURRO),
    }
    bot = HeuristicBot(
        poker_symbols_by_card_id=poker_symbols_by_card_id,
        banco_symbols_by_card_id=banco_symbols_by_card_id,
        poker_rank_order=list(game_data.config["poker_rank_order"]),
    )

    options = (
        DecisionOption(
            option_id="poker_card_card_pair",
            label_key="decision.play_poker_card.option",
            payload={"card_id": "card_pair", "match_id": "match_test"},
        ),
        DecisionOption(
            option_id="poker_card_card_diverse",
            label_key="decision.play_poker_card.option",
            payload={"card_id": "card_diverse", "match_id": "match_test"},
        ),
    )
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="play_poker_card",
            prompt_key="decision.play_poker_card.prompt",
            options=options,
            min_selections=1,
            max_selections=1,
            can_pass=False,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, PlayPokerCard)
        assert command.card_ids == ("card_diverse",)


# --- sell_dope always maxes its package (2026-09-24) ------------------------
# "rissa and sell sono importanti per ottenere ganci da spendere...
# vendendo merci con guadagni piccoli, senza necessariamente aspettare che i
# prezzi siano alti" — a bigger package sets a higher Link level (CLAUDE.md
# §11.5), so a random smaller count was quietly capping it.


def test_heuristic_bot_sells_the_largest_legal_package(game_data) -> None:
    state, _ = _new_game(game_data)
    player_id = state.player_order[0]
    player = next(p for p in state.players if p.player_id == player_id)
    player.base_inventory.dope_counts.clear()
    player.base_inventory.dope_counts[DopeType.RANA] = 3

    view = build_player_view(state, player_id, _price_tracks(game_data))
    spot_id = view.spots[0].spot_id

    options = tuple(
        DecisionOption(
            option_id=f"sell_{i}",
            label_key="decision.sell_dope.option",
            payload={"pawn_id": f"fake_pawn_{i}", "spot_id": spot_id, "dope_type": "rana"},
        )
        for i in range(3)
    )
    bot = HeuristicBot()
    for i in range(20):
        decision = PendingDecision(
            decision_id=f"decision_test_{i}",
            player_id=player_id,
            decision_type="sell_dope",
            prompt_key="decision.sell_dope.prompt",
            options=options,
            min_selections=1,
            max_selections=3,
            can_pass=True,
        )
        command = bot.choose(view, decision)
        assert isinstance(command, SellDope)
        assert len(command.sales) == 3
