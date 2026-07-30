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

1. **Setup iniziale:** denaro di partenza, numero di pedine per giocatore,
   carte iniziali in mano, Chips iniziali, merci nei Hoods a inizio
   partita, Cops/Feds iniziali sulla mappa, primo giocatore del turno 1,
   eventuali Hoods di partenza per i Criminali.
2. **Grinta:** numero di segnalini Grinta per giocatore, elenco completo
   delle azioni disponibili (oltre a Piazzare/Spostare/Comprare/Vendere/
   Corrompere/Comprare Cops-Feds) e associazione azione–Contact per i
   potenziamenti. *(Nota: "Grinta" è usato nel regolamento anche per i 3
   slot di livello dei Link — vedi `RULES_CANONICAL.md` §A5 — sono due usi
   distinti dello stesso termine, da non confondere in fase di modellazione.)*
3. **Prezzi:** quale valore tra 3, 1, 4, 6 è associato a quale tipo di Dope
   (Camaleonte / Rana / Polpo / Gufo); valore minimo e massimo del prezzo
   (`RULES_CANONICAL.md` §A3).
4. **Mappa:** nomi dei 10 Hoods, Contact di ciascuno, adiacenze e
   distribuzione iniziale delle Dope.
5. **Contacts e Spots:** elenco completo dei Contact (inclusi Preti e
   Politici, già citati per i Links), i due tipi di Dope accettati da
   ciascuno, adiacenza tra Spots per il movimento dei Feds.
6. **Carte Clienti:** dataset completo delle 20 carte per Cliente (valori
   di boost azione, simboli Poker, Stonk, Guns, effetto Gamble e quali
   Clienti oltre ai Preti hanno carte Gamble). La struttura della carta è
   nota (`RULES_CANONICAL.md` §A9), manca il contenuto.
7. **Jobs e Skills:** requisiti dei 9 tipi di Job, livelli e numero di copie
   per livello, modalità di verifica del completamento, contenuto delle
   carte Skill.
8. **Retate:** condizioni complete delle 7 carte Retata — quali condizioni
   fanno "cadere" una squadra nella Retata. Le squadre sono note: primo+
   quarto giocatore vs secondo+terzo (`RULES_CANONICAL.md` §D4).
9. **Punteggio denaro:** è confermato che la posizione sul tracciato denaro
   (1ª–4ª) assegna punti propri (`RULES_CANONICAL.md` §D6), ma non i valori
   esatti per ciascuna posizione.

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
