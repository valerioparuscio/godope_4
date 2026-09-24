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

- **Choose the action *type* itself, not just its targets** (2026-09-23,
  game designer: "mi sembra che facciano ancora poco per vincere...
  focalizzare ancora di piu le loro azioni per il raggiungimento dei
  loro jobs attivi" — score gap of ~25 vs 4-5 points observed against a
  human): the dominant lever this bot was still missing. Scoring targets
  well within an already-chosen action type is close to useless if the
  type itself is picked uniformly at random 5 rounds out of 6 — a bot
  could have the perfect Job sitting in front of it and still spend most
  of the game ignoring the one action type that would advance it.
  `score_action_type` reuses the exact same "which requirement types does
  this action type help" mapping the per-option bonus above uses,
  applied to the 6 `choose_action_type` options directly: summing over
  *every* revealed, still-unmet Job it could plausibly help (so a type
  useful to 2 Jobs at once naturally outscores one useful to only 1 —
  "sciegliendo azioni che sono utili per piu di un job attivo
  contemporaneamente", designer's own suggestion) plus the active
  Retata's escape criterion. Deliberately does *not* try to steer toward
  deliberately triggering/winning a Rissa for its Link payout (own_links
  already biases toward `sell_dope`, a safe path with no chance of
  losing the pawn/cards a lost Rissa would cost) — see the function's own
  docstring for the full reasoning.

- **Commit to one Job across turns, not a little of everything at once**
  (2026-09-23, game designer: "un job raramente viene raggiunto con una
  sola azione, anche se di grinta 3... forse è necessario avere un
  minimo di visione dei 2 o 3 turni successivi"). A 100-game all-
  heuristic sweep after the `score_action_type` addition above showed
  *why* that fix alone wasn't enough: bots complete under 1 Job per
  game on average (45% finish with zero), because spreading a flat
  bonus evenly across every revealed Job never lets any single one's
  requirement actually close before the game ends. Real multi-turn
  look-ahead (simulating hypothetical futures) is out of scope — too
  expensive, explicitly deferred by CLAUDE.md §14.3. `_committed_job_id`
  gets nearly the same effect much more cheaply: recomputed fresh from
  *live* progress on every call (no memory needed), it picks whichever
  currently-revealed Job the player is proportionally closest to
  finishing and gives it a strictly bigger bonus
  (`committed_job_bonus`) than any other revealed Job still gets
  (`job_progress_bonus`, unchanged, preserving the original "useful to
  more than one Job" tiebreak). Since progress only grows while a Job
  stays revealed, "closest right now" stays the same Job call to call
  in practice — multi-turn-consistent focus without actually being
  stateful.
- **Spend a Link for an extra action *toward* that commitment**
  (2026-09-23, same request: "magari prendendo il link giusto per poter
  ripetere un'azione già fatta nel turno"). `spend_link_for_extra_action`
  used to fall through to a plain coinflip (`rng.randint(0, 1)` on
  whether to act at all) — unlike the "always take it" decisions in
  `policies.py::_ALWAYS_MAX_DECISION_TYPES`, spending a Link isn't a
  free action: it permanently demotes that Link back to a plain Covo
  pawn (`rules/turn_flow.py::_handle_spend_link_for_extra_action`,
  §A5), so it stops counting toward Contact majority *and* toward any
  revealed Job's `own_links` requirement. `score_spend_link_for_extra_
  action_option` weighs the best action type that Link's Contact would
  unlock (`score_action_type`, so it inherits the same committed-Job
  focus) against that opportunity cost, and only recommends spending
  when the former outweighs the latter.
- **Bug found while measuring the above**: `own_dope_in_base` completion
  was checked as a flat "total units >= count", ignoring the
  `at_least_one_per_type` flag `rules/jobs.py::_check_requirement`
  actually enforces for job_05 — a bot hitting 4 units of a *single*
  Dope type looked "done" to the heuristic and silently stopped
  pursuing a Job it had never actually finished. Fixed in
  `_job_unmet_and_ratio`, the one place all three functions above now
  read progress/completion from.

- **Deliberately trigger a Rissa/reveal a strong Poker card when a Job
  needs it** (2026-09-23, game designer: "rissa with at least 2 guns in
  the cards, or poker with at least a card to get a couple or a tris
  must be played if needed for jobs" — the direct follow-up to the
  structural ceiling above: `win_brawls`/`own_poker_chips` are 2 of the
  3 revealed Jobs a bot could never actively work toward at all).
  `move_criminal` into a crowded Hood (the 5th-Criminal Rissa trigger)
  still costs `rissa_avoidance_penalty` by default, *unless* a
  `win_brawls` Job is currently revealed (still revealed = still unmet,
  a completed one gets replaced) *and* the hand holds a card with 2+
  Guns (`_has_strong_brawl_card`) — the bar the designer set for when
  the real risk (money/cards/a pawn) is worth it, not "any Rissa,
  anytime". Separately, `play_poker_card` (never scored before — a
  random hand card) now picks whichever card would form the strongest
  shape against the match's public banco symbols, scored against
  `poker_rank_order` (`data/game_config.json`) the same way `rules/
  poker.py::_resolve_match` itself does. **Corrected 2026-09-24**: the
  first version of this scorer assumed a repeated colour beats "5
  diversi" (real-world poker intuition) — backwards from this game's
  own confirmed ranking, where "five_different" is listed *first*
  (best) and "pair" last (worst); see `score_play_poker_card_option`'s
  own docstring. Found and fixed before ever reaching production
  (backend-only, redeploy still pending). This one has no real downside
  (the bet is already placed either way) so it's applied
  unconditionally, not gated on a Job needing it.

**Measured impact, honestly**: a 200-game all-heuristic-bot sweep
(`total_points` per player) went 5.16 (pre-`score_action_type`) → 5.52
(action-type awareness only) → 5.72 (+ commitment + Link spending + the
`own_dope_in_base` diversity fix) → 6.21 (+ deliberate Rissa/Poker for a
Job) — real and now the single biggest jump of the sequence (jobs
completed per player 1.03 → 1.35, zero-Job players 40% → 34%), but still
nowhere near closing the ~25-vs-5 gap the game designer measured against
a human. The remaining Jobs' thresholds (6 distinct Hoods, $30, 10
criminals ever placed...) stay steep relative to ~9 total actions/game
split across 6 types — this now looks like a genuine structural
throughput ceiling for a *shallow* heuristic (no look-ahead, no
multi-turn simulation) rather than a remaining targeting bug. Closing it
further would mean actual look-ahead/simulation (CLAUDE.md §14.3,
explicitly deferred) — a materially bigger project than any single
scoring tweak in this module.

Still out of scope: Grit-value selection (stays uniform-random — which
of the turn's 3 rounds gets which Grit value never changes the *total*
capacity spent this turn, only the per-round multiplier, so it's a much
smaller lever than either of the above) and genuine look-ahead
(simulating a full hypothetical round/turn before choosing) —
`score_action_type`/`_committed_job_id` stay *shallow* heuristics (does
this help, roughly how much, right now), not a simulation of the actual
outcome.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from dope_engine.application.views import PlayerGameView
from dope_engine.domain.content import JobDefinition, RaidCardDefinition
from dope_engine.domain.decisions import DecisionOption, PendingDecision
from dope_engine.domain.enums import PawnRole, PokerSymbolColor
from dope_engine.domain.ids import CardId, JobId, PlayerId, RaidCardId


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
    # Strictly bigger than job_progress_bonus — the single Job
    # `_committed_job_id` picks out gets this instead, everything else
    # revealed keeps the smaller flat bonus. Below rissa_avoidance_penalty
    # on purpose: even the committed Job shouldn't make a lost Rissa's
    # real cost (money/cards/a pawn sent away) look "free" by default —
    # see `score_option`'s move_criminal branch.
    committed_job_bonus: float = 5.0
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


def _has_strong_brawl_card(
    view: PlayerGameView, gun_count_by_card_id: dict[CardId, int] | None
) -> bool:
    """Whether the player's own hand holds at least one card with 2+
    Guns — the bar the game designer set (2026-09-23) for when
    deliberately triggering a Rissa (walking a 5th Criminal into an
    already-crowded Hood) is worth its real risk, rather than "any
    Rissa, anytime"."""
    if not gun_count_by_card_id:
        return False
    return any(gun_count_by_card_id.get(card_id, 0) >= 2 for card_id in view.own_hand_card_ids)


def _revealed_job_with_req_type(
    view: PlayerGameView,
    player_id: PlayerId,
    job_by_id: dict[JobId, JobDefinition] | None,
    req_type: str,
) -> JobId | None:
    """The player's currently-revealed Job (if any) with this exact
    requirement type — for `win_brawls`/`own_poker_chips`, which aren't
    in `_JOB_REQUIREMENT_HELPED_BY_ACTION_TYPE` (no *action type*
    decides them) but still matter for the one-off Rissa/Poker
    overrides below. "Still revealed" already means "still unmet" — a
    completed Job is replaced, never left sitting revealed."""
    if not job_by_id:
        return None
    for job_id in _revealed_job_ids(view, player_id):
        job = job_by_id.get(job_id)
        if job is not None and job.requirement.get("type") == req_type:
            return job_id
    return None


def _classify_poker_shape(symbols: tuple[PokerSymbolColor, ...]) -> str:
    """Mirrors `rules/poker.py::_hand_score`'s own shape_counts pattern
    match — the category name only, not its full colour-tiebreak key
    (a bot picking *which card to reveal* only needs "how strong,
    roughly", not the exact final placing)."""
    counts: dict[PokerSymbolColor, int] = {}
    for symbol in symbols:
        counts[symbol] = counts.get(symbol, 0) + 1
    shape_counts = sorted(counts.values(), reverse=True)
    if shape_counts == [1, 1, 1, 1, 1]:
        return "five_different"
    if shape_counts == [4, 1]:
        return "poker"
    if shape_counts == [3, 2]:
        return "full"
    if shape_counts == [3, 1, 1]:
        return "tris"
    if shape_counts == [2, 2, 1]:
        return "two_pair"
    return "pair"  # [2, 1, 1, 1] — the only remaining legal pattern


def score_play_poker_card_option(
    card_id: CardId,
    view: PlayerGameView,
    poker_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]],
    banco_symbols_by_card_id: dict[CardId, tuple[PokerSymbolColor, ...]],
    poker_rank_order: list[str] | None,
) -> float:
    """Higher is better. How strong a Poker hand this specific hand card
    would form once combined with the current match's public banco
    symbols (the launched card's own 3) plus this card's own 2 — scored
    against `poker_rank_order` (`data/game_config.json`, e.g.
    `["five_different", "poker", "full", ...]`, index 0 = best), the
    exact same list `rules/poker.py::_resolve_match` itself uses via
    `_hand_score`.

    **Bug fixed 2026-09-24** (found while reading this same code for an
    unrelated OutcomeModal request): the previous version scored by
    `max(colour repeat count)` — the *opposite* of this game's actual
    ranking. The game designer confirmed (2026-08-02, `_hand_score`'s
    own docstring: "index 0 = best rank") that "5 diversi" (no repeats
    at all) is the *best* shape here, not the worst as real-world poker
    would suggest — `poker_rank_order` itself confirms it, listed first.
    The old code was steering the bot toward deliberately *matching*
    colours with the banco, which actually chases the *worst* shapes
    (`pair` ranks last). Never reached production (backend-only,
    pending a Render redeploy at the time this was found).

    Returns 0.0 if there's no active match to read banco symbols from,
    the card contributes none of its own (a Preti "Gamble" card,
    `rules/poker.py`'s own docstring), or `poker_rank_order` wasn't
    supplied."""
    if not poker_rank_order:
        return 0.0
    launched_card_id = view.poker_launched_card_id
    if launched_card_id is None:
        return 0.0
    banco_symbols = banco_symbols_by_card_id.get(launched_card_id, ())
    card_symbols = poker_symbols_by_card_id.get(card_id, ())
    if not banco_symbols or not card_symbols:
        return 0.0
    shape = _classify_poker_shape((*banco_symbols, *card_symbols))
    if shape not in poker_rank_order:
        return 0.0
    return float(-poker_rank_order.index(shape))


def _own_criminals_out_of_base_count(view: PlayerGameView, player_id: PlayerId) -> int:
    return sum(
        1
        for pawn in view.pawns
        if pawn.owner_player_id == player_id and pawn.role != PawnRole.IN_BASE
    )


def _own_officer_count(view: PlayerGameView, player_id: PlayerId) -> int:
    return sum(1 for officer in view.officers if officer.owner_player_id == player_id)


def _revealed_job_ids(view: PlayerGameView, player_id: PlayerId) -> list[JobId]:
    progress = view.job_progress_by_player.get(player_id)
    if progress is None:
        return []
    return [job_id for job_id in progress.revealed_job_id_by_tier.values() if job_id is not None]


# Which `choose_action_type` options could plausibly move each Job
# requirement type — the same association `_job_progress_bonus` uses
# per-option, but at the coarser type level `score_action_type` needs
# (before any specific target exists to inspect). own_rats/win_brawls/
# own_poker_chips aren't here: none of the 6 action types decide them
# (see this module's own docstring for why Rissa-seeking specifically
# is deliberately not encouraged either).
_JOB_REQUIREMENT_HELPED_BY_ACTION_TYPE: dict[str, frozenset[str]] = {
    "own_dope_in_base": frozenset({"buy_dope"}),
    "criminals_in_distinct_hoods": frozenset({"move_criminal", "place_criminal"}),
    "criminals_out_of_base": frozenset({"place_criminal"}),
    "own_links": frozenset({"sell_dope"}),
    "own_money": frozenset({"sell_dope"}),
    "own_officers": frozenset({"buy_officer"}),
}

# Same idea for the 7 Retata escape criteria (data/raids.json) — only
# the ones with an obvious, safe action-type lever; most_criminals_in_jail
# and most_poker_wins aren't something any of the 6 action types decide.
_RAID_CRITERION_HELPED_BY_ACTION_TYPE: dict[str, frozenset[str]] = {
    "least_dope_value": frozenset({"sell_dope"}),
    "most_money": frozenset({"sell_dope"}),
    "most_links_with_contacts": frozenset({"sell_dope"}),
    "most_criminals_in_hoods": frozenset({"move_criminal", "place_criminal"}),
    "most_cops_bought": frozenset({"buy_officer"}),
}
_RAID_CRITERION_HURT_BY_ACTION_TYPE: dict[str, frozenset[str]] = {
    "least_dope_value": frozenset({"buy_dope"}),
}


def _job_unmet_and_ratio(
    job: JobDefinition, view: PlayerGameView, player_id: PlayerId
) -> tuple[bool, float] | None:
    """(is_still_unmet, progress_ratio) for a Job whose requirement type is
    one of `_JOB_REQUIREMENT_HELPED_BY_ACTION_TYPE`'s keys, or `None` if
    this requirement type isn't covered at all. Mirrors `rules/jobs.py::
    _check_requirement`'s own semantics — notably `own_dope_in_base`'s
    `at_least_one_per_type` flag (2026-09-23 bug found while diagnosing
    why bots' Job completion rate didn't move after `_committed_job_id`
    was added: a flat "total units >= count" check considers job_05 done
    after 4 units of a *single* Dope type, when the real requirement is 1
    of each of the 4 types — a bot hitting that false "done" state simply
    stops pursuing the Job it never actually finished, silently wasting
    every turn after that point). Shared by `score_action_type`,
    `_committed_job_id` and `_job_progress_bonus` so all three agree on
    the same live snapshot within a single call."""
    req_type = job.requirement["type"]
    if req_type not in _JOB_REQUIREMENT_HELPED_BY_ACTION_TYPE:
        return None
    count = job.requirement.get("count", 0)
    if count <= 0:
        return None

    if req_type == "own_dope_in_base":
        dope_counts = _find_player_view(view, player_id).base_inventory.dope_counts
        if job.requirement.get("at_least_one_per_type"):
            all_types = tuple(view.current_price_by_dope_type.keys())
            needed = len(all_types) or count
            held_types = sum(1 for dt in all_types if dope_counts.get(dt, 0) >= 1)
            return held_types < needed, held_types / needed
        total = sum(dope_counts.values())
        return total < count, min(total / count, 1.0)

    current_by_req_type = {
        "criminals_in_distinct_hoods": len(_own_criminal_hood_ids(view, player_id)),
        "criminals_out_of_base": _own_criminals_out_of_base_count(view, player_id),
        "own_links": _own_link_count(view, player_id),
        "own_money": _find_player_view(view, player_id).money,
        "own_officers": _own_officer_count(view, player_id),
    }
    current = current_by_req_type.get(req_type, count)
    return current < count, min(current / count, 1.0)


def _committed_job_id(
    view: PlayerGameView, player_id: PlayerId, job_by_id: dict[JobId, JobDefinition] | None
) -> JobId | None:
    """Which single revealed Job to concentrate this and the next turn's
    actions on — whichever the player is proportionally closest to
    finishing, among the requirement types a bot can actually move at all
    (`_JOB_REQUIREMENT_HELPED_BY_ACTION_TYPE`'s keys). See the module
    docstring for why recomputing this fresh every call (rather than
    HeuristicBot remembering a choice between decisions) still produces
    multi-turn-consistent focus. Ties (e.g. two untouched Jobs both at
    0 progress) favor the smaller `count` — the one that's structurally
    faster to finish, all else equal."""
    if not job_by_id:
        return None
    best_job_id: JobId | None = None
    best_ratio = -1.0
    best_count = 0
    for job_id in _revealed_job_ids(view, player_id):
        job = job_by_id.get(job_id)
        if job is None:
            continue
        unmet_and_ratio = _job_unmet_and_ratio(job, view, player_id)
        if unmet_and_ratio is None:
            continue
        is_unmet, ratio = unmet_and_ratio
        if not is_unmet:
            continue
        count = job.requirement.get("count", 0)
        if ratio > best_ratio or (ratio == best_ratio and count < best_count):
            best_ratio = ratio
            best_count = count
            best_job_id = job_id
    return best_job_id


def score_action_type(
    action_type: str,
    view: PlayerGameView,
    player_id: PlayerId,
    job_by_id: dict[JobId, JobDefinition] | None,
    raid_by_id: dict[RaidCardId, RaidCardDefinition] | None,
    weights: HeuristicWeights,
) -> float:
    """Higher is better. Scores a *type* of action — before any specific
    target exists to inspect — by how many of the player's currently
    revealed, still-unmet Jobs it could plausibly help toward, plus the
    active Retata's escape criterion. See the module docstring for why
    this is the highest-leverage addition: `choose_action_type` was the
    one decision left completely uniform-random despite every other
    decision already being scored.

    Deliberately shallow, same spirit as `_job_progress_bonus`/
    `_raid_criterion_bonus`: no attempt to simulate whether a
    `move_criminal` into a crowded Hood would actually *win* the Rissa it
    triggers — a lost Rissa costs money/cards and sends a pawn away, so
    `rissa_avoidance_penalty` (in `score_option`, once real targets
    exist) is left as the only Rissa-related signal; `own_links`
    deliberately only steers toward `sell_dope` (a Link is never at risk
    of being lost the way a Rissa participant is) rather than also
    toward walking into a 5th-Criminal Hood on purpose."""
    score = 0.0
    if job_by_id:
        committed_job_id = _committed_job_id(view, player_id, job_by_id)
        for job_id in _revealed_job_ids(view, player_id):
            job = job_by_id.get(job_id)
            if job is None:
                continue
            req_type = job.requirement["type"]
            if action_type not in _JOB_REQUIREMENT_HELPED_BY_ACTION_TYPE.get(req_type, frozenset()):
                continue
            unmet_and_ratio = _job_unmet_and_ratio(job, view, player_id)
            if unmet_and_ratio is not None and unmet_and_ratio[0]:
                score += (
                    weights.committed_job_bonus
                    if job_id == committed_job_id
                    else weights.job_progress_bonus
                )

    if raid_by_id and view.raid_card_id is not None:
        raid = raid_by_id.get(view.raid_card_id)
        if raid is not None:
            criterion = raid.escape_criterion
            if action_type in _RAID_CRITERION_HELPED_BY_ACTION_TYPE.get(criterion, frozenset()):
                score += weights.raid_criterion_bonus
            if action_type in _RAID_CRITERION_HURT_BY_ACTION_TYPE.get(criterion, frozenset()):
                score -= weights.raid_criterion_bonus

    return score


def _job_progress_bonus(
    decision: PendingDecision,
    payload: Mapping[str, Any],
    view: PlayerGameView,
    player_id: PlayerId,
    job_by_id: dict[JobId, JobDefinition] | None,
    weights: HeuristicWeights,
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
    types (see module docstring). Whichever Job `_committed_job_id`
    picks gets `weights.committed_job_bonus` here too, same as in
    `score_action_type` — a target-level option that advances the
    committed Job should outscore one that only advances some other,
    less-pressing revealed Job."""
    if not job_by_id:
        return 0.0
    own_player = _find_player_view(view, player_id)
    committed_job_id = _committed_job_id(view, player_id, job_by_id)
    bonus = 0.0
    for job_id in _revealed_job_ids(view, player_id):
        job = job_by_id.get(job_id)
        if job is None:
            continue
        requirement = job.requirement
        req_type = requirement.get("type")
        count = requirement.get("count", 0)
        weight = (
            weights.committed_job_bonus
            if job_id == committed_job_id
            else weights.job_progress_bonus
        )

        if req_type == "own_dope_in_base" and decision.decision_type == "buy_dope":
            unmet_and_ratio = _job_unmet_and_ratio(job, view, player_id)
            if unmet_and_ratio is not None and unmet_and_ratio[0]:
                held = own_player.base_inventory.dope_counts.get(payload["dope_type"], 0)
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
    gun_count_by_card_id: dict[CardId, int] | None = None,
) -> float:
    """Higher is better. See module docstring for the heuristics and what's
    deliberately left out. `job_by_id`/`raid_by_id`/`gun_count_by_card_id`
    are optional — omitting them (any existing caller) just skips those
    bonus terms."""
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
            win_brawls_job_id = _revealed_job_with_req_type(
                view, player_id, job_by_id, "win_brawls"
            )
            if win_brawls_job_id is not None and _has_strong_brawl_card(view, gun_count_by_card_id):
                score += weights.job_progress_bonus
            else:
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

    score += _job_progress_bonus(decision, payload, view, player_id, job_by_id, weights)
    score += _raid_criterion_bonus(
        decision, payload, view, player_id, raid_by_id, weights.raid_criterion_bonus
    )

    return score


def score_spend_link_for_extra_action_option(
    payload: Mapping[str, Any],
    view: PlayerGameView,
    player_id: PlayerId,
    job_by_id: dict[JobId, JobDefinition] | None,
    raid_by_id: dict[RaidCardId, RaidCardDefinition] | None,
    link_extra_action_types: Mapping[str, tuple[str, ...]],
    weights: HeuristicWeights,
) -> float:
    """Higher is better; may be negative — unlike the "always take it"
    decisions in `policies.py::_ALWAYS_MAX_DECISION_TYPES`, spending a
    Link for an extra action isn't free (see module docstring: it
    permanently demotes that Link back to a plain Covo pawn). Scores the
    best of the action types this Link's Contact would unlock
    (`score_action_type`, so it inherits the same committed-Job focus)
    against `_own_links_opportunity_cost` — the value of *not* setting
    back an unmet `own_links` Job requirement by spending any Link at
    all right now."""
    contact_id = payload["contact_id"]
    allowed_types = link_extra_action_types.get(contact_id, ())
    if not allowed_types:
        return float("-inf")
    best_action_value = max(
        score_action_type(action_type, view, player_id, job_by_id, raid_by_id, weights)
        for action_type in allowed_types
    )
    return best_action_value - _own_links_opportunity_cost(view, player_id, job_by_id, weights)


def _own_links_opportunity_cost(
    view: PlayerGameView,
    player_id: PlayerId,
    job_by_id: dict[JobId, JobDefinition] | None,
    weights: HeuristicWeights,
) -> float:
    """The bonus this player's still-unmet `own_links` Job(s) would have
    scored had this decision been a `sell_dope` one instead — spending
    *any* Link for an extra action sets back that same progress, so this
    is charged once per unmet `own_links` Job regardless of which
    specific Link gets spent."""
    if not job_by_id:
        return 0.0
    committed_job_id = _committed_job_id(view, player_id, job_by_id)
    own_links = _own_link_count(view, player_id)
    cost = 0.0
    for job_id in _revealed_job_ids(view, player_id):
        job = job_by_id.get(job_id)
        if job is None or job.requirement.get("type") != "own_links":
            continue
        count = job.requirement.get("count", 0)
        if own_links >= count:
            continue
        cost += (
            weights.committed_job_bonus
            if job_id == committed_job_id
            else weights.job_progress_bonus
        )
    return cost
