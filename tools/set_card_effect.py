"""Sets the mechanical `effect` of one or more cards in `data/customer_cards.json`.

Usage:
    python tools/set_card_effect.py "3,10" '{"type": "ignore_officer_block"}'

The first argument is a comma-separated list of card numbers (3 -> card_003). The card's
"effetto non ancora implementato" note is cleared. Rewrites the file in the importer's format.
"""

import json
import sys
from pathlib import Path

PATH = Path("data/customer_cards.json")


def main() -> int:
    numbers = [int(n) for n in sys.argv[1].split(",")]
    effect = json.loads(sys.argv[2])
    data = json.loads(PATH.read_text(encoding="utf8"))
    wanted = {f"card_{n:03d}" for n in numbers}
    hit = 0
    for card in data["cards"]:
        if card["card_id"] in wanted:
            card["effect"] = effect
            card["notes"] = None
            hit += 1
    if hit != len(wanted):
        print(f"only {hit} of {len(wanted)} cards found", file=sys.stderr)
        return 1
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"effect set on {hit} card(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
