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

## Semplificazioni tecniche della Milestone 2 (in attesa di conferma)

3. **Rimozione del Fed da uno Spot "senza Merci e senza Ganci" (NON
   IMPLEMENTATA in Milestone 2):** un Fed entra in uno Spot esattamente
   quando lo Spot si svuota (§A6), quindi la condizione di rimozione
   "senza Merci" sarebbe già vera nell'istante dello spawn, e si
   auto-annullerebbe subito senza un secondo trigger reale finché non
   esistono i Link (Milestone 3, "senza Ganci"). La rimozione del Cop da
   un Hood *è* implementata (quella condizione non è auto-annullante,
   perché un restock lascia sempre 1-3 Merci). Va rivista quando arrivano
   i Link.
4. **Link su vendita a pacchetto (NON IMPLEMENTATO in Milestone 2,
   ATTESO):** `RULES_CANONICAL.md` §C4 ("Vendita a pacchetto") prevede
   che vendendo 2/3 Merci in pacchetto dallo stesso Quartiere/Punto di
   Vendita si prenda un Link di livello pari al numero di merci vendute
   — confermato dal game designer (2026-07-31). `rules/economy.py::
   _handle_sell_dope` non crea ancora alcun Link: i Link (creazione,
   scorrimento tra livelli, spesa per azione extra) sono esplicitamente
   Milestone 3 (CLAUDE.md sezione 21). Non è un'ambiguità di regola — è
   un pezzo di funzionalità volutamente rimandato, da implementare quando
   arriva la Milestone 3.
5. **Rissa non ancora risolta quando lo Spostamento raggiunge il conteggio
   che la scatena (ATTESO, Milestone 4):** `RULES_CANONICAL.md` §D1
   conferma (2026-07-31) che il Piazzamento non può mai portare un
   Quartiere al conteggio che scatena la Rissa (è illegale), ma lo
   Spostamento sì — è esattamente il suo trigger. Finché la Rissa non è
   implementata, `MoveCriminal` lascia il Quartiere a quel conteggio senza
   alcuna risoluzione automatica (nessun Criminale sconfitto viene
   spostato via). Non è un bug: è lo stub Milestone 1-3 già descritto in
   `rules/turn_flow.py` ("Real handlers replace the stubs as each
   milestone lands"), da sostituire quando arriva la Rissa.

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
