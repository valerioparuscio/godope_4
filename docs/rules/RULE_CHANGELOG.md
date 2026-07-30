# Changelog delle regole

Ogni voce registra una decisione di regolamento approvata dal game designer,
con data e riferimento. Formato:

```text
## YYYY-MM-DD — <titolo>
Decisione: <testo>
Riferimento: <RULES_PENDING punto N, o altra fonte>
Impatto: <moduli/file coinvolti>
```

## 2026-07-30 — Acquisizione del regolamento (how_to_play_v056)
Decisione: il testo completo del regolamento (sezioni A–D, componenti/fasi/
azioni/altre regole) è stato fornito dal game designer in chat e trascritto
integralmente in `RULES_CANONICAL.md` senza reinterpretazione.
Riferimento: risolve o riduce sostanzialmente i punti 3, 4, 7, 8, 10 (in
parte) e 12, 13, 18, 19, 20, 21, 22, 23, 24, 25, 27, 29, 30, 33 (integrali)
della precedente numerazione di `RULES_PENDING.md`. La nuova numerazione del
file riflette solo ciò che resta aperto.
Impatto: creato `docs/rules/RULES_CANONICAL.md`; riscritto e ridotto
`docs/rules/RULES_PENDING.md` da 34 a 22 punti aperti; nessun impatto sul
codice (non ancora scritto in questa fase).

## 2026-07-30 — Decisioni di design su ambiguità di interazione tra regole
Decisione: il game designer ha risolto, tramite Q&A diretta, tutte le 22
ambiguità di interazione tra regole rimaste dopo la trascrizione del
regolamento. Nel dettaglio:

1. Durata partita: 3 turni completi; i "4 giorni" dell'introduzione sono
   narrativi.
2. Punteggio tracciato denaro: la posizione (1ª–4ª) assegna punti propri
   (valori esatti ancora da fornire, vedi `RULES_PENDING.md`).
3. Evasione: il sesto Rat evolve direttamente in Link dai Politici, senza
   passare dal Covo; solo 5 Rats tornano ai Covi.
4. Cops/Feds "rimandati al Commissariato": vanno in una riserva separata
   dai 6 slot di Rats/Merci, non li condividono.
5. Acquisto Cops/Feds dal Covo altrui: il proprietario non può rifiutare la
   vendita.
6. Corruzione: le 2 azioni possono avere lo stesso bersaglio e si risolvono
   in sequenza (la seconda vede l'effetto della prima).
7. Arresto del Link di livello minore da parte del Fed: non può esserci
   parità, perché ogni Contact ha un solo Link per livello (1/2/3) — nuova
   informazione strutturale sui Links, ora in `RULES_CANONICAL.md` §A5.
8. Feds nel Covo: condividono il limite di 3 con i Cops (non hanno una
   categoria propria).
9. Rissa — forza dei partecipanti: può scendere sotto zero (somma
   algebrica, nessun troncamento).
10. Covo pieno: una Dope acquistata o recuperata dall'Evasione oltre il
    limite di 3 per tipo viene persa, l'azione avviene comunque.
11. Rientro di Cops/Feds in riserva: il controllo avviene subito dopo ogni
    evento rilevante, non solo a fine azione.
12. Pesca "a scelta" nel Den: il giocatore sceglie il mazzo Cliente da cui
    pescare, poi la carta è casuale.
13. Capienza del Den: 6 Gambler al massimo.
14. Costruzione della mano Poker da 5 simboli: esiste un banco comune di 3
    simboli creato solo con carte Gamble dei Preti; ogni giocatore che ha
    puntato aggiunge i propri 2 simboli al banco.

Riferimento: sostituisce integralmente i punti 12–22 (ambiguità di
risoluzione) e 1, 8, 11 (parte) della vecchia numerazione di
`RULES_PENDING.md`.
Impatto: `docs/rules/RULES_CANONICAL.md` annotato inline con le decisioni
sopra; `docs/rules/RULES_PENDING.md` ridotto a 9 voci, tutte relative a
dati di contenuto (setup, mappa, carte, Jobs, Retate) che nessuna decisione
di design può sostituire.

## 2026-07-30 — Setup iniziale della partita
Decisione: il game designer ha fornito i dati completi di setup: 15 dollari
e 10 pedine Criminale a testa; 3 carte iniziali pescate da un mazzetto di 3
carte per Contact; 2 Dope iniziali per giocatore secondo tabella per
seggio; 5 Hoods scoperti (uno per Cliente, 3 Dope ciascuno) e 5 Hoods
coperti che si rivelano tramite tile rotonda quando un Criminale sconfitto
in Rissa vi viene mandato; nessun Cops/Feds iniziale; primo giocatore del
turno 1 casuale; 3 Criminali piazzati in setup nei Quartieri corrispondenti
alle 3 carte iniziali pescate.
Riferimento: risolve il punto "Setup iniziale" della vecchia numerazione di
`RULES_PENDING.md`; introduce anche il meccanismo delle tile rotonde per i
Quartieri coperti, che chiarisce parzialmente il "Quartiere inesplorato" di
`RULES_CANONICAL.md` §D1.
Impatto: aggiunta sezione `## E) Setup` a `docs/rules/RULES_CANONICAL.md`;
`docs/rules/RULES_PENDING.md` ridotto da 9 a 9 voci (rinumerate), con il
dettaglio mappa/Contacts arricchito dai nuovi elementi da confermare
(numero totale di Contact, Hood di Preti/Politici, contenuto tile rotonde).

## 2026-07-30 — Meccanica della Grinta e mappa Contact↔Azione
Decisione: ogni giocatore ha 3 segnalini Grinta di valore fisso 1/2/3 (non
una pedina su un tracciato); in ogni round si sceglie un segnalino e lo si
assegna a una delle 6 azioni, il valore indica quante pedine eseguono
l'azione contemporaneamente (una ciascuna, nella propria posizione). Le
azioni restano esattamente le 6 già note (§C1–C6). Mappa Contact↔azione
confermata: Artisti = comprare/vendere, Studenti = spostare, Manager =
piazzare, Politici = corrompere/comprare Cops-Feds; i Preti sono un caso
speciale (azione extra da Link di qualunque tipo tranne comprare Cops/Feds;
ogni carta Preti associata a una singola azione specifica; giocare una
carta Preti lancia un Poker invece di potenziare un'azione). La Grinta
dell'azione extra da Link corrisponde al livello del Link.
Riferimento: risolve il punto "Grinta" della vecchia numerazione di
`RULES_PENDING.md`; conferma che i 5 Contact dei Quartieri scoperti sono
Artisti, Studenti, Manager, Politici, Preti.
Impatto: `docs/rules/RULES_CANONICAL.md` §B2 ampliata con la meccanica
Grinta e la tabella Contact↔Azione; `docs/rules/RULES_PENDING.md` ridotto a
9 voci (rinumerate), con nuova voce sul riutilizzo dei segnalini Grinta tra
round dello stesso turno.

## 2026-07-30 — Tracciati prezzo per tipo di Dope
Decisione: i prezzi 3, 1, 4, 6 di §A3 sono, nell'ordine, quelli di
Camaleonte, Rana, Polpo, Gufo (stesso ordine di §A2). Ogni tipo di Dope ha
un proprio tracciato di valori ammessi, non un range di interi consecutivi:
Camaleonte [2,3,4,6,8], Rana [0,1,3,5], Polpo [3,4,5,7,9,11], Gufo
[4,6,8,10,12,14]. Tutti partono al secondo valore del proprio tracciato. Un
prezzo che "sale/scende di 1" (acquisto, requisizione, vendita, Marketing)
si muove di uno step sul tracciato del proprio tipo, non di un dollaro.
Riferimento: risolve il punto "Prezzi" della vecchia numerazione di
`RULES_PENDING.md`.
Impatto: `docs/rules/RULES_CANONICAL.md` §A3 riscritta con la tabella dei
tracciati; `docs/rules/RULES_PENDING.md` ridotto a 8 voci (rinumerate).

## 2026-07-31 — Mappa: Hoods, Contact e Dope iniziali
Decisione: ogni Contact ha esattamente 2 Hoods, uno scoperto e uno coperto:
Q1/Q2 Artisti, Q3/Q4 Studenti, Q5/Q6 Manager, Q7/Q8 Preti, Q9/Q10 Politici.
I 5 Hoods scoperti iniziano con 3 Dope: Q1 Rana, Q3 Gufo, Q5 Rana, Q7
Camaleonte, Q9 Polpo. Le adiacenze sono state trascritte come fornite, ma
restano PROVVISORIE: due coppie (Q2↔Q6, Q5↔Q9) sono asimmetriche nei dati
ricevuti e vanno confermate.
Riferimento: risolve la parte "nomi Hoods / Contact / Dope iniziali" del
punto "Mappa" della vecchia numerazione di `RULES_PENDING.md`; le
adiacenze restano aperte come nuovo punto PROVVISORIO, così come il
contenuto delle tile rotonde dei Quartieri coperti.
Impatto: aggiunta sezione `## F) Mappa` a `docs/rules/RULES_CANONICAL.md`
(§F1 Hoods/Contact, §F2 adiacenze provvisorie, §F3 Spots ancora vuoto);
`docs/rules/RULES_PENDING.md` ridotto a 9 voci (rinumerate).

## 2026-07-31 — Conferma adiacenze mappa
Decisione: confermate simmetriche entrambe le coppie segnalate come
asimmetriche: Q2↔Q6 e Q5↔Q9 sono adiacenti in entrambi i versi.
Riferimento: chiude il punto "Adiacenze della mappa (PROVVISORIO)".
Impatto: `docs/rules/RULES_CANONICAL.md` §F2 aggiornata e il flag
PROVVISORIO rimosso; `docs/rules/RULES_PENDING.md` ridotto a 8 voci
(rinumerate).

## 2026-07-31 — Tile dei Quartieri coperti e dimensione mazzetto iniziale
Decisione: le 5 tile rotonde sono `1, 2, 2c, 3, 3c` (numero = Dope da
caricare, `c` = entra anche un Cops). A setup si formano 5 coppie
(tipo di Dope, tile) da 2 Camaleonte + 1 Rana + 1 Polpo + 1 Gufo abbinati
casualmente alle 5 tile, poi le 5 coppie sono assegnate casualmente ai 5
Quartieri coperti. Conferma inoltre che il mazzetto di carte iniziali
(§E2) è di 15 carte (5 Contact × 3), con 3 carte avanzate a 4 giocatori.
Riferimento: risolve il punto "Tile rotonde dei Quartieri coperti" della
vecchia numerazione di `RULES_PENDING.md`.
Impatto: `docs/rules/RULES_CANONICAL.md` nuova §F3 (tile), §E2 aggiornata
con la dimensione del mazzetto; `docs/rules/RULES_PENDING.md` ridotto a 7
voci (rinumerate).

## 2026-07-31 — Spots dei Contact: Dope accettata e adiacenze
Decisione: i 10 Spot (2 per Contact) sono disposti in fila nell'ordine
Artisti→Studenti→Manager→Preti→Politici, ciascuno adiacente solo al vicino
immediato in fila. Dope accettata, in ordine: Artisti Camaleonte/Polpo,
Studenti Camaleonte/Rana, Manager Gufo/Camaleonte, Preti Rana/Polpo,
Politici Rana/Gufo.
Riferimento: risolve il punto "Spots" della vecchia numerazione di
`RULES_PENDING.md`. Resta aperto se la fila sia chiusa ad anello (Artisti-1
adiacente a Politici-2) o aperta agli estremi — assunto aperta finché non
confermato, nuovo punto in `RULES_PENDING.md`.
Impatto: `docs/rules/RULES_CANONICAL.md` §F4 riscritta con tabella Spot↔
Dope↔adiacenze; `docs/rules/RULES_PENDING.md` ridotto a 7 voci (rinumerate,
con la nuova voce sull'anello della fila di Spot).

## 2026-07-31 — Chips iniziali, riuso Grinta, catena Spot aperta
Decisione: Chips Cops/Poker nel Covo partono da 0; ogni segnalino Grinta si
usa una sola volta per turno (3 round = 3 segnalini distinti, uno a testa);
la fila di 10 Spot è aperta, non ad anello (Artisti-1° e Politici-2° non
sono adiacenti).
Riferimento: chiude i punti "Chips Cops/Poker iniziali", "Riutilizzo dei
segnalini Grinta" e "Adiacenza degli Spot in fila aperta o chiusa ad
anello" della vecchia numerazione di `RULES_PENDING.md`. Carte Clienti,
Jobs/Skills e Retate restano rimandati a una prossima sessione su richiesta
esplicita del game designer.
Impatto: `docs/rules/RULES_CANONICAL.md` §E3, §B2, §F4 aggiornate;
`docs/rules/RULES_PENDING.md` ridotto a 4 voci (le 3 rimandate + punteggio
denaro).

## 2026-07-31 — Valori di punteggio del tracciato denaro
Decisione: la posizione sul tracciato denaro vale, dalla più alta: 1ª = 4
punti, 2ª = 3, 3ª = 2, 4ª = 1. In caso di parità, i giocatori pareggiati
prendono tutti il valore più basso tra le posizioni che occuperebbero
(es. due giocatori a pari merito per 2ª/3ª prendono entrambi 2 punti).
Riferimento: chiude il punto "Punteggio denaro" della vecchia numerazione
di `RULES_PENDING.md` — era l'ultimo punto non rimandato a domani.
Impatto: `docs/rules/RULES_CANONICAL.md` §D6 completata con la tabella
punti; `docs/rules/RULES_PENDING.md` ridotto a 3 voci, tutte esplicitamente
rimandate dal game designer (Carte Clienti, Jobs/Skills, Retate).
