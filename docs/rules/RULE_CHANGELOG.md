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
