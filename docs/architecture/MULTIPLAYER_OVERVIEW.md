# DOPE multiplayer: cosa abbiamo e cosa possiamo fare

Documento di discussione, 2026-10-24. Scritto per essere letto da un chatbot che non vede il codice: tutto ciò che serve
è qui dentro. Nessuna decisione è presa; le scelte aperte sono in fondo (sezione 8).

**Obiettivo:** più persone umane nella stessa partita, con **le stesse regole della modalità Easy Price** (nessuna regola
nuova: il multiplayer è un livello di sessione e di trasporto sopra il motore esistente).

## 0. In breve

- Il motore di gioco è già adatto: è autoritativo, deterministico, serializzabile, decide **una cosa alla volta** (una
  decisione pendente con il giocatore a cui spetta) e produce una **vista per giocatore** con le informazioni nascoste
  tolte. Le regole non vanno toccate.
- Quasi tutto il lavoro sta fuori dal motore. Oggi il sistema presume **un solo umano e tre bot**, senza identità né
  stanze, con le partite solo in RAM e i bot fatti avanzare dal browser.
- I cinque nodi da sciogliere: (1) un solo umano per partita, (2) nessuna autenticazione (chiunque può leggere la mano
  di chiunque, o scaricare e ricaricare uno stato), (3) i bot avanzano solo se il browser lo chiede, (4) lo stato vive in
  RAM in un solo processo, (5) gli eventi che il server manda non sono filtrati per giocatore.
- Strada proposta (sezione 6): server-driven con token per posto e log di eventi per partita; stanze con codice; poi
  ripristino dopo riavvio e gestione di chi sparisce; poi tutto il resto (matchmaking, account, spettatori).

## 1. Il gioco in poche righe

- **4 giocatori fissi** (le Retate dividono i giocatori in squadre 1+4 contro 2+3 secondo l'ordine di gioco). Con meno
  umani, gli altri posti sono bot.
- **3 turni**, ognuno con **3 round d'azione**; nel round ogni giocatore, a partire dal primo, sceglie un segnalino
  **Grinta** (1, 2 o 3) e **un'azione** tra 6 (Piazza, Sposta, Compra, Vendi, Manovra Cops/Feds, Corrompi Cops/Feds),
  agendo con tante pedine quanto la Grinta. Non si ripete la stessa azione base nello stesso turno. In più, prima o dopo
  l'azione principale si può **spendere un Link** per un'azione extra; durante l'azione si può giocare **Marketing** (carte
  Stonk che spostano i prezzi) e lanciare un **Poker** (una partita per round, puntata e risolta a fine round).
- **Eventi che interrompono il turno e coinvolgono altri giocatori:** la **Rissa** (al quinto Criminale in un Quartiere:
  i partecipanti dichiarano una carta coperta in ordine, poi si rivela tutto), il **Poker** (puntate e carte), le **Retate**
  (a fine turno, squadre contro squadre, macchiano REP), i **Job** (completati in automatico da chi li soddisfa, anche
  durante il turno di altri; il giocatore sceglie il premio).
- **Informazione nascosta:** la mano di carte (si vede solo il numero degli altri), le carte coperte della Rissa fino alla
  rivelazione, le carte pescate. Tutto il resto del tabellone è pubblico.
- **Easy Price** (`data_packs/easy_price`, sopra la Big): prezzi su quattro livelli che cambiano solo quando un Punto di
  Vendita si riempie, un Quartiere si svuota o per Marketing; il Poker non dà soldi al lancio ma il vincitore prende 2$ per
  partecipante; nella Rissa il vincitore ruba sempre una carta. Dettagli in `docs/variants/EASY_PRICE.md`.
- Dimensioni: 10 pedine a testa, mappa di 10 Quartieri, Den, Jail a 4 posti, mano massima 5 carte.

## 2. Cosa abbiamo oggi

### 2.1 Architettura (a strati, senza cicli)

```text
Browser (React + Vite + TypeScript; GitHub Pages / dope-game.it in iframe)
   | HTTPS + JSON, nessuna autenticazione; player_id nel corpo o nella query
   v
FastAPI (adapters/http/app.py, ~1.170 righe; un processo su Render)
   |   _games: dict game_id -> GameState   (in RAM)
   |   _undo_snapshots, un GameService per ruleset
   |        |
   |        +--> adapters/persistence/db.py -> Postgres (Supabase): solo telemetria
   |             (tabelle games, game_players, game_events) e classifica; mai autorevole
   v
application/ GameService -> CommandBus -> rules/*   (dominio puro, nessuna dipendenza da FastAPI)
   |-- legal_actions.get_legal_decision: la UNICA decisione legale pendente
   |-- views.build_player_view: la vista filtrata per un giocatore
   '-- bots/ (RandomLegalBot, HeuristicBot): stessa interfaccia dell'umano
```

- **Stato**: un `GameState` (dataclass) completamente serializzabile in JSON, con seed e stato del generatore casuale
  dentro. Le trasformazioni sono `stato + comando validato -> nuovo stato + eventi di dominio` (`CommandBus`, lavora su
  una copia profonda: un comando rifiutato non lascia mai stato a metà).
- **Giocatori**: `PlayerState.controller_type` è `HUMAN` o `BOT`. In `create_initial_state` c'è **un solo** `human_seat`;
  gli altri posti diventano bot (nome "Player N").
- **Comandi**: ogni comando porta `game_id`, `player_id`, `expected_revision` (scarta i comandi su stato vecchio) e un
  payload tipizzato. Il motore controlla che a muovere sia il giocatore giusto (`current_player_id`, passo attivo).
- **Decisioni**: `state.pending_decision` ha `player_id`, tipo, opzioni, min/max scelte, `can_pass`. Il client sceglie
  solo tra le opzioni; `POST /decisions/answer` costruisce il comando dal solo elenco di `option_id`. Tutte le
  decisioni sono **sequenziali**: anche Rissa, Poker e premi dei Job chiedono un giocatore alla volta (non c'è nessuna
  fase in cui più giocatori scelgono insieme).
- **Rotazione**: `current_player_id` cambia anche quando la decisione tocca un altro giocatore (partecipanti a una
  Rissa, chi riscuote un Job, chi sceglie il primo giocatore a inizio turno, cioè il Link più alto presso i Preti).
- **Viste**: `view_for(state, player_id)` espone tabellone, pedine, prezzi, Job e Skill pubblici, numero di carte (non le
  carte) degli altri, e `pending_decision` solo se è del giocatore che guarda.
- **Bot**: scelgono sempre tra le opzioni legali. `GameService.advance(state)` fa girare bot e fasi automatiche finché
  tocca a un umano o la partita finisce (con l'opzione "un solo segmento": si ferma dopo ogni azione di un bot, per
  poterla raccontare).
- **Salvataggio e replay**: `GET /save` dà lo stato intero, `POST /games/load` lo ricarica (con versione di schema);
  `GET /replay` dà seed + comandi accettati; strumenti da riga di comando li riverificano. Esistono 627 test backend e
  simulatori massivi bot contro bot.

### 2.2 Come gira una partita oggi (protocollo del client)

1. `POST /api/v1/games` con `human_seat`, `ruleset` (`standard`, `simple`, `easy_price`), `bot_policy`, `seed`,
   `nickname` -> `game_id`. Il client assume di essere `player_<human_seat>`.
2. Finché non tocca all'umano il **browser** chiama `POST /games/{id}/advance?single_player_segment=true`: il server fa
   un segmento di un bot e restituisce eventi + vista; il client li anima (`TurnPlayback`), mostra i popup di Rissa, Poker e
   Retata (che il giocatore deve confermare con OK), aggiorna il log.
3. Turno dell'umano: `GET /view?player_id=...` (decisione filtrata); `POST /decisions/plan` simula scelte preparatorie
   (Grinta, tipo di azione, "Gancio", Marketing, Poker) su copie dello stato per mostrare anteprime senza consumare
   nulla; `POST /decisions/answer` esegue la scelta (con eventuali scelte preparatorie in un colpo solo, atomico).
4. `POST /undo`: annulla fino a 4 comandi dell'umano, ma solo se nessun altro ha agito nel frattempo e non è stata
   pescata una carta, data una Skill o scoperto un Quartiere nascosto.
5. A fine partita: punteggi e classifica (Supabase) solo per la modalità Big; Easy Price e Small sono per ora fuori dalla
   classifica.

### 2.3 Cosa è già a favore del multiplayer

- Autorità sul server, regole solo nel backend, dominio senza HTTP: aggiungere un trasporto non tocca le regole.
- Determinismo e stato serializzabile: salvare, riprendere dopo un riavvio, rigiocare e fare debug sono già possibili.
- Una sola decisione pendente per volta con un destinatario chiaro: non servono risoluzioni simultanee.
- Vista filtrata per giocatore già costruita; la preview (`/decisions/plan`) lavora su copie e non ha effetti.
- Bot con la stessa interfaccia degli umani: sono già i "riempitivi" naturali per i posti vuoti e per chi si disconnette.
- Il database Supabase ha già `player_type` per ogni posto e un registro eventi.
- Il comando porta `expected_revision`, quindi i comandi duplicati o su stato vecchio vengono rifiutati.

### 2.4 Cosa non va bene per il multiplayer (stato attuale)

| # | Limite | Dove | Conseguenza |
|---|---|---|---|
| 1 | Un solo umano per partita | `create_initial_state(human_seat=...)`, `CreateGameRequest`, nel client `humanPlayerId` fisso e il ciclo "finché non tocca a me chiama advance" | Serve passare a posti con tipo di controllore per ognuno e un client che non assuma "io sono l'unico umano" |
| 2 | Nessuna autenticazione | `GET /view?player_id=player_2` restituisce la mano di player_2; `POST /commands` si fida del `player_id` nel corpo; `/save`, `/replay` danno l'intero stato (mani, mazzi, seme); `/games/load` accetta uno stato qualunque | Barare è banale. Servono token per posto e limiti su save/replay/load |
| 3 | Bot guidati dal client | `/advance` è chiamato dal browser | Con più umani nessuno ha il compito di far muovere i bot; va spostato sul server |
| 4 | Stato solo in RAM | `_games`, `_undo_snapshots`, `GameService._command_history` e la policy dei bot per partita sono dizionari in un processo | Un riavvio perde tutte le partite; con più processi (`--workers`) si rompe |
| 5 | Nessun controllo di concorrenza | Gli endpoint sincroni girano in un pool di thread; `_games[id] = nuovo_stato` è "l'ultimo che scrive vince"; `/advance` non controlla la revisione | Due richieste insieme possono perdere una mossa |
| 6 | Eventi non filtrati e non memorizzati | `/commands`, `/answer`, `/advance` restituiscono gli eventi solo a chi ha fatto la richiesta; `CardDrawn` contiene l'id della carta; nessun log per partita da cui "recuperare" gli eventi persi | Gli altri umani non vedono cosa hanno fatto gli avversari, e quando lo vedranno non va mostrato chi ha pescato cosa |
| 7 | Una fuga di informazione di design | `job_progress_by_player.tier_piles` espone l'ordine dei Job futuri di tutti | Accettabile contro bot (commento nel codice), da decidere contro umani |
| 8 | Annulla pensato per un umano | `_undo_snapshots` per partita, invalidato quando "un bot ha agito" | Con più umani va invalidato quando agisce chiunque altro; da decidere se esiste ancora |
| 9 | Popup bloccanti | Rissa, Poker, Retata e "Turno N" aspettano l'OK del giocatore prima che il gioco prosegua, nel client | In una partita condivisa non può bloccare gli altri: l'OK deve diventare solo locale |
| 10 | Niente stanze, identità, timer | Nessun concetto di lobby, nickname univoco, "pronto", abbandono, riconnessione, inattività | Va costruito da zero |
| 11 | Hosting | Frontend statico su GitHub Pages; backend su Render (un servizio, deploy automatico a ogni push in `main`); CORS con elenco fisso di origini | Da verificare: se il piano di Render addormenta il servizio per inattività; cosa succede alle partite in corso al deploy |

## 3. Cosa significa "multiplayer": scelte di prodotto

Le risposte cambiano molto l'architettura:

1. **Tempo reale o a distanza?** Reale: tutti collegati insieme, partita di decine di minuti. A distanza (asincrona):
   si gioca una mossa quando si può, si riceve un avviso; richiede persistenza forte e notifiche.
2. **Quanti umani?** Da 2 a 4, con i bot a riempire; oppure solo 4 umani. Con 1 umano resta il gioco di oggi.
3. **Come ci si trova?** Stanza privata con codice o link da condividere; oppure coda pubblica; oppure entrambe.
4. **Identità:** solo nickname (anonimo, con token salvato nel browser), oppure account (e-mail/Google, tramite Supabase Auth,
   già in uso come database).
5. **Chi sparisce:** timer per mossa? Un bot subentra e poi si può riprendere il posto? Si può abbandonare?
6. **Spettatori e replay:** guardare una partita, ricondividere la ripresa.
7. **Chat o emoji** tra giocatori (se sì, moderazione).
8. **Classifica:** una sola per tutte le modalità o una per modalità (oggi Easy Price è esclusa, in via provvisoria).

## 4. Opzioni di architettura

### 4.1 Tempi e trasporto

| Opzione | Come | Pro | Contro |
|---|---|---|---|
| A. Polling | Ogni client chiede `GET /games/{id}/events?since=<revisione>` ogni 1-2 s | Semplicissimo, funziona ovunque, nessuno stato di connessione | Latenza e traffico; scalabile poco |
| B. Long polling / SSE | Il client apre uno stream `GET /games/{id}/stream` (Server-Sent Events); i comandi restano POST | Eventi subito; resta HTTP; FastAPI lo gestisce; si riprende da `Last-Event-ID` | Un processo deve tenere aperte le connessioni; servono regole per il proxy di Render |
| C. WebSocket | Un canale bidirezionale per partita | Il più flessibile (presenza, chat) | Più codice e più casi di errore; per un gioco a turni non serve di più |

Il gioco è a turni e la banda minima: **B (SSE)** o, per iniziare, **A** con la stessa API (`since`) è la scelta più semplice;
passare a SSE dopo cambia solo il trasporto.

### 4.2 Dove gira il "motore delle partite"

- **Un solo processo, partite in RAM, snapshot su database ad ogni revisione** (consigliata all'inizio): una partita =
  un oggetto con il proprio **lock** e l'elenco di client in ascolto. Si ripristina dai snapshot (`to_save_dict`).
  Limite: un solo processo e un solo servizio.
- **Stato nel database** (ogni richiesta carica lo stato, applica il comando, lo salva): più robusto e scalabile, ma ogni
  mossa costa un viaggio al database e serve un lock in lettura-scrittura.
- **Un "attore" per partita su una coda** (es. Redis): serve solo se si va oltre una macchina; fuori portata ora.

### 4.3 Chi fa muovere i bot

Oggi il browser. Nel multiplayer lo fa il **server**, subito dopo ogni comando accettato: esegue `advance` finché tocca
a un umano e **mette gli eventi nel log della partita**. Per non far saltare l'animazione, si può aggiungere un ritardo
fra un segmento e l'altro, o far ricostruire il ritmo al client dai confini di segmento già presenti negli eventi.

## 5. Che cosa cambierebbe, pezzo per pezzo

**Motore (poco).**
- `create_initial_state` accetta un elenco di posti `[{kind: human|bot, name}]` al posto di `human_seat`.
- I nomi dei bot restano; il nome dell'umano viene dal nickname del posto.
- Il resto (regole, comandi, decisioni) invariato. Da verificare con test: nessuna regola assume "il giocatore 0 è
  l'umano" (cercare `human_seat`, `HUMAN`, `player_0`).

**Applicazione.**
- Un **registro delle partite** (nuovo): per partita, stato, lock, log eventi per revisione, posti con token, policy dei
  bot, stato della stanza (in attesa, in corso, finita). Sostituisce i dizionari sparsi in `app.py`.
- **Eventi**: ogni comando accettato produce un blocco `{revision, actor, eventi}`; il log è consultabile da
  `since=<revisione>`. Ogni evento passa da un **filtro per destinatario** che toglie ciò che non va visto (id delle carte
  pescate dagli altri, carte coperte della Rissa fino alla rivelazione, ecc.). Un test controlla che nessun evento
  filtrato contenga un `card_id` della mano di un altro.
- **Autorizzazione**: ogni richiesta porta un token di posto; il server deduce `player_id` dal token e lo confronta con il
  comando. `GET /view` restituisce solo la vista del proprio posto. `/save`, `/replay` e `/load` restano solo per
  strumenti interni (token amministratore) o diventano "esporta la mia partita finita".
- **Concorrenza**: un lock per partita attorno a "leggi stato, applica comando, salva stato, accoda eventi, fai girare i
  bot". I comandi restano protetti da `expected_revision`.
- **Annulla**: nel multiplayer o si toglie, o resta solo fino al primo comando di un altro giocatore (la regola attuale,
  riscritta per "qualunque altro posto ha agito"); le anteprime del pianificatore non cambiano.

**API (nuove o cambiate).**
- `POST /rooms` (crea stanza: modalità, numero di posti umani, bot a riempimento, privata/pubblica) -> codice stanza;
  `POST /rooms/{code}/join` (nickname) -> token di posto; `POST /rooms/{code}/ready`, `.../leave`, `.../start`.
- `GET /games/{id}/view` (token), `POST /games/{id}/decisions/answer|plan|undo` (token), `GET /games/{id}/events?since=` o
  `GET /games/{id}/stream` (SSE).
- Le rotte attuali per il gioco contro i bot restano come modalità "solo" (token creato in automatico).

**Persistenza.**
- Snapshot dello stato (`to_save_dict`) e, per sicurezza, del log comandi, a ogni revisione o ogni N, in una tabella nuova
  (partita, revisione, JSON, posti, policy bot, ruleset). Al riavvio si caricano le partite non finite.
- La tabella esistente `game_players.player_type` copre già "umano o bot" per posto; mancano gli identificativi dei
  giocatori umani se si vuole la classifica per persona.

**Frontend.**
- Schermata iniziale con "gioca da solo" (come oggi) e "crea stanza / entra con codice"; lobby con i posti, i nickname e
  "pronto".
- `App.tsx` smette di assumere `humanPlayerId` e il ciclo `advance`: la vista arriva dal flusso eventi; lo stesso
  `TurnPlayback` riproduce gli eventi di chiunque (anche di altri umani), non solo dei bot.
- Banner "tocca a Marco" con eventuale timer; stato di connessione (riconnessione con lo stesso token).
- I popup di Rissa, Poker e Retata restano ma l'OK diventa locale e non ferma il server.
- Colori e nomi per posto già esistono (`playerColorForId`).

**Test.**
- Simulatore con N client HTTP finti (bot che si comportano da umani) contro il server vero: partite complete con 2, 3 e
  4 umani, richieste in parallelo, disconnessioni e riconnessioni casuali, controllo delle invarianti dopo ogni comando.
- Test di sicurezza: un token non può leggere le mani degli altri né comandare per altri; ripetizioni e comandi vecchi
  vengono rifiutati.
- Ripetibilità: stesso seme e stessa sequenza di comandi danno lo stesso stato (c'è già; va esteso con più umani).

## 6. Percorso proposto, a fasi

| Fase | Contenuto | Esito verificabile | Impegno |
|---|---|---|---|
| 1. Nucleo server | Registro partite con lock; posti con token; autorizzazione; bot guidati dal server; log eventi con filtro per destinatario; `create_initial_state` con più posti | Partita 2-4 "umani" fatti da client finti, completa e identica nei risultati a una simulata; test di fuga di informazioni | Medio-alto |
| 2. Stanze e client | Crea/entra con codice, lobby, `App.tsx` senza il vincolo "un solo umano", riproduzione degli eventi di tutti, popup con OK locale | Quattro finestre del browser giocano una partita completa | Alto (è la parte più grande del frontend) |
| 3. Robustezza | Snapshot e ripristino dopo riavvio, riconnessione, timer e subentro del bot, abbandono, pulizia partite ferme, limiti di richieste | Riavvio del server a metà partita senza perdere nulla; un giocatore sparisce e il bot lo sostituisce | Medio |
| 4. Prodotto | Coda pubblica, account, classifica per modalità, spettatori, chat, asincrono con notifiche | A seconda delle scelte | Variabile |

La fase 1 si può provare senza toccare il frontend (client finti da riga di comando), quindi è il primo passo naturale.

## 7. Rischi

- **Informazione nascosta**: i log degli eventi sono il punto dove è più facile far trapelare una mano; servono il filtro
  e il test dedicato prima di far giocare umani veri.
- **Ritmo di gioco**: i bot oggi sono lenti a posta (animazioni raccontate dal browser). Se il server li fa muovere subito, gli
  umani vedranno scatti: serve decidere dove sta il ritmo (server o client).
- **Hosting**: un solo servizio con le partite in RAM è il collo di bottiglia e il punto debole (un deploy a metà partita).
  Da capire quanto è un problema reale (quante partite insieme, quanto durano).
- **Tempi lunghi di gioco**: una partita a 4 umani può durare molto; senza timer una persona lenta ferma tutti.
- **Regole che assumono un umano**: tutorial, classifica e reportistica leggono un solo posto umano.

## 8. Domande aperte (da portare al chatbot)

1. Tempo reale, asincrono, o prima solo tempo reale con lo stesso schema pronto a diventare asincrono?
2. Umani per partita: 2-4 con bot a riempimento, o solo 4? I bot vanno dichiarati agli altri giocatori?
3. Stanza privata con codice come prima versione? Serve subito la coda pubblica?
4. Identità: solo nickname con token nel browser, o account? Cosa si vuole sapere di una persona tra una partita e l'altra
   (classifica, storico)?
5. Timer per mossa: quanto, e cosa succede allo scadere (passa, gioca il bot, si salta)? Un giocatore che torna può
   riprendersi il posto dal bot?
6. "Annulla": tenerlo nel multiplayer (e con quale limite) o toglierlo? Le anteprime di scelta restano in ogni caso.
7. Informazione nascosta: i Job futuri degli altri giocatori devono restare visibili (come oggi) o nascosti? Le carte
   scartate e l'identità delle carte pescate dagli altri?
8. Chi può vedere la ripresa (replay) di una partita finita?
9. Come si ritma la partita: velocità fissa delle azioni dei bot, conferma di visione dei popup, tempo minimo fra eventi?
10. Hosting: quante partite contemporanee si prevedono? Va bene un solo servizio (con partite in RAM più snapshot) all'inizio?
11. Si tiene una classifica separata per modalità e per numero di umani?
12. Che cosa serve per un primo test con amici (quattro persone, una stanza, codice condiviso) e cosa può aspettare?

## 9. Appendice: dove sta cosa nel repository

- `data/`, `data_packs/easy_price/`, `data_packs/simple/`: contenuti e configurazione; l'Easy Price è un pacchetto
  sovrapposto alla Big (`game_config.overrides.json`, `dope_types.json`).
- `backend/src/dope_engine/domain/`: stato, comandi, eventi, decisioni (dataclass, nessuna dipendenza esterna).
- `backend/src/dope_engine/rules/`: regole (turno, economia, Rissa, Poker, Job, Retate, Jail, punteggio...).
- `backend/src/dope_engine/application/`: `game_service.py` (crea partite, `dispatch`, `advance`, `answer_sequence`),
  `legal_actions.py` (le decisioni legali, ~2.900 righe), `views.py` (viste per giocatore), `command_bus.py`,
  `save_load.py`, `replay.py`, `human_planning.py` (scelte preparatorie).
- `backend/src/dope_engine/bots/`: `random_legal.py`, `policies.py` (euristico), `scoring.py`.
- `backend/src/dope_engine/adapters/http/app.py` e `schemas.py`: le rotte; `adapters/persistence/db.py`: Postgres.
- `frontend/src/`: `App.tsx` (flusso a un solo umano), `api.ts`, `components/BoardView.tsx` (tabellone, ~2.000 righe),
  `TurnPlayback.tsx`, `useHumanActionPlan.ts`, `outcome-queue.ts`, `log-narration.ts`.
- `docs/rules/` regole e storico delle decisioni, `docs/variants/EASY_PRICE.md`, `tools/` simulatori e strumenti.
