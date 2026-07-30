# Regole da chiarire

Fonte: `CLAUDE.md`, sezione 22. Quando una voce viene risolta dal game designer,
spostarla in `RULES_CANONICAL.md` con riferimento alla decisione e rimuoverla da qui.

Formato per ogni voce risolta in futuro:

```text
## <numero>. <titolo breve>
Stato: RISOLTO | PROVISIONAL
Decisione: <testo della decisione approvata>
Data: <YYYY-MM-DD>
Riferimento: <link o descrizione della fonte>
```

## Bloccanti o ad alta priorità

1. **Durata:** l'introduzione parla di 4 giorni, mentre la sezione delle fasi parla di 3 turni. Quanti turni completi ha una partita?
2. **Setup iniziale:** denaro, numero di pedine, carte iniziali, Chips, merci nei Hoods, Cops/Feds, primo giocatore e Hoods iniziali.
3. **Grinta:** numero di segnalini, posizioni iniziali, elenco delle azioni, associazione azioni–Contacts e significato esatto del valore di Grinta.
4. **Prezzi:** associazione dei prezzi iniziali `3, 1, 4, 6` ai tipi di Dope; minimo e massimo; comportamento al limite; ordine preciso del crollo del mercato.
5. **Mappa:** nomi dei 10 Hoods, Contact, adiacenze e distribuzione iniziale delle Dope.
6. **Contacts e Spots:** elenco completo, due tipi di Dope accettati da ciascun Contact e adiacenza tra Spots per il movimento dei Feds.
7. **Carte Clienti:** dataset completo, boost, simboli Poker, Stonks, Guns ed effetto Gamble.
8. **Poker:** come si costruisce esattamente una combinazione di 5 simboli se ciascun giocatore rivela una carta con due simboli; significato di "5 colori uguali/diversi"; gestione dei giocatori senza carta valida.
9. **Jobs:** requisiti dei 9 tipi, livelli, copie, modalità di verifica e contenuto delle Skills.
10. **Retate:** condizioni complete delle 7 carte, valutazione delle squadre e identificazione dei singoli giocatori che macchiano REP.
11. **Punteggio denaro:** conversione esatta dell'ordine sul tracciato denaro nelle posizioni/punti 1–4.

## Ambiguità di risoluzione

12. Quando il sesto Rat provoca l'Evasione, in quale ordine diventa Link dai Politici e torna al Covo?
13. Un Link arrestato perde definitivamente il livello e torna come normale pedina dopo l'Evasione?
14. I Cops/Feds "rimandati al Commissariato" entrano in una riserva separata o occupano i 6 slot della Jail?
15. Quando si comprano Cops/Feds dal Covo di un altro giocatore, il proprietario può opporsi? Quale presenza nella località è richiesta?
16. In una corruzione le due azioni devono essere di tipo diverso. Possono avere lo stesso bersaglio? Qual è l'ordine dei trigger intermedi?
17. Se un Fed deve arrestare il Link di livello minore e più Link sono pari, chi sceglie?
18. Una Rissa considera solo il quinto `Criminal`, oppure anche altri ruoli fisicamente presenti?
19. I Links contano in ogni Hood del Contact anche se ciò produce presenza in più Risse simultaneamente?
20. La carta Rissa può assegnare tutte le Guns a un unico partecipante o distribuirle? Le Guns negative possono portare la forza sotto zero?
21. Nella Rissa il vincitore sceglie una sola tipologia di ricompensa globale o una ricompensa per ciascuno sconfitto?
22. L'invio del Criminal sconfitto in un Hood inesplorato è scelto dal vincitore, dallo sconfitto o automaticamente?
23. Ordine completo dei tie-break della Rissa e significato di "primo giocatore, o seguenti".
24. In acquisto/vendita a pacchetto, ciascuna merce usa lo stesso prezzo iniziale del pacchetto oppure un prezzo progressivo con sola modifica del track rinviata?
25. Il Marketing può modificare anche altre Dope non direttamente comprate/vendute nel pacchetto? Il testo sembra limitarlo alle merci trattate.
26. Se il Covo è pieno, una merce acquistata o recuperata dall'Evasione può essere persa, rifiutata o sostituita?
27. Quando uno Spot si svuota per effetto di un Fed, entra comunque un nuovo Fed come nel caso riempimento/svuotamento descritto nei componenti?
28. Quando Cops/Feds non hanno più le condizioni per restare, il controllo di rientro avviene immediatamente dopo ogni evento o a fine azione?
29. Il limite di 5 carte viene applicato dopo ogni action round del giocatore, dopo l'intera fase Azione o in entrambi i momenti?
30. "Una sola azione extra per turno" significa per giocatore per turno completo, non per action round?
31. Ordine di scelta del primo giocatore quando nessuno possiede Link presso i Preti.
32. Regole per la capienza del Den e conseguenze quando è pieno.
33. Quantità e significato delle Chips Poker nel Covo, oltre al limite di 3.
34. Modalità di scelta della carta pescata "a scelta" nel Den: Contact/deck, carta visibile o pesca casuale dal mazzo scelto.

Finché un punto resta aperto, il codice deve segnalarlo chiaramente (es. errore tipizzato o
`# PROVISIONAL` con test dedicato) e non trasformare una supposizione in regola definitiva.
