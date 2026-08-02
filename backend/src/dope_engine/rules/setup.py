"""Builds the initial GameState per docs/rules/RULES_CANONICAL.md section
E (Setup) and F (Mappa), using the game's deterministic RNG for every
random choice (starter hand pool, covered-Hood tile assignment, Job
piles, Raid selection, first player).

This module is deliberately the only place that turns `GameData`
(loaded, static content) plus a seed into a live `GameState`; nothing
here touches the filesystem or a transport layer.
"""

from __future__ import annotations

from dope_engine.application.data_loader import GameData
from dope_engine.domain.entities import (
    BaseInventory,
    DeckState,
    HoodState,
    JailSlot,
    PawnLocation,
    PawnState,
    SalesSpotState,
)
from dope_engine.domain.enums import (
    ActiveStep,
    ControllerType,
    DopeType,
    GamePhase,
    GameStatus,
    PawnRole,
)
from dope_engine.domain.events import DomainEvent, GameStarted
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    EventId,
    GameId,
    HoodId,
    JobId,
    PawnId,
    PlayerId,
    SkillId,
)
from dope_engine.domain.rng import GameRandom
from dope_engine.domain.state import (
    BoardState,
    DecksState,
    GameState,
    JailState,
    JobBoardCell,
    JobsState,
    MarketState,
    PlayerJobProgress,
    PlayerState,
    PokerState,
    RaidsState,
    SkillsState,
)
from dope_engine.rules import turn_flow


def create_initial_state(
    data: GameData,
    *,
    game_id: GameId,
    seed: int,
    human_seat: int,
) -> tuple[GameState, list[DomainEvent]]:
    player_count = data.config["player_count"]
    if not 0 <= human_seat < player_count:
        raise ValueError(f"human_seat must be in [0, {player_count}), got {human_seat}")

    rng = GameRandom.from_seed(seed)

    player_order = [PlayerId(f"player_{i}") for i in range(data.config["player_count"])]
    players = _build_players(data, player_order, human_seat)
    pawns = _build_pawns(data, players)

    board = _build_board(data)
    _apply_covered_hood_tiles(data, board, rng.derive_stream("covered_tiles"))

    hands, decks = _deal_starter_hands(data, player_order, rng.derive_stream("starter_hands"))
    for player in players:
        player.hand_card_ids = hands[player.player_id]

    _place_starting_criminals(data, players, pawns, board, hands)

    market = _build_market(data, board)
    jail = JailState(slots=[JailSlot(index=i) for i in range(data.config["jail_slot_count"])])
    jobs = _build_jobs_state(data, player_order, rng.derive_stream("jobs"))
    raids = _build_raids_state(data, rng.derive_stream("raids"))
    skills = _build_skills_state(data, rng.derive_stream("skills"))

    first_player_id = rng.derive_stream("first_player").choice(player_order)

    # §D4/§D5 (Milestone 5): rules/raids.py needs the Raid cards' escape
    # criteria and the full per-Dope-type price tracks — both static,
    # load-time content — but is reached from many different points deep
    # in rules/turn_flow.py's and rules/poker.py's own round-advance call
    # graphs. Rather than threading two extra parameters through that
    # entire graph just to reach the one call site at the end of it
    # (rules/turn_flow.py::_enter_showdown_phase), they're derived once
    # here and copied onto `state.configuration` — the same place every
    # other piece of static game content (the whole of game_config.json)
    # already lives, reachable from any rule function without threading.
    # A copy, not a reference to `data.config`: nothing may mutate the
    # shared GameData across multiple games sharing one process.
    configuration = dict(data.config)
    configuration["raid_escape_criterion_by_raid_card_id"] = {
        r.raid_card_id: r.escape_criterion for r in data.raids
    }
    configuration["price_track_by_dope_type"] = {
        dope_type: list(definition.price_track)
        for dope_type, definition in data.dope_types.items()
    }
    # Milestone 5 Stage 4: each Skill's mechanical effect (data/skills.json
    # ::effect) is static content too, read by rules/skills.py from any
    # rule function without needing separate threading — same reasoning
    # as the two lookups just above.
    configuration["skill_effect_by_id"] = {s.skill_id: s.effect for s in data.skills}

    state = GameState(
        schema_version=data.config["schema_version"],
        rules_version=data.config["rules_version"],
        game_id=game_id,
        seed=seed,
        revision=1,
        rng_state=rng.get_state(),
        status=GameStatus.IN_PROGRESS,
        configuration=configuration,
        players=players,
        player_order=player_order,
        first_player_id=first_player_id,
        current_player_id=first_player_id,
        turn_index=1,
        action_round_index=0,
        phase=GamePhase.TIP_OFF,
        active_step=ActiveStep.NONE,
        pawns=pawns,
        board=board,
        market=market,
        jail=jail,
        decks=decks,
        jobs=jobs,
        raids=raids,
        poker=PokerState(),
        skills=skills,
        pending_decision=None,
        event_log_cursor=0,
        final_score=None,
    )

    events: list[DomainEvent] = [
        GameStarted(
            event_id=EventId("event_0001"),
            game_id=game_id,
            revision=1,
            seed=seed,
            rules_version=state.rules_version,
            player_ids=tuple(player_order),
        ),
    ]
    state.event_log_cursor = len(events)
    turn_flow.start_tip_off(state, events)
    state.event_log_cursor = len(events)
    return state, events


def _build_players(
    data: GameData, player_order: list[PlayerId], human_seat: int
) -> list[PlayerState]:
    starting_dope_by_seat = data.config["starting_dope_by_seat"]
    players = []
    for seat_index, player_id in enumerate(player_order):
        dope_counts: dict[DopeType, int] = {}
        for dope_name in starting_dope_by_seat[seat_index]:
            dope_type = DopeType(dope_name)
            dope_counts[dope_type] = dope_counts.get(dope_type, 0) + 1

        players.append(
            PlayerState(
                player_id=player_id,
                seat_index=seat_index,
                controller_type=(
                    ControllerType.HUMAN if seat_index == human_seat else ControllerType.BOT
                ),
                display_name=f"Player {seat_index + 1}",
                money=data.config["starting_money"],
                base_inventory=BaseInventory(dope_counts=dope_counts),
            )
        )
    return players


def _build_pawns(data: GameData, players: list[PlayerState]) -> dict[PawnId, PawnState]:
    pawns: dict[PawnId, PawnState] = {}
    for player in players:
        for i in range(data.config["pawns_per_player"]):
            pawn_id = PawnId(f"pawn_{player.player_id}_{i:02d}")
            pawns[pawn_id] = PawnState(
                pawn_id=pawn_id,
                owner_player_id=player.player_id,
                role=PawnRole.IN_BASE,
                location=PawnLocation.base(),
            )
            player.pawn_ids.append(pawn_id)
    return pawns


def _build_board(data: GameData) -> BoardState:
    hoods: dict[HoodId, HoodState] = {}
    for hood_def in data.board.hoods:
        dope_stack = (
            [hood_def.starting_dope_type] * 3
            if hood_def.revealed and hood_def.starting_dope_type
            else []
        )
        hoods[hood_def.hood_id] = HoodState(
            hood_id=hood_def.hood_id,
            contact_id=hood_def.contact_id,
            adjacent_hood_ids=list(hood_def.adjacent_hood_ids),
            revealed=hood_def.revealed,
            dope_stack=dope_stack,
            capacity=data.config["hood_capacity"],
            dope_type=hood_def.starting_dope_type if hood_def.revealed else None,
        )

    spots = {}
    for spot_def in data.contacts.spots:
        spots[spot_def.spot_id] = SalesSpotState(
            spot_id=spot_def.spot_id,
            contact_id=spot_def.contact_id,
            accepted_dope_type=spot_def.accepted_dope_type,
            adjacent_spot_ids=list(spot_def.adjacent_spot_ids),
            capacity=data.config["spot_max_dope"],
        )

    return BoardState(hoods=hoods, spots=spots)


def _apply_covered_hood_tiles(data: GameData, board: BoardState, rng: GameRandom) -> None:
    tiles = list(data.board.covered_hood_tiles.tile_values)
    dope_pool = list(data.board.covered_hood_tiles.dope_pool)
    rng.shuffle(tiles)
    rng.shuffle(dope_pool)
    pairs = list(zip(tiles, dope_pool, strict=True))

    covered_hood_ids = [hood_id for hood_id, hood in board.hoods.items() if not hood.revealed]
    rng.shuffle(covered_hood_ids)

    for hood_id, (tile, dope_type) in zip(covered_hood_ids, pairs, strict=True):
        board.covered_hood_tile_assignment[hood_id] = (tile.tile_id, dope_type)


def _deal_starter_hands(
    data: GameData, player_order: list[PlayerId], rng: GameRandom
) -> tuple[dict[PlayerId, list[CardId]], DecksState]:
    customer_decks: dict[ContactId, DeckState] = {}
    starter_pool: list[tuple[ContactId, CardId]] = []

    cards_by_contact: dict[ContactId, list[CardId]] = {}
    for card in data.customer_cards:
        cards_by_contact.setdefault(card.contact_id, []).append(card.card_id)

    for contact_id, card_ids in cards_by_contact.items():
        deck_rng = rng.derive_stream(f"deck_{contact_id}")
        shuffled = list(card_ids)
        deck_rng.shuffle(shuffled)
        taken, remaining = shuffled[:3], shuffled[3:]
        customer_decks[contact_id] = DeckState(draw_pile_card_ids=remaining)
        starter_pool.extend((contact_id, card_id) for card_id in taken)

    rng.shuffle(starter_pool)

    hands: dict[PlayerId, list[CardId]] = {p: [] for p in player_order}
    index = 0
    for player_id in player_order:
        for _ in range(data.config["starter_hand_cards_dealt_per_player"]):
            _, card_id = starter_pool[index]
            hands[player_id].append(card_id)
            index += 1

    for contact_id, card_id in starter_pool[index:]:
        customer_decks[contact_id].draw_pile_card_ids.append(card_id)

    return hands, DecksState(customer_decks_by_contact=customer_decks)


def _place_starting_criminals(
    data: GameData,
    players: list[PlayerState],
    pawns: dict[PawnId, PawnState],
    board: BoardState,
    hands: dict[PlayerId, list[CardId]],
) -> None:
    revealed_hood_by_contact: dict[ContactId, HoodId] = {
        hood.contact_id: hood.hood_id for hood in board.hoods.values() if hood.revealed
    }
    card_by_id = {card.card_id: card for card in data.customer_cards}

    for player in players:
        available_pawn_ids = iter(
            pid for pid in player.pawn_ids if pawns[pid].role == PawnRole.IN_BASE
        )
        for card_id in hands[player.player_id]:
            contact_id = card_by_id[card_id].contact_id
            hood_id = revealed_hood_by_contact[contact_id]
            pawn = pawns[next(available_pawn_ids)]
            pawn.role = PawnRole.CRIMINAL
            pawn.location = PawnLocation.hood(hood_id)
            board.hoods[hood_id].criminal_pawn_ids.append(pawn.pawn_id)


def _build_market(data: GameData, board: BoardState) -> MarketState:
    price_index: dict[DopeType, int] = {}
    supply_remaining: dict[DopeType, int] = {}

    placed_counts: dict[DopeType, int] = {}
    for hood in board.hoods.values():
        for dope_type in hood.dope_stack:
            placed_counts[dope_type] = placed_counts.get(dope_type, 0) + 1

    for dope_type, definition in data.dope_types.items():
        price_index[dope_type] = definition.initial_price_index
        supply_remaining[dope_type] = definition.total_supply - placed_counts.get(dope_type, 0)

    for player_seat_dope in data.config["starting_dope_by_seat"]:
        for dope_name in player_seat_dope:
            dope_type = DopeType(dope_name)
            supply_remaining[dope_type] -= 1

    return MarketState(
        price_index_by_dope_type=price_index,
        supply_remaining_by_dope_type=supply_remaining,
    )


def _build_jobs_state(data: GameData, player_order: list[PlayerId], rng: GameRandom) -> JobsState:
    jobs_by_tier: dict[int, list[JobId]] = {}
    for job in data.jobs:
        jobs_by_tier.setdefault(job.tier, []).append(job.job_id)

    progress_by_player: dict[PlayerId, PlayerJobProgress] = {}
    for player_id in player_order:
        player_rng = rng.derive_stream(f"jobs_{player_id}")
        tier_piles: dict[int, list[JobId]] = {}
        revealed: dict[int, JobId | None] = {}
        for tier, job_ids in jobs_by_tier.items():
            pile = list(job_ids)
            player_rng.shuffle(pile)
            revealed[tier] = pile.pop(0)
            tier_piles[tier] = pile
        progress_by_player[player_id] = PlayerJobProgress(
            tier_piles=tier_piles, revealed_job_id_by_tier=revealed
        )

    board_cells = [
        JobBoardCell(job_id=job.job_id, column_index=col)
        for job in data.jobs
        for col in range(data.config["job_board_columns_per_row"])
    ]

    return JobsState(progress_by_player=progress_by_player, board=board_cells)


def _build_skills_state(data: GameData, rng: GameRandom) -> SkillsState:
    remaining_by_contact: dict[ContactId, list[SkillId]] = {}
    for skill in data.skills:
        remaining_by_contact.setdefault(skill.contact_id, []).append(skill.skill_id)
    for contact_id, skill_ids in remaining_by_contact.items():
        rng.derive_stream(f"skills_{contact_id}").shuffle(skill_ids)
    return SkillsState(remaining_by_contact=remaining_by_contact)


def _build_raids_state(data: GameData, rng: GameRandom) -> RaidsState:
    all_ids = [r.raid_card_id for r in data.raids]
    selected = rng.sample(all_ids, data.config["raid_cards_per_game"])
    return RaidsState(selected_card_ids=tuple(selected))
