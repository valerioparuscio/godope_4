"""Reversible UI choices. Never preview board actions or another player's turn."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dope_engine.application.command_bus import CommandFailure
from dope_engine.application.views import PlayerGameView
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.enums import ActionType
from dope_engine.domain.ids import PlayerId
from dope_engine.domain.state import GameState, find_player

if TYPE_CHECKING:
    from dope_engine.application.game_service import GameService


def is_preparatory_selection(state: GameState, selection: list[str]) -> bool:
    decision = state.pending_decision
    if decision is None:
        return False
    if decision.decision_type in {"choose_grit_action", "choose_action_type"}:
        return bool(selection)
    if selection or not decision.can_pass:
        return False
    if decision.decision_type in {
        "choose_marketing_card", "play_marketing_card", "launch_poker", "play_customer_card_boost",
    }:
        return True
    if decision.decision_type == "spend_link_for_extra_action":
        return not find_player(state, decision.player_id).extra_action_from_post_main
    return False


class PlanningError(Exception):
    """A staged path that cannot be previewed (illegal choice, too many steps)."""


@dataclass(frozen=True)
class OptionalPlan:
    kind: str
    view: PlayerGameView
    prefix: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class GritPlan:
    decision: PendingDecision | None
    prefix: tuple[tuple[str, ...], ...]
    # Grit value -> the action types offered once that Grit is chosen.
    action_options: dict[str, tuple[DecisionOption, ...]]


@dataclass(frozen=True)
class DecisionPlan:
    view: PlayerGameView
    prefix: list[list[str]]
    optional: list[OptionalPlan]
    grit: GritPlan | None
    selected_grit: int | None
    selected_action: ActionType | None


MAX_PREPARATORY_STEPS = 12


def build_decision_plan(
    service: GameService,
    state: GameState,
    player_id: PlayerId,
    selections: Sequence[Sequence[str]],
    *,
    view_for: Callable[[GameState], PlayerGameView],
) -> DecisionPlan:
    """Previews the player's preparatory choices (Grit, action type, optional Link / Marketing /
    Poker) on copies of the state: nothing is consumed, no event is stored, no revision moves,
    and only decisions that belong to `player_id` are ever crossed. `view_for` builds the
    player's view of a previewed state (the multiplayer routes hide future Jobs in it)."""
    working = state
    prefix: list[list[str]] = []
    optional: list[OptionalPlan] = []
    grit: GritPlan | None = None
    selected_grit: int | None = None

    def preview(current: GameState, selection: list[str]) -> GameState:
        try:
            result = service.answer_sequence(current, player_id, [selection], preview=True)
        except (KeyError, ValueError) as exc:
            raise PlanningError(str(exc)) from exc
        if isinstance(result, CommandFailure):
            raise PlanningError(result.error.message)
        return result.state

    # Every path is bounded, and can only cross preparatory decisions belonging to this human.
    for index in range(MAX_PREPARATORY_STEPS):
        pending = working.pending_decision
        if pending is None or pending.player_id != player_id:
            break
        kind = pending.decision_type
        player = find_player(working, player_id)
        optional_kind = None
        if kind == "spend_link_for_extra_action":
            optional_kind = "link"
        elif kind == "launch_poker":
            optional_kind = "poker"
        elif kind in {"choose_marketing_card", "play_marketing_card"} and (
            player.marketing_chosen_card_id is None
        ):
            optional_kind = "marketing"
        if optional_kind and pending.options:
            optional.append(
                OptionalPlan(
                    kind=optional_kind,
                    view=view_for(working),
                    prefix=tuple(tuple(step) for step in prefix),
                )
            )
        if kind == "choose_grit_action":
            action_options: dict[str, tuple[DecisionOption, ...]] = {}
            for option in pending.options:
                after_grit = preview(working, [option.option_id])
                next_decision = view_for(after_grit).pending_decision
                action_options[str(option.payload["grit_value"])] = (
                    tuple(next_decision.options)
                    if next_decision and next_decision.decision_type == "choose_action_type"
                    else ()
                )
            grit = GritPlan(
                decision=view_for(working).pending_decision,
                prefix=tuple(tuple(step) for step in prefix),
                action_options=action_options,
            )
        if index < len(selections):
            selection = list(selections[index])
            if kind == "choose_grit_action" and selection:
                selected_grit = next(
                    (
                        o.payload["grit_value"]
                        for o in pending.options
                        if o.option_id == selection[0]
                    ),
                    None,
                )
        elif optional_kind and is_preparatory_selection(working, []):
            selection = []
        else:
            break
        working = preview(working, selection)
        prefix.append(selection)
    else:
        raise PlanningError("Too many preparatory choices")
    if len(prefix) < len(selections):
        raise PlanningError("Invalid preparatory path")
    planning_player = find_player(working, player_id)
    return DecisionPlan(
        view=view_for(working),
        prefix=prefix,
        optional=optional,
        grit=grit,
        selected_grit=selected_grit,
        selected_action=planning_player.pending_action_type,
    )
