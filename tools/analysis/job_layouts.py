"""Alternative assignments of the nine Jobs to the three tiers, for experiments.

These are not game data: `data/jobs.json` stays as it is. A layout is a set of tier changes; `build_pack` writes a
temporary data pack (an overlay on the real one) with the modified `jobs.json`, ready for `load_game_data`.

  current  data/jobs.json as it is
  A        "10 Criminali fuori" (job_08) to tier 2, "2 Rats" (job_04) to tier 3
  C        tiers re-sorted by difficulty: job_08 to tier 1, "Vinci 1 Rissa" (job_01) to tier 2, job_04 to tier 3
"""

from __future__ import annotations

import json
from pathlib import Path

LAYOUTS: dict[str, dict[str, int]] = {
    "current": {},
    "A": {"job_08": 2, "job_04": 3},
    "C": {"job_08": 1, "job_01": 2, "job_04": 3},
}

# the two overlay files of the "Easy Price" pack; every other file comes from data/
_OVERLAY_FILES = ("dope_types.json", "game_config.overrides.json")


def tiers_of(layout: str, jobs: list[dict]) -> dict[int, list[str]]:
    moves = LAYOUTS[layout]
    by_tier: dict[int, list[str]] = {}
    for job in jobs:
        by_tier.setdefault(moves.get(job["job_id"], job["tier"]), []).append(job["job_id"])
    return by_tier


def _write_if_changed(path: Path, data: bytes) -> None:
    """Only touch a file whose content really changes, so that a second run of the same layout started while the
    first is still going does not rewrite files the first run's workers may be reading."""
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def build_pack(
    repo: Path, ruleset: str, layout: str, work_dir: Path, write: bool = True
) -> tuple[Path, Path | None]:
    """Returns (pack_dir, base_dir) for `load_game_data(pack_dir, base_dir=base_dir)`.

    `write=False` only computes the paths: the workers of a parallel run use it, the main process writes the pack once
    before starting them."""
    if layout not in LAYOUTS:
        raise SystemExit(f"unknown layout '{layout}' (choose from {', '.join(LAYOUTS)})")
    if ruleset == "standard":
        pack, base = repo / "data", None
    elif ruleset == "easy_price":
        pack, base = repo / "data_packs" / "easy_price", repo / "data"
    else:
        if layout != "current":
            raise SystemExit("job layouts are only supported for the standard and easy_price rulesets")
        return repo / "data_packs" / ruleset, None
    if layout == "current":
        return pack, base

    out = work_dir / f"{ruleset}_{layout}"
    base_dir = base if ruleset == "easy_price" else None
    if not write:
        return out, base_dir
    out.mkdir(parents=True, exist_ok=True)
    if ruleset == "easy_price":
        for name in _OVERLAY_FILES:
            _write_if_changed(out / name, (pack / name).read_bytes())
    else:  # standard: a full pack, copied whole
        for path in pack.glob("*.json"):
            _write_if_changed(out / path.name, path.read_bytes())
    jobs = json.loads((repo / "data" / "jobs.json").read_text(encoding="utf8"))
    moves = LAYOUTS[layout]
    for job in jobs:
        job["tier"] = moves.get(job["job_id"], job["tier"])
    _write_if_changed(out / "jobs.json", json.dumps(jobs, indent=2, ensure_ascii=False).encode("utf8"))
    return out, base_dir
