from dope_engine.domain.enums import DopeType, PawnRole
from dope_engine.domain.ids import GameId, JobId
from dope_engine.rules import jail
from dope_engine.rules.setup import create_initial_state


def _new_game(game_data, seed=1, human_seat=0):
    return create_initial_state(game_data, game_id=GameId("g"), seed=seed, human_seat=human_seat)


def _set_revealed_job(state, game_data, player_id, job_id: str) -> None:
    job_def = next(j for j in game_data.jobs if j.job_id == job_id)
    progress = state.jobs.progress_by_player[player_id]
    progress.revealed_job_id_by_tier[job_def.tier] = JobId(job_id)
    progress.tier_piles[job_def.tier] = [
        jid for jid in progress.tier_piles[job_def.tier] if jid != job_id
    ]


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


def test_evasion_immune_rat_stays_in_its_slot_when_someone_else_triggers(game_data) -> None:
    """Cards 054/059 "BIG RAT" ("piazza un criminale in prigione. Se c'è
    Evasione, non evade", game designer, 2026-08-31): a Rat with
    `jail_evasion_immune` set stays in its own slot (and its own
    confiscated Dope, if any, stays with it) when a *different* pawn
    fills the 6th slot and triggers Evasion — the flag is consumed
    either way, so a second Evasion would release it normally."""
    state, _ = _new_game(game_data)
    player = state.players[0]
    pawn_ids = player.pawn_ids[:6]
    events: list = []

    for pawn_id in pawn_ids[:4]:
        jail.arrest_pawn(state, pawn_id, events)
    immune_pawn_id = pawn_ids[4]
    jail.arrest_pawn(state, immune_pawn_id, events)
    state.pawns[immune_pawn_id].jail_evasion_immune = True
    immune_slot_index = state.pawns[immune_pawn_id].jail_slot
    state.jail.slots[immune_slot_index].confiscated_dope_type = DopeType.RANA

    jail.arrest_pawn(state, pawn_ids[5], events)

    assert any(type(e).__name__ == "JailEscapeTriggered" for e in events)
    immune_pawn = state.pawns[immune_pawn_id]
    assert immune_pawn.role == PawnRole.RAT
    assert immune_pawn.jail_slot == immune_slot_index
    assert immune_pawn.jail_evasion_immune is False
    assert state.jail.slots[immune_slot_index].rat_pawn_id == immune_pawn_id
    assert state.jail.slots[immune_slot_index].confiscated_dope_type == DopeType.RANA
    for pawn_id in pawn_ids[:4]:
        assert state.pawns[pawn_id].role == PawnRole.IN_BASE
    trigger_pawn = state.pawns[pawn_ids[5]]
    assert trigger_pawn.role == PawnRole.LINK


def test_evasion_immune_rat_stays_even_as_the_triggering_pawn(game_data) -> None:
    """The one case the card text doesn't spell out (PROVISIONAL,
    game designer, 2026-08-31): if the immune Rat itself fills the 6th
    slot, it stays a plain Rat instead of evolving into a Politici Link —
    "non evade" applied uniformly rather than inventing a substitute
    evolution for someone else. The other 5 still resolve normally."""
    state, _ = _new_game(game_data)
    player = state.players[0]
    pawn_ids = player.pawn_ids[:6]
    events: list = []

    for pawn_id in pawn_ids[:5]:
        jail.arrest_pawn(state, pawn_id, events)
    immune_pawn_id = pawn_ids[5]
    state.pawns[immune_pawn_id].jail_evasion_immune = True

    jail.arrest_pawn(state, immune_pawn_id, events)

    assert any(type(e).__name__ == "JailEscapeTriggered" for e in events)
    immune_pawn = state.pawns[immune_pawn_id]
    assert immune_pawn.role == PawnRole.RAT
    assert immune_pawn.jail_evasion_immune is False
    for pawn_id in pawn_ids[:5]:
        assert state.pawns[pawn_id].role == PawnRole.IN_BASE
    assert not any(type(e).__name__ == "PawnBecameLink" for e in events)


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


def test_own_rats_job_completes_even_when_the_third_rat_triggers_evasion(game_data) -> None:
    """Bug report (2026-08-27): with 2 Rats already, sending a 6th Rat
    overall (this player's own 3rd) triggered Evasion correctly but never
    completed Job 4 ("Abbi 3 Rats") — the post-success hook that normally
    checks completion only runs once, at the very end of the whole
    command, by which point Evasion had already returned every Rat
    (this player's 3 included) back to base, so the live snapshot no
    longer showed 3. rules/jail.py now checks completion itself at the
    one moment the snapshot can be true: right as the 6th slot fills,
    before Evasion undoes it."""
    state, _ = _new_game(game_data)
    job = next(j for j in game_data.jobs if j.requirement["type"] == "own_rats")
    assert job.requirement["count"] == 3
    player_0 = state.players[0]
    _set_revealed_job(state, game_data, player_0.player_id, job.job_id)
    events: list = []

    # 5 arrests: 2 belong to player 0, spread among the other 3 players'
    # pawns so player 0 only has 2 Rats — not yet 3 — after this.
    jail.arrest_pawn(state, state.players[1].pawn_ids[0], events)
    jail.arrest_pawn(state, state.players[2].pawn_ids[0], events)
    jail.arrest_pawn(state, player_0.pawn_ids[0], events)
    jail.arrest_pawn(state, state.players[3].pawn_ids[0], events)
    jail.arrest_pawn(state, player_0.pawn_ids[1], events)
    assert not any(type(e).__name__ == "JobCompleted" for e in events)

    # The 6th arrest overall is player 0's own 3rd Rat, and also the one
    # that fills the last slot and triggers Evasion.
    jail.arrest_pawn(state, player_0.pawn_ids[2], events)

    assert any(type(e).__name__ == "JailEscapeTriggered" for e in events)
    completed = [e for e in events if type(e).__name__ == "JobCompleted"]
    assert any(e.player_id == player_0.player_id and e.job_id == job.job_id for e in completed)
    assert state.pending_job_reward is not None
    assert any(
        entry.player_id == player_0.player_id and entry.job_id == job.job_id
        for entry in state.pending_job_reward.queue
    )
