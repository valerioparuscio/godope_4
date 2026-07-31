"""Load every file in data/ and cross-check referential integrity.

Usage:
    python tools/validate_data.py [data_dir]

Defaults to ./data relative to the current working directory. Exits
with status 1 and prints every problem found if validation fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from dope_engine.application.data_loader import GameData, load_game_data  # noqa: E402


def validate(data: GameData) -> list[str]:
    problems: list[str] = []

    hood_ids = {h.hood_id for h in data.board.hoods}
    for hood in data.board.hoods:
        for adj in hood.adjacent_hood_ids:
            if adj not in hood_ids:
                problems.append(f"board.json: hood '{hood.hood_id}' references unknown adjacent hood '{adj}'")
            if hood.hood_id not in _adjacent_of(data.board.hoods, adj):
                problems.append(f"board.json: adjacency '{hood.hood_id}' -> '{adj}' is not symmetric")

    contact_ids = {c.contact_id for c in data.contacts.contacts}
    for hood in data.board.hoods:
        if hood.contact_id not in contact_ids:
            problems.append(f"board.json: hood '{hood.hood_id}' references unknown contact '{hood.contact_id}'")

    spot_ids = {s.spot_id for s in data.contacts.spots}
    for spot in data.contacts.spots:
        if spot.contact_id not in contact_ids:
            problems.append(f"contacts.json: spot '{spot.spot_id}' references unknown contact '{spot.contact_id}'")
        for adj in spot.adjacent_spot_ids:
            if adj not in spot_ids:
                problems.append(f"contacts.json: spot '{spot.spot_id}' references unknown adjacent spot '{adj}'")

    revealed_hoods_by_contact = [h for h in data.board.hoods if h.revealed]
    if len(revealed_hoods_by_contact) != len(contact_ids):
        problems.append(
            f"board.json: expected exactly one revealed Hood per Contact "
            f"({len(contact_ids)} contacts), found {len(revealed_hoods_by_contact)}"
        )

    for job in data.jobs:
        for cid in job.contact_ids:
            if cid not in contact_ids:
                problems.append(f"jobs.json: job '{job.job_id}' references unknown contact '{cid}'")

    for skill in data.skills:
        if skill.contact_id not in contact_ids:
            problems.append(f"skills.json: skill '{skill.skill_id}' references unknown contact '{skill.contact_id}'")

    for card in data.customer_cards:
        if card.contact_id not in contact_ids:
            problems.append(f"customer_cards.json: card '{card.card_id}' references unknown contact '{card.contact_id}'")
        if card.action_type is None and not card.provisional:
            problems.append(
                f"customer_cards.json: card '{card.card_id}' has no action_type but is not marked provisional"
            )

    for contact in data.contacts.contacts:
        cards_for_contact = [c for c in data.customer_cards if c.contact_id == contact.contact_id]
        if len(cards_for_contact) != 20:
            problems.append(
                f"customer_cards.json: contact '{contact.contact_id}' has {len(cards_for_contact)} cards, expected 20"
            )

    if len(data.customer_cards) != 100:
        problems.append(f"customer_cards.json: expected 100 cards total, found {len(data.customer_cards)}")

    return problems


def _adjacent_of(hoods: tuple, hood_id: str) -> set[str]:
    for hood in hoods:
        if hood.hood_id == hood_id:
            return set(hood.adjacent_hood_ids)
    return set()


def main() -> int:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    data = load_game_data(data_dir)
    problems = validate(data)

    if problems:
        print(f"{len(problems)} problem(s) found in {data_dir}:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"data/ OK: {len(data.board.hoods)} hoods, {len(data.contacts.contacts)} contacts, "
          f"{len(data.contacts.spots)} spots, {len(data.jobs)} jobs, {len(data.skills)} skills, "
          f"{len(data.raids)} raids, {len(data.customer_cards)} customer cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
