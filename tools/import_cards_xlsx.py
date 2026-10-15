"""One-shot import of the designer's card sheet into `data/customer_cards.json`.

Usage:
    python tools/import_cards_xlsx.py [xlsx_path] [json_path]

Defaults: `docs/cards/carte_azioni_v11_ITA-EN.xlsx` -> `data/customer_cards.json`.

The sheet gives title, deck, action, text, Poker symbols, Banco, Stonks and Guns. The
mechanical `effect` of each card is NOT in the sheet: for a card whose effect is the same as
a card of the previous set, it is copied from the old `customer_cards.json` (see
`EFFECT_FROM_OLD_CARD`); every other card gets `effect: null` until its effect is implemented
(such a card is simply never boost-eligible — rules/customer_cards.py). Later work edits the
`effect` fields in the JSON directly; this importer is for the first import of a new sheet.
"""

import json
import sys
from pathlib import Path

import openpyxl

ACTION_MAP = {
    "acquistare": "buy_dope",
    "vendere": "sell_dope",
    "muovere": "move_criminal",
    "piazzare": "place_criminal",
    "manovrare": "maneuver_officer",
    "corrompere": "corrupt_officer",
}
COLOR_MAP = {
    "rosa": "rosa",
    "verde": "verde",
    "blu": "azzurro",
    "azzurro": "azzurro",
    "grigio": "grigio",
    "arancione": "arancione",
}
BANCO_LETTER = {"R": "rosa", "V": "verde", "B": "azzurro", "G": "grigio", "A": "arancione"}

# new card number -> old card number whose `effect` it reuses (game designer, 2026-10-15:
# same effect as before, only the card's position/title changed).
EFFECT_FROM_OLD_CARD = {
    1: 1, 2: 2, 4: 17, 5: 5, 6: 6, 7: 7, 9: 9, 15: 15, 18: 18,
    24: 24, 25: 25, 27: 33, 28: 32, 30: 37, 38: 28, 39: 21,
    41: 41, 43: 43, 45: 43, 47: 47, 48: 48, 53: 53, 56: 53, 59: 41, 60: 46,
    83: 66, 95: 76,
}


def main() -> int:
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/cards/carte_azioni_v11_ITA-EN.xlsx")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/customer_cards.json")
    old = {
        int(card["card_id"].split("_")[1]): card
        for card in json.loads(out.read_text(encoding="utf8"))["cards"]
    }
    sheet = openpyxl.load_workbook(xlsx, data_only=True).active
    cards = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        number = int(row[0])
        deck, title, action, text, text_en = row[1], row[2], row[3], row[5], row[6]
        poker = [COLOR_MAP[c.strip().lower()] for c in (row[7], row[8]) if c and c.strip() != "-"]
        banco = [BANCO_LETTER[ch] for ch in (row[9] or "")]
        source = EFFECT_FROM_OLD_CARD.get(number)
        effect = old[source]["effect"] if source is not None else None
        is_gamble = bool(banco)
        cards.append({
            "card_id": f"card_{number:03d}",
            "title": title,
            "contact_id": deck.strip().lower(),
            "action_type": ACTION_MAP[action.strip().lower()],
            "poker_symbols": poker,
            "stonk_count": int(row[10]),
            "gun_count": int(row[11]),
            "boost_text": text,
            "boost_text_en": text_en,
            "banco_symbols": banco,
            "provisional": False,
            "notes": None if (effect or is_gamble) else "effetto non ancora implementato",
            "effect": effect,
        })
    payload = {
        "dataset_status": "REVISED_V11",
        "dataset_note": (
            "Carte aggiornate dal game designer il 2026-10-15 (carte_azioni_v11_ITA-EN.xlsx). "
            "Le carte con effect null non sono ancora implementate (vedi "
            "docs/cards/REVISIONE_CARTE_2026-10.md)."
        ),
        "cards": cards,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    implemented = sum(1 for c in cards if c["effect"])
    print(f"{len(cards)} cards written, {implemented} with an effect carried over")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
