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

## 2026-07-31 — Conferma magnitudo prezzo a pacchetto e promemoria Link su vendita
Decisione: il game designer conferma che, comprando o vendendo 2/3 Merci
in pacchetto (stesso Quartiere/stesso Punto di Vendita), il prezzo si
muove di tante posizioni quante sono le unità del pacchetto (es. 3
unità → 3 posizioni), applicate una sola volta alla fine — esattamente
la lettura già implementata provvisoriamente. Il game designer ricorda
inoltre che vendendo 2/3 Merci in pacchetto si prende un Link di livello
pari al numero di merci vendute (già transcritto in `RULES_CANONICAL.md`
§C4, ma non ancora implementato in Milestone 2 perché i Link sono
Milestone 3).
Riferimento: chiude la voce "Magnitudo dello scatto di prezzo nei
pacchetti" di `RULES_PENDING.md`.
Impatto: `docs/rules/RULES_PENDING.md` — rimossa la voce sulla magnitudo
(ora confermata, non più PROVVISORIA); aggiunta voce 4 "Link su vendita a
pacchetto (NON IMPLEMENTATO in Milestone 2, ATTESO)" per tracciare
esplicitamente il gap fino alla Milestone 3; `backend/src/dope_engine/
rules/economy.py` docstring di modulo aggiornata di conseguenza.

## 2026-08-01 — Timing dell'azione extra da Link (Milestone 3)
Decisione: il game designer conferma che l'azione extra ottenibile
spendendo un Link può essere giocata prima o dopo l'azione principale del
round, al massimo una volta per turno intero (non per round), a meno di
Skill o carte non ancora implementate che rompano questo vincolo. Il Link
speso torna sempre al Covo dopo l'uso, indipendentemente da quando è stato
giocato nel turno.
Riferimento: RULES_CANONICAL.md §A5 (nuova decisione 2026-08-01); conferma
diretta durante l'implementazione della Milestone 3.
Impatto: `rules/turn_flow.py` offre l'azione extra in due punti per round
(`_enter_grit_or_extra_action_offer` prima della Grinta,
`proceed_after_main_action` dopo l'azione principale), entrambi
declinabili via `PassOptionalStep`; `PlayerState.extra_action_from_post_main`
traccia quale dei due punti è attivo per riprendere il flusso corretto.

## 2026-08-01 — Milestone 3: Links, Corruzione, Acquisto Officers, Jail/Evasione
Decisione: implementata la Milestone 3 (CLAUDE.md sezione 21) seguendo le
regole già transcritte in RULES_CANONICAL.md, con alcune scelte tecniche
non ambigue nel regolamento ma necessarie per l'implementazione, tutte
tracciate come voci PROVVISORIE in RULES_PENDING.md invece di essere
inventate silenziosamente: quale pedina evolve in Link su una vendita a
pacchetto con più venditori sullo stesso Punto di Vendita; l'evoluzione a
Link su singola vendita resa automatica invece che opzionale; il bersaglio
dell'arresto Feds ("Link di livello minore") cercato fra tutti i
giocatori, non solo il corruttore; una sentinella "skip" per il raro caso
in cui la 2ª azione di una Corruzione non ha bersagli legali; l'eventualità
che un pacchetto di Corruzione invalidi un target successivo nella coda
(scoperta tramite simulazione bot-only massiva, non dai test unitari); il
modello di associazione Rat↔Merce confiscata nella Jail (due ricerche
indipendenti per slot, non un accoppiamento forzato). La rimozione del Feds
da uno Spot "senza Ganci" resta non implementata: i Link ora esistono ma il
trigger è sparso su troppi moduli per essere corretto in modo affidabile
prima di Milestone 4 (Rissa), che dovrà comunque centralizzare il calcolo
della presenza dei Link.
Riferimento: RULES_PENDING.md voci 3-10.
Impatto: nuovi moduli `rules/links.py`, `rules/jail.py`, `rules/officers.py`;
estesi `domain/commands.py`, `domain/events.py`, `domain/enums.py`,
`domain/state.py` (CorruptOfficer, ChooseCorruptionAction, BuyOfficer,
SpendLinkForExtraAction, ActiveStep.WAITING_FOR_CORRUPTION_ACTION,
GameState.pending_corruption); `application/legal_actions.py` esteso con
generatori di opzioni per Corrompere/Comprare Officers e per il
sotto-flusso della Corruzione e dell'azione extra da Link;
`application/views.py`/adapter HTTP estesi con Officers e Jail; 23 nuovi
test unitari; verificato con 2000 partite bot-only simulate senza errori.

## 2026-08-01 — Rissa: assegnazione Pistole, ricompensa, destinazione, tie-break (Milestone 4)
Decisione: il game designer conferma 4 punti aperti su §D1 prima
dell'implementazione della Milestone 4: (1) tutte le Pistole di una carta
coperta rivelata vanno a un solo bersaglio, non distribuite; (2) la scelta
fra 2 dollari o 1 carta come ricompensa è indipendente per ciascuno
sconfitto; (3) il vincitore sceglie il Quartiere inesplorato di
destinazione quando ce n'è più di uno disponibile; (4) il tie-break finale
"il primo giocatore, o seguenti" è l'ordine di rotazione dei turni a
partire da `first_player_id`, applicato solo fra i partecipanti ancora in
parità dopo gli altri criteri.
Riferimento: RULES_CANONICAL.md §D1, nuova sezione "Decisioni
(2026-08-01), Milestone 4".
Impatto: sblocca l'implementazione di `rules/brawl.py`; restano
PROVVISORIE (RULES_PENDING.md voci 11-12) due scelte tecniche non coperte
da queste conferme: quanti Criminali dello sconfitto vengono spostati via
(tutti quelli nel Quartiere, non uno) e se il furto di 1 carta sia casuale
o a scelta (casuale, perché le mani sono informazione nascosta).

## 2026-08-01 — Milestone 4 (parte 1): implementazione della Rissa
Decisione: implementata la sotto-macchina a stati della Rissa (declare →
reveal → reward) seguendo le 4 conferme e le 2 scelte PROVVISORIE già
registrate nella voce precedente. Il trigger resta esclusivamente
`MoveCriminal` (mai `PlaceCriminal`, già limitato da Milestone 2); una
Rissa può scattare su *qualunque* mossa di un pacchetto multi-mossa, non
solo l'ultima, quindi `MoveCriminal` ora si mette in pausa/ripresa
attorno a `rules/movement.py::process_move_queue` invece di risolvere
tutte le mosse in un solo passaggio.

Durante l'implementazione, una simulazione bot-only ha scoperto due gap
strutturali non coperti dalle 4 conferme del game designer, entrambi
sul limite di 5 carte in mano (CLAUDE.md punto 22.29, già aperto): (a)
la ricompensa "1 carta" e il pescaggio alla ricollocazione di uno
sconfitto possono far salire sopra 5 la mano di un partecipante che non
è il giocatore che riprende il pacchetto (`resume_player_id`), un caso
per cui non esiste ancora una decisione interattiva "fuori turno"; (b)
`domain/invariants.py::_check_hand_size` esentava dal controllo solo il
giocatore corrente esattamente allo step `WAITING_FOR_HAND_DISCARD`, ma
un'azione extra da Link giocata "prima" del round può legittimamente
lasciare la mano sopra 5 per diversi step intermedi dello stesso round
(e, con la Rissa, anche mentre `resume_player_id` resta in pausa dentro
una Rissa annidata) prima che il controllo di fine round scatti
davvero. Il primo è stato risolto con uno scarto automatico e casuale
(PROVVISORIO, RULES_PENDING.md voce 12); il secondo ampliando
l'esenzione dell'invariante al giocatore corrente in generale e a
`pending_brawl.resume_player_id` quando una Rissa è in corso — non è
una nuova regola di design, solo una correzione del controllo affinché
rispecchi il comportamento già inteso da Milestone 1-3.
Riferimento: RULES_CANONICAL.md §D1; RULES_PENDING.md voce 12; CLAUDE.md
punto 22.29 (ancora aperto).
Impatto: nuovi moduli `rules/movement.py`, `rules/brawl.py`; estesi
`domain/state.py` (`BrawlProgress`, `GameState.pending_brawl`),
`domain/commands.py` (5 nuovi comandi Rissa), `domain/events.py` (7
nuovi eventi); `rules/economy.py` ridotto (logica di movimento estratta);
`application/legal_actions.py` e `adapters/http/app.py` estesi con le
opzioni/i comandi dei 3 sotto-step della Rissa; `domain/invariants.py::
_check_hand_size` corretto come sopra. Resta un gap noto e documentato
(non ancora risolto): una Rissa annidata scatenata dalla ricollocazione
di uno sconfitto in un Quartiere appena rivelato non viene gestita da
uno stack di `pending_brawl` — vedi il docstring di `rules/brawl.py`.

## 2026-08-01 — Milestone 4 (parte 2): due bug trovati da simulazione bot-only a 500 seed
Decisione: non una decisione di design ma la correzione di due bug
concreti (non ambiguità di regolamento) emersi eseguendo 500 partite
bot-only end-to-end con controllo delle invarianti dopo ogni comando —
lo stesso metodo già usato in Milestone 2/3 (RULES_PENDING.md voci 8 e
9). Nessuno dei due era coperto dai test unitari perché richiede una
Rissa innescata *dentro* un pacchetto `MoveCriminal` multi-mossa, una
combinazione che solo una simulazione ampia raggiunge con probabilità
sufficiente.

(a) **Ricollocazione oltre la capacità del Quartiere:** tutti i
Criminali sconfitti di *tutti* gli sconfitti convergono sullo stesso,
singolo Quartiere scelto dal vincitore (decisione già confermata
sopra); con più sconfitti aventi più Criminali ciascuno, il totale può
superare la capacità di 5, cosa che `rules/brawl.py::
_handle_choose_brawl_relocation_destination` non controllava affatto.
Corretto imponendo lo stesso limite di capacità già rispettato da
`rules/movement.py::move_one_pawn` per un movimento normale: i
Criminali oltre la capacità del Quartiere scelto vanno al Covo invece
che lì, stesso precedente già stabilito per il Covo pieno (decisione
del 2026-07-30, punto 10: "l'eccedenza va persa, l'azione avviene
comunque"). Non tenta di far scattare una nuova Rissa annidata quando
la capacità viene raggiunta — resta il gap noto già documentato.

(b) **Ripresa di un pacchetto `MoveCriminal` con una mossa ormai
non valida:** quando una Rissa risolve una mossa in coda, può
spostare/rimuovere *altre* pedine dello stesso giocatore che si
trovavano in quel Quartiere (proprie pedine sconfitte nella Rissa che
il pacchetto avrebbe mosso più avanti), invalidando quella mossa già
in coda. Prima della correzione, la ripresa del pacchetto
(`rules/brawl.py::_finish_brawl` → `rules/movement.py::
process_move_queue`) falliva l'intero comando su quella mossa —
scartando anche le scelte di ricompensa già confermate con comandi
precedenti e rischiando uno stallo, perché `get_legal_decision`
avrebbe riproposto la stessa decisione. Corretto aggiungendo un
parametro `resuming` a `process_move_queue`: quando è la ripresa dopo
una Rissa (mai la sottomissione originale del comando, che deve
continuare a fallire rumorosamente se un bot propone una mossa
illegale), una mossa in coda diventata non valida viene scartata in
silenzio invece di far fallire l'intero comando.
Riferimento: nessuna voce RULES_PENDING nuova (non sono ambiguità di
regolamento, sono correzioni di implementazione).
Impatto: `rules/brawl.py::_handle_choose_brawl_relocation_destination`;
`rules/movement.py::process_move_queue` (nuovo parametro `resuming`);
`rules/brawl.py::_finish_brawl` (passa `resuming=True`).

## 2026-08-01 — Rissa: pedina singola per sconfitto e definizione di partecipante (Milestone 4)
Decisione: il game designer corregge direttamente due punti
dell'implementazione della Rissa, in seguito ai risultati della
simulazione bot-only di cui sopra:
1. Quando un giocatore perde una Rissa, viene mandata via **una sola**
   pedina fra quelle sue fisicamente presenti nel Quartiere, non tutte
   — anche se ne aveva più di una lì (che comunque contribuivano alla
   Forza). Questo risolve retroattivamente la voce PROVVISORIA
   precedente (ex punto 11 di RULES_PENDING.md, ora rimossa perché
   risolta) sostituendola con una regola definitiva.
2. Partecipano a una Rissa solo i giocatori con almeno 1 pedina
   Criminale fisicamente nel Quartiere che raggiunge la soglia. I Link
   presso il Contact del Quartiere si sommano alla Forza di un
   partecipante già presente fisicamente — tutti e 3 i livelli, se
   presenti — ma non rendono partecipante da solo un giocatore che ha
   lì solo un Link e nessun Criminale fisico — `rules/brawl.py::
   compute_participants` includeva erroneamente anche questi giocatori
   "solo Link", un bug di implementazione (non un'ambiguità di
   regolamento) corretto qui.
3. Chiarito che non esiste un tetto fisso di Pistole per Rissa: ogni
   carta vale da 0 a 4 Pistole a seconda di quale viene giocata. Il "gap
   noto" sulla Rissa annidata (già documentato nel docstring di
   `rules/brawl.py`) resta quindi teoricamente possibile solo se un
   Quartiere di destinazione non fosse vuoto, ma con solo 4 giocatori in
   partita e la regola della pedina singola per sconfitto, al massimo 3
   pedine convergono in una singola risoluzione — il controllo di
   capacità sulla ricollocazione resta comunque come rete di sicurezza.
Riferimento: RULES_CANONICAL.md §D1 (nuove decisioni aggiunte); rimossa
la voce 11 (ora 12→11 rinumerate) da RULES_PENDING.md.
Impatto: `rules/brawl.py::_handle_choose_brawl_relocation_destination`
(una sola pedina per sconfitto, scelta deterministica: prima nell'ordine
di `hood.criminal_pawn_ids`); `rules/brawl.py::compute_participants`
(rimossa l'inclusione errata dei giocatori "solo Link").

## 2026-08-01 — Bug pre-esistente (Milestone 3): Link speso per azione extra arrestato dalla propria stessa azione
Decisione: non un'ambiguità di regolamento ma un bug di implementazione
trovato dalla stessa simulazione bot-only, in un caso limite
auto-referenziale: un giocatore spende un proprio Link (es. presso i
Politici) per un'azione extra, e sceglie come azione extra proprio
"Corrompere un Officer"; se la 2ª sotto-azione di quella corruzione è un
Feds che arresta "il Link di livello minore" presso lo stesso Contact,
può finire per arrestare il Link che sta *in quel momento* alimentando
l'azione extra stessa. `rules/turn_flow.py::finish_action_or_extra`
(chiamata a fine di ogni azione principale o extra) presumeva sempre
che quella pedina fosse ancora un Link e la riportava incondizionatamente
al Covo (`role = IN_BASE`) — sovrascrivendo così l'arresto appena
avvenuto (`role = RAT`, in uno slot della Jail) senza liberare lo slot,
lasciando la pedina "in_base" ma ancora indicizzata nello slot come Rat.
**Superato dalla decisione successiva dello stesso giorno** (vedi sotto):
il game designer ha chiarito che il Link torna al Covo *subito* quando
viene speso, non a fine azione — la correzione qui sotto (guardia su
`role == LINK`) è stata quindi sostituita da quella struttural­mente
corretta, non solo mascherata.
Riferimento: nessuna voce RULES_PENDING nuova (bug di implementazione,
non ambiguità di regolamento).
Impatto: superseduto, vedi la voce successiva.

## 2026-08-01 — Tre correzioni dirette del game designer: scarto di fine turno, Covo illimitato, Link restituito subito
Decisione: il game designer corregge direttamente tre punti
dell'implementazione, indipendenti dalla Rissa ma emersi durante la
stessa sessione di lavoro:
1. **Limite di 5 carte in mano:** si applica solo alla fine del turno
   del singolo giocatore (il suo ultimo dei 3 action round), non dopo
   ogni round. Risolve CLAUDE.md punto 22.29. `rules/turn_flow.py::
   _continue_after_main_action` ora apre `WAITING_FOR_HAND_DISCARD` solo
   quando `action_round_index` è l'ultimo del turno
   (`_is_players_last_round`); negli altri round l'eccedenza resta e si
   somma finché non si arriva all'ultimo round. Di conseguenza
   `domain/invariants.py::_check_hand_size` non può più essere
   verificata durante `ACTION_PHASE` per nessun giocatore in particolare
   (chiunque può legittimamente avere più di 5 carte fino al proprio
   ultimo round) — l'invariante ora si applica solo a fine
   `ACTION_PHASE`, quando ogni giocatore ha già passato il proprio
   controllo di fine turno. Questo risolve anche, per costruzione, il
   problema del "bystander" di una Rissa (voce PROVVISORIA precedente,
   ora rimossa da RULES_PENDING.md): non serve più uno scarto
   automatico sul momento, perché l'eccedenza è comunque legittima fino
   al turno del giocatore in questione — `rules/brawl.py::
   _enforce_bystander_hand_limit` è stato rimosso.
2. **Capienza del Covo:** l'unica cosa senza alcun limite nel Covo sono
   le pedine Criminale stesse (limitate solo dal totale di 10 possedute
   da ciascun giocatore, non da una capienza del Covo — non era comunque
   mai stato implementato un tetto per le pedine). Dope, Chip Poker e
   Cops/Feds mantengono tutti il tetto di 3 (per tipo, nel caso delle
   Dope) già confermato in CLAUDE.md §11.1/§7.6 e nella decisione
   2026-07-30 punto 8 — **nessun cambiamento** qui, `rules/economy.py::
   _handle_buy_dope`, `rules/jail.py::_recover_dope` e
   `domain/invariants.py::_check_base_chip_caps` restano come prima di
   questa sessione. (Una prima lettura di "il Covo ha capienza
   illimitata" aveva rimosso per errore il tetto sulle Dope; corretta
   nella stessa sessione dopo il chiarimento del game designer che si
   riferiva solo alle pedine.)
3. **Link speso per azione extra:** torna al Covo *immediatamente* nel
   momento in cui viene scelto (`SpendLinkForExtraAction`), prima che
   l'azione extra stessa venga anche solo scelta — non a fine azione
   come implementato inizialmente in Milestone 3. Questo rende
   strutturalmente impossibile che l'azione extra stessa possa
   arrestare/toccare il Link che la sta alimentando (risolve in modo
   definitivo, non solo mascherandolo, il bug della voce precedente):
   quando una qualunque sotto-azione gira, quella pedina è già una
   normale pedina in Covo, non più un Link cercabile da un Fed/Cop.
   Poiché il Contact del Link non è più leggibile dalla pedina a quel
   punto, `PlayerState` guadagna un nuovo campo
   `extra_action_contact_id` che lo mette in cache al momento dello
   spend; `application/legal_actions.py::_link_extra_action_decision` e
   `rules/economy.py::_handle_choose_action_type` lo leggono da lì
   invece che dalla pedina.
Riferimento: nessuna nuova voce RULES_PENDING (punto 1 risolve
direttamente CLAUDE.md 22.29; punti 2-3 sono correzioni dirette, non
ambiguità). Rimossa la voce "bystander" da RULES_PENDING.md (superata
dal punto 1).
Impatto: `rules/turn_flow.py` (`_continue_after_main_action`,
`_handle_spend_link_for_extra_action`, `finish_action_or_extra`);
`domain/state.py` (`PlayerState.extra_action_contact_id`);
`application/legal_actions.py`; `rules/economy.py::
_handle_choose_action_type` (legge `extra_action_contact_id`, non tocca
la logica del punto 2); `rules/brawl.py` (rimossa
`_enforce_bystander_hand_limit`); `domain/invariants.py::
_check_hand_size`.

## 2026-08-01 — Bug pre-esistente (Milestone 3): stallo quando l'azione extra da Link non ha bersagli legali
Decisione: non un'ambiguità di regolamento ma un bug di implementazione,
trovato dalla simulazione bot-only rilanciata dopo le correzioni sopra
(la copertura di seed più ampia lo ha reso raggiungibile con frequenza
non trascurabile). Una volta speso un Link per l'azione extra, il
sotto-passo "scegli il tipo di azione" può legittimamente non avere
alcuna opzione qualificante (es. il Contact permette solo
`buy_dope`/`sell_dope` ma il giocatore non ha denaro o pedine
disponibili in quel momento) — `application/legal_actions.py::
_choose_action_type_decision` lo riconosce correttamente
(`can_pass=not options`), ma `rules/turn_flow.py::
_handle_pass_optional_step` rifiutava **sempre** un `PassOptionalStep`
una volta che un Link era stato speso (`cannot_decline_started_extra_action`),
indipendentemente dal fatto che esistessero davvero alternative. Il
Link, ormai già tornato al Covo (vedi la decisione precedente sullo
stesso punto), è comunque perso: rifiutare di proseguire non lo
recupera, blocca solo la partita in un vicolo cieco identico nello
spirito al "corr_skip" già risolto per la Corruzione (RULES_PENDING.md,
voce risolta in Milestone 3). Corretto rendendo il `PassOptionalStep`
sempre accettabile una volta speso il Link, simmetrico a come
un'azione principale normale può sempre essere passata anche dopo aver
scelto il tipo di azione (`WAITING_FOR_MAIN_ACTION_TARGETS`).
Riferimento: nessuna voce RULES_PENDING nuova (bug di implementazione,
non ambiguità di regolamento).
Impatto: `rules/turn_flow.py::_handle_pass_optional_step`.

## 2026-08-01 — Gap PROVVISORIO: sforamento delle 5 carte per un bystander di Rissa senza turno successivo
Decisione: la regola "scarto solo a fine del proprio turno" (decisione
precedente sullo stesso giorno) lascia un gap quando un partecipante a
una Rissa diverso da chi riprende il pacchetto riceve una carta (da
ricompensa o ricollocazione) *dopo* che il proprio controllo di fine
round è già passato per quel turno: normalmente si autocorregge al
turno successivo dello stesso giocatore, ma se la partita finisce prima
(scoperto dalla simulazione bot-only, 12/500 seed) non c'è un turno
successivo in cui farlo. Poiché lo scoring di fine partita (Milestone 5,
non ancora implementato) non fa riferimento al contenuto della mano,
`domain/invariants.py::_check_hand_size` è stato esteso a saltare il
controllo anche quando `phase == FINISHED`, non solo durante
`ACTION_PHASE`. Marcato PROVVISORIO: da rivedere quando la Milestone 5
definirà lo scoring finale.
Riferimento: RULES_PENDING.md, nuova voce 12.
Impatto: `domain/invariants.py::_check_hand_size`.

## 2026-08-01 — Milestone 4 (parte 2): implementazione del Poker; ripristinato lo scarto automatico per i bystander di Rissa
Decisione: implementato il Poker (§D2) — lancio con carta Gamble dei
Preti ("prima" la scelta di Grinta del round, senza consumarlo), un
unico giro di puntate a fine turno per tutte le partite lanciate quel
turno (in base ai propri Gambler nel Den), risoluzione in ordine di
lancio con rivelazione di una carta non-Preti a testa (banco 3 simboli
+ propri 2), classifica e tie-break per colore dominante come confermato
dal game designer, conseguenze (Chip bancata further capped a 3,
incasso, evoluzione a Link dei Preti per il vincitore; arresto del
Gambler per gli sconfitti).

La simulazione bot-only (300 seed) ha mostrato che lo sforamento delle
5 carte per un "bystander" di Rissa (voce RULES_PENDING #12) — già
risolto il 2026-08-01 con "l'autocorrezione al turno successivo" — non
è affidabile: essendo `POKER_PHASE` ora una fase reale con decisioni
vere (non più un no-op istantaneo), la finestra in cui questo
sforamento resta osservabile e irrisolto si allunga a sufficienza da
essere colto dalle invarianti prima che il bystander riceva mai un
proprio round successivo. **Ripristinato** lo scarto automatico e
casuale per i bystander (`rules/brawl.py::
_enforce_bystander_hand_limit`, la stessa funzione rimossa in una
decisione precedente dello stesso giorno) come difesa primaria; le
esenzioni di `_check_hand_size` per `ACTION_PHASE`/`FINISHED` restano
come rete di sicurezza secondaria, non più la difesa principale per
questo caso.
Riferimento: RULES_CANONICAL.md §D2 (nuova sezione "Decisioni
(2026-08-01), Milestone 4 — Poker"); RULES_PENDING.md voci 13-15 (nuove,
Poker) e voce 12 (aggiornata).
Impatto: nuovo modulo `rules/poker.py`; `domain/state.py`
(`PokerMatchState.revealed_symbols_by_player_id`, nuovi campi
`PokerState.pending_bettor_*`/`resolving_match_index`/
`pending_jackpot_chips`); `domain/commands.py` (`LaunchPoker`,
`PlacePokerBet`, `PlayPokerCard`); `domain/events.py` (`PokerLaunched`,
`PokerBetsPlaced`, `PokerCardRevealed`, `PokerMatchResolved`);
`domain/enums.py` (`ActiveStep.WAITING_FOR_POKER_LAUNCH`);
`rules/turn_flow.py` (`_enter_grit_or_extra_action_offer` ora offre il
lancio Poker prima dell'azione extra da Link; `_enter_poker_phase`
delega a `rules/poker.py`; nuova funzione pubblica
`enter_link_extra_action_or_grit`); `application/legal_actions.py` e
`adapters/http/app.py` estesi con i 3 nuovi sotto-passi; `application/
game_service.py::advance()` non si ferma più non appena la fase non è
`ACTION_PHASE` (bug preesistente, esposto solo ora che `POKER_PHASE` può
davvero richiedere altre decisioni bot); `rules/brawl.py` (ripristinata
`_enforce_bystander_hand_limit`).

## 2026-08-01 — Bug pre-esistente (Milestone 3): pacchetto Compra Officer poteva superare il tetto di 3 nel Covo
Decisione: non un'ambiguità di regolamento ma un bug di implementazione
trovato dalla simulazione bot-only estesa a 1500 seed (1 occorrenza).
`rules/officers.py::_buy_officer_into_base` controlla correttamente il
tetto di 3 Cops/Feds nel Covo per **ogni singolo acquisto**, ma
`application/legal_actions.py::_buy_officer_options` non teneva conto
dell'effetto cumulativo di più acquisti "verso il proprio Covo" nello
stesso pacchetto (stessa Grinta): poteva offrire, ad esempio, 2 opzioni
del genere quando restava spazio per una sola, lasciando poi rifiutare
l'intero comando a metà pacchetto (con il primo acquisto altrimenti
legittimo perso insieme al secondo, dato che il comando è atomico).
Corretto limitando il numero di opzioni "verso il Covo" offerte alla
capacità residua effettiva; le opzioni "verso la mappa" (comprare un
Officer già nel Covo di qualcuno per piazzarlo) non hanno questo
vincolo e restano illimitate.
Riferimento: nessuna voce RULES_PENDING nuova (bug di implementazione,
non ambiguità di regolamento).
Impatto: `application/legal_actions.py::_buy_officer_options`;
`rules/officers.py::_officer_count_in_base` rinominata pubblica
(`officer_count_in_base`) per il riuso cross-modulo.

## 2026-08-01 — Correzione del game designer: innesco del lancio Poker legato all'action_type della carta
Decisione: il game designer ha corretto il timing del lancio Poker
implementato in "Milestone 4 (parte 2): implementazione del Poker"
(voce precedente): non è un'offerta indipendente prima della Grinta, ma
"il lancio è gratuito ma [solo] in un turno in cui il giocatore esegue
l'azione indicata sulla carta Preti". Tre domande di chiarimento hanno
confermato:
1. l'`action_type` della carta Gamble deve combaciare con l'`action_type`
   scelto dal giocatore per il round (non un lancio libero);
2. la scelta di lanciare o no va offerta subito dopo aver scelto il tipo
   di azione (`ChooseActionType`), prima della selezione dei bersagli —
   non più "prima della Grinta";
3. vale anche per l'azione extra da Link con lo stesso `action_type`
   della carta, non solo per l'azione principale del round (risposta
   esplicita, non quella raccomandata).
Riferimento: sostituisce il punto "Innesco del lancio" della voce
"Decisioni (2026-08-01), Milestone 4 — Poker" in `RULES_CANONICAL.md`.
Impatto: `domain/state.py` (`PlayerState.poker_launch_return_step`
sostituisce l'assunzione di un'offerta indipendente); `rules/economy.py`
(`_handle_choose_action_type` ora offre il lancio subito dopo aver
registrato l'`action_type` del round, se il giocatore ha una carta Preti
corrispondente); `rules/poker.py::_handle_launch_poker` (nuovo controllo
`card_action_type_mismatch`, ripristino dello step interrotto invece del
vecchio punto di offerta "prima della Grinta"); `rules/turn_flow.py`
(rimosso il pre-check di lancio da `_enter_grit_or_extra_action_offer`,
tornata alla forma originaria pre-Poker); `application/legal_actions.py`
e `application/game_service.py` (nuovo parametro `action_type_by_card_id`
propagato a `get_legal_decision` e ai `register_handlers` di `economy` e
`poker`); test aggiornati in `test_poker.py`, `test_turn_flow.py`,
`test_economy.py`, `test_brawl.py`, `test_extra_action.py`,
`test_http_app.py`.

Bug di implementazione trovato dalla prima simulazione bot-only a 2000
seed (198 occorrenze) e corretto nella stessa sessione: il nuovo punto
di offerta (fra `ChooseActionType` e la selezione dei bersagli) permette
al lancio di spostare una pedina IN_BASE del giocatore nel Den come
Gambler, che può far scendere le pedine disponibili sotto il
`grit_value` già impegnato per l'azione principale/extra appena scelta
(es. Piazzare Criminali con Grinta 2 ma un solo Criminal rimasto in
base). `application/legal_actions.py::_action_targets_decision`
restituiva comunque `min_selections=grit_value, can_pass=False` con
zero opzioni, un vicolo cieco (`RandomLegalBot` andava in crash tentando
un campione impossibile). Corretto rendendo la decisione dichiarabile
(`can_pass=True, min_selections=0`) quando le opzioni risultano vuote —
condizione che, per costruzione di `_options_for_action_type`, significa
sempre "il grit_value non è più soddisfacibile", mai una carenza
parziale — e aggiungendo il fallback a `PassOptionalStep` in
`build_command_from_selection` per le 6 decisioni di bersaglio-azione
(`place_criminal`, `move_criminal`, `buy_dope`, `sell_dope`,
`corrupt_officer`, `buy_officer`) quando la selezione è vuota, simmetrico
a quanto già esisteva per `choose_action_type`/
`spend_link_for_extra_action`. Riverificato con l'intera suite pytest
(128 test) e con due ulteriori simulazioni bot-only da 2000 seed, l'ultima
senza fallimenti.

## 2026-08-01 — Correzione del game designer: i 3 slot Link per Contact sono condivisi tra tutti i giocatori, non un tracciato per giocatore
Decisione: durante la pianificazione della Milestone 5 (Retate — serviva
sapere "chi ha il Link più alto ai Preti" per la scelta del primo
giocatore), il game designer ha corretto un'implementazione errata della
Milestone 3: i 3 slot di Link (livello 1/2/3) di ciascun Contact sono
**condivisi fra tutti e 4 i giocatori**, non un tracciato indipendente per
ciascun giocatore. Non possono mai esistere contemporaneamente due pedine
Link di due giocatori diversi allo stesso livello dello stesso Contact.
Segnale che aveva già anticipato la lettura corretta:
`rules/officers.py::_lowest_level_link_at_contact` (arresto Fed, §C5, già
Milestone 3) era scritta senza filtro per proprietario e senza gestione di
pareggio, assumendo implicitamente l'unicità globale dei livelli —
un'incoerenza tra moduli mai notata prima.
Riferimento: aggiorna la decisione (2026-07-30) in `RULES_CANONICAL.md`
§A5 sui 3 slot per Contact.
Impatto: `rules/links.py::contact_links` non filtra più per
`owner_player_id` (firma cambiata da `(state, player_id, contact_id)` a
`(state, contact_id)`); `insert_link`'s cascata ora scorre/espelle
occupanti di qualunque proprietario, restituendo un occupante espulso al
Covo del *proprio* proprietario (non di chi ha inserito il nuovo Link) —
gli eventi `LinkLevelChanged`/`LinkPawnReturnedToBase` ora riportano
`player_id` dell'occupante originale, non del giocatore che inserisce.
Nessun'altra chiamata a `contact_links` esisteva fuori da `links.py`; i 4
call site di `insert_link` (`brawl.py`, `jail.py`, `poker.py`,
`economy.py`) restano invariati nella firma. Aggiunti
`test_link_slots_are_shared_across_players_not_per_player` e
`test_insert_link_ejects_a_different_players_level_three_occupant_to_their_own_base`
in `test_links.py`; aggiornato l'unico test che chiamava la vecchia firma
di `contact_links`. Verificato con l'intera suite pytest (130 test), ruff,
mypy, e una simulazione bot-only da 2000 seed.

## 2026-08-02 — Milestone 5 (Stage 1): implementazione dei Jobs
Decisione: implementata la Stage 1 della Milestone 5 (CLAUDE.md §11.12):
rilevamento automatico del completamento dei Job, claim sulla board
condivisa, e banking del bonus (Skill = solo inventario, l'effetto
meccanico delle Skill è rimandato alla Stage 4). Tre decisioni raccolte
dal game designer durante la pianificazione (vedi `RULES_CANONICAL.md`
§A10): le 4 colonne bonus sono le stesse su ogni riga di Job (non una
tabella diversa per Job); i Job con 2 Contact lasciano scelta libera; la
Retata "comprato più Cops" conta anche i Fed (stesso contatore del Job
"Compra 1 Cop/Fed"); il Job "Abbi tutti i 10 Criminali fuori dal Covo"
conta qualsiasi pedina non IN_BASE; il Job "Abbi 3 Rats" è uno snapshot,
non un contatore cumulativo.
Riferimento: `RULES_CANONICAL.md` §A10 (decisioni 2026-08-01); punti 16 e
17 di `RULES_PENDING.md` per i due gap PROVVISORI trovati.
Impatto:
- `domain/state.py`: `PlayerState` guadagna 3 contatori cumulativi
  (`brawls_won_count`, `poker_matches_won_count`,
  `officers_bought_count`, incrementati rispettivamente in
  `rules/brawl.py::_finish_brawl`, `rules/poker.py::_resolve_match`,
  `rules/officers.py::_handle_buy_officer`); nuovi tipi `SkillsState`,
  `PendingJobRewardEntry`, `JobRewardProgress`; `GameState.skills` e
  `GameState.pending_job_reward`.
- `application/command_bus.py`: nuovo meccanismo generico
  `CommandBus.register_post_success_hook` — una lista di hook eseguiti
  dopo ogni `CommandSuccess`, ciascuno con la propria lista di eventi
  "fresca" (stesso schema di numerazione id di `event_utils.emit`
  concatenato in coda). Evita di dover inserire una chiamata al
  controllo dei Job sparsa in ognuno di `economy.py`/`movement.py`/
  `brawl.py`/`poker.py`/`officers.py`/`jail.py`.
- `domain/commands.py`: nuovo comando `ChooseJobReward`. Corretta anche
  la docstring di `LaunchPoker`, rimasta non aggiornata dalla correzione
  del timing del lancio Poker della sessione precedente.
- `domain/events.py`: nuovi eventi `JobCompleted`, `JobBonusClaimed`,
  `SkillDrawn`.
- `rules/jobs.py` (nuovo): predicati puri per i 9 tag di requisito già in
  `data/jobs.json`; `check_and_queue_completions` (hook post-successo,
  cicla finché una scansione completa non trova più nulla di nuovo,
  ordine deterministico player_order/tier, mette in pausa qualunque
  step interrotto in `GameState.pending_job_reward`); handler di
  `ChooseJobReward` (valida colonna libera e Contact, applica il bonus
  riusando `rules/links.insert_link` e `rules/economy.draw_card`).
- `application/legal_actions.py` e `application/game_service.py`: nuovo
  branch/decisione `WAITING_FOR_JOB_REWARD`, nuovo parametro `job_by_id`
  propagato a `get_legal_decision`.
- `application/views.py`: `PlayerGameView` guadagna `job_board`,
  `job_progress_by_player` (contenuto pubblico per CLAUDE.md §12: tutti
  i 9 Job sono comuni a ogni giocatore) e
  `remaining_skill_count_by_contact` (solo il conteggio, non gli id, dato
  che l'ordine di pesca resta informazione nascosta come i mazzi carte).
- `domain/invariants.py`: nuovo `_check_jobs_state` (nessuna cella board
  rivendicata due volte dallo stesso giocatore, i 15 Skill sempre
  partizionati senza duplicati fra mazzetti e giocatori, coerenza dei
  campi di ripresa di `pending_job_reward`); corretto anche
  `_check_link_levels`, rimasto con la vecchia chiave
  `(owner_player_id, contact_id, link_level)` dopo la correzione ai Link
  condivisi della voce precedente — non avrebbe mai rilevato la
  violazione che quella stessa correzione risolveva.
- `data/game_config.json`: nuova chiave `job_board_column_bonuses`.
- `backend/tests/unit/test_jobs.py` (nuovo, 21 test): un test per
  requisito, completamento→scarto→rivelazione, claim per ognuno dei 4
  bonus incluso esaurimento mazzetto Skill, completamenti multipli nello
  stesso comando, ripristino dopo interruzione, comando rifiutato senza
  mutazioni.

Due bug trovati da una simulazione bot-only a 2000 seed, corretti nella
stessa sessione:
1. Il bonus "2 carte" può far sforare il limite di 5 carte per un
   giocatore che non ha più un proprio round in questo turno di gioco
   per accorgersene (35 occorrenze) — lo stesso problema del "bystander"
   di Rissa (`RULES_PENDING.md` punto 12), ma più generale: il
   completamento di un Job può riguardare *qualunque* giocatore dopo
   *qualunque* comando, quindi non esiste un singolo `resume_player_id`
   con cui confrontare il destinatario. Corretto con
   `rules/jobs.py::_enforce_hand_limit_after_bonus`, che scarta sempre
   automaticamente e casualmente le carte in eccesso subito dopo il
   bonus, indipendentemente da fase o turno (`RULES_PENDING.md` punto 17).
2. Un bug nel test stesso (non nel motore): l'helper `_set_revealed_job`
   sovrascriveva il Job rivelato di un tier senza rimuoverlo anche dal
   mazzetto residuo di quel tier, permettendo allo stesso Job di
   ripresentarsi dopo il completamento — corretto nell'helper.

Verificato con l'intera suite pytest (151 test), ruff, mypy, e una
simulazione bot-only da 2000 seed senza fallimenti.

## 2026-08-02 — Milestone 5 (Stage 2): implementazione delle Retate
Decisione: implementata la Stage 2 della Milestone 5 (CLAUDE.md §11.13):
scelta del primo giocatore/squadre della Retata a Tip-off, valutazione
automatica a fine turno, macchiatura della REP (obbligatoria da Retata
persa e volontaria via `StainReputationForMoney`). Decisioni raccolte dal
game designer durante la pianificazione (vedi `RULES_CANONICAL.md` §D4/
§D5): scegliere il primo giocatore della Retata è la stessa scelta di
`first_player_id`, non un concetto separato; nessun tie-break serve più
per "Link più alto ai Preti" grazie alla correzione ai Link condivisi
(voce precedente); la Retata "comprato più Cops" conta anche i Fed.
Riferimento: `RULES_CANONICAL.md` §D4/§D5 (decisioni 2026-08-02).
Impatto:
- `domain/state.py`: `PlayerState.stain_offer_from_post_main` (mirror di
  `extra_action_from_post_main`).
- `domain/enums.py`: nuovo `ActiveStep.WAITING_FOR_STAIN_FOR_CASH_OFFER`
  (`WAITING_FOR_RAID_RESOLUTION` esisteva già, inutilizzato).
- `domain/commands.py`: `ChooseRaidFirstPlayer`, `StainReputationForMoney`.
  Corretta anche una docstring di `LaunchPoker` rimasta non aggiornata.
- `domain/events.py`: `RaidFirstPlayerChosen`, `RaidResolved`,
  `ReputationStained`.
- `rules/raids.py` (nuovo): funzione pura per ognuno dei 7
  `escape_criterion` di `data/raids.json`; `stain_one_clean_token`
  (helper condiviso fra Retata obbligatoria e macchiatura volontaria —
  gira il primo segnalino R pulito posseduto, la scelta è indifferente
  poiché ogni segnalino vale 2 punti allo stesso modo prima di essere
  macchiato); `player_can_stain_for_cash`; `resolve_raid` (somma per
  squadra, gestisce il pareggio esatto "cadono tutti e 4", applica
  `raid_stain_counts_by_occurrence[occorrenza]` alla squadra perdente).
  Legge `state.configuration["raid_escape_criterion_by_raid_card_id"]` e
  `["price_track_by_dope_type"]` invece di ricevere questi due lookup
  come parametri — l'alternativa avrebbe richiesto propagarli attraverso
  l'intera catena di avanzamento round di `rules/turn_flow.py` e
  `rules/poker.py` solo per raggiungere l'unico punto di chiamata a fine
  turno; sono invece popolati una volta sola in `rules/setup.py`, sullo
  stesso `state.configuration` che già porta tutto il resto del
  contenuto statico del gioco (l'intero `game_config.json`) a qualunque
  funzione delle regole senza bisogno di essere propagati esplicitamente.
- `rules/turn_flow.py`: `start_tip_off` ora mette in pausa
  (`WAITING_FOR_RAID_RESOLUTION`) quando un giocatore ha un Link ai
  Preti, altrimenti prosegue invariato; `_enter_grit_or_extra_action_offer`
  e `proceed_after_main_action` guadagnano un terzo controllo (stain-for-
  cash) prima dell'azione extra da Link, con lo stesso schema "prima/
  dopo" già esistente; `_enter_showdown_phase` chiama
  `raids.resolve_raid` prima di terminare il turno.
- `rules/setup.py`: `state.configuration` non è più una referenza diretta
  a `data.config` ma una copia con due chiavi derivate aggiunte
  (`raid_escape_criterion_by_raid_card_id`, `price_track_by_dope_type` —
  quest'ultima con le tuple convertite in liste per restare coerente col
  resto del contenuto, tutto originariamente JSON, quando la
  configurazione viene serializzata).
- `application/legal_actions.py`, `game_service.py`, `views.py`: nuovi
  branch/decisioni `WAITING_FOR_RAID_RESOLUTION`/
  `WAITING_FOR_STAIN_FOR_CASH_OFFER`; `GamePhase.TIP_OFF` aggiunta alla
  whitelist di fase di `get_legal_decision`/`_refresh_pending_decision`/
  `advance()`; `PlayerGameView` guadagna `raid_card_id` e
  `raid_lost_occurrences_count`.
- `domain/invariants.py`: nuovo controllo in `_check_jobs_state` — un
  segnalino macchiato deve sempre appartenere a un giocatore.
- `backend/tests/unit/test_raids.py` (nuovo, 19 test): le 7 funzioni
  criterio, split di squadra e pareggio esatto, macchiatura parziale per
  segnalini insufficienti, scaling per occorrenza, la pausa a Tip-off con
  fallback "nessun Link ai Preti", `StainReputationForMoney` in entrambe
  le direzioni.

Verificato con l'intera suite pytest (170 test), ruff, mypy, e una
simulazione bot-only da 2000 seed senza fallimenti (nessun bug trovato
dalla simulazione questa volta).

## 2026-08-02 — Milestone 5 (Stage 3): implementazione del punteggio finale
Decisione: implementata la Stage 3 della Milestone 5 (CLAUDE.md §11.14):
calcolo automatico del `FinalScoreBreakdown` per ogni giocatore a fine
partita, attraversando la fase `END_GAME_SCORING` prima di `FINISHED`.
Riferimento: `RULES_CANONICAL.md` §D6 (decisioni implementative 2026-08-02).
Impatto:
- `domain/scoring.py` (nuovo): `FinalScoreBreakdown` (7 campi esatti di
  CLAUDE.md §11.14 più `total_points`), `FinalScoreState`
  (breakdown per giocatore + `winner_ids`, >1 elemento = vittoria
  condivisa). `GameState.final_score` passa da placeholder
  `dict[str, Any] | None` al tipo tipizzato.
- `domain/events.py`: nuovo `FinalScoreCalculated`; `GameFinished`
  guadagna `winner_ids`.
- `rules/scoring.py` (nuovo): `compute_final_score` — punti tracciato
  denaro (pareggi prendono il valore della posizione più bassa tra
  quelle occupate, verificato contro l'esempio esatto di §D6); punti REP
  (2×pulite + 1×macchiate, scansione di `state.jobs.board`); maggioranza
  per Contact (peso Criminal/Link da `game_config.json`, pareggio =
  nessun punto — test `test_contact_majority_tie_awards_no_point`
  nominato esattamente da CLAUDE.md §17.2); punti Chips
  (`poker_chip_count // 3`); punti Skill (`len(skill_ids)`); somma;
  vincitore/i per punti totali, poi conteggio REP pulite (non i punti,
  campo separato `tie_break_clean_reputation`), poi vittoria condivisa.
- `rules/turn_flow.py::_end_turn`: quando `turn_index` raggiunge il
  limite configurato, passa per `END_GAME_SCORING` (calcola
  `final_score`, emette `FinalScoreCalculated`) prima di `FINISHED`
  (`GameFinished` ora con `winner_ids`) — nessuna decisione del
  giocatore in questa fase, come l'attuale `SHOWDOWN_PHASE` automatica.
- `backend/tests/unit/test_scoring.py` (nuovo, 11 test): tabella
  tracciato denaro dall'esempio esatto di §D6 (pareggio singolo e
  pareggio a 4), maggioranza in parità e a leader singolo (Criminal vs
  Link), aritmetica chips/skill, cascata di tie-break (punti pari →
  conteggio REP pulite → vittoria condivisa). Estesi
  `test_turn_flow.py::test_full_game_reaches_finished_deterministically`
  e i due test bot-only di `test_game_service.py` per asserire
  `final_score is not None` e `len(winner_ids) >= 1`.

Verificato con l'intera suite pytest (181 test), ruff, mypy, e una
simulazione bot-only da 2000 seed senza fallimenti.

## 2026-08-02 — Milestone 5 (Stage 4a): effetti Skill "+1 Grinta sempre"
Decisione: implementata la prima sotto-parte della Stage 4 (i 15 effetti
meccanici delle Skill): il bundle "+1 Grinta sempre" (Artisti-1,
Studenti-1, Manager-1, Politici-1). Le altre 11 Skill restano solo
inventario (già banchificabili dalla Stage 1) fino alle prossime
sotto-parti.
Riferimento: `RULES_CANONICAL.md` §A10 (decisioni implementative
2026-08-02).
Impatto:
- `data/skills.json`: nuovo campo `effect` per ciascuna delle 15 Skill
  (schema dato-guidato, non hardcodato — CLAUDE.md §3.5); solo le 4 Skill
  di questa sotto-parte hanno un `effect.type` effettivamente consumato
  dal motore per ora, le altre 11 sono già presenti nel dato ma non
  ancora lette da nessun modulo.
- `domain/content.py::SkillDefinition` guadagna il campo `effect: dict`.
- `rules/setup.py`: nuova chiave `state.configuration["skill_effect_by_id"]`
  (stesso pattern già usato per i criteri Retata e i price track — evita
  di dover propagare i dati delle Skill attraverso l'intera catena di
  comandi).
- `rules/skills.py` (nuovo): `effective_action_count(state, player,
  action_type, base_count)`, usata identicamente da
  `application/legal_actions.py` (generazione opzioni, 3 punti:
  `_choose_action_type_decision`, `_action_targets_decision`,
  `_choose_extra_action_link_decision`) e da
  `rules/economy.py::_validate_action_targets` (validazione, condivisa
  anche da `rules/officers.py` tramite l'alias `validate_action_targets`
  già esistente) — le due parti calcolano sempre lo stesso numero.
- `backend/tests/unit/test_skills.py` (nuovo, 9 test): la funzione pura
  per ciascuna delle 4 Skill, specificità per action_type, cumulo di più
  Skill (sintetico, dato che nessuna coppia reale si sovrappone), ciclo
  completo generazione-opzioni + validazione per Manager-1 (accetta il
  conteggio potenziato, rifiuta quello base).

Bug pre-esistente trovato (non causato da questa sotto-parte, ma
scoperto dalla stessa simulazione/suite): `choose_job_reward`,
`choose_raid_first_player` e `stain_reputation_for_money` — introdotti
rispettivamente nelle Stage 1 e 2 — non erano mai stati aggiunti né
all'adapter HTTP (`adapters/http/app.py`, mancava la conversione da
payload JSON a comando per tutti e tre) né all'helper generico di guida
della partita in `tests/integration/test_http_app.py`. Il gap è rimasto
latente perché nessun seed precedente aveva mai attraversato quei punti
di decisione entro i limiti di passi dei test esistenti; la simulazione
di questa sotto-parte lo ha reso visibile per la prima volta tramite
`test_full_game_completes_through_http`. Corretto in entrambi i punti.

Verificato con l'intera suite pytest (190 test), ruff, mypy, e una
simulazione bot-only da 2000 seed senza fallimenti.
