"""Player-turn tables from sim_jobs3.py output: which Job was active when each Raid was current, what happened in
that turn, and how the player's resources changed over it."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

RES = ["money", "in_base", "criminals", "links", "gamblers", "rats", "hand", "chips", "dope", "officers"]


def load3(paths):
    pt_rows, aj_rows = [], []
    for path in paths:
        for line in open(path, encoding="utf8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r["error"] or not r["finished"]:
                continue
            gid = f"{path.split('/')[-1].split(chr(92))[-1]}:{r['seed']}"
            resolved = [x for x in r["raids"] if x["event"] == "RaidResolved"]
            if len(resolved) != 3:
                continue
            pts = {pid: p["final"]["total_points"] for pid, p in r["players"].items()}
            mean_pts = float(np.mean(list(pts.values())))
            for pid, p in r["players"].items():
                by_turn = {x["turn"]: x for x in p["rounds"] if x["round"] == 1}
                if set(by_turn) != {1, 2, 3}:
                    continue
                end = p["end"]
                for t in (1, 2, 3):
                    start = by_turn[t]
                    nxt = by_turn.get(t + 1, end)
                    ev = resolved[t - 1]
                    caught = int(pid in ev["caught_team"])
                    row = dict(game=gid, seed=r["seed"], pid=pid, turn=t, raid=start["raid"], raid_resolved=ev["raid_card_id"], caught=caught, tie=int(not ev["escaping_team"]),
                               stains=ev["stain_count_applied"].get(pid, 0), pts_c=pts[pid] - mean_pts, pts=pts[pid])
                    for k in RES:
                        row["s_" + k] = start[k]
                        row["d_" + k] = nxt[k] - start[k]
                    pt_rows.append(row)
                    for tier, job in start["active"].items():
                        comp = [c for c in p["completions"] if c["job"] == job and c["turn"] == t]
                        aj_rows.append(dict(game=gid, seed=r["seed"], pid=pid, turn=t, raid=start["raid"], tier=int(tier), job=job, caught=caught,
                                            done=int(bool(comp)), rc=(comp[0]["round"] if comp else np.nan), pts_c=pts[pid] - mean_pts,
                                            **{"s_" + k: start[k] for k in RES}))
    return pd.DataFrame(pt_rows), pd.DataFrame(aj_rows)
