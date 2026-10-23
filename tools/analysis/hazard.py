"""Same calendar rounds, different position: is a Job easier to complete per round when it was revealed later?

Per-round completion probability ("hazard") in rounds 4-9, among Job instances that were already active at the start of
the round, split into Jobs active from the start of the game (1st of their tier) and Jobs revealed later (2nd/3rd).
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bankability as B  # noqa: E402
import json  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
for arg in sys.argv[1:]:
    label, files = arg.split("=", 1)
    exposure, events = Counter(), Counter()
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
                        if not e["revealed"]:
                            continue
                        kind = "first" if e["pos"] == 1 else "later"
                        for k in range(4, 10):
                            if e["reveal_g"] < k and (not e["done"] or e["done_g"] >= k):
                                exposure[(e["job"], kind)] += 1
                                if e["done"] and e["done_g"] == k:
                                    events[(e["job"], kind)] += 1
    print(f"## {label}: probabilità di completare il Job in un round (round 4-9), se era già attivo all'inizio del round\n")
    print("| Job | attivo dall'inizio (1°) | rivelato dopo (2°/3°) | rapporto |")
    print("|---|---:|---:|---:|")
    for job, name in B.JOB_NAME.items():
        h1 = events[(job, "first")] / exposure[(job, "first")] if exposure[(job, "first")] else float("nan")
        h2 = events[(job, "later")] / exposure[(job, "later")] if exposure[(job, "later")] else float("nan")
        print(f"| {name} | {100 * h1:.1f}% (n={exposure[(job, 'first')]}) | {100 * h2:.1f}% (n={exposure[(job, 'later')]}) | {h2 / h1:.2f}× |")
    print()
