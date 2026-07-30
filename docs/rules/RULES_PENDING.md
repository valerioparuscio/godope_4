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

1. **Grinta:** numero di segnalini Grinta per giocatore, elenco completo
   delle azioni disponibili (oltre a Piazzare/Spostare/Comprare/Vendere/
   Corrompere/Comprare Cops-Feds) e associazione azione–Contact per i
   potenziamenti. *(Nota: "Grinta" è usato nel regolamento anche per i 3
   slot di livello dei Link — vedi `RULES_CANONICAL.md` §A5 — sono due usi
   distinti dello stesso termine, da non confondere in fase di modellazione.)*
2. **Prezzi:** quale valore tra 3, 1, 4, 6 è associato a quale tipo di Dope
   (Camaleonte / Rana / Polpo / Gufo); valore minimo e massimo del prezzo
   (`RULES_CANONICAL.md` §A3).
3. **Mappa:** nomi dei 10 Hoods (5 scoperti + 5 coperti, vedi
   `RULES_CANONICAL.md` §E4), Contact/colore di ciascuno, adiacenze,
   distribuzione dei tipi di Dope nei mercati scoperti, e contenuto delle
   tile rotonde dei Quartieri coperti (quante Dope 1–3, presenza di un
   Cops). Include la conferma che Preti e Politici abbiano un proprio
   Quartiere scoperto tra i 5 iniziali, e il numero totale di Contact nel
   gioco (rilevante anche per la dimensione del mazzetto carte iniziali,
   `RULES_CANONICAL.md` §E2).
4. **Contacts e Spots:** elenco completo dei Contact, i due tipi di Dope
   accettati da ciascuno, adiacenza tra Spots per il movimento dei Feds.
5. **Carte Clienti:** dataset completo delle 20 carte per Cliente (valori
   di boost azione, simboli Poker, Stonk, Guns, effetto Gamble e quali
   Clienti oltre ai Preti hanno carte Gamble). La struttura della carta è
   nota (`RULES_CANONICAL.md` §A9), manca il contenuto.
6. **Jobs e Skills:** requisiti dei 9 tipi di Job, livelli e numero di copie
   per livello, modalità di verifica del completamento, contenuto delle
   carte Skill.
7. **Retate:** condizioni complete delle 7 carte Retata — quali condizioni
   fanno "cadere" una squadra nella Retata. Le squadre sono note: primo+
   quarto giocatore vs secondo+terzo (`RULES_CANONICAL.md` §D4).
8. **Punteggio denaro:** è confermato che la posizione sul tracciato denaro
   (1ª–4ª) assegna punti propri (`RULES_CANONICAL.md` §D6), ma non i valori
   esatti per ciascuna posizione.
9. **Chips Cops/Poker iniziali nel Covo:** presumibilmente 0 a inizio
   partita (`RULES_CANONICAL.md` §E3), da confermare esplicitamente.

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
