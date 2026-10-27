# Variante "Easy Price"

Terza modalità di gioco; dal 2026-10-25 è **l'unica offerta** nella schermata iniziale (Big e Small restano nel motore ma non
si scelgono più). Parte dalla Big (stessi Clienti, Merci, carte, Job, Skill e Retate) e usa il tabellone `BOARD_v17_C.webp`
(dal 2026-10-27; la `BOARD_v17.webp` ha le stesse posizioni e un altro sfondo; prima `BOARD_v16_GODOPE_4_4 PREZZI.webp`): rispetto al precedente cambiano di posto i Quartieri, il Den (ora
al centro) e la Jail (in basso a destra), le cui posizioni sono in `frontend/src/board-layout-easy-price.ts`. Richiesta del
game designer, 2026-10-20.

## 1. Economia e setup

- Setup, dotazioni iniziali, costi e guadagni restano quelli della Big, **tranne i prezzi di partenza** (vedi 3).
- Acquisti, vendite, piazzamento, acquisto e manipolazione dei Cops mantengono le rispettive regole economiche.
- Eccezioni: il Poker (vedi 2) e il premio della Rissa (vedi 6).

## 2. Poker

- **Lanciare** una partita di Poker **non dà più soldi** (niente 3$, né i 6$ della Skill Preti-2).
- Il **vincitore** incassa invece **2$ per ogni giocatore che ha partecipato**, lui compreso (decisione del game
  designer, 2026-10-20). Il premio arriva dalla **banca**: gli sconfitti non perdono soldi.
- **Pareggio:** si accumulano i premi da 2$ a partecipante. Nessuno viene pagato, le Chip dei giocatori in pareggio
  restano in gioco (jackpot) e il vincitore della partita successiva incassa 2$ per ogni Chip riportata, oltre ai 2$ per
  ogni giocatore che ha partecipato a quella partita (es. pareggio a 2 giocatori, poi vince una partita a 2: 2$ x (2 + 2)
  = 8$).
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

Come nella Big (decisione del game designer, 2026-10-21, che sostituisce la versione più rigida del 2026-10-20):

- Ogni Stonk sposta di **un livello** (in su o in giù) il prezzo di **una Merce a scelta**.
- Gli Stonk della carta si assegnano **a piacere**: su Merci diverse oppure sommati sulla stessa, e si possono anche
  lasciare inutilizzati.
- Il tracciato ha solo quattro livelli: uno Stonk che spinge oltre un estremo non ha effetto (nessun errore).
- Rinunciare del tutto al Marketing (non giocare la carta) resta possibile.
- La versione rigida del 2026-10-20 (ogni Stonk su una Merce diversa, tutti da usare, niente uscita dal tracciato) resta
  nel motore come opzione non attiva (`marketing_mode: "distinct_exact"`). Le partite già salvate in Easy Price
  conservano la chiave nel proprio stato e continuano col Marketing rigido.

## 6. Rissa

Decisione del game designer, 2026-10-20 (solo in questa variante; nella Big e nella Small il vincitore sceglie ancora
tra soldi e carta):

- Il vincitore **ruba sempre una carta** (a caso, dalla mano) a **ciascuno sconfitto**: non si sceglie più tra soldi e
  carta. Se lo sconfitto non ha carte in mano non si ruba nulla.
- Le carte che danno un premio extra **restano e si aggiungono** al furto della carta:
  - SHAKE DOWN (030): prende anche **4$** (2$ + il bonus della carta) allo sconfitto, al massimo quanto ha;
  - SPOILS (039): prende anche **una Merce a sua scelta** (si sceglie solo se lo sconfitto ha più di un tipo di Merce);
  - TAKE THE POT (038): prende anche **una Chip Poker**. Il Covo non tiene mai più di 3 Chip per tipo (decisione del
    game designer, 2026-10-20): se il vincitore ne ha già 3, la Chip dello sconfitto si perde, come per le Merci in
    eccesso (vale anche nella Big);
  - STREET TAX (024), il pedaggio di 1$ per Criminale nemico incassato da chi provoca la Rissa, resta com'è.
- Il testo stampato di SHAKE DOWN dice "4$ invece di 2$": in questa variante non c'è più la base di 2$ a cui
  contrapporlo (la carta dà semplicemente 4$ in più del furto della carta).
- Il pop up "Rissa conclusa" elenca il bottino (carta / 4$ / Chip / Merce) per ogni sconfitto, senza mostrare quale carta.

## 7. Implementazione

- Pacchetto dati sovrapposto: `data_packs/easy_price/` contiene solo `dope_types.json` (tracciati) e
  `game_config.overrides.json` (chiavi sotto); il resto si legge da `data/` (così carte, Job, ecc. restano quelli della Big).
- Chiavi di configurazione (assenti = comportamento Big): `price_change_mode: "extremes"`,
  `poker_launch_pays_money: false`, `poker_launch_cashout: 0`, `poker_win_cash_per_chip: 2`,
  `brawl_reward_mode: "steal_card"`, `ruleset_id: "easy_price"`. Vengono copiate nello stato della partita: i
  salvataggi conservano la variante e quelli precedenti restano compatibili (nuovi campi con valore di default:
  `PlayerState.pending_price_extremes`, `BrawlProgress.pending_outcome`, `LastBrawlOutcome.rewards`).
- Backend: `rules/prices.py` (`set_price_extreme`), `rules/economy.py` (`extremes_mode`, `set_price_extreme`,
  `apply_ordinary_price_step`, validazione del Marketing), `rules/officers.py` (requisizione), `rules/skills.py`
  (Poker), `rules/brawl.py` (furto della carta: `steal_card_mode`, `_apply_steal_reward`), `application/legal_actions.py`
  (opzioni del Marketing e scelta della Merce di SPOILS), `bots/option_picking.py::pick_marketing_options`.
- Frontend: modalità `easy_price` nella schermata iniziale, tabellone dedicato, posizioni dei segnalini prezzo
  (`board-layout.ts`), controlli del Marketing, pagina "Varianti → Variante Easy Price" nel regolamento.
- Test: `backend/tests/unit/test_easy_price.py` (prezzi, Marketing, Poker) e `test_easy_price_brawl.py` (Rissa);
  simulazioni con `tools/run_full_test_game.py --data-dir data_packs/easy_price`.

## 8. Effetti esistenti segnalati (nessuna sostituzione inventata)

- **Crollo del mercato:** nella Big, quando tutte e quattro le Merci arrivano al prezzo massimo il mercato crolla e
  tutti i prezzi tornano al livello più basso. La regola è rimasta invariata: con gli svuotamenti che portano le Merci al
  massimo può ora scattare più facilmente. Da confermare.
- **Skill Preti-2** (Poker: 6$ al lancio): in questa variante vale 0, perché il lancio non dà più soldi.
- **Skill Manager-3** (rigioca il Marketing a fine azione): invariata rispetto alla Big (ripete gli stessi spostamenti; a
  un estremo del tracciato non si va oltre, senza errore).
- **Skill Artisti-2** (acquisti a -1$, vendite a +1$ per unità): modifica il denaro pagato/incassato, non il tracciato;
  compatibile (il prezzo non scende sotto 0).
- **Carte con "al prezzo della Merce più cara/meno cara"** e le carte "Fai 2 Marketing": compatibili (ogni carta di
  Marketing è una risoluzione a sé).
- **Retate / Job basati sul valore delle Merci:** leggono i nuovi valori dei tracciati.
