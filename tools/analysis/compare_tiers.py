"""Side-by-side comparison of Job groupings: how unfair is the starting hand under each?

Usage: python compare_tiers.py label=games.jsonl [label=games.jsonl ...]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def dummies(df, cols):
    mats = []
    for c in cols:
        for v in sorted(df[c].unique())[1:]:
            ind = (df[c] == v).astype(float)
            mats.append(ind.values - ind.groupby(df.game).transform("mean").values)
    return np.column_stack(mats)


def summarize(path):
    df, comps = A.load(path)
    y, g = df.pts_c.values, df.game.values
    tiers = {t: sorted(df[f"first{t}"].unique()) for t in (1, 2, 3)}
    seat = dummies(df, ["seat"])
    X1 = np.column_stack([seat, dummies(df, ["first1", "first2", "first3"])])
    _, _, r2_first, _ = A.ols_cluster(y, X1, g)
    combo = df.first1 + "|" + df.first2 + "|" + df.first3
    rows = []
    for c in sorted(combo.unique()):
        m, se, n = A.cluster_mean(df, (combo == c).values)
        w, _, _ = A.cluster_mean(df, (combo == c).values, "win")
        rows.append((m, se, n, c, w))
    means = np.array([r[0] for r in rows]); ses = np.array([r[1] for r in rows]); ns = np.array([r[2] for r in rows], float)
    wmean = (means * ns).sum() / ns.sum()
    var = ((means - wmean) ** 2 * ns).sum() / ns.sum()
    true_sd = float(np.sqrt(max(0.0, var - (ses**2).mean())))
    per_tier = {}
    for t, jobs in tiers.items():
        stats_ = []
        for j in jobs:
            m, se, n = A.cluster_mean(df, (df[f"first{t}"] == j).values)
            w, _, _ = A.cluster_mean(df, (df[f"first{t}"] == j).values, "win")
            c = comps[(comps.job == j) & (comps.pos == 0)].done.mean()
            stats_.append((j, m, se, w, c))
        per_tier[t] = stats_
    return dict(
        games=df.game.nunique(), pts=df.pts.mean(), sd=df.pts.std(), jobs=df.n_jobs.mean(), zero=(df.n_jobs == 0).mean(),
        r2_first=r2_first, spread=max(means) - min(means), true_sd=true_sd,
        best=max(rows), worst=min(rows), per_tier=per_tier,
    )


def main():
    items = [a.split("=", 1) for a in sys.argv[1:]]
    res = {label: summarize(path) for label, path in items}
    labels = list(res)
    print("| | " + " | ".join(labels) + " |")
    print("|---|" + "---:|" * len(labels))
    def row(name, f):
        print(f"| {name} | " + " | ".join(f(res[l]) for l in labels) + " |")
    row("partite", lambda r: str(r["games"]))
    row("punti medi (dev. std.)", lambda r: f"{r['pts']:.2f} ({r['sd']:.2f})")
    row("Job completati a testa", lambda r: f"{r['jobs']:.2f}")
    row("giocatori senza Job", lambda r: f"{100 * r['zero']:.0f}%")
    row("varianza spiegata dai 3 Job iniziali (R²)", lambda r: f"{100 * r['r2_first']:.1f}%")
    row("scarto reale tra combinazioni (dev. std.)", lambda r: f"{r['true_sd']:.2f} pt")
    row("migliore − peggiore combinazione", lambda r: f"{r['spread']:.2f} pt")
    for t in (1, 2, 3):
        row(f"livello {t}: Job (completato se 1°)", lambda r, t=t: ", ".join(f"{j[-2:]} {100 * c:.0f}%" for j, m, se, w, c in r["per_tier"][t]))
        row(f"livello {t}: punti vs tavolo", lambda r, t=t: ", ".join(f"{j[-2:]} {m:+.2f}" for j, m, se, w, c in r["per_tier"][t]))
        row(f"livello {t}: vittorie", lambda r, t=t: ", ".join(f"{j[-2:]} {100 * w:.0f}%" for j, m, se, w, c in r["per_tier"][t]))
        row(f"livello {t}: scarto tra primi Job", lambda r, t=t: f"{max(m for _, m, *_ in r['per_tier'][t]) - min(m for _, m, *_ in r['per_tier'][t]):.2f} pt")
        row(f"livello {t}: completamento medio se 1°", lambda r, t=t: f"{100 * np.mean([c for *_, c in r['per_tier'][t]]):.0f}%")


if __name__ == "__main__":
    main()
