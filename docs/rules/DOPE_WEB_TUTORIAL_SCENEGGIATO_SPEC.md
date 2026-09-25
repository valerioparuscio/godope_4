# DOPE Web — Tutorial interattivo sceneggiato

> **Correzioni applicate (2026-09-26)**, confermate dal game designer dopo
> verifica diretta contro il motore (`backend/src/dope_engine/rules/
> turn_flow.py::start_tip_off`, `application/legal_actions.py::
> _brawl_reward_decision`) — la versione originale di questo documento
> conteneva due imprecisioni corrette qui:
>
> 1. **Primo Giocatore (§3.2, Scena 4, Scena 38):** non "chi ha il Gancio
>    di rango più alto diventa automaticamente Primo Giocatore". Solo chi
>    possiede il Link **più alto presso i Preti** (non un Gancio
>    qualsiasi) **sceglie** chi sarà il Primo Giocatore — può scegliere
>    anche un altro giocatore, non necessariamente sé stesso. Se nessuno
>    ha un Link dai Preti, resta Primo Giocatore chi lo era nel turno
>    precedente. Nel motore questo è **lo stesso momento** in cui si
>    rivela la Retata del turno (`ActiveStep.WAITING_FOR_RAID_RESOLUTION`),
>    non due meccaniche separate.
> 2. **Ordine premi Rissa (Scene 19-21):** il motore risolve nell'ordine
>    Ricompensa (2$/carta, per ogni sconfitto) → Gancio → Scacciare, non
>    Gancio → Ricompensa → Scacciare. Le scene 19 e 20 sono state scambiate
>    di conseguenza in questo documento (i numeri restano stabili come
>    slot di sequenza, i contenuti sono scambiati).
>
> Il resto del documento è invariato rispetto alla versione originale.

## Obiettivo

Implementare un tutorial interattivo per **DOPE Web** che NON funzioni come un regolamento da leggere, ma come una **partita tutorial sceneggiata**.

Il giocatore deve imparare le regole osservando e compiendo azioni in stati di gioco preparati.

Principio base:

```text
MOSTRA → FAI FARE → MOSTRA LA CONSEGUENZA
```

Ogni schermata deve insegnare una sola idea principale.

Le regole complesse devono essere spezzate in più schermate consecutive mantenendo lo stesso stato di gioco, così che il giocatore possa capire:

```text
causa → scelta → effetto
```

Esempio:

```text
Muovi un Criminale
→ il movimento fa scattare una Rissa
→ giochi Pistole
→ vinci la Rissa
→ scegli la ricompensa
→ scegli un Gancio
→ mandi via gli sconfitti
```

---

# 1. Filosofia UX

Il tutorial deve essere costruito come una vera sequenza di situazioni di gioco.

NON creare:

- pagine teoriche lunghe;
- schermate enciclopediche;
- spiegazioni astratte scollegate dal board;
- quiz obbligatori;
- domande del tipo "Hai capito?".

Preferire sempre:

- board visibile;
- stato partita preparato;
- pochi elementi evidenziati;
- testo breve;
- un'azione concreta da eseguire;
- conseguenza immediatamente visibile.

Il tutorial deve sembrare una partita semplificata e controllata.

---

# 2. Tipi di schermata

Usare principalmente due tipi di scene.

## 2.1 FAI

Il giocatore deve compiere un'azione corretta.

Caratteristiche:

- elementi validi evidenziati;
- elementi non validi oscurati o disabilitati;
- il tutorial prosegue solo dopo l'azione richiesta;
- eventuali click errati non devono modificare lo stato.

Esempio:

```text
Muovi il Criminale illuminato nel quartiere evidenziato.
```

## 2.2 GUARDA

Il giocatore osserva uno stato preparato.

Caratteristiche:

- nessun input obbligatorio oltre a "Continua";
- board, carta, punteggi o area rilevante evidenziati;
- usare zoom o focus visivo;
- testo molto breve.

Esempio:

```text
Questa è la Retata corrente.
Alla fine del Round determinerà cosa conterà nella Resa dei Conti.
```

---

# 3. Regole aggiornate obbligatorie

Queste regole hanno priorità su eventuali versioni precedenti.

## 3.1 Struttura partita

La partita dura:

```text
3 Turni
3 Round per Turno
```

Totale:

```text
9 Round
```

## 3.2 Primo Giocatore

Il Primo Giocatore viene **scelto all'inizio di ogni nuovo Turno**, nello
stesso momento in cui si rivela la Retata del turno.

```text
Solo chi possiede il Link più alto presso i Preti sceglie
chi sarà il Primo Giocatore (può scegliere sé stesso o un altro).
Se nessuno ha un Link dai Preti, resta Primo Giocatore
chi lo era nel turno precedente.
```

Il tutorial deve mostrare questa regola in modo visivo, insieme alla
rivelazione della Retata (sono lo stesso momento di gioco).

Esempio:

```text
Nuovo Turno. Si rivela la Retata.
Il tuo Link di rango 2 dai Preti è il più alto in gioco:
scegli tu chi sarà il Primo Giocatore di questo Turno.
```

Non usare versioni precedenti della regola del Primo Giocatore (in
particolare: non è un confronto automatico tra i Ganci di qualsiasi
Contact, ed è una scelta, non un'assegnazione automatica).

## 3.3 Jail

La Jail ha:

```text
4 posti
```

Quando entra il quarto prigioniero:

```text
scatta immediatamente l'Evasione
```

Regola da mostrare chiaramente:

```text
4° prigioniero = Evasione
```

## 3.4 Poker

Il Poker:

```text
può essere lanciato 1 sola volta
```

e viene risolto:

```text
alla fine di ogni Round
```

NON alla fine del Turno.

---

# 4. Struttura narrativa del tutorial

Il tutorial deve seguire una progressione comprensibile per un giocatore nuovo.

Ordine logico:

```text
1. Ambientazione
2. Obiettivo
3. Modi di fare Respect
4. Turni / Round
5. Primo Giocatore (e rivelazione Retata, stesso momento)
6. Grinta
7. Jobs
8. Retate
9. Dove possono stare i Criminali
10. Azioni base
11. Conseguenze delle azioni
12. Risse
13. Ganci
14. Commercio
15. Cops / Feds
16. Jail
17. Den / Poker
18. Carte
19. Fine Round
20. Punteggio finale
```

---

# 5. Sequenza tutorial proposta

Implementare una prima versione da circa:

```text
28-32 schermate
```

La seguente sequenza estesa è quella di riferimento.

## SCENA 1 — Ambientazione

Tipo: `GUARDA`

Stato:
- board completo;
- quartieri visibili;
- alcuni Criminali e Ganci già presenti;
- leggere evidenziazioni animate.

Testo:

> **Benvenuto in DOPE.**  
> Quattro gang si contendono la città: muovono Criminali, fanno affari, costruiscono Ganci e cercano di aumentare il proprio Respect.  
> Ma tra Cops, Risse, Poker e Retate, la città non resta tranquilla a lungo.

CTA: `Continua`

## SCENA 2 — Obiettivo

Tipo: `GUARDA`

Stato:
- esempio di pannello punteggio finale;
- highlight sequenziale delle voci.

Testo:

> **L'obiettivo è ottenere più Respect degli altri Boss.**  
> Puoi costruirlo in modi diversi: REP, denaro, controllo dei Contacts, Chips e Skill.  
> Non devi fare tutto: puoi costruire la tua strategia.

## SCENA 3 — Struttura della partita

Tipo: `GUARDA`

Stato:

```text
Turno 1 → Round 1 → Round 2 → Round 3
Turno 2 → Round 1 → Round 2 → Round 3
Turno 3 → Round 1 → Round 2 → Round 3
```

Testo:

> Una partita dura **3 Turni**.  
> Ogni Turno contiene **3 Round**.  
> Il contatore in alto ti dice sempre in quale Turno e Round ti trovi.

## SCENA 4 — Primo Giocatore e Retata

Tipo: `GUARDA`

Stato:
- nuovo Turno appena iniziato;
- Retata del turno rivelata;
- Link ai Preti dei 4 giocatori mostrati;
- evidenzia il rango più alto.

Testo:

> All'inizio di ogni nuovo Turno si rivela la Retata e si sceglie il **Primo Giocatore**.  
> Chi ha il Link più alto presso i Preti decide chi sarà il Primo Giocatore — anche un altro giocatore, non per forza sé stesso.  
> Se nessuno ha un Link dai Preti, resta Primo Giocatore chi lo era prima.

Visual:

```text
Link Preti rango 2 (il più alto) → SCEGLIE il Primo Giocatore
```

## SCENA 5 — Ordine di gioco

Tipo: `GUARDA`

Stato:
- indicatore ordine giocatori.

Testo:

> Il Primo Giocatore agisce per primo.  
> Gli altri seguono nell'ordine indicato.  
> L'ordine è anche quello usato per dividere le squadre nella Retata.

## SCENA 6 — Grinta

Tipo: `GUARDA`

Stato:

```text
MUOVERE     3
COMPRARE    2
CORROMPERE  1
```

Testo:

> La **Grinta** dice quanto insisti su un'azione.  
> Hai assegnato Grinta 3 al Movimento: quando scegli questa azione puoi muovere fino a 3 tuoi Criminali.

## SCENA 7 — Grinta in azione

Tipo: `FAI`

Stato:
- 3 Criminali validi evidenziati;
- contatore `Movimenti disponibili: 0 / 3`.

Testo:

> Hai Grinta 3 nel Movimento.  
> Muovi il primo Criminale illuminato.

Dopo l'azione mostra `1 / 3`.

## SCENA 8 — Job

Tipo: `GUARDA`

Stato:
- zoom carta Job corrente;
- requisiti visivamente collegati al board.

Testo:

> Questo è un **Job**.  
> È un obiettivo che puoi completare durante la partita.  
> Le tue normali mosse possono quindi servire anche a costruire REP.

## SCENA 9 — Completare un Job

Tipo: `GUARDA`

Stato:
- Job quasi completato;
- ultimo requisito diventa valido;
- traccia REP evidenziata.

Testo:

> Hai soddisfatto i requisiti del Job.  
> Completarlo ti fa ottenere **REP** e può darti altre ricompense.

## SCENA 10 — Retata: anticipazione

Tipo: `GUARDA`

Stato:
- zoom carta Retata attuale (la stessa rivelata alla Scena 4);
- board visibile sullo sfondo.

Testo:

> Questa è la **Retata corrente**.  
> Quando arriverà la Resa dei Conti, la carta dirà cosa sarà importante.  
> Tienila d'occhio: le mosse che fai ora possono aiutarti dopo.

Non spiegare ancora completamente la Retata.

## SCENA 11 — Dove possono stare i Criminali

Tipo: `GUARDA`

Stato:
- Criminale in Hood;
- Gancio presso Contact;
- Gambler nel Den;
- Rat in Jail.

Testo:

> I tuoi uomini possono trovarsi in situazioni molto diverse.  
> Nel quartiere sono Criminali attivi. Presso un Contact possono diventare **Ganci**.  
> Nel Den diventano **Gambler**. Se vengono arrestati finiscono in **Jail**.

## SCENA 12 — Piazzare un Criminale

Tipo: `FAI`

Stato:
- Criminale nel Covo evidenziato;
- destinazioni valide illuminate.

Testo:

> Cominciamo a giocare.  
> Clicca sul Criminale illuminato e poi su uno dei quartieri disponibili.

## SCENA 13 — Muovere un Criminale

Tipo: `FAI`

Stato:
- Criminale già su board;
- quartiere adiacente evidenziato.

Testo:

> Ora muovilo.  
> Clicca sul Criminale e poi sul quartiere illuminato.

## SCENA 14 — Pescare una carta

Tipo: `GUARDA`

Stato:
- movimento appena completato;
- carta pescata appare;
- Contact associato evidenziato.

Testo:

> Entrare in questo quartiere ti fa pescare una carta del Contact associato.  
> Le carte hanno molti usi. Tra poco ne useremo una.

## SCENA 15 — Movimento che scatena una Rissa

Tipo: `FAI`

Stato:
- quartiere quasi pieno;
- Criminale del giocatore pronto a entrare.

Testo:

> Muovi il Criminale illuminato nel quartiere evidenziato.

Il movimento deve far scattare automaticamente la Rissa.

## SCENA 16 — Scoppia la Rissa

Tipo: `GUARDA`

Stato:
- quartiere lampeggia;
- giocatori coinvolti evidenziati.

Testo:

> Il quartiere è diventato troppo affollato: **scoppia una Rissa**.  
> Ogni Boss coinvolto conta la propria forza presente qui.

## SCENA 17 — Pistole

Tipo: `FAI`

Stato:
- mano del giocatore;
- una carta con Pistole illuminata.

Testo:

> Le **Pistole** sulle carte aumentano la tua forza nella Rissa.  
> Criminali, Ganci e Pistole si sommano — le Pistole della tua carta vanno sempre a te.  
> Gioca la carta illuminata.

## SCENA 18 — Risultato della Rissa

Tipo: `GUARDA`

Stato:

```text
TU
3 presenza + 2 Pistole = 5

AVVERSARIO
4 presenza = 4
```

Testo:

> Hai vinto **5 a 4**.  
> Il vincitore della Rissa può ora sfruttare il controllo ottenuto.

## SCENA 19 — Ricompensa Rissa

Tipo: `FAI`

Stato:

```text
PRENDI 2$
PRENDI 1 CARTA
```

Testo:

> Il vincitore può prendere qualcosa a ogni sconfitto.  
> Scegli: **2$ oppure 1 carta**.

## SCENA 20 — Creare un Gancio

Tipo: `FAI`

Stato:
- pedine eleggibili illuminate.

Testo:

> Puoi trasformare una delle pedine evidenziate in un **Gancio** presso questo Contact.  
> Scegline una (o passa).

Dopo il click:
- mostra chiaramente la trasformazione;
- mostra il rango del Gancio.

## SCENA 21 — Mandare via gli sconfitti

Tipo: `FAI`

Stato:
- quartieri inesplorati validi evidenziati;
- sconfitto selezionato.

Testo:

> Ora decidi dove mandare gli sconfitti.  
> I quartieri evidenziati sono destinazioni valide.  
> Scegline uno.

## SCENA 22 — Utilità dei Ganci

Tipo: `GUARDA`

Stato:
- Gancio appena creato;
- Contact evidenziato;
- rango visibile.

Testo:

> Un **Gancio** rappresenta un'influenza stabile presso un Contact.  
> I Ganci contano per il controllo e possono darti vantaggi durante la partita.

## SCENA 23 — Azione extra tramite Gancio

Tipo: `FAI`

Stato:
- azioni normali già esaurite;
- Gancio utilizzabile evidenziato.

Testo:

> Hai già usato le tue azioni normali.  
> Questo Gancio può darti un'azione extra.  
> Clicca sul Gancio illuminato.

## SCENA 24 — Comprare Dope

Tipo: `FAI`

Stato:
- Criminale presso mercato valido;
- merce acquistabile illuminata;
- prezzo mostrato chiaramente.

Testo:

> I Criminali servono anche a fare affari.  
> Qui puoi comprare Dope.  
> Clicca sulla merce illuminata per acquistarla al prezzo corrente.

## SCENA 25 — Il prezzo cambia

Tipo: `GUARDA`

Stato:
- animazione prezzo prima/dopo.

Testo:

> Gli acquisti modificano il mercato.  
> Più una merce viene richiesta, più il suo prezzo può salire.  
> Controlla sempre il nuovo prezzo.

## SCENA 26 — Vendere Dope

Tipo: `FAI`

Stato:
- Criminale presso Spot compatibile;
- Dope posseduta illuminata.

Testo:

> Ora rivendiamola.  
> Questo Spot accetta la merce che possiedi.  
> Seleziona la Dope e completa la vendita.

## SCENA 27 — Cops e Feds

Tipo: `GUARDA`

Stato:
- situazione in cui Cop o Fed blocca un'azione;
- elemento bloccato evidenziato.

Testo:

> Non sempre puoi agire liberamente.  
> **Cops e Feds** possono bloccare determinate azioni o aree.  
> Quando succede, devi prima occuparti di loro.

## SCENA 28 — Corruzione

Tipo: `FAI`

Stato:
- Cop/Fed cliccabile;
- costo mostrato.

Testo:

> Questo agente può essere corrotto.  
> Selezionalo e paga il costo indicato.

## SCENA 29 — Jail

Tipo: `GUARDA`

Stato:
- Jail con tre posti occupati;
- quarto Criminale arrestato pronto a entrare.

Visual:

```text
[1] [2] [3] [4]
```

Testo:

> Un Criminale arrestato finisce in Jail.  
> La Jail ha solo **4 posti**.  
> Ora sta entrando il quarto prigioniero...

## SCENA 30 — Evasione

Tipo: `GUARDA`

Stato:
- quarto slot occupato;
- evasione animata.

Testo:

> Il quarto ingresso fa scattare immediatamente un'**Evasione**.  
> Ricorda: **4° prigioniero = EVASIONE.**

## SCENA 31 — Den e Gambler

Tipo: `FAI`

Stato:
- Criminale eleggibile;
- Den evidenziato.

Testo:

> Non tutti gli uomini devono restare per strada.  
> Entra nel Den con il Criminale illuminato.  
> Da questo momento diventa un **Gambler** e può partecipare al Poker.

## SCENA 32 — Lanciare il Poker

Tipo: `FAI`

Stato:
- Gambler nel Den;
- comando Poker disponibile.

Testo:

> Ora puoi lanciare il **Poker**.  
> Il Poker può essere lanciato **una sola volta**.  
> Avvialo.

## SCENA 33 — Poker e fine Round

Tipo: `GUARDA`

Stato:
- Poker aperto;
- timeline Round quasi concluso.

Testo:

> Il Poker non si risolve subito.  
> Resta aperto fino alla fine del Round.  
> Quando il Round termina, si determina il risultato.

## SCENA 34 — Le carte e i loro usi

Tipo: `GUARDA`

Stato:
- mostrare 4 carte preparate;
- highlight successivo di Pistole, Poker, Stonk, Potenziamento.

Testo:

> Finora hai già usato le carte in modi diversi.  
> Una carta può aiutarti in una Rissa con le Pistole, nel Poker, nel Marketing con gli Stonk o a potenziare alcune azioni.  
> Decidere quando usarla è parte della strategia.

## SCENA 35 — Fine Round

Tipo: `GUARDA`

Stato:
- contatore Round passa al successivo;
- Poker si risolve.

Testo:

> Il Round è finito.  
> Ora si risolvono gli effetti che aspettavano la sua conclusione.  
> Tra questi c'è il Poker.

## SCENA 36 — Retata a squadre

Tipo: `GUARDA`

Stato:
- carta Retata corrente zoomata (la stessa delle Scene 4 e 10);
- 4 giocatori divisi nelle squadre previste dal gioco;
- valori rilevanti evidenziati.

Testo:

> Ora arriva la **Resa dei Conti della Retata**.  
> I Boss non combattono da soli: vengono divisi in due squadre.  
> La carta Retata indica cosa viene confrontato.

## SCENA 37 — Risoluzione Retata

Tipo: `GUARDA`

Stato:
- due squadre visive;
- conteggio richiesto dalla carta;
- squadra vincente evidenziata.

Testo:

> Confrontiamo i valori richiesti dalla carta.  
> La squadra con il risultato migliore vince la Retata.  
> Le conseguenze dipendono dalla Retata in corso.

## SCENA 38 — Nuovo Turno / nuovo Primo Giocatore

Tipo: `GUARDA`

Stato:
- fine Turno;
- nuovo Turno;
- nuova Retata rivelata;
- confronto dei Link ai Preti dei giocatori.

Testo:

> È iniziato un nuovo Turno: si rivela una nuova Retata.  
> Per scegliere il Primo Giocatore si guarda chi ha il Link più alto dai Preti.  
> Quel giocatore **sceglie** chi sarà il nuovo Primo Giocatore — anche un altro, non per forza sé stesso.

Questa scena deve far vedere la regola una seconda volta nel momento naturale in cui si applica (stesso meccanismo della Scena 4).

## SCENA 39 — Fine partita / scoring

Tipo: `GUARDA`

Stato:
- schermata punteggio finale;
- voci evidenziate una alla volta.

Testo:

> Alla fine della partita si calcola il **Respect**.  
> Contano più fonti: REP, denaro, controllo dei Contacts, Chips e Skill.  
> La strategia sta nel combinarle meglio degli altri Boss.

## SCENA 40 — Chiusura

Tipo: `GUARDA`

Stato:
- board completo;
- pulsante nuova partita.

Testo:

> Hai visto i meccanismi fondamentali di DOPE.  
> Ora sai muovere la tua Gang, fare affari, costruire Ganci, gestire Risse, Poker, Jobs e Retate.  
> Il resto lo scoprirai giocando.

CTA:

```text
INIZIA UNA PARTITA
```

---

# 6. Approccio tecnico

Il tutorial deve usare stati controllati.

Non è necessario che ogni scena derivi da una vera partita giocata dall'inizio.

È preferibile predisporre snapshot/scenari.

Esempio:

```ts
interface TutorialScenario {
  id: string;
  state: GameState;
  step: TutorialStep;
}
```

---

# 7. Modello di uno step

Suggerimento:

```ts
type TutorialStepType = "observe" | "action";

interface TutorialStep {
  id: string;
  type: TutorialStepType;

  title?: string;
  text: string;

  highlight?: HighlightTarget[];

  allowedActions?: TutorialAllowedAction[];

  requiredAction?: TutorialExpectedAction;

  boardFocus?: BoardFocus;

  nextStep: string | null;
}
```

---

# 8. Azioni consentite

Durante le schermate `FAI`:

- disabilitare azioni non previste;
- non permettere al giocatore di rompere lo scenario;
- evidenziare gli elementi cliccabili;
- validare l'azione richiesta.

Esempio:

```ts
requiredAction: {
  type: "MOVE_CRIMINAL",
  criminalId: "tutorial_player_c1",
  destinationId: "hood_4"
}
```

---

# 9. Evidenziazione UI

Supportare almeno:

```text
pulse
outline
dimOthers
arrow
tooltip
zoom
```

Esempio:

```ts
highlight: [
  {
    type: "piece",
    id: "criminal_12",
    effect: "pulse"
  },
  {
    type: "hood",
    id: "hood_4",
    effect: "outline"
  }
]
```

---

# 10. Zoom contestuali

Per le scene `GUARDA` usare zoom/focus su:

```text
Carta Job
Carta Retata
Jail
Den
Contact
Mercato
Spot
Carta giocata
Gancio
Punteggio
```

La descrizione testuale deve essere sempre collegata visivamente all'elemento di cui sta parlando.

---

# 11. Testi brevi

Regola editoriale:

Ogni schermata dovrebbe avere idealmente:

```text
20-50 parole
```

Massimo consigliato:

```text
70 parole
```

Se una regola richiede più testo, dividerla in più scene.

NON usare scroll lunghi.

---

# 12. Controllo del flusso

UI minima:

```text
[Indietro]   16 / 40   [Continua]
```

Per scene `FAI`, `Continua` deve essere disabilitato fino al completamento dell'azione, salvo casi specifici.

---

# 13. Skip

Prevedere:

```text
SALTA TUTORIAL
```

con conferma leggera:

```text
Vuoi uscire dal tutorial?
```

Non obbligare un giocatore esperto a completarlo.

---

# 14. Replay

Il tutorial deve poter essere rilanciato dal menu principale.

Voce:

```text
TUTORIAL
```

oppure:

```text
COME SI GIOCA
```

---

# 15. Reset

Ogni scena deve poter ripristinare lo stato iniziale dello scenario.

Questo è utile se:

- il giocatore compie un input anomalo;
- si verificano errori;
- il tutorial viene riaperto;
- si torna indietro.

---

# 16. Nessuna modifica involontaria al gioco reale

Il tutorial deve usare un contesto separato.

Non deve:

- salvare statistiche come partita reale;
- influenzare leaderboard;
- scrivere eventi reali nel database;
- assegnare vittorie;
- cambiare profilo;
- interferire con multiplayer reale.

Preferire:

```text
tutorialMode = true
```

---

# 17. Regole da rinforzare due volte

## Ganci

Prima:

```text
ottenere un Gancio dopo una Rissa
```

Poi:

```text
usarlo per un vantaggio / azione extra
```

## Primo Giocatore

Prima:

```text
spiegazione iniziale (Scena 4, insieme alla Retata)
```

Poi:

```text
nuovo Turno → nuova Retata → chi ha il Link più alto dai Preti sceglie → nuovo Primo Giocatore (Scena 38)
```

## Retata

Prima:

```text
mostrare la carta come obiettivo futuro (Scena 10)
```

Poi:

```text
risolverla realmente a squadre (Scene 36-37)
```

## Carte

Prima:

```text
pescare una carta
```

Poi:

```text
usare Pistole
```

Infine:

```text
riepilogo dei diversi utilizzi
```

---

# 18. Priorità didattica

Il tutorial deve privilegiare:

```text
capire cosa cliccare
capire perché
vedere cosa succede
```

rispetto a:

```text
conoscere tutte le eccezioni
```

Le eccezioni possono restare nel regolamento completo.

---

# 19. Prima implementazione minima

Se 40 scene sono troppe per una prima release, implementare inizialmente questo core di circa 30 scene:

```text
1 Ambientazione
2 Obiettivo
3 Turni/Round
4 Primo Giocatore (e Retata)
6 Grinta
8 Job
10 Retata anticipazione
11 Location Criminali
12 Piazzamento
13 Movimento
14 Carta
15 Movimento → Rissa
16 Rissa
17 Pistole
18 Risultato
19 Ricompensa
20 Gancio
21 Scacciare
24 Comprare
25 Prezzo
26 Vendere
27 Cops/Feds
29 Jail
30 Evasione
31 Den
32 Poker
33 Poker fine Round
34 Carte
35 Fine Round
36 Retata
38 Nuovo Turno / Primo Giocatore
39 Scoring
40 Chiusura
```

---

# 20. Acceptance criteria

La feature è accettabile quando:

- [ ] il tutorial appare come una partita guidata;
- [ ] esistono scene `FAI`;
- [ ] esistono scene `GUARDA`;
- [ ] ogni scena insegna una sola idea principale;
- [ ] gli elementi validi vengono evidenziati;
- [ ] gli input non previsti sono bloccati;
- [ ] il movimento viene insegnato con click su pedina + destinazione;
- [ ] una scena di movimento fa scattare una Rissa;
- [ ] il giocatore usa una carta Pistole;
- [ ] il risultato della Rissa viene mostrato numericamente;
- [ ] il vincitore sceglie tra 2$ o 1 carta per ogni sconfitto;
- [ ] il vincitore può scegliere un Gancio;
- [ ] il vincitore sceglie dove mandare gli sconfitti;
- [ ] il tutorial mostra acquisto e vendita di Dope;
- [ ] mostra Cops/Feds;
- [ ] mostra la Jail da 4 posti;
- [ ] il quarto prigioniero scatena l'Evasione;
- [ ] mostra Den e Gambler;
- [ ] mostra Poker;
- [ ] il Poker può essere lanciato una sola volta;
- [ ] il Poker viene risolto a fine Round;
- [ ] la partita è descritta come 3 Turni × 3 Round;
- [ ] il Primo Giocatore viene scelto a inizio Turno, insieme alla rivelazione della Retata;
- [ ] il Primo Giocatore è scelto da chi ha il Link più alto dai Preti (non assegnato automaticamente in base a un Gancio qualsiasi);
- [ ] questa regola viene mostrata almeno due volte;
- [ ] Jobs e REP vengono mostrati in uno stato concreto;
- [ ] la carta Retata viene mostrata prima della sua risoluzione;
- [ ] la Retata viene poi risolta a squadre;
- [ ] le carte vengono spiegate dopo averne già mostrato usi concreti;
- [ ] esiste una scena di scoring finale;
- [ ] il tutorial può essere saltato;
- [ ] il tutorial può essere rilanciato dal menu;
- [ ] il tutorial non modifica statistiche o partite reali.

---

# 21. Deliverable atteso da Claude Code

Claude Code deve:

1. analizzare il frontend e il game engine esistenti;
2. individuare quali componenti del gioco reale possono essere riutilizzati;
3. proporre una struttura `TutorialMode`;
4. creare un sistema di scenari/snapshot controllati;
5. implementare il motore degli step;
6. implementare highlight e blocco degli input;
7. creare almeno il core tutorial;
8. evitare duplicazioni inutili della logica del gioco;
9. riusare il più possibile board, carte, pedine e componenti reali;
10. segnalare eventuali conflitti tra le regole qui definite e il codice esistente;
11. eseguire test/lint/build disponibili;
12. riportare alla fine:
   - file creati;
   - file modificati;
   - scene implementate;
   - scene ancora TODO;
   - eventuali incoerenze rilevate nel game engine.

---

# 22. Principio finale

Il tutorial NON deve spiegare DOPE prima di farlo giocare.

Deve far succedere qualcosa, far compiere al giocatore una scelta e spiegare la regola nel momento in cui quella regola diventa rilevante.

La sensazione desiderata è:

```text
"Sto già giocando, e intanto sto imparando."
```
