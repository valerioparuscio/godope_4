"""What does completing each Job bring with it (beyond its own REP)? Within-table regressions of the
final-score components on 'completed job j' dummies (all nine at once, plus a count-only baseline)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
df, comps = A.load(sys.argv[1])
done = comps.groupby(["game", "pid", "job"]).done.max().unstack("job").reset_index()
dd = df.merge(done, on=["game", "pid"])
jobs = list(A.TITLE)
groups = dd.game.values


def centred(col):
    return (dd[col] - dd.groupby("game")[col].transform("mean")).values


Xj = np.column_stack([centred(j) if dd[j].dtype != bool else (dd[j].astype(float) - dd[j].astype(float).groupby(dd.game).transform("mean")).values for j in jobs])
Xj = np.column_stack([(dd[j].astype(float) - dd[j].astype(float).groupby(dd.game).transform("mean")).values for j in jobs])

comps_cols = [("pts", "totale"), ("money_pts", "denaro"), ("clean_pts", "REP pulite"), ("stained_pts", "REP macchiate"), ("maj_pts", "maggioranze"), ("chip_pts", "chip"), ("skill_pts", "skill")]
print("## Cosa porta con sé aver completato ciascun Job (tutti e nove insieme, nello stesso modello; punti rispetto al tavolo)")
print("| Job completato | " + " | ".join(n for _, n in comps_cols) + " |")
print("|---|" + "---:|" * len(comps_cols))
betas = {}
for col, name in comps_cols:
    y = centred(col)
    b, V, r2, _ = A.ols_cluster(y, Xj, groups)
    betas[col] = (b, np.sqrt(np.diag(V)))
for i, j in enumerate(jobs):
    cells = [f"{betas[c][0][i]:+.2f} ±{1.96 * betas[c][1][i]:.2f}" for c, _ in comps_cols]
    print(f"| {A.TITLE[j]} ({j[-2:]}) | " + " | ".join(cells) + " |")
print()

# a Job's net worth beyond the 2 points of its REP: total effect minus 2 (a clean REP is 2 points; stained 1)
print("## Valore netto oltre ai 2 punti della REP (coefficiente del totale − 2)")
b, se = betas["pts"]
for i, j in sorted(enumerate(jobs), key=lambda t: -b[t[0]]):
    print(f"- {A.TITLE[j]}: {b[i] - 2:+.2f} ±{1.96 * se[i]:.2f}")
