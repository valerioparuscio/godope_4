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
inside a special event (`brawl_card`).

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
from dope_engine.domain.ids import CardId, ContactId, HoodId, OfficerId, PlayerId
from dope_engine.domain.state import BrawlProgress, GameState, find_player
from dope_engine.rules import links

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
    (`data/board.json`) — and `create_initial_state` already stands one
    of the human's own Criminals in hood_q1, so no manual pawn placement
    is needed, only the decision itself. The other 2 Criminals setup
    hands out (own_dope_in_base gives every player 3 of them, in 3
    different Hoods) are sent back to the Covo here — with all 3 still
    on the board, this decision offers ~7 destinations per pawn across
    3 movable pawns at once, correct but too busy for a single clean
    "click the pawn, then its destination" lesson."""
    player = _human(state)
    _ready_for_human(state)
    for pawn_id in player.pawn_ids:
        pawn = state.pawns[pawn_id]
        hood_id = pawn.location.hood_id
        if pawn.role == PawnRole.CRIMINAL and hood_id is not None and hood_id != "hood_q1":
            state.board.hoods[hood_id].criminal_pawn_ids.remove(pawn_id)
            pawn.role = PawnRole.IN_BASE
            pawn.location = PawnLocation.base()
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


def build_brawl_card(state: GameState, game_data: GameData) -> None:
    """A Rissa already underway in hood_q1, with the Hood actually
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
        pawn_id = next(pid for pid in owner.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
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
    stands from setup — both officer lessons need a reachable target."""
    officer_id = OfficerId("officer_tutorial_cop")
    state.board.officers[officer_id] = OfficerState(
        officer_id=officer_id,
        officer_type=OfficerType.COP,
        location_type=OfficerLocationType.HOOD,
        hood_id=HoodId("hood_q1"),
    )
    state.board.hoods[HoodId("hood_q1")].cop_ids.append(officer_id)


def build_corrupt_officer(state: GameState, game_data: GameData) -> None:
    player = _human(state)
    _ready_for_human(state)
    _place_cop_next_to_the_human(state)
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


def build_spend_link(state: GameState, game_data: GameData) -> None:
    """Gives the human a real Link (via `rules/links.py::insert_link`, so
    the Contact's own 3-slot track is updated exactly as a real sale
    would) and stops at the "spend it for an extra action?" offer."""
    player = _human(state)
    _ready_for_human(state)
    pawn_id = next(pid for pid in player.pawn_ids if state.pawns[pid].role == PawnRole.IN_BASE)
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
    "grit",
    "place_criminal",
    "move_criminal",
    "buy_dope",
    "sell_dope",
    "corrupt_officer",
    "buy_officer",
    "spend_link",
    "brawl_card",
    "hand_discard",
)

_BUILDER_BY_SCENARIO_ID: dict[str, TutorialScenarioBuilder] = {
    "grit": build_grit,
    "place_criminal": build_place_criminal,
    "move_criminal": build_move_criminal,
    "buy_dope": build_buy_dope,
    "sell_dope": build_sell_dope,
    "corrupt_officer": build_corrupt_officer,
    "buy_officer": build_buy_officer,
    "spend_link": build_spend_link,
    "brawl_card": build_brawl_card,
    "hand_discard": build_hand_discard,
}


def build_tutorial_scenario(scenario_id: str, state: GameState, game_data: GameData) -> None:
    """Raises KeyError for an unknown id — the HTTP adapter turns that
    into a 404, same as any other not-found resource."""
    _BUILDER_BY_SCENARIO_ID[scenario_id](state, game_data)
