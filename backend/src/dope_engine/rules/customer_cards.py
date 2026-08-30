"""Customer Card boosts (game designer, 2026-08-27): playing a hand card
whose own printed `action_type` matches the round's just-committed
action applies that card's `data/customer_cards.json::effect` to this
one action instance, then discards the card — a third way to spend a
hand card alongside Marketing (Stonk symbols) and a Poker launch (Preti
Gamble cards), all three reading the *same* card differently depending
on which offer the player accepts.

Offered right after `ChooseActionType`
(`ActiveStep.WAITING_FOR_CARD_BOOST`), chained *after* both the
Poker-launch and Marketing offers if the player is eligible for more
than one this round (same "each is independently declinable, in a fixed
order" shape those two already use — see
`rules/economy.py::_handle_choose_action_type`,
`rules/turn_flow.py::resume_after_poker_launch_offer`, and
`rules/economy.py::_handle_play_marketing_card`/
`rules/turn_flow.py::_handle_pass_optional_step`'s Marketing-decline
branch, all three of which call `offer_boost_or_resume` below instead of
resuming directly).

A card's `effect` is `None` for every Gamble (Preti) card and for any
card whose effect isn't implemented yet (`docs/rules/RULES_PENDING.md`)
— such a card is simply never boost-eligible, same as a card with no
Stonk symbols is never Marketing-eligible.

Only the effect *types* that fold into `rules/skills.py::_effects_of_type`
(`cost_delta`, `extra_grit`, `trade_price_delta` — a played boost is
mechanically just a one-shot, one-action Skill, see that module) need no
code here beyond stashing `PlayerState.active_card_boost`. The other
Tier-1 types (`price_at_extreme`, `pre_action_restock`,
`pre_action_clear_spot`, `extra_price_step`, `bonus_card_draw_per_unit`)
are read directly off `active_card_boost` by the one handler that
actually needs them (`rules/economy.py`'s Buy/Sell/Place handlers).
"""

from __future__ import annotations

from dope_engine.application.command_bus import (
    CommandBus,
    CommandFailure,
    CommandOutcome,
    CommandSuccess,
)
from dope_engine.domain.commands import PlayCustomerCardBoost
from dope_engine.domain.enums import ActionType, ActiveStep, GamePhase
from dope_engine.domain.errors import DomainError, wrong_phase, wrong_player
from dope_engine.domain.events import CustomerCardBoostPlayed, DomainEvent
from dope_engine.domain.ids import CardId, ContactId
from dope_engine.domain.state import GameState, PlayerState, find_player
from dope_engine.rules.event_utils import emit as _emit


def can_play_boost_for_action(
    state: GameState,
    player: PlayerState,
    action_type: ActionType,
    card_effect_by_id: dict[CardId, dict | None],
    action_type_by_card_id: dict[CardId, ActionType | None],
) -> bool:
    return any(
        card_effect_by_id.get(card_id) is not None
        and action_type_by_card_id.get(card_id) == action_type
        for card_id in player.hand_card_ids
    )


def offer_boost_or_resume(
    state: GameState,
    player: PlayerState,
    return_step: ActiveStep,
    card_effect_by_id: dict[CardId, dict | None],
    action_type_by_card_id: dict[CardId, ActionType | None],
) -> None:
    """Shared tail for every point a Poker-launch or Marketing offer can
    finish resolving (accepted or declined): offers a Card Boost next if
    the player still has one to offer for this round's own
    `pending_action_type`, else resumes `return_step` directly. Also
    called from `_handle_choose_action_type` itself, for a player
    eligible for a Boost but neither of the other two."""
    action_type = player.pending_action_type
    if action_type is not None and can_play_boost_for_action(
        state, player, action_type, card_effect_by_id, action_type_by_card_id
    ):
        player.card_boost_return_step = return_step
        state.active_step = ActiveStep.WAITING_FOR_CARD_BOOST
    else:
        state.active_step = return_step


def _handle_play_customer_card_boost(
    state: GameState,
    command: PlayCustomerCardBoost,
    card_effect_by_id: dict[CardId, dict | None],
    action_type_by_card_id: dict[CardId, ActionType | None],
    card_contact_by_id: dict[CardId, ContactId],
) -> CommandOutcome:
    if state.phase != GamePhase.ACTION_PHASE:
        return CommandFailure(wrong_phase(GamePhase.ACTION_PHASE.value, state.phase.value))
    if state.current_player_id != command.player_id:
        return CommandFailure(wrong_player(str(state.current_player_id), str(command.player_id)))
    if state.active_step != ActiveStep.WAITING_FOR_CARD_BOOST:
        return CommandFailure(
            DomainError(
                code="wrong_active_step",
                message=f"Not waiting for a Card Boost (state is at '{state.active_step.value}').",
                details={"actual_step": state.active_step.value},
            )
        )

    player = find_player(state, command.player_id)
    effect = card_effect_by_id.get(command.card_id)
    action_type = player.pending_action_type
    if (
        command.card_id not in player.hand_card_ids
        or effect is None
        or action_type is None
        or action_type_by_card_id.get(command.card_id) != action_type
    ):
        return CommandFailure(
            DomainError(
                code="card_not_eligible_for_boost",
                message=f"Card '{command.card_id}' has no boost for this action, or isn't in hand.",
                details={},
            )
        )

    state.revision += 1
    events: list[DomainEvent] = []

    player.hand_card_ids.remove(command.card_id)
    contact_id = card_contact_by_id[command.card_id]
    state.decks.customer_decks_by_contact[contact_id].discard_pile_card_ids.append(command.card_id)
    # `cost_delta`/`extra_grit` piggyback on `skills.py`'s Skill-effect
    # machinery, which keys `action_types` on the effect dict — a printed
    # card only ever boosts its own action, so inject it here rather than
    # duplicating it in every wave-1 JSON entry. Harmless for the other
    # effect types, which never read that key.
    player.active_card_boost = {**effect, "action_types": [action_type.value]}
    _emit(
        state,
        events,
        CustomerCardBoostPlayed,
        player_id=command.player_id,
        card_id=command.card_id,
        action_type=action_type.value,
        effect_type=effect["type"],
    )

    return_step = player.card_boost_return_step
    assert return_step is not None
    player.card_boost_return_step = None
    state.active_step = return_step

    state.event_log_cursor += len(events)
    return CommandSuccess(state=state, events=tuple(events))


def register_handlers(
    bus: CommandBus,
    *,
    card_effect_by_id: dict[CardId, dict | None],
    action_type_by_card_id: dict[CardId, ActionType | None],
    card_contact_by_id: dict[CardId, ContactId],
) -> None:
    bus.register(
        PlayCustomerCardBoost,
        lambda s, c: _handle_play_customer_card_boost(
            s, c, card_effect_by_id, action_type_by_card_id, card_contact_by_id
        ),
    )
