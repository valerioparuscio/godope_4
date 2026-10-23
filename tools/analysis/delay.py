"""Rounds between a Job's reveal and its completion (among those who complete it), first Job of a tier versus later ones.

python delay.py label=file.jsonl[,file2.jsonl] [...]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import bankability as B  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
for arg in sys.argv[1:]:
    label, files = arg.split("=", 1)
    first, later = defaultdict(list), defaultdict(list)
    for path in files.split(","):
        for line in open(path, encoding="utf8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r["error"] or not r["finished"]:
                continue
            for p in r["players"].values():
                for tier in ("1", "2", "3"):
                    for e in B.timeline(p, tier):
                        if e["done"]:
                            (first if e["pos"] == 1 else later)[e["job"]].append(e["done_g"] - e["reveal_g"])
    print(f"## {label}: round (di 9) tra la rivelazione e il completamento, tra chi lo completa")
    print("| Job | se è il 1° (dall'inizio della partita) | se è 2°/3° | completamenti nello stesso round della rivelazione (2°/3°) |")
    print("|---|---:|---:|---:|")
    for job, name in B.JOB_NAME.items():
        lat = later[job]
        print(f"| {name} | {np.mean(first[job]):.1f} | {np.mean(lat):.1f} | {100 * np.mean([x == 0 for x in lat]):.0f}% |")
    print()
