"""Bot-vs-bot games for the Job / Raid studies: one JSON line per game with everything the analyses need.

Every player's Jobs (the three tiers' piles), when each Job was completed (and the state right after), a snapshot of
every player at the start of every action round (money, pawns by role, hand, chips, Cops/Feds, the Job active in each
tier, the current Raid, the action types on offer, whether he passed), the Poker launches, the Job bonuses taken, every
Raid revealed / resolved and every REP stain, and the final score breakdown.

Usage
    python tools/analysis/simulate.py --layout A --policy heuristic --seeds 500000-501999 --out analysis_data/x.jsonl

    --ruleset  easy_price (default) | standard | simple
    --layout   current (default) | A | C       Job-to-tier assignment, see job_layouts.py
    --policy   heuristic                       the heuristic bot with its default weights
               heuristic:key=value,...         the same with HeuristicWeights overridden, e.g.
                                               heuristic:raid_criterion_bonus=4  (Raid criterion weighted 4x)
                                               heuristic:job_progress_bonus=6,committed_job_bonus=10  (Jobs pursued harder)
               mix:link,skill,two_cards,money  every seat has a fixed preference for the Job bonus column (shuffled
                                               per game): the reward-value experiment
    --seeds    first-last (inclusive); seeds already in --out are skipped, so a run can be resumed or extended
    --workers  parallel processes (default 24)

A game is identified by its seed (game id `jobseq_<seed>`), so the same seed gives the same Raid sequence, setup and
bot randomness whatever the layout or the policy: runs on the same seeds are directly comparable.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# The bot code iterates over sets of strings, so with Python's per-process hash randomisation the same game can
# play out differently on each run. A fixed hash seed (inherited by the worker processes) makes a game, and so a
# whole run, reproducible from its seed, policy and layout.
os.environ.setdefault("PYTHONHASHSEED", "0")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import job_layouts  # noqa: E402
from dope_engine.application.command_bus import CommandFailure  # noqa: E402
from dope_engine.application.data_loader import load_game_data  # noqa: E402
from dope_engine.application.game_service import GameService  # noqa: E402
from dope_engine.application.legal_actions import build_command_from_selection  # noqa: E402
from dope_engine.bots import policies  # noqa: E402
from dope_engine.bots.scoring import HeuristicWeights  # noqa: E402
from dope_engine.domain.enums import GameStatus, PawnRole  # noqa: E402
from dope_engine.domain.ids import GameId  # noqa: E402
from dope_engine.domain.state import officer_count_in_base  # noqa: E402

WORK_DIR = REPO / "analysis_data" / "_packs"
RECORD_VERSION = 3
_DATA: dict = {}


def _plain(value):
    """JSON-safe copy of an event field."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _game_data(ruleset: str, layout: str, write: bool = False):
    """Loaded game data of a ruleset and Job layout (cached per process). Only the main process writes the layout's
    pack, once, before the workers start; the workers just read it."""
    key = (ruleset, layout)
    if key not in _DATA or write:
        pack, base = job_layouts.build_pack(REPO, ruleset, layout, WORK_DIR, write=write)
        _DATA[key] = load_game_data(pack, base_dir=base) if base else load_game_data(pack)
    return _DATA[key]


def _parse_weights(spec: str) -> HeuristicWeights:
    """`heuristic` or `heuristic:key=value,...` -> HeuristicWeights."""
    if spec == "heuristic":
        return HeuristicWeights()
    if not spec.startswith("heuristic:"):
        raise SystemExit(f"unknown policy '{spec}'")
    fields = {f.name for f in dataclasses.fields(HeuristicWeights)}
    kwargs = {}
    for part in spec.split(":", 1)[1].split(","):
        key, value = part.split("=")
        if key not in fields:
            raise SystemExit(f"HeuristicWeights has no field '{key}' (fields: {', '.join(sorted(fields))})")
        kwargs[key] = float(value)
    return HeuristicWeights(**kwargs)


def _heuristic(weights: HeuristicWeights, game_data):
    return policies.HeuristicBot(
        weights,
        job_by_id={job.job_id: job for job in game_data.jobs},
        raid_by_id={raid.raid_card_id: raid for raid in game_data.raids},
        gun_count_by_card_id={card.card_id: card.gun_count for card in game_data.customer_cards},
        link_extra_action_types={
            c.contact_id: c.link_extra_action_restricted_to for c in game_data.contacts.contacts
        },
        poker_symbols_by_card_id={c.card_id: c.poker_symbols for c in game_data.customer_cards},
        banco_symbols_by_card_id={c.card_id: c.banco_symbols for c in game_data.customer_cards},
        poker_rank_order=game_data.config.get("poker_rank_order"),
    )


class PrefBot:
    """The heuristic bot, except that it picks the Job bonus column by a fixed preference order."""

    def __init__(self, inner, pref, game_data):
        self.inner = inner
        self.rank = {t: i for i, t in enumerate(pref)}
        self.columns = game_data.config["job_board_column_bonuses"]
        self.job_by_id = {j.job_id: j for j in game_data.jobs}

    def _type(self, option):
        job = self.job_by_id[option.payload["job_id"]]
        kind = (
            job.column_bonus_overrides.get(option.payload["column_index"])
            or self.columns[option.payload["column_index"]]
        )
        return "two_cards" if kind == "money_or_two_cards" else kind

    def choose(self, view, decision, simulate=None):
        if decision.decision_type == "choose_job_reward" and decision.options:
            best = min(self.rank.get(self._type(o), 99) for o in decision.options)
            candidates = [o for o in decision.options if self.rank.get(self._type(o), 99) == best]
            pick = random.Random(
                f"{view.game_id}:{decision.decision_id}:{decision.player_id}"
            ).choice(candidates)
            return build_command_from_selection(view, decision, (pick.option_id,))
        return self.inner.choose(view, decision, simulate)


def _snap(state, player) -> dict:
    roles = {r.value: 0 for r in PawnRole}
    for pid in player.pawn_ids:
        roles[state.pawns[pid].role.value] += 1
    return {
        "money": player.money,
        "in_base": roles.get("in_base", 0),
        "criminals": roles.get("criminal", 0),
        "links": roles.get("link", 0),
        "gamblers": roles.get("gambler", 0),
        "rats": roles.get("rat", 0),
        "hand": len(player.hand_card_ids),
        "chips": player.base_inventory.poker_chip_count,
        "dope": sum(player.base_inventory.dope_counts.values()),
        "officers": officer_count_in_base(state, player.player_id),
    }


def run_game(task: tuple[str, str, int, str]) -> dict:
    ruleset, layout, seed, spec = task
    data = _game_data(ruleset, layout)
    pids = [f"player_{i}" for i in range(4)]

    prefs: dict[str, str | None] = {pid: None for pid in pids}
    weights = HeuristicWeights()
    if spec.startswith("mix:"):
        order = spec[4:].split(",")
        random.Random(seed).shuffle(order)
        prefs = dict(zip(pids, order, strict=True))
    else:
        weights = _parse_weights(spec)
    bots = {}
    for pid in pids:
        inner = _heuristic(weights, data)
        pref = prefs[pid]
        order = [pref, *[t for t in ("link", "skill", "two_cards", "money") if t != pref]] if pref else None
        bots[pid] = PrefBot(inner, order, data) if pref else inner
    service = GameService(data, bot_policy=bots[pids[0]])
    state = service.create_game(game_id=GameId(f"jobseq_{seed}"), seed=seed, human_seat=0).state

    players: dict[str, dict] = {}
    for p in state.players:
        progress = state.jobs.progress_by_player[p.player_id]
        players[p.player_id] = {
            "seat": p.seat_index,
            "pref": prefs[p.player_id],
            "start_money": p.money,
            "job_seq": {
                str(t): [progress.revealed_job_id_by_tier[t], *progress.tier_piles[t]]
                for t in sorted(progress.revealed_job_id_by_tier)
            },
            "completions": [],
            "bonuses": [],
            "rounds": [],
            "poker_launches": [],
        }
    rec = {
        "version": RECORD_VERSION, "seed": seed, "ruleset": ruleset, "layout": layout, "policy": spec,
        "error": None, "player_order": list(state.player_order), "players": players, "raids": [], "stains": [],
    }
    seen_rounds: set[tuple[int, int, str]] = set()
    entry_of: dict[tuple[int, int, str], dict] = {}
    steps = 0
    t0 = time.time()
    while state.status is not GameStatus.FINISHED and steps < 8000:
        steps += 1
        decision = state.pending_decision
        if decision is None:
            rec["error"] = "no pending decision"
            break
        pid = decision.player_id
        player = next(p for p in state.players if p.player_id == pid)
        turn, rnd = state.turn_index, state.action_round_index
        key = (turn, rnd, pid)
        if decision.decision_type == "choose_grit_action" and key not in seen_rounds:
            seen_rounds.add(key)
            entry = {
                "turn": turn, "round": rnd, **_snap(state, player), "raid": state.raids.current_turn_card_id,
                "active": {
                    str(k): v for k, v in state.jobs.progress_by_player[pid].revealed_job_id_by_tier.items()
                },
            }
            entry_of[key] = entry
            players[pid]["rounds"].append(entry)
        elif (
            decision.decision_type == "choose_action_type"
            and key in entry_of
            and "offered" not in entry_of[key]
        ):
            entry_of[key]["offered"] = [o.payload["action_type"] for o in decision.options]
        view = service.view_for(state, pid)
        try:
            command = bots[pid].choose(view, decision, service._make_simulate_fn(state, pid))
        except Exception as exc:  # a bot/engine problem must not kill the whole batch
            rec["error"] = (
                f"bot error {type(exc).__name__}: {exc}; decision {decision.decision_type} "
                f"min={decision.min_selections} max={decision.max_selections} options={len(decision.options)} "
                f"pass={decision.can_pass} ctx={dict(decision.context)} player={pid} "
                f"step={state.active_step.value} pref={prefs.get(pid)}"
            )
            break
        base_before = sum(1 for x in player.pawn_ids if state.pawns[x].role == PawnRole.IN_BASE)
        outcome = service.dispatch(state, command)
        if isinstance(outcome, CommandFailure):
            rec["error"] = f"CommandFailure: {outcome.error}"
            break
        state = outcome.state
        for e in outcome.events:
            name = type(e).__name__
            if name == "JobCompleted":
                pl = next(p for p in state.players if p.player_id == e.player_id)
                players[e.player_id]["completions"].append({
                    "job": e.job_id, "tier": e.tier, "turn": turn, "round": rnd, "step": steps,
                    "after": _snap(state, pl), "raid": state.raids.current_turn_card_id,
                })
            elif name == "JobBonusClaimed":
                players[e.player_id]["bonuses"].append({
                    "job": e.job_id, "column": e.column_index, "bonus": _plain(e.bonus_type), "turn": turn,
                })
            elif name == "MainActionPassed" and (turn, rnd, e.player_id) in entry_of:
                entry_of[(turn, rnd, e.player_id)]["passed"] = True
            elif name == "GritActionChosen" and (turn, rnd, e.player_id) in entry_of:
                entry_of[(turn, rnd, e.player_id)]["grit"] = e.grit_value
            elif name == "PokerLaunched":
                players[e.player_id]["poker_launches"].append({
                    "turn": turn, "round": rnd, "in_base_before": base_before,
                    "gambler": e.gambler_pawn_id is not None,
                })
            elif name in ("RaidRevealed", "RaidReplaced", "RaidFirstPlayerChosen", "RaidResolved"):
                rec["raids"].append({"event": name, "turn": turn, **{k: _plain(v) for k, v in e.__dict__.items()}})
            elif name == "ReputationStained":
                rec["stains"].append({"turn": turn, **{k: _plain(v) for k, v in e.__dict__.items()}})

    rec["steps"], rec["finished"], rec["turns"] = steps, state.status is GameStatus.FINISHED, state.turn_index
    rec["seconds"] = round(time.time() - t0, 1)
    if state.final_score is not None:
        rec["winners"] = list(state.final_score.winner_ids)
        for pid in pids:
            players[pid]["final"] = dataclasses.asdict(state.final_score.breakdown_by_player[pid])
    for p in state.players:
        players[p.player_id]["end"] = {**_snap(state, p), "skill_ids": list(p.skill_ids)}
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ruleset", default="easy_price", choices=["easy_price", "standard", "simple"])
    ap.add_argument("--layout", default="current", choices=list(job_layouts.LAYOUTS))
    ap.add_argument("--policy", default="heuristic")
    ap.add_argument("--seeds", required=True, help="first-last, inclusive")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()

    if not args.policy.startswith("mix:"):
        _parse_weights(args.policy)  # fail early on a typo
    first, last = (int(x) for x in args.seeds.split("-"))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done: set[int] = set()
    if out_path.exists():
        done = {json.loads(line)["seed"] for line in out_path.read_text(encoding="utf8").splitlines() if line.strip()}
    tasks = [(args.ruleset, args.layout, s, args.policy) for s in range(first, last + 1) if s not in done]
    print(f"{len(tasks)} games to run: {args.ruleset} / layout {args.layout} / {args.policy} "
          f"({len(done)} already in {out_path.name}), {args.workers} workers", flush=True)
    _game_data(args.ruleset, args.layout, write=True)  # build the pack once before the workers start
    t0 = time.time()
    n = errors = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool, out_path.open("a", encoding="utf8") as fh:
        for rec in pool.map(run_game, tasks, chunksize=1):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            n += 1
            errors += bool(rec["error"] or not rec["finished"])
            if n % 50 == 0 or n == len(tasks):
                rate = n / (time.time() - t0)
                print(f"  {n}/{len(tasks)} done, {errors} errors, {rate:.2f} games/s, "
                      f"eta {(len(tasks) - n) / max(rate, 1e-9) / 60:.1f} min", flush=True)
    print(f"done in {(time.time() - t0) / 60:.1f} min, {errors} errors/unfinished", flush=True)


if __name__ == "__main__":
    main()
