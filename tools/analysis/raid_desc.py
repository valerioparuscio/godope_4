import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402
import raidlib as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
df, games = R.load(sys.argv[1:])
print(f"{games.game.nunique()} partite, {len(df)} giocatori-partita\n")
print("## Quanto costa una Retata (macchie applicate) in base al turno e alla carta")
print("| Retata | uscita a T1 | a T2 | a T3 | macchie a testa se T1 / T2 / T3 | persa (squadra) | pareggi (tutti presi) |")
print("|---|---:|---:|---:|---|---:|---:|")
for rid, name in R.RAID_NAME.items():
    cells = []
    stains = []
    for t in (1, 2, 3):
        m = (df[f"r{t}"] == rid)
        cells.append(f"{100 * m.mean():.0f}%")
        stains.append(f"{df.loc[m, f'stain{t}'].mean():.2f}")
    # caught probability over all appearances
    caught = np.mean([df.loc[df[f"r{t}"] == rid, f"caught{t}"].mean() for t in (1, 2, 3)])
    ties = np.mean([df.loc[df[f"r{t}"] == rid, f"tie{t}"].mean() for t in (1, 2, 3)])
    print(f"| {name} | " + " | ".join(cells) + f" | {' / '.join(stains)} | {100 * caught:.0f}% | {100 * ties:.0f}% |")
print()
print(f"Macchie totali per giocatore: media {df.stains.mean():.2f}; REP macchiate a fine partita {df.stained_cnt.mean():.2f}; REP pulite {df.clean_cnt.mean():.2f}")
print(f"Punti persi per le macchie ≈ {df.stained_cnt.mean():.2f} a testa (una REP macchiata vale 1 invece di 2)")
print(f"Giocatori con almeno 1 macchia: {100 * (df.stains > 0).mean():.0f}%; con 3 o più: {100 * (df.stains >= 3).mean():.0f}%")
print("\nREP possedute (Job completati) nel momento di ciascuna Retata, media: "
      f"T1 {df.jobs_by_t1.mean():.2f}, T2 {df.jobs_by_t2.mean():.2f}, T3 {df.jobs_by_t3.mean():.2f}")
print("Macchie applicate in media a chi è preso: "
      f"T1 {df.loc[df.caught1 == 1, 'stain1'].mean():.2f} (di 1), T2 {df.loc[df.caught2 == 1, 'stain2'].mean():.2f} (di 2), T3 {df.loc[df.caught3 == 1, 'stain3'].mean():.2f} (di 3)")
print("Punti vs tavolo di chi viene preso 0/1/2/3 volte:")
for k in range(4):
    mask = ((df.caught1 + df.caught2 + df.caught3) == k).values
    m, se, n = A.cluster_mean(df.assign(game=df.game), mask, "pts_c") if False else (df.loc[mask, "pts_c"].mean(), df.loc[mask, "pts_c"].std() / np.sqrt(mask.sum()), mask.sum())
    print(f"  preso {k} volte: n={n}, punti vs tavolo {m:+.2f} ±{1.96 * se:.2f}")
