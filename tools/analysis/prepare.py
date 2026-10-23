"""Do the Raids prepare Jobs that have not been revealed yet?

Part 1  What a Raid makes the players do: change of every resource over the turn in which that Raid is the current
        one (money, chips, Links, Cops/Feds in the Covo, Dope, Criminals on the map, Rats...), against the other Raids
        (turn fixed). The designer's expectation: +Poker -> chips, +Links -> Links, +Cops -> officers, -$ -> less money...
Part 2  Do the matching Jobs, once revealed later, get completed faster because of it? For the Poker, Cops/Feds and
        Links Jobs revealed as 2nd/3rd: share already satisfied at the reveal, and completed within 3 rounds, split by
        whether the matching Raid was current at the reveal (or came the turn before).

python prepare.py <jobs3.jsonl[,more]>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import analyze_jobs as A  # noqa: E402
import lib3  # noqa: E402
import raidlib as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
paths = sys.argv[1].split(",")
pt, aj = lib3.load3(paths)
print(f"{pt.game.nunique()} partite, {len(pt)} turni-giocatore\n")
RAIDS = ["raid_01", "raid_02", "raid_03", "raid_04", "raid_05", "raid_06", "raid_07"]
SHORT = {"raid_01": "+Links", "raid_02": "-Rats", "raid_03": "-Dope", "raid_04": "+Poker", "raid_05": "+Cops", "raid_06": "-$", "raid_07": "-Crimes"}
RES = [("chips", "chip Poker"), ("links", "Link"), ("officers", "Cop/Fed nel Covo"), ("money", "denaro"), ("dope", "Dope nel Covo"),
       ("criminals", "Criminali nei Quartieri"), ("rats", "Rats"), ("in_base", "pedine in base"), ("hand", "carte")]
EXPECT = {("raid_04", "chips"): "+", ("raid_01", "links"): "+", ("raid_05", "officers"): "+", ("raid_06", "money"): "-",
          ("raid_03", "dope"): "-", ("raid_07", "criminals"): "-", ("raid_02", "rats"): "-"}

print("## 1. Cosa cambia durante il turno di una Retata (variazione di ciascuna risorsa dall'inizio alla fine del turno, rispetto alle altre Retate)\n")
print("| Retata corrente | " + " | ".join(n for _, n in RES) + " |")
print("|---|" + "---:|" * len(RES))
for r in RAIDS:
    cells = []
    for key, _ in RES:
        col = "d_" + key
        # turn-fixed: subtract the mean change of that turn over all players
        y = pt[col] - pt.groupby("turn")[col].transform("mean")
        mask = (pt.raid == r).values
        g = pd.DataFrame({"game": pt.game.values, "s": np.where(mask, y.values, 0.0), "n": mask.astype(float)}).groupby("game").sum()
        m = g.s.sum() / g.n.sum()
        se = np.sqrt(((g.s - m * g.n) ** 2).sum()) / g.n.sum()
        star = "**" if abs(m) > 1.96 * se else ""
        mark = EXPECT.get((r, key), "")
        cells.append(f"{star}{m:+.2f}{star}{(' (' + mark + ' atteso)') if mark else ''}")
    print(f"| {SHORT[r]} | " + " | ".join(cells) + " |")
print("\n(variazione media per giocatore e per turno; in grassetto oltre il 95%)\n")

# ------------------------------------------------------------------ part 2
MATCH = {"job_03": ("raid_04", "chips", "Poker"), "job_06": ("raid_01", "links", "Link"), "job_02": ("raid_05", "officers", "Cop/Fed")}
rows = []
for path in paths:
    for line in open(path, encoding="utf8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r["error"] or not r["finished"]:
            continue
        for pid, p in r["players"].items():
            raid_of = {x["turn"]: x["raid"] for x in p["rounds"] if x["round"] == 1}
            start = {x["turn"]: x for x in p["rounds"] if x["round"] == 1}
            done = {c["job"]: c for c in p["completions"]}
            for tier in ("1", "2", "3"):
                seq = p["job_seq"][tier]
                for pos in (1, 2):
                    prev_job, job = seq[pos - 1], seq[pos]
                    if prev_job not in done or job not in MATCH:
                        continue
                    pc = done[prev_job]
                    t = pc["turn"]
                    if t not in raid_of:
                        continue
                    c = done.get(job)
                    rg = (pc["turn"] - 1) * 3 + pc["round"]
                    rows.append(dict(game=r["seed"], job=job, turn=t, raid_now=raid_of[t], raid_before=raid_of.get(t - 1),
                                     immediate=int(bool(c and c["step"] == pc["step"])),
                                     w3=int(bool(c and (c["turn"] - 1) * 3 + c["round"] - rg <= 3)) if rg <= 6 else np.nan,
                                     res=start[t][MATCH[job][1]]))
d = pd.DataFrame(rows)
print("## 2. I Job Poker / Cop-Fed / Link rivelati per secondi o terzi: li prepara la Retata corrispondente?\n")
print("| Job rivelato dopo | n | già soddisfatto alla rivelazione: Retata corrispondente in corso | altre Retate | entro 3 round: corrispondente | altre | risorsa a inizio turno: corrispondente | altre |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for job, (raid, key, name) in MATCH.items():
    s = d[d.job == job]
    if s.empty:
        continue
    a = s.raid_now == raid
    def pc(x):
        return f"{100 * x.mean():.1f}% (n={len(x)})" if len(x) else "-"
    print(f"| {R.JOB_NAME[job]} | {len(s)} | {pc(s[a].immediate)} | {pc(s[~a].immediate)} | {pc(s[a].w3.dropna())} | {pc(s[~a].w3.dropna())} | {s[a].res.mean():.2f} | {s[~a].res.mean():.2f} |")
print("\nStessa domanda, con la Retata corrispondente uscita nel turno *precedente* alla rivelazione:\n")
print("| Job rivelato dopo | già soddisfatto: Retata corrispondente prima | altre | entro 3 round: corrispondente prima | altre |")
print("|---|---:|---:|---:|---:|")
for job, (raid, key, name) in MATCH.items():
    s = d[(d.job == job) & d.raid_before.notna()]
    if s.empty:
        continue
    a = s.raid_before == raid
    def pc(x):
        return f"{100 * x.mean():.1f}% (n={len(x)})" if len(x) else "-"
    print(f"| {R.JOB_NAME[job]} | {pc(s[a].immediate)} | {pc(s[~a].immediate)} | {pc(s[a].w3.dropna())} | {pc(s[~a].w3.dropna())} |")
