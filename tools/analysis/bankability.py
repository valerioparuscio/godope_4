"""How 'bankable' is each Job: can its requirement be met before the Job is revealed?

For every Job and every position in its tier's pile (1st / 2nd / 3rd):
  - how often it is completed once it has been revealed,
  - how often it is already satisfied at the moment it is revealed (completed in the very same command that completed
    the previous Job of the tier: the engine completes and reveals in a loop, so that is a chain completion),
  - how often it is completed within 3 action rounds of its reveal (a fair speed comparison between a first Job,
    revealed at the start, and a later one, which has fewer rounds left): only reveals with >= 3 rounds left count.

Usage: python bankability.py label=file.jsonl[,file2.jsonl] [...]
"""
import json
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
JOB_NAME = {"job_01": "Vinci 1 Rissa", "job_02": "1 Cop/Fed", "job_03": "2 Chip Poker", "job_04": "2 Rats", "job_05": "4 Dope nel Covo",
            "job_06": "4 Link", "job_07": "6 Hoods diversi", "job_08": "10 Criminali fuori", "job_09": "30 dollari"}


def g(c):
    return (c["turn"] - 1) * 3 + c["round"]


def timeline(p, tier):
    """One entry per position of the tier's pile: was it revealed, when, was it completed, and when."""
    seq = p["job_seq"][tier]
    done = {c["job"]: c for c in p["completions"]}
    out, prev = [], None
    for pos, job in enumerate(seq):
        revealed = pos == 0 or prev is not None
        reveal_g = 0 if pos == 0 else (g(prev) if prev else None)
        c = done.get(job) if revealed else None
        out.append(dict(job=job, pos=pos + 1, revealed=revealed, reveal_g=reveal_g, done=c is not None,
                        done_g=g(c) if c else None, immediate=bool(c and prev and c["step"] == prev["step"])))
        prev = c  # a Job that is not completed ends the chain
    return out


def analyse(paths):
    cell = defaultdict(Counter)  # (job, pos) -> counters
    chains = Counter()
    completions, immediate_by_job = Counter(), Counter()
    n_games = 0
    for path in paths:
        for line in open(path, encoding="utf8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r["error"] or not r["finished"]:
                continue
            n_games += 1
            for p in r["players"].values():
                for tier in ("1", "2", "3"):
                    run = 1
                    for e in timeline(p, tier):
                        c = cell[(e["job"], e["pos"])]
                        c["n"] += 1
                        if e["revealed"]:
                            c["revealed"] += 1
                            c["done"] += e["done"]
                            if e["pos"] > 1:
                                c["rev_later"] += 1
                                c["imm"] += e["immediate"]
                            if e["reveal_g"] <= 6:
                                c["w_n"] += 1
                                c["w_done"] += bool(e["done"] and e["done_g"] - e["reveal_g"] <= 3)
                        if e["done"]:
                            completions[e["job"]] += 1
                            immediate_by_job[e["job"]] += e["immediate"]
                        if e["immediate"]:
                            run += 1
                        elif run > 1:
                            chains[run] += 1
                            run = 1
                    if run > 1:
                        chains[run] += 1
    return cell, chains, completions, immediate_by_job, n_games


def pct(a, b):
    return f"{100 * a / b:.0f}% (n={b})" if b else "-"


def main():
    for arg in sys.argv[1:]:
        label, files = arg.split("=", 1)
        cell, chains, completions, imm_by_job, n_games = analyse(files.split(","))
        print(f"## {label}  ({n_games} partite)\n")
        print("| Job | completato se 1° | se 2° (già rivelato) | se 3° (già rivelato) | già soddisfatto alla rivelazione | completato entro 3 round dalla rivelazione: se 1° | se 2°/3° |")
        print("|---|---:|---:|---:|---:|---:|---:|")
        for job, name in JOB_NAME.items():
            c1, c2, c3 = (cell[(job, k)] for k in (1, 2, 3))
            later = Counter()
            for c in (c2, c3):
                later.update(c)
            print(f"| {name} | {pct(c1['done'], c1['revealed'])} | {pct(c2['done'], c2['revealed'])} | {pct(c3['done'], c3['revealed'])} | "
                  f"{pct(later['imm'], later['rev_later'])} | {pct(c1['w_done'], c1['w_n'])} | {pct(later['w_done'], later['w_n'])} |")
        total = sum(completions.values())
        n_imm = sum(imm_by_job.values())
        print(f"\n- Completamenti immediati alla rivelazione: {n_imm} su {total} ({100 * n_imm / total:.1f}%). "
              f"Catene nello stesso livello (Job completati nello stesso istante): " + ", ".join(f"{k} Job: {v}" for k, v in sorted(chains.items())) + ".")
        print("- Quota dei completamenti di ciascun Job che è immediata: " + ", ".join(f"{JOB_NAME[j]} {100 * imm_by_job[j] / completions[j]:.0f}%" for j in JOB_NAME if completions[j]) + ".\n")


if __name__ == "__main__":
    main()
