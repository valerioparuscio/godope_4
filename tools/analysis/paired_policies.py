"""Same Job layout, same seeds (so the same Raid sequence and setup), two bot policies: what changes?

Built for "the bots weigh the Raid criterion four times as much" against the default, but any two runs of one layout on
the same seeds will do. Paired bootstrap over seeds for every difference (variant - base).

  1. How the players' resources respond to the Raid of the turn: change over the turn of the resource each Raid asks
     for, against the other Raids of the same turn index (chips for +Poker, Links for +Links, Cops/Feds for +Cops, less
     money for -$, less Dope for -Dope, fewer Criminals for -Crimes, fewer Rats for -Rats).
  2. What the Raids do to the players: stains, times caught, ties.
  3. Jobs completed and points.

python paired_policies.py <base.jsonl[,..]> <variant.jsonl[,..]> [label]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import lib3  # noqa: E402
import raidlib as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
B = 1000
rng = np.random.default_rng(7)
base_paths, var_paths = sys.argv[1].split(","), sys.argv[2].split(",")
label = sys.argv[3] if len(sys.argv) > 3 else ""

pt_b, _ = lib3.load3(base_paths)
pt_v, _ = lib3.load3(var_paths)
df_b, _ = R.load(base_paths)
df_v, _ = R.load(var_paths)
seeds = np.array(sorted(set(pt_b.seed) & set(pt_v.seed)))
idx = rng.integers(0, len(seeds), size=(B, len(seeds)))
print(f"## {label}: {len(seeds)} seed in comune (stessa sequenza di Retate e stesso setup)\n")

SHORT = {"raid_01": "+Links", "raid_02": "-Rats", "raid_03": "-Dope", "raid_04": "+Poker", "raid_05": "+Cops", "raid_06": "-$", "raid_07": "-Crimes"}
EXPECT = [("raid_04", "chips", "chip Poker (+Poker)"), ("raid_01", "links", "Link (+Links)"), ("raid_05", "officers", "Cop/Fed nel Covo (+Cops)"),
          ("raid_06", "money", "denaro (-$)"), ("raid_03", "dope", "Dope nel Covo (-Dope)"), ("raid_07", "criminals", "Criminali nei Quartieri (-Crimes)"),
          ("raid_02", "rats", "Rats (-Rats)")]


def per_seed(pt, raid, res):
    """Per seed: sum and count of the turn-fixed change of `res` over turns where `raid` is the current Raid."""
    y = pt["d_" + res] - pt.groupby("turn")["d_" + res].transform("mean")
    m = (pt.raid == raid)
    g = pd.DataFrame({"seed": pt.seed.values, "s": np.where(m, y.values, 0.0), "n": m.astype(float).values}).groupby("seed").sum().reindex(seeds).fillna(0.0)
    return g.s.values, g.n.values


def est(s, n):
    point = s.sum() / n.sum()
    boot = s[idx].sum(axis=1) / n[idx].sum(axis=1)
    return point, boot


print("### 1. Risposta delle risorse alla Retata del turno (variazione nel turno, rispetto alle altre Retate; IC 95% sui seed)\n")
print("| Retata → risorsa | base | variante | differenza |")
print("|---|---:|---:|---:|")
for raid, res, name in EXPECT:
    pb, bb = est(*per_seed(pt_b, raid, res))
    pv, bv = est(*per_seed(pt_v, raid, res))
    d = bv - bb
    print(f"| {name} | {pb:+.3f} | {pv:+.3f} | {pv - pb:+.3f} [{np.percentile(d, 2.5):+.3f}, {np.percentile(d, 97.5):+.3f}] |")
print()


def seed_mean(df, col):
    return df.groupby("seed")[col].mean().reindex(seeds).values


def line(name, a, b, fmt="{:.3f}"):
    d = b - a
    boot = d[idx].mean(axis=1)
    print(f"| {name} | {fmt.format(a.mean())} | {fmt.format(b.mean())} | {d.mean():+.3f} [{np.percentile(boot, 2.5):+.3f}, {np.percentile(boot, 97.5):+.3f}] |")


print("### 2. Cosa fanno le Retate ai giocatori\n")
print("| | base | variante | differenza |")
print("|---|---:|---:|---:|")
for df in (df_b, df_v):
    df["caught_n"] = df.caught1 + df.caught2 + df.caught3
    df["ties_n"] = df.tie1 + df.tie2 + df.tie3
line("macchie inflitte dalle Retate per giocatore", seed_mean(df_b, "stains"), seed_mean(df_v, "stains"))
line("volte preso per giocatore (su 3)", seed_mean(df_b, "caught_n"), seed_mean(df_v, "caught_n"))
line("Retate finite in pareggio (su 3)", seed_mean(df_b, "ties_n"), seed_mean(df_v, "ties_n"))
print()
print("### 3. Job e punti\n")
print("| | base | variante | differenza |")
print("|---|---:|---:|---:|")
line("Job completati a testa", seed_mean(df_b, "n_jobs"), seed_mean(df_v, "n_jobs"), "{:.2f}")
line("punti medi", seed_mean(df_b, "pts"), seed_mean(df_v, "pts"), "{:.2f}")
line("REP macchiate a fine partita", seed_mean(df_b, "stained_cnt"), seed_mean(df_v, "stained_cnt"), "{:.2f}")
