"""How much of the spread of final points is explained by the initial Jobs, by the Raid sequence, and by the
Job x Raid interaction? Out-of-sample (5-fold by game), so that the many interaction terms cannot flatter the result.

Two views:
  total   - variance of a player's points around the grand mean (the Raids that come out change the whole table);
  within  - variance around the player's own table average (what decides who wins the game).

python variance_shares.py <games.jsonl[,more]> [label]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import raidlib as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
RAIDS = list(R.RAID_NAME)


def build(df):
    tiers = {t: sorted(df[f"first{t}"].unique()) for t in (1, 2, 3)}
    jobs = [j for t in (1, 2, 3) for j in tiers[t]]
    f = {j: ((df.first1 == j) | (df.first2 == j) | (df.first3 == j)).astype(float).values for j in jobs}
    # J: initial Jobs, two dummies per tier
    J = np.column_stack([f[j] for t in (1, 2, 3) for j in tiers[t][1:]])
    # R: which Raid came out in each of the three turns (six dummies per position)
    Rm = np.column_stack([(df[f"r{p}"] == r).astype(float).values for p in (1, 2, 3) for r in RAIDS[1:]])
    present = {r: ((df.r1 == r) | (df.r2 == r) | (df.r3 == r)).astype(float).values - 3 / 7 for r in RAIDS}
    JR = np.column_stack([f[j] * present[r] for j in jobs for r in RAIDS])
    return J, Rm, JR


def cv_r2(X, y, groups, k=5, seed=0):
    """Out-of-sample R² of ridge-free OLS (pinv), folds drawn by game."""
    rng = np.random.default_rng(seed)
    games = np.unique(groups)
    fold_of = dict(zip(games, rng.integers(0, k, len(games))))
    fold = np.array([fold_of[x] for x in groups])
    ss_res = ss_tot = 0.0
    for i in range(k):
        tr, te = fold != i, fold == i
        Xt = np.column_stack([np.ones(tr.sum()), X[tr]])
        b = np.linalg.pinv(Xt, rcond=1e-8) @ y[tr]
        pred = np.column_stack([np.ones(te.sum()), X[te]]) @ b
        ss_res += ((y[te] - pred) ** 2).sum()
        ss_tot += ((y[te] - y[tr].mean()) ** 2).sum()
    return 1 - ss_res / ss_tot


def shares(df, seed=0):
    J, Rm, JR = build(df)
    g = df.game.values
    out = {}
    for view, y in (("total", df.pts.values.astype(float)), ("within", df.pts_c.values)):
        out[view] = {
            "J": cv_r2(J, y, g, seed=seed),
            "R": cv_r2(Rm, y, g, seed=seed),
            "J+R": cv_r2(np.column_stack([J, Rm]), y, g, seed=seed),
            "J+R+JxR": cv_r2(np.column_stack([J, Rm, JR]), y, g, seed=seed),
        }
    return out


if __name__ == "__main__":
    paths = sys.argv[1].split(",")
    label = sys.argv[2] if len(sys.argv) > 2 else ""
    df, games = R.load(paths)
    s = shares(df)
    print(f"## {label}: {games.game.nunique()} partite\n")
    print("| Quota di varianza dei punti spiegata (fuori campione) | solo Job iniziali | solo sequenza di Retate | Job + Retate | + interazione Job × Retata | **interazione aggiunta** |")
    print("|---|---:|---:|---:|---:|---:|")
    for view, name in (("total", "rispetto alla media generale"), ("within", "rispetto alla media del proprio tavolo")):
        v = s[view]
        print(f"| {name} | {100 * v['J']:.1f}% | {100 * v['R']:.1f}% | {100 * v['J+R']:.1f}% | {100 * v['J+R+JxR']:.1f}% | **{100 * (v['J+R+JxR'] - v['J+R']):+.2f} pt** |")
