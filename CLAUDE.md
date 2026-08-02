# DOPE — Project Instructions for AI Coding Agents

> Questo file è pensato per Claude Code. Per Codex può essere copiato anche come `AGENTS.md` nella root del repository.

## 1. Scopo del progetto

Implementare una versione digitale 2D del gioco da tavolo **DOPE**.

La prima versione giocabile deve supportare esattamente:

- 4 giocatori;
- 1 giocatore umano;
- 3 bot;
- partita locale, senza multiplayer di rete;
- backend Python autoritativo;
- frontend web (React + Vite + TypeScript) — decisione presa il 2026-08-02,
  vedi `docs/architecture/decisions/0001-frontend-stack-react-vite.md`;
- utilizzo delle immagini già disponibili nel progetto;
- salvataggio e caricamento della partita;
- partite riproducibili tramite seed casuale;
- bot inizialmente semplici, purché capaci di completare una partita usando solo azioni legali.

L'intelligenza strategica dei bot verrà sviluppata in una fase successiva. L'architettura deve però essere progettata fin dall'inizio affinché giocatore umano e bot usino la stessa interfaccia di gioco e lo stesso generatore di azioni legali.

## 2. Fonti di verità

L'ordine di priorità delle fonti è:

1. decisioni esplicite approvate dal game designer e registrate nella documentazione del progetto;
2. regolamento corrente `how_to_play_v056.docx`;
3. file dati versionati del gioco;
4. test automatici che codificano regole già approvate;
5. codice esistente.

Il codice non è una fonte di verità superiore al regolamento o a una decisione documentata.

Quando una regola è assente, ambigua o contraddittoria:

- non inventare una soluzione definitiva;
- non nascondere l'ambiguità dentro il codice;
- aggiungere o aggiornare una voce in `docs/rules/RULES_PENDING.md`;
- rendere il comportamento configurabile quando è tecnicamente sensato;
- usare una scelta provvisoria solo se esplicitamente marcata come `PROVISIONAL` e coperta da un test che ne renda evidente la natura temporanea.

## 3. Principi architetturali obbligatori

### 3.1 Backend autoritativo

Tutte le regole, le validazioni e le trasformazioni dello stato appartengono al backend Python.

Il frontend non deve:

- decidere se un'azione è legale;
- calcolare costi, ricavi, punteggi o maggioranze;
- pescare carte autonomamente;
- modificare direttamente lo stato della partita;
- risolvere Risse, Poker, Retate, Jobs o Evasioni;
- contenere copie parallele delle regole del backend.

Il frontend visualizza lo stato ricevuto, raccoglie una scelta dell'utente e invia un comando.

### 3.2 Motore deterministico

La trasformazione fondamentale è:

```text
stato precedente + comando validato + stato RNG -> eventi di dominio + nuovo stato
```

A parità di:

- stato iniziale;
- sequenza di comandi;
- seed;
- versione delle regole;

il risultato deve essere identico.

Non usare direttamente funzioni casuali globali. Lo stato del generatore casuale, o almeno il seed e la sequenza deterministica necessaria a ricostruirlo, deve essere parte della partita salvata.

### 3.3 Separazione tra dominio e trasporto

Il package del dominio non deve importare:

- FastAPI;
- il frontend;
- librerie grafiche;
- filesystem;
- rete;
- database.

FastAPI è un adapter esterno. Deve essere possibile testare un'intera partita importando solo il motore Python.

### 3.4 Stato serializzabile

L'intero stato autoritativo deve poter essere serializzato in JSON senza riferimenti circolari o oggetti grafici.

Usare identificatori stabili, per esempio:

- `player_0`;
- `hood_03`;
- `pawn_p0_04`;
- `card_customer_priests_012`;
- `job_level_2_05`.

Non serializzare riferimenti Python a oggetti. Usare ID e collezioni esplicite.

### 3.5 Dati separati dalle regole

Contenuti specifici come mappa, mazzi, immagini, testi, Jobs, Skills, Retate, Contacts e configurazione iniziale devono essere caricati da file dati versionati.

Non hardcodare nel motore:

- adiacenze della mappa;
- nomi dei Quartieri;
- associazioni Hood–Contact;
- associazioni Spot–Dope;
- contenuto delle carte;
- requisiti dei Jobs;
- condizioni delle Retate;
- effetti delle Skills;
- percorsi delle immagini.

Le invarianti generali, come il massimo di 5 carte in mano o i 6 slot della Jail, possono stare nel codice solo se sono regole stabili e confermate. È comunque preferibile raccoglierle in una configurazione versionata.

## 4. Stack tecnico

### Backend

- Python 3.12 o superiore;
- standard library per il dominio, con `dataclasses`, `enum`, `typing` e tipi immutabili dove opportuno;
- Pydantic esclusivamente per schemi I/O e validazione ai confini;
- FastAPI come adapter HTTP locale;
- pytest per i test;
- Ruff per lint e formattazione;
- mypy in modalità progressivamente rigorosa.

### Frontend

- React 18+ con TypeScript;
- Vite come build tool e dev server;
- componenti funzionali con hook, nessuno stato globale di dominio (solo
  l'ultima `GameView` ricevuta e stato effimero di UI);
- CSS semplice, layout responsive dove ragionevole;
- testi UI separati dai dati e predisposti per localizzazione;
- nessuna logica di dominio duplicata.

### Comunicazione iniziale

Per lo sviluppo usare HTTP locale su `127.0.0.1`:

- il frontend si collega al backend già in esecuzione (`tools/run_backend.py`);
- il frontend invia comandi JSON;
- il backend restituisce una vista aggiornata, gli eventi prodotti e l'eventuale decisione successiva;
- la partita è turn-based: WebSocket non è necessario per l'MVP.

Il dominio deve restare indipendente da HTTP, così il trasporto potrà essere sostituito in fase di packaging.

## 5. Struttura raccomandata del repository

```text
/
├─ CLAUDE.md
├─ README.md
├─ docs/
│  ├─ architecture/
│  │  ├─ overview.md
│  │  └─ decisions/
│  ├─ rules/
│  │  ├─ how_to_play_v056.docx
│  │  ├─ RULES_CANONICAL.md
│  │  ├─ RULES_PENDING.md
│  │  └─ RULE_CHANGELOG.md
│  └─ api/
├─ data/
│  ├─ game_config.json
│  ├─ board.json
│  ├─ contacts.json
│  ├─ dope_types.json
│  ├─ customer_cards.json
│  ├─ jobs.json
│  ├─ raids.json
│  ├─ skills.json
│  └─ asset_manifest.json
├─ backend/
│  ├─ pyproject.toml
│  ├─ src/dope_engine/
│  │  ├─ domain/
│  │  │  ├─ enums.py
│  │  │  ├─ ids.py
│  │  │  ├─ entities.py
│  │  │  ├─ state.py
│  │  │  ├─ commands.py
│  │  │  ├─ events.py
│  │  │  ├─ decisions.py
│  │  │  └─ errors.py
│  │  ├─ rules/
│  │  │  ├─ setup.py
│  │  │  ├─ turn_flow.py
│  │  │  ├─ placement.py
│  │  │  ├─ movement.py
│  │  │  ├─ trade.py
│  │  │  ├─ officers.py
│  │  │  ├─ brawl.py
│  │  │  ├─ poker.py
│  │  │  ├─ raids.py
│  │  │  ├─ jobs.py
│  │  │  ├─ jail.py
│  │  │  └─ scoring.py
│  │  ├─ application/
│  │  │  ├─ game_service.py
│  │  │  ├─ legal_actions.py
│  │  │  ├─ views.py
│  │  │  ├─ save_load.py
│  │  │  └─ replay.py
│  │  ├─ bots/
│  │  │  ├─ base.py
│  │  │  ├─ random_legal.py
│  │  │  └─ policies.py
│  │  └─ adapters/
│  │     └─ http/
│  │        ├─ app.py
│  │        └─ schemas.py
│  └─ tests/
│     ├─ unit/
│     ├─ integration/
│     ├─ scenarios/
│     └─ fixtures/
├─ frontend/
│  ├─ package.json
│  ├─ vite.config.ts
│  ├─ tsconfig.json
│  ├─ index.html
│  └─ src/
│     ├─ api.ts
│     ├─ types.ts
│     ├─ App.tsx
│     └─ components/
│        ├─ SetupScreen.tsx
│        ├─ PlayerStrip.tsx
│        ├─ HandView.tsx
│        ├─ BoardSummary.tsx
│        ├─ DecisionPanel.tsx
│        └─ FinishedScreen.tsx
└─ tools/
   ├─ validate_data.py
   ├─ run_backend.py
   └─ run_full_test_game.py
```

La struttura può evolvere, ma la separazione `domain / application / adapters / frontend` è obbligatoria.

## 6. Linguaggio del dominio

Nel codice usare nomi inglesi coerenti. Nell'interfaccia mantenere i termini di gioco approvati, anche quando sono in inglese nel regolamento.

Mappatura raccomandata:

| Regolamento/UI | Codice |
|---|---|
| Quartiere / Hood | `Hood` |
| Covo / Base | `PlayerBase` |
| Criminale | `Criminal` |
| Link | `Link` |
| Gambler | `Gambler` |
| Rat | `Rat` |
| Merce / Dope | `DopeToken` / `DopeType` |
| Punto di Vendita / Spot | `SalesSpot` |
| Cliente / Contact | `Contact` |
| Poliziotto | `Cop` |
| Detective | `Fed` |
| Commissariato / Jail | `Jail` |
| Bisca / Den | `Den` |
| Grinta | `Grit` |
| Reputazione / REP | `ReputationToken` |
| Retata | `Raid` |
| Rissa | `Brawl` |
| Soffiata | `TipOffPhase` |
| Resa dei Conti | `ShowdownPhase` |

Non alternare sinonimi diversi per lo stesso concetto nel codice.

## 7. Modello di stato

### 7.1 `GameState`

Deve contenere almeno:

```text
GameState
- schema_version
- rules_version
- game_id
- revision
- seed / rng_state
- status
- configuration
- players[4]
- player_order
- first_player_id
- current_player_id
- turn_index
- action_round_index
- phase
- active_step
- board_state
- market_state
- jail_state
- decks_state
- jobs_state
- raids_state
- poker_state
- pending_decision
- event_log_cursor
- final_score, quando presente
```

`revision` aumenta dopo ogni comando accettato. Un comando deve indicare la revisione attesa per impedire doppio invio o comandi applicati a uno stato obsoleto.

### 7.2 `PlayerState`

Deve contenere almeno:

```text
PlayerState
- player_id
- seat_index
- controller_type: HUMAN | BOT
- display_name
- money
- hand_card_ids
- base_inventory
- pawn_ids
- links_by_contact_and_level
- reputation_tokens
- stained_reputation_token_ids
- completed_job_ids
- skill_ids
- grit_markers
- moved_pawn_ids_this_turn
- extra_action_used_this_turn
- gamble_cards_played_this_round
```

Non dedurre la posizione di una pedina da più strutture contemporaneamente. Deve esistere una sola rappresentazione autoritativa della sua posizione.

### 7.3 Pedine e ruoli

Usare un'unica entità con ruolo esplicito:

```text
PawnState
- pawn_id
- owner_player_id
- role: IN_BASE | CRIMINAL | LINK | GAMBLER | RAT
- location
- contact_id, solo per LINK
- link_level, solo per LINK
- jail_slot, solo per RAT
```

Ogni pedina deve trovarsi in un solo luogo e avere un solo ruolo.

### 7.4 Quartieri e mappa

Ogni Hood ordinario contiene:

```text
HoodState
- hood_id
- contact_id
- adjacent_hood_ids
- criminal_pawn_ids
- dope_stack
- cop_ids
- capacity = 5
```

Il Den e la Jail sono località speciali con strutture dedicate, non normali Hood con eccezioni sparse.

### 7.5 Jail

Rappresentare i 6 slot in ordine:

```text
JailSlot
- index: 0..5
- rat_pawn_id | null
- confiscated_dope_type | null
```

L'associazione tra Rat e Merce confiscata deve restare esplicita, perché durante l'Evasione il Rat può portare con sé la Merce presente nel proprio slot.

### 7.6 Mercato e Spots

```text
MarketState
- price_by_dope_type
- supply_by_dope_type

SalesSpotState
- spot_id
- contact_id
- accepted_dope_type
- sold_dope_tokens
- fed_ids
- capacity = 3
```

Usare interi per prezzi e denaro.

### 7.7 Carte

Separare definizione immutabile e istanza/stato:

```text
CustomerCardDefinition
- card_id
- contact_id
- base_action_boost
- poker_symbols
- stonk_count
- gun_count
- gamble_effect, se presente
- asset_id

DeckState
- draw_pile_card_ids
- discard_pile_card_ids
```

Una carta giocata produce un solo effetto tra quelli disponibili, come indicato dal regolamento. La scelta dell'effetto deve essere esplicita nel comando.

## 8. Stato della partita e macchina a stati

Non modellare il turno con una lunga funzione monolitica. Usare una macchina a stati esplicita.

Fasi principali:

```text
SETUP
TIP_OFF
ACTION_PHASE
POKER_PHASE
SHOWDOWN_PHASE
END_GAME_SCORING
FINISHED
```

Durante `ACTION_PHASE` esistono tre action round per giocatore, salvo modifica approvata delle regole.

Sotto-stati tipici:

```text
WAITING_FOR_GRIT_ACTION
WAITING_FOR_CARD_USAGE
WAITING_FOR_MAIN_ACTION_TARGETS
RESOLVING_TRIGGERED_EFFECTS
WAITING_FOR_LINK_EXTRA_ACTION
WAITING_FOR_HAND_DISCARD
WAITING_FOR_BRAWL_CARD
WAITING_FOR_BRAWL_ASSIGNMENT
WAITING_FOR_BRAWL_REWARD
WAITING_FOR_POKER_BETS
WAITING_FOR_POKER_CARD
WAITING_FOR_RAID_RESOLUTION
WAITING_FOR_JOB_REWARD
WAITING_FOR_JAIL_ESCAPE
```

Lo stato deve sempre indicare chi deve decidere e quali decisioni sono ammesse.

## 9. Comandi, eventi e decisioni

### 9.1 Comandi

Un comando rappresenta l'intenzione di un controller. Esempi:

```text
StartGame
ChooseGritAction
PlayCustomerCard
PlaceCriminal
MoveCriminal
BuyDope
SellDope
CorruptCop
CorruptFed
BuyOfficer
SpendLinkForExtraAction
LaunchPoker
PlacePokerBet
PlayPokerCard
PlayBrawlCard
AssignBrawlGuns
ChooseBrawlReward
ClaimJob
ChooseJobReward
StainReputationForMoney
DiscardCards
PassOptionalStep
```

Ogni comando deve includere:

- `game_id`;
- `player_id`;
- `expected_revision`;
- payload tipizzato;
- eventuale `decision_id` a cui risponde.

### 9.2 Eventi

Gli eventi descrivono ciò che è realmente avvenuto. Esempi:

```text
GameStarted
TurnStarted
RaidRevealed
FirstPlayerChosen
GritActionChosen
CardPlayed
CriminalPlaced
CriminalMoved
DopeBought
DopeSold
PriceChanged
HoodRestocked
CopEnteredHood
SpotCleared
FedEnteredSpot
PawnBecameLink
BrawlStarted
BrawlResolved
PawnArrested
DopeConfiscated
JailEscapeTriggered
PokerLaunched
PokerResolved
JobCompleted
ReputationStained
FinalScoreCalculated
GameFinished
```

Gli eventi servono per:

- animazioni/transizioni del frontend;
- log leggibile;
- replay;
- debugging;
- test di scenario.

Non è obbligatorio adottare event sourcing completo. Lo stato salvato può essere uno snapshot, ma ogni comando accettato deve produrre eventi di dominio espliciti.

### 9.3 Decisioni pendenti

Il backend deve esporre una sola `PendingDecision` attiva alla volta, salvo una sequenza simultanea modellata esplicitamente.

```text
PendingDecision
- decision_id
- player_id
- decision_type
- prompt_key
- context
- options
- min_selections
- max_selections
- can_pass
```

Le opzioni devono contenere ID stabili e metadati sufficienti alla UI. Il frontend non deve ricostruire autonomamente le opzioni legali.

## 10. Generatore di azioni legali

Implementare una funzione centrale:

```python
def get_legal_decision(state: GameState, player_id: PlayerId) -> PendingDecision | None:
    ...
```

Oppure un servizio equivalente con la stessa responsabilità.

Questo servizio è usato da:

- frontend umano;
- bot;
- test automatici;
- strumenti di debug;
- eventuale futura modalità online.

Un bot non deve inviare comandi non presenti nelle opzioni legali, salvo test espliciti di validazione negativa.

La validazione deve comunque essere ripetuta nel command handler: il client e il bot non sono fonti fidate.

## 11. Regole da implementare

### 11.1 Componenti e limiti noti

Il motore deve rappresentare almeno:

- 10 Hoods ordinari;
- Den e Jail come luoghi speciali;
- 5 piazze per Hood;
- 4 tipi di Dope con disponibilità totale configurata;
- massimo 3 Dope nel mercato di un Hood;
- massimo 3 Dope nel Covo per tipo;
- massimo 3 Dope in ciascuno Spot;
- 3 livelli di Link per Contact;
- Cops nei Quartieri;
- Feds negli Spots;
- massimo 5 carte in mano al termine del turno del giocatore;
- 6 slot nella Jail;
- 7 carte Raid, di cui 3 usate in una partita;
- 3 pile Job per livello di difficoltà;
- 4 giocatori.

I valori non sufficientemente definiti dal regolamento devono provenire da `game_config.json`.

### 11.2 Piazzare Criminali

Validare almeno:

- pedina disponibile nel Covo;
- Hood ordinario valido;
- spazio disponibile;
- disponibilità di 2 dollari;
- fase e giocatore corretti.

Effetti:

- pagamento di 2 dollari;
- trasferimento della pedina;
- pesca di una carta relativa al Hood/Contact;
- verifica di eventuali trigger di capienza, se previsti dai dati approvati.

### 11.3 Spostare Criminali

Validare almeno:

- pedina controllata dal giocatore;
- ruolo e posizione compatibili;
- destinazione adiacente oppure Den;
- pedina non già spostata nello stesso turno;
- capienza della destinazione;
- regole speciali Den.

Quando entra nel Den:

- la pedina diventa `GAMBLER`;
- il giocatore pesca una carta a scelta secondo le opzioni legali esposte dal backend.

Dal Den il Gambler può raggiungere qualsiasi Hood, tornando `CRIMINAL` salvo diversa regola approvata.

### 11.4 Acquistare Dope

Validare almeno:

- presenza abilitante di Criminal o Link;
- almeno una Dope nel Hood;
- assenza di Cops bloccanti;
- capacità nel Covo;
- denaro sufficiente;
- eventuale Marketing valido.

La risoluzione deve supportare l'acquisto a pacchetto:

- selezione di più acquisti nello stesso Hood;
- calcolo dei pagamenti secondo il prezzo applicabile;
- aumento del prezzo alla fine del pacchetto;
- ricarica a 3 quando il mercato si svuota;
- ingresso di un Cop alla ricarica;
- verifica del crollo del mercato dopo ogni variazione pertinente.

Non assumere la semantica esatta del prezzo di ogni pezzo nel pacchetto oltre quanto approvato nei chiarimenti.

### 11.5 Vendere Dope

Validare almeno:

- presenza abilitante di Criminal o Link;
- Spot compatibile con il tipo di Dope;
- assenza di Feds bloccanti;
- Dope presente nel Covo;
- capacità dello Spot;
- eventuale Marketing valido.

Supportare la vendita a pacchetto:

- riduzione dei prezzi alla fine del pacchetto;
- un solo Link con livello pari al numero di merci vendute, nei limiti previsti;
- svuotamento dello Spot quando raggiunge 3;
- ingresso di un Fed;
- opzione del Criminal che ha venduto di evolvere in Link quando la regola lo permette.

### 11.6 Link

Un Link:

- appartiene a un giocatore e a un Contact;
- ha livello 1, 2 o 3;
- conta come presenza nei Hoods del relativo Contact per le attività indicate dal regolamento;
- può essere speso per un'azione extra compatibile con Contact e livello;
- torna nel Covo dopo l'uso;
- può causare lo scorrimento dei Link già presenti quando viene inserito al livello 1;
- se espulso oltre il livello massimo torna nel Covo.

Il backend deve calcolare la presenza virtuale dei Link. Non duplicare fisicamente lo stesso Link in più Hoods.

### 11.7 Corrompere Cops e Feds

Costi noti:

- Cop: 2 dollari;
- Fed: 3 dollari.

Una corruzione produce esattamente due azioni tra quelle consentite, da modellare come sequenza di decisioni. La regola dice “2 diverse azioni”: il backend deve impedire di selezionare due volte la stessa tipologia di azione nella medesima corruzione, salvo chiarimento contrario.

Azioni Cop:

- spostarsi in un Hood adiacente;
- arrestare un Criminal nel Hood;
- confiscare una Dope nel Hood, aumentando il relativo prezzo di 1.

Azioni Fed:

- spostarsi in uno Spot adiacente;
- arrestare il Link di livello minore;
- confiscare una Dope nello Spot, aumentando il relativo prezzo di 1.

Un Rat può corrompere Cops ovunque. Le opzioni legali devono comunque rispettare disponibilità, bersagli e costi.

### 11.8 Comprare Cops e Feds

Costo noto: 7 dollari.

Il motore deve distinguere:

- acquisto di un officer presente sulla mappa e trasferimento nel proprio Covo;
- acquisto di un officer dal Covo di un altro giocatore presente nella località pertinente e trasferimento sulla mappa;
- pagamento al proprietario che perde l'officer dal Covo;
- possibilità di scartare un officer posseduto per guardare una Raid futura.

Le condizioni ancora ambigue sono elencate nella sezione “Regole da chiarire”.

### 11.9 Rissa

Trigger noto: ingresso del quinto Criminal in un Hood.

La Rissa deve essere una sotto-macchina a stati:

1. determinazione partecipanti;
2. ordine di dichiarazione a partire dal giocatore alla sinistra dell'innescatore;
3. eventuale carta coperta;
4. rivelazione;
5. assegnazione delle Guns a sé o a un altro partecipante;
6. calcolo forza: Criminals + Links + Guns nette;
7. determinazione vincitore e sconfitto/i;
8. scelta ricompensa/conseguenza;
9. ingresso di un Cop nel Hood.

Le carte e le assegnazioni nascoste non devono essere visibili agli altri controller prima della rivelazione.

Registrare negli eventi sia il dato pubblico sia, nel log autoritativo, il riferimento completo necessario al replay.

### 11.10 Poker

Il Poker deve essere modellato separatamente dalla normale mano di carte e deve supportare:

- massimo 2 partite lanciate per turno;
- massimo 1 carta Gamble giocata da un giocatore per action round;
- incasso di 3 dollari da parte di chi lancia la partita;
- ingresso di un Criminal nel Den come Gambler, se c'è posto;
- numero di puntate consentite in base ai Gamblers;
- puntata tramite Chip;
- rivelazione simultanea delle carte;
- ranking e tie-break configurabili;
- jackpot riportato alla partita successiva in caso di ulteriore pareggio;
- premi del vincitore;
- arresto dei Gamblers sconfitti;
- evoluzione opzionale di un Gambler in Link presso i Preti.

La composizione esatta della mano da valutare non è sufficientemente definita dal regolamento e non deve essere inventata.

### 11.11 Jail ed Evasione

Quando un Criminal o Link viene arrestato:

- entra nel primo slot disponibile;
- diventa Rat;
- mantiene il proprietario;
- perde eventuale stato Link secondo la regola approvata;
- può essere associato alla Dope confiscata nello stesso slot.

Quando entra il sesto Rat:

- si innesca l'Evasione;
- i 6 Rats tornano ai rispettivi Covi;
- ciascuno porta la Dope presente nel proprio slot;
- la pedina che ha causato l'Evasione può evolvere in Link dai Politici secondo l'ordine di risoluzione da chiarire.

L'Evasione deve essere atomica dal punto di vista del motore, ma può produrre più eventi per permettere le animazioni.

### 11.12 Jobs e REP

I Job devono essere data-driven.

Al completamento:

- il giocatore ottiene una REP;
- il token viene collocato nella riga del Job;
- sceglie una colonna libera e il relativo bonus;
- il colore/Contact del Job determina dove ottenere il bonus;
- viene rivelato il Job successivo dello stesso livello, quando disponibile.

Bonus citati:

- carta Skill;
- Link;
- 2 carte.

Il backend deve verificare automaticamente il completamento dei Job dopo ogni evento potenzialmente rilevante. Non richiedere al frontend di sapere quando un Job è completato.

### 11.13 Retate e REP macchiata

A inizio turno:

- viene rivelata una Raid;
- il giocatore con il Link più alto presso i Preti, se presente, sceglie il primo giocatore;
- l'ordine determina le squadre 1+4 contro 2+3;
- a fine turno si valuta la Raid;
- la prima Raid persa macchia 1 REP, la seconda 2, la terza 3.

Un giocatore con 2 dollari o meno può macchiare una REP per ottenere 5 dollari.

Una REP macchiata:

- non può essere ripristinata;
- vale 1 punto invece di 2 a fine partita.

Le condizioni specifiche di ogni Raid devono essere definite in `raids.json` tramite predicate dichiarativi o handler esplicitamente testati.

### 11.14 Fine partita e punteggio

Il motore deve produrre un `FinalScoreBreakdown` per ogni giocatore:

```text
- money_track_position_points
- clean_reputation_points
- stained_reputation_points
- contact_majority_points
- base_chip_points
- skill_points
- total_points
- tie_break_clean_reputation
```

Regole note:

- 2 punti per REP non macchiata;
- 1 punto per REP macchiata;
- 1 punto per maggioranza presso ogni Contact;
- Criminal vale 1 e Link vale 2 per le maggioranze;
- i pareggi di maggioranza si annullano;
- 1 punto ogni 3 Chips, anche miste, nel Covo;
- 1 punto per Skill;
- parità finale risolta dal maggior numero di REP non macchiate;
- ulteriore parità: vittoria condivisa.

La conversione della posizione sul tracciato denaro in punti deve essere implementata solo dopo chiarimento preciso.

## 12. Informazioni nascoste e viste per giocatore

Il backend conserva lo stato completo, ma espone una `GameView` specifica per il controller.

Il giocatore umano non deve vedere:

- carte in mano ai bot;
- carte coperte giocate in Rissa prima della rivelazione;
- carte future non guardate legalmente;
- informazioni che i bot non dovrebbero conoscere.

I bot devono ricevere una vista limitata equivalente a quella di un giocatore, non l'intero `GameState`, salvo componenti di test esplicitamente autorizzati.

Per debug può esistere una `DebugGameView`, disabilitata nelle build normali.

## 13. API HTTP minima

### Creazione partita

```http
POST /api/v1/games
```

Payload indicativo:

```json
{
  "human_seat": 0,
  "bot_policy": "random_legal",
  "seed": 123456,
  "rules_version": "0.56"
}
```

### Lettura vista

```http
GET /api/v1/games/{game_id}/view?player_id=player_0
```

### Invio comando

```http
POST /api/v1/games/{game_id}/commands
```

Payload indicativo:

```json
{
  "command_type": "move_criminal",
  "player_id": "player_0",
  "expected_revision": 42,
  "decision_id": "decision_0042",
  "payload": {
    "pawn_id": "pawn_p0_03",
    "destination_id": "hood_05"
  }
}
```

### Risposta generica a una decisione pendente

```http
POST /api/v1/games/{game_id}/decisions/answer
```

Payload indicativo:

```json
{
  "player_id": "player_0",
  "decision_id": "decision_0042",
  "selected_option_ids": ["move_criminal_pawn_p0_03_hood_05"]
}
```

Wrapper sottile su `application/legal_actions.py::build_command_from_selection`:
il client seleziona solo tra `PendingDecision.options` (mai un payload di
comando costruito a mano) — pensato per il frontend, che così non deve
conoscere la forma di ciascun `command_type`. `/commands` resta disponibile
per client che devono costruire un comando esplicito (tool di debug, test).

### Avanzamento automatico bot

```http
POST /api/v1/games/{game_id}/advance
```

Il servizio esegue bot ed effetti automatici fino a quando:

- serve una decisione del giocatore umano;
- la partita termina;
- viene raggiunto un limite di sicurezza di passi.

Risposta standard:

```json
{
  "game_id": "game_001",
  "revision": 43,
  "view": {},
  "events": [],
  "pending_decision": {},
  "status": "waiting_for_human"
}
```

### Salvataggi

`GET /api/v1/games/{game_id}/save` e `POST /api/v1/games/load` (implementati,
Milestone 6) coprono snapshot/caricamento — vedi `application/save_load.py`.
Esportazione/importazione di un replay restano da implementare (Milestone 6,
fuori scope finché non esiste una registrazione dei comandi accettati).

## 14. Bot

### 14.1 Interfaccia

```python
class BotPolicy(Protocol):
    def choose(self, view: PlayerGameView, decision: PendingDecision) -> CommandPayload:
        ...
```

### 14.2 Bot MVP

Implementare `RandomLegalBot`:

- sceglie esclusivamente tra opzioni legali;
- usa il RNG della partita o un sottoseed deterministico;
- non legge informazioni nascoste;
- non entra in loop;
- preferisce `pass` solo quando necessario o secondo peso configurato;
- deve permettere di completare migliaia di partite simulate per scoprire deadlock e invarianti violate.

È accettabile aggiungere semplici euristiche per evitare comportamenti bloccanti, ma non sviluppare una strategia complessa prima che il motore sia completo e testato.

### 14.3 Futuri bot strategici

L'architettura deve consentire:

- euristiche modulari;
- scoring delle azioni legali;
- ricerca look-ahead su copie dello stato;
- simulazioni Monte Carlo;
- profili di personalità;
- livelli di difficoltà.

Nessuna di queste funzioni deve essere necessaria per l'MVP.

## 15. Frontend React

> Decisione (2026-08-02): il frontend è React + Vite + TypeScript, non
> Godot — vedi `docs/architecture/decisions/0001-frontend-stack-react-vite.md`.
> Le responsabilità sotto sono le stesse previste fin dall'inizio per
> Godot, riformulate per lo stack attuale: nessuna regola cambia in base
> alla tecnologia scelta.

### 15.1 Responsabilità

Il frontend deve:

- mostrare board, Hoods, pedine, mercato, prezzi, Spots, Links, Jail, Den e Covo;
- mostrare la mano del giocatore umano;
- evidenziare esclusivamente opzioni ricevute dal backend (`PendingDecision.options`);
- inviare il comando selezionato — preferibilmente tramite
  `POST /api/v1/games/{game_id}/decisions/answer` (sezione 13), che accetta
  solo gli `option_id` scelti e lascia al backend costruire il comando
  tipizzato (`build_command_from_selection`), così il frontend non deve mai
  conoscere la forma esatta del payload di ciascun comando;
- riprodurre gli eventi con transizioni/animazioni brevi;
- mostrare log e spiegazione degli errori;
- supportare layout adattivo se la board non entra nello schermo;
- mostrare chiaramente fase, turno, action round, giocatore attivo e decisione pendente.

### 15.2 Stato locale

Un unico stato React (vedi `frontend/src/App.tsx`) conserva solo l'ultima
`GameView` ricevuta e lo stato effimero dell'interfaccia (selezione
corrente, flag di invio in corso, errori).

Non è autorizzato a modificare il gioco. Dopo un comando:

1. blocca input duplicati (flag "submitting");
2. invia il comando;
3. riceve risposta;
4. riproduce gli eventi (quando previsto);
5. sostituisce la vista locale;
6. abilita la decisione successiva.

### 15.3 Componenti riutilizzabili

Creare componenti riutilizzabili almeno per:

- Hood;
- pawn;
- Dope token;
- Cop/Fed;
- Link track;
- Sales Spot;
- card;
- hand;
- Player Base;
- Jail slot;
- decision panel;
- action log;
- score panel.

I componenti devono ricevere dati tramite props esplicite (es. `view: GameViewResponse`) e non devono interrogare direttamente altri componenti per ricostruire lo stato — nessun context/store globale di dominio.

### 15.4 Asset manifest

Tutte le immagini devono essere associate tramite `data/asset_manifest.json`:

```json
{
  "card.customer.example": "customer/example.png",
  "hood.example": "board/hoods/example.png"
}
```

Il backend usa solo `asset_id`, mai percorsi del frontend. Il frontend
risolve `asset_id` in un URL/import servibile da Vite (es.
`/assets/{path}` o un import statico) — non ancora implementato: gli asset
grafici definitivi (tabellone, carte, pedine, token) sono forniti dal game
designer e verranno integrati in un giro successivo (vedi Milestone 6).

## 16. Persistenza, replay e migrazioni

Ogni salvataggio deve includere:

- `schema_version`;
- `rules_version`;
- snapshot completo;
- seed/RNG;
- revision;
- opzionalmente comandi ed eventi successivi all'ultimo snapshot.

Creare funzioni di migrazione quando cambia lo schema. Non modificare in modo incompatibile un formato di salvataggio già rilasciato senza aumentare `schema_version`.

Un replay deve poter ricostruire una partita da:

- configurazione iniziale;
- seed;
- sequenza di comandi accettati.

## 17. Test obbligatori

### 17.1 Unit test

Ogni regola deve avere test per:

- caso valido;
- caso non valido;
- limiti di capacità;
- costi e modifiche di prezzo;
- trigger automatici;
- tie-break;
- assenza di mutazioni parziali dopo comando rifiutato.

### 17.2 Test di scenario

Usare scenari leggibili con nomi descrittivi, per esempio:

```text
test_buying_last_dope_restocks_hood_and_adds_cop
test_selling_third_dope_clears_spot_and_adds_fed
test_fifth_criminal_triggers_brawl
test_sixth_rat_triggers_jail_escape
test_spending_link_allows_only_one_extra_action_per_turn
test_stained_reputation_is_never_restored
test_contact_majority_tie_awards_no_point
```

### 17.3 Simulazioni complete

`tools/run_full_test_game.py` deve poter eseguire partite con 4 bot legali.

Obiettivi minimi:

- nessun crash;
- nessun deadlock;
- nessuna decisione senza opzioni e senza possibilità di passare;
- partita terminata entro un limite ragionevole di comandi;
- invarianti valide dopo ogni comando;
- replay identico allo stato finale originale.

### 17.4 Invarianti

Implementare `validate_invariants(state)` almeno in test e debug. Verificare:

- ogni pawn compare in un solo luogo;
- ogni carta compare in un solo luogo logico;
- quantità totale delle Dope conservata, salvo zone esplicitamente esterne allo stato;
- denaro e prezzi interi;
- capacità non superate;
- owner coerente;
- Link level valido;
- massimo carte in mano quando richiesto dalla fase;
- current player coerente con la phase;
- decisione pendente coerente con stato e giocatore;
- nessun ID duplicato;
- stato serializzabile e deserializzabile senza perdita.

## 18. Workflow dell'agente di sviluppo

Per ogni modifica non banale:

1. leggere il regolamento e i documenti pertinenti;
2. identificare la regola o il requisito da implementare;
3. verificare `RULES_PENDING.md`;
4. proporre o applicare la più piccola modifica coerente;
5. scrivere prima o insieme i test;
6. implementare nel backend;
7. esporre la nuova informazione nella vista/API;
8. aggiungere la UI del frontend solo dopo che il backend è testato;
9. eseguire lint, type check e test;
10. aggiornare documentazione e changelog delle regole quando necessario.

Prima di dichiarare completata una funzione, indicare:

- file modificati;
- regole implementate;
- test aggiunti;
- ambiguità rimaste;
- eventuali effetti sui salvataggi o sull'API.

## 19. Regole di modifica del codice

- Preferire funzioni piccole e pure per calcoli e validazioni.
- Non mutare lo stato prima che tutte le validazioni del comando siano concluse.
- Applicare il comando su una copia o tramite una transazione logica; un errore non deve lasciare stato parziale.
- Non usare eccezioni generiche per normali mosse illegali: restituire errori di dominio tipizzati.
- Non catturare eccezioni senza logging e contesto.
- Non introdurre dipendenze senza motivazione documentata.
- Non creare classi “manager” generiche con responsabilità indistinte.
- Non usare singleton globali per il motore.
- Non accoppiare ID di dominio a path di scene o texture.
- Non usare float per denaro, prezzi, conteggi o punteggi.
- Non riformattare o rinominare grandi parti del progetto mentre si implementa una singola regola.
- Non modificare gli asset originali senza richiesta esplicita.

## 20. Definition of Done

Una feature di gioco è completata solo quando:

- la regola è documentata o collegata a una decisione approvata;
- esiste un comando o un trigger chiaro;
- il backend valida i prerequisiti;
- il backend produce eventi;
- lo stato finale rispetta le invarianti;
- esistono test positivi e negativi;
- la serializzazione include i nuovi dati;
- il generatore di azioni legali la espone;
- almeno il bot casuale può attraversarla senza logica speciale illegale;
- il frontend può visualizzarla e inviare la scelta senza calcolare regole;
- eventuali modifiche API o schema sono versionate.

## 21. Ordine di implementazione

### Milestone 0 — Fondazioni

- repository e tooling;
- loader e validatore dei file dati;
- ID, enum e modelli base;
- `GameState` serializzabile;
- RNG deterministico;
- command bus, eventi ed errori;
- test delle invarianti.

### Milestone 1 — Setup e navigazione del turno

- creazione partita 1 umano + 3 bot;
- setup data-driven;
- fasi e action round;
- ordine giocatori;
- decisioni pendenti;
- endpoint minimi;
- frontend debug testuale.

### Milestone 2 — Azioni economiche principali

- piazzamento;
- movimento;
- acquisto;
- vendita;
- prezzi;
- Marketing;
- Cops/Feds bloccanti;
- mano e scarti.

### Milestone 3 — Links, officers e Jail

- creazione/scorrimento/spesa Links;
- corruzione;
- arresto e confisca;
- acquisto officers;
- Jail ed Evasione.

### Milestone 4 — Rissa e Poker

- flussi multi-step;
- informazioni nascoste;
- tie-break;
- eventi e animazioni.

### Milestone 5 — Jobs, Skills, Retate e punteggio

- requisiti data-driven;
- REP e REP macchiata;
- maggioranze;
- fine partita;
- schermata risultati.

### Milestone 6 — Partita completa e UX

- `RandomLegalBot` robusto;
- simulazioni massive;
- salvataggio/caricamento;
- replay;
- frontend React completo con gli asset grafici definitivi (tabellone, carte, pedine, token);
- tutorial e messaggi di errore.

Non sviluppare bot strategici prima del completamento stabile della Milestone 6.

## 22. Regole da chiarire prima o durante l'implementazione

Registrare le risposte definitive anche in `docs/rules/RULES_PENDING.md` e poi spostarle in `RULES_CANONICAL.md`.

### Bloccanti o ad alta priorità

1. **Durata:** l'introduzione parla di 4 giorni, mentre la sezione delle fasi parla di 3 turni. Quanti turni completi ha una partita?
2. **Setup iniziale:** denaro, numero di pedine, carte iniziali, Chips, merci nei Hoods, Cops/Feds, primo giocatore e Hoods iniziali.
3. **Grinta:** numero di segnalini, posizioni iniziali, elenco delle azioni, associazione azioni–Contacts e significato esatto del valore di Grinta.
4. **Prezzi:** associazione dei prezzi iniziali `3, 1, 4, 6` ai tipi di Dope; minimo e massimo; comportamento al limite; ordine preciso del crollo del mercato.
5. **Mappa:** nomi dei 10 Hoods, Contact, adiacenze e distribuzione iniziale delle Dope.
6. **Contacts e Spots:** elenco completo, due tipi di Dope accettati da ciascun Contact e adiacenza tra Spots per il movimento dei Feds.
7. **Carte Clienti:** dataset completo, boost, simboli Poker, Stonks, Guns ed effetto Gamble.
8. **Poker:** come si costruisce esattamente una combinazione di 5 simboli se ciascun giocatore rivela una carta con due simboli; significato di “5 colori uguali/diversi”; gestione dei giocatori senza carta valida.
9. **Jobs:** requisiti dei 9 tipi, livelli, copie, modalità di verifica e contenuto delle Skills.
10. **Retate:** condizioni complete delle 7 carte, valutazione delle squadre e identificazione dei singoli giocatori che macchiano REP.
11. **Punteggio denaro:** conversione esatta dell'ordine sul tracciato denaro nelle posizioni/punti 1–4.

### Ambiguità di risoluzione

12. Quando il sesto Rat provoca l'Evasione, in quale ordine diventa Link dai Politici e torna al Covo?
13. Un Link arrestato perde definitivamente il livello e torna come normale pedina dopo l'Evasione?
14. I Cops/Feds “rimandati al Commissariato” entrano in una riserva separata o occupano i 6 slot della Jail?
15. Quando si comprano Cops/Feds dal Covo di un altro giocatore, il proprietario può opporsi? Quale presenza nella località è richiesta?
16. In una corruzione le due azioni devono essere di tipo diverso. Possono avere lo stesso bersaglio? Qual è l'ordine dei trigger intermedi?
17. Se un Fed deve arrestare il Link di livello minore e più Link sono pari, chi sceglie?
18. Una Rissa considera solo il quinto `Criminal`, oppure anche altri ruoli fisicamente presenti?
19. I Links contano in ogni Hood del Contact anche se ciò produce presenza in più Risse simultaneamente?
20. La carta Rissa può assegnare tutte le Guns a un unico partecipante o distribuirle? Le Guns negative possono portare la forza sotto zero?
21. Nella Rissa il vincitore sceglie una sola tipologia di ricompensa globale o una ricompensa per ciascuno sconfitto?
22. L'invio del Criminal sconfitto in un Hood inesplorato è scelto dal vincitore, dallo sconfitto o automaticamente?
23. Ordine completo dei tie-break della Rissa e significato di “primo giocatore, o seguenti”.
24. In acquisto/vendita a pacchetto, ciascuna merce usa lo stesso prezzo iniziale del pacchetto oppure un prezzo progressivo con sola modifica del track rinviata?
25. Il Marketing può modificare anche altre Dope non direttamente comprate/vendute nel pacchetto? Il testo sembra limitarlo alle merci trattate.
26. Se il Covo è pieno, una merce acquistata o recuperata dall'Evasione può essere persa, rifiutata o sostituita?
27. Quando uno Spot si svuota per effetto di un Fed, entra comunque un nuovo Fed come nel caso riempimento/svuotamento descritto nei componenti?
28. Quando Cops/Feds non hanno più le condizioni per restare, il controllo di rientro avviene immediatamente dopo ogni evento o a fine azione?
29. Il limite di 5 carte viene applicato dopo ogni action round del giocatore, dopo l'intera fase Azione o in entrambi i momenti?
30. “Una sola azione extra per turno” significa per giocatore per turno completo, non per action round?
31. Ordine di scelta del primo giocatore quando nessuno possiede Link presso i Preti.
32. Regole per la capienza del Den e conseguenze quando è pieno.
33. Quantità e significato delle Chips Poker nel Covo, oltre al limite di 3.
34. Modalità di scelta della carta pescata “a scelta” nel Den: Contact/deck, carta visibile o pesca casuale dal mazzo scelto.

Finché un punto resta aperto, il codice deve segnalarlo chiaramente e non trasformare una supposizione in regola definitiva.

## 23. Prima attività consigliata all'agente

Prima di implementare scene o regole avanzate:

1. creare i file di progetto e la struttura base;
2. convertire il regolamento in `RULES_CANONICAL.md` senza reinterpretarlo;
3. creare `RULES_PENDING.md` usando la sezione precedente;
4. definire gli schemi JSON per board, carte e configurazione;
5. implementare un `GameState` minimale serializzabile;
6. implementare setup configurabile e macchina a stati vuota;
7. creare `RandomLegalBot` contro decisioni fittizie;
8. eseguire una partita scheletro completa senza regole, solo per validare il flusso Python ↔ frontend;
9. implementare le regole una alla volta con test di scenario.

L'obiettivo iniziale non è mostrare una board completa: è ottenere un motore deterministico, testabile e incapace di accettare azioni illegali.
