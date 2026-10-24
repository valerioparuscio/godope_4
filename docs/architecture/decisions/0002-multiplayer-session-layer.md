# 0002 — Multiplayer: un livello di sessione attorno al motore

- Stato: accettata (backend implementato, frontend da fare)
- Data: 2026-10-24
- Guida: [`../GPT_MULTIPLAYER.md`](../GPT_MULTIPLAYER.md) (fonte di verità per architettura e ordine di
  implementazione). Panoramica di partenza: [`../MULTIPLAYER_OVERVIEW.md`](../MULTIPLAYER_OVERVIEW.md).
  Riferimento API: [`../../api/multiplayer.md`](../../api/multiplayer.md).

## Contesto

CLAUDE.md §1 prevedeva, per la prima versione, "partita locale, senza multiplayer di rete". Il game designer ha chiesto
(2026-10-24) una versione multiplayer con le stesse regole della modalità Easy Price: nessuna regola nuova, 4 posti fissi,
da 2 a 4 umani con i bot sui posti vuoti, stanze private, solo nickname, polling, tempo reale.

## Decisione

Il multiplayer è un livello di sessione, autorizzazione, concorrenza e trasporto attorno al motore, che non cambia:

- `rules/setup.py` accetta posti espliciti (`SeatConfig`); `human_seat` resta come scorciatoia per il solo.
- `application/multiplayer/` (senza FastAPI): `GameSession`, `Seat`, `GameRegistry` (stanze, partite, indice dei token),
  `MultiplayerService` (casi d'uso), `event_filter` (cosa vede ciascun giocatore).
- `adapters/http/multiplayer.py` (route sottili) e `adapters/http/serialization.py` (conversioni condivise con il solo).
- Identità solo dal token di posto (`Authorization: Bearer`), conservato come hash SHA-256. Il `player_id` del client non
  conta.
- Un lock per partita attorno a "leggi, autorizza, controlla la revisione, applica, fai muovere i bot, salva gli eventi".
  I lettori (vista, eventi, anteprime) non aspettano i bot: leggono una coppia (stato, log) pubblicata insieme.
- I bot li fa muovere il server subito dopo ogni comando accettato, un segmento per volta; ogni segmento è un blocco di
  eventi del log. Il polling non muove mai il gioco.
- Log di eventi per partita, interrogabile da una revisione; ogni evento passa dal filtro per destinatario. Una classificazione
  obbligatoria di ogni tipo di evento (test) impedisce di aggiungerne uno che perde informazioni.
- Stato in RAM in un solo processo (nessuna persistenza ancora).

## Scostamenti dalla guida (e perché)

1. **Percorsi delle route di gioco:** `/api/v1/mp/games/{game_id}/...` e non `/api/v1/games/{game_id}/...`. Così le route
   del solo restano intatte e non possono raggiungere una partita multiplayer (lo stato vive solo nel registro
   multiplayer): verificato da test. Le stanze sono `/api/v1/rooms/...` come previsto.
2. **`POST .../commands` non è esposto** per il multiplayer (la guida lo elenca tra quelle da proteggere): il client risponde
   alle decisioni con `.../decisions/answer`, che costruisce il comando dal solo elenco di `option_id`.
3. **Il seed lo sceglie il server.** La richiesta di creazione stanza non lo accetta: chi lo scegliesse potrebbe calcolare
   ogni mano. Solo i test lo fissano, dal servizio.
4. **Vista senza Job futuri per tutti, compreso chi guarda** (`tier_piles` vuoto): l'ordine dei Job non rivelati è
   informazione nascosta. Il solo non cambia.
5. **Scarti nascosti:** gli altri vedono quante carte si scartano, non quali (cautela: il regolamento non lo dice).
   Carte pescate (anche come premio Job) nascoste agli altri. Carta rubata in una Rissa nota solo a vincitore e sconfitto.
   Il `seed` dell'evento `GameStarted` è azzerato. Carte giocate scoperte (Marketing, Boost, Gamble, rivelazioni di Poker e
   Rissa) restano pubbliche.
6. **Chi lascia una partita in corso lascia il posto a un bot** (la guida non lo definisce): evita che la partita si fermi.
   Non è il subentro automatico a tempo (rimandato). In lobby: il posto si libera; se esce l'host la stanza si chiude.
7. **Nome dei posti bot:** "Bot N" (il solo continua con "Player N"). Nickname unico dentro la stanza.
8. **Lock sincrono (`threading.Lock`)** e non asincrono: gli handler sono sincroni e girano nel pool di thread di FastAPI.
9. **Telemetria su database non registrata per le partite multiplayer** (`db.record_*`), da decidere con la classifica.
10. **Ogni blocco di eventi porta la plancia del giocatore subito dopo il passo** (`EventBatch.state_after`, vista calcolata al
    momento della richiesta con `view_for(..., hide_future_jobs=True)`). Nel solo il browser racconta i bot un'azione alla volta
    perché `advance(single_player_segment=True)` gli dà la plancia dopo ogni azione; con un solo flusso di eventi lo stesso
    racconto richiede la plancia di ogni passo, non solo l'ultima. Lo stato dopo il passo si tiene per gli ultimi 80 blocchi
    (`BATCH_STATE_WINDOW`, ~75 KB l'uno): un client che torna dopo molto salta al primo che ce l'ha. La risposta a `answer`
    ha sempre le plance dei blocchi che ha prodotto. La guida non lo prevedeva: senza, le azioni degli altri
    sarebbero comparse tutte insieme.

11. **Persistenza (fase 4):** snapshot per stanza in Postgres (`mp_sessions`, stesso `DOPE_DB_URL` della telemetria, spento se
    non impostato), uno dopo ogni operazione e quindi sempre a un confine di decisione umana, scritto da un thread con
    "l'ultimo vince" per stanza. Il ripristino è **pigro** (alla prima richiesta per codice o token), non all'avvio: su un
    host che fa partire il nuovo processo prima di spegnere il vecchio, caricare tutto all'avvio darebbe stanze in ritardo di
    quanto si è giocato nel frattempo. Per lo stesso motivo un database non leggibile risponde 503 `store_unavailable` e non
    "stanza inesistente", e uno snapshot vecchio non sovrascrive uno nuovo. Il log eventi non si salva: un client indietro
    riceve la vista di adesso. La pulizia delle stanze ferme è opportunistica (alla creazione di una stanza), senza thread.
    Timer e subentro del bot restano fuori (fase 5 della guida).

## Questioni di regola emerse

- **Poker (risolta il 2026-10-24):** il motore rivelava le carte una alla volta, in ordine di rotazione; con umani chi sceglieva
  dopo vedeva le carte di chi aveva scelto prima. Il game designer ha confermato la regola del regolamento: carta scelta in
  segreto, rivelazione simultanea. Ora ogni scelta viene registrata coperta (`PokerCardCommitted`) e le carte si scoprono
  tutte insieme quando l'ultimo ha scelto. Le puntate restano sequenziali e pubbliche, come da regolamento. Dettagli in
  `RULE_CHANGELOG.md`, 2026-10-24.

## Conseguenze

- Il frontend (fasi 2 e 3 della guida) c'è: lobby (`MultiplayerLobby`) e schermata di gioco nella stessa `App.tsx` del solo
  (stato `mp`: risposte e anteprime col token del posto, polling ogni secondo, `ingestBatches` + `TurnPlayback` per
  raccontare le mosse di bot e altri umani, banner "Tocca a …" quando non è il proprio turno, ripresa dopo un ricaricamento).
  Il backend si prova anche con client HTTP scriptati (`backend/tests/integration/fake_human.py`).
- La fase 4 della guida c'è (punto 11): ripristino dopo riavvio, pulizia delle stanze ferme, deploy che non perde le partite.
  Restano per la fase 5: timer e subentro del bot per chi sparisce (oggi un giocatore che chiude la scheda ferma il tavolo
  finché non esce esplicitamente), classifica multiplayer, più worker.
- Il ripristino non è provato su Supabase (nessun accesso da qui): è provato su un Postgres 16 locale. Al primo deploy con
  `DOPE_DB_URL` conviene guardare nei log del backend la riga `multiplayer persistence on (Postgres)`.
