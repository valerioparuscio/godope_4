"""Simple, view-computable heuristics for `bots/policies.py::HeuristicBot`
("basi per bot più intelligenti", 2026-08-25; extended 2026-09-18 —
"ragioniamo sul rendere piu intelligenti i bot", game designer). Deliberately
modest — see CLAUDE.md §14.3, which explicitly allows "euristiche modulari"
for a first pass without requiring look-ahead/Monte Carlo yet:

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
- **Progress a revealed Job** (2026-09-18): a bonus toward whichever of
  the player's own currently-revealed Jobs (§A10) this option's action
  type can help satisfy — e.g. buying a Dope type the Covo doesn't hold
  yet toward "Abbi 4 Dope (almeno una per tipo)", moving/placing into a
  Hood with no existing presence toward "Criminali in 6 Hoods diversi".
  Only the requirement types reachable from buy_dope/sell_dope/
  move_criminal/place_criminal are covered — win_brawls/own_rats/
  own_poker_chips/own_officers aren't things a single option can
  meaningfully aim at (see `_job_progress_bonus`'s own docstring).
- **Mind the active Retata, mildly** (2026-09-18): a small nudge (well
  under the Job bonus — "attenti, ma non ossessionati", game designer)
  toward this turn's raid escape criterion where it overlaps with an
  already-scored action type — e.g. `least_dope_value` penalizes buying
  and rewards selling.

This is the one heuristic set that genuinely needs data beyond
`PlayerGameView`/`PendingDecision` — a Job's/Raid's own requirement
content, which only exists server-side in `GameData`/`data/jobs.json`
and `data/raids.json`. Threaded in as `job_by_id`/`raid_by_id` (optional,
default `None` → those two bonuses simply don't apply, so any existing
caller of `score_option` without them keeps working unchanged) rather
than widening `BotPolicy.choose`'s own signature — Job/Raid content is
public/common knowledge (`PublicJobProgressView`'s own docstring), so
handing a bot's *scoring* function a read-only copy of it isn't the
same as leaking hidden information the way widening `choose()` itself
to read raw `GameData` more broadly would risk elsewhere.

Explicitly still out of scope: scoring `choose_action_type` or Grit-value
selection (stays uniform-random, same as RandomLegalBot — see
policies.py's own docstring) — comparing hypothetical outcomes *across*
action types is closer to real look-ahead than option-scoring within one
already-chosen type.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from dope_engine.application.views import PlayerGameView
from dope_engine.domain.content import JobDefinition, RaidCardDefinition
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.enums import PawnRole
from dope_engine.domain.ids import JobId, PlayerId, RaidCardId


@dataclass(frozen=True)
class HeuristicWeights:
    """Tunable knobs — the hook for future "personality profiles"
    (CLAUDE.md §14.3) without building more than one concrete personality
    yet. All defaults are a first, unvalidated guess: real tuning is
    future playtesting work, not part of this basis."""

    price_weight: float = 1.0
    rissa_avoidance_penalty: float = 5.0
    majority_bonus: float = 2.0
    job_progress_bonus: float = 3.0
    # Deliberately smaller than job_progress_bonus — a Retata is a single
    # turn's swing, a Job is permanent REP; "attenti, ma non ossessionati".
    raid_criterion_bonus: float = 1.0


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


def _find_player_view(view: PlayerGameView, player_id: PlayerId):  # noqa: ANN201
    return next(p for p in view.players if p.player_id == player_id)


def _own_criminal_hood_ids(view: PlayerGameView, player_id: PlayerId) -> set[str]:
    return {
        pawn.hood_id
        for pawn in view.pawns
        if pawn.owner_player_id == player_id
        and pawn.role == PawnRole.CRIMINAL
        and pawn.hood_id is not None
    }


def _own_link_count(view: PlayerGameView, player_id: PlayerId) -> int:
    return sum(
        1 for pawn in view.pawns if pawn.owner_player_id == player_id and pawn.role == PawnRole.LINK
    )


def _own_criminals_out_of_base_count(view: PlayerGameView, player_id: PlayerId) -> int:
    return sum(
        1
        for pawn in view.pawns
        if pawn.owner_player_id == player_id and pawn.role != PawnRole.IN_BASE
    )


def _revealed_job_ids(view: PlayerGameView, player_id: PlayerId) -> list[JobId]:
    progress = view.job_progress_by_player.get(player_id)
    if progress is None:
        return []
    return [job_id for job_id in progress.revealed_job_id_by_tier.values() if job_id is not None]


def _job_progress_bonus(
    decision: PendingDecision,
    payload: Mapping[str, Any],
    view: PlayerGameView,
    player_id: PlayerId,
    job_by_id: dict[JobId, JobDefinition] | None,
    weight: float,
) -> float:
    """A bonus toward whichever of the player's revealed Jobs this
    option's action type could plausibly help — only the requirement
    types a single buy_dope/sell_dope/move_criminal/place_criminal
    option can meaningfully move (own_dope_in_base,
    criminals_in_distinct_hoods, criminals_out_of_base, own_links,
    own_money). win_brawls/own_rats/own_poker_chips/own_officers aren't
    decided by picking among this option set — winning a Rissa/getting
    arrested/a Poker outcome isn't a choice made here, and own_officers
    needs buy_officer, not yet one of HeuristicBot's scored decision
    types (see module docstring)."""
    if not job_by_id:
        return 0.0
    own_player = _find_player_view(view, player_id)
    bonus = 0.0
    for job_id in _revealed_job_ids(view, player_id):
        job = job_by_id.get(job_id)
        if job is None:
            continue
        requirement = job.requirement
        req_type = requirement.get("type")
        count = requirement.get("count", 0)

        if req_type == "own_dope_in_base" and decision.decision_type == "buy_dope":
            held = own_player.base_inventory.dope_counts.get(payload["dope_type"], 0)
            total_held = sum(own_player.base_inventory.dope_counts.values())
            if total_held < count:
                # Extra weight for a type the Covo doesn't hold at all yet
                # — "almeno una per tipo" makes diversity worth more than
                # a 2nd/3rd unit of one already held.
                bonus += weight * (2.0 if held == 0 else 1.0)

        elif req_type == "criminals_in_distinct_hoods" and decision.decision_type in (
            "move_criminal",
            "place_criminal",
        ):
            hood_id = payload.get("destination_hood_id") or payload.get("hood_id")
            own_hoods = _own_criminal_hood_ids(view, player_id)
            if hood_id is not None and hood_id not in own_hoods and len(own_hoods) < count:
                bonus += weight

        elif req_type == "criminals_out_of_base" and decision.decision_type == "place_criminal":
            if _own_criminals_out_of_base_count(view, player_id) < count:
                bonus += weight

        elif req_type == "own_links" and decision.decision_type == "sell_dope":
            # A sale merely *offers* a Link evolution (or grants one
            # automatically on a package) — not guaranteed — so this is
            # a softer nudge than the others, same weight regardless.
            if _own_link_count(view, player_id) < count:
                bonus += weight

        elif req_type == "own_money" and decision.decision_type == "sell_dope":
            if own_player.money < count:
                bonus += weight

    return bonus


def _raid_criterion_bonus(
    decision: PendingDecision,
    payload: Mapping[str, Any],
    view: PlayerGameView,
    player_id: PlayerId,
    raid_by_id: dict[RaidCardId, RaidCardDefinition] | None,
    weight: float,
) -> float:
    """A small nudge toward this turn's Retata escape criterion, only
    where it overlaps with an already-scored action type — deliberately
    thin, see `HeuristicWeights.raid_criterion_bonus`'s own comment."""
    if not raid_by_id or view.raid_card_id is None:
        return 0.0
    raid = raid_by_id.get(view.raid_card_id)
    if raid is None:
        return 0.0
    criterion = raid.escape_criterion

    if criterion == "least_dope_value":
        if decision.decision_type == "buy_dope":
            return -weight
        if decision.decision_type == "sell_dope":
            return weight
    elif (
        criterion in ("most_money", "most_links_with_contacts")
        and decision.decision_type == "sell_dope"
    ):
        return weight
    elif criterion == "most_criminals_in_hoods" and decision.decision_type in (
        "move_criminal",
        "place_criminal",
    ):
        hood_id = payload.get("destination_hood_id") or payload.get("hood_id")
        own_hoods = _own_criminal_hood_ids(view, player_id)
        if hood_id is not None and hood_id not in own_hoods:
            return weight

    return 0.0


def score_option(
    option: DecisionOption,
    decision: PendingDecision,
    view: PlayerGameView,
    weights: HeuristicWeights = DEFAULT_WEIGHTS,
    *,
    job_by_id: dict[JobId, JobDefinition] | None = None,
    raid_by_id: dict[RaidCardId, RaidCardDefinition] | None = None,
) -> float:
    """Higher is better. See module docstring for the heuristics and what's
    deliberately left out. `job_by_id`/`raid_by_id` are optional — omitting
    them (any existing caller) just skips those two bonus terms."""
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

    score += _job_progress_bonus(
        decision, payload, view, player_id, job_by_id, weights.job_progress_bonus
    )
    score += _raid_criterion_bonus(
        decision, payload, view, player_id, raid_by_id, weights.raid_criterion_bonus
    )

    return score
