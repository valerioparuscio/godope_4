"""What state does each starting Job leave a player in? From sim_jobs2.py's round snapshots.

Part A  randomised: players grouped by the Job they were dealt first in a tier (the draw is random, so
        differences in how their game *looks* — money, pawns in base, passes, Poker — come from the Job).
Part B  event study: around the completion of each Job, the change from the start of the completion round to the
        start of the next one, minus the same change of the other players of that game in that round.
Part C  timing: share of players who completed the Job by the end of each turn.

Usage: python aftermath.py games.jsonl
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
TITLE = A.TITLE
path = sys.argv[1]
recs = [json.loads(l) for l in open(path, encoding="utf8") if l.strip()]
recs = [r for r in recs if not r["error"] and r["finished"]]

rows, snaps, comps = [], [], []
for r in recs:
    for pid, p in r["players"].items():
        rd = [x for x in p["rounds"] if (x["turn"], x["round"]) != (1, 1)]  # round 1 is everyone's identical start
        def share(f):
            return np.mean([f(x) for x in rd]) if rd else np.nan
        launches = p["poker_launches"]
        row = dict(
            game=r["seed"], pid=pid, pts=p["final"]["total_points"], n_jobs=len(p["completions"]),
            money=share(lambda x: x["money"]), low_money=share(lambda x: x["money"] <= 2), zero_money=share(lambda x: x["money"] == 0),
            in_base=share(lambda x: x["in_base"]), no_base=share(lambda x: x["in_base"] == 0),
            no_place=share(lambda x: "offered" in x and "place_criminal" not in x["offered"]),
            passed=share(lambda x: bool(x.get("passed"))),
            hand=share(lambda x: x["hand"]), chips=share(lambda x: x["chips"]), gamblers=share(lambda x: x["gamblers"]),
            links=share(lambda x: x["links"]), criminals=share(lambda x: x["criminals"]),
            launches=len(launches), launches_no_gambler=sum(1 for l in launches if not l["gambler"]),
            end_money=p["end"]["money"],
        )
        for t in ("1", "2", "3"):
            row[f"first{t}"] = p["job_seq"][t][0]
        rows.append(row)
        for x in p["rounds"]:
            snaps.append(dict(game=r["seed"], pid=pid, g=(x["turn"] - 1) * 3 + x["round"], **{k: x[k] for k in ("money", "in_base", "hand", "links", "criminals", "chips", "gamblers")}))
        for c in p["completions"]:
            comps.append(dict(game=r["seed"], pid=pid, job=c["job"], tier=c["tier"], g=(c["turn"] - 1) * 3 + c["round"], turn=c["turn"],
                              first=(c["job"] == p["job_seq"][str(c["tier"])][0]), **{f"after_{k}": v for k, v in c["after"].items()}))
df = pd.DataFrame(rows)
snaps = pd.DataFrame(snaps)
comps = pd.DataFrame(comps)
METRICS = ["pts", "money", "low_money", "zero_money", "in_base", "no_base", "no_place", "passed", "hand", "chips", "gamblers", "links", "criminals", "launches", "launches_no_gambler"]
for m in METRICS:
    df[m + "_c"] = df[m] - df.groupby("game")[m].transform("mean")
print(f"# Stato lasciato dai Job — {df.game.nunique()} partite\n")

LAB = {"pts": "punti finali", "money": "denaro medio ($)", "low_money": "round con ≤ 2$", "zero_money": "round con 0$", "in_base": "pedine in base (media)", "no_base": "round con 0 pedine in base",
       "no_place": "round senza «Piazza» disponibile", "passed": "round passati (azione persa)", "hand": "carte in mano", "chips": "chip Poker", "gamblers": "Gambler nel Den",
       "links": "Link", "criminals": "Criminali sul tabellone", "launches": "Poker lanciati", "launches_no_gambler": "Poker lanciati senza Gambler"}
print("## A. Come appare la partita a chi riceve per primo un certo Job (differenza dalla media del proprio tavolo)")
for tier in (3, 2, 1):
    jobs = sorted(df[f"first{tier}"].unique())
    print(f"\n**Primo Job del livello {tier}**\n")
    print("| | " + " | ".join(TITLE[j] for j in jobs) + " |")
    print("|---|" + "---:|" * len(jobs))
    for m in METRICS:
        scale = 100 if m in ("low_money", "zero_money", "no_base", "no_place", "passed") else 1
        unit = " pt%" if scale == 100 else ""
        cells = []
        for j in jobs:
            mean, se, n = A.cluster_mean(df, (df[f"first{tier}"] == j).values, m + "_c")
            cells.append(f"{scale * mean:+.2f}{unit} ±{scale * 1.96 * se:.2f}")
        print(f"| {LAB[m]} | " + " | ".join(cells) + " |")
print(f"\n(medie assolute dell'intero campione: denaro {df.money.mean():.1f}$, round con ≤ 2$ {100 * df.low_money.mean():.0f}%, con 0$ {100 * df.zero_money.mean():.0f}%, "
      f"con 0 pedine in base {100 * df.no_base.mean():.0f}%, senza «Piazza» {100 * df.no_place.mean():.0f}%, passati {100 * df.passed.mean():.0f}%)\n")

print("## B. Intorno al completamento di ciascun Job (da inizio round a inizio round successivo, meno gli altri giocatori della stessa partita)")
snaps_idx = snaps.set_index(["game", "pid", "g"])
by_round = snaps.groupby(["game", "g"])
deltas = []
for c in comps.itertuples():
    nxt = c.g + 1 if c.g < 9 else None
    try:
        before = snaps_idx.loc[(c.game, c.pid, c.g)]
        after = snaps_idx.loc[(c.game, c.pid, nxt)] if nxt else None
    except KeyError:
        continue
    if after is None:
        continue
    others = snaps[(snaps.game == c.game) & (snaps.g == c.g) & (snaps.pid != c.pid)].set_index("pid")
    others_next = snaps[(snaps.game == c.game) & (snaps.g == nxt) & (snaps.pid != c.pid)].set_index("pid")
    common = others.index.intersection(others_next.index)
    if len(common) == 0:
        continue
    row = dict(job=c.job, first=c.first, g=c.g)
    for m in ("money", "in_base", "hand", "links", "criminals", "chips"):
        row[m] = (after[m] - before[m]) - float((others_next.loc[common, m] - others.loc[common, m]).mean())
    deltas.append(row)
dd = pd.DataFrame(deltas)
print("| Job | n | denaro | pedine in base | carte | Link | Criminali sul tabellone | chip |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for j in TITLE:
    x = dd[dd.job == j]
    if len(x) < 20:
        continue
    cells = [f"{x[m].mean():+.2f} ±{1.96 * x[m].std() / np.sqrt(len(x)):.2f}" for m in ("money", "in_base", "hand", "links", "criminals", "chips")]
    print(f"| {TITLE[j]} ({j[-2:]}) | {len(x)} | " + " | ".join(cells) + " |")
print()

print("## C. Entro quando viene completato (tra chi lo ha rivelato dall'inizio)")
print("| Job | entro fine turno 1 | entro fine turno 2 | entro fine turno 3 |")
print("|---|---:|---:|---:|")
first_n = defaultdict(int)
for r in recs:
    for p in r["players"].values():
        for t in ("1", "2", "3"):
            first_n[p["job_seq"][t][0]] += 1
for j in TITLE:
    x = comps[(comps.job == j) & comps["first"]]
    cells = [f"{100 * (x.turn <= t).sum() / first_n[j]:.0f}%" for t in (1, 2, 3)]
    print(f"| {TITLE[j]} ({j[-2:]}) | " + " | ".join(cells) + " |")
