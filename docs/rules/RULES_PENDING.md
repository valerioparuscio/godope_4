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

La lettura del regolamento completo (2026-07-30) ha risolto gran parte delle
domande originarie: dettagli vedi `RULE_CHANGELOG.md`, voce 2026-07-30.
L'elenco sotto contiene solo ciò che resta genuinamente aperto.

## Bloccanti o ad alta priorità

1. **Durata:** l'introduzione parla di 4 giorni, la sezione B) Fasi parla di
   3 turni — la contraddizione è presente nel testo del regolamento stesso,
   non è un errore di trascrizione. Quanti turni completi ha una partita?
2. **Setup iniziale:** denaro, numero di pedine, carte iniziali, Chips,
   merci nei Hoods, Cops/Feds, primo giocatore e Hoods iniziali. Non
   presente nel documento ricevuto.
3. **Grinta:** numero di segnalini, posizioni iniziali, elenco completo
   delle azioni disponibili e associazione azioni–Contact. Sappiamo solo
   che un segnalino Grinta si sposta su un'azione per ogni action round
   (`RULES_CANONICAL.md` §B2).
4. **Prezzi:** quale valore tra 3, 1, 4, 6 è associato a quale tipo di Dope
   (Camaleonte / Rana / Polpo / Gufo); valore minimo e massimo del prezzo
   (`RULES_CANONICAL.md` §A3).
5. **Mappa:** nomi dei 10 Hoods, Contact di ciascuno, adiacenze e
   distribuzione iniziale delle Dope.
6. **Contacts e Spots:** elenco completo dei Contact, i due tipi di Dope
   accettati da ciascuno, adiacenza tra Spots per il movimento dei Feds.
7. **Carte Clienti:** dataset completo delle 20 carte per Cliente (valori di
   boost, simboli Poker, Stonk, Guns, effetto Gamble). La struttura della
   carta è nota (`RULES_CANONICAL.md` §A9), manca il contenuto.
8. **Poker:** come si costruisce la combinazione di 5 simboli/colori da
   valutare, dato che ogni giocatore rivela una sola carta con 2 simboli
   Poker (`RULES_CANONICAL.md` §D2); comportamento quando un giocatore che
   ha puntato non ha, o non rivela, una carta valida.
9. **Jobs:** requisiti dei 9 tipi, livelli, numero di copie, modalità di
   verifica del completamento, contenuto delle Skills.
10. **Retate:** condizioni complete delle 7 carte Retata — quali condizioni
    fanno "cadere" una squadra. Le squadre sono note: primo+quarto
    giocatore vs secondo+terzo (`RULES_CANONICAL.md` §D4).
11. **Punteggio denaro:** il riposizionamento dei birilli sul tracciato
    punti (`RULES_CANONICAL.md` §D6) assegna punti in sé, oppure prepara
    solo il tracciato che accumulerà gli altri punteggi (REP, maggioranze,
    chips, skill)? L'elenco dei punteggi non cita esplicitamente punti per
    posizione denaro.

## Ambiguità di risoluzione

12. Il sesto Rat che causa l'Evasione evolve in Link dai Politici
    (`RULES_CANONICAL.md` §A5) mentre il regolamento dice anche che "i 6
    Rats tornano nei Covi" (§A1 Jail). Evolve al posto di tornare al Covo, o
    torna al Covo e viene promosso subito dopo?
13. I Cops/Feds "rimandati al Commissariato" (`RULES_CANONICAL.md` §A6)
    occupano gli stessi 6 slot dei Rats/Merci confiscate, o una riserva
    separata? Il Commissariato è descritto altrove come contenitore solo di
    Rats e Merci requisite.
14. Nell'acquisto di un Cops/Feds dal Covo di un altro giocatore
    (`RULES_CANONICAL.md` §C6), il proprietario può opporsi?
15. Nella corruzione, le due azioni diverse possono avere lo stesso
    bersaglio? Qual è l'ordine di risoluzione se un trigger intermedio (es.
    un arresto che libera lo slot) influenza la seconda azione?
16. Se più Link hanno lo stesso livello minimo, chi sceglie quale viene
    arrestato dal Fed corrotto?
17. Le Guns assegnate a un partecipante nella Rissa possono portarne la
    forza sotto zero?
18. Cosa succede a una Dope acquistata, o recuperata dall'Evasione, se il
    Covo di destinazione ha già 3 pezzi di quel tipo?
19. Il controllo per far rientrare al Commissariato un Cops/Feds che ha
    perso le condizioni per restare avviene immediatamente dopo ogni
    evento, o a fine azione?
20. Capienza del Den (numero massimo di Gambler ospitabili) e conseguenze
    quando è pieno — il regolamento menziona "se c'è posto" ma non il
    valore.
21. Come si sceglie esattamente la carta pescata "a scelta" nel Den
    (Contact/mazzo scelto dal giocatore, carta visibile, pesca casuale)?
22. `RULES_CANONICAL.md` §A7 elenca le categorie di Chip nel Covo con
    limite 3 (Cops, Poker, Merci dei 4 tipi) ma non cita i Feds: hanno
    anch'essi un limite di 3, condividono il conteggio con i Cops, o non
    risiedono affatto nel Covo?

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es.
errore tipizzato o `# PROVISIONAL` con test dedicato) e non trasformare una
supposizione in regola definitiva.
