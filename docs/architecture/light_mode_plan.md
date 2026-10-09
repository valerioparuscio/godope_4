# Modalità "light" (semplice) — piano e istruzioni

> Stato: **test di fattibilità del backend completato (2026-10-09)**. Tutto ciò che è
> marcato `PROVISIONAL` è una scelta provvisoria dello sviluppo, non una decisione del
> game designer (CLAUDE.md §2).

## 1. Obiettivo

Offrire all'avvio una modalità "semplice" dello stesso gioco, senza fork e senza
riscrivere il motore:

| | Standard | Light (bozza) |
|---|---|---|
| Merci | 4 | **3** (`PROVISIONAL`: via il Gufo) |
| Clienti | 5 | **4** (via gli Studenti) |
| Quartieri | 10 (2 per Cliente) | **8** (2 per Cliente, 4 scoperti + 4 nascosti) |
| Punti vendita | 10 | **8** (2 per Cliente) |
| Pedine per giocatore | 10 | **9** |
| Manager | Piazza | **Piazza e Sposta** (carte e Ganci) |
| Jobs | 9 | 9, semplificati (vedi §4) |

## 2. Decisione: una modalità nello stesso progetto

Non conviene un fork (ogni correzione andrebbe fatta due volte) né ripartire da zero
(il motore ha oltre 500 test). Si usa un **pacchetto di dati** per modalità, scelto alla
creazione della partita. Il motore è già quasi tutto guidato dai dati (`data/*.json`):
mappa, adiacenze, Clienti, azioni dei Ganci, Merci e prezzi, carte, Jobs, Skill, Retate e
configurazione. I Clienti con un ruolo speciale nel codice sono solo i **Preti** (Poker,
scelta del primo giocatore) e i **Politici** (Evasione, poliziotti): restano nel light.

## 3. Cosa esiste già

- `tools/make_simple_pack_draft.py` — genera `data_packs/simple/` a partire da `data/`
  (ogni scelta non confermata è marcata `PROVISIONAL` nello script).
- `data_packs/simple/` — il pacchetto di dati provvisorio.
- `tools/validate_data.py` — ora aspetta 20 carte per Cliente, non 100 fisse.
- `rules/economy.py` — il prezzo "più caro / meno caro" scorre le Merci dei dati, non
  l'enumerazione fissa (unica correzione al motore servita dal test).

Comandi:

```bash
python tools/make_simple_pack_draft.py                     # rigenera il pacchetto
python tools/validate_data.py data_packs/simple            # valida i dati
python tools/run_full_test_game.py --data-dir data_packs/simple --seeds 1-60 \
    --bot-policy random_legal                              # simulazioni + invarianti
python tools/run_full_test_game.py --data-dir data_packs/simple --seeds 100-160 \
    --bot-policy heuristic
```

## 4. Risultati del test di fattibilità

- 60 partite su 60 con bot casuali, 61 su 61 con bot euristici: nessun errore e nessuna
  violazione di invariante. I test del gioco standard (521) passano, standard invariato.
- Confronto su 40 partite con bot euristici:

| | Standard | Light (bozza) |
|---|---|---|
| Comandi per partita | 300 | 312 |
| Punti medi a giocatore | 6,89 | 7,44 |
| Jobs completati a partita | 7,1 | **9,3** |

I Jobs semplificati del pacchetto bozza sono più facili: da bilanciare.

Jobs nel pacchetto bozza: via gli Studenti (il Job 1 passa ai Manager, `PROVISIONAL`);
"Criminali in 6 Quartieri" → 5; "tutti i 10 Criminali" → 9; "4 Merci, una per tipo" → 3.

## 4b. Cosa NON è stato fatto

- **Frontend:** nessuna modifica. Tabellone, coordinate e icone sono quelli a 5 Clienti.
- **Scelta della modalità all'avvio** e salvataggio della modalità nella partita.
- Le 20 carte degli Studenti sono state tolte, non redistribuite sugli altri Clienti.
- Poker: ancora 5 colori di simboli (vedi §6).
- Tutorial: costruito sul tabellone standard.

## 5. Passi per completare

1. **Dati e contenuti** (con il game designer): confermare le Merci, la mappa a 8
   Quartieri, i PdV, la distribuzione delle carte e delle Skill degli Studenti, i Jobs
   e il bilanciamento dei Jobs. Poi trasformare la bozza in dati curati
   (`data_packs/light/`), non più generati dallo script.
2. **Backend — modalità nella partita:**
   - `ruleset_id` dentro `GameState`, salvataggi, replay e leaderboard (separare le
     classifiche per modalità);
   - un `GameService` per modalità (il bus dei comandi si costruisce dai dati), scelto
     dalla modalità della partita; `POST /api/v1/games` accetta `ruleset`;
   - generalizzare l'enumerazione `DopeType` (4 valori fissi) se il light usa una Merce
     che non esiste nello standard.
3. **Frontend:** layout per modalità. Le coordinate di Quartieri, PdV, piste dei Ganci,
   scale dei prezzi e griglia dei Jobs sono costanti in `frontend/src/board-layout.ts`:
   vanno spostate in un layout per modalità, con il tabellone nuovo (immagine) e le
   icone dei Clienti. Anche `rules/content/` e `assets/index.ts` nominano gli Studenti.
4. **Schermata iniziale:** scelta Standard / Semplice.
5. **Tutorial:** disattivarlo nel light e rifarlo dopo.
6. **Test:** eseguire i test chiave su entrambe le modalità e ripetere le simulazioni
   (comandi sopra) a ogni modifica ai dati.

## 6. Decisioni aperte per il game designer

- Quale Merce si toglie, e quali PdV accettano quali Merci.
- Mappa a 8 Quartieri (adiacenze, quali sono scoperti all'inizio, Merce di partenza).
- Distribuzione delle 20 carte e delle 3 Skill degli Studenti sugli altri Clienti.
- **Poker:** le combinazioni usano 5 colori di simboli, abbinati ai 5 Clienti; con 4
  Clienti restano 5 colori sulle carte o si passa a 4 (e come cambiano le combinazioni)?
- Jobs: quali requisiti semplificare e di quanto (il bozza è troppo facile).
- Punteggio: le maggioranze valgono 1 punto per Cliente, quindi il massimo scende da 5 a 4.
- Leaderboard: classifica unica o una per modalità.

## 7. Rischi

- Il motore regge il light, ma le euristiche dei bot sono tarate sullo standard: rifare
  le simulazioni dopo ogni cambio di dati.
- Il frontend è la parte più grossa (grafica e coordinate): il collo di bottiglia non è
  il motore.
