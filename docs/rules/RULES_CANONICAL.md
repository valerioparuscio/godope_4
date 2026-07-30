# Regolamento canonico — DOPE

Fonte primaria: `how_to_play_v056` (fornito dal game designer in chat il 2026-07-30,
4 pagine, sezioni A–D). Trascrizione fedele, senza reinterpretazione, secondo
`CLAUDE.md` sezione 2 — Fonti di verità.

I punti non coperti o ancora ambigui dopo questa trascrizione sono elencati in
`RULES_PENDING.md`, con riferimento alla sezione qui sotto quando pertinente.

> In Dope sarete i Boss di una Gang di criminali alle prime armi che cerca di
> farsi spazio nel mondo del malaffare in città. Nel corso di 4 giorni dovrete
> mettere in piedi il vostro giro di affari sporchi che vi consentirà di
> portare a termine il maggior numero di Jobs. Vince la Gang con più Respect.

## A) Componenti

### A1) Hoods (Quartieri)

Ci sono 10 Quartieri collegati da una rete di strade, più 2 Quartieri speciali,
Den e Jail.

Ciascun Hood ha 5 piazze ed è caratterizzato da un colore che indica un Contact.
Al centro del Quartiere c'è il mercato della Dope acquistabile dai Criminali.
Da un Quartiere i Criminali potranno vendere Merce solo al relativo Cliente.

**Den**

- Il Den è un Quartiere speciale in cui non sono permessi acquisti, vendite o risse.
- Un Criminale non può essere piazzato nel Den ma può raggiungerlo con uno
  spostamento da qualunque Quartiere.
- Un Criminale che entra nel Den fa pescare una carta a scelta e prende il
  nome di Gambler. **Decisione (2026-07-30):** il giocatore sceglie da quale
  mazzo Cliente pescare, poi la carta è casuale (pesca dalla cima del mazzo
  scelto).
- Dal Den i Gambler possono essere spostati in un qualunque Quartiere.
- Per ogni Gambler i giocatori possono partecipare ad un Poker per turno.
- **Decisione (2026-07-30):** il Den ospita al massimo 6 Gambler
  contemporaneamente.

**Jail**

- Il Commissariato è un Quartiere speciale in cui i Criminali entrano quando
  vengono arrestati, diventando Rats.
- Nei 6 slot del Commissariato vengono messi i Rats e le Merci requisite.
- I Rats possono corrompere Cops in qualunque Quartiere.
- Quando il Commissariato si riempie c'è l'Evasione e i 6 Rats tornano nei
  Covi, portandosi dietro la Merce su cui sono posizionati. **Decisione
  (2026-07-30):** il sesto Rat, quello che causa l'Evasione, non torna al
  Covo come Rat: evolve direttamente in Link dai Politici (vedi §A5). Sono
  quindi 5 i Rats che tornano ai Covi come pedine libere con la loro Merce.

### A2) Dope (Merci)

Ci sono 4 tipi di Dope, in quantità limitate: Camaleonte (14 pezzi), Rana (16
pezzi), Polpo (10 pezzi), Gufo (8 pezzi).

- Le Dope disponibili per l'acquisto sono impilate al centro di ogni
  Quartiere (max 3).
- Le Dope acquistate vanno posizionate nei Covi (max 3).
- Le Dope vendute vanno posizionate nei Punti di Vendita dei Clienti (max 3).

**Decisione (2026-07-30):** se una Dope acquistata, o recuperata da
un'Evasione, dovrebbe superare il limite di 3 pezzi per tipo nel Covo di
destinazione, l'azione avviene comunque e la Merce in eccesso va persa
(rimossa dal gioco).

### A3) Prices (Prezzi)

I Prezzi delle Dope iniziano da 3, 1, 4, 6, nell'ordine Camaleonte, Rana,
Polpo, Gufo (stesso ordine di §A2).

**Decisione (2026-07-30):** il prezzo di ciascun tipo di Dope non è un
intero libero, ma un indice su un **tracciato di valori ammessi**, specifico
per tipo. "Sale di 1" / "scende di 1" (§A3, §C3, §C4, §C5) significa uno
step lungo questo tracciato, non +1/-1 in dollari:

| Dope | Tracciato prezzi (min → max) | Prezzo iniziale |
|---|---|---|
| Camaleonte | 2, 3, 4, 6, 8 | 3 |
| Rana | 0, 1, 3, 5 | 1 |
| Polpo | 3, 4, 5, 7, 9, 11 | 4 |
| Gufo | 4, 6, 8, 10, 12, 14 | 6 |

Tutti i tipi iniziano al secondo valore del proprio tracciato (indice 1). Il
minimo è il primo valore del tracciato, il massimo l'ultimo.

I Prezzi salgono di uno step per ogni:
- Dope acquistata
- Dope requisita

I prezzi scendono di uno step per ogni:
- Dope venduta

Inoltre, con la free-action "Marketing" i giocatori possono far salire o
scendere i Prezzi (di uno step per Stonk, §D3).

Se tutti i Prezzi arrivano al massimo del proprio tracciato, crolla il
mercato e i Prezzi scendono tutti al minimo (indice 0) del proprio
tracciato.

### A4) Spot (Punti di Vendita)

Ciascun Cliente ha due Spot che indicano le Dope a cui è interessato.
Ogni Spot può contenere al massimo 3 Dope.

### A5) Links (Connessioni)

Ciascun Contact ha 3 Links, posizioni/status privilegiate che possono essere
prese dai Criminali. **Decisione (2026-07-30):** i 3 Links di un Contact
corrispondono a 3 slot distinti, uno per livello (Grinta 1, 2, 3); ogni slot
può contenere una sola pedina. Di conseguenza non può mai esistere una
parità di livello minimo tra Link dello stesso Contact (rilevante per §C5,
arresto Feds).

- Un Criminale che ha venduto Merci o vinto una Rissa in un Quartiere, può
  evolversi in un Link del relativo Cliente.
- Un giocatore che ha vinto un Poker evolve un suo Gambler in un Link presso
  i Preti.
- Il Criminale che entra per sesto in prigione, causando l'evasione, evolve
  in un Link dai Politici. **Decisione (2026-07-30):** evolve direttamente,
  senza passare dal Covo (vedi §A1 Jail).
- Quando si manda un Criminale su un Link lo si mette sulla Grinta 1, se il
  Link a Grinta 1 è occupato le pedine presenti scorrono a destra. Se una
  pedina esce dal tracciato, torna nel Covo.
- I Link contano come se fossero Criminali presenti in tutti i Quartieri del
  Cliente al fine di Acquistare, Vendere e Corrompere, e per le Risse.
- Un Link può essere speso per giocare una azione extra della relativa
  grinta, fra quelle del Cliente.
- Le azioni extra possono essere giocate al massimo una volta per turno, e
  possono essere potenziate dalle carte.
- Dopo aver usato l'azione extra il Link torna nel Covo.

### A6) Cops e Feds (Poliziotti e Detective)

Ci sono 2 tipi di poliziotti: Cops, che pattugliano i Quartieri, e Feds, che
indagano nei Punti di Vendita.

- Cops entrano in gioco in un Quartiere quando avviene una Rissa e quando si
  svuota/ricarica di Merci.
- Feds entrano in gioco in un Punto di Vendita quando questo si
  riempie/svuota di Merci.
- Cops e Feds hanno l'effetto di bloccare acquisti/vendite delle Merci.
- Cops in un Quartiere senza Merci o senza Criminali vengono rimandati al
  Commissariato. **Decisione (2026-07-30):** vanno in una riserva separata
  dai 6 slot dei Rats/Merci confiscate (non competono per lo spazio); il
  controllo che li rimanda in riserva viene rieseguito subito dopo ogni
  evento che ne cambia le condizioni, non solo a fine azione.
- Feds da un Cliente senza Merci e senza Ganci vengono rimandati al
  Commissariato (stessa decisione: riserva separata, controllo immediato).
- Più Cops o Feds possono stare nello stesso Quartiere/Punti di Vendita.

### A7) Base (Covo)

Il Covo è la plancia di ciascun giocatore.

- Nel Covo possono stare al massimo 3 Chip per tipo: Cops, Poker, Merci dei
  4 tipi. **Decisione (2026-07-30):** i Feds non hanno una categoria propria,
  condividono il conteggio con i Cops (limite 3 totale tra Cops+Feds nel
  Covo).
- Nel Covo si selezionano le azioni con le pedine Grinta.

### A8) Criminali

Le pedine giocate nei quartieri si chiamano Criminali. Possono diventare
Links, Gambler o Rats.

### A9) Carte

Nel gioco ci sono 3 tipi di carte:

**Carte Clienti**

Ciascun Cliente offre 20 carte che contengono:
- in basso, il potenziamento dell'azione base (ciascun Cliente potenzia un
  certo tipo di Azione);
- in alto a sinistra, due simboli da giocare per il Poker;
- in alto a destra, quattro simboli tra "stonk" e "pistole" da giocare per
  influenzare il mercato o per fare Rissa.

Le carte si giocano per ottenere solo uno degli effetti, e quando giocate
vengono scartate. Possono essere giocate più carte nello stesso turno. Alla
fine di ogni suo turno, ciascun giocatore può avere al massimo 5 carte in
mano.

**Carte Job**

Indicano i 9 diversi "Job" con cui le Gang guadagnano Reputazione. Ogni
giocatore ha tre pile di carte JOB suddivise per livello di difficoltà. Si
inizia il gioco rivelando JOB per livello. Quando un JOB viene portato a
termine, un altro JOB dello stesso livello viene scoperto. Ciascun Job è
associato ad 1 o 2 Clienti.

**Carte Retata**

7 carte che indicano un obiettivo generale, ossia come "non macchiare la
propria reputazione". In ogni partita ne entrano in gioco 3.

### A10) Jobs

Quando un giocatore completa un Job incassa una REP, posizionando un Token
sul tabellone sulla riga del Job. Può scegliere la colonna libera che
preferisce per incassare il relativo bonus tra: prendere una carta Skill,
prendere un Link o prendere 2 carte. Il colore della carta Job indica presso
quale Cliente raccogliere il bonus.

## B) Fasi

I 3 turni si compongono di 4 fasi. **Decisione (2026-07-30):** la partita ha
3 turni completi; i "4 giorni" dell'introduzione sono narrativi, non un
valore di regola.

### B1) Soffiata

Si scopre una carta Retata e il giocatore con il Link più alto con i Preti
sceglie il primo giocatore.

### B2) Azione

Per tre round ciascun giocatore:
- sposta un segnalino Grinta sopra una azione;
- se vuole, gioca una o più carte per potenziare l'azione scelta o per fare
  marketing;
- fa svolgere, a diversi Criminali, 1 azione per ogni Grinta;
- può fare un'azione extra, prima o dopo l'azione principale, spendendo un
  Link;
- scarta fino ad avere al massimo 5 carte in mano.

**Decisione (2026-07-30) — meccanica della Grinta:** ogni giocatore ha 3
segnalini Grinta, di valore fisso 1, 2 e 3 (non una singola pedina che si
sposta su un tracciato). In ciascuno dei suoi 3 round per turno, il
giocatore sceglie **uno** dei 3 segnalini e lo assegna a una delle 6 azioni
(§C1–C6). Il valore del segnalino indica **quante pedine Criminale/Link**
eseguono quell'azione nello stesso round, una ciascuna, ognuna nella
propria posizione: es. "compro con Grinta 3" → si scelgono 3 pedine in
gioco, e ciascuna acquista 1 Dope nel proprio Quartiere. *(Non ancora
confermato: se un segnalino usato in un round torni disponibile nei round
successivi dello stesso turno, o resti impegnato fino al turno seguente —
l'esempio dato implica 3 round e 3 segnalini distinti, quindi presumibilmente
ciascun segnalino si usa una sola volta per turno.)*

**Decisione (2026-07-30) — associazione Contact↔Azione:** le carte Cliente
potenziano l'azione base secondo questa mappa, che vale anche per il tipo di
azione extra ottenibile spendendo un Link di quel Contact (il livello del
Link determina la Grinta, cioè quante pedine, dell'azione extra):

| Contact | Azione base potenziata / azione extra da Link |
|---|---|
| Artisti | Comprare Dope, Vendere Dope |
| Studenti | Spostare Criminali |
| Manager | Piazzare Criminali |
| Politici | Corrompere Cops/Feds, Comprare Cops/Feds |
| Preti | Diverso dagli altri — vedi sotto |

I **Preti** sono un caso speciale:
- l'azione extra ottenuta spendendo un Link dei Preti può essere di
  **qualunque tipo tranne Comprare Cops/Feds**;
- le carte Preti non potenziano una singola azione fissa: ciascuna carta è
  associata a una singola azione specifica (diversa carta per carta, a
  copertura di tutte le 6 azioni);
- quando una carta Preti viene giocata, invece di potenziare un'azione
  lancia un Poker per fine round: chi la gioca incassa 3 dollari e mette la
  carta sul banco del Poker (banco che può contenere al massimo 2 carte per
  turno — coerente con `RULES_CANONICAL.md` §D2). Le carte Preti sono quindi
  le "carte Gamble" citate in §A9/§D2.

### B3) Poker

Alla fine di ogni turno si risolvono le carte Poker, se giocate, e si
assegna il primo giocatore del turno seguente.

### B4) Resa Dei Conti

Si verifica quali giocatori sono caduti nella Retata e macchiano la loro
reputazione.

## C) Azioni

### C1) Piazzare Criminali

- Si piazza un Criminale dal Covo in un Quartiere.
- Si pagano 2 dollari.
- Si pesca una carta relativa al Quartiere.

### C2) Spostare Criminali

- Un Criminale si sposta in un Quartiere adiacente o nel Den.
- Si pesca una carta del Quartiere o a scelta, nel Den.
- Non si può spostare lo stesso Criminale più volte nello stesso turno.

### C3) Acquistare Merce

- Si sceglie un Criminale in un Quartiere dove c'è almeno una Merce e non ci
  sono Cops.
- Si decide se giocare una carta per fare Marketing. Per ogni Stonk si può
  modificare di 1 il prezzo della merce prima o dopo l'acquisto. (Gli Stonk
  vengono distribuiti a piacere tra le merci acquistate nel turno)
- Si paga il Prezzo della Merce e il Prezzo della Merce sale di 1.
- Si sposta la Merce dal Quartiere nel Covo.
- Se non restano Merci nel Quartiere, questo viene ricaricato di 3 merci ed
  entra in gioco un Cops.

**Acquisto a pacchetto:** Se si comprano più merci nello stesso Quartiere
(con più Criminali) l'aumento dei prezzi si applica alla fine.

### C4) Vendere Merce

- Si sceglie un Criminale in un Quartiere e il relativo Punto di Vendita non
  occupato da Feds.
- Si decide se giocare una carta per fare Marketing. Per ogni Stonk si può
  modificare di 1 il prezzo della merce prima o dopo la vendita. (Gli Stonk
  vengono distribuiti a piacere tra le merci vendute nel turno)
- Si incassa il Prezzo della Merce e il Prezzo della Merce scende di 1.
- Si sposta la Merce dal Covo nel Punto di Vendita.
- Il Criminale che ha venduto può evolvere in un Link.
- Se il Punto di Vendita si riempie (3 Merci) viene svuotato ed entra in
  gioco un Feds.

**Vendita a pacchetto:** Se si vendono più merci dallo stesso Quartiere allo
stesso Punto di Vendita la riduzione dei prezzi si applica alla fine. Si
prende un solo Link del livello pari al numero di merci vendute.

### C5) Corrompere Cops e Feds

- Un Criminale/Link può pagare 2 dollari per corrompere un Cops o 3 dollari
  per corrompere un Feds.
- Un Rat può corrompere Cops ovunque.
- Quando un Cops viene corrotto svolge 2 diverse azioni tra le seguenti:
  - si sposta in un Quartiere adiacente;
  - arresta un Criminale a scelta nel Quartiere;
  - requisisce una Merce nel Quartiere (Prezzo della Merce sale di 1).
- Quando un Feds viene corrotto svolge 2 diverse azioni tra le seguenti:
  - si sposta in un Punto di Vendita adiacente;
  - arresta il Link di livello minore;
  - requisisce una Merce nel Punto di Vendita (Prezzo della Merce sale di 1).
- Criminali e Link arrestati entrano in Commissariato nella prima posizione
  disponibile e diventano Rats.
- Le merci requisite entrano in Commissariato nella prima posizione
  disponibile.

**Decisioni (2026-07-30):**
- le 2 azioni diverse della corruzione possono avere lo stesso bersaglio e
  sono risolte in sequenza: la seconda azione agisce sullo stato prodotto
  dalla prima (es. sposta poi arresta nel nuovo Quartiere);
- la parità di livello minimo tra Link per l'arresto del Feds non può
  verificarsi (vedi §A5: un solo Link per livello per Contact), quindi non
  serve una regola di scelta.

### C6) Comprare Cops e Feds

- I Criminali possono comprare Cops e Feds.
- Un Cops/Feds può essere comprato da Criminali/Link:
  - in un Quartiere/Punto di Vendita e piazzato nel proprio Covo;
  - nel Covo di un giocatore presente nel Quartiere e piazzato nel
    Quartiere (anche se stessi).
- Per comprare bisogna pagare 7 dollari.
- Il giocatore che perde un Cops/Feds dal Covo guadagna 7 dollari.
- Un Cops/Feds comprato, può essere scartato per sbirciare una delle retate
  future.

**Decisione (2026-07-30):** il proprietario non può opporsi alla vendita del
proprio Cops/Feds; se il compratore soddisfa i requisiti (presenza, 7
dollari), l'operazione va sempre a buon fine.

## D) Altre Regole

### D1) Fare Rissa

- La Rissa scatta quando si sposta il quinto Criminale in un Quartiere.
- Partecipano alla Rissa tutti i giocatori che hanno almeno un Criminale nel
  Quartiere.
- A partire dal giocatore alla sinistra di chi ha iniziato la Rissa, i
  partecipanti possono giocare una carta coperta (Pistole).
- Si rifà il giro scoprendo la carta e assegnando le Pistole a sé stessi
  (aggiunge Pistole) o a un altro partecipante (toglie Pistole).
- Si sommano Criminali + Links + Pistole.
- Si determinano vincitore e sconfitto.
- In caso di pareggio per determinare il vincitore, vince chi ha giocato
  meno Pistole, il giocatore che ha provocato la Rissa, il primo giocatore,
  o seguenti.
- In caso di pareggio per determinare lo sconfitto, perdono tutti.
- Il vincitore:
  - ruba 2 dollari o 1 carta ad ogni sconfitto;
  - può mandare un suo Criminale dal Quartiere sul primo Link del Cliente;
  - manda il Criminale sconfitto in un Quartiere inesplorato (si prende la
    relativa carta), se c'è, o nel Covo.
- Dopo una rissa un Cops entra in gioco nel Quartiere.

**Decisione (2026-07-30):** la forza (Criminali + Links + Pistole) può
scendere sotto zero; è una somma algebrica senza troncamento a zero.

### D2) Scommettere

- Le carte Gamble permettono di associare ad una azione base il lancio di
  una partita a Poker per fine turno. (Max 2 per turno)
- Il giocatore che lancia una partita posiziona la carta sul tabellone,
  incassa 3 dollari e manda un Criminale dal Covo nel Den, se c'è posto,
  pescando una carta.
- Alla fine del turno, a partire dal primo giocatore, ogni giocatore può
  puntare su 2, 1 o zero Poker in base a quanti Gamblers ha nel Den. Per
  puntare, posiziona una Chip sulle carte Poker su cui intende giocare.
- Finito il giro di puntate si risolvono le partite: a partire dalla prima
  carta Poker giocata, i giocatori che hanno puntato rivelano assieme una
  carta.
- Si vince nell'ordine con 5 colori uguali/diversi > Poker > Full > Tris >
  Doppia coppia > Coppia.
- In caso di pareggio i colori vincenti sono nell'ordine: arancione > grigio
  > blu > verde > rosa.
- In caso di ulteriore pareggio le Chip restano in gioco e si sommano alla
  posta del Poker successivo.
- In caso di vittoria, il vincitore:
  - incassa 2 dollari per ogni Chip;
  - mette una sua Chip nel Covo;
  - evolve un Gambler in un Link dei Preti.
- Gli sconfitti mandano il proprio Gambler in prigione.
- Un giocatore che ha già 3 Chip nel Covo, può giocare a poker rimuovendole
  dal Covo.
- Un giocatore può giocare una sola carta Gamble per Round.

**Decisione (2026-07-30) — costruzione della mano da 5 simboli:** esiste un
banco comune di 3 simboli, creato con carte Gamble, tutte e sole quelle dei
Preti. Ciascun giocatore che ha puntato aggiunge i propri 2 simboli
(rivelando la propria carta) al banco comune, per un totale di 5 simboli da
valutare secondo il ranking sopra descritto.

### D3) Marketing

Quando si compra o vende si può scartare una carta per usare gli Stonk. Per
ogni Stonk si può modificare di 1 il prezzo di una delle merci in acquisto o
vendita, prima o dopo lo svolgimento dell'azione. Gli Stonk vengono
distribuiti a piacere tra le merci trattate nel turno.

### D4) Retate

- A inizio del turno viene scoperta una carta Retata.
- Il giocatore che ha il Link di più alto livello con i Preti (ne c'è
  almeno uno) decide il primo giocatore e quindi le squadre che
  affronteranno la Retata: il primo e il quarto giocatore vs il secondo e
  il terzo.
- Alla fine del turno i giocatori che cadono nella Retata macchiano la loro
  reputazione.
- La prima Retata macchia 1 Reputazione, la seconda 2, la terza 3.

*(vedi RULES_PENDING — condizioni complete delle 7 carte Retata; scelta del
primo giocatore quando nessuno ha Link ai Preti)*

### D5) Macchiare REP

- Una REP macchiata viene indicata girando il token sul tabellone. Quella
  REP varrà 1 solo punto a fine partita.
- Una REP può venire macchiata a seguito di una retata persa.
- I giocatori con 2 dollari o meno possono macchiarsi una REP per incassare
  5 dollari.
- Le REP macchiate non possono essere ripristinate.

### D6) Condizione di Vittoria

A fine partita il tracciato dei soldi si trasforma nel tracciato punti:

- i birilli vengono spostati a inizio track nell'ordine in cui sono, nelle
  posizioni 1, 2, 3, 4. Nei pareggi si prende la posizione più in basso;
- si assegnano 2 punti per ogni REP o 1 per ogni REP macchiata;
- si assegna un punto per ogni maggioranza presso i clienti (Criminali
  valgono 1, Link 2), i pareggi si annullano;
- si assegna un punto per ogni 3 fiches, anche miste, nel Covo;
- si assegna un punto per ogni Skill.

Vince chi ha più punti. In caso di pareggio vince chi ha più REP non
macchiate. In caso di ulteriore pareggio la vittoria è condivisa.

**Decisione (2026-07-30):** la posizione sul tracciato denaro assegna punti
propri, da sommare a REP/maggioranze/chips/skill. *(vedi RULES_PENDING — i
punti esatti per ciascuna delle 4 posizioni non sono ancora noti)*

## E) Setup

Sezione non presente nel documento `how_to_play_v056` originale; dati
forniti direttamente dal game designer in chat il 2026-07-30.

### E1) Denaro e pedine

- Ogni giocatore parte con **15 dollari**.
- Ogni giocatore ha **10 pedine Criminale** in totale (nel Covo a inizio
  partita).

### E2) Carte iniziali

Si forma un mazzetto con 3 carte di ciascun Contact (mescolate insieme).
Ogni giocatore pesca **3 carte** da questo mazzetto. Le carte avanzate
(mazzetto − 3 × numero giocatori) tornano nei rispettivi mazzi dei Contact
di provenienza. *(Il numero totale di Contact, e quindi la dimensione del
mazzetto, sarà confermato con la sezione Mappa — vedi `RULES_PENDING.md`.)*

### E3) Dope iniziali nel Covo

Ogni giocatore parte con **2 Dope** nel Covo, assegnate per ordine di seggio
(seat 1–4):

| Seggio | Dope iniziali |
|---|---|
| 1 | Rana + Polpo |
| 2 | Camaleonte + Polpo |
| 3 | Rana + Gufo |
| 4 | Camaleonte + Gufo |

Chips Cops/Poker iniziali nel Covo: non specificato esplicitamente,
presumibilmente 0 (coerente con l'assenza di Cops/Feds e Poker in corso a
inizio partita) — da confermare.

### E4) Hoods e mercato iniziale

- Ci sono **5 Quartieri scoperti** a inizio partita, uno per Cliente,
  ciascuno con **3 Dope** nel proprio mercato (i tipi esatti dipendono dal
  Cliente — vedi sezione Mappa, ancora da fornire).
- Ci sono **5 Quartieri coperti**, inizialmente vuoti/non rivelati.
- Un Quartiere coperto si attiva quando un Criminale sconfitto in una Rissa
  viene mandato lì (vedi `RULES_CANONICAL.md` §D1, "Quartiere inesplorato"):
  si rivela flippando una **tile rotonda** posta sul Quartiere, che indica
  quante Dope caricare nel mercato (1–3) ed eventualmente se entra un Cops.

### E5) Cops e Feds iniziali

Nessun Cops o Feds è presente sulla mappa a inizio partita; entrano solo
durante il gioco secondo le regole di §A6.

### E6) Primo giocatore

Il primo giocatore del turno 1 è scelto **casualmente**. Dal turno 2 in poi
si applica la regola di §B1/§D4 (Link più alto con i Preti).

### E7) Piazzamento iniziale dei Criminali

Ogni giocatore piazza **3 dei suoi 10 Criminali** durante il setup (gli
altri 7 restano nel Covo). Per ciascuna delle 3 carte pescate in E2, si
piazza un Criminale nel Quartiere scoperto del Contact corrispondente a
quella carta. Esempio: 2 carte "Manager" + 1 carta "Preti" → 2 Criminali nel
Quartiere scoperto del Manager, 1 Criminale nel Quartiere scoperto dei
Preti. *(Conferma che Preti, e presumibilmente Politici, hanno anch'essi un
Quartiere scoperto con mercato proprio tra i 5 iniziali — da confermare con
la sezione Mappa.)*

## F) Mappa

Dati forniti dal game designer in chat il 2026-07-31.

### F1) Quartieri e Contact

Ogni Contact ha esattamente 2 Hoods: uno **scoperto** (mercato attivo fin
dall'inizio) e uno **coperto** (si rivela con una tile rotonda quando un
Criminale sconfitto in Rissa vi viene mandato, vedi §E4).

| Hood | Contact | Stato iniziale | Dope iniziali |
|---|---|---|---|
| Q1 | Artisti | Scoperto | 3× Rana |
| Q2 | Artisti | Coperto | — (tile da rivelare) |
| Q3 | Studenti | Scoperto | 3× Gufo |
| Q4 | Studenti | Coperto | — (tile da rivelare) |
| Q5 | Manager | Scoperto | 3× Rana |
| Q6 | Manager | Coperto | — (tile da rivelare) |
| Q7 | Preti | Scoperto | 3× Camaleonte |
| Q8 | Preti | Coperto | — (tile da rivelare) |
| Q9 | Politici | Scoperto | 3× Polpo |
| Q10 | Politici | Coperto | — (tile da rivelare) |

### F2) Adiacenze — PROVVISORIO, da confermare

Trascrizione letterale di quanto fornito, con due note: la lista conteneva
due righe "4 con ..." — la seconda è stata interpretata come "5 con ..."
(refuso plausibile, dato che altrimenti Q5 non avrebbe adiacenze). Inoltre
due coppie risultano asimmetriche (A adiacente a B ma B non elenca A tra le
sue adiacenze) — segnalate sotto. **Non trattare questa tabella come
definitiva finché non confermata.**

| Hood | Adiacenti (come forniti) |
|---|---|
| Q1 | Q2, Q3 |
| Q2 | Q1, Q3, Q4, Q6 ⚠️ |
| Q3 | Q1, Q2, Q4, Q5 |
| Q4 | Q2, Q3, Q5, Q6, Q7 |
| Q5 | Q3, Q4, Q7, Q9 ⚠️, Q10 *(riga "4 con 3 4 7 9 10" interpretata come Q5)* |
| Q6 | Q3, Q4, Q7, Q8 |
| Q7 | Q4, Q5, Q6, Q8, Q9 |
| Q8 | Q6, Q7, Q9 |
| Q9 | Q7, Q8, Q10 |
| Q10 | Q5, Q9 |

⚠️ **Asimmetrie da chiarire:**
- Q2 elenca Q6 come adiacente, ma Q6 non elenca Q2.
- Q5 (dedotto) elenca Q9 come adiacente, ma Q9 non elenca Q5.

### F3) Spots dei Contact

*(vedi RULES_PENDING — quali 2 tipi di Dope accetta ciascun Contact, e
adiacenze tra Spots per i Feds, ancora da fornire)*

## Stato

Sezioni A–D trascritte integralmente dal documento fornito il 2026-07-30.
Le ambiguità di risoluzione (interazioni tra regole) sono state chiuse lo
stesso giorno con decisioni del game designer, annotate inline come
"Decisione (2026-07-30)" nelle sezioni sopra; dettagli completi in
`RULE_CHANGELOG.md`.

Nessuna sezione di Setup dettagliato, mappa, Contacts/Spots, dataset carte,
Jobs/Skills, carte Retata o valori di punteggio del tracciato denaro era
presente nel documento ricevuto: questi contenuti restano da acquisire e
sono tracciati in `RULES_PENDING.md`.
