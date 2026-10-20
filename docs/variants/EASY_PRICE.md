# Variante "Easy Price"

Terza modalità di gioco, selezionabile nella schermata iniziale accanto a **Big** (gioco completo, invariato) e
**Small**. Parte dalla Big attuale (stessa mappa, stessi Clienti, Merci, carte, Job, Skill e Retate) e usa il tabellone
`BOARD_v16_GODOPE_4_4 PREZZI.webp`. Richiesta del game designer, 2026-10-20.

## 1. Economia e setup

- Setup, dotazioni iniziali, costi e guadagni restano quelli della Big, **tranne i prezzi di partenza** (vedi 3).
- Acquisti, vendite, piazzamento, acquisto e manipolazione dei Cops mantengono le rispettive regole economiche.
- Unica eccezione: il Poker (vedi 2).

## 2. Poker

- Il Poker **non fa più guadagnare soldi**: né l'incasso di chi lancia la partita (3$, 6$ con la Skill Preti-2), né il
  premio in denaro del vincitore.
- Restano tutte le altre ricompense e regole: Chip, Link, arresto degli sconfitti, jackpot, ecc.

## 3. Tracciati dei prezzi

Ogni Merce ha esattamente quattro livelli, in ordine crescente:

| Merce | Livelli |
|---|---|
| Rana | 0, 1, 2, 3 |
| Camaleonte | 2, 3, 4, 6 |
| Polpo | 4, 5, 7, 9 |
| Gufo | 6, 8, 10, 13 |

Il prezzo 0 della Rana è un prezzo valido (acquisto a costo zero), non un valore mancante.

**Prezzi di partenza** (decisione del game designer, 2026-10-20): tutte e quattro le Merci partono dal **livello più
basso** del proprio tracciato, cioè Rana 0, Camaleonte 2, Polpo 4, Gufo 6 (`initial_price_index: 0` in
`data_packs/easy_price/dope_types.json`). Rispetto alla Big (1, 3, 4, 6) cambiano quindi Rana e Camaleonte.

## 4. Variazioni dei prezzi

- **Eliminati** gli aggiornamenti automatici associati alle singole operazioni: acquisto, vendita e requisizione non
  cambiano più i prezzi.
- Il prezzo cambia invece quando:
  - un **Punto di Vendita si riempie** (3 Merci): il prezzo della Merce corrispondente va **al livello minimo**;
  - un **Quartiere si svuota**: il prezzo della Merce corrispondente va **al livello massimo**;
  - il **Marketing** lo modifica (vedi 5).
- Riempimento e svuotamento valgono qualunque sia la causa: azioni ordinarie, requisizioni, carte, altri effetti.
- Conta il **passaggio** alla condizione di pieno/vuoto, non lo stato: un Punto di Vendita già pieno o un Quartiere già
  vuoto non riapplicano l'effetto, e il Marketing può spostare il prezzo subito dopo.
- Una compravendita o requisizione che provoca uno di questi eventi aggiorna comunque il prezzo all'estremo, ma non
  produce variazioni ordinarie.
- Nei pacchetti di acquisto/vendita l'aggiornamento all'estremo avviene **a fine pacchetto** (tutte le unità dello
  stesso pacchetto costano il prezzo che c'era all'inizio, come nella Big). Se la vendita offre l'evoluzione in Link,
  l'aggiornamento attende la scelta, come ogni variazione di prezzo di quel pacchetto. Le requisizioni (che non sono
  pacchetti) lo applicano subito.
- Dopo lo svuotamento il Quartiere si ricarica e riceve un Cop come nella Big; il prezzo resta al massimo.

## 5. Marketing

- Ogni Stonk sposta di **esattamente un livello** il prezzo di **una Merce**.
- Ogni Merce può essere modificata **al massimo una volta** nella stessa risoluzione del Marketing.
- Esempi: 1 Stonk → una Merce di un livello; 3 Stonk → tre Merci diverse di un livello ciascuna; 4 Stonk → tutte e
  quattro le Merci.
- Non si possono concentrare più Stonk sulla stessa Merce, scartare Stonk o uscire dal tracciato: a un estremo l'unico
  movimento consentito è verso l'interno. Il numero di Stonk da usare è esattamente `min(Stonk della carta, 4)`.
- Rinunciare del tutto al Marketing (non giocare la carta) resta possibile.

## 6. Implementazione

- Pacchetto dati sovrapposto: `data_packs/easy_price/` contiene solo `dope_types.json` (tracciati) e
  `game_config.overrides.json` (chiavi sotto); il resto si legge da `data/` (così carte, Job, ecc. restano quelli della Big).
- Chiavi di configurazione (assenti = comportamento Big): `price_change_mode: "extremes"`, `marketing_mode:
  "distinct_exact"`, `poker_pays_money: false`, `poker_launch_cashout: 0`, `poker_win_cash_per_chip: 0`,
  `ruleset_id: "easy_price"`. Vengono copiate nello stato della partita: i salvataggi conservano la variante e quelli
  precedenti restano compatibili (nuovo campo `PlayerState.pending_price_extremes` con valore di default).
- Backend: `rules/prices.py` (`set_price_extreme`), `rules/economy.py` (`extremes_mode`, `set_price_extreme`,
  `apply_ordinary_price_step`, validazione del Marketing), `rules/officers.py` (requisizione), `rules/skills.py`
  (Poker), `application/legal_actions.py` (opzioni del Marketing), `bots/option_picking.py::pick_marketing_options`.
- Frontend: modalità `easy_price` nella schermata iniziale, tabellone dedicato, posizioni dei segnalini prezzo
  (`board-layout.ts`), controlli del Marketing, pagina "Varianti → Variante Easy Price" nel regolamento.
- Test: `backend/tests/unit/test_easy_price.py`; simulazioni con `tools/run_full_test_game.py --data-dir
  data_packs/easy_price`.

## 7. Effetti esistenti segnalati (nessuna sostituzione inventata)

- **Crollo del mercato:** nella Big, quando tutte e quattro le Merci arrivano al prezzo massimo il mercato crolla e
  tutti i prezzi tornano al livello più basso. La regola è rimasta invariata: con gli svuotamenti che portano le Merci al
  massimo può ora scattare più facilmente. Da confermare.
- **Skill Preti-2** (Poker: 6$ al lancio): in questa variante vale 0, perché il Poker non dà più soldi.
- **Skill Manager-3** (rigioca il Marketing a fine azione): la ripetizione usa gli stessi spostamenti ma, se la Merce è
  già a un estremo, non si muove oltre il tracciato (nessun errore).
- **Skill Artisti-2** (acquisti a -1$, vendite a +1$ per unità): modifica il denaro pagato/incassato, non il tracciato;
  compatibile (il prezzo non scende sotto 0).
- **Carte con "al prezzo della Merce più cara/meno cara"** e le carte "Fai 2 Marketing": compatibili (ogni carta di
  Marketing è una risoluzione a sé, con le sue Merci diverse).
- **Retate / Job basati sul valore delle Merci:** leggono i nuovi valori dei tracciati.
