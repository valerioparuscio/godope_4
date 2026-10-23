"""Job draw x Raid triple, done properly (centred Raid indicators, so the interactions are deviations from
the Job's average value, and an out-of-sample test: fit on one set of games, predict another).

python raid_job_interaction.py <train.jsonl> <test.jsonl>
python raid_job_interaction.py <games.jsonl> -        # one dataset: even seeds train, odd seeds test
"""
import sys
from itertools import combinations, product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402
import raidlib as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
JOBS = list(R.JOB_NAME)
RAIDS = list(R.RAID_NAME)
PRESENCE = 3 / 7


def prepare(df):
    for j in JOBS:
        df["f_" + j] = ((df.first1 == j) | (df.first2 == j) | (df.first3 == j)).astype(float)
    for r in RAIDS:
        df["raid_" + r] = ((df.r1 == r) | (df.r2 == r) | (df.r3 == r)).astype(float) - PRESENCE
        df["late_" + r] = ((df.r2 == r) | (df.r3 == r)).astype(float) - 2 / 7
    return df


def design(df, interactions=True, late=False):
    def dm(series):
        return (series - series.groupby(df.game).transform("mean")).values
    cols = [dm(df["f_" + j]) for j in JOBS]
    if interactions:
        key = "late_" if late else "raid_"
        cols += [dm(df["f_" + j] * df[key + r]) for j in JOBS for r in RAIDS]
    return np.column_stack(cols)


SPLIT = sys.argv[2] == "-"
if SPLIT:
    everything, every_games = R.load([sys.argv[1]])
    train, test = everything[everything.seed % 2 == 0].copy(), everything[everything.seed % 2 == 1].copy()
    games_tr, games_te = every_games[every_games.seed % 2 == 0], every_games[every_games.seed % 2 == 1]
else:
    train, games_tr = R.load([sys.argv[1]])
    test, games_te = R.load([sys.argv[2]])
train, test = prepare(train), prepare(test)
y_tr, y_te = train.pts_c.values, test.pts_c.values

print(f"Allenamento: {games_tr.game.nunique()} partite; verifica: {games_te.game.nunique()} partite\n")
rows = []
for label, late in (("Retata presente (qualunque turno)", False), ("Retata presente ai turni 2-3 (quelli in cui costa di più)", True)):
    X_tr_main, X_te_main = design(train, False), design(test, False)
    X_tr_full, X_te_full = design(train, True, late), design(test, True, late)
    b_main = np.linalg.pinv(X_tr_main) @ y_tr
    b_full = np.linalg.pinv(X_tr_full, rcond=1e-8) @ y_tr
    def r2(y, yhat):
        yhat = yhat - pd.Series(yhat).groupby(test.game.values).transform("mean").values if len(yhat) == len(test) else yhat
        return 1 - ((y - yhat) ** 2).sum() / (y**2).sum()
    r2_main = r2(y_te, X_te_main @ b_main)
    r2_full = r2(y_te, X_te_full @ b_full)
    # significance of the gain: paired comparison of squared errors, clustered by game
    e_main = (y_te - (X_te_main @ b_main - pd.Series(X_te_main @ b_main).groupby(test.game.values).transform("mean").values))
    e_full = (y_te - (X_te_full @ b_full - pd.Series(X_te_full @ b_full).groupby(test.game.values).transform("mean").values))
    gain = pd.DataFrame({"game": test.game.values, "d": e_main**2 - e_full**2}).groupby("game").d.sum()
    z = gain.mean() / (gain.std() / np.sqrt(len(gain)))
    print(f"### {label}")
    print(f"R² sulle partite di verifica: solo i Job iniziali {100 * r2_main:.2f}%  →  con Job × Retata {100 * r2_full:.2f}%  (z della differenza = {z:+.1f})")
    print(f"  In media, l'errore quadratico per partita cala di {gain.mean():+.3f} (±{1.96 * gain.std() / np.sqrt(len(gain)):.3f})\n")

# ---------------------------------------------------------------- fit on everything and describe the interactions
allp, _ = R.load([sys.argv[1]] if SPLIT else [sys.argv[1], sys.argv[2]])
allp = prepare(allp)
y = allp.pts_c.values
g = allp.game.values
X = design(allp, True, False)
beta, V, r2_, adj = A.ols_cluster(y, X, g)
se = np.sqrt(np.diag(V))
off = len(JOBS)
print("## Interazione Job × Retata sui punti (scostamento dal valore medio del Job, quando la Retata è nella partita)")
print("| Job \\ Retata | " + " | ".join(R.RAID_NAME[r] for r in RAIDS) + " |")
print("|---|" + "---:|" * len(RAIDS))
sig = []
for a, j in enumerate(JOBS):
    cells = []
    for b_, r in enumerate(RAIDS):
        k = off + a * len(RAIDS) + b_
        z = abs(beta[k]) / se[k] if se[k] > 0 else 0
        star = "**" if z > 1.96 else ""
        mark = R.SYNERGY.get((j, r), "")
        cells.append(f"{star}{beta[k]:+.2f}{star}{(' ' + mark) if mark else ''}")
        if z > 1.96:
            sig.append((z, j, r, beta[k], se[k]))
    print(f"| {R.JOB_NAME[j]} | " + " | ".join(cells) + " |")
idx = list(range(off, X.shape[1]))
bb = beta[idx]
rank = int(np.linalg.matrix_rank(X[:, off:], tol=1e-8))
W = float(bb @ np.linalg.pinv(V[np.ix_(idx, idx)], rcond=1e-10) @ bb)
print(f"\nTest congiunto «nessuna interazione»: χ²({rank}) ≈ {W:.1f}, p ≈ {stats.chi2.sf(W, rank):.3g}")
print(f"Celle significative: {len(sig)} su {len(JOBS) * len(RAIDS)} (≈ {0.05 * len(JOBS) * len(RAIDS):.0f} per puro caso)")
for z, j, r, b, s in sorted(sig, reverse=True)[:12]:
    print(f"  - {R.JOB_NAME[j]} × {R.RAID_NAME[r]}: {b:+.2f} ±{1.96 * s:.2f}  {R.SYNERGY.get((j, r), '')}")

# ---------------------------------------------------------------- predicted advantage of every Job trio under every Raid triple
main_b = beta[:off]
inter_b = beta[off:].reshape(len(JOBS), len(RAIDS))
tiers = {1: ["job_01", "job_02", "job_07"], 2: ["job_04", "job_05", "job_06"], 3: ["job_03", "job_08", "job_09"]}
trios = list(product(tiers[1], tiers[2], tiers[3]))
rows = []
for triple in combinations(RAIDS, 3):
    present = np.array([1.0 if r in triple else 0.0 for r in RAIDS]) - PRESENCE
    for trio in trios:
        v = sum(main_b[JOBS.index(j)] for j in trio) + sum(inter_b[JOBS.index(j)] @ present for j in trio)
        base = sum(main_b[JOBS.index(j)] for j in trio)
        rows.append((triple, trio, v, base))
pred = pd.DataFrame(rows, columns=["triple", "trio", "pred", "base"])
pred["pred_c"] = pred.pred - pred.groupby("triple").pred.transform("mean")
pred["base_c"] = pred.base - pred.groupby("triple").base.transform("mean")
pred["dev"] = pred.pred_c - pred.base_c
print("\n## Quanto si spostano i vantaggi dei 27 trii di Job iniziali con la sequenza di Retate (modello Job × Retata, tutti i dati)")
print(f"- Senza Retate (solo effetti medi): trio migliore {pred.base_c.max():+.2f}, peggiore {pred.base_c.min():+.2f}, deviazione standard {pred.base_c.std():.2f}")
print(f"- Con la Retata: per ciascuna delle 35 triple la deviazione standard dei trii va da {pred.groupby('triple').pred_c.std().min():.2f} a {pred.groupby('triple').pred_c.std().max():.2f}")
print(f"- Lo scostamento dovuto alle Retate (stima − effetto medio): mediana {pred["dev"].abs().median():.2f}, 95° percentile {pred["dev"].abs().quantile(0.95):.2f}, massimo {pred["dev"].abs().max():.2f} punti")
top = pred.reindex(pred["dev"].abs().sort_values(ascending=False).index).head(8)
for _, row in top.iterrows():
    print(f"  - Retate {', '.join(R.RAID_NAME[r].split(' ')[0] for r in row.triple)} + trio {', '.join(j[-2:] for j in row.trio)}: effetto medio {row.base_c:+.2f}, con le Retate {row.pred_c:+.2f} (scostamento {row['dev']:+.2f})")
