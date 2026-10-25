# Registrazione delle partite nel database

Le partite si registrano in un database Postgres (Supabase) per confrontare i playtest tra versioni del codice e delle
regole. È solo analisi: non è mai la fonte di verità e nessuna regola ne dipende (l'unica lettura è la classifica, che è
decorativa). Vale `adapters/persistence/db.py`.

- **Acceso solo con `DOPE_DB_URL`** (stringa di connessione libpq). Senza, tutto è disattivato in silenzio: sviluppo locale e
  test non hanno bisogno di un database.
- **Un guasto non tocca mai il gioco.** Ogni scrittura è in un `try/except` che registra l'errore e va avanti; nel
  multiplayer le scritture partono da un thread a parte (`application/telemetry.py::BackgroundTelemetry`), quindi una richiesta
  non aspetta il database.

## Quali partite

| Partita | Registrata? |
|---|---|
| Solo, **Easy Price** (da 2026-10-25) | sì |
| Solo, Big (regole standard, non più offerta in interfaccia) | sì |
| Solo, Small | no |
| **Multiplayer** (qualunque stanza) | sì, `mode = 'multi'` (da 2026-10-25) |
| Tutorial | no |

Dopo un riavvio del server una partita multiplayer ripristinata continua a registrarsi nelle stesse righe.

## Tabelle

Le prime tre esistono da prima e le gestisce a mano il game designer in Supabase; il codice non le modifica.

- `games(id, game_version, rules_version, status, started_at, ended_at, winner_seat, total_turns)` — una riga per partita;
  `game_version` è l'hash git del codice che la gioca.
- `game_players(id, game_id, seat, player_type, character_id, bot_type, final_money, winner, ...punti per categoria,
  total_points)` — quattro righe per partita. `character_id` è il **nickname** di un umano (null per un bot); `bot_type` è la
  classe del bot (`HeuristicBot`, `RandomLegalBot`; prima del 2026-10-25 era sempre `RandomLegalBot`).
- `game_events(id, game_id, turn_number, seat, event_type, payload, created_at)` — un evento del motore per riga, per tutti i
  giocatori, con il contenuto completo in `payload` (JSON).

Due tabelle sono nuove (2026-10-25) e le crea il backend se mancano (`CREATE TABLE IF NOT EXISTS`, all'avvio): non si tocca
nessuna tabella esistente. Se il database non permette di crearle le partite si registrano come prima, senza queste due.

```sql
CREATE TABLE IF NOT EXISTS game_info (
    game_id      uuid PRIMARY KEY,
    ruleset      text NOT NULL,     -- 'easy_price', 'standard', 'simple'
    mode         text NOT NULL,     -- 'solo' | 'multi'
    bot_policy   text,              -- 'heuristic', 'random_legal'
    human_count  integer,
    room_code    text               -- solo multiplayer
);

CREATE TABLE IF NOT EXISTS game_job_completions (
    id                  bigserial PRIMARY KEY,
    game_id             uuid NOT NULL,
    seat                integer NOT NULL,
    player_type         text,        -- 'human' | 'bot'
    ordinal             integer NOT NULL,   -- 1 per il primo Job completato dal giocatore, 2 per il secondo...
    job_id              text NOT NULL,
    tier                integer,
    next_job_id         text,        -- il Job rivelato al suo posto (la "progressione" della pila)
    turn_number         integer,
    action_round_index  integer,
    phase               text,
    completed_at        timestamptz NOT NULL DEFAULT now(),
    bonus_column_index  integer,     -- la colonna scelta per la ricompensa...
    bonus_type          text,        -- ...e il bonus: skill, link, two_cards, money
    bonus_contact_id    text,
    bonus_skill_id      text,
    bonus_claimed_at    timestamptz
);
CREATE INDEX IF NOT EXISTS game_job_completions_game_seat_idx ON game_job_completions (game_id, seat);
```

`game_job_completions` ha una riga per ogni Job che un giocatore completa, **bot e umani**, nell'ordine in cui li completa: si
crea quando il Job è completato (`JobCompleted`) e si completa con la colonna scelta quando la ricompensa viene riscossa
(`JobBonusClaimed`). `player_type` è quello del posto *nello stato del gioco*: in multiplayer, mentre un bot gioca al posto di
un umano che non risponde, i suoi Job risultano `bot`.

## Cosa si vede negli eventi

Gli eventi si registrano **così come li produce il motore**, senza il filtro per destinatario del multiplayer: ci sono anche le
carte pescate e scartate. È un archivio privato del proprietario del database, mai esposto da nessuna rotta (la classifica
legge solo nickname e punti); non va incollato in log o in luoghi leggibili dai giocatori.

## Classifica

`GET /api/v1/leaderboard` mostra le partite **solo** (`mode = 'solo'`); una partita senza riga in `game_info` (tutte quelle
registrate prima del 2026-10-25) conta come solo. Le partite multiplayer si registrano ma non entrano in classifica: mescolarle
è una decisione di prodotto da prendere (guida multiplayer, sezione 48). Big ed Easy Price oggi stanno nella stessa lista.

## Interrogazioni utili

```sql
-- Quanti Job completano in media bot e umani, per modalità
SELECT i.mode, c.player_type, COUNT(*)::float / COUNT(DISTINCT c.game_id) AS jobs_per_game
FROM game_job_completions c JOIN game_info i ON i.game_id = c.game_id
GROUP BY i.mode, c.player_type;

-- A che turno, in media, un giocatore completa il suo n-esimo Job (solo Easy Price)
SELECT c.ordinal, AVG(c.turn_number) AS avg_turn, COUNT(*) AS n
FROM game_job_completions c JOIN game_info i ON i.game_id = c.game_id
WHERE i.ruleset = 'easy_price' GROUP BY c.ordinal ORDER BY c.ordinal;

-- Quali colonne di ricompensa si scelgono (bonus) per Job
SELECT c.job_id, c.bonus_type, COUNT(*) FROM game_job_completions c GROUP BY 1, 2 ORDER BY 1, 3 DESC;
```

## Come provarlo in locale

`DOPE_TEST_DB_URL=postgresql://... pytest -k telemetry` (vuota le tabelle di quel database: va usato un database a perdere, per
esempio `docker run -d -e POSTGRES_PASSWORD=test -p 54329:5432 postgres:16-alpine`).
