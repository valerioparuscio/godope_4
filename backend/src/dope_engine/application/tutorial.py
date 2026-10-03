"""Tutorial sandbox scenarios ("prova a pensare alla differenza fra
regolamento e tutorial", game designer, 2026-09-24) — each one patches a
freshly-created, otherwise normal `GameState` so the human's very next
`PendingDecision` is exactly the one situation a tutorial card teaches
("clicca la pedina illuminata, poi il quartiere"), reusing the *real*
engine (`rules/setup.py::create_initial_state`, the real
`legal_actions.py` generator, the real command handlers) rather than a
mocked-up teaching mode — CLAUDE.md's own "stessa interfaccia di gioco"
principle applies here too: a scenario is a real, playable game, just
one hand-picked into the right starting shape.

Pilot (2026-09-24, 5 of the ~20 cards discussed with the game designer,
chosen to cover every distinct interaction *shape* already in the
frontend before building the rest): a quick-pill click (`grit`), a
single-stage board click (`place_criminal`), a two-stage board click
(`move_criminal`, the designer's own original example), a multi-target
package with a Confirm button (`buy_dope`), and a hand-card decision
inside a special event (`brawl_trigger`). Grown since (2026-09-26,
following `docs/rules/DOPE_WEB_TUTORIAL_SCENEGGIATO_SPEC.md`'s own
scripted sequence) into a fuller run reusing the same pattern, plus
`frontend/src/tutorial/scenarios.ts`'s `continuesPrevious` flag for
sequences that share one sandbox across several cards instead of each
being its own throwaway game (a Rissa's own trigger → cards → reward →
Gancio → relocation, all one running `BrawlProgress`).

Deliberately *not* exposed as its own `BotPolicy`/decision-generation
path: a scenario only ever mutates a state that `create_initial_state`
already produced validly, using the same direct field-patching pattern
`tests/unit/test_officers.py`/`test_brawl.py`'s own fixtures use — never
an ad-hoc "fake" state shape the real generator wouldn't also accept."""

from __future__ import annotations

from collections.abc import Callable

from dope_engine.application.data_loader import GameData
from dope_engine.domain.entities import (
    OfficerLocationType,
    OfficerState,
    PawnLocation,
)
from dope_engine.domain.enums import ActionType, ActiveStep, GamePhase, OfficerType, PawnRole
from dope_engine.domain.events import DomainEvent
from dope_engine.domain.ids import (
    CardId,
    ContactId,
    HoodId,
    JobId,
    OfficerId,
    PawnId,
    PlayerId,
    SpotId,
)
from dope_engine.domain.state import (
    BrawlProgress,
    GameState,
    PlayerState,
    PokerMatchState,
    find_player,
)
from dope_engine.rules import jail, links, poker

TutorialScenarioBuilder = Callable[[GameState, GameData], None]


def _human(state: GameState):  # noqa: ANN201 - PlayerState, avoids an unused import otherwise
    return find_player(state, PlayerId("player_0"))


def _ready_for_human(state: GameState) -> None:
    """Common to every scenario: it's the human's own turn, right now,
    in a phase `legal_actions.py::get_legal_decision` actually serves
    decisions in (`current_player_id` must match exactly, own entry
    check) — regardless of whichever bot the real seed/setup happened
    to hand the turn to."""
    state.phase = GamePhase.ACTION_PHASE
    state.current_player_id = PlayerId("player_0")
    # Overridden by every builder that teaches a different step; a stage
    # applied over a previous one must never inherit its `active_step`.
    state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION


def _reset_flow(state: GameState) -> None:
    """The tutorial is *one* running game: every stage is applied on top of
    whatever the previous lessons left behind (game designer, 2026-10-02:
    "le schermate devono essere la sequenza di una unica partita"), so each
    stage first drops the transient, mid-action bookkeeping of the one
    before — never the board itself (pawns, Dope, Links stay where they
    are)."""
    state.pending_decision = None
    # Every answered lesson ends the human's action, which advances the
    # round counter (the bots never take a turn here) — three lessons in a
    # row would end the Turn and pop a Raid recap in the middle of "Buy".
    # Each stage starts back at Round 1 of Turn 1 so that never happens.
    state.turn_index = 1
    state.action_round_index = 1
    state.pending_corruption = None
    state.pending_brawl = None
    state.pending_job_reward = None
    state.poker.current_match = None
    state.poker.pending_bettor_order = []
    state.poker.pending_bettor_index = 0
    state.poker.pending_symbol_choice = None
    for player in state.players:
        player.pending_action_type = None
        player.current_round_grit_value = None
        player.corrupted_pawn_ids_this_action = []
        player.officer_buyer_pawn_ids_this_action = []
        player.extra_action_link_pawn_id = None
        player.extra_action_contact_id = None
        player.extra_actions_used_this_round = 0
        player.moved_pawn_ids_this_turn = []
        player.action_types_used_this_turn = []
        player.poker_launch_return_step = None
    player = _human(state)
    if not player.available_grit_values:
        player.available_grit_values = [1, 2, 3]


def _release_jail(state: GameState) -> None:
    """Sends every Rat home so a Jail lesson always starts from an empty
    Jail, whatever earlier lessons (or the learner's own play) arrested."""
    for slot in state.jail.slots:
        if slot.rat_pawn_id is None:
            continue
        pawn = state.pawns[slot.rat_pawn_id]
        pawn.role = PawnRole.IN_BASE
        pawn.location = PawnLocation.base()
        pawn.jail_slot = None
        slot.rat_pawn_id = None
        slot.confiscated_dope_type = None


def _empty_den(state: GameState) -> None:
    """Sends every Gambler home, so the Poker lesson seats exactly the
    Gamblers it needs whatever earlier lessons left in the Den."""
    for pawn_id in list(state.board.den_gambler_pawn_ids):
        pawn = state.pawns[pawn_id]
        pawn.role = PawnRole.IN_BASE
        pawn.location = PawnLocation.base()
    state.board.den_gambler_pawn_ids.clear()


def _free_pawn(state: GameState, player: PlayerState) -> PawnId:
    """An IN_BASE pawn of `player`, pulling a Criminal back from the map
    when none is left (a long continuous tutorial can run the Covo dry)."""
    pawn_id = next(
        (pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE), None
    )
    if pawn_id is not None:
        return pawn_id
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL)
    hood_id = state.pawns[pawn_id].location.hood_id
    if hood_id is not None:
        state.board.hoods[hood_id].criminal_pawn_ids.remove(pawn_id)
    state.pawns[pawn_id].role = PawnRole.IN_BASE
    state.pawns[pawn_id].location = PawnLocation.base()
    return pawn_id


def _keep_single_criminal(state: GameState) -> None:
    """Setup scatters 3 of the human's Criminals over the map; with all 3
    the first decisions offer ~7 destinations per pawn at once, too busy
    for a clean "click the pawn, then its destination" lesson. Two go back
    to the Covo — hood_q1's own stays."""
    player = _human(state)
    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        hood_id = pawn.location.hood_id
        if pawn.role == PawnRole.CRIMINAL and hood_id is not None and hood_id != "hood_q1":
            state.board.hoods[hood_id].criminal_pawn_ids.remove(pawn_id)
            pawn.role = PawnRole.IN_BASE
            pawn.location = PawnLocation.base()


def prepare_tutorial_state(state: GameState) -> None:
    """The tutorial's opening board, applied once when the sandbox game is
    created (never again — later stages must not move pawns around)."""
    _keep_single_criminal(state)


def build_grit(state: GameState, game_data: GameData) -> None:
    player = _human(state)
    _ready_for_human(state)
    state.active_step = ActiveStep.WAITING_FOR_GRIT_ACTION
    player.available_grit_values = [1, 2, 3]


def build_place_criminal(state: GameState, game_data: GameData) -> None:
    player = _human(state)
    _ready_for_human(state)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = ActionType.PLACE_CRIMINAL
    player.current_round_grit_value = 1
    player.money = 20


def build_move_criminal(state: GameState, game_data: GameData) -> None:
    """hood_q1/hood_q3 are both revealed from setup and adjacent
    (`data/board.json`), and `prepare_tutorial_state` already left exactly
    one of the human's Criminals on the map (in hood_q1) — only the
    decision itself is set here."""
    player = _human(state)
    _ready_for_human(state)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = ActionType.MOVE_CRIMINAL
    player.current_round_grit_value = 1


def build_buy_dope(state: GameState, game_data: GameData) -> None:
    """Grit 3: a package of up to 3 purchases, to teach "click several
    targets, then Confirm" — hood_q1 already has 3 units of Dope in
    stock at setup and one of the human's own Criminals already stands
    there."""
    player = _human(state)
    _ready_for_human(state)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = ActionType.BUY_DOPE
    player.current_round_grit_value = 3
    player.money = 20


def build_brawl_trigger(state: GameState, game_data: GameData) -> None:
    """First card of the Rissa chain (renamed from `build_brawl_card`,
    2026-09-26, once the Rissa lesson was split into its own sequence of
    tutorial cards — trigger/cards/reward/Gancio/relocation — sharing
    this one sandbox instead of each being its own throwaway game).

    A Rissa already underway in hood_q1, with the Hood actually
    holding the 5 Criminals that trigger one (`brawl_trigger_criminal_
    count`), one of them the human's own — the board has to *show* the
    situation the card is talking about (game designer, 2026-09-24: "non
    c'e' un quartiere effettivamente con 5 pedine, di cui almeno una
    rossa"). The human declares first; `card_007` (Artisti, 3 Guns)
    replaces whatever hand setup dealt, the same "just assign it"
    pattern test_brawl.py's own fixtures use, so the lesson always has
    an obviously-strong card to play."""
    player = _human(state)
    _ready_for_human(state)
    hood_id = HoodId("hood_q1")
    other_ids = [PlayerId(f"player_{i}") for i in (1, 2, 3)]
    hood = state.board.hoods[hood_id]

    # Cleared first, then refilled to *exactly* the trigger count: setup
    # already scatters a few Criminals into hood_q1 (how many, and whose,
    # depends on the seed), so appending blindly overfilled it past 5.
    for pawn_id in list(hood.criminal_pawn_ids):
        pawn = state.pawns[pawn_id]
        pawn.role = PawnRole.IN_BASE
        pawn.location = PawnLocation.base()
    hood.criminal_pawn_ids.clear()

    trigger_count = state.configuration["brawl_trigger_criminal_count"]
    # The human's own first, so a red pawn is always in the Rissa, then
    # one from each other player, cycling until the Hood is exactly full.
    owners = [PlayerId("player_0"), *other_ids]
    for i in range(trigger_count):
        owner = find_player(state, owners[i % len(owners)])
        pawn_id = _free_pawn(state, owner)
        pawn = state.pawns[pawn_id]
        pawn.role = PawnRole.CRIMINAL
        pawn.location = PawnLocation.hood(hood_id)
        hood.criminal_pawn_ids.append(pawn_id)

    state.pending_brawl = BrawlProgress(
        hood_id=hood_id,
        triggering_player_id=PlayerId("player_0"),
        participants=[PlayerId("player_0"), *other_ids],
        resume_player_id=PlayerId("player_0"),
    )
    state.active_step = ActiveStep.WAITING_FOR_BRAWL_CARD
    player.hand_card_ids = [CardId("card_007")]


def build_sell_dope(state: GameState, game_data: GameData) -> None:
    """One unit of every Dope type in the Covo, so whichever Contact the
    human's own Criminals happen to stand at always has something
    sellable at one of its Spots (setup's own starting inventory only
    covers 2 types, and which ones depends on the seed)."""
    player = _human(state)
    _ready_for_human(state)
    for dope_type in game_data.dope_types:
        player.base_inventory.dope_counts[dope_type] = 1
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = ActionType.SELL_DOPE
    player.current_round_grit_value = 1


def _place_cop_next_to_the_human(state: GameState) -> None:
    """A Cop in hood_q1, where one of the human's own Criminals already
    stands from setup — both officer lessons need a reachable target.
    Idempotent: the tutorial is one continuous game, so an earlier lesson
    may already have moved, arrested or bought this very Cop."""
    officer_id = OfficerId("officer_tutorial_cop")
    previous = state.board.officers.pop(officer_id, None)
    if previous is not None:
        for hood in state.board.hoods.values():
            if officer_id in hood.cop_ids:
                hood.cop_ids.remove(officer_id)
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.HOOD,
        hood_id=HoodId("hood_q1"),
    )
    state.board.hoods[HoodId("hood_q1")].cop_ids.append(officer_id)


def _place_fed_in_a_spot(state: GameState) -> None:
    """A Fed in spot_artisti_1 (same Contact as hood_q1), so the Cops-and-
    Feds card can show both kinds of officer — a Cop in a Hood, a Fed in a
    Spot. Idempotent for the same reason as the Cop above."""
    officer_id = OfficerId("officer_tutorial_fed")
    state.board.officers.pop(officer_id, None)
    for spot in state.board.spots.values():
        if officer_id in spot.fed_ids:
            spot.fed_ids.remove(officer_id)
    spot_id = SpotId("spot_artisti_1")
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.FED,
        location_type=OfficerLocationType.SPOT,
        spot_id=spot_id,
    )
    state.board.spots[spot_id].fed_ids.append(officer_id)


def build_corrupt_officer(state: GameState, game_data: GameData) -> None:
    player = _human(state)
    _ready_for_human(state)
    _place_cop_next_to_the_human(state)
    _place_fed_in_a_spot(state)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = ActionType.CORRUPT_OFFICER
    player.current_round_grit_value = 1
    player.money = 20


def build_buy_officer(state: GameState, game_data: GameData) -> None:
    player = _human(state)
    _ready_for_human(state)
    _place_cop_next_to_the_human(state)
    state.active_step = ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS
    player.pending_action_type = ActionType.BUY_OFFICER
    player.current_round_grit_value = 1
    player.money = 20


def build_intro(state: GameState, game_data: GameData) -> None:
    """First card of the opening chain (Ambientazione → Struttura Turni/
    Round → Obiettivo, tutorial_istruzioni.md Scene 1-3) — a plain ready
    state is enough, none of these 3 cards answers a decision."""
    build_grit(state, game_data)


def build_first_player_raid(state: GameState, game_data: GameData) -> None:
    """Primo Giocatore and the Retata's reveal, taught together because
    they're the *same* moment in the engine (`rules/turn_flow.py::
    start_tip_off`, corrected 2026-09-26 after the original tutorial
    spec wrongly described a highest-Gancio-of-any-Contact auto-pick):
    only whoever holds the highest Link at the Preti gets to *choose*
    the Turn's first player. Gives the human a level-2 Preti Link so
    they're that chooser, at `WAITING_FOR_RAID_RESOLUTION` with a real
    Retata card already revealed — specifically raid_04
    (most_poker_wins), so the card can show its own image and explain a
    concrete escape criterion instead of a generic "a Retata is
    revealed" (game designer, 2026-09-26)."""
    player = _human(state)
    pawn_id = _free_pawn(state, player)
    links.insert_link(state, player.player_id, pawn_id, ContactId("preti"), 2, [])
    state.phase = GamePhase.TIP_OFF
    state.current_player_id = PlayerId("player_0")
    state.active_step = ActiveStep.WAITING_FOR_RAID_RESOLUTION
    poker_raid = next(r for r in game_data.raids if r.escape_criterion == "most_poker_wins")
    state.raids.current_turn_card_id = poker_raid.raid_card_id


def build_criminal_states(state: GameState, game_data: GameData) -> None:
    """One pawn in each of the 4 roles a Criminal can end up in, all at
    once — Criminal (already in hood_q1 from setup), Link, Gambler, Rat
    — so a single board shows every one side by side
    (tutorial_istruzioni.md Scena 11)."""
    player = _human(state)
    _ready_for_human(state)
    _release_jail(state)

    link_pawn_id = _free_pawn(state, player)
    links.insert_link(state, player.player_id, link_pawn_id, ContactId("artisti"), 1, [])

    gambler_id = _free_pawn(state, player)
    gambler_pawn = state.pawns[gambler_id]
    gambler_pawn.role = PawnRole.GAMBLER
    gambler_pawn.location = PawnLocation.den()
    state.board.den_gambler_pawn_ids.append(gambler_id)

    jail.arrest_pawn(state, _free_pawn(state, player), [])


def build_jail_near_full(state: GameState, game_data: GameData) -> None:
    """3 of the Jail's 4 slots filled with one Rat from each other
    player — one more and Evasion triggers (tutorial_istruzioni.md
    Scena 29). `arrest_pawn` only handles the Jail side of the move
    (its own docstring) — the Hood's own `criminal_pawn_ids` entry has
    to be cleared here first, same as any other caller."""
    _ready_for_human(state)
    _release_jail(state)
    for i in (1, 2, 3):
        other = find_player(state, PlayerId(f"player_{i}"))
        pawn_id = next(
            (pid for pid in other.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL), None
        )
        if pawn_id is None:
            pawn_id = _free_pawn(state, other)
        else:
            hood_id = state.pawns[pawn_id].location.hood_id
            if hood_id is not None:
                state.board.hoods[hood_id].criminal_pawn_ids.remove(pawn_id)
        jail.arrest_pawn(state, pawn_id, [])


def build_jail_evasion_with_events(
    state: GameState, game_data: GameData, events: list[DomainEvent]
) -> None:
    """The 4th arrest itself, with its real events (the frontend replays the
    Evasion from them: the 4th Rat reaches the Jail, all four pulse, then
    one becomes a Politici Link and the others go home). Continues the
    previous lesson when the Jail already holds its 3 Rats; otherwise (a
    fresh game) sets that up first. The arrested pawn is the human's own
    Criminal on the map when there is one, so it visibly walks to the Jail."""
    player = _human(state)
    if sum(slot.rat_pawn_id is not None for slot in state.jail.slots) != 3:
        build_jail_near_full(state, game_data)
    on_map = next(
        (pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.CRIMINAL), None
    )
    if on_map is None:
        pawn_id = _free_pawn(state, player)
    else:
        pawn_id = on_map
        hood_id = state.pawns[pawn_id].location.hood_id
        if hood_id is not None:
            state.board.hoods[hood_id].criminal_pawn_ids.remove(pawn_id)
    jail.arrest_pawn(state, pawn_id, events)
    build_grit(state, game_data)


def build_jail_evasion(state: GameState, game_data: GameData) -> None:
    """Show the actual aftermath, including the triggering Rat's Politici Link."""
    build_jail_evasion_with_events(state, game_data, [])


def build_poker(state: GameState, game_data: GameData) -> None:
    """A real round-end match: bet, reveal a card, then show the normal recap."""
    _ready_for_human(state)
    _empty_den(state)
    state.first_player_id = PlayerId("player_0")
    gamble = next(c for c in game_data.customer_cards if c.contact_id == "preti")
    reveal_cards = [c for c in game_data.customer_cards if c.contact_id != "preti"]
    for i in (0, 1):
        player = find_player(state, PlayerId(f"player_{i}"))
        pawn_id = _free_pawn(state, player)
        pawn = state.pawns[pawn_id]
        pawn.role = PawnRole.GAMBLER
        pawn.location = PawnLocation.den()
        state.board.den_gambler_pawn_ids.append(pawn_id)
        player.hand_card_ids = [reveal_cards[i].card_id]
    state.poker.current_match = PokerMatchState(
        match_id="tutorial_poker",
        launched_by_player_id=PlayerId("player_0"),
        gamble_card_id=gamble.card_id,
        banco_symbols=gamble.banco_symbols,
    )
    poker.resolve_round_match(state, [])


def build_goal(state: GameState, game_data: GameData) -> None:
    """Info-only card (how points are scored): the frontend shows the
    board with markers and never answers a decision here, so any valid
    starting position works — the Grit pick is just a harmless one."""
    build_grit(state, game_data)


def build_job_reward(state: GameState, game_data: GameData) -> None:
    """job_02 ("own 1 Cop/Fed") revealed as the human's tier-1 Job, and a
    Cop to buy right next to their own Criminal — the purchase completes
    the Job, which then asks where on the REP grid to place the token
    (and so which of the 4 column bonuses to take). Completion is checked
    by the real post-command hook (`rules/jobs.py`), not faked here."""
    build_buy_officer(state, game_data)
    progress = state.jobs.progress_by_player[PlayerId("player_0")]
    progress.revealed_job_id_by_tier[1] = JobId("job_02")


def build_spend_link(state: GameState, game_data: GameData) -> None:
    """Gives the human a real Link (via `rules/links.py::insert_link`, so
    the Contact's own 3-slot track is updated exactly as a real sale
    would) and stops at the "spend it for an extra action?" offer."""
    player = _human(state)
    _ready_for_human(state)
    pawn_id = _free_pawn(state, player)
    links.insert_link(state, player.player_id, pawn_id, ContactId("artisti"), 1, [])
    state.active_step = ActiveStep.WAITING_FOR_LINK_EXTRA_ACTION
    player.extra_action_link_pawn_id = None
    player.money = 20


def build_hand_discard(state: GameState, game_data: GameData) -> None:
    """7 cards against `max_hand_size` 5, so the end-of-turn discard step
    asks for exactly 2 — enough to show the "pick several, then Conferma"
    shape rather than a single forced click."""
    player = _human(state)
    _ready_for_human(state)
    player.hand_card_ids = [CardId(f"card_{i:03d}") for i in range(1, 8)]
    state.active_step = ActiveStep.WAITING_FOR_HAND_DISCARD


TUTORIAL_SCENARIO_IDS = (
    "intro",
    "first_player_raid",
    "goal",
    "job_reward",
    "criminal_states",
    "grit",
    "place_criminal",
    "move_criminal",
    "buy_dope",
    "sell_dope",
    "corrupt_officer",
    "buy_officer",
    "spend_link",
    "brawl_trigger",
    "jail_near_full",
    "jail_evasion",
    "poker",
    "hand_discard",
)

_BUILDER_BY_SCENARIO_ID: dict[str, TutorialScenarioBuilder] = {
    "intro": build_intro,
    "first_player_raid": build_first_player_raid,
    "goal": build_goal,
    "job_reward": build_job_reward,
    "criminal_states": build_criminal_states,
    "grit": build_grit,
    "place_criminal": build_place_criminal,
    "move_criminal": build_move_criminal,
    "buy_dope": build_buy_dope,
    "sell_dope": build_sell_dope,
    "corrupt_officer": build_corrupt_officer,
    "buy_officer": build_buy_officer,
    "spend_link": build_spend_link,
    "brawl_trigger": build_brawl_trigger,
    "jail_near_full": build_jail_near_full,
    "jail_evasion": build_jail_evasion,
    "poker": build_poker,
    "hand_discard": build_hand_discard,
}


# Stages whose own change is worth replaying on screen: they hand back the
# domain events they produced (the others just patch the state silently).
_EVENT_BUILDER_BY_SCENARIO_ID: dict[
    str, Callable[[GameState, GameData, list[DomainEvent]], None]
] = {
    "jail_evasion": build_jail_evasion_with_events,
}


def build_tutorial_scenario(
    scenario_id: str, state: GameState, game_data: GameData
) -> list[DomainEvent]:
    """Applies one stage on top of the *current* state — the tutorial is a
    single running game, not one throwaway game per card. Returns the
    domain events the stage produced (empty for most). Raises KeyError for
    an unknown id — the HTTP adapter turns that into a 404, same as any
    other not-found resource."""
    builder = _BUILDER_BY_SCENARIO_ID[scenario_id]
    _reset_flow(state)
    events: list[DomainEvent] = []
    event_builder = _EVENT_BUILDER_BY_SCENARIO_ID.get(scenario_id)
    if event_builder is not None:
        event_builder(state, game_data, events)
    else:
        builder(state, game_data)
    return events
