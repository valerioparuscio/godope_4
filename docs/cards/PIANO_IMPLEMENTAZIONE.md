# Piano di implementazione delle carte nuove (Excel v11)

Stato: **fasi 1 e 2 fatte**; **fasi 3 e 4 fatte**; le fasi 5–7 aspettano le risposte del game designer.
Una carta con `effect: null` in `data/customer_cards.json` si può comunque pescare e usare per Marketing
(Stonk) o Poker (simboli), ma non offre il suo effetto di potenziamento.

## Fase 1 — Dati, immagini, id (fatta, 2026-10-15)
- `tools/import_cards_xlsx.py`: importa l'Excel; i 27 effetti invariati sono copiati dalle carte vecchie.
- Id: Preti = carte 61–80, Politici = 81–100 (prima il contrario); le altre sono ancora 1–60.
- Immagini: `tools/optimize_card_images.py` crea `frontend/src/assets/cards/web/NN.webp` (800 px, circa 100 KB
  l'una, 10 MB in tutto) dai file originali da 1461×2047 px (80 MB), che restano sul disco e fuori da Git.
- Small: le 20 carte Studenti (21–40) sono tolte dal pacchetto, come prima.

## Fase 2 — Acquistare e Vendere (fatta, 2026-10-15; carte 03, 08, 10, 11, 12, 13, 14, 16, 17, 19, 20, 21, 23)
- 03/10 `ignore_officer_block`: gli acquisti/le vendite ignorano Cops/Feds (opzioni e validazione).
- 08/20/21/23 `marketing_cards` (limite 2 o 1): dopo aver giocato la carta si offre il Marketing, fino al limite.
- 11/19 `after_trade_place`, 14/16 `after_trade_den`, 17 `after_trade_move`: a fine acquisto/vendita parte un
  seguito obbligatorio, ristretto ai Quartieri/pedine dove si è fatto lo scambio (azione Piazza/Muovi a un bersaglio).
  Se non si può fare, viene saltato. Il pannello dice "Carta: …" (campo `context.card_followup`).
- 12 `sale_link_any_contact` (scelta del Cliente del Link) e 13 `sale_link_level` (Link al livello 3, spinge fuori chi c'è).

## Fase 3 — Muovere (fatta, 2026-10-15; carte 26, 29, 31, 32, 40)
- 40 `bonus_card_draw_new_hood`: entrando in un Quartiere dove non hai Criminali peschi 2 carte invece di 1.
- 31 `link_to_criminal`: un tuo Link torna Criminale in uno dei due Quartieri del suo Cliente (pesca, può dare Rissa).
- 26 `badge_hunt` e 32 `den_seat_swap`: seguiti dopo il movimento (`rules/move_followups.py`, passo
  `WAITING_FOR_MOVE_FOLLOWUP`, decisione `move_followup`): sposti un Cop del Quartiere dove entri (1$, un Cop per
  pedina) / scambi posto con un Gambler avversario (anche a Den pieno, allora obbligatorio).
- 29 `move_distance_2`: ogni pedina può muoversi a 1 o 2 Quartieri di distanza (conta solo la destinazione).

## Fase 4 — Rissa (fatta, 2026-10-15; carte 22, 33, 34, 35, 36, 37)
- 22 `provoker_gun_bonus_per_cop`: +2 Pistole per ogni Cop già nel Quartiere. 33/34 `brawl_losers_to_jail`: gli
  sconfitti (1 pedina ciascuno, a partire dal giocatore dopo il vincitore) vanno in Jail al posto del Quartiere
  nascosto; la ricompensa resta; Jail piena = Evasione. 35 `brawl_win_link_level`: il Link del vincitore va al
  livello 3. 36 `brawl_win_corrupt_cop` / 37 `brawl_win_free_place`: ultimi passi facoltativi (corrompi il Cop
  entrato, 7$; piazzi gratis una pedina nel Quartiere, peschi, limite 4), tramite `rules/move_followups.py`.

## Fase 5 — Piazzare (fatta, 2026-10-15; carte 42, 44, 46/58, 49, 50, 51/57, 52/55, 54)
- 42 `place_in_den_evict_enemy` (già esistente). 44 `place_free_where_present`: gratis dove hai presenza (anche Link).
  46/58 `place_in_hidden_hood`: 1 Quartiere non rivelato, 2$, si rivela e peschi. 49 `place_all_reserves`: tutte le
  pedine del Covo a 3$. 50 `place_then_corrupt_cop`, 51/57 `place_then_move`, 54 `place_then_decoy`: passi dopo il
  piazzamento via `move_followups` (kind `badge_hire`, `expansion`, `decoy`). 52/55 `place_then_buy`: niente carte,
  poi 1 pedina piazzata può comprare (restrizione kind `buy`, facoltativa).
- PROVISIONAL: DECOY non ha limite di riserva Cop (il motore non ne ha uno): il Cop entra sempre.

## Fase 6 — Manovrare e Corrompere (fatta, 2026-10-16; carte 81–98, 100)

## Fase 7 — NEW ORDERS (99), PAYOFF (82) e pulizia
Rimuovere dal motore gli effetti delle carte vecchie che non esistono più (elenco in
`REVISIONE_CARTE_2026-10.md`), con i loro test.
