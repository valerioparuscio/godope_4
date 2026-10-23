"""For every Raid: how much does the Job a player starts with (per tier) change his final points?

Points are relative to the average of the player's own table (game-clustered 95% intervals); the spread is
max - min of the three initial Jobs of the tier. The last row of each table is the same thing over all games,
so a Raid whose spread is clearly larger than that row is one that makes the starting Job matter more.

python raid_tables.py <games.jsonl[,more.jsonl]> [position 1|2|3|any]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402
import raidlib as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
paths = sys.argv[1].split(",")
positions = sys.argv[2].split(",") if len(sys.argv) > 2 else ["any", "1", "2", "3"]
df, games = R.load(paths)
print(f"{games.game.nunique()} partite, {len(df)} giocatori-partita\n")
tiers = {t: sorted(df[f"first{t}"].unique()) for t in (1, 2, 3)}
SHORT = {"raid_01": "+Links", "raid_02": "-Rats", "raid_03": "-Dope", "raid_04": "+Poker", "raid_05": "+Cops", "raid_06": "-$", "raid_07": "-Crimes"}
for pos in positions:
    title = "in qualunque turno" if pos == "any" else f"come {pos}ª Retata"
    print(f"# Retata uscita {title}\n")
    if pos == "any":
        present = {r: ((df.r1 == r) | (df.r2 == r) | (df.r3 == r)).values for r in R.RAID_NAME}
    else:
        present = {r: (df[f"r{pos}"] == r).values for r in R.RAID_NAME}
    for t, jobs in tiers.items():
        print(f"**Livello {t}**\n")
        print("| Retata (n partite) | " + " | ".join(R.JOB_NAME[j] for j in jobs) + " | scarto max−min |")
        print("|---|" + "---:|" * (len(jobs) + 1))
        spreads = {}
        for r, name in SHORT.items():
            mask_r = present[r]
            cells, means = [], []
            for j in jobs:
                m, se, n = A.cluster_mean(df, mask_r & (df[f"first{t}"] == j).values, "pts_c")
                cells.append(f"{m:+.2f} ±{1.96 * se:.2f}")
                means.append(m)
            spreads[r] = max(means) - min(means)
            print(f"| {name} ({df[mask_r].game.nunique()}) | " + " | ".join(cells) + f" | **{spreads[r]:.2f}** |")
        cells, means = [], []
        for j in jobs:
            m, se, n = A.cluster_mean(df, (df[f"first{t}"] == j).values, "pts_c")
            cells.append(f"{m:+.2f} ±{1.96 * se:.2f}")
            means.append(m)
        print(f"| tutte le partite | " + " | ".join(cells) + f" | {max(means) - min(means):.2f} |")
        extremes = sorted(spreads.items(), key=lambda kv: -kv[1])
        print(f"\nScarto maggiore con la Retata {SHORT[extremes[0][0]]} ({extremes[0][1]:.2f}), minore con {SHORT[extremes[-1][0]]} ({extremes[-1][1]:.2f}); "
              f"media sulle 7 Retate {np.mean(list(spreads.values())):.2f}.\n")
