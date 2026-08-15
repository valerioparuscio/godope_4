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
   confermato. `rules/jobs.py::_handle_choose_job_reward` resta
   invariata (nessun effetto, silenziosamente).
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
   (2026-08-02):** il game designer ha chiarito che "prima o dopo lo
   svolgimento dell'azione" si riferisce all'**intera azione** (l'intero
   pacchetto Buy/Sell, incluso il suo step di prezzo automatico), non al
   solo step automatico come implementato inizialmente. Marketing
   "prima" è ora offerto subito dopo `ChooseActionType` (prima della
   selezione bersagli, qualunque tipo di Merce — il pacchetto non esiste
   ancora), analogo al lancio Poker; Marketing "dopo" resta offerto in
   coda a `BuyDope`/`SellDope`, ristretto alle Merci effettivamente
   trattate nel pacchetto. Un giocatore normale ottiene l'uno o l'altro,
   mai entrambi nella stessa azione — Manager-3 (punto 18) è l'unica
   eccezione, che replica "dopo" le stesse allocazioni fatte "prima".
   `PlayMarketingCard.allocations` non porta più un flag `apply_before`
   per singolo Stonk (il timing è ora determinato da *quale* dei due
   punti di offerta è stato usato, non da una scelta per-Stonk).

   **Quale carta — RISOLTO (2026-08-15):** il game designer ha confermato
   che con più di una carta idonea in mano è una scelta reale del
   giocatore, non un auto-pick della carta con più Stonk. Aggiunto un
   sotto-passo dedicato `ChooseMarketingCard`/decision_type
   `choose_marketing_card` (`application/legal_actions.py::
   _choose_marketing_card_decision`), offerto solo con 2+ carte idonee —
   con esattamente una carta idonea non c'è nulla da scegliere, si passa
   dritti all'allocazione degli Stonk come prima. La scelta è
   declinabile (equivale a rifiutare Marketing del tutto per quell'offerta).

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
