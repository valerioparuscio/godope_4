# Regole da chiarire

Fonte: `RULES_CANONICAL.md` (trascrizione di `how_to_play_v056`) e `CLAUDE.md`
sezione 22. Quando una voce viene risolta dal game designer, spostarla in
`RULES_CANONICAL.md` con riferimento alla decisione e rimuoverla da qui.

Formato per ogni voce risolta in futuro:

```text
## <numero>. <titolo breve>
Stato: RISOLTO | PROVISIONAL
Decisione: <testo della decisione approvata>
Data: <YYYY-MM-DD>
Riferimento: <link o descrizione della fonte>
```

Tutte le ambiguità di *interazione tra regole* (22 punti originari) sono
state risolte il 2026-07-30, sia leggendo il regolamento completo sia con
decisioni dirette del game designer — dettagli in `RULE_CHANGELOG.md`.
Quello che resta qui sotto sono solo **dati di contenuto** che il
regolamento non fornisce e che nessuna decisione di design può sostituire:
servono i numeri/nomi/testi reali dal gioco fisico.

## Dati mancanti

1. **Carte Clienti — versione definitiva:** è disponibile un dataset di
   100 carte (20 per Contact) in `data/customer_cards_draft.csv` /
   `.xlsx`, ma il game designer ha confermato (2026-07-31) che è una
   **versione non aggiornata**, da usare solo come PROVISIONAL/placeholder
   per sviluppo e test. In particolare 5 carte Politici ("BACKSTABBER")
   hanno un'azione "reputazione" che **non esiste più** nella versione
   corrente delle regole — vanno corrette quando arriva il dataset
   definitivo. Resta da fornire: la versione aggiornata delle 100 carte
   (con le carte Preti che coprono tutte le 6 azioni, non solo 3 come nel
   placeholder).
2. **Adiacenza Q3↔Q6 — RISOLTO (2026-08-02):** confermato dal game
   designer che Q3 e Q6 **non sono adiacenti** — l'asimmetria rilevata da
   `tools/validate_data.py` era un errore nella lista di Q6 (che elencava
   Q3), non un'omissione nella lista di Q3. `data/board.json` corretto
   rimuovendo Q3 dagli adiacenti di Q6.
9. **"Sbirciare una Retata futura" scartando un Cop/Feds comprato (NON
   IMPLEMENTATO):** §C6 lo cita come abilità opzionale dell'acquisto di
   un officer; richiede un modello di informazione nascosta per giocatore
   sulle Retate. `BuyOfficer` copre solo l'acquisto, non questa abilità
   accessoria — resta da implementare, non ancora richiesto dal game
   designer.

## Confermate/risolte dal game designer (2026-08-02)

3. **Rimozione del Fed da uno Spot "senza Merci e senza Ganci" — RISOLTO,
   IMPLEMENTATO:** `rules/links.py::check_spot_fed_removal_for_contact`
   rimuove ogni Fed da uno Spot con `sold_dope_tokens` vuoto quando il
   Contact di quello Spot non ha più **nessun** Link (a nessun livello,
   di nessun giocatore). Chiamata solo dai due punti dove un Link
   *scompare* — `rules/officers.py`'s arresto Fed del Link di livello
   minore, e `rules/turn_flow.py`'s ritorno al Covo del Link speso per
   l'azione extra — mai dal punto che svuota lo Spot vendendo (
   `rules/economy.py::_clear_spot_and_spawn_fed`), che altrimenti
   annullerebbe il Fed appena creato nello stesso istante in cui entra.
4. **Quale pedina evolve in Link su una vendita a pacchetto — RISOLTO:**
   confermato indifferente dal game designer — le posizioni delle
   pedine dentro lo stesso Quartiere sono equivalenti. `rules/economy.py::
   _handle_sell_dope` continua a scegliere deterministicamente la prima
   pedina nell'ordine del comando.
5. **Evoluzione a Link su singola vendita — RISOLTO, CORRETTO
   (2026-08-02):** il game designer ha confermato che deve restare una
   **scelta SI/NO del giocatore** (come dice §A5 "può evolversi"), non
   automatica come implementato in Milestone 3. Nuovo comando
   `EvolveSaleLink(evolve: bool)` e step `ActiveStep.
   WAITING_FOR_LINK_EVOLUTION_CHOICE`, offerto una volta per ogni Spot
   con esattamente 1 venditore nel pacchetto (`PlayerState.
   pending_sale_link_evolutions`, una coda per gestire più Spot da 1
   unità nello stesso pacchetto). La vendita a pacchetto (2-3 unità allo
   stesso Spot) resta automatica, come dice esplicitamente §C4 "si
   prende".
6. **Bersaglio dell'arresto Feds — "il Link di livello minore" fra tutti
   i giocatori — RISOLTO:** confermato. `rules/officers.py::
   _lowest_level_link_at_contact` resta invariata (nessun filtro per
   proprietario).
7. **Sentinella "skip" per il 2° step di Corruzione senza bersagli
   legali — RISOLTO:** confermato. `rules/officers.py`'s `action="skip"`
   resta invariata.
8. **Un pacchetto di Corruzione può invalidare un target successivo
   nella coda — RISOLTO:** confermato. `rules/officers.py::
   _finish_corruption` continua a scartare silenziosamente il resto
   della coda invece di rifiutare l'intero comando.
10. **Associazione Rat↔Merce confiscata nello stesso slot della Jail —
   RISOLTO:** confermato dal game designer esattamente come già
   implementato — i 6 slot si riempiono da 1 a 6 in ordine, sia per Rat
   sia per Merce confiscata, con due ricerche indipendenti ("prima
   posizione libera del proprio tipo") che a volte convergono sullo
   stesso slot e a volte no; non è un accoppiamento forzato.
11. **Furto di 1 carta come ricompensa — casuale — RISOLTO:** confermato.
   `rules/brawl.py` resta invariata (scelta casuale, sotto-seed
   deterministico).
12. **Sforamento delle 5 carte per un "bystander" di Rissa — RISOLTO,
   CORRETTO (2026-08-02), RIBALTATO (2026-08-15):** il game designer aveva
   confermato che il check delle 5 carte avviene solo alla fine del
   **turno** del giocatore (inteso allora come l'intero turno di 3
   round); una carta ricevuta durante il turno di un altro giocatore si
   teneva senza scartare, anche oltre il limite, finché non arrivava la
   fine del proprio turno. **Il 2026-08-15 il game designer ha chiarito la
   terminologia turno/round** (un turno = 3 round; 3 turni a partita = 9
   round per giocatore, vedi `RULES_CANONICAL.md` §B2) **e ribaltato la
   decisione: il check scatta alla fine di ogni round**, non solo
   dell'ultimo dei 3 round di un turno — quindi fino a 9 volte a partita
   per giocatore, non 3. Implementato in
   `rules/turn_flow.py::_continue_after_main_action` (rimossa la
   condizione `_is_players_last_round`). Resta comunque vero che una
   carta ricevuta durante il round di un *altro* giocatore si tiene senza
   scartare finché non arriva la fine del **proprio prossimo round**
   (finestra più stretta di prima, ma stesso principio): resta rimosso
   `rules/brawl.py::_enforce_bystander_hand_limit` (lo scarto automatico e
   casuale introdotto in Milestone 4) — un bystander trattiene
   semplicemente le carte in eccesso fino al proprio prossimo round.
   `domain/invariants.py::_check_hand_size` rimosso — non esiste più un
   punto di campionamento affidabile dove "tutti devono avere ≤5 carte"
   valga sempre.
13. **Poker — "5 uguali" — RISOLTO (2026-08-02):** il game designer ha
   confermato che "5 uguali" **non può mai verificarsi**: il banco non
   ha mai 3 simboli identici, quindi nessuna mano di 5 simboli (i 3 del
   banco + i 2 della carta rivelata) può mai essere monocolore. Rimosso
   il ramo `shape_counts == [5]` da `rules/poker.py::_hand_score`
   (diventa un caso dell'`AssertionError` finale, "non dovrebbe mai
   accadere"); la categoria di vertice della classifica è sempre "5
   diversi" (`"five_different"`, rinominata da `"five_same_or_diff"` in
   `data/game_config.json`'s `poker_rank_order`), sempre in parità con
   ogni altra mano "5 diversi" (nessun colore dominante da confrontare).
14. **Poker — beneficiario del jackpot su ulteriore pareggio — RISOLTO:**
   confermato esattamente come implementato. `rules/poker.py` resta
   invariata.
15. **Poker — arresto del Gambler sconfitto con Jail piena — RISOLTO
   (2026-08-02):** il game designer ha chiarito che la Jail **non è mai
   piena** nel momento dell'arresto: il 6° Rat che entra innesca
   l'Evasione immediatamente (`rules/jail.py::arrest_pawn`), svuotando
   tutti e 6 gli slot prima che quella stessa chiamata ritorni. Con Jail
   a 5 e 2 sconfitti a Poker, il primo arresto è il 6° e innesca
   l'Evasione (quella pedina evolve in Link Politici, non resta Rat); il
   secondo arresto va poi nella Jail ormai vuota. Il ciclo per-sconfitto
   in `rules/poker.py::_resolve_match` ricontrollava già
   `jail.has_free_rat_slot` a ogni singolo arresto (non una volta sola
   prima del ciclo), quindi il comportamento era già corretto — nessuna
   modifica al codice, solo un test di regressione dedicato
   (`test_second_defeated_gambler_is_arrested_right_after_the_first_triggers_evasion`).
16. **Job — bonus Link/Skill senza risorsa disponibile — RISOLTO:**
   confermato per il caso generale. `rules/jobs.py::_handle_choose_job_reward`
   resta invariata (nessun effetto, silenziosamente) — **eccetto** il Job 8
   ("Abbi tutti i 10 Criminali fuori dal Covo"), per cui il game designer
   (2026-09-02) ha chiesto un'eccezione specifica: la sua colonna 2 (Link)
   non dà più nulla in silenzio, ma offre la scelta tra $3 o 2 carte
   (`JobDefinition.column_bonus_overrides`, `JobBonusType.
   MONEY_OR_TWO_CARDS`) — Job 8 è l'unico caso in cui completarlo implica
   *sempre* zero pedine in Covo, quindi il caso "nessun effetto" non era
   mai solo un edge case raro, ma la norma per quella colonna.
17. **Job — sforamento delle 5 carte dal bonus "2 carte" fuori dal
   proprio turno — RISOLTO, CORRETTO (2026-08-02), RIBALTATO (2026-08-15):**
   stessa correzione del punto 12 — il check delle 5 carte avviene alla
   fine di ogni round (fino a 9 a partita per giocatore), non solo alla
   fine del turno di 3 round, ma resta vero che non scatta fuori dal
   proprio round. Rimosso `rules/jobs.py::
   _enforce_hand_limit_after_bonus`.
18. **Manager-3 "Applichi Stonk 2 volte" — RISOLTO (Milestone 5 Stage
   4c-bis, 2026-08-02):** era bloccato perché il meccanismo di base
   Marketing/Stonk (§D3) non esisteva ancora nel motore; implementato
   insieme a Marketing stesso (vedi punto 21) — `rules/skills.py::
   marketing_applies_both_timings`: se il giocatore ha usato Marketing
   "prima" dell'azione, le stesse allocazioni si ripetono
   automaticamente "dopo", senza scartare una nuova carta.
19. **Artisti-3/Studenti-3 "mandi dal Covo sul Link" — scelta della
   pedina e fallback — RISOLTO, CORRETTO (2026-08-02):** confermato che
   queste due Skill sostituiscono l'evoluzione esistente (non aggiungono
   a essa). Il game designer ha corretto il fallback: se il Covo non ha
   una pedina libera, **si manda dal Quartiere come di consueto**
   (comportamento normale, come se il giocatore non avesse la Skill) —
   non più "l'evoluzione salta silenziosamente". Per Artisti-3
   (`rules/economy.py::_evolve_sale_link`) e Studenti-3 (`rules/brawl.py::
   _auto_apply_brawl_link_from_base`, che ora lascia `link_evolution_done`
   `False` in questo caso, facendo scattare naturalmente la normale
   scelta del vincitore `ChooseBrawlLinkEvolution`). Resta la scelta
   deterministica "prima pedina IN_BASE" per quale pedina del Covo usare
   quando ce n'è una disponibile (non contestata dal game designer).
20. **Studenti-2 "hai una Pistola in più" — ambito del bonus — RISOLTO,
   CORRETTO (2026-08-02):** il game designer ha confermato che il bonus
   si applica **sempre**, anche a un partecipante che non ha giocato
   nessuna carta in quella Rissa ("tutti i presenti nel quartiere
   partecipano sempre in ogni caso, anche se non giocano carte").
   Corretto `rules/brawl.py::_force_by_player`: il bonus ora si somma
   direttamente alla Forza base (Criminali + Link) di ogni partecipante
   con la Skill, incondizionatamente, invece di essere agganciato al
   meccanismo di assegnazione Pistole di una carta giocata.
21. **Marketing/Stonk — semantica "prima/dopo" — RISOLTO, CORRETTO
   (2026-08-02), SUPERATO (2026-08-17):** il game designer aveva chiarito
   che "prima o dopo lo svolgimento dell'azione" si riferisce all'**intera
   azione** (l'intero pacchetto Buy/Sell, incluso il suo step di prezzo
   automatico), non al solo step automatico come implementato
   inizialmente — Marketing "prima" offerto subito dopo
   `ChooseActionType`, "dopo" offerto in coda a `BuyDope`/`SellDope`.
   **Superato il 2026-08-17:** l'offerta "dopo" è stata rimossa del tutto
   — Marketing si gioca **solo prima**, un tentativo per azione (vedi
   `RULE_CHANGELOG.md` 2026-08-17). `PlayMarketingCard.allocations` non
   porta più un flag `apply_before` per singolo Stonk (non serviva già
   più dal 2026-08-02, e ora il timing è sempre "prima", niente altro da
   determinare). Confermato inoltre esplicitamente che gli Stonk di una
   carta si possono dividere tra più Merci a scelta, non solo accumulare
   sulla stessa.

   **Quale carta — RISOLTO (2026-08-15):** il game designer ha confermato
   che con più di una carta idonea in mano è una scelta reale del
   giocatore, non un auto-pick della carta con più Stonk. Aggiunto un
   sotto-passo dedicato `ChooseMarketingCard`/decision_type
   `choose_marketing_card` (`application/legal_actions.py::
   _choose_marketing_card_decision`), offerto solo con 2+ carte idonee —
   con esattamente una carta idonea non c'è nulla da scegliere, si passa
   dritti all'allocazione degli Stonk come prima. La scelta è
   declinabile (equivale a rifiutare Marketing del tutto per quell'offerta).

22. **Compra/Vendi Merce — presenza abilitante di un Link, non solo di un
   Criminale — RISOLTO (game designer, 2026-08-15):** confermato che un
   Link conta come presenza in entrambi i Quartieri del proprio Contact
   per Compra/Vendi Merce, esattamente come già valeva per la corruzione
   di Cops/Feds (`rules/officers.py::has_presence_at_hood/_at_spot`, ora
   spostate in `rules/economy.py` per essere condivise). Compra Merce
   richiede una scelta esplicita di *quale* Quartiere quando il Link ha
   scorta legale in entrambi (i due Quartieri di uno stesso Contact hanno
   scorte/prezzi indipendenti) — `BuyDope.pawn_ids` è diventato
   `BuyDope.purchases: tuple[(pawn_id, hood_id), ...]`. Vendi Merce non ha
   bisogno di questa disambiguazione: i Punti di Vendita sono per
   Contact, non per Quartiere, quindi i due Quartieri di un Contact danno
   sempre accesso agli stessi 2 Spot (`SellDope.sales` invariato).

   **Resta PROVVISORIO:** quando un Link (già Link, non Criminale) vende,
   non innesca né l'offerta di evoluzione a Link né una sua eventuale
   "evoluzione ulteriore" — il regolamento parla solo di "il Criminale
   che ha venduto può evolvere in un Link", mai di un Link che evolve
   ulteriormente. Un pacchetto venduto allo stesso Spot da soli pedine
   Link (nessun Criminale tra i venditori) salta quindi del tutto
   l'offerta di evoluzione per quello Spot (`rules/economy.py::
   _handle_sell_dope`, `criminal_seller_ids`); un pacchetto misto
   Criminale+Link converte comunque un Criminale, con livello pari al
   totale di merci vendute (Link inclusi). Non ancora sottoposto al game
   designer.

23. **Covo pieno all'acquisto — RISOLTO (game designer, 2026-08-23):**
   quando il Covo ha già 3 unità di una Merce, un ulteriore acquisto di
   quello stesso tipo viene **rifiutato** (bloccato), non lasciato
   avvenire per poi scartare la Merce a posteriori. Le altre unità dello
   stesso pacchetto (di un tipo diverso, non ancora al limite) restano
   acquistabili normalmente nello stesso comando. `rules/economy.py::
   _handle_buy_dope` ora rifiuta con `base_inventory_full` l'unità che
   sforerebbe il limite, invece di emettere `DopeLostToOverflow` (evento
   ancora usato solo dal recupero Merce durante l'Evasione,
   `rules/jail.py`, non toccato da questa decisione — **resta
   PROVVISORIO**, era la seconda metà del punto CLAUDE.md §22 #26).
   `application/legal_actions.py::_buy_dope_options` resta invariata
   deliberatamente: continua a offrire ogni opzione individualmente
   legale senza budget condiviso a tempo di generazione (stesso principio
   già documentato lì per la scorta di Quartiere); il bot
   (`bots/random_legal.py::_pick_buy_dope_options`) budgeta ora anche la
   capacità residua del Covo per tipo, oltre alla scorta di Quartiere già
   presente, per non proporre mai un pacchetto che verrebbe rifiutato.

## Bug noti (non ambiguità di regole — motore, da correggere)

24. **Nondeterminismo del motore fra processi diversi (stesso seed, stesso
   `rules_version`) — UN'ISTANZA TROVATA E CORRETTA (2026-09-01), sospetto
   originario non escluso:** scoperto durante gli sweep di `tools/
   run_full_test_game.py` per le Card Boost (2026-08-27/28) — confermato
   allora sia sul codice delle Card Boost sia su `main` prima di quel
   lavoro, quindi preesistente. Sospetto originario: un punto del motore
   itera un `set`/`dict` la cui iterazione dipende dall'hash di stringa,
   sensibile a `PYTHONHASHSEED` (randomizzato per processo salvo fissato
   esplicitamente). Viola CLAUDE.md §3.2 ("a parità di seed... il
   risultato deve essere identico").

   **Metodo di riproduzione (funziona in modo affidabile, a differenza del
   semplice "rilanciare il processo e sperare"):** eseguire lo stesso lotto
   di seed due volte con `PYTHONHASHSEED` fissato esplicitamente a due
   valori diversi (es. `PYTHONHASHSEED=1` vs `PYTHONHASHSEED=999`) e
   confrontare un fingerprint deterministico dello stato finale (hash
   SHA-256 del JSON via `domain/serialization.py::to_json_dict`) per ogni
   seed — su un lotto di 300 seed, 3 (150/228/279) differivano. Per
   individuare il punto esatto di divergenza: rieseguire lo stesso seed
   sotto i due `PYTHONHASHSEED`, stampando una riga per decisione
   (`decision_type` + tupla ordinata di `option_id`) e confrontare le due
   trascrizioni — la prima riga diversa è il generatore di opzioni
   colpevole (non serve indovinare leggendo il codice).

   **Istanza trovata con questo metodo:** `application/legal_actions.py`'s
   ramo `PawnRole.LINK` di `_move_criminal_options` (carte 034/035
   "REPOSITION", Wave 2k, 2026-08-31) costruiva l'insieme degli Hood
   adiacenti con una comprehension `{...}` (un `set`) e poi iterava
   *quell'insieme* per generare le opzioni — l'ordine delle opzioni
   offerte per un Link con più destinazioni possibili variava quindi fra
   processi, e `bots/option_picking.py`'s picker (shuffle+cammino su una
   lista con lo stesso seed RNG ma un ordine di partenza diverso) sceglie
   un'opzione diversa di conseguenza, facendo divergere tutto il resto
   della partita. Corretto sostituendo l'iterazione del `set` con un
   ordine costruito da `own_contact_hood_ids` (una lista, ordine di
   `state.board.hoods.items()`, deterministico) — il `set` resta solo per
   la deduplicazione (`in`, mai iterato).

   **Verifica:** i 3 seed noti (150/228/279) ora coincidono esattamente
   fra `PYTHONHASHSEED` diversi; un resweep di 4000+ seed aggiuntivi
   (1-1000 e 1-3000, con coppie di `PYTHONHASHSEED` diverse ogni volta) non
   ha trovato altre divergenze.

   **Non ancora escluso:** questa istanza è nel codice di carte 034/035,
   scritto oggi (2026-08-31) — non può essere la stessa istanza già
   osservata "su main prima" del lavoro Card Boost (2026-08-27/28), che
   quindi potrebbe essere un'istanza *diversa*, non ancora trovata, dello
   stesso pattern (probabilmente più rara, dato che 4000+ seed dopo questa
   correzione non l'hanno fatta riemergere). Se il sintomo si ripresenta,
   ripartire dal metodo di riproduzione sopra invece di rileggere tutto il
   codice da capo — ogni futura iterazione su un `set`/`frozenset` di
   stringhe di dominio (HoodId/PawnId/ContactId/...) il cui *ordine*
   (non solo l'appartenenza) influenza una scelta è un sospetto.

25. **Un Poker in sospeso può restare senza carte da rivelare — TROVATO E
   CORRETTO (2026-09-02):** scoperto durante lo sweep 2026-08-27 (seed
   288, riprodotto solo tramite il nondeterminismo del punto 24, non in
   modo affidabile sullo stesso seed). Diagnosi originaria (`hand_discard`
   di fine round, Marketing o una Card Boost che scarta le carte
   "riservate" da `_handle_place_poker_bet`) **verificata e scartata**:
   scambio/scarto mano avviene solo durante `ACTION_PHASE`, la puntata e
   ogni rivelazione avvengono tutte dentro `POKER_PHASE` senza finestre
   intermedie — nessuno di quei 3 eventi può materialmente interporsi fra
   una puntata e la sua rivelazione.

   **Causa reale trovata rileggendo `application/legal_actions.py::
   _play_poker_card_decision`:** Preti-1 ("puoi giocare 2 carte per ogni
   Poker") lascia `max_selectable` fisso a `min(2, len(options))` —
   senza considerare che lo stesso giocatore può avere puntato su *più*
   partite (fino a 2/turno) e dover rivelare ancora per le altre dopo
   questa. `_handle_place_poker_bet`'s check iniziale garantisce solo
   ">= 1 carta non-Preti per partita puntata" in totale, non "per
   partita nel momento in cui tocca a lei" — un bettor con esattamente 2
   carte disponibili e puntato su 2 partite può rivelarle *entrambe* per
   la prima partita che si risolve (una scelta legittima, "puoi" non
   "devi"), lasciando la seconda partita a 0 carte rivelabili quando
   arriva il suo turno: esattamente il sintomo osservato
   (`min_selections=1`, 0 opzioni).

   **Corretto:** `_play_poker_card_decision` ora calcola quante *altre*
   partite ancora aperte (dopo `resolving_match_index`) hanno questo
   stesso giocatore fra i bettor, e capa `max_selectable` per lasciarne
   sempre almeno 1 di riserva per ciascuna. Ricontrollato anche in
   `rules/poker.py::_handle_play_poker_card`
   (CLAUDE.md §10: mai fidarsi solo del generatore di opzioni) — rifiuta
   esplicitamente (`would_starve_a_later_reveal`) una rivelazione a 2
   carte che lascerebbe meno carte non-Preti di quante partite aperte
   restano. Nuovo test di regressione dedicato in `tests/unit/
   test_poker.py` (verificato che fallisce contro il codice precedente,
   sia lato generatore sia lato handler).

## Card Boost — cronologia implementazione ("wave" successive)

26. **Effetti delle Customer Card — completate (Wave 1-2k, 2026-08-31):
   80/80 carte con `boost_text` hanno ora un `effect` non-null.** Le 20
   carte Preti "GAMBLE" restano `effect: null` per design (nessun
   `boost_text` stampato — non fanno parte di questo conteggio, vedi
   `dataset_note`). `data/customer_cards.json`'s `dataset_note` spiega la
   convenzione (`effect: null` = "non ancora implementato", il
   `boost_text` resta il testo reale). Le carte implementate
   (rules/customer_cards.py, rules/skills.py, economy.py, movement.py,
   rules/brawl.py, rules/officers.py, application/legal_actions.py):
   Wave 1 — 002,003,006,008,009,010,011,014,016,018,019,020,046,047,050,
   060,067,068,072,079 (riusano `skills.py`'s `cost_delta`/`extra_grit`/
   `trade_price_delta`, o effetti bespoke già scritti in economy.py:
   `price_at_extreme`/`pre_action_restock`/`pre_action_clear_spot`/
   `extra_price_step`/`bonus_card_draw_per_unit` per Place). Wave 2a —
   001,005 (`self_arrest_after_action`, economy.py: la prima pedina del
   pacchetto Buy/Sell finisce in prigione come Rat a fine pacchetto),
   029,031 (`bonus_card_draw_per_unit` esteso a Move, movement.py), 022
   (`provoker_gun_bonus`, rules/brawl.py::`_force_by_player` — testo
   sostituito dal game designer, 2026-08-28: il vecchio "puoi ritirare il
   dado 2 volte" non aveva alcun meccanismo di dado a cui agganciarsi,
   diventato "hai +2 Pistole" se il giocatore è
   `progress.triggering_player_id`, non ogni partecipante come lo
   Studenti-2 di `skills.py::extra_gun_bonus`).

   **Bug trovato dall'utente e corretto (2026-09-02):** 029/031/046/050
   (tutte le carte con `bonus_card_draw_per_unit`) pescavano 3 carte
   totali invece delle 2 stampate sulla carta ("prendi/pesca DUE carte
   per ogni...") — `data/customer_cards.json`'s `effect.count` era 2,
   sommato alla pescata normale che ogni piazzamento/movimento fa già da
   solo (economy.py/movement.py), invece di 1 (il `count` è le pescate
   *extra*, non il totale). Corretto il dato per tutte e 4 le carte; test
   dedicati in `tests/unit/test_economy.py` (sia a livello di codice —
   verificano il totale finale di 2 — sia a livello di dato — verificano
   `effect.count == 1` per tutte e 4, cosicché una regressione del dato
   da solo, senza toccare il codice, venga comunque colta).

   Wave 2b (2026-08-28) —
   065 (`officer_move_anywhere`, rules/officers.py::`_apply_move`: nessun
   vincolo di adiacenza — scoperto e corretto nello stesso giro un bug
   preesistente indipendente, `_apply_move` non aveva mai controllato
   "revealed" sul Cop neanche per una mossa adiacente normale, quindi
   nessun controllo del genere è stato aggiunto neanche per "ovunque"),
   063/064 (`keep_confiscated_dope`, rules/officers.py::
   `_apply_confiscate`: la Merce va subito nel Covo del corruttore via il
   nuovo `jail.recover_dope` — pubblico, prima `_recover_dope` privato,
   condiviso con `_resolve_evasion`), 004 (`same_contact_hood_presence`,
   legal_actions.py::`_buy_dope_options` — un Criminale ottiene la stessa
   portata Contact-wide che un Link ha già gratis), 017
   (`adjacent_hood_presence` — bersaglio invece un Quartiere adiacente
   sulla mappa, indipendente dal Contact: diverso da 004, non
   intercambiabile), 007/015 (`repeat_pawn_target`, economy.py — un pawn
   può comparire fino a `max_repeats` volte nello stesso pacchetto;
   scoperto e corretto nello stesso giro un bug che sarebbe emerso solo
   con questo boost: `_handle_sell_dope`'s riordino "pedina che evolve
   per prima" filtrava per `!=` invece di rimuovere una sola occorrenza,
   azzerando il livello del Link risultante quando la stessa pedina
   vendeva più unità allo stesso Spot — ora usa `list.remove`). Wave 2c
   (2026-08-28) — 041/049 (`place_double_no_draw`, un moltiplicatore ×2
   applicato dopo gli Skill additivi in `skills.py::
   effective_action_count`, condiviso da generatore di opzioni e
   validatore come ogni altro Skill "+Grinta"; il "non peschi carte" vive
   invece in `economy.py::_handle_place_criminal`, che salta del tutto il
   pescaggio normale quando questo boost è attivo — la variante 052/056
   della stessa "REINFORCE" è un meccanismo di moltiplicazione
   completamente diverso, implementato solo più avanti in Wave 2g), 012
   (`adjacent_hood_presence` sul lato Sell — vedi il bug di forma del
   comando risolto qui sotto). Wave 2d (2026-08-31) — 076/077/080
   (`arrest_extra_target`) e 078 (`confiscate_extra_unit`,
   rules/officers.py::`_apply_arrest`/`_apply_confiscate`): a differenza
   dell'ipotesi iniziale ("richiede una modifica alla forma del
   comando"), implementate come un secondo bersaglio/unità scelti
   *automaticamente* dopo il primo — stessa convenzione "posizione
   equivalente" di RULES_PENDING.md #4 — invece di una seconda scelta
   interattiva del giocatore, evitando così di toccare
   `ChooseCorruptionAction`; best-effort, silenziosamente saltato se non
   resta un secondo bersaglio/slot Jail libero (per il Cop: un secondo
   Criminale nello stesso Quartiere / una seconda Merce dalla stessa
   scorta; per il Fed: il Link di livello più basso ricalcolato dopo il
   primo arresto / una seconda Merce dallo stesso Spot).

   **Card 012 — bug di forma del comando risolto (`SellDope.explicit_spots`,
   2026-08-28):** a differenza di 004/017 (Buy), `SellDope.sales` porta
   solo `(pawn_id, dope_type)` — nessun `contact_id`/`spot_id` — perché
   finora un pawn aveva sempre *un solo* Contact raggiungibile, e
   `_find_spot(contact_id, dope_type)` lo derivava internamente senza
   ambiguità. Con `adjacent_hood_presence` un Criminale può raggiungere
   *più* Contact contemporaneamente — se due Contact adiacenti accettano
   lo stesso tipo di Dope, il comando non aveva più modo di sapere quale
   Spot il giocatore intendeva. Risolto aggiungendo un campo opzionale
   `explicit_spots: tuple[tuple[PawnId, DopeType, SpotId], ...]` (non un
   `dict` — una chiave tupla `(pawn_id, dope_type)` non sopravvive al
   codec generico di `domain/serialization.py`, che serializza le chiavi
   `Mapping` come stringhe JSON, lo stesso motivo per cui `sales` stesso è
   già una tupla di coppie invece di un `dict`); vuoto/assente per un
   pawn ricade sulla derivazione originale, quindi ogni chiamante
   preesistente (bot, endpoint di debug, test) resta invariato.
   `legal_actions.py::build_command_from_selection` lo popola sempre
   dallo `spot_id` già presente nel payload dell'opzione, non solo
   quando questo boost è attivo. Wave 2e (2026-08-31) — 033
   (`move_to_jail`, rules/movement.py::`move_one_pawn`) e 043/045
   (`place_to_jail`, rules/economy.py::`_handle_place_criminal`): nuovo
   sentinel `domain/ids.py::JAIL_ID`, stesso schema già usato per `DEN_ID`
   (un `HoodId` speciale accettato solo quando il boost è attivo, mai una
   vera scorciatoia costruibile dal client). 054/059 (`place_to_jail_
   evasion_immune`): stesso `JAIL_ID`, più un nuovo campo
   `PawnState.jail_evasion_immune` consumato una sola volta da
   `rules/jail.py::_resolve_evasion`.

   **PROVISIONAL (054/059):** il testo non dice cosa succede se il Rat
   immune è proprio quello che fa scattare l'Evasione (normalmente
   evolverebbe in Link Politici). Implementato applicando "non evade"
   in modo uniforme: resta un semplice Rat anche in quel caso — nessun
   Link evolve quel turno, non inventata un'evoluzione sostitutiva per
   qualcun altro. Non ancora sottoposto al game designer.

   Wave 2f (2026-08-31) — 048/055 (`place_in_den`, fino a 2 pedine) e
   042/057 (`place_in_den_evict_enemy`, 1 pedina + rimozione automatica
   di una pedina nemica dal Den): `PlaceCriminal.den_deck_contact_ids`,
   nuovo campo opzionale a tupla parallela (stesso motivo di
   `SellDope.explicit_spots` sopra — niente chiavi-tupla in un `dict`,
   il codec di serializzazione non le sopravvive), una voce per ogni
   occorrenza di `DEN_ID` in `hood_ids`, consumata nello stesso ordine;
   `rules/economy.py::_handle_place_criminal` applica gli stessi effetti
   di ingresso nel Den di `rules/movement.py`'s `DEN_ID` (ruolo Gambler,
   pescaggio dal mazzo scelto) raggiunti però direttamente dal Covo.
   L'espulsione di 042/057 è automatica/best-effort (nessuna nuova
   decisione interattiva, no-op se nessun Gambler nemico è nel Den),
   stessa convenzione di 076/077/080/078 (Wave 2d). Bug scoperto e
   corretto nello stesso giro: `adapters/http/app.py::_build_command`
   non passava affatto `den_deck_contact_ids` al costruire un
   `PlaceCriminal` da `/commands` (a differenza del percorso
   `/decisions/answer` via `build_command_from_selection`, già corretto),
   quindi qualunque client che passasse dall'endpoint `/commands`
   generico avrebbe sempre fallito con `deck_choice_required` — scoperto
   da `tests/integration/test_http_app.py::
   test_full_game_completes_through_http` dopo l'estensione dell'help
   `_command_type_and_payload` a questo nuovo campo.

   Wave 2g (2026-08-31, tutte e 3 confermate dal game designer dopo una
   domanda diretta su ciascuna ambiguità residua):
   - 044/051 (`invade_own_hoods`, "INVADE" — "ignora il valore di
     Grinta": confermato senza tetto, non solo un bonus additivo sopra
     Grinta). `rules/skills.py::effective_action_count` sostituisce
     interamente (non somma) il conteggio con il numero di Hood rivelati
     dove il giocatore ha già presenza (stessa "presenza" canonica di
     `rules/economy.py::has_presence_at_hood`, inlineata lì per evitare un
     ciclo di import economy→skills già esistente) — `application/
     legal_actions.py::_place_criminal_options` offre di conseguenza *solo*
     quegli Hood (un'opzione ciascuno, non le solite duplicate "fino a
     capienza"), e `rules/economy.py::_handle_place_criminal` rivalida lo
     stesso insieme lato comando (mai più di un bersaglio per Hood).
   - 052/056 (`reinforce_dope_discard`, "REINFORCE con Grinta 3" —
     confermato: il prezzo di *vendita* corrente della Merce scartata,
     capato a valle dalle pedine/denaro realmente disponibili, esattamente
     come già avviene per ogni altro pacchetto Place). "Con Grinta 3" si è
     rivelato un vincolo di *giocabilità* della carta, non solo del suo
     effetto — nuovo `ActiveStep.WAITING_FOR_REINFORCE_DISCARD` e comando
     `ChooseReinforceDiscard(dope_type)`, inserito da
     `rules/customer_cards.py::_handle_play_customer_card_boost` al posto
     della ripresa immediata che ogni altro boost fa (il conteggio bersagli
     dipende dalla Merce scelta, non ancora nota quando la carta viene
     giocata); `reinforce_discard_eligible` (Grinta==3 *e* almeno una
     Merce in Covo) è controllata sia per offrire la carta
     (`can_play_boost_for_action` in `rules/customer_cards.py`,
     `_card_boost_decision` in `legal_actions.py`) sia di nuovo al momento
     di giocarla (CLAUDE.md §10).
   - 032/036 (`double_den_draw`, "PLAY!!" — "peschi 2 carte a scelta":
     confermato 2 scelte di mazzo indipendenti, non la stessa carta
     pescata due volte — questo risolve anche il dubbio collegato sulla
     meccanica base "a scelta" del Den, che resta quella già implementata,
     ovvero la scelta del mazzo/Contact da cui pescare, non una carta
     vista in anticipo). `MoveCriminal.extra_den_deck_contact_ids`, stessa
     tupla parallela di `PlaceCriminal.den_deck_contact_ids` (Wave 2f),
     una voce per ogni mossa verso `DEN_ID` in `moves`; internamente la
     coda di mosse di `rules/movement.py::process_move_queue` è passata a
     4-tuple `(pawn_id, destinazione, deck_contact_id,
     extra_deck_contact_id)` invece di una tupla parallela separata,
     perché deve sopravvivere intatta a una Rissa che mette in pausa il
     pacchetto a metà (`BrawlProgress.remaining_moves`) — la forma
     pubblica del comando `MoveCriminal.moves` non cambia.

   Wave 2h (2026-08-31) — 061/062 (`fake_police_dope_payment`, "FAKE
   POLICE" — confermato dal game designer: 1 Merce di qualunque tipo,
   costo pieno, nessun resto, al posto dell'intero costo in denaro della
   corruzione): non un costo per singola sotto-azione (move/arrest/
   confiscate, $1 ciascuna secondo la decisione 2026-08-15 già in
   vigore) ma un pagamento unico per l'intera corruzione, scaricato in
   `rules/officers.py::_start_corruption` (che sceglie automaticamente
   quale tipo scartare — il primo con scorta >0, nessuna nuova
   decisione interattiva) — ogni sotto-azione successiva della stessa
   corruzione resta quindi gratuita in denaro
   (`_handle_choose_corruption_action`'s `action_cost` diventa 0),
   incluso il controllo "puoi ancora permettertene una" che decide se lo
   skip è consentito prima della prima azione. Ricontrollato in 3 punti
   indipendenti come da CLAUDE.md §10 (generatore opzioni
   `application/legal_actions.py::_corrupt_officer_options`, verifica
   pacchetto `_handle_corrupt_officer`, verifica per-corruzione
   `_start_corruption`) — nessuno slot Jail o meccanismo di scambio
   Merce↔denaro generico inventato, solo uno scarto diretto dal Covo.

   Wave 2i (2026-08-31) — cluster "FIGHT!!" (Studenti, tutte le carte con
   `action_type: move_criminal` il cui boost dipende dall'esito di una
   Rissa che quella stessa mossa può innescare), confermato dal game
   designer carta per carta:
   - 025/026/027 (`provoker_gun_bonus`, "hai +2 di Criminalità"):
     confermato sinonimo del "+2 Pistole" già implementato dalla carta
     022 — stesso effect dict `{"type": "provoker_gun_bonus", "amount":
     2}`, nessun codice nuovo.
   - 024/030/040 (`brawl_trigger_toll`, "se inizi una Rissa, prendi 1$ da
     ogni pedina nemica" — scope confermato: solo le pedine avversarie
     *fisicamente nello stesso Quartiere*, cioè gli stessi partecipanti
     alla Rissa): applicato in `rules/brawl.py::start_brawl` appena la
     Rissa parte, indipendentemente da come si risolve poi — un evento
     `BrawlTriggerTollCollected` per ogni avversario derubato, capato dal
     denaro realmente disponibile della vittima (`min(importo, denaro)`,
     stessa clausola difensiva già usata per la ricompensa "money").
   - 037/038 (`brawl_reward_money_bonus`, "rubi 5$ invece di 3$"): **bug
     di baseline scoperto** — la ricompensa "money" già implementata
     ruba `min(2, denaro dello sconfitto)`, cioè 2$, non 3$ come le
     carte assumono. Confermato dal game designer: 037/038 diventano un
     "+2$" flat sopra la base *reale* (min(4, denaro), non un valore
     assoluto di 5$) — si applica solo se il *vincitore* (non
     necessariamente chi ha innescato la Rissa) è chi ha giocato la
     carta, cioè "se vinci", non "se inizi".
   - 021/023 (`brawl_reward_dope_theft`) e 028/039
     (`brawl_reward_chip_theft`): due nuovi `reward_type` ("dope"/
     "poker_chip") accanto ai 2 esistenti ("money"/"card") in
     `ChooseBrawlLoserReward` — offerti solo quando il vincitore ha il
     boost giusto *e* lo sconfitto ha davvero qualcosa da rubare (una
     Merce qualunque > 0, o `poker_chip_count` > 0); il tipo di Merce
     rubata è scelto automaticamente (il primo tipo con scorta >0),
     nessuna nuova decisione interattiva per un'unità singola. Entrambi
     i controlli di eleggibilità sono ripetuti nel command handler
     (`rules/brawl.py::_handle_choose_brawl_loser_reward`), non solo nel
     generatore di opzioni (CLAUDE.md §10) — bug trovato e corretto nello
     stesso giro: la prima stesura permetteva a *chiunque* di inviare
     `reward_type="dope"`/`"poker_chip"` anche senza il boost attivo.

   Wave 2j (2026-08-31):
   - 069/070/071 (`officer_move_cross_type`, "REASSIGN" — **ipotesi
     iniziale sbagliata, corretta dal game designer**: non sposta affatto
     una Merce — sposta l'*ufficiale corrotto* stesso fra un Quartiere e
     un Punto di Vendita dello stesso Contact, che così cambia tipo: un
     Cop spostato su uno Spot diventa un Fed lì, un Fed spostato su un
     Hood diventa un Cop — solo entro il proprio Contact, "del cliente").
     Estende la sotto-azione "move" già esistente della corruzione con
     un secondo tipo di destinazione (non la sostituisce): `rules/
     officers.py::_apply_move` riconosce se `target_id` è uno Spot o un
     Hood e converte `officer_type`/`location_type` di conseguenza;
     nuovo evento `OfficerCrossTypeMoveApplied` accanto al normale
     `OfficerMoved`. Ricontrollato in 3 punti come da CLAUDE.md §10
     (opzioni `_corruption_action_candidates`, applicazione `_apply_move`,
     disponibilità `has_any_corruption_action_available`).
   - 073/074/075 (`redeem_release_rats`, "REDEEM" — confermato dal game
     designer: il corruttore libera 2 propri Rat già in Jail invece di
     arrestare): sostituisce del tutto la sotto-azione "arrest" (per
     entrambi i tipi di ufficiale, dato che "invece di arrestare" non
     distingue Cop/Fed) — nuova `jail.py::release_rat`, stessa logica
     "torna al Covo + recupera la Merce del proprio slot" già usata da
     `_resolve_evasion` per un Rat non scatenante, ma senza toccare
     `JailEscapeTriggered`/l'evoluzione a Link Politici (non è quel
     trigger). Non serve uno slot Jail libero (ne libera, non ne
     riempie), quindi bypassa quel controllo su tutti e 3 i punti dove
     compare (opzioni, applicazione, disponibilità).

     **PROVISIONAL (073/074/075):** "a scelta del corruttore" è
     interpretato come "il giocatore sceglie *se* usare questa abilità"
     (la scelta stessa), non come una vera scelta di *quali* 2 Rat fra
     più disponibili — quelli liberati sono i 2 con indice di slot Jail
     più basso, stesso criterio "primo disponibile" già usato ovunque in
     `jail.py`. Non ancora sottoposto di nuovo al game designer per
     confermare se serva davvero una scelta interattiva.

   Wave 2k (2026-08-31) — le ultime 6, tutte chiarite dal game designer
   nello stesso giro (nessuna carta Tier 3 residua: **80/80 Customer
   Card boost implementate**):
   - 013 (`spot_fill_bonus_links`, "SPREADING" — confermato: solo quando
     una singola vendita del pacchetto riempie/svuota il PdV e fa
     entrare un Fed, il giocatore prende 2 Link *aggiuntivi*, livello 1 e
     livello 2, da altre 2 pedine del Covo — in aggiunta, non al posto,
     al normale Link-per-Spot del pacchetto stesso, §C4): nuovo
     `_grant_spot_fill_bonus_links` in `rules/economy.py`, chiamato
     subito dopo `_clear_spot_and_spawn_fed`, best-effort se meno di 2
     pedine IN_BASE sono disponibili.
   - 034/035 (`link_reposition`, "REPOSITION" — confermato: il Link
     stesso si sposta verso un Contact adiacente, non un Criminale — un
     Link non ha un "da dove" fisico singolo, quindi l'adiacenza è
     controllata sull'unione degli Hood adiacenti a *entrambi* gli Hood
     del Contact attuale del Link): nuovo ramo `PawnRole.LINK` in
     `rules/movement.py::move_one_pawn`, che riusa `links.insert_link`
     (già gestisce lo scorrimento/espulsione in cascata) per il
     trasferimento — la pedina target *è già* un Link, quindi
     `insert_link` la "reinserisce" semplicemente al nuovo Contact/
     stesso livello, senza bisogno di un passo di rimozione esplicito
     (il vecchio Contact non la trova più una volta cambiato
     `pawn.contact_id`).
   - 053/058 (`shortcut_place_as_link`, "SHORTCUT" — confermato: crea un
     *nuovo* Link livello 1 al Contact dell'Hood scelto, non rinforza uno
     esistente): "un criminale" (singolare) limita l'effetto ad al più 1
     bersaglio per pacchetto (il primo in ordine di comando, stessa
     convenzione "posizione equivalente" di RULES_PENDING.md #4) — gli
     altri bersagli dello stesso pacchetto restano piazzamenti normali.
   - 066 (`insider_choose_jail_slot`, "INSIDER" — confermato: il
     corruttore sceglie *quale* slot Jail libero riceve la Merce
     requisita, fuori ordine, invece del solito "primo libero"): nuovo
     parametro opzionale `slot_index` su `jail.py::confiscate_dope`
     (mutualmente esclusivo con `keep_confiscated_dope`/
     `confiscate_extra_unit` — un giocatore ha sempre un solo boost
     attivo, quindi non serve gestire l'interazione fra loro); il
     generatore di opzioni offre un'opzione "confiscate" per slot libero
     invece della singola opzione consueta.

   **Bug trovato dal bot sweep dopo la Wave 2k (seed 1093) e corretto
   nello stesso giro:** la ricompensa "dope" di 021/023 (Wave 2i)
   incrementava `winner.base_inventory.dope_counts` con un assegnamento
   diretto invece di passare per `jail.recover_dope` — l'unica altra
   Merce rubata di questa sessione (062/061 non ne aggiunge, solo
   sottrae) a saltare il tetto dei 3 per tipo (§A2), violando
   `base_dope_overflow` quando il Covo del vincitore era già pieno di
   quel tipo. `rules/brawl.py::_handle_choose_brawl_loser_reward` ora usa
   `jail.recover_dope` come ogni altra aggiunta al Covo (unità in eccesso
   persa, evento `DopeLostToOverflow`) — nuovo test di regressione
   dedicato in `tests/unit/test_brawl.py`.

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
