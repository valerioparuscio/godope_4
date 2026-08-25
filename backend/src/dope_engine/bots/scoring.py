"""Simple, view-computable heuristics for `bots/policies.py::HeuristicBot`
("basi per bot più intelligenti", 2026-08-25). Deliberately modest — see
CLAUDE.md §14.3, which explicitly allows "euristiche modulari" for a
first pass without requiring look-ahead/Monte Carlo yet:

- **Buy cheap, sell high**: `buy_dope` already prefers cheaper price by
  default in `option_picking.py`, now explicit as a score;
  `sell_dope` gets a real preference for higher price for the first time
  (RandomLegalBot never ordered by it at all).
- **Avoid triggering a disadvantageous Rissa**: `move_criminal` into a
  Hood already at `capacity - 1` Criminals would be the 5th, triggering a
  Brawl (RULES_CANONICAL.md §D1) — penalized. `place_criminal` can never
  itself reach that count (`legal_actions.py::_place_criminal_options`
  already caps it at `brawl_trigger_criminal_count - 1`), so this term
  doesn't apply there.
- **Reinforce a Contact's majority**: a small bonus toward a Contact
  where this player already has strictly more presence (Criminals in its
  Hoods + Links) than every other player — reinforces end-game §D6
  Contact-majority points.

Explicitly out of scope for this first pass: scoring `choose_action_type`
or Grit-value selection (stays uniform-random, same as RandomLegalBot —
see policies.py's own docstring), and anything needing data outside
`PlayerGameView`/`PendingDecision` (e.g. a Job's actual requirement
predicate, which only exists server-side in `GameData`/`data/jobs.json`,
never in the per-player view — CLAUDE.md §12 keeps it that way
deliberately, and widening `BotPolicy.choose`'s inputs to reach it is a
larger interface change than "the basis" calls for).
"""

from __future__ import annotations

from dataclasses import dataclass

from dope_engine.application.views import PlayerGameView
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.enums import PawnRole


@dataclass(frozen=True)
class HeuristicWeights:
    """Tunable knobs — the hook for future "personality profiles"
    (CLAUDE.md §14.3) without building more than one concrete personality
    yet. All defaults are a first, unvalidated guess: real tuning is
    future playtesting work, not part of this basis."""

    price_weight: float = 1.0
    rissa_avoidance_penalty: float = 5.0
    majority_bonus: float = 2.0


DEFAULT_WEIGHTS = HeuristicWeights()


def _hood_contact_id(view: PlayerGameView, hood_id: str) -> str | None:
    return next((h.contact_id for h in view.hoods if h.hood_id == hood_id), None)


def _spot_contact_id(view: PlayerGameView, spot_id: str) -> str | None:
    return next((s.contact_id for s in view.spots if s.spot_id == spot_id), None)


def _own_presence_by_contact(view: PlayerGameView) -> dict[str, dict[str, int]]:
    """player_id -> contact_id -> presence count. Recomputed fresh per
    `score_option` call rather than cached — cheap enough at this game's
    scale (10 Hoods, at most a few dozen pawns total) that caching would
    only add complexity for no measurable benefit."""
    hood_contact = {h.hood_id: h.contact_id for h in view.hoods}
    presence: dict[str, dict[str, int]] = {}
    for pawn in view.pawns:
        contact_id = None
        if pawn.role == PawnRole.CRIMINAL and pawn.hood_id is not None:
            contact_id = hood_contact.get(pawn.hood_id)
        elif pawn.role == PawnRole.LINK:
            contact_id = pawn.contact_id
        if contact_id is None:
            continue
        by_contact = presence.setdefault(pawn.owner_player_id, {})
        by_contact[contact_id] = by_contact.get(contact_id, 0) + 1
    return presence


def _has_strict_majority(
    presence: dict[str, dict[str, int]], player_id: str, contact_id: str
) -> bool:
    own = presence.get(player_id, {}).get(contact_id, 0)
    if own == 0:
        return False
    return all(
        presence.get(other, {}).get(contact_id, 0) < own for other in presence if other != player_id
    )


def score_option(
    option: DecisionOption,
    decision: PendingDecision,
    view: PlayerGameView,
    weights: HeuristicWeights = DEFAULT_WEIGHTS,
) -> float:
    """Higher is better. See module docstring for the 3 heuristics and
    what's deliberately left out."""
    payload = option.payload
    player_id = decision.player_id
    score = 0.0
    contact_id: str | None = None

    if decision.decision_type == "buy_dope":
        score -= weights.price_weight * payload["price"]
        contact_id = _hood_contact_id(view, payload["hood_id"])
    elif decision.decision_type == "sell_dope":
        price = view.current_price_by_dope_type.get(payload["dope_type"])
        if price is not None:
            score += weights.price_weight * price
        contact_id = _spot_contact_id(view, payload["spot_id"])
    elif decision.decision_type == "place_criminal":
        contact_id = _hood_contact_id(view, payload["hood_id"])
    elif decision.decision_type == "move_criminal":
        destination_id = payload["destination_hood_id"]
        contact_id = _hood_contact_id(view, destination_id)
        hood = next((h for h in view.hoods if h.hood_id == destination_id), None)
        if hood is not None and len(hood.criminal_pawn_ids) >= hood.capacity - 1:
            score -= weights.rissa_avoidance_penalty
    elif decision.decision_type == "corrupt_officer":
        officer = next((o for o in view.officers if o.officer_id == payload["officer_id"]), None)
        if officer is not None:
            if officer.hood_id is not None:
                contact_id = _hood_contact_id(view, officer.hood_id)
            elif officer.spot_id is not None:
                contact_id = _spot_contact_id(view, officer.spot_id)

    if contact_id is not None:
        presence = _own_presence_by_contact(view)
        if _has_strict_majority(presence, player_id, contact_id):
            score += weights.majority_bonus

    return score
