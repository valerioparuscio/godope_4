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

## 2026-08-02 — Correzione del game designer: la Grinta è un massimo, non un numero esatto
Decisione: durante la discussione sulle Skill "+1 Grinta sempre", il game
designer ha corretto un comportamento implementato erroneamente fin dalla
Milestone 2: il valore della Grinta (eventualmente potenziato da una
Skill) indica il **massimo** di pedine che possono eseguire un'azione in
un round, non un numero esatto obbligatorio. Un giocatore con Grinta 3
può far agire anche solo 1 o 2 pedine, mai zero (rifiutare l'azione per
intero, prima di scegliere il tipo, resta `PassOptionalStep`). Vale per
tutte e 6 le azioni (Piazza/Muovi/Compra/Vendi/Corrompi/Compra Officer)
e per l'azione extra da Link.
Riferimento: aggiorna la decisione (2026-07-30) in `RULES_CANONICAL.md`
§B2 sulla meccanica della Grinta, e la voce Stage 4a di questo changelog
sull'effetto "+1 Grinta sempre" (ora anch'esso un massimo, non un valore
esatto).
Impatto:
- `application/legal_actions.py::_options_for_action_type` cambia
  contratto: da `tuple[DecisionOption, ...] | None` a
  `tuple[tuple[DecisionOption, ...], int] | None`, dove l'`int` è il
  massimo bersagli effettivamente selezionabile (1..grit_value) — `None`
  resta riservato al caso "zero bersagli raggiungibili", non più "meno
  di grit_value". Nuovo helper `_max_affordable_prefix_count` (prefisso
  più economico affordable, condiviso da `_buy_dope_options` e
  `_corrupt_officer_options`, i due generatori con costo variabile per
  candidato). Le 6 funzioni `_place_criminal_options`,
  `_move_criminal_options`, `_buy_dope_options`, `_sell_dope_options`,
  `_corrupt_officer_options`, `_buy_officer_options` sostituiscono il
  controllo "return None se meno di grit_value" con il calcolo del
  massimo realmente raggiungibile (per disponibilità di pedine e/o
  denaro), restituendolo insieme alle opzioni. `_action_targets_decision`
  espone `min_selections=1, max_selections=<quel massimo>` invece di
  `min_selections=max_selections=grit_value`.
  `_choose_action_type_decision`/`_choose_extra_action_link_decision`
  restano invariate (controllano solo `is not None`, compatibile col
  nuovo contratto).
- `rules/economy.py::_validate_action_targets`: il controllo passa da
  `target_count != expected_count` a `target_count < 1 or target_count >
  max_count` (condiviso da `rules/officers.py` tramite l'alias
  `validate_action_targets` già esistente, nessuna modifica lì
  necessaria). Il dettaglio dell'errore `wrong_target_count` cambia da
  `{"expected": N}` a `{"min": 1, "max": N}`.
- Test riscritti in `test_legal_actions.py`
  (`test_place_criminal_targets_allow_up_to_grit_value`, rinominato da
  "...require_exactly...") e `test_skills.py` (3 test aggiornati/nuovi:
  richiede solo il massimo aggiornato non più esatto, accetta un
  conteggio inferiore al massimo potenziato, rifiuta un conteggio
  superiore al massimo, rifiuta zero bersagli).

Verificato con l'intera suite pytest (200 test), ruff, mypy, e una
simulazione bot-only da 2000 seed senza fallimenti.

## 2026-08-02 — Milestone 5 Stage 4c: le 7 Skill "meccaniche singole"
Decisione: ultima sotto-parte della Milestone 5 Stage 4 (§A10). 6 delle 7
Skill rimanenti implementate; Manager-3 resta bloccato da un prerequisito
mancante (vedi sotto). Le due Skill "sostituzione" (Artisti-3/Studenti-3)
usano una scelta PROVVISORIA per la pedina del Covo e il suo fallback,
tracciata in `RULES_PENDING.md` #19.
Riferimento: `RULES_CANONICAL.md` §A10 ("Decisioni implementative
(2026-08-02), Milestone 5 Stage 4c"), `RULES_PENDING.md` #18–20.
Impatto:
- **Studenti-2** ("+1 Pistola in Rissa"): `rules/skills.py::
  extra_gun_bonus`. `rules/brawl.py` guadagna l'helper condiviso
  `_effective_guns` (sostituisce l'accesso diretto a
  `gun_count_by_card_id` sia in `_force_by_player` sia in
  `_guns_played`/`_break_tie_for_winner`, che ora prendono `state` come
  parametro in più) — il bonus si applica solo a un partecipante che ha
  effettivamente giocato una carta (PROVVISORIO, punto 20).
- **Manager-3** ("Stonk 2 volte"): non implementato. Il meccanismo di
  base Marketing/Stonk non esiste nel motore (`RULES_PENDING.md` #18) —
  prerequisito mancante, non un'ambiguità di regola.
- **Preti-2** ("incassi 6 dollari"): `rules/skills.py::
  poker_launch_cashout(state, player, base_amount)` sostituisce
  l'incasso base in `rules/poker.py::_handle_launch_poker`.
- **Preti-3** ("carte Gamble su qualunque azione"): `rules/skills.py::
  can_launch_poker_any_action`, letta sia da
  `rules/economy.py::_player_can_launch_poker_for_action` (lato offerta)
  sia da `rules/poker.py::_handle_launch_poker` (lato validazione del
  comando) per bypassare il controllo §D2 sull'`action_type`.
- **Politici-3** ("2 Ganci a turno"): `PlayerState.extra_action_used_this_turn`
  (bool) rinominato `extra_actions_used_this_turn` (int) — tutti e 5 i
  punti di lettura/scrittura in `rules/turn_flow.py` aggiornati a
  confrontarsi con `rules/skills.py::max_link_extra_actions_per_turn`
  (default 1, 2 con questa Skill) invece che con un bool fisso. 2 test
  esistenti (`test_turn_flow.py`, `test_extra_action.py`) aggiornati al
  nuovo nome/tipo di campo.
- **Artisti-3** ("mandi dal Covo sul Link" alla vendita):
  `rules/skills.py::sell_link_from_base`. `rules/economy.py::
  _handle_sell_dope` ramifica: con la Skill, una pedina fresca `IN_BASE`
  (stesso criterio deterministico di `rules/poker.py`'s Gambler fresco)
  diventa il Link e la pedina che ha venduto resta un Criminal sul
  campo; senza, comportamento invariato (la pedina venditrice evolve,
  come da Milestone 2).
- **Studenti-3** ("mandi dal Covo sul Link" vincendo una Rissa):
  `rules/skills.py::brawl_win_link_from_base`. `rules/brawl.py` guadagna
  `_auto_apply_brawl_link_from_base`, chiamata automaticamente dalla coda
  di `_handle_choose_brawl_loser_reward` quando l'ultimo sconfitto è
  stato risolto — per chi possiede questa Skill, l'evoluzione del Link
  diventa **automatica** (nessuna pedina rimossa dal Quartiere,
  `ChooseBrawlLinkEvolution` non viene più offerta); senza la Skill, il
  vincitore sceglie ancora come da Milestone 4.
- `backend/tests/unit/test_skills.py`: 19 nuovi test (helper di supporto
  per Rissa/Poker/azione extra replicati localmente, stesso stile di
  duplicazione già usato tra `test_brawl.py`/`test_poker.py`/
  `test_extra_action.py`) — funzione pura + comportamento end-to-end per
  ciascuna delle 6 Skill implementate.

Verificato con l'intera suite pytest (219 test), ruff, mypy, e una
simulazione bot-only da 2000 seed senza fallimenti.

## 2026-08-02 — Milestone 5 Stage 4c-bis: Marketing/Stonk (nuovo meccanismo) + Manager-3
Decisione: prima di committare la Stage 4c, il game designer ha chiesto di
implementare il meccanismo di base Marketing/Stonk (§D3), rimasto bloccato
(vedi voce Stage 4c sopra), così Manager-3 potesse essere completato nello
stesso giro. Pianificato con `EnterPlanMode`/`ExitPlanMode` prima
dell'implementazione, data l'ampiezza (nuovo comando/evento/stato, non solo
un effetto Skill).
Riferimento: `RULES_CANONICAL.md` §D3 ("Decisioni implementative
(2026-08-02), Milestone 5 Stage 4c-bis"), §A10 (Manager-3 aggiornato),
`RULES_PENDING.md` #18 (RISOLTO) e #21 (nuovo, PROVVISORIO).
Impatto:
- **Scoperta chiave:** `domain/enums.py`'s `ActiveStep.WAITING_FOR_CARD_USAGE`
  esisteva già (elencato anche in CLAUDE.md §8) ma senza alcun riferimento
  nel backend — uno slot riservato e mai usato, corrispondente esattamente
  a "gioca una o più carte... per fare marketing" (§B2).
- **Interpretazione "prima o dopo lo svolgimento dell'azione"**
  (PROVVISORIO, punto 21): invece di spezzare `BuyDope`/`SellDope` in
  selezione-pacchetto + risoluzione-differita (molto più invasivo), solo
  lo step di prezzo automatico di fine pacchetto (`price_step_totals`,
  già accumulato ma applicato subito) viene differito di un passo. Nuovo
  `PlayerState.pending_marketing_price_steps: dict[DopeType, int]`
  (segno già applicato, stesso stile di persistenza di
  `BaseInventory.dope_counts`).
- `rules/economy.py::_finish_buy_or_sell_package` (nuovo, sostituisce la
  chiamata diretta a `_apply_price_step` + `finish_action_or_extra` in
  coda a `_handle_buy_dope`/`_handle_sell_dope`): se il giocatore ha in
  mano una carta con `stonk_count > 0`, differisce lo step e passa a
  `WAITING_FOR_CARD_USAGE`; altrimenti comportamento invariato (nessun
  cambio osservabile per un giocatore senza carte idonee — la stragrande
  maggioranza dei test esistenti).
- `domain/commands.py::PlayMarketingCard(card_id, allocations: tuple[
  tuple[DopeType, int, bool], ...])` (dope_type, delta ∈{-1,+1},
  apply_before) — `PassOptionalStep` copre il rifiuto.
  `domain/events.py::MarketingCardPlayed`.
- `rules/economy.py::_handle_play_marketing_card` (nuovo): valida carta/
  conteggio Stonk/merci trattate/delta, scarta la carta, applica gli
  Stonk "prima", poi lo step differito, poi gli Stonk "dopo" — per un
  giocatore con Manager-3 (`rules/skills.py::
  marketing_applies_both_timings`), ogni allocazione si applica a
  **entrambi** i checkpoint indipendentemente dal suo `apply_before`.
- `rules/turn_flow.py`: nuovo branch `WAITING_FOR_CARD_USAGE` nel
  gestore di `PassOptionalStep` (`_apply_pending_marketing_price_steps`,
  duplica localmente la matematica di `rules/economy.py::
  _apply_price_step` invece di importarla — `economy.py` già importa
  `turn_flow`, quindi l'import inverso creerebbe un ciclo).
  `register_handlers` guadagna un parametro opzionale `price_tracks`.
- `application/legal_actions.py::_marketing_decision` (nuovo, per
  `WAITING_FOR_CARD_USAGE`): con più carte idonee in mano, offre solo le
  allocazioni di quella con più Stonk (PROVVISORIO, punto 21) — ogni
  combinazione (merce, direzione, timing) duplicata fino a `stonk_count`
  opzioni, `min_selections=0, can_pass=True`. Con Manager-3 la dimensione
  "timing" viene omessa dalle opzioni (il campo `apply_before` non è una
  scelta significativa in quel caso).
- Wiring end-to-end (facile da dimenticare, come già successo con Stage
  1-2): `application/game_service.py` costruisce
  `stonk_count_by_card_id` e lo passa sia a `economy.register_handlers`
  sia a `get_legal_decision`; `adapters/http/app.py` e
  `tests/integration/test_http_app.py` guadagnano il branch
  `play_marketing_card`.
- Test: `backend/tests/unit/test_marketing.py` (nuovo, 8 test) — nessuna
  offerta senza carta idonea, differimento con carta idonea, timing
  prima/dopo osservabile tramite il clamp del price track (le due
  applicazioni sono altrimenti commutative), rifiuto merce non trattata,
  rifiuto oltre il conteggio Stonk della carta, rifiuto applica comunque
  lo step differito, offerta della decisione fino al conteggio Stonk.
  `test_skills.py`: 3 nuovi test per Manager-3 (funzione pura,
  raddoppio end-to-end).

Bug pre-esistente trovato dalla simulazione bot-only (non causato da
questa sotto-parte, ma reso visibile per la prima volta dallo
spostamento della sequenza RNG dei bot che i nuovi step di Marketing
comportano): `application/legal_actions.py::_brawl_card_decision`
impostava `max_selections=1` incondizionatamente, anche quando
`player.hand_card_ids` è vuoto (0 opzioni) — `RandomLegalBot`'s ramo
generico (`random_legal.py`) può allora estrarre `count=1` e chiamare
`rng.sample([], 1)`, che solleva `ValueError`. Corretto con lo stesso
pattern "nessuna opzione, nessuna selezione possibile" già usato da
`_launch_poker_decision`/`_brawl_relocation_decision`:
`max_selections=1 if options else 0`.

Verificato con l'intera suite pytest (230 test), ruff, mypy, e una
simulazione bot-only da 2000 seed senza fallimenti.

## 2026-08-02 — Risoluzione in blocco dei punti PROVISIONAL/da confermare
Decisione: dopo la chiusura della Milestone 5, il game designer ha rivisto
in un colpo solo tutti i punti ancora aperti in `RULES_PENDING.md`
(eccetto #1 dataset carte e #9 "sbirciare una Retata", che restano da
fornire/implementare). La maggioranza erano semplici conferme del
comportamento già implementato (punti 4, 6, 7, 8, 10, 11, 14, 16 —
nessuna modifica al codice, solo lo stato in `RULES_PENDING.md` passa a
RISOLTO); i seguenti hanno invece richiesto correzioni reali.
Riferimento: `RULES_PENDING.md` (tutte le voci ora RISOLTO tranne #1, #9,
e la sotto-voce "quale carta" del #21), `RULES_CANONICAL.md` §A6, §A10,
§C4, §D2, §D3, §F2.

**#2 — Adiacenza Q3↔Q6:** confermate **non adiacenti** (l'asimmetria
originaria era un errore nella lista di Q6, non un'omissione in quella di
Q3). `data/board.json` corretto rimuovendo Q3 dagli adiacenti di Q6
(invece di aggiungere Q6 a quelli di Q3, come fatto provvisoriamente in
precedenza).

**#3 — Rimozione Fed da Spot "senza Merci e senza Ganci" (nuova
implementazione):** `rules/links.py::check_spot_fed_removal_for_contact`
(nuovo) — "senza Ganci" = il Contact dello Spot non ha più nessun Link, a
nessun livello, di nessun giocatore. Chiamata solo dai punti dove un Link
*scompare* (`rules/officers.py`'s arresto Fed del Link di livello minore;
`rules/turn_flow.py`'s ritorno al Covo del Link speso per l'azione
extra) — mai dal punto che svuota lo Spot vendendo
(`rules/economy.py::_clear_spot_and_spawn_fed`), che altrimenti
annullerebbe il Fed appena creato nello stesso istante in cui entra
(nota già presente nel modulo fin da Milestone 2). Vive in `links.py`
(non `economy.py`) perché deve essere chiamata sia da `economy.py` sia da
`turn_flow.py` — che già importa `economy.py`, quindi l'import inverso
creerebbe un ciclo; entrambi importano già `links.py`. Test:
`test_officers.py` (2, arresto che rimuove/non rimuove il Fed a seconda
che resti un altro Link), `test_extra_action.py` (1, Link speso per
l'azione extra).

**#5 — Evoluzione a Link su vendita singola (corretto — era stato
implementato sbagliato in Milestone 3):** torna a essere una scelta
SI/NO del giocatore, come dice §A5 "può evolversi" — non più automatica.
Nuovo comando `EvolveSaleLink(evolve: bool)` e step `ActiveStep.
WAITING_FOR_LINK_EVOLUTION_CHOICE`; nuovo `PendingSaleLinkEvolution`
(`domain/state.py`) in coda su `PlayerState.
pending_sale_link_evolutions` per gestire più Spot da 1 unità nello
stesso pacchetto. La vendita a pacchetto (2-3 unità allo stesso Spot)
resta automatica (§C4 "si prende", non contestato). `rules/economy.py::
_handle_sell_dope` ora smista per Spot: 1 venditore -> accoda la scelta;
2-3 venditori -> `_evolve_sale_link` immediato (stesso helper, estratto
dal vecchio corpo inline). Lo step di prezzo del pacchetto (e l'eventuale
offerta Marketing "dopo") aspetta che la coda si svuoti
(`player.pending_sale_price_steps`, `_handle_evolve_sale_link`'s coda).

**#12/#17 — Sforamento 5 carte fuori dal proprio turno (corretto — lo
scarto automatico introdotto in Milestone 4/5 non doveva esistere):** il
game designer ha confermato che il check delle 5 carte avviene **solo**
alla fine del proprio turno; una carta ricevuta durante il turno di un
altro giocatore si tiene senza scartare, anche oltre il limite, finché
non arriva la fine del proprio turno — anche a costo di restarci sopra
per più fasi/turni. Rimossi `rules/brawl.py::
_enforce_bystander_hand_limit` e `rules/jobs.py::
_enforce_hand_limit_after_bonus` (coi rispettivi param `card_contact_by_id`
ormai inutili su `_handle_choose_brawl_loser_reward`,
`_handle_choose_brawl_relocation_destination`, `jobs.register_handlers`/
`_handle_choose_job_reward` — rimossi anche quelli). Rimosso
`domain/invariants.py::_check_hand_size`: non esiste più un punto di
campionamento affidabile dove "tutti devono avere ≤5 carte" valga sempre
(uno sforamento legittimo può ora persistere attraverso più fasi).

**#13 — Poker "5 uguali" (corretto — la regola PROVVISORIA non serviva,
il caso è impossibile):** il banco non ha mai 3 simboli identici, quindi
nessuna mano di 5 simboli può mai essere monocolore. Rimosso il ramo
`shape_counts == [5]` da `rules/poker.py::_hand_score` (ora parte
dell'`AssertionError` finale, "non dovrebbe mai accadere"); la categoria
di vertice è sempre "5 diversi", rinominata `"five_different"` (da
`"five_same_or_diff"`) in `data/game_config.json`'s `poker_rank_order` e
nel codice. 4 test in `test_poker.py` che costruivano banchi a 3 simboli
identici e *arrivavano alla risoluzione della mano* sono stati corretti a
banchi validi (2+1) con lo stesso esito di vittoria/parità atteso; altri
4 che costruiscono banchi a 3 simboli identici ma non raggiungono mai
`_hand_score` (test di limite di lancio/puntata) sono stati lasciati
invariati.

**#15 — Arresto Gambler sconfitto con Jail piena (nessuna modifica al
codice — era già corretto):** confermato che la Jail non è mai
realmente piena al momento di un arresto: il 6° Rat innesca l'Evasione
immediatamente (`rules/jail.py::arrest_pawn`), svuotando tutti gli slot
prima che quello stesso arresto ritorni. Il ciclo per-sconfitto in
`rules/poker.py::_resolve_match` ricontrollava già `jail.has_free_rat_slot`
a ogni singolo arresto (non una volta sola prima del ciclo), quindi lo
scenario "Jail piena blocca un arresto" non si presenta mai nella
pratica. Aggiunto un test di regressione dedicato con 3 puntatori (1
vincitore + 2 sconfitti) e Jail già a 5: verifica che il primo arresto
inneschi l'Evasione (quella pedina evolve in Link Politici, non resta
Rat) e il secondo finisca pulito nello slot 0 ormai vuoto.

**#19 — Artisti-3/Studenti-3, fallback senza pedina nel Covo (corretto):**
invece di saltare silenziosamente l'evoluzione, si manda dal Quartiere
come di consueto (come se il giocatore non avesse la Skill). Per
Artisti-3, `_evolve_sale_link` ricade nel ramo normale quando `from_base`
è vero ma non c'è pedina libera. Per Studenti-3,
`_auto_apply_brawl_link_from_base` ora lascia `progress.
link_evolution_done` `False` in quel caso, il che fa scattare
naturalmente la normale scelta del vincitore (`ChooseBrawlLinkEvolution`)
al posto dell'automatismo.

**#20 — Studenti-2, ambito del bonus (corretto):** si applica **sempre**,
anche senza carta giocata ("tutti i presenti nel quartiere partecipano
sempre, anche se non giocano carte"). `rules/brawl.py::_force_by_player`
somma il bonus direttamente alla Forza base di ogni partecipante con la
Skill, invece di agganciarlo al meccanismo di assegnazione Pistole di una
carta giocata — `_effective_guns`/`_guns_played` tornano a essere puro
conteggio Pistole della carta, senza logica Skill al loro interno.

**#21 — Marketing/Stonk, semantica "prima/dopo" (redesign — la prima
implementazione aveva frainteso il riferimento):** "prima o dopo lo
svolgimento dell'azione" si riferisce all'**intera azione** (l'intero
pacchetto Buy/Sell, incluso il suo step di prezzo automatico), non al
solo step automatico come implementato la prima volta. Impatto:
- Marketing "prima" è ora offerto subito dopo `ChooseActionType`, prima
  della selezione bersagli — qualunque tipo di Merce (il pacchetto non
  esiste ancora), analogo al lancio Poker (`_handle_choose_action_type`,
  nuovo `elif` dopo il check Poker — PROVVISORIO: un giocatore idoneo per
  entrambi nello stesso round ottiene solo l'offerta Poker, mai
  entrambe, per evitare di dover incatenare due offerte "prima" separate).
  `player.marketing_pre_return_step`/`marketing_offer_is_pre` (nuovi,
  `domain/state.py`) mirano `poker_launch_return_step`.
- Il pacchetto si risolve normalmente e il suo step di prezzo automatico
  si applica **subito** (non più differito) — `_finish_buy_or_sell_package`
  semplificata.
- Marketing "dopo" resta offerto in coda al pacchetto, ristretto alle
  Merci trattate (`player.marketing_eligible_dope_types`, nuovo).
- Un giocatore normale ottiene l'uno o l'altro, mai entrambi. Manager-3
  (già implementato al punto #18) ora replica automaticamente "dopo" le
  stesse allocazioni fatte "prima" (`player.marketing_pre_allocations`,
  nuovo) invece di raddoppiare l'effetto di ogni singolo Stonk con un
  flag `apply_before` per allocazione — `PlayMarketingCard.allocations`
  perde quindi il terzo campo (`tuple[DopeType, int, bool]` ->
  `tuple[DopeType, int]`); `MarketingCardPlayed` guadagna `is_pre: bool`.
- `application/legal_actions.py::_marketing_decision` semplificata di
  conseguenza (niente più dimensione "timing" nelle opzioni).
- `rules/turn_flow.py::_handle_pass_optional_step` torna a non avere
  bisogno di `price_tracks` (nessuno step differito da applicare su
  rifiuto) — `register_handlers` e la sua firma tornano più semplici.
- `test_marketing.py` riscritto da zero per il nuovo flusso; nuovo test
  Manager-3 in `test_skills.py` che verifica la replica automatica.

Verificato con l'intera suite pytest (237 test), ruff, mypy, e una
simulazione bot-only da 2000 seed senza fallimenti.

## 2026-08-02 — Milestone 6 (parziale): salvataggio/caricamento + tool di simulazione massiva
Decisione: implementata la parte di Milestone 6 (CLAUDE.md §16, §17.3, §5)
relativa a salvataggio/caricamento di una partita e al tool committato di
simulazione bot-only, senza toccare alcuna regola di gioco. Il Replay vero
e proprio (ricostruzione da configurazione iniziale + seed + sequenza di
comandi, non da uno snapshot) resta esplicitamente fuori da questo giro.
Riferimento: nessun punto di `RULES_PENDING.md` coinvolto — puro lavoro di
infrastruttura, non di regolamento.
Impatto:
- `domain/state.py`: `GameState` guadagna `seed: int` (impostato una sola
  volta alla creazione in `rules/setup.py::create_initial_state`, mai
  mutato) — necessario perché `rng_state` cattura solo la posizione
  *corrente* della sequenza deterministica, non il seed originale da cui
  è partita, e un futuro Replay "da zero" ne avrà bisogno. Nessun bump di
  `schema_version`: non esistono salvataggi precedenti da migrare.
- `domain/errors.py`: nuovo `SaveFormatError`, sullo stesso precedente già
  in uso per `InvariantViolation` ("solleva, non restituire un
  DomainError" per un problema di dati/programmazione, non una mossa
  illegale ordinaria).
- `application/save_load.py` (nuovo): involucro sottile sopra
  `domain/serialization.py::to_json_dict`/`from_json_dict`, già generico e
  già testato per l'intero `GameState` — questo modulo si occupa solo
  della busta stabile del salvataggio (`schema_version`, `rules_version`,
  `snapshot`) e dell'I/O su file. `expected_schema_version` è passato
  esplicitamente dal chiamante (`GameData.config["schema_version"]`)
  invece di essere una costante di modulo, per non far dipendere questo
  modulo da `data_loader.py`.
- `adapters/http/schemas.py` e `adapters/http/app.py`: nuove route
  `GET /api/v1/games/{game_id}/save` e `POST /api/v1/games/load`, stesso
  stile delle route esistenti. Il caricamento non richiede di richiamare
  `create_game` né di ricalcolare la decisione pendente: `GameState` la
  include già e il round-trip JSON è provato esatto
  (`test_serialization.py::test_game_state_full_round_trip`), quindi lo
  stato ricaricato è bit-per-bit equivalente a quello salvato.
- `backend/pyproject.toml`: aggiunta `addopts = "--basetemp=.pytest_tmp"`
  a `[tool.pytest.ini_options]` — il primo test di questa sessione a usare
  la fixture `tmp_path` ha rivelato che `%TEMP%\pytest-of-VALE` non è
  scrivibile su questa macchina (problema di permessi del sistema
  operativo, non del codice); la directory `.pytest_tmp` locale al
  progetto, già ignorata da git come `.pytest_cache/`, aggira il problema.
- `tools/run_full_test_game.py` (nuovo, elencato da CLAUDE.md §5 e mai
  creato finora): CLI che formalizza lo script ad-hoc di simulazione già
  usato ripetutamente in questa sessione — argomenti `--seeds`,
  `--max-steps`, `--data-dir`, `--failures-dir`; gira N partite bot-only
  (tutti i seat, incluso quello umano, pilotati da `RandomLegalBot`, dato
  che lo scopo è scovare bug del motore) fino a `FINISHED` o al limite di
  passi, chiama `validate_invariants` dopo ogni comando accettato, e per
  ogni partita fallita scrive lo stato al momento del fallimento con
  `save_load.save_to_file` sotto `debug_failures/` (nuova voce in
  `.gitignore`) per riproducibilità immediata.
- Test: `backend/tests/unit/test_save_load.py` (nuovo, 5 test — round-trip
  via dict e via file, `SaveFormatError` su versione non corrispondente e
  su chiavi mancanti); `backend/tests/integration/test_http_app.py` (3
  nuovi test — save poi load via le route HTTP con vista identica, la
  partita ricaricata riceve ancora comandi, mismatch di schema_version
  rifiutato con 400).

Verificato con l'intera suite pytest (245 test), ruff, mypy, e
`tools/run_full_test_game.py --seeds 1-2000 --max-steps 4000` (2000/2000
partite completate senza fallimenti).

## 2026-08-03 — Correzione del game designer: un'azione base non può ripetersi nello stesso turno
Decisione: nei 3 round di un turno, l'azione base scelta con un segnalino
Grinta deve essere diversa in ciascun round — mai la stessa azione due
volte nello stesso turno (es. "piazza" al round 1 e di nuovo "piazza" al
round 3 non è consentito). Segnalato dal game designer durante una
sessione di test del nuovo frontend: giocando una partita reale si è
notato che il motore non applicava affatto questo vincolo. L'azione extra
da Link resta un meccanismo separato e non è soggetta a questa regola —
può liberamente ripetere un'azione già usata nello stesso turno.
Riferimento: `RULES_CANONICAL.md` §B2.
Impatto:
- `domain/state.py`: nuovo campo `PlayerState.action_types_used_this_turn:
  list[ActionType]`.
- `rules/turn_flow.py::_start_action_phase`: azzerato a inizio turno,
  insieme agli altri contatori "this_turn" già esistenti
  (`moved_pawn_ids_this_turn`, `extra_actions_used_this_turn`).
- `rules/economy.py::_handle_choose_action_type`: nuovo ramo `elif` che
  rifiuta (`action_type_already_used_this_turn`) un'azione base già usata
  in un round precedente dello stesso turno; il ramo esistente per
  `WAITING_FOR_LINK_EXTRA_ACTION` resta invariato e non è toccato dal
  nuovo controllo. Registra l'azione scelta nella lista solo per i round
  Grinta base, mai per l'azione extra da Link.
- `application/legal_actions.py::get_legal_decision`: il generatore di
  `choose_action_type` per il round base ora esclude a monte le azioni già
  usate, così né un bot né un giocatore umano le vedono mai come opzione
  (la validazione nell'handler resta comunque la fonte di verità, come da
  CLAUDE.md §10).
- Test: `test_legal_actions.py` (l'azione già usata non compare tra le
  opzioni), `test_economy.py` (2 nuovi test — rifiuto e registrazione),
  `test_extra_action.py` (1 nuovo test — l'azione extra da Link può
  liberamente ripetere un'azione base già usata, a conferma che il vincolo
  non la riguarda).

Verificato con l'intera suite pytest (252 test), ruff, mypy, e
`tools/run_full_test_game.py --seeds 1-2000 --max-steps 4000` (2000/2000
partite completate senza fallimenti).

## 2026-08-15 — Correzione del game designer: costo della corruzione Cops/Feds

Decisione: corrompere un Cop o un Fed non ha più un costo fisso ($2/$3)
per un pacchetto rigido di "esattamente 2 azioni diverse". Il costo è ora
**1 dollaro per azione**, uguale per Cop e Fed, e il giocatore sceglie
liberamente quante azioni far compiere all'ufficiale corrotto — da 1 a 3
(sposta/arresta/requisisci, mai la stessa due volte), fermandosi quando
vuole. Esempio del game designer: con 2 Grinta, una pedina corrompe
pagando $3 per farlo fare tutte e 3 le azioni, un'altra pedina paga $2 per
farne fare solo 2 (es. arresta + requisisci). La segnalazione era che "al
momento sembra che i cops facciano 1 sola cosa per ogni grinta" — il
motore in realtà eseguiva già sempre 2 azioni (mai 1), ma il layer
`legal_actions.py` non offriva mai la scelta di fermarsi in anticipo:
`can_pass` era vero solo quando non restava più nessuna azione legale, non
appena il giocatore ne aveva già presa almeno una — di fatto forzando
sempre le 2 azioni quando entrambe erano disponibili. Sostituisce
integralmente §C5 di `RULES_CANONICAL.md` (costo fisso, esattamente 2
azioni).
Riferimento: `RULES_CANONICAL.md` §C5.
Impatto:
- `data/game_config.json`: `costs.corrupt_cop`/`costs.corrupt_fed` (2/3)
  sostituiti da un unico `costs.corrupt_action: 1`.
- `rules/officers.py`: `corruption_cost` rinominata
  `corruption_action_cost` (niente più distinzione Cop/Fed, sempre $1
  base). `_start_corruption` non addebita più nulla in anticipo — verifica
  solo che il giocatore possa permettersi almeno 1 azione. Il costo viene
  addebitato azione per azione dentro `_handle_choose_corruption_action`,
  che verifica l'affordability prima di applicare ciascuna azione. Il tetto
  di azioni per ufficiale passa da 2 a 3
  (`len(progress.actions_taken) < 3`). La validazione a monte del pacchetto
  multi-ufficiale (`_handle_corrupt_officer`) ora controlla solo il costo
  *minimo* garantito (1 azione a ufficiale), non più un totale fisso.
- `application/legal_actions.py::_corruption_action_decision`: `can_pass`
  ora è vero non appena è già stata presa almeno 1 azione, anche se
  restano azioni legali — non solo quando non ne resta più nessuna. Le
  opzioni reali vengono nascoste del tutto se il giocatore non può più
  permettersi $1. `_corrupt_officer_options` aggiornato per il costo
  minimo unico (niente più distinzione Cop/Fed nel sort di affordability).
- Non toccato: l'effetto Skill Politici-2 ("corrompi con 1 dollaro in
  meno") ora si applica per-azione tramite lo stesso `effective_cost`,
  quindi con quella Skill ogni singola azione di corruzione costa $0 —
  conseguenza diretta del nuovo modello "a consumo", non reinterpretata
  altrimenti; il game designer può correggere se non è l'intento.
- Test: `test_officers.py` (2 test riscritti per il nuovo modello, 2 nuovi
  — costo per-azione, stop volontario dopo 1 sola azione),
  `test_legal_actions.py` (1 nuovo — `can_pass` insieme ad azioni reali
  ancora disponibili).

Verificato con l'intera suite pytest (257 test), ruff, mypy.

## 2026-08-15 — Correzione del game designer: limite individuale di 2 pedine nel Den

Decisione: un giocatore non può avere più di 2 proprie pedine nel Den
contemporaneamente, indipendentemente dal limite globale di 6 Gambler
(§A1) — un vincolo per-giocatore in più, non un ripensamento di quello
esistente. Prima di questa correzione il motore validava solo la
capienza globale.
Riferimento: `RULES_CANONICAL.md` §A1 (Den).
Impatto:
- `data/game_config.json`: nuova chiave `den_capacity_per_player: 2`.
- `rules/movement.py::move_one_pawn`: nuovo controllo
  `den_full_for_player` accanto a quello globale esistente (`den_full`),
  contato sulle sole pedine del giocatore che sta entrando.
- `application/legal_actions.py::_move_criminal_options`: una destinazione
  Den non viene più offerta come opzione una volta che il giocatore ha già
  raggiunto il proprio limite individuale, anche se il Den globale ha
  ancora posto.
- Test: `test_economy.py` (rifiuto al limite individuale, con un altro
  giocatore ancora libero di entrare), `test_legal_actions.py` (nessuna
  opzione Den offerta al limite).

## 2026-08-15 — Verifica del game designer: un Job completa solo se attualmente rivelato

Verifica confermata senza modifiche al comportamento: un giocatore ottiene
credito per un Job solo se è una delle 3 carte attualmente rivelate (una
per livello) — soddisfare il requisito di un Job non rivelato in quel
momento (es. "Criminali in 6 Hoods diversi" mentre il livello corrispondente
mostra un altro Job) non lo fa scattare. Se in seguito quel livello rivela
proprio quel Job, la condizione — se ancora vera — viene ripresa alla
prima verifica successiva (lo stesso hook post-successo di ogni comando).
`rules/jobs.py::check_and_queue_completions` controllava già solo
`progress.revealed_job_id_by_tier`, mai l'intero elenco dei Job — il
comportamento era già corretto. Aggiunto solo un test di regressione,
prima mancante, che fissa esplicitamente questo scenario.
Riferimento: `RULES_CANONICAL.md` §A10.
Impatto:
- Test: `test_jobs.py::test_satisfying_a_job_not_currently_revealed_does_not_complete_it`.

Verificato con l'intera suite pytest (260 test), ruff, mypy, e
`tools/run_full_test_game.py --seeds 1-300` (300/300 partite completate
senza fallimenti).

## 2026-08-15 — Limite di 5 carte: controllo dopo ogni round, non ogni turno

Decisione: il game designer ha chiarito la terminologia round/turno (un
turno = 3 round; 3 turni a partita = 9 round per giocatore) e, su questa
base, ha **ribaltato** la decisione del 2026-08-01 (RULES_PENDING.md
#12/#17): il limite di 5 carte in mano si verifica alla fine di **ogni
round** del giocatore, non solo dell'ultimo dei 3 round del suo turno.
Resta invariato che il check non scatta durante il round di un *altro*
giocatore (una carta ricevuta fuori dal proprio round si tiene anche oltre
il limite, finché non arriva la fine del proprio round successivo).
Riferimento: `RULES_PENDING.md` #12, #17; `RULES_CANONICAL.md` §B2.
Impatto:
- `rules/turn_flow.py::_continue_after_main_action`: rimossa la
  condizione `_is_players_last_round` (e l'helper stesso, ora inutilizzato)
  — lo scarto scatta ogni volta che `over_limit` è vero, a ogni round.
- Test: `test_turn_flow.py::test_hand_limit_is_checked_after_every_round_not_just_the_last`.

Verificato con l'intera suite pytest (261 test).

## 2026-08-15 — Marketing: scelta reale della carta con 2+ carte idonee

Decisione: il game designer ha confermato che, con più di una carta con
Stonk in mano, il giocatore sceglie quale giocare — non più un auto-pick
della carta con più Stonk (comportamento PROVVISORIO da Milestone 5,
mai sottoposto al game designer). Con esattamente una carta idonea non
cambia nulla: nessun sotto-passo, si va dritti all'allocazione degli
Stonk come prima.
Riferimento: `RULES_PENDING.md` #21.
Impatto:
- `domain/commands.py`: nuovo comando `ChooseMarketingCard(card_id)`.
- `domain/state.py`: `PlayerState.marketing_chosen_card_id`, impostato da
  `ChooseMarketingCard`, letto da `_marketing_decision`, azzerato alla
  risoluzione dell'offerta (giocata o rifiutata, in entrambi i punti di
  offerta "prima"/"dopo").
- `application/legal_actions.py::_marketing_decision`: con 2+ carte
  idonee e nessuna ancora scelta, ritorna il nuovo decision_type
  `choose_marketing_card` (`_choose_marketing_card_decision`) invece di
  procedere subito all'allocazione; `build_command_from_selection` lo
  traduce in `ChooseMarketingCard` (0 selezioni = `PassOptionalStep`,
  rifiuta Marketing del tutto).
- `rules/economy.py`: nuovo handler `_handle_choose_marketing_card`;
  `_handle_play_marketing_card` azzera `marketing_chosen_card_id` a
  successo.
- `rules/turn_flow.py::_handle_pass_optional_step` (ramo
  `WAITING_FOR_CARD_USAGE`): azzera `marketing_chosen_card_id` anche sul
  rifiuto, sia che si stesse rifiutando la scelta della carta sia
  l'allocazione stessa.
- `adapters/http/app.py`: nuovo `command_type` `choose_marketing_card`
  sull'endpoint `/commands` di debug.
- Frontend: `choose_marketing_card` risolto cliccando la carta nella mano
  (stesso trattamento di `launch_poker`/`play_poker_card`,
  `HandDrawer.tsx`); nuovo pannello dedicato in `DecisionPanel.tsx`.
- Test: `test_marketing.py` (4 nuovi: offerta con 2+ carte idonee, scelta
  che restringe l'allocazione alla carta scelta, rifiuto della scelta
  annulla Marketing del tutto, rifiuto di una carta non idonea);
  `test_http_app.py::_command_type_and_payload` esteso.

Verificato con l'intera suite pytest (265 test), ruff, mypy,
`tools/run_full_test_game.py --seeds 1-300` (300/300 partite completate),
e verifica manuale nel browser reale (stato iniettato via `/load` con 2
carte idonee: la scelta appare, cliccare una carta la seleziona e
restringe correttamente il passo successivo a quella carta).

## 2026-08-15 — Compra/Vendi Merce: un Link conta come presenza, non solo un Criminale

Decisione: il game designer ha confermato che un Link conta come presenza
per Comprare/Vendere Merce esattamente come già valeva per la corruzione
di Cops/Feds (`rules/officers.py::has_presence_at_hood/_at_spot`, mai
riusate qui finora — un vero gap, non un'ambiguità di regolamento).
Riferimento: `RULES_PENDING.md` #22; CLAUDE.md §11.4/§11.5/§11.6.
Impatto:
- `rules/economy.py`: `has_presence_at_hood`/`has_presence_at_spot` spostate
  qui da `rules/officers.py` (che ora le re-esporta come alias — questo
  modulo già dipendeva da `economy` per altra validazione condivisa, non
  il contrario) così sia la corruzione sia Compra/Vendi Merce condividono
  un'unica definizione.
- **Compra Merce — cambio di schema:** ogni Quartiere di un Contact ha
  scorta/prezzo indipendenti, quindi un Link con scorta legale in
  entrambi i Quartieri del proprio Contact richiede una scelta esplicita
  di quale. `BuyDope.pawn_ids: tuple[PawnId, ...]` è diventato
  `BuyDope.purchases: tuple[tuple[PawnId, HoodId], ...]` — ogni
  chiamante (comando HTTP di debug, `build_command_from_selection`, tutti
  i test) aggiornato di conseguenza.
  `application/legal_actions.py::_buy_dope_options` ora enumera entrambi
  i Quartieri di un Link (`buy_{pawn_id}_{hood_id}`, non più solo
  `buy_{pawn_id}`, per evitare collisioni tra le due opzioni).
- **Vendi Merce — nessun cambio di schema:** i Punti di Vendita sono per
  Contact, non per Quartiere (due Merci accettate per Contact), quindi i
  due Quartieri di un Link danno sempre accesso agli stessi 2 Spot —
  `_sell_dope_options` ora usa `has_presence_at_spot` direttamente,
  eliminando anche il giro passante per il Quartiere che c'era anche per
  i Criminali. `SellDope.sales` invariato.
- **PROVVISORIO** (`RULES_PENDING.md` #22): una vendita fatta interamente
  da pedine Link a uno Spot salta l'offerta di evoluzione a Link per quel
  gruppo (`rules/economy.py::_handle_sell_dope`, filtro
  `criminal_seller_ids`) — il regolamento non descrive un Link che
  evolve ulteriormente. Un gruppo misto Criminale+Link converte comunque
  un Criminale, con livello pari al totale di merci vendute (Link
  inclusi), non solo alla quota Criminale.
Test:
- `test_link_presence_trading.py` (nuovo): opzioni Compra Merce offrono
  entrambi i Quartieri di un Link; Compra Merce via Link riuscita;
  Compra Merce via Link rifiutata fuori dal proprio Contact; opzioni
  Vendi Merce includono un Link; Vendi Merce via Link riuscita; Vendi
  Merce via un Link non offre l'evoluzione.
- Tutti i costruttori `BuyDope(pawn_ids=...)` esistenti aggiornati a
  `purchases=...` in `test_economy.py`, `test_marketing.py`,
  `test_skills.py`, `test_legal_actions.py`.

Verificato con l'intera suite pytest (272 test), ruff, mypy,
`tools/run_full_test_game.py --seeds 1-500` (500/500 partite completate),
verifica manuale nel browser reale (stato iniettato via `/load`: un Link
con scorta in entrambi i propri Quartieri mostra correttamente la
disambiguazione a 2 tappe cliccando la propria pedina sul tabellone; una
vendita via Link separata verificata allo stesso modo), e
`smoke-test.mjs` (22 run, nessun fallimento riconducibile a questa
modifica — l'unico fallimento osservato è un flake preesistente e non
correlato, già visto prima di questa modifica, in `choose_job_reward`).

## 2026-08-16 — Un Quartiere nascosto non è piazzabile né raggiungibile a mano

Decisione: il game designer ha confermato che i Quartieri non ancora
scoperti sono raggiungibili **solo** tramite la relocation del Criminale
sconfitto in Rissa — mai con un piazzamento o uno spostamento normale.
Era un gap, non un'ambiguità: `_place_criminal_options`/
`_move_criminal_options` non controllavano affatto `hood.revealed`.
Riferimento: `RULES_CANONICAL.md` §C1/§C2.
Impatto:
- `application/legal_actions.py`: `_place_criminal_options` salta i
  Quartieri non scoperti; `_move_criminal_options` fa lo stesso sia per
  i Criminali (destinazioni adiacenti) sia per i Gambler che escono dal
  Den. `_place_criminal_options`'s `max_selectable` ora è anche
  ricalcolato (`min(max_selectable, len(options))`) — prima era
  calcolato solo da grinta/soldi/pedine disponibili, senza considerare
  quanta capacità piazzabile esiste davvero tra i soli Quartieri
  scoperti; con la nuova esclusione poteva restare più alto delle
  opzioni realmente generate.
- `rules/economy.py::_handle_place_criminal`,
  `rules/movement.py::move_one_pawn` (entrambi i rami Criminale e
  Gambler): stesso controllo ripetuto nel command handler
  (`hood_not_revealed`), coerente con CLAUDE.md — client/bot non sono
  fonti fidate.
- `bots/random_legal.py`: due bug di regressione trovati dallo sweep
  bot-only dopo la modifica sopra, non collegati alla causa ma esposti
  da essa (meno Quartieri disponibili = pool di opzioni più stretto,
  più probabile incappare in un caso limite già latente):
  1. `rng.sample(decision.options, count)` (ramo generico) poteva
     chiedere più opzioni di quante ne esistessero davvero per
     "place_criminal" una volta che `max_selectable` non era ancora
     stato ricalcolato (vedi sopra) — risolto insieme.
  2. `_pick_cheapest_options` (usata da "buy_dope") non deduplicava per
     pedina: un Link con 2 opzioni "buy_dope" (uno per Quartiere del
     proprio Contact, decisione 2026-08-15) poteva finire scelto due
     volte se entrambe erano tra le più economiche, rigettato dal
     command bus con `duplicate_pawn_in_targets`. Ora dedupe per pedina
     nello stesso ordine di costo, come già faceva
     `_pick_one_option_per_pawn` per "move_criminal"/"sell_dope".
Test:
- `test_economy.py::test_place_criminal_rejects_unrevealed_hood` (nuovo).
- `test_legal_actions.py::
  test_place_criminal_max_selections_never_exceeds_generated_options`
  (nuovo, riproduce il crash del bot in isolamento).
- `test_link_presence_trading.py::
  test_random_legal_bot_never_double_buys_through_the_same_link` (nuovo).
- `test_brawl.py`/`test_economy.py`/`test_extra_action.py`/
  `test_skills.py`: fixture esistenti che piazzavano/spostavano su
  `hood_q2` (non scoperto di default) aggiornate con
  `hood.revealed = True` esplicito, per preservare l'intento originale
  di ciascun test.

Verificato con l'intera suite pytest (275 test), ruff, mypy. Lo sweep
bot-only (`tools/run_full_test_game.py`) aveva inizialmente trovato 10
partite su 500 che si schiantavano sui due bug del bot sopra (semi 272,
286, 317, 343, 345, 355, 365, 409, 417, 426) — dopo la correzione,
900/900 partite pulite su due sweep successivi (semi 1-500 e 501-900).

## 2026-08-16 — Corrompi: un officer alla volta invece di un pacchetto pre-committato

Decisione: il game designer, giocando una partita reale, ha segnalato che
con Grinta 2 su "Corrompi", dopo che il primo ufficiale corrotto aveva
esaurito le proprie azioni (es. Sposta + Arresta), l'intera azione finiva
subito — mentre le 2 azioni fatte appartenevano solo al primo dei 2 slot
di Grinta, e il secondo slot doveva restare disponibile. La causa non era
un bug di generazione (il pacchetto `CorruptOfficer` upfront con 2
`(pawn_id, officer_id)` già funzionava, vedi
`test_corrupt_officer_with_grit_2_queues_two_officers`), ma un disallineamento
di design: il giocatore doveva impegnarsi su **quale** secondo ufficiale
corrompere prima ancora di sapere quante azioni (1-3, $1 ciascuna) gli
sarebbe servite sul primo — non corrisponde a come si vuole davvero
giocare. Decisione: la corruzione con Grinta N può ora corrompere fino a N
ufficiali diversi **decidendo uno alla volta**, dopo aver visto l'esito
del precedente, invece di sceglierli tutti in anticipo in un solo comando.
Riferimento: `RULES_CANONICAL.md` §C5 (nessun cambiamento al testo della
regola stessa — cambia solo *quando* si sceglie il prossimo bersaglio,
non le regole di corruzione in sé).
Impatto:
- `domain/state.py`: nuovo `PlayerState.corrupted_pawn_ids_this_action`
  (quali pedine hanno già corrotto un ufficiale in questa istanza
  d'azione), azzerato ad ogni nuova scelta di `action_type`
  (`rules/economy.py::_handle_choose_action_type`).
- `rules/officers.py::_start_corruption` registra la pedina usata;
  `_finish_corruption` — una volta esaurita la coda del comando
  corrente — torna allo step da cui l'azione era partita
  (`WAITING_FOR_MAIN_ACTION_TARGETS`/`WAITING_FOR_LINK_EXTRA_ACTION`) se
  resta budget di Grinta, invece di terminare sempre l'azione; se non
  resta nulla di realmente ottenibile, il meccanismo di "decisione vuota
  e declinabile" già esistente per `_action_targets_decision` (usato
  anche dal caso di starvation del lancio Poker) gestisce la chiusura
  senza nuovo codice dedicato. `_handle_corrupt_officer` rifiuta una
  pedina già usata in un comando precedente della stessa azione e
  applica il budget *residuo*, non quello pieno.
- `application/legal_actions.py::_corrupt_officer_options` esclude le
  pedine già usate e limita `max_selectable` al budget residuo.
- Nessuna modifica al frontend: la decisione ri-offerta è dello stesso
  `decision_type` "corrupt_officer" già gestito dalla UI esistente.
Test: nuovo
`test_officers.py::test_corrupt_officer_with_grit_2_offers_second_officer_after_first_finishes`.
Verificato: 278 test pytest, ruff, mypy, sweep bot-only da 1500 partite,
smoke test da browser.

## 2026-08-17 — Marketing: solo "prima" dell'azione, mai "dopo"

Decisione: il game designer ha richiesto che Marketing si possa giocare
**solo prima** di Acquista/Vendi, non più anche "dopo" — la versione
precedente (Milestone 5 Stage 4c-bis, 2026-08-02) offriva un secondo
tentativo "dopo" quando il giocatore non aveva usato Marketing "prima";
in prova non c'era mai un motivo per preferire "dopo" a usarlo "prima".
Confermato inoltre che gli Stonk di una stessa carta si possono dividere
liberamente tra più merci a scelta (già vero per "prima", che restava
l'unico caso non ristretto a `player.marketing_eligible_dope_types`) —
comportamento confermato esplicitamente, non solo implicito.
Riferimento: `RULES_CANONICAL.md` §C3/§C4/§D3, supera la decisione
2026-08-02 "prima o dopo l'intera azione".
Impatto:
- `rules/economy.py::_finish_buy_or_sell_package`: rimossa l'offerta
  "dopo" (il ramo `has_eligible_card` → `WAITING_FOR_CARD_USAGE`); ora
  applica sempre e solo l'eventuale replay automatico Manager-3, poi
  chiude l'azione. Parametro `stonk_count_by_card_id` non più
  necessario, rimosso insieme al parametro (ormai inutilizzato) dallo
  stesso in `_handle_buy_dope`/`_handle_sell_dope`/
  `_handle_evolve_sale_link`.
- `rules/economy.py::_handle_play_marketing_card`: rimossa la
  restrizione `eligible_dope_types`/il ramo "dopo" — sempre trattato
  come "prima" (l'unico caso rimasto), quindi sempre libero su
  qualunque Merce.
- `rules/turn_flow.py::_handle_pass_optional_step` (ramo
  `WAITING_FOR_CARD_USAGE`): rimosso il ramo "dopo" della decisione
  (declinare torna sempre alla selezione bersagli).
- `application/legal_actions.py::_marketing_decision`: sempre tutte le
  Merci del gioco, mai più ristretto a
  `player.marketing_eligible_dope_types`.
- `domain/state.py`: rimosso il campo `PlayerState.
  marketing_eligible_dope_types`, ormai morto (serviva solo a
  restringere l'offerta "dopo").
- Il codice `dope_type_not_in_package` (validazione dell'offerta "dopo")
  non è più raggiungibile ed è stato rimosso.
Test: rimossi i test specifici dell'offerta "dopo"
(`test_buy_dope_offers_marketing_after_when_before_was_not_used`,
`test_marketing_rejects_dope_type_not_in_package`,
`test_declining_marketing_after_still_finishes_the_action`), sostituiti
da `test_marketing.py::
test_buy_dope_never_offers_marketing_after_declining_before` (conferma
che l'azione si chiude direttamente, senza una seconda offerta) e
`test_marketing_before_allows_splitting_stonks_across_two_dope_types`
(conferma esplicita della divisione tra 2 merci a scelta). I test del
Manager-3 (`test_skills.py`, replay automatico) restano invariati, non
toccati dalla rimozione dell'offerta "dopo" perché il replay non dipende
da una decisione interattiva.
Verificato: 277 test pytest, ruff, mypy, sweep bot-only da 1500 partite,
smoke test da browser.

## 2026-08-17 — Azione extra da Link: una volta per round, non per turno intero

Decisione: il game designer, giocando una partita reale, ha richiesto che
l'azione extra da Link (§A5) sia utilizzabile **una volta per round**
(fino a 3 volte per turno, 9 per partita) invece che una sola volta per
l'intero turno, come deciso il 2026-08-01. Rimane invariato tutto il resto:
prima o dopo l'azione principale del round, Link speso torna sempre
immediatamente al Covo, il livello del Link determina la Grinta
dell'azione extra (già implementato correttamente, non toccato da questa
decisione).
Riferimento: `RULES_CANONICAL.md` §A5, supera la decisione 2026-08-01.
Impatto:
- `domain/state.py`: `PlayerState.extra_actions_used_this_turn` rinominato
  `extra_actions_used_this_round`.
- `rules/turn_flow.py`: l'azzeramento del contatore si sposta da
  `_start_action_phase` (una volta per turno) a `_start_new_round` (una
  volta per round, chiamata 3 volte per turno) — la formula del limite
  stesso (`rules/skills.py::max_link_extra_actions_per_round`, rinominata
  da `_per_turn`) non cambia, solo la frequenza di reset.
- **Nota non ancora confermata dal game designer:** la Skill Politici-3
  ("Puoi attivare 2 Ganci a turno", `amount: 2` in `data/skills.json`) non
  è stata toccata nei dati — dato che il limite base passa da 1/turno a
  1/round, lasciare la Skill un letterale "2/turno" la renderebbe *peggiore*
  del nuovo limite base per chi non ha la Skill. Reinterpretata quindi come
  "2/round" (raddoppia il nuovo limite base, invece di sostituirlo con un
  valore fisso più basso) — vedi `rules/skills.py::
  max_link_extra_actions_per_round`'s docstring. Da confermare.
Test: rinominati tutti i riferimenti in `test_extra_action.py`,
`test_skills.py`, `test_turn_flow.py`; nessun nuovo test dedicato al
"3 volte a turno" (già coperto indirettamente dallo sweep bot-only, che
esercita ripetutamente l'azione extra su più round dello stesso turno
senza mai incappare in `extra_action_already_used` prima del previsto).
Verificato: 279 test pytest, ruff, mypy, sweep bot-only da 1500 partite,
smoke test da browser.

## 2026-08-23 — Acquisto Merce oltre il limite del Covo: rifiutato, non scartato

Decisione: il game designer ha chiarito che il limite di 3 unità per tipo
di Merce nel Covo deve **bloccare** l'acquisto in eccesso, non lasciarlo
avvenire per poi scartare la Merce acquistata ("il limite di merci di un
tipo nel Covo blocca la terza vendita di polpo, non la scarta a
posteriori"). Un pacchetto di acquisto che include un'unità oltre il
limite viene rifiutato per intero (stessa semantica atomica di
`insufficient_funds`/`hood_has_no_dope`, già presenti nello stesso ciclo),
non applicato parzialmente — un pacchetto legale si compone invece
scegliendo meno unità del tipo già al limite e completando il resto con
un tipo diverso, ancora possibile nello stesso comando ("posso comunque
fare l'ultimo acquisto di un'altra merce").
Riferimento: `RULES_PENDING.md` #23, risolve la metà "acquisto" del punto
CLAUDE.md §22 #26 (la metà "recupero dall'Evasione" resta PROVVISORIA,
ancora `DopeLostToOverflow` in `rules/jail.py`, non toccata da questa
decisione).
Impatto:
- `rules/economy.py::_handle_buy_dope`: il ramo che emetteva
  `DopeLostToOverflow` quando il Covo era già a 3 è sostituito da un
  `CommandFailure(code="base_inventory_full")`, controllato prima di
  addebitare il denaro/consumare la scorta del Quartiere per quell'unità.
  Import di `DopeLostToOverflow` rimosso da questo modulo (resta usato
  solo da `rules/jail.py`).
- `bots/random_legal.py::_pick_buy_dope_options`: aggiunto un budget per
  la capacità residua del Covo per tipo di Merce (accanto al budget di
  scorta per Quartiere già presente), per non proporre mai un pacchetto
  che verrebbe rifiutato.
- `application/legal_actions.py::_buy_dope_options` invariata
  deliberatamente: continua a offrire ogni opzione individualmente legale
  senza budget condiviso a tempo di generazione, stesso principio già
  documentato lì per la scorta di Quartiere (il vincolo va rispettato a
  tempo di scelta/validazione, non di generazione).
Test: `test_economy.py::test_buy_dope_overflow_discards_dope_at_base_cap`
rinominato `test_buy_dope_rejects_purchase_that_would_exceed_base_cap` e
riscritto per il nuovo comportamento (`CommandFailure` invece di
`CommandSuccess` con evento `DopeLostToOverflow`).
Verificato: 291 test pytest, ruff, mypy.

## 2026-08-23 — Ricarica a meno di 3 quando la banca condivisa di un tipo è esaurita: confermata intenzionale

Decisione: il game designer ha segnalato che comprando l'ultima Merce di un
tipo in un Quartiere, la ricarica automatica può portare meno di 3 Merci
(es. 1 sola) — chiesto se fosse un bug. Verificato che non lo è:
`rules/economy.py::_restock_hood` già implementava correttamente
`min(3, banca_rimasta)`, e l'invariante di conservazione (banca + Merci sui
Quartieri + Merci nei Covi == `data/dope_types.json::total_supply`) è
rispettata e testata (`test_setup.py::test_setup_matches_documented_rules`).
Il totale per tipo è finito e condiviso da tutti i Quartieri/Covi — con
`gufo` a 8 unità totali, il solo setup (Quartiere scoperto + mani iniziali
dei 4 giocatori) ne consuma già 5, lasciandone 3 in banca prima di
qualunque ricarica, e un Quartiere coperto rivelato a metà partita può
consumarne altre 1-3 dello stesso tipo. Il game designer ha confermato
(2026-08-23) che questa scarsità è **intenzionale** (componenti fisici
finiti, come nel gioco da tavolo) e non richiede modifiche a dati o
motore — solo la documentazione in `RULES_CANONICAL.md` §C3 mancava
questo caso limite.
Riferimento: `RULES_CANONICAL.md` §C3 (nota aggiunta).
Impatto: nessuna modifica al motore. Solo documentazione.
Test: nessun nuovo test — comportamento già coperto da
`test_setup.py::test_setup_matches_documented_rules` e dai test esistenti
di `rules/economy.py::_restock_hood`.
Verificato: nessuna modifica al codice, nulla da rieseguire.

## 2026-08-23 — Job 2 / Retata 5 "Cops posseduti": da contatore cumulativo a possesso attuale

Decisione: il game designer ha segnalato che il Job "Compra 1 Cop/Fed"
non deve completarsi per il solo fatto di aver comprato un Cop/Fed da un
avversario — serve possederne almeno uno nel proprio Covo **in questo
momento**. Chiesto se lo stesso valesse per la Retata 5 ("comprato più
Cops"), che condivide lo stesso contatore cumulativo per decisione
documentata il 2026-08-01 ("stesso significato del Job 2") — confermato
di sì, cambiano entrambi insieme, restando un unico pool condiviso
Cops+Fed.
Riferimento: `RULES_CANONICAL.md` §A10, supera la decisione 2026-08-01
(sia per il Job sia per la Retata).
Impatto:
- `data/jobs.json`: Job 2 rinominato `requirement.type` da
  `buy_officers` a `own_officers` (stesso naming di `own_rats`/
  `own_links`), titolo da "Compra 1 Cop/Fed" a "Abbi 1 Cop/Fed".
- `rules/jobs.py::_check_requirement`: il ramo `own_officers` ora chiama
  `rules/officers.py::officer_count_in_base` (possesso attuale) invece
  di leggere `player.officers_bought_count`.
- `rules/raids.py::_most_cops_bought`: stessa logica di
  `officer_count_in_base`, duplicata inline invece che importata da
  `rules/officers.py` — `officers.py` importa `turn_flow`, che importa
  `raids`, quindi un import diretto sarebbe circolare.
- `rules/officers.py::_handle_buy_officer`: rimosso l'incremento di
  `player.officers_bought_count` (non più letto da nessuno).
- `domain/state.py`: rimosso il campo `PlayerState.officers_bought_count`
  (dead — nessun altro punto del codice lo leggeva o scriveva).
- `OutcomeModal.tsx`'s `RAID_CRITERION_LABEL`: "Cops/Feds comprati" ->
  "Cops/Feds posseduti" (il testo mostrato al giocatore non deve più
  suggerire un conteggio cumulativo). `data/raids.json`'s Raid 5 `text`
  ("comprato più Cops") lasciato invariato — trascrive il testo stampato
  sulla carta fisica, non la logica di punteggio.
Test: `test_jobs.py::test_buy_officers_requirement` rinominato
`test_own_officers_requirement_is_a_snapshot_not_a_cumulative_count` e
riscritto per costruire un `OfficerState` reale in Covo invece di
impostare il contatore direttamente (stesso stile di
`test_own_rats_requirement_is_a_snapshot_not_a_cumulative_count`).
`test_raids.py::test_most_cops_bought_counts_cops_and_feds_together`
riscritto allo stesso modo, con 2 Cops + 2 Feds reali in Covo.
Verificato: 291 test pytest, ruff, mypy.

## 2026-08-24 — Sovrapposizione lancio Poker / Marketing: entrambi offerti in sequenza
Decisione: un'azione Acquista/Vendi idonea sia al lancio Poker (carta
Preti idonea) sia a Marketing (carta Stonk idonea) offre prima il lancio
Poker; una volta risolto (lanciato o rifiutato), se il giocatore ha
ancora una carta Stonk idonea per quell'azione, Marketing viene offerto
subito dopo, prima della selezione bersagli. Segnalato dal game designer
come bug ("comprando/vendendo e lanciando un poker non mi veniva offerta
la possibilità di fare marketing") — confermato riproducibile:
`rules/economy.py::_handle_choose_action_type` offriva solo l'uno o
l'altro (un commento `PROVISIONAL` preesistente descriveva questo come
scelta deliberata, ma non era mai stato tracciato in `RULES_PENDING.md`
né coperto da un test, quindi non conforme alla propria stessa
convenzione per le decisioni provvisorie).
Riferimento: `RULES_CANONICAL.md` §D3, ultima voce.
Impatto:
- `rules/turn_flow.py`: nuova funzione condivisa
  `resume_after_poker_launch_offer` (risolve
  `player.poker_launch_return_step`, poi entra in
  `WAITING_FOR_CARD_USAGE` se ancora idoneo, altrimenti torna al
  `return_step` come prima). `register_handlers` e
  `_handle_pass_optional_step` guadagnano `stonk_count_by_card_id`
  (opzionale, default `{}`, stessa convenzione già usata in
  `economy.py::register_handlers`).
- `rules/poker.py::_handle_launch_poker`: usa la nuova funzione condivisa
  invece di tornare direttamente al `return_step`; `register_handlers`
  guadagna lo stesso parametro opzionale.
- `rules/economy.py::_handle_choose_action_type`: commento aggiornato
  (non più "mai entrambi").
- `application/game_service.py`: passa `stonk_count_by_card_id` anche a
  `turn_flow.register_handlers` e `poker.register_handlers`.
Test: `test_poker.py` — 3 nuovi test
(`test_launching_poker_then_offers_marketing_if_still_eligible`,
`test_declining_poker_then_offers_marketing_if_still_eligible`,
`test_launching_poker_without_a_stonk_card_skips_marketing_as_before`).
Verificato: 296 test pytest, ruff, mypy, sweep bot-only 500 seed.

## 2026-09-02 — Jail ridotta da 6 a 4 slot; Job "Abbi 3 Rats" -> "Abbi 2 Rats"
Decisione: il game designer ha fornito una nuova board art
(`BOARD_v15_GODOPE_4.webp`) con la Jail ridisegnata a 4 slot (posizione
anche leggermente diversa dai vecchi 6) e la griglia dei Job riorganizzata
in 3 gruppi visivi per tier invece dell'ordine job_01..09; ha inoltre
chiesto di abbassare il requisito del Job 4 da 3 a 2 Rats, in linea con
la Jail più piccola.
Riferimento: conversazione 2026-09-02 (nessun punto RULES_PENDING
associato — decisione diretta, non un'ambiguità del regolamento).
Impatto:
- `data/game_config.json`: `jail_slot_count` 6 -> 4.
- `data/jobs.json`: `job_04.title` "Abbi 3 Rats" -> "Abbi 2 Rats",
  `requirement.count` 3 -> 2.
- `frontend/src/assets/index.ts`: import della board da
  `BOARD_v14_b.png` a `BOARD_v15_GODOPE_4.webp`.
- `frontend/src/App.css`: `.board-view`'s `aspect-ratio` aggiornato alle
  dimensioni reali del nuovo file (8070/4200, prima 3200/1665 — quasi
  identico, ma allineato esattamente).
- `frontend/src/board-layout.ts`: `JAIL_SLOT_POSITION` (ora 4 punti,
  indice 0..3 = numeri "1".."4" stampati sull'art) e `JAIL_CENTER`
  rimisurati sul nuovo art; la griglia Job (`JOB_BOARD_CELL_POSITION`)
  rimisurata e disaccoppiata dal numero del `job_id` — prima la riga
  sulla board era dedotta direttamente dal suffisso numerico
  (`job_0N` -> riga N), ora è un elenco esplicito
  (`JOB_BOARD_ROW_ORDER`) che riflette il nuovo ordine per tier
  (job_01/02/07 tier 1, job_04/05/06 tier 2, job_03/08/09 tier 3),
  altrimenti riordinare `jobs.json` da solo non avrebbe spostato nulla
  visivamente.
- Commenti aggiornati per non riferirsi più a un conteggio fisso "6"/
  "sesto Rat" dove descrivevano il trigger dell'Evasione (ora generico,
  "l'ultimo Rat che riempie l'ultimo slot libero"): `rules/jail.py`,
  `rules/jobs.py`, `rules/officers.py`, `rules/economy.py`,
  `rules/setup.py`, `domain/events.py::JailEscapeTriggered`.
- `docs/rules/RULES_CANONICAL.md` §A1/§A5/§A2/§D2: "6 slot"/"sesto Rat"
  aggiornati a "4 slot"/"il quarto Rat" con annotazione di decisione.
Test: `backend/tests/unit/test_jail.py` (4 test riscalati a
`len(state.jail.slots)` invece di assumere 6 fisso: rinominati
`test_last_rat_triggers_evasion_and_returns_others_to_base` e
`test_own_rats_job_completes_even_when_the_last_rat_triggers_evasion`),
`backend/tests/unit/test_poker.py::
test_second_defeated_gambler_is_arrested_right_after_the_first_triggers_evasion`
(filler count derivato da `len(state.jail.slots) - 1`).
Verificato: 389 test pytest, ruff, mypy, `validate_data.py`, sweep
bot-only 500 seed, build frontend pulita, verifica visiva in browser
(screenshot) della griglia Job e della Jail a 4 slot allineate al nuovo
art.
Non ancora implementato in questa voce (vedi voce successiva, stesso
giorno): colonna 4 della griglia Job ("none" -> $3 fisso per tutti i
Job) e colonna 2 del Job "10 Criminali fuori dal Covo" (Link -> scelta
tra $3 e 2 carte).

## 2026-09-02 — Colonna 4 dei Job -> $3 fisso; colonna 2 di Job 8 -> scelta $3/2 carte
Decisione: seguito della voce precedente, stesso giorno. Colonna 4
("none", mai implementata come bonus reale) diventa un bonus $3 fisso,
uguale su ogni riga Job. Correzione della prima proposta del game
designer (colonna 4 = scelta $3/2 carte): la colonna 4 è **solo** $3
fisso; è la colonna 2 (Link) del solo Job 8 ("Abbi tutti i 10 Criminali
fuori dal Covo") a diventare la scelta $3/2 carte, perché completare
quel Job implica sempre 0 pedine in Covo (nessuna da promuovere a
Link) — la colonna Link per quel Job dava quindi sempre nulla in
silenzio (RULES_PENDING.md #16, già "risolto" come comportamento
generale accettato, ora con un'eccezione mirata).
Riferimento: RULES_PENDING.md #16 (aggiornato); conversazione
2026-09-02.
Impatto:
- `domain/enums.py`: `JobBonusType.MONEY` (colonna 4) e
  `JobBonusType.MONEY_OR_TWO_CARDS` (override Job 8); nuovo
  `ActiveStep.WAITING_FOR_JOB_BONUS_ALTERNATIVE_CHOICE`.
- `domain/commands.py`: nuovo comando `ChooseJobBonusAlternative`
  (`bonus_type: str`, "money" o "two_cards").
- `domain/content.py`: `JobDefinition` guadagna
  `column_bonus_overrides: dict[int, str]` (default `{}`), un
  override per-Job del bonus altrimenti condiviso da
  `job_board_column_bonuses` — oggi usato solo da Job 8.
- `data/game_config.json`: `job_board_column_bonuses[3]` "none" ->
  "money"; nuovo `job_board_money_bonus_amount: 3`.
- `data/jobs.json`: `job_08.column_bonus_overrides: {"1":
  "money_or_two_cards"}`.
- `rules/jobs.py::_handle_choose_job_reward`: calcola il bonus dalla
  colonna globale, poi applica l'override per-Job se presente; nuovi
  branch `MONEY` (grant diretto) e `MONEY_OR_TWO_CARDS` (pausa —
  stesso pattern "stash and resume" già usato per SKILL al tetto di 3,
  riusando `stalled_column_index`/`stalled_contact_id`); nuovo handler
  `_handle_choose_job_bonus_alternative` che risolve la scelta.
- **Bug preesistente trovato e corretto durante lo sweep bot** (non
  causato da questa modifica, solo esposto da essa): sia
  `game_service.py::_refresh_pending_decision` sia `advance()`'s own
  bot-driving loop controllavano solo `ActiveStep.WAITING_FOR_JOB_REWARD`
  per decidere se una decisione può essere pendente fuori dalle 3 fasi
  normali (necessario perché un Job può completarsi durante la
  risoluzione di Poker/Retata dell'ultimo turno, lasciando `state.phase`
  a `SHOWDOWN_PHASE`) — non includevano mai
  `WAITING_FOR_SKILL_DISCARD_CHOICE`, lo stesso identico gap dal
  2026-08-27, semplicemente mai incontrato nei 500+ seed di sweep
  precedenti. Corretto in entrambi i punti, ora una tupla condivisa
  `job_reward_flow_steps` che include tutti e 3 gli step del flusso.
- `application/legal_actions.py`: dispatcher per il nuovo
  `ActiveStep`, più `_job_bonus_alternative_decision` (2 opzioni fisse)
  e il branch corrispondente in `build_command_from_selection`.
- `adapters/http/app.py`: import + branch in `_build_command` per
  `choose_job_bonus_alternative`.
- `frontend/src/components/DecisionPanel.tsx`: nuovo branch per
  `choose_job_bonus_alternative` (bottoni "3$"/"2 Carte", stesso
  `QuickButtons` di `choose_grit_action`).
Test: `backend/tests/unit/test_jobs.py` — 4 test .index("none") ->
.index("money") aggiornati, `test_claim_none_bonus_does_nothing...`
riscritto in `test_claim_money_bonus_grants_the_configured_amount`
(asserisce il grant reale), più 4 nuovi test per il flusso di scelta
di Job 8 (offerta della scelta, grant $3, grant 2 carte, rifiuto di un
`bonus_type` non valido).
Verificato: 393 test pytest, ruff, mypy, `validate_data.py`, sweep
bot-only 800 seed (3 fallimenti "no pending_decision but game is not
finished" nel primo giro, dovuti al bug preesistente sopra — 0
fallimenti dopo la correzione), build frontend pulita, verifica visiva
in browser (screenshot, craft di uno stato in `WAITING_FOR_JOB_BONUS_
ALTERNATIVE_CHOICE`+`SHOWDOWN_PHASE`) — pannello con "3$"/"2 Carte",
click su "3$" risolve senza errori e il segnalino soldi avanza di 3
sul tracciato.

## 2026-09-02 — Colonna 4 dei Job: allineamento REP + niente scelta Contact per $3
Decisione: seguito delle due voci precedenti, stesso giorno. Il game
designer ha segnalato due problemi dopo il primo utilizzo dal vivo:
i segnalini REP nella colonna 4 apparivano leggermente spostati a
sinistra rispetto a prima, e nei Job bicolore scegliere $3 chiedeva
comunque di cliccare un Contact (visivamente, un Link) come se stesse
scegliendo a chi legarsi.
Riferimento: conversazione 2026-09-02.
Impatto:
- `frontend/src/board-layout.ts`: `JOB_BOARD_COLUMN_X`'s 4° valore
  corretto da 9.275 a 9.957 — la misurazione originale usava un ritaglio
  dell'immagine che tagliava il bordo destro della cella (il box
  rilevato risultava largo 103px invece dei 213px reali, con centro
  spostato a sinistra); rimisurato con un ritaglio più ampio, ora
  praticamente identico al vecchio board (9.938%).
- `rules/jobs.py::_job_reward_decision` (chiamata da
  `application/legal_actions.py`): per il bonus `MONEY` su un Job a 2
  Contact, ora genera **una sola** opzione (con un Contact qualunque,
  arbitrario, dato che non conta) invece di una per Contact — nuovo
  `effective_column_bonus_type` (condiviso con `_handle_choose_job_
  reward`, che già calcolava lo stesso override per-Job) per sapere il
  bonus reale di una colonna prima di decidere se duplicare le opzioni.
- **Bug preesistente trovato durante lo sweep bot** (esposto solo ora
  perché prima nessun bonus Job poteva cambiare i soldi di un giocatore
  in modo sincrono): `rules/jobs.py::_advance_job_reward_queue`
  ripristinava lo step interrotto (`resume_active_step`) senza
  ricontrollarne la precondizione — se quello step era
  `WAITING_FOR_STAIN_FOR_CASH_OFFER` e nel frattempo il giocatore aveva
  reclamato un bonus `MONEY` che lo portava sopra la soglia, il gioco
  offriva comunque la scelta di macchiare REP per contanti, poi la
  rifiutava (`cannot_stain_for_cash`) quando il giocatore (o bot)
  provava davvero. Corretto: al resume, se lo step è
  `WAITING_FOR_STAIN_FOR_CASH_OFFER` e l'idoneità non c'è più, si salta
  allo step successivo tramite la stessa logica "prima"/"dopo" già usata
  per il rifiuto esplicito dell'offerta — nuova funzione condivisa
  `turn_flow.py::resume_after_declining_stain_offer`, usata sia da
  `_handle_pass_optional_step` (rifiuto esplicito) sia dal resume di
  `_advance_job_reward_queue`.
Test: `backend/tests/unit/test_jobs.py` — nuovo
`test_money_column_offers_only_one_option_on_a_two_contact_job`
(contrasta col caso SKILL, che continua a offrire un'opzione per
Contact) e `test_resuming_a_stain_offer_rechecks_eligibility_after_a_
money_bonus` (verificato fallire contro il codice senza la correzione,
prima di essere ripristinata).
Verificato: 395 test pytest, ruff, mypy, `validate_data.py`, sweep
bot-only 1500 seed (1 fallimento nel primo giro a seed=58, riprodotto
5/5 volte in isolamento — non il bug di non-determinismo noto, un bug
reale — 0 fallimenti dopo la correzione), build frontend pulita,
verifica visiva in browser (screenshot: 8 segnalini REP allineati
verticalmente in colonna 4; click sulla colonna $3 di un Job bicolore
risolve con un solo click, nessuna scelta di Contact).
