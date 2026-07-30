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

1. **Adiacenze della mappa (PROVVISORIO):** la tabella in
   `RULES_CANONICAL.md` §F2 ha due asimmetrie da chiarire — Q2↔Q6 (solo Q2
   la elenca) e Q5↔Q9 (solo Q5 la elenca, dedotta da un probabile refuso
   "4 con 3 4 7 9 10" → "5 con..."). Confermare se le adiacenze mancanti
   vanno aggiunte o se gli elenchi originali erano quelli corretti (e quindi
   l'adiacenza è a senso unico, il che sarebbe insolito per una mappa di
   strade).
2. **Tile rotonde dei Quartieri coperti (Q2, Q4, Q6, Q8, Q10):** quante
   Dope (1–3) e presenza/assenza di un Cops per ciascuna tile — dataset del
   mazzo di tile, non solo il range ammesso.
3. **Spots:** i due tipi di Dope accettati da ciascun Contact, adiacenza tra
   Spots per il movimento dei Feds.
4. **Carte Clienti:** dataset completo delle 20 carte per Cliente (valori
   di boost azione per Artisti/Studenti/Manager/Politici, simboli Poker,
   Stonk, Guns; per i Preti, quale azione è associata a ciascuna delle 20
   carte). La struttura della carta è nota (`RULES_CANONICAL.md` §A9),
   manca il contenuto.
5. **Jobs e Skills:** requisiti dei 9 tipi di Job, livelli e numero di copie
   per livello, modalità di verifica del completamento, contenuto delle
   carte Skill.
6. **Retate:** condizioni complete delle 7 carte Retata — quali condizioni
   fanno "cadere" una squadra nella Retata. Le squadre sono note: primo+
   quarto giocatore vs secondo+terzo (`RULES_CANONICAL.md` §D4).
7. **Punteggio denaro:** è confermato che la posizione sul tracciato denaro
   (1ª–4ª) assegna punti propri (`RULES_CANONICAL.md` §D6), ma non i valori
   esatti per ciascuna posizione.
8. **Chips Cops/Poker iniziali nel Covo:** presumibilmente 0 a inizio
   partita (`RULES_CANONICAL.md` §E3), da confermare esplicitamente.
9. **Riutilizzo dei segnalini Grinta:** un segnalino Grinta usato in un
   round torna disponibile negli altri round dello stesso turno, o si usa
   ciascuno una sola volta per turno (uno per round)? (`RULES_CANONICAL.md`
   §B2)

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
