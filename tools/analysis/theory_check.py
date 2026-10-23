"""Designer's qualitative Job x Raid matrix (-5..+5) versus what the simulations show.

Observed: how much more (or less) often a player whose Job in that tier is X escapes Raid Y, in percentage points
(the same Raid event, the other three players of the game as control; game-clustered uncertainty).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import raidlib as R  # noqa: E402
import theory_matrix  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
COLS = theory_matrix.COLS
THEORY = theory_matrix.THEORY
JOBS = list(THEORY)

df, games = R.load(sys.argv[1:])
print(f"{games.game.nunique()} partite, {len(df)} giocatori-partita\n")
for j in JOBS:
    df["f_" + j] = ((df.first1 == j) | (df.first2 == j) | (df.first3 == j)).astype(float)
ev = []
for t in (1, 2, 3):
    sub = df[["game", "pid", f"r{t}", f"caught{t}", f"tie{t}"] + ["f_" + j for j in JOBS]].rename(columns={f"r{t}": "raid", f"caught{t}": "caught", f"tie{t}": "tie"})
    sub["turn"] = t
    ev.append(sub)
ev = pd.concat(ev, ignore_index=True)
ev["ev_id"] = ev.game + ":" + ev.turn.astype(str)
ev["escape"] = 1 - ev.caught
ev["escape_c"] = ev.escape - ev.groupby("ev_id").escape.transform("mean")

obs = np.zeros((len(JOBS), len(COLS)))
se = np.zeros_like(obs)
for a, j in enumerate(JOBS):
    for b, r in enumerate(COLS):
        s = ev[ev.raid == r]
        mask = (s["f_" + j] == 1).values
        g = pd.DataFrame({"g": s.ev_id.values, "s": np.where(mask, s.escape_c.values, 0.0), "n": mask.astype(float)}).groupby("g").sum()
        m = g.s.sum() / g.n.sum()
        obs[a, b] = 100 * m
        se[a, b] = 100 * np.sqrt(((g.s - m * g.n) ** 2).sum()) / g.n.sum()
theory = np.array([THEORY[j] for j in JOBS], float)
NAMES = theory_matrix.NAMES
print("## Effetto osservato sulla probabilità di sfuggire alla Retata (punti percentuali; in parentesi la teoria)\n")
print("| Job | " + " | ".join(NAMES) + " |")
print("|---|" + "---:|" * len(COLS))
for a, j in enumerate(JOBS):
    cells = []
    for b in range(len(COLS)):
        star = "**" if abs(obs[a, b]) > 1.96 * se[a, b] else ""
        cells.append(f"{star}{obs[a, b]:+.1f}{star} ({theory[a, b]:+.0f})")
    print(f"| {R.JOB_NAME[j]} | " + " | ".join(cells) + " |")
flat_t, flat_o = theory.ravel(), obs.ravel()
rho, p_rho = stats.spearmanr(flat_t, flat_o)
r_, p_r = stats.pearsonr(flat_t, flat_o)
print(f"\nCorrelazione teoria/osservato su 63 celle: Pearson {r_:+.2f} (p={p_r:.1g}), Spearman {rho:+.2f} (p={p_rho:.1g})")
strong = np.abs(flat_t) >= 3
agree = np.sign(flat_t[strong]) == np.sign(flat_o[strong])
sig = np.abs(flat_o[strong]) > 1.96 * se.ravel()[strong]
print(f"Celle con |teoria| ≥ 3: {strong.sum()}; segno concorde in {agree.sum()} ({100 * agree.mean():.0f}%); significative e concordi: {(agree & sig).sum()}, significative e discordi: {(~agree & sig).sum()}")
print("\nCelle dove la teoria sbaglia di più (teoria forte, osservato opposto e significativo):")
rows = []
for a, j in enumerate(JOBS):
    for b in range(len(COLS)):
        if abs(theory[a, b]) >= 3 and np.sign(theory[a, b]) != np.sign(obs[a, b]) and abs(obs[a, b]) > 1.96 * se[a, b]:
            rows.append((abs(obs[a, b]), R.JOB_NAME[j], NAMES[b], theory[a, b], obs[a, b], se[a, b]))
for _, jn, rn, t, o, s in sorted(rows, reverse=True):
    print(f"  - {jn} × {rn}: teoria {t:+.0f}, osservato {o:+.1f} ±{1.96 * s:.1f} pp")
print("\nCelle dove l'osservato è forte e la teoria è ~0 (|teoria| ≤ 1, |osservato| ≥ 4 pp):")
for a, j in enumerate(JOBS):
    for b in range(len(COLS)):
        if abs(theory[a, b]) <= 1 and abs(obs[a, b]) >= 4 and abs(obs[a, b]) > 1.96 * se[a, b]:
            print(f"  - {R.JOB_NAME[j]} × {NAMES[b]}: teoria {theory[a, b]:+.0f}, osservato {obs[a, b]:+.1f} ±{1.96 * se[a, b]:.1f} pp")
