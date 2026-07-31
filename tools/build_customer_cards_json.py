"""Build data/customer_cards.json from the customer_cards_draft.csv working sheet.

Usage:
    python tools/build_customer_cards_json.py [csv_path] [json_path]

Defaults to data/customer_cards_draft.csv -> data/customer_cards.json.
"""

import csv
import json
import sys
from pathlib import Path

ACTION_MAP = {
    "acquistare": "buy_dope",
    "vendere": "sell_dope",
    "muovere": "move_criminal",
    "piazzare": "place_criminal",
    "corrompere": "corrupt_officer",
}

# The placeholder spreadsheet uses "blu" for the color RULES_CANONICAL.md
# and the rest of the data files call "azzurro" (same color, different
# label chosen in different sessions). Normalize to the canonical name.
COLOR_MAP = {
    "rosa": "rosa",
    "verde": "verde",
    "blu": "azzurro",
    "azzurro": "azzurro",
    "grigio": "grigio",
    "arancione": "arancione",
}


def _color(raw: str) -> str:
    return COLOR_MAP[raw.strip().lower()]


def build(csv_path: Path, json_path: Path) -> int:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    cards = []
    for row in rows:
        action_word = row["action"].strip().lower()
        action_type = ACTION_MAP.get(action_word)
        provisional = action_type is None

        poker_symbols = [_color(p) for p in (row["poker_1"], row["poker_2"]) if p]
        banco_symbols = [
            _color(b) for b in (row["banco_1"], row["banco_2"], row["banco_3"]) if b
        ]

        cards.append({
            "card_id": f"card_{int(row['id']):03d}",
            "title": row["title"],
            "contact_id": row["contact"],
            "action_type": action_type,
            "poker_symbols": poker_symbols,
            "stonk_count": int(row["stonk_count"]),
            "gun_count": int(row["gun_count"]),
            "boost_text": row["effect_text"] or None,
            "banco_symbols": banco_symbols,
            "provisional": provisional,
            "notes": row["notes"] or None,
        })

    payload = {
        "dataset_status": "PLACEHOLDER",
        "dataset_note": (
            "Versione non aggiornata fornita dal game designer il 2026-07-31 "
            "(vedi docs/rules/RULE_CHANGELOG.md). Non trattare come regola "
            "definitiva: alcune carte Politici referenziano un'azione "
            "'reputazione' non piu' esistente (provisional=true)."
        ),
        "cards": cards,
    }

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(cards)


if __name__ == "__main__":
    csv_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/customer_cards_draft.csv")
    json_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/customer_cards.json")

    n = build(csv_arg, json_arg)
    print(f"Wrote {json_arg} ({n} cards)")
