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

## 2026-07-31 — Struttura dettagliata dei Jobs
Decisione: 9 Job in 3 tier da 3; ogni giocatore possiede un set completo
dei 9 (non un pool condiviso), organizzati in 3 mazzetti personali per
tier; scopre le prime 3 (una per tier) a inizio partita e ne scopre una
nuova dello stesso tier ogni volta che ne completa una. Il tabellone ha una
riga per Job con 4 colonne di bonus condivise tra i giocatori (Skill+1 PV,
Link diretto dal Covo, 2 carte, o nessun bonus); chi completa per primo un
Job sceglie tra tutte e 4, chi lo completa dopo tra quelle rimaste libere.
Ogni Job è associato a 1 o 2 Contact, che determinano il colore delle
risorse ottenute come bonus.
Riferimento: espande la voce "Jobs e Skills" della numerazione di
`RULES_PENDING.md`; resta aperto l'elenco dei 9 Job con requisiti e
Contact associato, e il contenuto delle Skill.
Impatto: `docs/rules/RULES_CANONICAL.md` §A10 ampliata;
`docs/rules/RULES_PENDING.md` voce 2 riformulata (mancano solo i dati,
non più la meccanica).

## 2026-07-31 — Elenco dei 9 Job
Decisione: il game designer ha fornito (via immagine di una tabella) i 9
Job con requisito e Contact associato: Vinci 1 Rissa (Studenti); Compra 1
Cop/Fed (Politici); Vinci 2 Poker (Preti); Abbi 3 Rats (Politici/Preti);
Abbi 4 Dope nel Covo, almeno una per tipo (Artisti); Abbi 4 Link in totale
(Politici/Artisti); Abbi Criminali in 6 Hoods diversi (Manager); Abbi tutti
i 10 Criminali in gioco, fuori dal Covo (Manager/Studenti); Abbi 30 dollari
o più (Manager/Artisti).
Riferimento: espande la voce "Jobs e Skills" di `RULES_PENDING.md`. Manca
ancora l'assegnazione ai 3 tier di difficoltà e il contenuto delle Skill.
Impatto: `docs/rules/RULES_CANONICAL.md` §A10 con la tabella dei 9 Job;
`docs/rules/RULES_PENDING.md` voce 2 ridotta a tier + Skill.

## 2026-07-31 — Tier dei 9 Job
Decisione: assegnati i tier (via immagine): tier 1 = Vinci 1 Rissa, Compra
1 Cop/Fed, Criminali in 6 Hoods; tier 2 = Abbi 3 Rats, Abbi 4 Dope nel Covo,
Abbi 4 Link; tier 3 = Vinci 2 Poker, Tutti i 10 Criminali fuori dal Covo,
Abbi 30 dollari o più.
Riferimento: chiude la parte "tier" della voce Jobs/Skills di
`RULES_PENDING.md`; resta solo il contenuto delle carte Skill.
Impatto: `docs/rules/RULES_CANONICAL.md` §A10 tabella completata con la
colonna Tier; `docs/rules/RULES_PENDING.md` voce Jobs ridotta a sole
Skill.

## 2026-07-31 — Effetti delle Skill per Contact
Decisione: il game designer ha fornito (via immagine) 15 effetti Skill, 3
per ciascuno dei 5 Contact (Artisti, Studenti, Manager, Preti, Politici),
tutti abilità permanenti che valgono anche 1 punto vittoria a fine
partita.
Riferimento: espande la voce Skill di `RULES_PENDING.md`. Resta aperto un
conteggio: sono stati forniti 15 effetti ma i Job con bonus Skill sono un
sottoinsieme dei 9 Job totali — da chiarire se il pool di Skill realmente
in gioco è di 15 carte o meno.
Impatto: `docs/rules/RULES_CANONICAL.md` §A10 con la tabella dei 15
effetti Skill; `docs/rules/RULES_PENDING.md` voce Skill riformulata sul
conteggio.

## 2026-07-31 — Conferma conteggio Skill e le 7 carte Retata
Decisione: confermato che le Skill in gioco sono 15 (3 per Contact); non
tutte vengono prese in una singola partita. Trascritte le 7 carte Retata
da `RET_V8.pdf`: Più Ganci coi Clienti; Più Criminali in prigione; Meno
valore di Merci; Vinto più Poker; Comprato più Cops; Più dollari; Più
Criminali nei Quartieri. Il criterio di ciascuna carta si applica sommando
i valori dei due compagni di squadra e confrontando le due squadre; la
squadra con la somma migliore (più alta, o più bassa per "meno valore di
Merci") sfugge, l'altra cade e ogni suo componente macchia la reputazione.
Riferimento: chiude il conteggio Skill; chiude il punto "Retate" della
vecchia numerazione di `RULES_PENDING.md` tranne il comportamento in caso
di parità tra squadre, che resta aperto. Riportata in evidenza anche la
voce "primo giocatore senza Link ai Preti" (§D4), rimasta aperta dai 34
punti originari e non ancora chiusa.
Impatto: `docs/rules/RULES_CANONICAL.md` §A10 (Skill) e §D4 (Retate)
aggiornate; `docs/rules/RULES_PENDING.md` ridotto a 3 voci: Carte Clienti
(rimandate), parità Retate, primo giocatore senza Link ai Preti.

## 2026-07-31 — Unificazione token REP e segnalini R dei Job
Decisione: i token REP di §D5 sono gli stessi segnalini R piazzati sul
tracciato Job al completamento (§A10) — non c'è un pool di REP separato.
Macchiare una REP gira sul retro un segnalino R già piazzato (quindi serve
averne almeno uno non macchiato); un R dritto vale 2 punti a fine partita,
girato vale 1.
Riferimento: chiarisce senza contraddire il testo originale del
regolamento (§D5 già parlava di "girare il token"); esplicita il legame
con §A10 non evidente a una prima lettura.
Impatto: `docs/rules/RULES_CANONICAL.md` §D5 ampliata con il collegamento
a §A10.

## 2026-07-31 — Primo giocatore senza Link ai Preti
Decisione: se in un turno (dal 2° in poi) nessun giocatore ha un Link ai
Preti, resta primo giocatore chi lo era nel turno precedente (nessun
cambio).
Riferimento: chiude il punto "Primo giocatore quando nessuno ha Link ai
Preti" della vecchia numerazione di `RULES_PENDING.md`, riportato in
evidenza il 2026-07-31 dopo essere stato erroneamente omesso in una
precedente riscrittura del file.
Impatto: `docs/rules/RULES_CANONICAL.md` §D4 e §E6 aggiornate;
`docs/rules/RULES_PENDING.md` ridotto a 2 voci: Carte Clienti (rimandate),
parità tra squadre nelle Retate.

## 2026-07-31 — Parità nelle Retate e conferma "a testa"
Decisione: in caso di parità tra le due squadre nel confronto di una carta
Retata, cadono tutti e 4 i giocatori (nessuno sfugge). Confermato inoltre
che i valori "1/2/3 REP macchiate" per prima/seconda/terza Retata della
partita sono a testa: ogni giocatore che cade macchia quel numero di
propri segnalini R.
Riferimento: chiude il punto "Retate — parità tra squadre" della vecchia
numerazione di `RULES_PENDING.md`. La clausola "a testa" apre però una
nuova domanda: cosa succede se un giocatore non ha abbastanza segnalini R
non macchiati da girare.
Impatto: `docs/rules/RULES_CANONICAL.md` §D4 aggiornata con la regola di
parità; `docs/rules/RULES_PENDING.md` ridotto a 2 voci: Carte Clienti
(rimandate), REP insufficienti da macchiare.

## 2026-07-31 — REP insufficienti da macchiare
Decisione: se un giocatore non ha abbastanza segnalini R non macchiati per
il quantitativo richiesto da una Retata persa, semplicemente non macchia
quelli che non può — nessuna penalità o effetto sostitutivo.
Riferimento: chiude il punto "REP insufficienti da macchiare" della
vecchia numerazione di `RULES_PENDING.md`. Con questo si chiudono tutte le
ambiguità di regole raccolte finora: resta aperto solo il dataset delle
Carte Clienti, esplicitamente rimandato dal game designer.
Impatto: `docs/rules/RULES_CANONICAL.md` §D4 aggiornata;
`docs/rules/RULES_PENDING.md` ridotto a 1 sola voce (Carte Clienti).

## 2026-07-31 — Schema dettagliato delle Carte Clienti
Decisione: confermata da un esempio di carta ("TRY AGAIN", azione
Acquistare) la codifica esatta delle icone: 6 icone di azione base
(stella=Acquistare, cuore=Vendere, freccia giù=Piazzare, freccia
destra=Spostare, distintivo=Corrompere, distintivo+dollaro=Comprare
Cops/Feds); 2 simboli Poker (fiori a 5 petali, 5 colori possibili: rosa
scuro, arancione, verde, grigio, azzurro); 4 simboli Stonk/Pistola in
combinazione libera; potenziamento azione in testo libero, non formula
fissa; titolo flavor senza effetto meccanico.
Riferimento: espande `RULES_CANONICAL.md` §A9. Resta da chiarire come
identificare il Contact di appartenenza di ogni carta quando arriva il
dataset completo.
Impatto: `docs/rules/RULES_CANONICAL.md` §A9 ampliata con lo schema
dettagliato; `docs/rules/RULES_PENDING.md` voce Carte Clienti aggiornata.

## 2026-07-31 — Identificazione Contact e schema delle carte Preti
Decisione: il Contact di una carta si riconosce dal colore di sfondo, sulla
stessa palette dei 5 semi Poker: Artisti rosa, Studenti verde, Manager
azzurro, Preti grigio, Politici arancione. Confermato che il titolo flavor
("TRY AGAIN") non ha effetto meccanico. Le carte Preti (esempio "GAMBLE")
non hanno mai i 2 simboli Poker in alto a sinistra; hanno comunque
un'icona azione base (ripetuta in basso); mantengono i 4 simboli
Stonk/Pistola; al posto del testo di potenziamento hanno 3 simboli Poker
su sfondo nero, che diventano il banco comune quando la carta viene
giocata come Gamble (coerente con la decisione già registrata in §D2).
Riferimento: chiude l'identificazione del Contact per `RULES_PENDING.md`.
Resta aperto se "GAMBLE" sia il titolo fisso di tutte le carte Preti o
vari carta per carta.
Impatto: `docs/rules/RULES_CANONICAL.md` §A9 completata con la mappa
colore↔Contact e lo schema delle carte Preti; `docs/rules/RULES_PENDING.md`
ridotto al solo contenuto delle 100 carte + la domanda sul titolo
"GAMBLE".

## 2026-07-31 — Dataset placeholder delle 100 Carte Clienti
Decisione: il game designer ha fornito un dataset completo (100 carte, 20
per Contact) sotto forma di tabella; conferma però che è una **versione
non aggiornata**. Va usata come PROVISIONAL/placeholder per sviluppo e
test, non come regola definitiva. In particolare: (a) 5 carte Politici
"BACKSTABBER" mostrano un'azione "reputazione" che il game designer
conferma non esistere più; (b) le carte Preti in questo dataset coprono
solo 3 azioni su 6 (acquistare/vendere/piazzare), mentre resta confermato
che le carte Preti possono avere qualunque delle 6 azioni.
Riferimento: il titolo "GAMBLE" risulta fisso su tutte le 20 carte Preti
di questo dataset, a supporto (non definitiva conferma, essendo una
versione superata) di quanto ipotizzato in precedenza.
Impatto: creati `data/customer_cards_draft.csv` e `.xlsx` (100 righe,
marcate PLACEHOLDER); `docs/rules/RULES_PENDING.md` aggiornato per
riflettere che serve la versione aggiornata del dataset, non più lo
schema (già noto) né un dataset da zero.

## 2026-08-01 — Terza asimmetria di adiacenza rilevata (Q3↔Q6)
Decisione: durante l'implementazione della Milestone 0,
`tools/validate_data.py` ha rilevato che Q6 elenca Q3 come adiacente ma
Q3 non elencava Q6 — un'asimmetria non notata durante la revisione della
mappa del 2026-07-31 (che aveva corretto solo Q2↔Q6 e Q5↔Q9). Applicata
correzione PROVVISORIA in `data/board.json` (aggiunta Q3→Q6) in attesa di
conferma esplicita, seguendo lo stesso criterio delle altre due correzioni
già confermate.
Riferimento: nuovo punto "Adiacenza Q3↔Q6" in `RULES_PENDING.md`.
Impatto: `data/board.json` aggiornato con nota PROVISIONAL sul campo;
`docs/rules/RULES_CANONICAL.md` §F2 annotata; `docs/rules/RULES_PENDING.md`
ha una nuova voce in attesa di conferma.

## 2026-07-31 — Piazzamento non può mai portare un Quartiere al trigger della Rissa
Decisione: il game designer conferma che un Quartiere non è mai davvero
pieno, perché è lo Spostamento (non il Piazzamento) del quinto Criminale
a far scattare subito la Rissa, che sposta via almeno un Criminale
sconfitto (il vincitore può diventare Link). Il Piazzamento non fa mai
scattare la Rissa e quindi non deve mai poter portare un Quartiere a quel
conteggio: un piazzamento che lo farebbe è illegale, non solo "in attesa
di Rissa".
Riferimento: implementato in `backend/src/dope_engine/rules/economy.py`
(`_handle_place_criminal`) e `backend/src/dope_engine/application/
legal_actions.py` (`_place_criminal_options`), entrambi ora limitano il
Piazzamento a `brawl_trigger_criminal_count - 1` Criminali per Quartiere
invece della capacità piena (5).
Impatto: `docs/rules/RULES_CANONICAL.md` §D1 ampliata con la decisione;
`docs/rules/RULES_PENDING.md` nuova voce 5 sul gap temporaneo (lo
Spostamento può ancora raggiungere quel conteggio senza risoluzione
automatica finché la Rissa non è implementata in Milestone 4); nuovo test
`test_place_criminal_never_brings_hood_to_rissa_trigger_count`.

## 2026-07-31 — Semplificazioni tecniche della Milestone 2 (economia)
Decisione (provvisoria, in attesa di conferma del game designer): durante
l'implementazione delle azioni economiche (Piazzare/Spostare/Acquistare/
Vendere), due punti non sufficientemente specificati da
`RULES_CANONICAL.md` §C3/§C4/§A6 sono stati risolti con una scelta
tecnica esplicitamente marcata PROVISIONAL: (a) lo scatto di prezzo a
fine pacchetto vale 1 posizione per ogni unità di quel tipo comprata/
venduta nel pacchetto, non 1 posizione fissa per pacchetto; (b) la
rimozione di un Fed da uno Spot "senza Merci e senza Ganci" non è
implementata, perché la condizione si auto-annullerebbe nell'istante
stesso dello spawn del Fed finché non esistono i Link (Milestone 3) — la
rimozione del Cop da un Hood, che non ha questo problema, è invece
implementata.
Riferimento: commenti nel modulo (`backend/src/dope_engine/rules/
economy.py`, docstring di modulo e di `_handle_buy_dope`/
`_handle_sell_dope`).
Impatto: `docs/rules/RULES_PENDING.md` nuove voci 3 e 4 nella sezione
"Semplificazioni tecniche della Milestone 2".
