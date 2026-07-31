"""The single source of legal decisions (CLAUDE.md section 10): human
frontend, bots, tests and debug tools all call `get_legal_decision`
instead of reconstructing options on their own.

`build_command_from_selection` is the matching inverse — turning a
chosen option (or set of options, for multi-select decisions) back into
the concrete `Command` the command bus expects — shared by bots and by
the HTTP layer so there is exactly one place that knows how a
decision_type maps to a command type.
"""

from __future__ import annotations

from dope_engine.application.views import PlayerGameView
from dope_engine.domain.commands import ChooseGritAction, Command, DiscardCards, PassOptionalStep
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.enums import ActiveStep, GamePhase
from dope_engine.domain.ids import DecisionId, PlayerId
from dope_engine.domain.state import GameState, find_player


def get_legal_decision(state: GameState, player_id: PlayerId) -> PendingDecision | None:
    if state.phase != GamePhase.ACTION_PHASE or state.current_player_id != player_id:
        return None

    decision_id = DecisionId(f"decision_{state.revision:04d}")
    player = find_player(state, player_id)

    if state.active_step == ActiveStep.WAITING_FOR_GRIT_ACTION:
        options = tuple(
            DecisionOption(
                option_id=f"grit_{value}",
                label_key="decision.choose_grit_action.option",
                payload={"grit_value": value},
            )
            for value in sorted(player.available_grit_values)
        )
        return PendingDecision(
            decision_id=decision_id,
            player_id=player_id,
            decision_type="choose_grit_action",
            prompt_key="decision.choose_grit_action.prompt",
            options=options,
            min_selections=1,
            max_selections=1,
            can_pass=False,
        )

    if state.active_step == ActiveStep.WAITING_FOR_MAIN_ACTION_TARGETS:
        # Milestone 1: no economic action (§C1-C6) exists yet, so passing
        # is the only legal move. Milestone 2 replaces this with real
        # per-action-type options.
        return PendingDecision(
            decision_id=decision_id,
            player_id=player_id,
            decision_type="main_action_targets",
            prompt_key="decision.main_action_targets.prompt",
            options=(),
            min_selections=0,
            max_selections=0,
            can_pass=True,
        )

    if state.active_step == ActiveStep.WAITING_FOR_HAND_DISCARD:
        overflow = len(player.hand_card_ids) - state.configuration["max_hand_size"]
        options = tuple(
            DecisionOption(
                option_id=f"discard_{card_id}",
                label_key="decision.hand_discard.option",
                payload={"card_id": card_id},
            )
            for card_id in player.hand_card_ids
        )
        return PendingDecision(
            decision_id=decision_id,
            player_id=player_id,
            decision_type="hand_discard",
            prompt_key="decision.hand_discard.prompt",
            options=options,
            min_selections=overflow,
            max_selections=overflow,
            can_pass=False,
        )

    return None


def build_command_from_selection(
    view: PlayerGameView,
    decision: PendingDecision,
    selected_option_ids: tuple[str, ...],
) -> Command:
    game_id = view.game_id
    player_id = decision.player_id
    expected_revision = view.revision
    decision_id = decision.decision_id
    options_by_id = {option.option_id: option for option in decision.options}

    if decision.decision_type == "choose_grit_action":
        (option_id,) = selected_option_ids
        return ChooseGritAction(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            grit_value=options_by_id[option_id].payload["grit_value"],
        )

    if decision.decision_type == "main_action_targets":
        return PassOptionalStep(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
        )

    if decision.decision_type == "hand_discard":
        card_ids = tuple(options_by_id[oid].payload["card_id"] for oid in selected_option_ids)
        return DiscardCards(
            game_id=game_id,
            player_id=player_id,
            expected_revision=expected_revision,
            decision_id=decision_id,
            card_ids=card_ids,
        )

    raise ValueError(f"Unknown decision_type '{decision.decision_type}'")
