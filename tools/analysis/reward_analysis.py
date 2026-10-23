"""Which Job bonus column is worth most? Every game has four bots, each with a different fixed preference
(Link / Skill / 2 cards / money) for the column it takes when it completes a Job; everything else is
identical, so the difference in final points is the value of the preference.

Usage: python reward_analysis.py games.jsonl
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
recs = [json.loads(l) for l in open(sys.argv[1], encoding="utf8") if l.strip()]
recs = [r for r in recs if not r["error"] and r["finished"]]
rows = []
for r in recs:
    for pid, p in r["players"].items():
        f = p["final"]
        taken = {t: sum(1 for b in p["bonuses"] if b["bonus"] == t) for t in ("link", "skill", "two_cards", "money")}
        rows.append(dict(game=r["seed"], pid=pid, pref=p["pref"], pts=f["total_points"], n_jobs=len(p["completions"]), win=1.0 / len(r["winners"]) if pid in r["winners"] else 0.0,
                         money_pts=f["money_track_position_points"], clean=f["clean_reputation_points"], stained=f["stained_reputation_points"], maj=f["contact_majority_points"],
                         chip=f["base_chip_points"], skill=f["skill_points"], **{"n_" + k: v for k, v in taken.items()}))
df = pd.DataFrame(rows)
for c in ["pts", "win", "money_pts", "clean", "stained", "maj", "chip", "skill", "n_jobs"]:
    df[c + "_c"] = df[c] - df.groupby("game")[c].transform("mean")
LAB = {"link": "Link", "skill": "Skill", "two_cards": "2 carte", "money": "3$"}
print(f"# Valore dei premi dei Job — {df.game.nunique()} partite, {len(df)} giocatori-partita\n")
print("| preferenza | n | bonus presi (Link / Skill / 2 carte / 3$) | punti vs tavolo | vittorie | per Job completato |")
print("|---|---:|---|---:|---:|---:|")
for t in ("link", "skill", "two_cards", "money"):
    mask = (df.pref == t).values
    m, se, n = A.cluster_mean(df, mask, "pts_c")
    w, wse, _ = A.cluster_mean(df, mask, "win_c")
    sub = df[mask]
    mix = " / ".join(f"{sub['n_' + k].mean():.2f}" for k in ("link", "skill", "two_cards", "money"))
    # per completed Job: ITT effect divided by the Jobs this group completes (the bonus only matters when a Job is completed)
    per = m / sub.n_jobs.mean()
    print(f"| {LAB[t]} | {n} | {mix} | {A.fmt(m, se)} | {100 * (0.25 + w):.1f}% ±{196 * wse:.1f} | {per:+.2f} |")
print()
print("Differenze (punti):")
for a, b in [("link", "skill"), ("link", "two_cards"), ("link", "money"), ("skill", "two_cards"), ("skill", "money"), ("two_cards", "money")]:
    d, dse = A.cluster_diff(df, (df.pref == a).values, (df.pref == b).values, "pts_c")
    print(f"- {LAB[a]} − {LAB[b]}: {A.fmt(d, dse)}" + ("  ← significativo" if abs(d) > 1.96 * dse else ""))
print()
print("Da dove viene la differenza (rispetto al tavolo):")
cols = ["money_pts", "clean", "stained", "maj", "chip", "skill", "n_jobs"]
names = ["denaro", "REP pulite", "REP macchiate", "maggioranze", "chip", "skill", "Job completati"]
print("| preferenza | " + " | ".join(names) + " |")
print("|---|" + "---:|" * len(cols))
for t in ("link", "skill", "two_cards", "money"):
    mask = (df.pref == t).values
    print(f"| {LAB[t]} | " + " | ".join(A.fmt(*A.cluster_mean(df, mask, c + "_c")[:2]) for c in cols) + " |")
