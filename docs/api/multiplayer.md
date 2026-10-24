# API multiplayer (v1)

Stanze private da 2 a 4 umani, bot sui posti vuoti, polling. Decisione e scostamenti dalla guida:
[`0002-multiplayer-session-layer.md`](../architecture/decisions/0002-multiplayer-session-layer.md).

Tutte le route sono sotto `/api/v1`. Le route del gioco contro i bot (`/games/...`) non toccano le partite multiplayer.

## Identità

Creando o entrando in una stanza si riceve un **token di posto** segreto (`seat_token`): è l'unica cosa che dice chi sta
chiamando. Si manda come `Authorization: Bearer <seat_token>`. Nessuna route multiplayer legge un `player_id` dal client.
Il token va conservato dal browser (non nell'URL, non nei log), vale solo per la propria stanza/partita e permette di
rientrare dopo un ricaricamento. Il codice stanza **non** è un segreto di autorizzazione: serve solo a chiedere di entrare.

## Errori

Corpo `{"error": <codice>, "message": <testo>, "details": {...}}`.

| Stato | Codici |
|---|---|
| 400 | `invalid_request`, `invalid_decision` (selezione illegale; `details.domain_error` dice quale regola) |
| 401 | `invalid_token` (manca, sconosciuto o di un'altra stanza/partita) |
| 403 | `forbidden` (solo l'host può avviare) |
| 404 | `room_not_found`, `game_not_found` |
| 409 | `room_full`, `room_already_started`, `room_not_ready` (`details.missing_seat_indexes`), `room_closed`, `nickname_taken`, `not_your_turn`, `stale_revision` (`details.expected`, `details.received`), `stale_decision`, `game_finished` |
| 422 | corpo malformato (validazione FastAPI) |

Un 409 `stale_revision`/`stale_decision` vuol dire "il gioco è andato avanti": rileggere vista ed eventi.

## Stanze

| Route | Cosa fa |
|---|---|
| `POST /rooms` `{ruleset, human_seats (2-4), bot_policy, nickname}` | Crea la stanza; chi crea è l'host (posto 0). Risponde con `room_code`, `seat_index`, `player_id`, `seat_token`. `ruleset` default `easy_price`, `bot_policy` default `heuristic`. Il seed lo sceglie il server. |
| `GET /rooms/{code}` | Stato pubblico: stato della stanza, posti (nickname, umano o bot, occupato, host), `game_id` quando è partita. Mai token. |
| `POST /rooms/{code}/join` `{nickname}` | Prende il primo posto umano libero; risponde con le credenziali. |
| `POST /rooms/{code}/start` (token dell'host) | Serve che tutti i posti umani siano occupati. Crea la partita, fa muovere i bot fino alla prima decisione umana. |
| `POST /rooms/{code}/leave` (token) | In lobby libera il posto (l'host che esce chiude la stanza). In partita il posto passa a un bot. |

I codici stanza sono di 4 caratteri, senza maiuscole/minuscole e senza i simboli ambigui.

## Partita

`game_id` si legge da `GET /rooms/{code}` dopo l'avvio.

| Route | Cosa fa |
|---|---|
| `GET /mp/games/{game_id}/view` | Stanza, il proprio posto, `revision`, `awaiting_player_id` (di chi è la decisione), `status` e la **vista** del proprio giocatore (la stessa del solo, con la propria mano, la propria decisione pendente e senza l'ordine dei Job non rivelati). |
| `GET /mp/games/{game_id}/events?since=<revisione>&include_view=<bool>` | I blocchi di eventi con `revision_to > since`, già filtrati per il proprio giocatore; `current_revision`, `awaiting_player_id`, `status`, `requires_refresh` (`since` oltre la partita). Con `include_view` anche la vista. **Non muove mai il gioco**; ripeterla dà lo stesso risultato. |
| `POST /mp/games/{game_id}/decisions/plan` `{decision_id, selections}` | Anteprima delle scelte preparatorie (Grinta, tipo di azione, Gancio, Marketing, Poker) su copie dello stato. Non consuma nulla. Solo per la propria decisione. |
| `POST /mp/games/{game_id}/decisions/answer` `{decision_id, expected_revision, selected_option_ids, preparatory_selections}` | Risponde alla propria decisione. Il server applica il comando, fa muovere i bot fino alla prossima decisione umana e risponde con revisione, stato, `awaiting_player_id`, i blocchi di eventi prodotti e la vista aggiornata. |
| `POST /mp/games/{game_id}/leave` (token) | Come sopra, per partita. |

### Blocchi di eventi

```json
{"index": 12, "revision_from": 40, "revision_to": 43, "actor_player_id": "player_2",
 "segment_type": "bot_segment", "events": [ {"event_type": "CriminalMoved", "...": "..."} ]}
```

Poker: le carte scelte restano coperte. Gli altri ricevono solo `PokerCardCommitted` ("ha scelto", con il numero di carte);
quando l'ultimo ha scelto, nello stesso blocco escono insieme tutti i `PokerCardRevealed` e poi `PokerMatchResolved`.

`segment_type`: `game_start`, `human_command`, `bot_segment`, `seat_left`. Gli indici e le revisioni sono contigue
(`revision_to` di un blocco = `revision_from` del successivo). Ogni segmento di bot è un blocco a sé, per poter
raccontare un'azione alla volta.

### Cosa vedono gli altri giocatori degli eventi

Pubblico: quasi tutto. Redatto per chi non è il destinatario: `CardDrawn.card_id` e le carte pescate come premio di un Job (`null`),
`CardsDiscarded.card_ids` (una lista di `null`: si vede quante, non quali), `BrawlLoserRewardChosen.stolen_card_id` (visibile solo a
vincitore e sconfitto), `GameStarted.seed` (sempre 0).

### Ciclo tipico di un client

1. `POST /rooms` o `POST /rooms/{code}/join` → salvare `seat_token`.
2. `GET /rooms/{code}` finché `status` è `running` → `game_id`.
3. `GET .../view` per partire; ricordare `revision`.
4. Ogni ~1 s: `GET .../events?since=<ultima revisione vista>`; animare i blocchi nuovi; aggiornare l'ultima revisione.
5. Se `awaiting_player_id` è il proprio: leggere `view.pending_decision` e rispondere con `.../answer`
   (con `expected_revision` = `revision` della vista).
6. Dopo un ricaricamento della pagina: ripartire da `view` (e da `events?since=0` se serve la storia).
