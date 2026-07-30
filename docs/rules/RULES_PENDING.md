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

1. **Spots:** i due tipi di Dope accettati da ciascun Contact, adiacenza tra
   Spots per il movimento dei Feds.
2. **Carte Clienti:** dataset completo delle 20 carte per Cliente (valori
   di boost azione per Artisti/Studenti/Manager/Politici, simboli Poker,
   Stonk, Guns; per i Preti, quale azione è associata a ciascuna delle 20
   carte). La struttura della carta è nota (`RULES_CANONICAL.md` §A9),
   manca il contenuto.
3. **Jobs e Skills:** requisiti dei 9 tipi di Job, livelli e numero di copie
   per livello, modalità di verifica del completamento, contenuto delle
   carte Skill.
4. **Retate:** condizioni complete delle 7 carte Retata — quali condizioni
   fanno "cadere" una squadra nella Retata. Le squadre sono note: primo+
   quarto giocatore vs secondo+terzo (`RULES_CANONICAL.md` §D4).
5. **Punteggio denaro:** è confermato che la posizione sul tracciato denaro
   (1ª–4ª) assegna punti propri (`RULES_CANONICAL.md` §D6), ma non i valori
   esatti per ciascuna posizione.
6. **Chips Cops/Poker iniziali nel Covo:** presumibilmente 0 a inizio
   partita (`RULES_CANONICAL.md` §E3), da confermare esplicitamente.
7. **Riutilizzo dei segnalini Grinta:** un segnalino Grinta usato in un
   round torna disponibile negli altri round dello stesso turno, o si usa
   ciascuno una sola volta per turno (uno per round)? (`RULES_CANONICAL.md`
   §B2)

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
