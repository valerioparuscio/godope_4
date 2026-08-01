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
2. **Adiacenza Q3↔Q6 (PROVVISORIO):** `tools/validate_data.py` ha
   rilevato che Q6 elenca Q3 come adiacente (`RULES_CANONICAL.md` §F2)
   ma Q3 non elencava Q6 — asimmetria non notata durante la revisione
   della mappa del 2026-07-31. `data/board.json` include provvisoriamente
   Q3→Q6 per simmetria (coerente con come sono state risolte le altre due
   asimmetrie, Q2↔Q6 e Q5↔Q9), ma serve conferma esplicita del game
   designer.

## Semplificazioni tecniche in attesa di conferma

3. **Rimozione del Fed da uno Spot "senza Merci e senza Ganci" (ANCORA
   NON IMPLEMENTATA dopo Milestone 3):** i Link ora esistono, quindi la
   condizione non è più strutturalmente auto-annullante come in
   Milestone 2 — ma "senza Ganci" può cambiare da eventi sparsi in più
   moduli (creazione di un Link da vendita a pacchetto, arresto di un
   Link, scorrimento/espulsione in cascata, ritorno al Covo dopo
   un'azione extra), non solo dalle azioni di `rules/economy.py` come per
   il Cop su un Hood. Implementarla ora rischierebbe di ricontrollare la
   condizione in modo incompleto/incoerente sui numerosi punti che
   toccano i Link; rimandata a quando la Milestone 4 (Rissa) dovrà
   comunque centralizzare il calcolo della presenza dei Link per
   Quartiere/Contact.
4. **Quale pedina evolve in Link su una vendita a pacchetto con più
   venditori sullo stesso Punto di Vendita:** `RULES_CANONICAL.md` §C4
   dice che si prende "un solo Link" ma non specifica quale pedina fra le
   2-3 che hanno venduto in pacchetto. `rules/economy.py::
   _handle_sell_dope` sceglie deterministicamente la prima pedina
   nell'ordine del comando; le altre restano Criminali normali. Non
   influisce sulla legalità delle azioni, solo su quale pedina specifica
   diventa Link.
5. **Evoluzione a Link su singola vendita resa automatica (non più
   opzionale):** §A5 dice che un Criminale che ha venduto Merci "può
   evolversi" in Link (opzionale), mentre §C4 per il pacchetto dice "si
   prende" (sembra automatico). Milestone 3 rende **entrambi** i casi
   automatici per evitare un'ulteriore decisione interattiva per ogni
   singola vendita — una vendita di 1 Merce evolve sempre la pedina in
   Link di livello 1. Va rivisto se il game designer conferma che la
   singola vendita deve restare una scelta del giocatore.
6. **Bersaglio dell'arresto Feds — "il Link di livello minore" fra tutti
   i giocatori:** §C5 non specifica se il Feds corrotto da un giocatore
   possa arrestare il Link di livello minore di un *altro* giocatore.
   `rules/officers.py::_lowest_level_link_at_contact` cerca fra **tutti**
   i giocatori (non solo chi corrompe), coerente con la logica
   competitiva delle altre azioni di corruzione (requisire Merci, per
   esempio, non è limitato a Merci del corruttore).
7. **Sentinella "skip" per il 2° step di Corruzione senza bersagli
   legali (PROVVISORIO, edge case):** §C5 richiede sempre "2 diverse
   azioni", ma la 2ª azione dipende dall'effetto della 1ª (es. un Cop che
   si sposta in un Quartiere ormai senza Criminali e senza Merci non ha
   più "arresta"/"requisisci" legali). `rules/officers.py` accetta un
   `action="skip"` (offerto da legal_actions.py solo quando nessuna
   azione qualifica) per chiudere la corruzione con 1 sola azione invece
   di bloccarsi in stallo. Verificato con simulazioni massive che questo
   caso è raro ma reale.
8. **Un pacchetto di Corruzione può invalidare un target successivo nella
   coda (PROVVISORIO, edge case):** se la 1ª azione di una corruzione
   (es. un Feds che arresta il Link di livello minore) tocca per
   coincidenza la pedina o l'officer previsto per la 2ª corruzione dello
   stesso pacchetto, `rules/officers.py::_finish_corruption` scarta
   silenziosamente il resto della coda invece di rifiutare l'intero
   comando (che annullerebbe anche l'azione già legittimamente applicata
   sulla 1ª corruzione). Scoperto tramite simulazione bot-only massiva,
   non tramite i test unitari.
9. **"Sbirciare una Retata futura" scartando un Cop/Feds comprato (NON
   IMPLEMENTATO):** §C6 lo cita come abilità opzionale dell'acquisto di
   un officer; richiede un modello di informazione nascosta per giocatore
   sulle Retate che non esiste prima della Milestone 5 (Retate). `BuyOfficer`
   in Milestone 3 copre solo l'acquisto, non questa abilità accessoria.
10. **Associazione Rat↔Merce confiscata nello stesso slot della Jail:**
   CLAUDE.md §7.5 modella `rat_pawn_id` e `confiscated_dope_type` come
   due campi indipendenti dello stesso slot, ciascuno riempito dalla
   "prima posizione disponibile" per il proprio campo. `rules/jail.py`
   segue questo modello: un arresto e una confisca nello stesso momento
   tendono a occupare lo stesso slot (da cui l'"associazione" descritta
   in CLAUDE.md), ma non è una regola di accoppiamento forzato — sono
   due ricerche indipendenti che a volte convergono sullo stesso slot e a
   volte no.
11. **Furto di 1 carta come ricompensa — carta scelta o casuale
   (PROVVISORIO):** §D1 non specifica se il vincitore, scegliendo di
   rubare "1 carta" invece di 2 dollari, veda la mano dello sconfitto per
   scegliere quale, o la rubi alla cieca. `rules/brawl.py` la sceglie
   **casualmente** (sotto-seed deterministico della partita) perché le
   mani sono informazione nascosta per regola generale (CLAUDE.md §12) e
   nessuna meccanica la rende visibile in questo momento specifico. Va
   confermato dal game designer.
12. **Sforamento delle 5 carte per un "bystander" di Rissa che non ha più
   un turno successivo (PROVVISORIO):** il limite di 5 carte si applica
   solo a fine del turno del singolo giocatore (decisione 2026-08-01,
   risolve CLAUDE.md punto 22.29). Un partecipante a una Rissa diverso
   da chi riprende il pacchetto può però ricevere una carta (ricompensa
   o ricollocazione) *dopo* che il proprio controllo di fine round è già
   passato per quel turno — normalmente si autocorregge al turno
   successivo dello stesso giocatore, ma se la partita finisce prima non
   c'è più un turno successivo in cui farlo. Poiché il punteggio di fine
   partita (Milestone 5, non ancora implementato) non fa riferimento al
   contenuto della mano, `domain/invariants.py::_check_hand_size` non
   controlla il limite quando la fase è `FINISHED`. Va rivisto quando la
   Milestone 5 definirà lo scoring finale, per verificare che non serva
   davvero uno scarto anche a fine partita.
Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
