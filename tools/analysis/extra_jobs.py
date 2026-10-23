"""Extra cuts of the Job-sequence data: how much of each starting-Job effect runs through the number
of Jobs completed, what a completed Job is worth, tier-3 x tier-2 table, completion timing."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
df, comps = A.load(sys.argv[1])
y = df.pts_c.values
groups = df.game.values


def dummies(cols):
    mats, names = [], []
    for c in cols:
        vals = sorted(df[c].unique())
        for v in vals[1:]:
            ind = (df[c] == v).astype(float)
            mats.append(ind.values - ind.groupby(df.game).transform("mean").values)
            names.append(f"{c}={v}")
    return np.column_stack(mats), names


# 1. how much of the starting-job effect runs through the number of Jobs completed
X, names = dummies(["first1", "first2", "first3"])
b, V, r2, adj = A.ols_cluster(y, X, groups)
nj = (df.n_jobs - df.groupby("game").n_jobs.transform("mean")).values
Xm = np.column_stack([X, nj])
bm, Vm, r2m, adjm = A.ols_cluster(y, Xm, groups)
print("## Effetto dei Job iniziali sui punti, con e senza i Job completati")
print("| termine | effetto totale | effetto a parità di Job completati |")
print("|---|---:|---:|")
for i, n in enumerate(names):
    se, sem = np.sqrt(V[i, i]), np.sqrt(Vm[i, i])
    print(f"| {n} (base: primo Job con id più basso del livello) | {b[i]:+.2f} ±{1.96 * se:.2f} | {bm[i]:+.2f} ±{1.96 * sem:.2f} |")
print(f"R² {100 * r2:.1f}% → {100 * r2m:.1f}% aggiungendo il numero di Job completati (coefficiente {bm[-1]:+.2f} pt per Job)\n")

# 2. what a completed job is worth (observational, within the table)
print("## Valore di un Job completato (punti vs tavolo di chi lo completa, rispetto a chi no)")
print("| Job | lo completa | punti vs tavolo se lo completa | se non lo completa | differenza |")
print("|---|---:|---:|---:|---:|")
done = comps.groupby(["game", "pid", "job"]).done.max().unstack("job").reset_index()
dd = df.merge(done, on=["game", "pid"])
for j, t in A.TITLE.items():
    m1, se1, n1 = A.cluster_mean(dd, dd[j].values)
    m0, se0, n0 = A.cluster_mean(dd, ~dd[j].values.astype(bool))
    d, dse = A.cluster_diff(dd, dd[j].values, ~dd[j].values.astype(bool))
    print(f"| {t} ({j[-2:]}) | {100 * n1 / len(dd):.0f}% | {m1:+.2f} | {m0:+.2f} | {A.fmt(d, dse)} |")
print()

# 3. tier 3 x tier 2 first job
print("## Punti vs tavolo: primo Job del livello 3 (righe) × primo Job del livello 2 (colonne)")
t2 = A.TIERS[2]
print("| livello 3 \\ livello 2 | " + " | ".join(A.TITLE[j] for j in t2) + " |")
print("|---|" + "---:|" * len(t2))
for j3 in A.TIERS[3]:
    cells = []
    for j2 in t2:
        m, se, n = A.cluster_mean(df, ((df.first3 == j3) & (df.first2 == j2)).values)
        cells.append(f"{m:+.2f} ±{1.96 * se:.2f} (n={n})")
    print(f"| {A.TITLE[j3]} | " + " | ".join(cells) + " |")
print()

# 4. 03 vs 09 conditional on the other tiers (is the verdict stable?)
print("## «2 Chip Poker» − «30 dollari» come primo Job del livello 3, in base al resto")
for tier in (1, 2):
    for j in A.TIERS[tier]:
        a = ((df.first3 == "job_03") & (df[f"first{tier}"] == j)).values
        bb = ((df.first3 == "job_09") & (df[f"first{tier}"] == j)).values
        d, dse = A.cluster_diff(df, a, bb)
        w, wse = A.cluster_diff(df, a, bb, "win")
        print(f"- livello {tier} = {A.TITLE[j]}: punti {A.fmt(d, dse)}, vittorie {100 * w:+.1f} pt ±{196 * wse:.1f}")
print()

# 5. when the starting job is completed
print("## Turno di completamento (quando lo completa) e Job completati *oltre* al primo del livello 3")
for j in A.TIERS[3]:
    c = comps[(comps.job == j) & (comps.pos == 0) & comps.done]
    others = []
    m = df[df.first3 == j]
    done_first = comps[(comps.job == j) & (comps.pos == 0)].set_index(["game", "pid"]).done
    nj_other = m.set_index(["game", "pid"]).n_jobs - done_first.reindex(m.set_index(["game", "pid"]).index).astype(int)
    print(f"- {A.TITLE[j]}: turno medio di completamento {c.turn.mean():.2f}; completati in media {nj_other.mean():.2f} altri Job (il tavolo: {df.n_jobs.mean():.2f} in totale)")
