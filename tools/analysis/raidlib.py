"""Loader joining Job draws, Raid sequence and outcomes (player-game and game level)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

RAID_NAME = {
    "raid_01": "Ganci (più Link)",
    "raid_02": "Prigione (meno Rats)",
    "raid_03": "Merci (meno valore)",
    "raid_04": "Poker (più Chip)",
    "raid_05": "Cop/Fed (più in Covo)",
    "raid_06": "Soldi (meno $)",
    "raid_07": "Quartieri (meno Criminali)",
}
JOB_NAME = {
    "job_01": "Vinci 1 Rissa", "job_02": "1 Cop/Fed", "job_03": "2 Chip Poker", "job_04": "2 Rats", "job_05": "4 Dope nel Covo",
    "job_06": "4 Link", "job_07": "6 Hoods diversi", "job_08": "10 Criminali fuori", "job_09": "30 dollari",
}
# which raid rewards / punishes the thing a Job asks for (my reading of the criteria)
SYNERGY = {("job_02", "raid_05"): "+", ("job_03", "raid_04"): "+", ("job_06", "raid_01"): "+",
           ("job_04", "raid_02"): "-", ("job_05", "raid_03"): "-", ("job_07", "raid_07"): "-", ("job_08", "raid_07"): "-", ("job_09", "raid_06"): "-"}


def load(paths: list[str]):
    rows = []
    games = []
    for path in paths:
        for line in open(path, encoding="utf8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r["error"] or not r["finished"]:
                continue
            resolved = [x for x in r["raids"] if x["event"] == "RaidResolved"]
            if len(resolved) != 3:
                continue
            seq = [x["raid_card_id"] for x in resolved]
            gid = f"{path.split('/')[-1].split(chr(92))[-1]}:{r['seed']}"
            games.append(dict(game=gid, seed=r["seed"], r1=seq[0], r2=seq[1], r3=seq[2],
                              tie1=not resolved[0]["escaping_team"], tie2=not resolved[1]["escaping_team"], tie3=not resolved[2]["escaping_team"]))
            for pid, p in r["players"].items():
                f = p["final"]
                row = dict(game=gid, seed=r["seed"], pid=pid, seat=p["seat"], pts=f["total_points"], n_jobs=len(p["completions"]),
                           clean_cnt=f["tie_break_clean_reputation"], stained_cnt=f["stained_reputation_points"],
                           clean_pts=f["clean_reputation_points"], money_pts=f["money_track_position_points"],
                           win=(1.0 / len(r["winners"])) if pid in r["winners"] else 0.0,
                           r1=seq[0], r2=seq[1], r3=seq[2])
                for t in (1, 2, 3):
                    x = resolved[t - 1]
                    row[f"caught{t}"] = int(pid in x["caught_team"])
                    row[f"stain{t}"] = x["stain_count_applied"].get(pid, 0)
                    row[f"tie{t}"] = int(not x["escaping_team"])
                    row[f"first{t}"] = p["job_seq"][str(t)][0]
                # REP the player held when each raid hit (completed jobs by that turn) — completions are timed
                for t in (1, 2, 3):
                    row[f"jobs_by_t{t}"] = sum(1 for c in p["completions"] if c["turn"] <= t)
                rows.append(row)
    df = pd.DataFrame(rows)
    df["pts_c"] = df.pts - df.groupby("game").pts.transform("mean")
    df["win_c"] = df.win - df.groupby("game").win.transform("mean")
    df["stains"] = df.stain1 + df.stain2 + df.stain3
    return df, pd.DataFrame(games)
