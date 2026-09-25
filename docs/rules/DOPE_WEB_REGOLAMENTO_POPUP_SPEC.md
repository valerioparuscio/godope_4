# DOPE Web — Specifiche per tutorial/regolamento contestuale in popup

## Obiettivo

Implementare nel frontend di **DOPE Web** un sistema di tutorial/regolamento consultabile:

1. **prima della partita**, come tutorial introduttivo;
2. **durante la partita**, senza abbandonare la schermata di gioco;
3. tramite un **popup/modal sovrapposto** alla UI di gioco;
4. con contenuti organizzati come una piccola **wiki ipertestuale**;
5. con schede dedicate a:
   - azioni;
   - oggetti;
   - personaggi;
   - luoghi;
   - eventi;
   - fasi del gioco;
   - condizioni particolari;
   - punteggio finale;
6. con supporto a **immagini, zoom del tabellone, diagrammi e screenshot contestuali**.

Il sistema deve essere pensato come una fonte unica di contenuti riutilizzabile sia per il tutorial iniziale sia per l'help contestuale durante la partita.

---

# 1. Regole aggiornate da considerare

Queste regole hanno priorità rispetto a eventuali versioni precedenti presenti nel codice, nei documenti o nelle note di progetto.

## 1.1 Struttura della partita

La partita è composta da:

- **3 turni**
- ogni turno contiene **3 round**

Quindi la struttura temporale principale è:

```text
PARTITA
├── TURNO 1
│   ├── ROUND 1
│   ├── ROUND 2
│   └── ROUND 3
├── TURNO 2
│   ├── ROUND 1
│   ├── ROUND 2
│   └── ROUND 3
└── TURNO 3
    ├── ROUND 1
    ├── ROUND 2
    └── ROUND 3
```

Il regolamento web deve usare sempre questa terminologia.

Non usare vecchi riferimenti a una partita composta da 4 turni.

---

## 1.2 Jail

La **Jail ha 4 posti**.

Regola aggiornata:

- slot disponibili: 1, 2, 3, 4;
- quando viene occupato il **quarto posto**, si attiva immediatamente l'evento di **evasione**;
- eventuali testi o immagini che mostrano 6 posti devono essere considerati obsoleti.

Nel tutorial deve essere molto evidente:

> **Il quarto prigioniero fa scattare l'evasione.**

Prevedere una scheda specifica:

```text
/jail
/jail/evasione
```

---

## 1.3 Poker

Regola aggiornata:

- il Poker può essere **lanciato una sola volta**;
- il limite precedente era 2;
- il Poker viene **risolto alla fine di ogni round**;
- non viene più risolto alla fine del turno.

### Assunzione implementativa

Se nel codice esistente il limite "2 Poker" è già associato a uno specifico scope
(es. per giocatore / per turno / per altra unità temporale),
mantenere lo stesso scope e cambiare semplicemente:

```text
2 -> 1
```

Non inventare un nuovo scope se quello corrente è già definito dal game engine.

La modifica obbligatoria è:

```text
MAX_POKER_LAUNCHES = 1
POKER_RESOLUTION_PHASE = END_OF_ROUND
```

Il tutorial deve riflettere esplicitamente questa sequenza:

```text
Round
→ azioni dei giocatori
→ eventuale Poker lanciato
→ fine round
→ risoluzione Poker
→ round successivo
```

---

# 2. Principio UX

Il regolamento NON deve apparire come un PDF o una pagina lunga.

Deve essere una **modal window / overlay** sopra la partita.

Comportamento desiderato:

```text
GAME UI
┌──────────────────────────────────────────────┐
│                                              │
│                 TABELLONE                    │
│                                              │
│       [ ? REGOLAMENTO ]                      │
│                                              │
└──────────────────────────────────────────────┘

               ↓ click

┌──────────────────────────────────────────────┐
│  REGOLAMENTO                            [X]  │
│──────────────────────────────────────────────│
│  Indice / ricerca / breadcrumb               │
│                                              │
│  contenuto della scheda                      │
│                                              │
│  immagini                                    │
│  link correlati                              │
│                                              │
│  ← indietro                                  │
└──────────────────────────────────────────────┘
```

Il popup:

- non deve ricaricare la pagina;
- non deve modificare lo stato della partita;
- non deve far perdere selezioni o azioni in corso;
- deve poter essere chiuso in qualsiasi momento;
- deve supportare navigazione interna tra schede;
- deve mantenere uno storico di navigazione interno;
- deve poter essere aperto direttamente su una scheda specifica.

---

# 3. Entry point

Inserire un pulsante persistente nella UI di gioco:

```text
? Regolamento
```

oppure una versione compatta:

```text
?
```

con tooltip:

```text
Regolamento e tutorial
```

Il pulsante deve essere accessibile:

- durante il proprio turno;
- durante il turno degli altri;
- durante Poker;
- durante Rissa;
- durante Retata;
- durante schermate di riepilogo;
- durante schermate di fine round;
- durante schermate di fine turno.

---

# 4. Apertura contestuale

Il sistema deve permettere di aprire il popup direttamente su una specifica scheda.

Esempi:

```tsx
openRules("actions/buy-dope")
openRules("actions/sell-dope")
openRules("characters/link")
openRules("locations/jail")
openRules("events/brawl")
openRules("events/poker")
openRules("jobs/reputation")
```

Questo permette di aggiungere piccoli pulsanti `?` vicino agli elementi dell'interfaccia.

Esempio:

```text
COMPRA DOPE   [?]
```

click su `?`:

```text
Regolamento → Comprare Dope
```

NON deve aprire l'indice generale.

---

# 5. Due modalità di consultazione

La home del regolamento deve offrire due modalità.

## A. Impara a giocare

Tutorial progressivo per un nuovo giocatore.

Struttura consigliata:

1. Obiettivo
2. Il tabellone
3. Il proprio Covo
4. Struttura della partita
5. Il round
6. Le azioni principali
7. Criminali e trasformazioni
8. Dope e mercato
9. Cops e Feds
10. Jail
11. Poker
12. Risse
13. Jobs e REP
14. Retate
15. Fine partita e punteggio

---

## B. Consulta il regolamento

Accesso diretto alle singole schede tramite indice, ricerca e link.

---

# 6. Home del regolamento

La home deve contenere almeno queste aree.

## Come faccio a...

- Piazzare un Criminale?
- Spostare un Criminale?
- Comprare Dope?
- Vendere Dope?
- Diventare Link?
- Entrare nel Den?
- Lanciare un Poker?
- Partecipare al Poker?
- Fare Marketing?
- Corrompere un Cop?
- Corrompere un Fed?
- Comprare un Cop/Fed?
- Completare un Job?
- Ottenere REP?
- Usare una Skill?
- Uscire dalla Jail?
- Ottenere un'azione extra?

## Cosa succede se...

- entra un Criminale che fa scattare una Rissa?
- finisce la Dope in un mercato?
- uno Spot si riempie?
- il quarto posto della Jail viene occupato?
- arrestano il mio Criminale?
- arrestano il mio Link?
- perdo un Poker?
- completo un Job?
- perdo una Retata?
- ho troppe carte?
- termina un round?
- termina un turno?

---

# 7. Indice principale

Implementare il seguente indice logico.

## 7.1 Regole base

Slug:

```text
basics/
```

Schede:

```text
basics/goal
basics/board
basics/den
basics/game-structure
basics/turn
basics/round
basics/end-game
```

### basics/game-structure

Deve indicare chiaramente:

```text
3 turni
3 round per turno
```

### basics/round

Deve descrivere:

- cosa avviene nel round;
- quando si eseguono le azioni;
- cosa avviene alla fine del round;
- risoluzione del Poker alla fine del round.

---

## 7.2 Azioni

Slug:

```text
actions/
```

Schede:

```text
actions/place-criminal
actions/move-criminal
actions/buy-dope
actions/sell-dope
actions/bribe-cop
actions/bribe-fed
actions/buy-cop-fed
actions/link-extra-action
actions/marketing
```

---

## 7.3 Personaggi / pedine

Slug:

```text
characters/
```

Schede:

```text
characters/criminal
characters/link
characters/gambler
characters/rat
characters/cop
characters/fed
```

---

## 7.4 Luoghi

Slug:

```text
locations/
```

Schede:

```text
locations/hood
locations/contact
locations/den
locations/jail
locations/hideout
locations/spot
locations/dope-market
```

### locations/jail

Mostrare graficamente quattro slot:

```text
[1] [2] [3] [4 → EVASIONE]
```

La grafica deve rendere immediatamente leggibile che:

```text
4° OCCUPANTE = EVASIONE
```

---

## 7.5 Dope e mercato

Slug:

```text
market/
```

Schede:

```text
market/dope
market/buying
market/selling
market/prices
market/package-buying
market/package-selling
market/market-crash
market/marketing
```

---

## 7.6 Polizia e Jail

Slug:

```text
police/
```

Schede:

```text
police/cop
police/fed
police/bribery
police/arrest-criminal
police/arrest-link
police/confiscation
police/jail
police/jailbreak
```

---

## 7.7 Carte

Slug:

```text
cards/
```

Schede:

```text
cards/contact
cards/job
cards/raid
cards/skill
cards/symbols
cards/hand-limit
```

---

## 7.8 Jobs e reputazione

Slug:

```text
jobs/
```

Schede:

```text
jobs/job
jobs/job-levels
jobs/complete-job
jobs/reputation
jobs/stained-reputation
jobs/job-rewards
```

---

## 7.9 Risse

Slug:

```text
events/brawl
```

Sottosezioni:

- quando parte;
- chi partecipa;
- pistole;
- forza;
- pareggi;
- vincitore;
- sconfitto;
- conseguenze;
- Cop dopo la rissa.

Inserire almeno un esempio visuale sequenziale.

---

## 7.10 Poker

Slug:

```text
events/poker
```

Sottosezioni:

```text
events/poker/start
events/poker/enter-den
events/poker/betting
events/poker/hands
events/poker/colors
events/poker/win
events/poker/lose
events/poker/tie
events/poker/chips
events/poker/end-of-round-resolution
```

La scheda principale deve evidenziare:

```text
Il Poker viene risolto ALLA FINE DEL ROUND.
```

e:

```text
Il Poker può essere lanciato una sola volta secondo lo scope già previsto dal motore di gioco.
```

Non usare mai il vecchio limite di 2.

---

## 7.11 Marketing

Slug:

```text
marketing/
```

Schede:

```text
marketing/stonk
marketing/start
marketing/before-after-trade
marketing/distribute-stonk
marketing/example
```

---

## 7.12 Retate

Slug:

```text
raids/
```

Schede:

```text
raids/raid
raids/reveal
raids/first-player
raids/teams
raids/showdown
raids/consequences
```

---

## 7.13 Grinta e azioni extra

Slug:

```text
grit/
```

Schede:

```text
grit/grit
grit/action-selection
grit/number-of-actions
grit/card-boost
grit/link-extra-action
```

---

## 7.14 Fine partita e punteggio

Slug:

```text
scoring/
```

Schede:

```text
scoring/cash
scoring/reputation
scoring/stained-reputation
scoring/contact-majorities
scoring/poker-chips
scoring/skills
scoring/ties
scoring/example
```

---

## 7.15 Glossario

Slug:

```text
glossary/
```

Termini minimi:

```text
Boss
Gang
Hood
Contact
Criminal
Link
Gambler
Rat
Dope
Spot
Cop
Fed
Jail
Den
Covo
Grinta
REP
Job
Retata
Rissa
Stonk
Poker
Skill
Round
Turno
```

Ogni termine deve linkare alla relativa scheda principale.

---

# 8. Template standard di una scheda

Ogni pagina deve usare una struttura coerente.

Esempio:

```text
TITOLO

Sintesi
1-3 frasi che spiegano la regola.

[IMMAGINE / ZOOM TABELLONE]

COSA SERVE
- prerequisiti

COSA FAI
1.
2.
3.

COSA SUCCEDE
- conseguenze

ATTENZIONE
- eccezioni
- limiti
- errori comuni

ESEMPIO
breve esempio concreto

VEDI ANCHE
→ Link
→ Jail
→ Arresto
```

Non tutte le sezioni sono obbligatorie, ma il layout visivo deve rimanere consistente.

---

# 9. Formato dei contenuti

Separare contenuto e UI.

Preferenza:

```text
src/
  rules/
    content/
```

I contenuti possono essere:

- Markdown;
- MDX;
- JSON strutturato + componenti React.

Preferenza consigliata: **MDX** se già supportato dal progetto.

In alternativa usare Markdown con metadata/frontmatter.

Esempio:

```md
---
id: actions-buy-dope
slug: actions/buy-dope
title: Comprare Dope
category: actions
keywords:
  - comprare
  - acquisto
  - dope
  - mercato
related:
  - market/prices
  - characters/cop
  - market/package-buying
image: /rules/board/buy-dope.webp
---

# Comprare Dope

...
```

Il contenuto NON deve essere scritto direttamente dentro i componenti React.

---

# 10. Modello dati minimo

Se viene usato JSON/TypeScript:

```ts
export interface RulePage {
  id: string;
  slug: string;
  title: string;
  category: RuleCategory;

  summary?: string;

  keywords?: string[];

  body: string;

  images?: RuleImage[];

  related?: string[];

  contextualTriggers?: string[];
}

export interface RuleImage {
  src: string;
  alt: string;
  caption?: string;

  focus?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}
```

---

# 11. Componenti React suggeriti

Creare componenti separati.

```text
RulesModal
RulesHome
RulesIndex
RulesPage
RulesBreadcrumb
RulesSearch
RulesRelatedLinks
RulesImage
RulesBoardZoom
RulesBackButton
RulesCloseButton
RulesContextHelpButton
```

Possibile struttura:

```text
src/components/rules/
  RulesModal.tsx
  RulesHome.tsx
  RulesPage.tsx
  RulesIndex.tsx
  RulesSearch.tsx
  RulesBoardZoom.tsx
  RulesBreadcrumb.tsx
  RulesContextHelpButton.tsx
```

---

# 12. Stato del popup

Suggerimento:

```ts
interface RulesState {
  isOpen: boolean;
  currentSlug: string | null;
  history: string[];
}
```

API minima:

```ts
openRules()
openRules(slug)
closeRules()
navigateRules(slug)
goBackRules()
```

Esempio:

```ts
openRules("events/poker")
```

---

# 13. Deep link

È utile supportare anche URL leggibili.

Esempio:

```text
/game/123?rules=events/poker
```

oppure:

```text
/game/123#rules/events/poker
```

Il link NON deve causare il reload della partita.

Questo permette in futuro anche di condividere direttamente una regola.

---

# 14. Navigazione interna

Ogni pagina deve avere:

- breadcrumb;
- indietro;
- home regolamento;
- schede correlate.

Esempio:

```text
Regolamento
> Polizia
> Jail
> Evasione
```

---

# 15. Ricerca

Inserire una ricerca testuale interna.

Cercare almeno in:

```text
title
summary
keywords
body
```

Esempi di query:

```text
evasione
quarto prigioniero
poker
rissa
comprare
fed
link
```

La ricerca "evasione" deve restituire almeno:

```text
Jail
Evasione
Rat
```

---

# 16. Link ipertestuali nei testi

Le parole chiave devono poter diventare link.

Esempio:

```md
Quando un [Criminale](/rules/characters/criminal)
viene arrestato...
```

o tramite componente dedicato:

```tsx
<RuleLink slug="characters/criminal">
  Criminale
</RuleLink>
```

Preferire la seconda soluzione se evita navigazioni reali del browser.

---

# 17. Immagini

Il sistema deve supportare:

1. screenshot del tabellone;
2. crop specifici;
3. diagrammi;
4. immagini delle carte;
5. immagini delle pedine;
6. schemi passo-passo.

Path consigliato:

```text
public/rules/
  board/
  cards/
  pieces/
  diagrams/
```

Esempio:

```text
public/rules/board/jail.webp
public/rules/board/dope-market.webp
public/rules/board/den.webp
public/rules/diagrams/criminal-link-gambler.svg
```

---

# 18. Zoom sul tabellone

Creare un componente:

```tsx
<RulesBoardZoom />
```

che permetta di mostrare:

- immagine completa del tabellone;
- area evidenziata;
- zoom;
- didascalia.

Esempio concettuale:

```tsx
<RulesBoardZoom
  image="/rules/board/full-board.webp"
  focus={{
    x: 420,
    y: 150,
    width: 250,
    height: 200
  }}
  caption="Il mercato della Dope"
/>
```

Non è obbligatorio implementare subito pan/zoom dinamico.

Un crop statico ben fatto è sufficiente per la prima versione.

---

# 19. Hotspot del tabellone

Predisporre la possibilità futura di una pagina:

```text
Il tabellone
```

con hotspot cliccabili.

Esempio:

```text
[JAIL]
→ locations/jail

[DEN]
→ locations/den

[MERCATO DOPE]
→ locations/dope-market

[CONTACT]
→ locations/contact
```

La prima implementazione può usare aree HTML assolute sopra un'immagine.

---

# 20. Help contestuale dentro il gioco

Aggiungere progressivamente `?` nei punti principali.

Priorità:

```text
Compra Dope
Vendi Dope
Poker
Rissa
Jail
Job
Retata
Link
Cop
Fed
Marketing
Grinta
```

Esempio componente:

```tsx
<RulesContextHelpButton slug="actions/buy-dope" />
```

Output:

```text
[?]
```

Il click NON deve propagarsi al bottone di gioco sottostante.

Usare:

```ts
event.stopPropagation()
```

dove necessario.

---

# 21. Tutorial prima della partita

Dalla schermata iniziale aggiungere:

```text
IMPARA A GIOCARE
```

Questo apre lo stesso sistema `RulesModal`, ma parte da:

```text
/tutorial
```

Il tutorial non deve duplicare i contenuti.

Deve essere una sequenza di schede già presenti nel regolamento.

Esempio:

```ts
const tutorialSteps = [
  "basics/goal",
  "basics/board",
  "basics/game-structure",
  "basics/round",
  "actions/place-criminal",
  "actions/buy-dope",
  "actions/sell-dope",
  "characters/link",
  "police/jail",
  "events/poker",
  "events/brawl",
  "jobs/job",
  "raids/raid",
  "scoring/example"
];
```

UI:

```text
← PRECEDENTE       4 / 14       SUCCESSIVO →
```

---

# 22. Responsività

Desktop:

```text
larghezza modal: 70-85vw
altezza: 80-90vh
```

Mobile:

```text
full screen
```

Il popup deve diventare praticamente una pagina piena su schermi piccoli.

---

# 23. Accessibilità

Obbligatorio:

- chiusura con `ESC`;
- focus trap dentro la modal;
- `aria-modal="true"`;
- `role="dialog"`;
- focus iniziale corretto;
- ritorno del focus all'elemento che ha aperto il popup;
- testi alternativi per le immagini;
- pulsanti navigabili via tastiera;
- contrasto coerente con la UI del gioco.

---

# 24. Persistenza dello stato partita

Aprire il regolamento NON deve:

- inviare mosse;
- modificare lo stato;
- fermare timer lato server;
- cambiare player state;
- resettare form;
- resettare scelte temporanee.

Il modal deve essere puramente frontend/UI.

---

# 25. Regole critiche da non mostrare più

Rimuovere o correggere ovunque nel tutorial:

```text
Jail = 6 posti
```

DEVE diventare:

```text
Jail = 4 posti
4° posto = evasione
```

---

Rimuovere:

```text
Poker lanciabile 2 volte
```

DEVE diventare:

```text
Poker lanciabile 1 volta
```

---

Rimuovere:

```text
Poker risolto a fine turno
```

DEVE diventare:

```text
Poker risolto a fine round
```

---

Rimuovere eventuali riferimenti a:

```text
4 turni
```

DEVE diventare:

```text
3 turni
3 round per turno
```

---

# 26. Source of truth

Prima di scrivere i testi definitivi:

1. individuare nel repository il regolamento corrente;
2. individuare eventuali costanti del game engine;
3. confrontare i contenuti con le variazioni definite in questo documento;
4. trattare questo documento come override per:
   - numero posti Jail;
   - trigger evasione;
   - limite Poker;
   - timing risoluzione Poker;
   - numero turni;
   - numero round per turno.

Se documentazione e codice sono in conflitto, NON correggere silenziosamente la logica di gioco.

Segnalare il conflitto separatamente.

Il task principale di questo documento riguarda la UI del regolamento.

---

# 27. Prima versione da implementare

Per il primo rilascio implementare almeno:

## UI

- `RulesModal`
- `RulesHome`
- `RulesPage`
- `RulesBreadcrumb`
- `RulesSearch`
- `RulesContextHelpButton`

## contenuti minimi

```text
Obiettivo
Struttura partita
Round
Comprare Dope
Vendere Dope
Criminale
Link
Cop
Fed
Jail
Evasione
Poker
Rissa
Job
REP
Retata
Punteggio finale
```

## immagini minime

```text
tabellone intero
Jail
Den
mercato Dope
Spot
area Contact
```

---

# 28. Acceptance criteria

La feature è completata quando:

- [ ] esiste un pulsante Regolamento sempre accessibile durante la partita;
- [ ] apre una modal senza reload;
- [ ] la partita rimane nello stesso stato dopo la chiusura;
- [ ] la home presenta indice e ricerca;
- [ ] è possibile navigare tra schede senza chiudere la modal;
- [ ] esiste breadcrumb;
- [ ] esiste pulsante indietro;
- [ ] i link correlati funzionano;
- [ ] i pulsanti `?` possono aprire una specifica regola;
- [ ] il tutorial pre-partita usa gli stessi contenuti;
- [ ] la Jail è descritta con 4 posti;
- [ ] il quarto posto attiva l'evasione;
- [ ] il Poker ha limite 1;
- [ ] il Poker viene risolto a fine round;
- [ ] il regolamento indica 3 turni;
- [ ] ogni turno contiene 3 round;
- [ ] non rimangono testi visibili con le vecchie regole;
- [ ] le immagini hanno alt text;
- [ ] ESC chiude il popup;
- [ ] il modal funziona su desktop e mobile.

---

# 29. Non fare in questa fase

Non implementare per ora:

- editor visuale del regolamento;
- CMS;
- backend dedicato;
- sincronizzazione server dei contenuti;
- traduzione automatica;
- animazioni complesse;
- video;
- walkthrough che blocca la UI di gioco;
- modifica automatica del game engine.

Il regolamento deve restare un layer frontend indipendente.

---

# 30. Obiettivo architetturale finale

La stessa scheda deve poter essere raggiunta in tre modi:

```text
1. Tutorial iniziale
2. Indice del regolamento
3. Help contestuale [?] durante la partita
```

Esempio:

```text
events/poker
```

deve essere:

- uno step del tutorial;
- una voce dell'indice;
- il contenuto aperto dal pulsante `?` della UI Poker.

Non duplicare il testo.

---

# 31. Priorità implementativa

Ordine consigliato:

```text
1. RulesModal
2. sistema di routing interno per slug
3. loader contenuti
4. RulesPage
5. home / indice
6. breadcrumb + history
7. ricerca
8. help contestuale
9. tutorial sequenziale
10. immagini / zoom board
11. hotspot board
```

---

# 32. Deliverable atteso da Claude Code

Claude Code deve:

1. analizzare l'architettura frontend esistente;
2. proporre i file da aggiungere/modificare;
3. implementare il sistema di regolamento;
4. evitare modifiche non necessarie al game engine;
5. riutilizzare componenti e design system già presenti;
6. inserire contenuti iniziali strutturati;
7. segnalare eventuali conflitti tra vecchie e nuove regole;
8. eseguire test/lint/build disponibili nel repository;
9. riportare alla fine:
   - file creati;
   - file modificati;
   - eventuali TODO;
   - eventuali regole del codice non coerenti con questo documento.
