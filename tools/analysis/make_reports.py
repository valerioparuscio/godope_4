"""Regenerates every report of the Job / Raid studies from the datasets in analysis_data/ into docs/analysis/reports/.

    python tools/analysis/make_reports.py            # everything whose datasets exist
    python tools/analysis/make_reports.py 07 10      # only the reports whose file name starts with 07 or 10

The datasets (analysis_data/, not versioned) are produced by simulate.py; docs/analysis/README.md says which run is
which. Each report is the text printed by one analysis script, so the command that makes it is the list below.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
DATA = REPO / "analysis_data"
OUT = REPO / "docs" / "analysis" / "reports"

CUR1 = "current_layout/heuristic_v1_seeds1000-3999.jsonl"
CUR2 = "current_layout/heuristic_v2_seeds100000-101499.jsonl"
A2, A3 = "layout_A/heuristic_v2_seeds300000-300999.jsonl", "layout_A/heuristic_v3_seeds500000-501999.jsonl"
C2, C3 = "layout_C/heuristic_v2_seeds400000-400999.jsonl", "layout_C/heuristic_v3_seeds500000-501999.jsonl"
REWARD = "reward_preference/mix_v2_seeds200000-201199.jsonl"
HI, LO = "bot_variants/jobs_hi_v1_seeds20000-20699.jsonl", "bot_variants/jobs_lo_v1_seeds30000-30699.jsonl"
X4_A = "raid_x4/layout_A_raidx4_seeds500000-501999.jsonl"
X4_C = "raid_x4/layout_C_raidx4_seeds500000-501999.jsonl"


def p(*names: str) -> str:
    """Comma-joined dataset paths for scripts that take several files."""
    return ",".join(str(DATA / n) for n in names)


# (report file, script, arguments). Arguments that look like dataset paths are resolved under analysis_data/.
REPORTS: list[tuple[str, str, list[str]]] = [
    ("01_job_sequence_current_layout.md", "analyze_jobs.py", [p(CUR1)]),
    ("02_job_sequence_current_layout_extra.md", "extra_jobs.py", [p(CUR1)]),
    ("03_job_value_current_layout.md", "job_value.py", [p(CUR1)]),
    ("04_bot_variant_jobs_hi.md", "analyze_jobs.py", [p(HI)]),
    ("05_bot_variant_jobs_lo.md", "analyze_jobs.py", [p(LO)]),
    ("06_job_bonus_value.md", "reward_analysis.py", [p(REWARD)]),
    ("07_state_after_jobs_current_layout.md", "aftermath.py", [p(CUR2)]),
    ("08_state_after_jobs_layout_A.md", "aftermath.py", [p(A2)]),
    ("09_state_after_jobs_layout_C.md", "aftermath.py", [p(C2)]),
    ("10_layouts_compared_without_raids.md", "compare_tiers.py", [f"attuale={p(CUR2)}", f"A={p(A2)}", f"C={p(C2)}"]),
    ("11_bankability.md", "bankability.py", [f"attuale={p(CUR1, CUR2)}", f"A={p(A2, A3)}", f"C={p(C2, C3)}"]),
    ("12_completion_per_round.md", "hazard.py", [f"attuale={p(CUR1, CUR2)}", f"A={p(A2, A3)}", f"C={p(C2, C3)}"]),
    ("13_rounds_reveal_to_completion.md", "delay.py", [f"attuale={p(CUR1, CUR2)}", f"A={p(A2, A3)}", f"C={p(C2, C3)}"]),
    ("14_raid_costs_current_layout.md", "raid_desc.py", [str(DATA / CUR1), str(DATA / CUR2)]),
    ("15_raid_job_interaction_current_layout.md", "raid_job_interaction.py", [str(DATA / CUR1), str(DATA / CUR2)]),
    ("16_raid_job_interaction_layout_A.md", "raid_job_interaction.py", [str(DATA / A2), str(DATA / A3)]),
    ("17_raid_job_interaction_layout_C.md", "raid_job_interaction.py", [str(DATA / C2), str(DATA / C3)]),
    ("18_designer_matrix_vs_simulation_current_layout.md", "theory_check.py", [str(DATA / CUR1), str(DATA / CUR2)]),
    ("19_designer_matrix_vs_simulation_layout_A.md", "theory_check.py", [str(DATA / A2), str(DATA / A3)]),
    ("20_designer_matrix_vs_simulation_layout_C.md", "theory_check.py", [str(DATA / C2), str(DATA / C3)]),
    ("21_raid_tables_layout_A.md", "raid_tables.py", [p(A2, A3), "any,1,2,3"]),
    ("22_raid_tables_layout_C.md", "raid_tables.py", [p(C2, C3), "any,1,2,3"]),
    ("23_active_job_x_current_raid_A_C.md", "activejob_raid.py", [p(A3, C3)]),
    ("24_raid_preparation_A_C.md", "prepare.py", [p(A3, C3)]),
    ("25_variance_shares_layout_A.md", "variance_shares.py", [p(A2, A3), "A"]),
    ("26_variance_shares_layout_C.md", "variance_shares.py", [p(C2, C3), "C"]),
    ("27_layout_A_vs_C_paired.md", "paired_AC.py", [p(A3), p(C3)]),
    ("28_raid_outcome_share.md", "outcome_share.py", [f"attuale={p(CUR1, CUR2)}", f"A={p(A2, A3)}", f"C={p(C2, C3)}"]),
    # the same questions with bots that weigh the Raid criterion four times as much
    ("30_raid_x4_raid_preparation_A_C.md", "prepare.py", [p(X4_A, X4_C)]),
    ("31_raid_x4_designer_matrix_A.md", "theory_check.py", [str(DATA / X4_A)]),
    ("32_raid_x4_designer_matrix_C.md", "theory_check.py", [str(DATA / X4_C)]),
    ("33_raid_x4_active_job_x_current_raid_A_C.md", "activejob_raid.py", [p(X4_A, X4_C)]),
    ("34_raid_x4_raid_job_interaction_A.md", "raid_job_interaction.py", [str(DATA / X4_A), "-"]),
    ("35_raid_x4_raid_tables_A.md", "raid_tables.py", [p(X4_A), "any,1,2,3"]),
    ("36_raid_x4_raid_tables_C.md", "raid_tables.py", [p(X4_C), "any,1,2,3"]),
    ("37_raid_x4_variance_shares_A.md", "variance_shares.py", [p(X4_A), "A, Retata x4"]),
    ("38_raid_x4_variance_shares_C.md", "variance_shares.py", [p(X4_C), "C, Retata x4"]),
    ("39_raid_x4_layout_A_vs_C_paired.md", "paired_AC.py", [p(X4_A), p(X4_C)]),
    ("40_raid_x4_outcome_share.md", "outcome_share.py", [f"A_x1={p(A3)}", f"A_x4={p(X4_A)}", f"C_x1={p(C3)}", f"C_x4={p(X4_C)}"]),
    ("41_raid_x4_vs_x1_paired.md", "paired_policies.py", [p(A3), p(X4_A), "A"]),
    ("42_raid_x4_vs_x1_paired_C.md", "paired_policies.py", [p(C3), p(X4_C), "C"]),
    ("43_raid_x4_raid_job_interaction_C.md", "raid_job_interaction.py", [str(DATA / X4_C), "-"]),
]


def datasets_exist(args: list[str]) -> bool:
    for arg in args:
        for piece in arg.split("=", 1)[-1].split(","):
            if piece.endswith(".jsonl") and not Path(piece).exists():
                return False
    return True


def main() -> None:
    wanted = sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    for name, script, args in REPORTS:
        if wanted and not any(name.startswith(w) for w in wanted):
            continue
        if not (TOOLS / script).exists() or not datasets_exist(args):
            print(f"skip   {name} (missing script or dataset)")
            continue
        t0 = time.time()
        cmd = [sys.executable, str(TOOLS / script), *args]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=REPO)
        if result.returncode != 0:
            print(f"FAILED {name}: {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else result.returncode}")
            continue
        (OUT / name).write_text(result.stdout, encoding="utf-8")
        print(f"ok     {name} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
