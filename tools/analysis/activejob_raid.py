"""Job active at the start of a turn x Raid current in that turn.

For every (Job, Raid): how often the Job is completed during that turn, how many rounds it takes, how often the player
escapes the Raid, and the final points — each as a difference from the same Job's average over all the other Raids
(the Raid of a turn is random, so the difference is the Raid's effect). Compared with the designer's -5..+5 matrix.

python activejob_raid.py <jobs3.jsonl[,more]>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import lib3  # noqa: E402
import raidlib as R  # noqa: E402
from theory_matrix import COLS, NAMES, THEORY  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
pt, aj = lib3.load3(sys.argv[1].split(","))
JOBS = [j for j in THEORY if j in set(aj.job)]
print(f"{aj.game.nunique()} partite, {len(pt)} turni-giocatore, {len(aj)} Job attivi osservati\n")


def diff_vs_others(sub_all, job, raid, col):
    """mean(col | job active, raid current) - mean(col | job active, another raid), game-clustered SE."""
    s = sub_all[sub_all.job == job]
    a = (s.raid == raid).values
    y = s[col].values.astype(float)
    ok = ~np.isnan(y)
    g = pd.DataFrame({"game": s.game.values, "sa": np.where(a & ok, y, 0.0), "na": (a & ok).astype(float), "sb": np.where(~a & ok, y, 0.0), "nb": (~a & ok).astype(float)}).groupby("game").sum()
    if g.na.sum() < 30 or g.nb.sum() < 30:
        return np.nan, np.nan, int(g.na.sum())
    ma, mb = g.sa.sum() / g.na.sum(), g.sb.sum() / g.nb.sum()
    infl = (g.sa - ma * g.na) / g.na.sum() - (g.sb - mb * g.nb) / g.nb.sum()
    return ma - mb, float(np.sqrt((infl**2).sum())), int(g.na.sum())


aj["escape"] = 1 - aj.caught
aj["done_pp"] = aj.done * 100.0
aj["escape_pp"] = aj.escape * 100.0
# A Raid has its own average effect on everybody (some are simply easier to escape): take it out by measuring each
# outcome against the other players' Jobs of the same game and turn, so what is left is the Job x Raid part.
for col in ("done_pp", "escape_pp", "pts_c", "rc"):
    aj[col + "_t"] = aj[col] - aj.groupby(["game", "turn"])[col].transform("mean")

NAME = {"done_pp": "probabilità di completare il Job nel turno (punti percentuali)", "escape_pp": "probabilità di sfuggire alla Retata (punti percentuali)",
        "pts_c": "punti finali rispetto al tavolo (punti)", "rc": "round di completamento (se completato nel turno; meno round = più veloce)"}
mats = {}
for col in ("escape_pp", "done_pp", "pts_c", "rc"):
    M = np.full((len(JOBS), len(COLS)), np.nan)
    S = np.full_like(M, np.nan)
    print(f"## {NAME[col]}: differenza quando la Retata è quella del turno, rispetto alle altre Retate\n")
    print("| Job attivo | " + " | ".join(NAMES) + " |")
    print("|---|" + "---:|" * len(COLS))
    for a, j in enumerate(JOBS):
        cells = []
        for b, r in enumerate(COLS):
            d, s, n = diff_vs_others(aj, j, r, col + "_t")
            M[a, b], S[a, b] = d, s
            if np.isnan(d):
                cells.append("-")
            else:
                star = "**" if abs(d) > 1.96 * s else ""
                cells.append(f"{star}{d:+.1f}{star}" if col != "pts_c" and col != "rc" else f"{star}{d:+.2f}{star}")
        print(f"| {R.JOB_NAME[j]} | " + " | ".join(cells) + " |")
    print()
    mats[col] = (M, S)

theory = np.array([THEORY[j] for j in JOBS], float)
print("## Confronto con la matrice teorica (-5..+5)\n")
for col, label in (("escape_pp", "probabilità di sfuggire"), ("done_pp", "probabilità di completare il Job nel turno"), ("pts_c", "punti finali")):
    M, S = mats[col]
    ok = ~np.isnan(M.ravel())
    rho, p = stats.spearmanr(theory.ravel()[ok], M.ravel()[ok])
    r_, pr = stats.pearsonr(theory.ravel()[ok], M.ravel()[ok])
    print(f"- {label}: Pearson {r_:+.2f} (p={pr:.2g}), Spearman {rho:+.2f} (p={p:.2g}) su {ok.sum()} celle")
