"""Reversible UI choices. Never preview board actions or another player's turn."""

from dope_engine.domain.state import GameState, find_player


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
