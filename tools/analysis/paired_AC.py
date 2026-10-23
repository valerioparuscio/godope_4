"""Two Job layouts (say A and C) on the same seeds: same prices, setup and Raid sequence; only the Jobs' tiers differ.

Out-of-sample (5 folds by seed, the same for both configurations) share of the variance of final points explained by the
initial Jobs, the Raid sequence, both, and the Job x Raid interaction; best-worst starting combination; jobs per player.
Paired bootstrap over seeds for every A - C difference.

python paired_AC.py <first-layout.jsonl[,..]> <second-layout.jsonl[,..]>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import raidlib as R  # noqa: E402
import variance_shares as V  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
B = 1000
rng = np.random.default_rng(1)


def prepare(paths):
    df, games = R.load(paths.split(","))
    return df, games


def cv_sums(X, y, df, k=5):
    """Per game: (sum of squared out-of-fold residuals, sum of squared deviations from the training mean)."""
    fold = (df.seed.values % k)
    res = np.zeros(len(df)); dev = np.zeros(len(df))
    for i in range(k):
        tr, te = fold != i, fold == i
        Xt = np.column_stack([np.ones(tr.sum()), X[tr]])
        b = np.linalg.pinv(Xt, rcond=1e-8) @ y[tr]
        pred = np.column_stack([np.ones(te.sum()), X[te]]) @ b
        res[te] = (y[te] - pred) ** 2
        dev[te] = (y[te] - y[tr].mean()) ** 2
    return pd.DataFrame({"seed": df.seed.values, "res": res, "dev": dev}).groupby("seed").sum()


def block_sums(df):
    J, Rm, JR = V.build(df)
    out = {}
    for view, y in (("total", df.pts.values.astype(float)), ("within", df.pts_c.values)):
        for name, X in (("J", J), ("R", Rm), ("J+R", np.column_stack([J, Rm])), ("J+R+JxR", np.column_stack([J, Rm, JR]))):
            out[(view, name)] = cv_sums(X, y, df)
    return out


dfA, gA = prepare(sys.argv[1])
dfC, gC = prepare(sys.argv[2])
common = sorted(set(dfA.seed) & set(dfC.seed))
dfA = dfA[dfA.seed.isin(common)].reset_index(drop=True)
dfC = dfC[dfC.seed.isin(common)].reset_index(drop=True)
print(f"Seed in comune: {len(common)} (A: {dfA.game.nunique()} partite, C: {dfC.game.nunique()})\n")
sums = {"A": block_sums(dfA), "C": block_sums(dfC)}
seeds = np.array(common)
idx = rng.integers(0, len(seeds), size=(B, len(seeds)))


def r2_boot(key, cfg):
    s = sums[cfg][key].reindex(seeds)
    res, dev = s.res.values, s.dev.values
    point = 1 - res.sum() / dev.sum()
    boot = 1 - res[idx].sum(axis=1) / dev[idx].sum(axis=1)
    return point, boot


rows = []
for view, label in (("total", "rispetto alla media generale"), ("within", "rispetto alla media del proprio tavolo")):
    print(f"### Quota di varianza spiegata {label} (fuori campione, IC 95% con bootstrap sui seed)\n")
    print("| | A | C | A − C |")
    print("|---|---:|---:|---:|")
    for name, desc in (("J", "Job iniziali"), ("R", "sequenza di Retate"), ("J+R", "Job + Retate"), ("J+R+JxR", "Job + Retate + interazione")):
        pa, ba = r2_boot((view, name), "A")
        pc, bc = r2_boot((view, name), "C")
        d = ba - bc
        print(f"| {desc} | {100 * pa:.1f}% [{100 * np.percentile(ba, 2.5):.1f}, {100 * np.percentile(ba, 97.5):.1f}] | {100 * pc:.1f}% [{100 * np.percentile(bc, 2.5):.1f}, {100 * np.percentile(bc, 97.5):.1f}] | {100 * (pa - pc):+.2f} [{100 * np.percentile(d, 2.5):+.2f}, {100 * np.percentile(d, 97.5):+.2f}] |")
    pa1, ba1 = r2_boot((view, "J+R"), "A"); pa2, ba2 = r2_boot((view, "J+R+JxR"), "A")
    pc1, bc1 = r2_boot((view, "J+R"), "C"); pc2, bc2 = r2_boot((view, "J+R+JxR"), "C")
    inc_a, inc_c = ba2 - ba1, bc2 - bc1
    print(f"| **interazione Job × Retata aggiunta** | {100 * (pa2 - pa1):+.2f} pt | {100 * (pc2 - pc1):+.2f} pt | {100 * ((pa2 - pa1) - (pc2 - pc1)):+.2f} [{100 * np.percentile(inc_a - inc_c, 2.5):+.2f}, {100 * np.percentile(inc_a - inc_c, 97.5):+.2f}] |\n")

# best - worst combination, jobs per player, mean points
def per_game_combo(df):
    combo = df.first1 + "|" + df.first2 + "|" + df.first3
    s = df.assign(combo=combo).groupby(["seed", "combo"]).pts_c.agg(["sum", "count"]).reset_index()
    S = s.pivot(index="seed", columns="combo", values="sum").reindex(seeds).fillna(0.0)
    N = s.pivot(index="seed", columns="combo", values="count").reindex(seeds).fillna(0.0)
    return S.values, N.values


def spread_boot(df):
    S, N = per_game_combo(df)
    W = np.zeros((B, len(seeds)))
    for b in range(B):
        np.add.at(W[b], idx[b], 1)
    means = (W @ S) / np.maximum(W @ N, 1)
    point = (S.sum(0) / np.maximum(N.sum(0), 1))
    return point.max() - point.min(), means.max(axis=1) - means.min(axis=1)


pa, ba = spread_boot(dfA); pc, bc = spread_boot(dfC)
print(f"### Migliore − peggiore combinazione iniziale (punti rispetto al tavolo)\n")
print(f"- A {pa:.2f} [{np.percentile(ba, 2.5):.2f}, {np.percentile(ba, 97.5):.2f}]; C {pc:.2f} [{np.percentile(bc, 2.5):.2f}, {np.percentile(bc, 97.5):.2f}]; A − C {pa - pc:+.2f} [{np.percentile(ba - bc, 2.5):+.2f}, {np.percentile(ba - bc, 97.5):+.2f}]\n")
for col, label in (("n_jobs", "Job completati a testa"), ("pts", "punti medi")):
    a = dfA.groupby("seed")[col].mean().reindex(seeds).values; c = dfC.groupby("seed")[col].mean().reindex(seeds).values
    d = a - c
    boot = d[idx].mean(axis=1)
    print(f"- {label}: A {a.mean():.2f}, C {c.mean():.2f}, differenza {d.mean():+.3f} [{np.percentile(boot, 2.5):+.3f}, {np.percentile(boot, 97.5):+.3f}]")
corr = np.corrcoef(dfA.groupby("seed").pts.mean().reindex(seeds), dfC.groupby("seed").pts.mean().reindex(seeds))[0, 1]
print(f"\nEfficacia dell'appaiamento: correlazione tra A e C dei punti medi della stessa partita {corr:+.2f}")
