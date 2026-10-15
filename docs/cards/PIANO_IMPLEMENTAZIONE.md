# Piano di implementazione delle carte nuove (Excel v11)

Stato: **fase 1 fatta** (dati e immagini); le fasi 2–7 aspettano le risposte del game designer.
Una carta con `effect: null` in `data/customer_cards.json` si può comunque pescare e usare per Marketing
(Stonk) o Poker (simboli), ma non offre il suo effetto di potenziamento.

## Fase 1 — Dati, immagini, id (fatta, 2026-10-15)
- `tools/import_cards_xlsx.py`: importa l'Excel; i 27 effetti invariati sono copiati dalle carte vecchie.
- Id: Preti = carte 61–80, Politici = 81–100 (prima il contrario); le altre sono ancora 1–60.
- Immagini: `tools/optimize_card_images.py` crea `frontend/src/assets/cards/web/NN.webp` (800 px, circa 100 KB
  l'una, 10 MB in tutto) dai file originali da 1461×2047 px (80 MB), che restano sul disco e fuori da Git.
- Small: le 20 carte Studenti (21–40) sono tolte dal pacchetto, come prima.

## Fase 2 — Acquistare e Vendere (carte 03, 08, 10, 11, 12, 13, 14, 16, 17, 19, 20, 21, 23)
Ignorare i Cops/Feds, Marketing 1/2, e le azioni dopo l'acquisto/la vendita (piazzare, Den, muovere, Link).

## Fase 3 — Muovere (26, 29, 31, 32, 40; da verificare 24, 27, 28, 30)

## Fase 4 — Rissa (22, 33, 34, 35, 36, 37)

## Fase 5 — Piazzare (42, 44, 45, 46, 49, 50, 51, 52, 54, 55, 57, 58)

## Fase 6 — Manovrare e Corrompere (81–98, 100)

## Fase 7 — NEW ORDERS (99), PAYOFF (82) e pulizia
Rimuovere dal motore gli effetti delle carte vecchie che non esistono più (elenco in
`REVISIONE_CARTE_2026-10.md`), con i loro test.
