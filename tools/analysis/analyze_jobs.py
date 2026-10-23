"""Impact of a player's Job sequence on his final points, from sim_jobs.py's JSONL.

Everything is measured *within the game* (points minus the table's average) so that the strength
of a particular game's draw of cards/market does not blur the comparison, and every uncertainty is
clustered by game (the four players of one game are not independent).

Usage: python analyze_jobs.py <games.jsonl> [report.md]
"""

from __future__ import annotations

import json
import sys
from itertools import permutations

import numpy as np
import pandas as pd
from scipy import stats

TITLE = {
    "job_01": "Vinci 1 Rissa",
    "job_02": "Abbi 1 Cop/Fed",
    "job_03": "2 Chip Poker",
    "job_04": "2 Rats",
    "job_05": "4 Dope nel Covo",
    "job_06": "4 Link",
    "job_07": "Criminali in 6 Hoods",
    "job_08": "10 Criminali fuori",
    "job_09": "30 dollari",
}
TIERS = {1: ["job_01", "job_02", "job_07"], 2: ["job_04", "job_05", "job_06"], 3: ["job_03", "job_08", "job_09"]}

OUT: list[str] = []


def say(text: str = "") -> None:
    print(text)
    OUT.append(text)


def load(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, comps = [], []
    for line in open(path, encoding="utf8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r["error"] or not r["finished"]:
            continue
        winners = r["winners"]
        for pid, p in r["players"].items():
            f = p["final"]
            seq = p["job_seq"]
            comp = p["completions"]
            row = dict(
                game=r["seed"], pid=pid, seat=p["seat"],
                pts=f["total_points"], money_pts=f["money_track_position_points"],
                clean_pts=f["clean_reputation_points"], stained_pts=f["stained_reputation_points"],
                maj_pts=f["contact_majority_points"], chip_pts=f["base_chip_points"],
                skill_pts=f["skill_points"], clean_cnt=f["tie_break_clean_reputation"],
                n_jobs=len(comp), win=(1.0 / len(winners)) if pid in winners else 0.0,
                first_completion_turn=min((c["turn"] for c in comp), default=np.nan),
            )
            for tier in (1, 2, 3):
                order = seq[str(tier)]
                row[f"first{tier}"] = order[0]
                row[f"second{tier}"] = order[1]
                row[f"order{tier}"] = ">".join(j[-2:] for j in order)
            rows.append(row)
            for tier in (1, 2, 3):
                order = seq[str(tier)]
                done = {c["job"]: c for c in comp}
                for pos, job in enumerate(order):
                    comps.append(dict(game=r["seed"], pid=pid, job=job, tier=tier, pos=pos,
                                      done=job in done, turn=done[job]["turn"] if job in done else np.nan))
    df = pd.DataFrame(rows)
    df["pts_c"] = df.pts - df.groupby("game").pts.transform("mean")
    df["win_c"] = df.win - df.groupby("game").win.transform("mean")
    return df, pd.DataFrame(comps)


def cluster_mean(df: pd.DataFrame, mask, y: str = "pts_c") -> tuple[float, float, int]:
    """Mean of y over the rows in `mask`, with a game-clustered standard error."""
    mask = np.asarray(mask, dtype=bool)
    g = pd.DataFrame({"game": df.game.values, "s": np.where(mask, df[y].values, 0.0), "n": mask.astype(float)}).groupby("game").sum()
    n = g.n.sum()
    m = g.s.sum() / n
    se = np.sqrt(((g.s - m * g.n) ** 2).sum()) / n
    return m, se, int(n)


def cluster_diff(df: pd.DataFrame, mask_a, mask_b, y: str = "pts_c") -> tuple[float, float]:
    """mean(y | a) - mean(y | b), game-clustered standard error."""
    mask_a, mask_b = np.asarray(mask_a, bool), np.asarray(mask_b, bool)
    g = pd.DataFrame({
        "game": df.game.values,
        "sa": np.where(mask_a, df[y].values, 0.0), "na": mask_a.astype(float),
        "sb": np.where(mask_b, df[y].values, 0.0), "nb": mask_b.astype(float),
    }).groupby("game").sum()
    ma, mb = g.sa.sum() / g.na.sum(), g.sb.sum() / g.nb.sum()
    infl = (g.sa - ma * g.na) / g.na.sum() - (g.sb - mb * g.nb) / g.nb.sum()
    return ma - mb, float(np.sqrt((infl**2).sum()))


def fmt(m: float, se: float, digits: int = 2) -> str:
    return f"{m:+.{digits}f} ±{1.96 * se:.{digits}f}"


def ols_cluster(y: np.ndarray, X: np.ndarray, groups: np.ndarray):
    """OLS (no intercept: y is already centred within game) with game-clustered covariance."""
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    e = y - X @ beta
    order = np.argsort(groups, kind="stable")
    gs = groups[order]
    starts = np.r_[0, np.flatnonzero(gs[1:] != gs[:-1]) + 1]
    scores = X[order] * e[order][:, None]
    meat_parts = np.add.reduceat(scores, starts, axis=0)
    meat = meat_parts.T @ meat_parts
    n_groups, k = len(starts), X.shape[1]
    V = xtx_inv @ meat @ xtx_inv * (n_groups / (n_groups - 1))
    sst = float((y**2).sum())
    r2 = 1 - float((e**2).sum()) / sst
    adj = 1 - (1 - r2) * (len(y) - 1) / (len(y) - k - 1)
    return beta, V, r2, adj


def wald(beta: np.ndarray, V: np.ndarray, idx: list[int]) -> tuple[float, int, float]:
    b = beta[idx]
    W = float(b @ np.linalg.pinv(V[np.ix_(idx, idx)]) @ b)
    return W, len(idx), float(stats.chi2.sf(W, len(idx)))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    path = sys.argv[1]
    df, comps = load(path)
    games = df.game.nunique()
    say(f"# Sequenza dei Job e punti finali — Easy Price, bot euristici\n")
    say(f"{games} partite ({len(df)} giocatori-partita), file `{path.split(chr(92))[-1].split('/')[-1]}`.\n")

    say("## 1. Quadro generale")
    say(f"- Punti finali per giocatore: media {df.pts.mean():.2f}, deviazione standard {df.pts.std():.2f}; "
        f"nella stessa partita la deviazione standard tra i 4 giocatori è {df.groupby('game').pts.std(ddof=0).mean():.2f}.")
    say(f"- Job completati per giocatore: media {df.n_jobs.mean():.2f}; nessun Job: {100 * (df.n_jobs == 0).mean():.0f}% dei giocatori.")
    by_n = df.groupby("n_jobs").agg(n=("pts", "size"), pts=("pts", "mean"), win=("win", "mean"))
    say("- Punti medi per numero di Job completati: " + "; ".join(f"{k} Job → {r.pts:.2f} pt (vince {100 * r.win:.0f}%, n={int(r.n)})" for k, r in by_n.iterrows()))
    seat_rows = []
    for st_ in sorted(df.seat.unique()):
        m, se, n = cluster_mean(df, (df.seat == st_).values)
        w, _, _ = cluster_mean(df, (df.seat == st_).values, "win")
        seat_rows.append(f"posto {st_}: {fmt(m, se)} pt, vince {100 * w:.1f}%")
    say("- Posizione al tavolo (punti rispetto alla media del tavolo): " + "; ".join(seat_rows))
    slope = np.polyfit(df.n_jobs, df.pts_c, 1)[0]
    say(f"- In media ogni Job completato in più vale circa {slope:+.2f} punti (a parità di partita).\n")

    say("## 2. Il primo Job di ogni livello (quello rivelato a inizio partita)")
    say("Punti rispetto alla media del proprio tavolo, e quota di vittorie (25% = pari). ± = intervallo di confidenza al 95%.\n")
    for tier, jobs in TIERS.items():
        say(f"**Livello {tier}**\n")
        say("| Job rivelato per primo | n | punti vs tavolo | vittorie | Job completati | lo completa |")
        say("|---|---:|---:|---:|---:|---:|")
        for j in jobs:
            mask = (df[f"first{tier}"] == j).values
            m, se, n = cluster_mean(df, mask)
            w, wse, _ = cluster_mean(df, mask, "win")
            nj, njse, _ = cluster_mean(df, mask, "n_jobs")
            c = comps[(comps.job == j) & (comps.pos == 0)]
            say(f"| {TITLE[j]} ({j[-2:]}) | {n} | {fmt(m, se)} | {100 * w:.1f}% ±{196 * wse:.1f} | {nj:.2f} | {100 * c.done.mean():.0f}% |")
        say("")
        pairs = [(a, b) for i, a in enumerate(jobs) for b in jobs[i + 1:]]
        for a, b in pairs:
            d, dse = cluster_diff(df, df[f"first{tier}"] == a, df[f"first{tier}"] == b)
            say(f"- {TITLE[a]} − {TITLE[b]}: {fmt(d, dse)} punti" + ("  ← **significativo**" if abs(d) > 1.96 * dse else ""))
        say("")

    say("## 3. Quanto pesa la sequenza nel suo insieme (modello con effetto-partita)")
    y = df.pts_c.values
    groups = df.game.values
    def design(cols: list[str], extra_perm: bool = False) -> tuple[np.ndarray, list[str]]:
        mats, names = [], []
        for c in cols:
            vals = sorted(df[c].unique())
            for v in vals[1:]:
                mats.append((df[c] == v).astype(float).values - (df[c] == v).groupby(df.game).transform("mean").values)
                names.append(f"{c}={v}")
        return np.column_stack(mats), names
    seat_X, seat_names = design(["seat"])
    first_cols = ["first1", "first2", "first3"]
    X0 = seat_X
    X1, n1 = design(first_cols)
    X1 = np.column_stack([seat_X, X1]); n1 = seat_names + n1
    b0, V0, r0, a0 = ols_cluster(y, X0, groups)
    b1, V1, r1, a1 = ols_cluster(y, X1, groups)
    idx_first = list(range(len(seat_names), len(n1)))
    W, k, p = wald(b1, V1, idx_first)
    say(f"- Solo la posizione al tavolo: R² nella partita {100 * r0:.2f}%.")
    say(f"- Posizione + Job iniziali dei 3 livelli: R² {100 * r1:.2f}% (corretto {100 * a1:.2f}%); effetto congiunto dei Job iniziali: χ²({k}) = {W:.1f}, p = {p:.3g}.")
    for tier in (1, 2, 3):
        idx = [i for i, nme in enumerate(n1) if nme.startswith(f"first{tier}=")]
        W, k, p = wald(b1, V1, idx)
        say(f"  - solo livello {tier}: χ²({k}) = {W:.1f}, p = {p:.3g}")
    # does the order *after* the first job matter? first + second job of every tier
    X2, n2 = design(["first1", "second1", "first2", "second2", "first3", "second3"])
    X2 = np.column_stack([seat_X, X2]); n2 = seat_names + n2
    b2, V2, r2, a2 = ols_cluster(y, X2, groups)
    say(f"- Posizione + primo e secondo Job di ogni livello: R² {100 * r2:.2f}% (corretto {100 * a2:.2f}%).")
    for tier in (1, 2, 3):
        idx = [i for i, nme in enumerate(n2) if nme.startswith(f"second{tier}=")]
        W, k, p = wald(b2, V2, idx)
        say(f"  - il secondo Job del livello {tier} (dato il primo): χ²({k}) = {W:.1f}, p = {p:.3g}")
    X3, n3 = design(["order1", "order2", "order3"])
    X3 = np.column_stack([seat_X, X3]); n3 = seat_names + n3
    b3, V3, r3, a3 = ols_cluster(y, X3, groups)
    say(f"- Posizione + ordine completo (6 ordini per livello): R² {100 * r3:.2f}% (corretto {100 * a3:.2f}%).\n")

    say("## 4. Le 27 combinazioni di Job iniziali (livello 1 · livello 2 · livello 3)")
    combo = df.first1.str[-2:] + "·" + df.first2.str[-2:] + "·" + df.first3.str[-2:]
    rows = []
    for c in sorted(combo.unique()):
        m, se, n = cluster_mean(df, (combo == c).values)
        w, _, _ = cluster_mean(df, (combo == c).values, "win")
        rows.append((m, se, n, c, w))
    rows.sort(reverse=True)
    say(f"Differenza tra la migliore e la peggiore: {rows[0][0] - rows[-1][0]:.2f} punti (con rumore di campionamento ±{1.96 * np.hypot(rows[0][1], rows[-1][1]):.2f}).")
    say("| combinazione | n | punti vs tavolo | vittorie |")
    say("|---|---:|---:|---:|")
    for m, se, n, c, w in rows[:5] + rows[-5:]:
        say(f"| {c} | {n} | {fmt(m, se)} | {100 * w:.1f}% |")
    combo_cols = sorted(combo.unique())
    C = np.column_stack([(combo == c).astype(float).values - (combo == c).groupby(df.game).transform("mean").values for c in combo_cols[1:]])
    Xc_, nc_ = np.column_stack([seat_X, C]), None
    bC, VC, rC, aC = ols_cluster(y, Xc_, groups)
    idx = list(range(seat_X.shape[1], Xc_.shape[1]))
    W, k, p = wald(bC, VC, idx)
    say(f"Test «le 27 combinazioni sono tutte uguali»: χ²({k}) = {W:.1f}, p = {p:.3g}. R² del modello a 27 combinazioni: {100 * rC:.2f}% (corretto {100 * aC:.2f}%).")
    # interactions only: combos residualised on the main effects of the three tiers
    Hm = X1 @ np.linalg.pinv(X1)
    Cperp = C - Hm @ C
    XI = np.column_stack([X1, Cperp])
    bI, VI, rI, aI = ols_cluster(y, XI, groups)
    rank_i = int(np.linalg.matrix_rank(Cperp, tol=1e-8))
    idx = list(range(X1.shape[1], XI.shape[1]))
    b_ = bI[idx]
    W_i = float(b_ @ np.linalg.pinv(VI[np.ix_(idx, idx)], rcond=1e-10) @ b_)
    say(f"Interazioni tra i tre livelli (oltre agli effetti singoli): χ²({rank_i}) ≈ {W_i:.1f}, p ≈ {stats.chi2.sf(W_i, rank_i):.3g}.\n")

    say("## 5. Perché: completamento dei Job in base alla posizione nella pila")
    say("| Job | lo completa se è il 1° | se è il 2° | se è il 3° | turno medio di completamento |")
    say("|---|---:|---:|---:|---:|")
    for tier, jobs in TIERS.items():
        for j in jobs:
            c = comps[comps.job == j]
            cells = [f"{100 * c[c.pos == p].done.mean():.0f}%" for p in (0, 1, 2)]
            say(f"| {TITLE[j]} (liv. {tier}) | {cells[0]} | {cells[1]} | {cells[2]} | {c.turn.mean():.2f} |")
    say("")

    say("## 6. Da dove viene la differenza di punti (primo Job del livello 3)")
    comps_cols = ["money_pts", "clean_pts", "stained_pts", "maj_pts", "chip_pts", "skill_pts"]
    df_comp = df.copy()
    for c in comps_cols:
        df_comp[c + "_c"] = df_comp[c] - df_comp.groupby("game")[c].transform("mean")
    say("| primo Job liv. 3 | " + " | ".join(c.replace("_pts", "") for c in comps_cols) + " | totale |")
    say("|---|" + "---:|" * (len(comps_cols) + 1))
    for j in TIERS[3]:
        mask = (df_comp.first3 == j).values
        cells = [fmt(*cluster_mean(df_comp, mask, c + "_c")[:2]) for c in comps_cols]
        say(f"| {TITLE[j]} | " + " | ".join(cells) + f" | {fmt(*cluster_mean(df, mask)[:2])} |")
    say("")
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
