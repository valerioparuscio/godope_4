"""Builds `data_packs/simple/`: a DRAFT data pack for a simplified "semplice" mode,
derived from the standard `data/` files (feasibility spike, 2026-10-09).

Every choice below that the game designer has not confirmed is marked PROVISIONAL
(CLAUDE.md §2): which Dope is dropped, the 8-Hood map, the Spots' accepted Dope,
the spread of the dropped Clients' content. The point of this pack is to check that
the engine runs a 4-Client / 3-Dope / 8-Hood / 9-pawn game, not to settle the design.

Usage:  python tools/make_simple_pack_draft.py
        python tools/run_full_test_game.py --data-dir data_packs/simple --seeds 1-50
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data"
OUT = ROOT / "data_packs" / "simple"

DROPPED_CONTACT = "studenti"
DROPPED_DOPE = "gufo"  # PROVISIONAL: which of the 4 Dope goes
CONTACTS = ["artisti", "manager", "preti", "politici"]
DOPES = ["camaleonte", "rana", "polpo"]


def load(name: str):
    return json.loads((SRC / name).read_text(encoding="utf8"))


def dump(name: str, data) -> None:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    # Anything not rewritten below is the standard file, unchanged.
    for path in SRC.glob("*.json"):
        shutil.copy(path, OUT / path.name)

    # --- Dope: 3 types ------------------------------------------------------
    dope = load("dope_types.json")
    dope.pop(DROPPED_DOPE)
    dump("dope_types.json", dope)

    # --- Contacts: 4 Clients; Managers also take the Move action -------------
    contacts = load("contacts.json")
    kept = [c for c in contacts["contacts"] if c["contact_id"] != DROPPED_CONTACT]
    for contact in kept:
        if contact["contact_id"] == "manager":
            # PROVISIONAL: Manager Links/cards now cover Place and Move.
            contact["boosted_actions"] = ["place_criminal", "move_criminal"]
            contact["link_extra_action_restricted_to"] = ["place_criminal", "move_criminal"]
    # 8 Spots, 2 per Client, each accepting two of the 3 Dope (PROVISIONAL), in a
    # chain for Fed movement.
    accepted = {
        "artisti": ["camaleonte", "polpo"],
        "manager": ["camaleonte", "rana"],
        "preti": ["rana", "polpo"],
        "politici": ["rana", "camaleonte"],
    }
    spots = []
    ids = [f"spot_{c}_{i}" for c in CONTACTS for i in (1, 2)]
    for index, spot_id in enumerate(ids):
        contact_id, number = spot_id.split("_")[1], int(spot_id.split("_")[2])
        neighbours = [ids[j] for j in (index - 1, index + 1) if 0 <= j < len(ids)]
        spots.append(
            {
                "spot_id": spot_id,
                "contact_id": contact_id,
                "accepted_dope_type": accepted[contact_id][number - 1],
                "adjacent_spot_ids": neighbours,
            }
        )
    contacts["contacts"] = kept
    contacts["spots"] = spots
    dump("contacts.json", contacts)

    # --- Board: 8 Hoods, 2 per Client, 4 revealed / 4 covered (PROVISIONAL) --
    board = load("board.json")
    layout = [
        # id, contact, revealed, starting dope, adjacent
        ("hood_q1", "artisti", True, "rana", ["hood_q2", "hood_q3"]),
        ("hood_q2", "artisti", False, None, ["hood_q1", "hood_q3", "hood_q4"]),
        ("hood_q3", "manager", True, "camaleonte", ["hood_q1", "hood_q2", "hood_q4", "hood_q5"]),
        ("hood_q4", "manager", False, None, ["hood_q2", "hood_q3", "hood_q5", "hood_q6"]),
        ("hood_q5", "preti", True, "polpo", ["hood_q3", "hood_q4", "hood_q6", "hood_q7"]),
        ("hood_q6", "preti", False, None, ["hood_q4", "hood_q5", "hood_q7", "hood_q8"]),
        ("hood_q7", "politici", True, "rana", ["hood_q5", "hood_q6", "hood_q8"]),
        ("hood_q8", "politici", False, None, ["hood_q6", "hood_q7"]),
    ]
    board["hoods"] = [
        {
            "hood_id": hood_id,
            "label": hood_id.replace("hood_", "").upper(),
            "contact_id": contact_id,
            "revealed": revealed,
            "starting_dope_type": starting,
            "adjacent_hood_ids": adjacent,
        }
        for hood_id, contact_id, revealed, starting, adjacent in layout
    ]
    tiles = board["covered_hood_tiles"]["tile_values"]
    board["covered_hood_tiles"] = {
        "tile_values": [t for t in tiles if t["tile_id"] in ("tile_1", "tile_2", "tile_2c", "tile_3")],
        "dope_pool": ["camaleonte", "rana", "polpo", "camaleonte"],
    }
    dump("board.json", board)

    # --- Config ---------------------------------------------------------------
    config = load("game_config.json")
    config["pawns_per_player"] = 9
    config["starting_dope_by_seat"] = [
        ["rana", "polpo"],
        ["camaleonte", "polpo"],
        ["rana", "camaleonte"],
        ["camaleonte", "polpo"],
    ]
    config["rules_version"] = "0.56-simple-draft"
    dump("game_config.json", config)

    # --- Cards: the Client's 20 cards are dropped for now (PROVISIONAL: they
    # should be spread over the other Clients, a content job) ------------------
    cards = load("customer_cards.json")
    cards["cards"] = [c for c in cards["cards"] if c["contact_id"] != DROPPED_CONTACT]
    dump("customer_cards.json", cards)

    # --- Skills: the dropped Client's go too ----------------------------------
    skills = [s for s in load("skills.json") if s["contact_id"] != DROPPED_CONTACT]
    dump("skills.json", skills)

    # --- Jobs: no dropped Client; 5 Hoods / 9 pawns; 3 Dope types -------------
    jobs = load("jobs.json")
    for job in jobs:
        ids = [c for c in job["contact_ids"] if c != DROPPED_CONTACT]
        # job_01 was Studenti-only: give it to the Managers (PROVISIONAL).
        job["contact_ids"] = ids or ["manager"]
        requirement = job["requirement"]
        if requirement["type"] == "criminals_in_distinct_hoods":
            requirement["count"] = 5
        if requirement["type"] == "criminals_out_of_base":
            requirement["count"] = 9
        if requirement["type"] == "own_dope_in_base":
            requirement["count"] = len(DOPES)
    dump("jobs.json", jobs)

    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
