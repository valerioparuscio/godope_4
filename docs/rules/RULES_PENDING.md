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
   `rules_version`) — APERTO, NON UNA REGOLA:** scoperto durante gli sweep
   di `tools/run_full_test_game.py` per le Card Boost (2026-08-27/28):
   la stessa partita (stesso `seed`, stessa sequenza di comandi bot) può
   produrre risultati diversi fra due invocazioni separate del processo
   Python, confermato sia sul codice delle Card Boost sia su `main` prima
   di quel lavoro (quindi preesistente, non causato dalle Card Boost).
   Sospetto: un punto del motore itera un `set`/`dict` la cui iterazione
   dipende dall'hash di stringa, sensibile a `PYTHONHASHSEED` (che varia
   per processo salvo fissato esplicitamente) — non ancora individuato il
   punto esatto. Viola CLAUDE.md §3.2 ("a parità di seed... il risultato
   deve essere identico"). Da investigare separatamente: cercare
   iterazioni su `set[...]`/`dict` con chiavi di dominio dove l'ordine
   arriva a influenzare una scelta (es. mescolare o scegliere il "primo"
   elemento).

25. **Un Poker in sospeso può restare senza carte da rivelare — APERTO,
   NON UNA REGOLA:** scoperto dallo stesso giro di sweep (2026-08-27,
   seed 288, riprodotto solo tramite il nondeterminismo del punto 24, non
   in modo affidabile sullo stesso seed). `rules/poker.py::
   _handle_place_poker_bet` riserva già, *al momento della puntata*, un
   numero di carte non-Preti nella mano sufficiente per le rivelazioni
   future (`revealable_card_count`) — ma nulla impedisce a un evento
   successivo, prima che quella rivelazione arrivi (`hand_discard` di
   fine round, Marketing, una Card Boost giocata, §21 di questo file), di
   scartare proprio quelle carte riservate. Se succede,
   `legal_actions.py::_play_poker_card_decision` genera una decisione
   con `min_selections=1` ma 0 opzioni disponibili (mai emesso prima
   d'ora — bug preesistente, reso raggiungibile dal punto 24, non causato
   dalle Card Boost: nessuna di quelle aggiunte finora tocca `hand_card_ids`
   in modo che riduca le carte disponibili, il draw aggiuntivo semmai le
   aumenta). Non è una regola da inventare (rules/poker.py::
   _handle_play_poker_card rifiuta esplicitamente 0 carte — "rivelare 0
   carte" non è un meccanismo previsto dal regolamento, es. "si ritira"
   non è mai descritto) — la correzione corretta è proteggere il budget
   riservato in tutti i generatori di opzioni che possono scartare/giocare
   carte (hand_discard, Marketing, Card Boost) finché una puntata resta
   aperta, non ancora implementato.

## Card Boost — carte non ancora implementate (Tier 2/3, "wave" successive)

26. **Effetti delle Customer Card oltre la Wave 1/2a — 55 carte, `effect:
   null` deliberato:** `data/customer_cards.json`'s `dataset_note` spiega
   già la convenzione (`effect: null` = "non ancora implementato", il
   `boost_text` resta il testo reale). Le 25 carte già implementate
   (rules/customer_cards.py, rules/skills.py, economy.py, movement.py,
   rules/brawl.py): Wave 1 — 002,003,006,008,009,010,011,014,016,018,
   019,020,046,047,050,060,067,068,072,079 (riusano `skills.py`'s
   `cost_delta`/`extra_grit`/`trade_price_delta`, o effetti bespoke già
   scritti in economy.py: `price_at_extreme`/`pre_action_restock`/
   `pre_action_clear_spot`/`extra_price_step`/`bonus_card_draw_per_unit`
   per Place). Wave 2a — 001,005 (`self_arrest_after_action`, economy.py:
   la prima pedina del pacchetto Buy/Sell finisce in prigione come Rat a
   fine pacchetto), 029,031 (`bonus_card_draw_per_unit` esteso a Move,
   movement.py), 022 (`provoker_gun_bonus`, rules/brawl.py::
   `_force_by_player` — testo sostituito dal game designer, 2026-08-28:
   il vecchio "puoi ritirare il dado 2 volte" non aveva alcun meccanismo
   di dado a cui agganciarsi, diventato "hai +2 Pistole" se il giocatore
   è `progress.triggering_player_id`, non ogni partecipante come lo
   Studenti-2 di `skills.py::extra_gun_bonus`).

   Le altre 55 (Artisti 004/007/012/013/015/017; Studenti 021/023-028/
   030/032-040 tranne 029/031; Manager 041-045/048/049/051-059; Politici
   061-066/069-071/073-078/080) restano `effect: null`, divise in due
   categorie:

   **Tier 2 — meccanica chiara, richiede un nuovo hook non ancora
   scritto (nessuna ambiguità di regola, solo lavoro non ancora fatto):**
   - 004/017 (Artisti, "acquista in un quartiere adiacente") e 012
     (Artisti, "vendi in un quartiere adiacente"): serve un nuovo tipo di
     effetto che allenta la presenza abilitante da "nel/al Quartiere" ad
     "anche in uno adiacente", sia nel generatore di opzioni sia nella
     validazione del comando — stesso principio già usato per
     `pre_action_restock`/`pre_action_clear_spot`, ma sulla presenza
     invece che su scorta/blocco.
   - 007/015 (Artisti, "acquisti/vendi fino a 3 merci con un criminale"):
     un solo pawn può comparire fino a 3 volte nello stesso pacchetto —
     richiede allentare il controllo `duplicate_pawn_in_targets` e offrire
     lo stesso pawn come candidato multiplo, solo quando questo boost è
     attivo.
   - 033 (Studenti, "muovi un criminale da un quartiere qualunque in
     prigione") e 043/045 (Manager, "un criminale puoi piazzarlo in
     prigione"): a differenza di 001/005 (arresto *dopo* l'azione), qui
     "prigione" è una **destinazione alternativa** dell'azione stessa —
     serve modellare "jail" come bersaglio di `MoveCriminal`/
     `PlaceCriminal` (oggi accettano solo `HoodId` reali, più il
     sentinel `DEN_ID` per il Den) prima di potercisi agganciare.
   - 054/059 (Manager, "BIG RAT" — piazza in prigione, immune
     all'Evasione): stessa dipendenza di 043/045 più un nuovo stato "Rat
     immune alla prossima Evasione" su `JailSlot`/`PawnState`, mai
     esistito finora.
   - 048/055 (Manager, "GO GAMBLE" — fino a 2 pedine nel Den) e 042/057
     (Manager, "NO GAMBLE" — 1 pedina nel Den + rimuovi una pedina
     nemica): il Den come bersaglio di `PlaceCriminal` (oggi il Den si
     raggiunge solo via `MoveCriminal`); 042/057 aggiungono anche la
     scelta di un bersaglio nemico da rimuovere, mai modellata per
     Place.
   - 041/049/052/056 (Manager, "REINFORCE" — piazzi 2 per Grinta, non
     peschi carte): un moltiplicatore (non un delta fisso) sul numero di
     bersagli più una soppressione del pescaggio normale — nessuno dei
     due esiste come tipo di effetto oggi.
   - 063/064 (Politici, "prendi la Merce requisita"): oggi una Merce
     confiscata (`rules/jail.py::confiscate_dope`) va nello slot di
     Jail e torna al *proprietario dell'arrestato* solo in caso di
     Evasione — questa carta la darebbe subito a chi corrompe. Serve un
     ramo dedicato in `rules/officers.py::_apply_confiscate`.
   - 065 (Politici, "TRANSFER" — se sposti, manda il poliziotto dove
     vuoi): allenta il vincolo di adiacenza dell'azione "sposta" della
     corruzione (`rules/officers.py`), stesso principio di 004/012/017
     ma sul lato Cop/Fed.
   - 076/077/080 (Politici, "BASHER" — arresta 2 invece di 1) e 078
     (Politici, "STRIKE" — requisisci 2 invece di 1): estendono il
     numero di bersagli di un singolo step di corruzione da 1 a 2 — non
     ancora parametrizzato in `rules/officers.py`.

   **Tier 3 — meccanica non definita dal regolamento, richiede una
   decisione del game designer prima di implementare (CLAUDE.md §2: non
   inventare):**
   - 032/036 (Studenti, "se vai nel Den, peschi 2 carte a scelta"):
     dipende da come funziona oggi "pesca a scelta" al Den — se quel
     meccanismo stesso è ancora un placeholder (un mazzo scelto dal
     giocatore, non una carta scelta a vista), raddoppiarlo eredita la
     stessa incertezza.
   - 034/035 (Studenti, "puoi muovere i criminali da un Gancio ad uno
     vicino"): i Link non sono mai spostabili nel regolamento attuale —
     "muovere un Link" non è un'operazione definita (verso quale altro
     Contact/Hood? un Link è legato al proprio Contact).
   - 044/051 (Manager, "INVADE" — piazzi uno in ogni quartiere dove sei
     presente): ambito non definito — "ogni Quartiere dove sei presente"
     è potenzialmente illimitato, indipendente dal valore di Grinta
     scelto quel round; non è chiaro se sia comunque limitato dalla
     Grinta o genuinamente senza tetto.
   - 053/058 (Manager, "SHORTCUT" — un criminale puoi piazzarlo su un
     Gancio"): diventare direttamente Link al piazzamento non è mai
     descritto dal regolamento — quale Contact, quale livello, e con
     quale Merce/presenza a giustificarlo restano indefiniti.
   - 061/062 (Politici, "FAKE POLICE" — paghi la mazzetta con una
     Merce): la corruzione costa denaro per definizione (§11.7); pagare
     "con una Merce" non specifica quale Merce, né un tasso di cambio
     Merce↔denaro.
   - 066 (Politici, "INSIDER" — se requisisci, scegli dove mettere la
     Merce"): "dove mettere" non è chiaro — gli slot della Jail sono
     intercambiabili (RULES_PENDING #10), quindi non c'è una scelta
     significativa da offrire finché non si capisce cosa significhi
     davvero questo testo.
   - 069/070/071 (Politici, "REASSIGN" — sposta Merce fra Punto di
     Vendita e Quartiere del cliente): non esiste alcuna operazione che
     sposti una Merce fra uno Spot e un Hood — la Merce nello Spot è
     "venduta" (sparisce nella Chip venduta), non un token spostabile.
   - 073/074/075 (Politici, "REDEEM" — invece di arrestare, fai evadere
     due criminali"): un'Evasione forzata di soli 2 Rats scelti (non i 6
     regolari) non è un meccanismo previsto da §A1/§C5 — richiede
     decidere quali 2 Rats (di chi?) e se conta come l'Evasione normale
     ai fini di REP/Link Politici.

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
