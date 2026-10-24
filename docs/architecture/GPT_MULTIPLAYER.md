# GPT_MULTIPLAYER.md

## DOPE — Multiplayer implementation bible

**Status:** implementation guide  
**Scope:** first production-capable multiplayer foundation for DOPE  
**Primary ruleset:** `easy_price`  
**Audience:** Claude Code / coding agents working on the `godope_4` repository  
**Priority:** correctness, security of hidden information, determinism, minimal impact on the existing game engine

---

# 1. Purpose

This document defines how multiplayer must be implemented in DOPE.

Treat this file as the **source of truth for multiplayer architecture and implementation order** unless a later explicit project decision overrides it.

The multiplayer work must **not redesign the game rules**.

The existing game engine is already conceptually suitable for multiplayer because:

- the server is authoritative;
- game state is serializable;
- commands are validated server-side;
- commands include `expected_revision`;
- the engine exposes a filtered view per player;
- there is only one pending decision at a time;
- every pending decision has a specific `player_id`;
- bots use the same legal-action system as humans;
- the game is deterministic when seed and command sequence are fixed.

The multiplayer layer must therefore be implemented mainly as a **session, authorization, concurrency, transport and persistence layer around the existing engine**.

Do not rewrite working game rules merely to make multiplayer easier.

---

# 2. Product target for the first multiplayer version

The first multiplayer version is intentionally small.

It must support:

- real-time games only;
- exactly 4 seats, as required by DOPE rules;
- 2, 3 or 4 human players;
- bots automatically filling unused seats;
- private rooms;
- room code and/or shareable room URL;
- nickname only;
- no account required;
- one secret seat token per human player;
- polling for updates;
- automatic server-side bot progression;
- reconnect using the same seat token;
- player-specific views;
- player-specific filtered events;
- a complete game from lobby to final score.

The first version does **not** need:

- public matchmaking;
- asynchronous play;
- WebSockets;
- SSE;
- public spectators;
- chat;
- emoji;
- user accounts;
- Google login;
- persistent player profiles;
- global multiplayer ranking;
- public replay sharing;
- multiple backend workers;
- Redis;
- distributed game actors;
- advanced moderation;
- automatic bot takeover after timeout;
- sophisticated presence tracking.

These may be added later.

---

# 3. Non-negotiable architectural principles

## 3.1 Server authority

The backend is authoritative.

The client may:

- display state;
- request legal plans/previews;
- submit choices;
- animate events.

The client must never decide:

- whether a move is legal;
- whose turn it is;
- what hidden information another player may see;
- when bots should move;
- what the next authoritative game state is.

---

## 3.2 Do not trust `player_id` from the client

In multiplayer, identity must come from the authenticated seat token.

Bad:

```text
POST /games/{game_id}/commands
{
  "player_id": "player_2",
  ...
}
```

Trusted identity must instead be resolved server-side:

```text
Authorization: Bearer <seat_token>
```

Conceptually:

```python
seat = session.resolve_token(token)
player_id = seat.player_id
```

If a request body still contains `player_id` for compatibility, the server must ignore it or verify that it matches the token-derived player.

The client must never be able to impersonate another seat by changing an ID in JSON or a query string.

---

## 3.3 Hidden information is a security boundary

DOPE contains hidden information.

At minimum:

- cards in each player's hand;
- identity of cards drawn by another player;
- covered Fight/Rissa choices before reveal;
- other hidden or future information exposed by internal state;
- any deck ordering or RNG state that could reveal future cards.

Therefore:

- never expose the raw `GameState` to a normal multiplayer client;
- never expose unrestricted `/save`;
- never expose unrestricted `/replay`;
- never expose unrestricted `/load`;
- never expose another player's view;
- never return raw domain events without filtering.

Player-facing data must always go through:

1. a player-specific view builder;
2. an event-filtering layer.

Security tests are mandatory.

---

## 3.4 One authoritative mutation at a time per game

Each game must have its own lock.

The critical section must cover the complete authoritative mutation sequence:

```text
read current session/state
    ↓
authorize actor
    ↓
validate expected revision
    ↓
apply human command
    ↓
store resulting events
    ↓
advance automatic phases
    ↓
advance bots until the next human decision
    ↓
store all generated events
    ↓
update state/session revision
    ↓
release lock
```

Do not lock globally across all games.

Different games should be able to progress independently.

---

## 3.5 Preserve determinism

The multiplayer layer must not introduce random decisions outside the existing deterministic game logic.

A given:

```text
initial seed
+
same ordered sequence of accepted human commands
+
same bot policy
```

must produce the same authoritative result.

Do not use client timestamps, network timing or arrival order as game mechanics.

---

## 3.6 Rules remain independent from HTTP

Keep the current layered architecture.

The domain/rules layer must not depend on:

- FastAPI;
- room codes;
- HTTP headers;
- tokens;
- database sessions;
- browser concepts;
- sockets;
- polling.

Multiplayer infrastructure belongs above the domain engine.

---

# 4. Existing project structure to preserve

Relevant areas of the repository:

```text
backend/src/dope_engine/domain/
    state
    commands
    events
    decisions

backend/src/dope_engine/rules/
    game rules

backend/src/dope_engine/application/
    game_service.py
    legal_actions.py
    views.py
    command_bus.py
    save_load.py
    replay.py
    human_planning.py

backend/src/dope_engine/bots/
    random_legal.py
    policies.py
    scoring.py

backend/src/dope_engine/adapters/http/
    app.py
    schemas.py

backend/src/dope_engine/adapters/persistence/
    db.py

frontend/src/
    App.tsx
    api.ts
    components/BoardView.tsx
    TurnPlayback.tsx
    useHumanActionPlan.ts
    outcome-queue.ts
    log-narration.ts
```

The multiplayer implementation should reduce responsibilities currently concentrated in `adapters/http/app.py`, not add even more unrelated state to it.

---

# 5. Core multiplayer model

Introduce a game/session registry abstraction.

Do not continue growing unrelated dictionaries such as:

```python
_games
_undo_snapshots
_command_history
_bot_policy_by_game
```

inside the HTTP adapter.

The exact class names are flexible, but the architecture should converge on something like:

```python
@dataclass
class Seat:
    player_id: str
    seat_index: int
    controller_type: Literal["HUMAN", "BOT"]
    nickname: str
    token_hash: str | None
    connected: bool = False
```

and:

```python
@dataclass
class GameSession:
    game_id: str
    room_code: str
    status: Literal["LOBBY", "RUNNING", "FINISHED"]
    state: GameState | None
    seats: list[Seat]
    bot_policy: str
    ruleset: str
    event_log: list[EventBatch]
    lock: ...
```

Possible additional fields:

```text
created_at
started_at
finished_at
last_activity_at
host_seat_index
revision
```

Do not over-model presence or matchmaking in phase 1.

---

# 6. Seat model

DOPE always has 4 gameplay seats.

The game engine must support a configuration equivalent to:

```python
players = [
    PlayerConfig(kind="human", name="Marco"),
    PlayerConfig(kind="human", name="Luca"),
    PlayerConfig(kind="bot", name="Player 3"),
    PlayerConfig(kind="bot", name="Player 4"),
]
```

Replace the assumption:

```python
create_initial_state(human_seat=...)
```

with an API capable of defining every seat.

The old single-player creation flow may remain as a compatibility wrapper:

```python
create_single_player_game(human_seat=0, ...)
```

which internally builds:

```text
1 HUMAN
3 BOT
```

Do not maintain two separate game engines.

---

# 7. Room lifecycle

Minimum room lifecycle:

```text
LOBBY
  ↓
RUNNING
  ↓
FINISHED
```

A room must not mutate gameplay state while in `LOBBY`.

A room becomes `RUNNING` when the start condition is met.

For the first implementation:

- host creates the room;
- host chooses desired number of human seats: 2, 3 or 4;
- unused seats are bots;
- human players join with nickname;
- the host starts when required human seats are occupied.

A later "ready" system is optional.

Do not make `ready` mandatory if it creates unnecessary frontend work for the first version.

---

# 8. Room codes

Room codes should be:

- short;
- human-readable;
- case-insensitive;
- hard enough to guess casually;
- unique among active rooms.

Example:

```text
F7KQ
```

The room code is **not** an authentication secret.

Knowing a room code may allow a user to request joining the room.

It must never allow access to an already occupied player's seat.

---

# 9. Seat tokens

Every human seat receives a cryptographically random secret token at join/create time.

Example conceptual response:

```json
{
  "room_code": "F7KQ",
  "game_id": "8bd...",
  "player_id": "player_1",
  "seat_index": 1,
  "seat_token": "..."
}
```

Requirements:

- generate using a cryptographically secure random generator;
- token must not encode predictable seat information;
- do not log the raw token;
- preferably store a hash server-side;
- browser stores the raw token locally;
- token identifies exactly one seat in exactly one room/game;
- tokens must not be accepted across games.

A reconnect uses the same token.

---

# 10. Authorization contract

All private multiplayer endpoints must identify the player using the seat token.

Preferred transport:

```http
Authorization: Bearer <seat_token>
```

At minimum protect:

```text
GET  /games/{id}/view
GET  /games/{id}/events
POST /games/{id}/decisions/plan
POST /games/{id}/decisions/answer
POST /games/{id}/commands
POST /games/{id}/leave
```

Do not accept:

```text
?player_id=player_2
```

as sufficient authorization.

Public lobby metadata may use separate endpoints that expose only safe information.

---

# 11. Game registry

Introduce a dedicated registry/service.

Conceptual interface:

```python
class GameRegistry:
    def create_room(...)
    def get_room(...)
    def join_room(...)
    def start_room(...)
    def resolve_token(...)
    def get_session(...)
    def append_events(...)
    def get_events_since(...)
```

Do not let FastAPI route functions directly manipulate internal dictionaries throughout `app.py`.

FastAPI handlers should remain thin.

Example:

```python
@app.post(...)
def answer_decision(...):
    auth = auth_service.resolve(...)
    return multiplayer_service.answer(...)
```

not:

```python
@app.post(...)
def answer_decision(...):
    # 100 lines of state lookup, authorization,
    # locking, command execution, bot advancement,
    # event filtering and serialization
```

---

# 12. Server-driven bot progression

This is one of the most important changes.

Current single-player behavior must not survive conceptually in multiplayer:

```text
browser notices it is not my turn
→ browser calls /advance
→ server moves bot
```

In multiplayer the server owns bot progression.

After each accepted human action:

```text
human command
→ apply
→ collect events
→ process automatic game phases
→ if next required actor is BOT:
      execute one bot segment
      collect events
      repeat
→ stop when:
      a HUMAN decision is pending
      or game is finished
```

No browser is responsible for making the game continue.

There should be no race where two human browsers both call `/advance`.

---

# 13. Human turn boundary

The server should stop automatic progression when it reaches a state requiring input from a HUMAN seat.

This includes any human pending decision, even if it is not the nominal active turn player.

Examples:

- Rissa/Fight choice;
- Poker choice;
- Job reward choice;
- first-player choice;
- any interrupt or reaction represented by `pending_decision`.

The correct stopping condition is therefore based on the authoritative pending decision/controller, not merely `current_player_id`.

---

# 14. Event log

Every accepted authoritative mutation must append an immutable event batch.

Conceptual structure:

```python
@dataclass
class EventBatch:
    revision_from: int
    revision_to: int
    actor_player_id: str | None
    segment_type: str
    events: list[DomainEvent]
```

The exact schema may differ.

Important properties:

- strictly ordered;
- append-only during the game;
- queryable incrementally;
- sufficient for clients to know what happened after a known revision;
- does not require clients to infer gameplay transitions.

Do not rely solely on HTTP responses to the player who made the move.

Other players must be able to fetch the same public consequences later.

---

# 15. Event filtering

Never send raw domain events directly to multiplayer clients.

Introduce a function or service conceptually equivalent to:

```python
filter_event_for_player(event, viewer_player_id, state_context)
```

or:

```python
build_player_event_batch(batch, viewer_player_id)
```

The filtering layer must protect hidden information.

At minimum review events related to:

```text
CardDrawn
CardPlayed
Fight/Rissa hidden declarations
Poker hidden declarations
deck operations
future Job information
random state
private rewards
private player hand mutations
```

Important distinction:

- some events are public;
- some are public with redacted fields;
- some are visible only to one player;
- some become public only later.

The filtering model should support all four cases.

---

# 16. Required hidden-information test

Add an explicit automated security test.

The test should:

1. create a multiplayer game with at least 2 human seats;
2. cause player A to draw or hold a known card;
3. retrieve:
   - player A view/events;
   - player B view/events;
4. assert:
   - A can see information A is allowed to know;
   - B cannot see A's private card identity;
   - B may still see public consequences such as "A drew a card";
5. scan serialized responses for forbidden identifiers where practical.

This is a release blocker.

---

# 17. Player view

The existing player-specific view builder should remain the basis of multiplayer state delivery.

The endpoint:

```text
GET /games/{id}/view
```

must derive the viewing player from the seat token.

The client must not be allowed to request another player's view.

The returned view should include enough public room/game metadata to render:

```text
my player ID
my seat
player nicknames
controller types
whose input is awaited
current revision
game state visible to me
```

Do not expose raw room secrets.

---

# 18. Polling transport for v1

Use polling first.

Do not introduce SSE or WebSockets in the first implementation.

Recommended client request:

```http
GET /games/{id}/events?since=<revision>
Authorization: Bearer <seat_token>
```

Suggested interval:

```text
750–1000 ms
```

The exact interval is a product tuning parameter, not a game rule.

Possible response:

```json
{
  "game_id": "...",
  "from_revision": 138,
  "current_revision": 140,
  "events": [...],
  "requires_refresh": false
}
```

The client may fetch `/view` after receiving new events or the events endpoint may include the latest player view.

Prefer correctness and simple recovery over minimizing a few small HTTP requests.

---

# 19. Polling semantics

The client tracks:

```text
last_seen_revision
```

On poll:

```text
GET events?since=last_seen_revision
```

Server returns all visible event batches after that revision.

Requirements:

- duplicate polling is harmless;
- asking twice from the same revision returns the same logical data;
- old/duplicate client requests must not mutate game state;
- polling must never advance bots;
- polling must never apply automatic phases.

Only accepted commands mutate gameplay state.

---

# 20. Revision semantics

Continue using `expected_revision`.

Every gameplay mutation submitted by a client must include the revision the client believes it is acting on.

If stale:

```http
409 Conflict
```

or equivalent typed error.

The response should tell the client enough to recover, for example:

```json
{
  "error": "stale_revision",
  "expected": 142,
  "received": 140
}
```

The client must refresh its view/events.

Never silently accept a decision built against an obsolete state.

---

# 21. Per-game lock

Each active game gets one lock.

Conceptually:

```python
async with session.lock:
    ...
```

or equivalent correct synchronization for the current FastAPI execution model.

The lock must protect:

- state mutation;
- revision checks;
- bot progression;
- event-log append;
- snapshot mutation if enabled.

Do not assume CPython dictionary assignment is sufficient concurrency control.

---

# 22. Locking tests

Create tests with intentionally simultaneous requests.

Examples:

```text
two commands sent with the same expected_revision
```

Expected:

```text
exactly one may succeed
the other is rejected as stale/invalid
state remains valid
no event is duplicated
revision sequence remains monotonic
```

Also test concurrent polling while a move is being processed.

---

# 23. Undo

For the first multiplayer version:

**disable Undo in multiplayer.**

Keep existing Undo behavior for solo play if desired.

Reason:

- multiplayer creates ambiguity after another player has observed a move;
- hidden information may have been revealed;
- event history may already have been consumed by other clients;
- undo semantics become much more complicated than the value it adds.

Do not spend phase-1 implementation time solving multiplayer Undo.

Planning/previews remain allowed because they do not mutate authoritative state.

---

# 24. Planning endpoint

`/decisions/plan` may remain available.

Requirements:

- authorized using the seat token;
- plan only for the requesting player's legal decision;
- operates on copies;
- must not mutate state;
- must not consume RNG;
- must not append events;
- must not advance bots;
- must not change revision.

Add tests for all of these invariants.

---

# 25. Existing save/load/replay endpoints

Normal multiplayer clients must not have unrestricted access to:

```text
/save
/load
/replay
```

because these may reveal:

- hands;
- deck order;
- random generator state;
- hidden choices;
- future content.

For multiplayer v1 either:

### Option A — simplest

Disable them for multiplayer games.

### Option B

Protect them behind an internal/admin mechanism not available in the public client.

Do not design public replay sharing in phase 1.

---

# 26. Future Job information

Review:

```text
job_progress_by_player.tier_piles
```

or any equivalent state currently exposing future Job ordering.

Against bots, such leakage may have been tolerated.

Against humans, default to:

**future Job order of other players is hidden unless game rules explicitly say otherwise.**

Do not preserve an implementation leak merely because the old solo UI could access it.

Add a targeted test.

---

# 27. Bot visibility

Bots should be explicitly marked as bots in lobby and game UI.

Example:

```text
Marco
Luca
BOT
BOT
```

Do not pretend a bot seat is a human nickname.

This is useful for product clarity and debugging.

---

# 28. Lobby API target

Exact names may evolve, but aim for an interface equivalent to:

```text
POST /api/v1/rooms
POST /api/v1/rooms/{code}/join
GET  /api/v1/rooms/{code}
POST /api/v1/rooms/{code}/start
POST /api/v1/rooms/{code}/leave
```

### Create room

Input conceptually:

```json
{
  "ruleset": "easy_price",
  "human_seats": 2,
  "bot_policy": "heuristic",
  "nickname": "Marco"
}
```

Output conceptually:

```json
{
  "room_code": "F7KQ",
  "game_id": null,
  "seat_index": 0,
  "player_id": "player_0",
  "seat_token": "..."
}
```

### Join room

Input:

```json
{
  "nickname": "Luca"
}
```

Output:

```json
{
  "room_code": "F7KQ",
  "seat_index": 1,
  "player_id": "player_1",
  "seat_token": "..."
}
```

### Start

Starting should:

1. verify caller permissions;
2. verify required human seats are occupied;
3. create bot seats for remaining positions;
4. create `GameState`;
5. assign names/controller types;
6. transition room to `RUNNING`;
7. run initial automatic progression if required;
8. stop on first human decision.

---

# 29. Solo compatibility

Do not break current solo play while building multiplayer.

Preferred approach:

- keep current solo UI initially;
- internally reuse the same improved session infrastructure where practical;
- if migration is risky, keep the old route temporarily and add multiplayer beside it;
- remove duplication after parity tests exist.

Do not force a giant all-at-once frontend rewrite.

---

# 30. Backend-only milestone

Before meaningful React multiplayer work, the backend must support a complete game driven by synthetic clients.

This is the first mandatory milestone.

Target matrix:

```text
2 HUMAN + 2 BOT
3 HUMAN + 1 BOT
4 HUMAN + 0 BOT
```

All three configurations must complete full games.

---

# 31. Fake-human integration simulator

Create an integration test or command-line simulator where bots behave as **external human clients**, not internal bot controllers.

Important distinction:

```text
internal BOT
```

uses existing server bot machinery.

```text
fake HUMAN
```

uses HTTP endpoints exactly like a browser would.

A fake-human loop may conceptually do:

```python
while not game_over:
    view = client.get_view()

    if view.pending_decision_for_me:
        choice = choose_random_legal_option(view.pending_decision)
        client.answer(choice, expected_revision=view.revision)

    events = client.get_events_since(last_seen_revision)
```

Use legal random choices initially.

The purpose is protocol validation, not strategic strength.

---

# 32. Integration simulator requirements

The simulator should be able to run:

- one complete game;
- many games;
- different seeds;
- 2/3/4 human configurations;
- optional randomized polling delays;
- optional simultaneous request attempts;
- disconnect/reconnect simulation later.

After every accepted command, validate existing game invariants if available.

At game end validate:

- all clients agree game is finished;
- authoritative final state is valid;
- final revision is coherent;
- no player could access another player's private state.

---

# 33. Deterministic parity test

Where practical, create a parity test.

Run the same game logically through:

### Path A
existing direct simulation / application service

### Path B
multiplayer HTTP fake clients

Using:

```text
same seed
same bot policy
same human decisions
```

Final authoritative states should be equivalent.

This test is especially valuable because multiplayer should be a transport/session layer, not a rules fork.

---

# 34. Frontend multiplayer architecture

Only after backend-only multiplayer is reliable, update the frontend.

The frontend must stop assuming:

```text
there is exactly one human
my player is fixed from human_seat
if it is not my turn, I should call /advance
```

Instead the client has:

```text
room_code
game_id
my_player_id
my_seat_index
seat_token
last_seen_revision
```

The server tells the client whose input is needed.

---

# 35. Frontend startup flow

Target:

```text
DOPE

[ Play solo ]
[ Multiplayer ]
```

Multiplayer:

```text
[ Create room ]
[ Join room ]
```

Create room:

```text
Nickname
Human players: 2 / 3 / 4
Create
```

Lobby:

```text
ROOM F7KQ

1 Marco
2 Luca
3 BOT
4 BOT

[ Start ]
```

Join:

```text
Room code
Nickname
[ Join ]
```

Keep this UI minimal.

---

# 36. Frontend seat token storage

Persist the seat token locally so a page reload does not immediately lose the seat.

Use a storage strategy appropriate for the current frontend.

At minimum persist:

```text
room_code
game_id
seat_token
```

Do not persist another player's state.

Do not place the token in:

- URL query strings;
- logs;
- analytics;
- shareable room links.

---

# 37. Frontend game loop

New conceptual loop:

```text
load authenticated player view
↓
poll events since last_seen_revision
↓
animate received events
↓
update view
↓
if server says a decision belongs to me:
    enable interaction
else:
    show "waiting for <nickname>"
```

There is no client-side bot-advance loop.

---

# 38. Playback and animation

Reuse `TurnPlayback` and the existing event narration machinery where possible.

Events generated by:

- other humans;
- bots;
- automatic game phases;

should all use the same playback pipeline.

The frontend should not need to know whether an event came from a bot or human merely to animate it.

---

# 39. Blocking popups

Current popup confirmations must not block authoritative server progress.

Examples:

- Rissa result;
- Poker result;
- Retata result;
- "Turn N";
- other narrative confirmations.

In multiplayer:

```text
server progresses independently
```

and:

```text
OK only acknowledges local presentation
```

A slow player's popup must not freeze everyone else's game.

---

# 40. Event playback backlog

The client may receive multiple event batches while still animating older ones.

Therefore maintain a local presentation queue.

Do not assume:

```text
network event arrival == animation completion
```

The authoritative view may already be ahead of what the player is currently watching.

Separate:

```text
authoritative state synchronization
```

from:

```text
presentation playback
```

---

# 41. First multiplayer frontend acceptance test

Open four independent browser contexts.

Prefer:

```text
normal window
incognito window
other browser
browser profile
```

or automated contexts.

Verify:

- four different tokens;
- four different private hands;
- shared public board;
- correct turn ownership;
- decisions only enabled for the correct player;
- all players receive other players' visible actions;
- no one needs to manually refresh;
- game reaches final scoring.

---

# 42. Reconnect

A minimal reconnect is required before considering multiplayer usable.

For v1:

```text
page reload
→ read stored seat token
→ authenticate
→ fetch current view
→ fetch missed events if useful
→ resume
```

Do not require a full account system.

If the backend process itself restarts, recovery may initially fail until persistence is added.

That is acceptable only for the first development milestone, not as the final robust multiplayer deployment.

---

# 43. Persistence — phase after core multiplayer

Once multiplayer works in memory, add state snapshots.

Recommended target:

- snapshot authoritative state after every revision initially;
- optimize frequency later if needed;
- persist enough session metadata to restore active rooms.

Persist at minimum:

```text
game_id
room_code
status
revision
ruleset
bot_policy
serialized GameState
seat metadata
timestamps
```

Do not persist raw seat tokens if avoidable; persist hashes.

---

# 44. Restart recovery

After persistence exists:

```text
backend restart
↓
load unfinished sessions
↓
recreate locks
↓
restore GameState
↓
restore seats
↓
restore bot policy
↓
clients reconnect with their existing token
```

Acceptance test:

```text
start a multiplayer game
play several actions
restart backend
reconnect clients
finish the same game
```

---

# 45. Hosting constraint

The initial architecture may assume:

```text
one backend service
one backend process
games in RAM
```

provided that:

- this limitation is explicit;
- per-game locks are correct;
- snapshots are added before relying on it operationally;
- deployment does not accidentally start multiple independent workers sharing no state.

Do not scale to multiple workers until state ownership is redesigned.

If multiple workers are later required, introduce a proper shared coordination model rather than hoping RAM state will work.

---

# 46. Deployment safety

Automatic deployment during live games can destroy in-memory sessions.

Before multiplayer is considered production-ready, choose at least one:

- restore active games from snapshots;
- controlled deployment windows;
- graceful drain;
- another explicit operational strategy.

Do not ignore deployment behavior.

---

# 47. Timeouts and bot takeover

Not part of initial implementation.

Design the architecture so it can be added later.

Future possible behavior:

```text
human inactive for N seconds
→ server marks seat temporarily BOT-controlled
→ bot acts
→ returning human may reclaim seat
```

Do not implement this until basic multiplayer and reconnect are stable.

---

# 48. Multiplayer ranking

Do not build ranking into phase 1.

Later rankings may need dimensions such as:

```text
ruleset
human player count
possibly bot policy
```

Do not mix multiplayer results into the existing ranking without an explicit product decision.

---

# 49. Security checklist

Before first external test, verify all of the following.

- [ ] A player cannot request another player's view.
- [ ] A player cannot submit a command for another player.
- [ ] Changing `player_id` in JSON does not grant authority.
- [ ] Seat tokens are unpredictable.
- [ ] Raw tokens are not logged.
- [ ] `/save` cannot leak full state.
- [ ] `/replay` cannot leak hidden state.
- [ ] `/load` cannot replace an active multiplayer state.
- [ ] Event streams are filtered per viewer.
- [ ] Other players' card IDs are hidden where required.
- [ ] Covered Rissa/Fight choices remain hidden until reveal.
- [ ] Future hidden Jobs are not leaked.
- [ ] RNG/deck order is not exposed.
- [ ] Stale revisions are rejected.
- [ ] Concurrent commands cannot overwrite each other.
- [ ] Room code alone does not grant seat ownership.

---

# 50. Game correctness checklist

- [ ] 4 gameplay seats always exist.
- [ ] 2 humans + 2 bots works.
- [ ] 3 humans + 1 bot works.
- [ ] 4 humans works.
- [ ] Human pending decisions stop server automation.
- [ ] Bot pending decisions are resolved server-side.
- [ ] Automatic phases continue correctly.
- [ ] Rissa works across multiple humans.
- [ ] Poker works across multiple humans.
- [ ] Job reward choices can interrupt another player's turn correctly.
- [ ] first-player selection works with any human seat.
- [ ] Retate resolve correctly.
- [ ] final scoring works.
- [ ] same seed + same accepted command sequence remains deterministic.

---

# 51. API correctness checklist

- [ ] Create room.
- [ ] Join room.
- [ ] Start room.
- [ ] Reject join when human seats are full.
- [ ] Reject start too early.
- [ ] Return safe lobby metadata.
- [ ] Authenticated view.
- [ ] Authenticated planning.
- [ ] Authenticated decision answer.
- [ ] Poll events since revision.
- [ ] Reject stale commands.
- [ ] Reject wrong actor.
- [ ] Reject invalid token.
- [ ] Reject token from another game.
- [ ] Safe handling of repeated requests.

---

# 52. Frontend correctness checklist

- [ ] User can choose solo or multiplayer.
- [ ] User can create a room.
- [ ] User can join by room code.
- [ ] Nicknames appear in lobby.
- [ ] Bots are visibly identified.
- [ ] Shareable room code/link is easy to copy.
- [ ] Seat token survives reload.
- [ ] Current actor is shown.
- [ ] Controls activate only when appropriate.
- [ ] Other players' events animate.
- [ ] Bot events animate.
- [ ] Blocking OK popups are local only.
- [ ] Reload restores the player's seat.
- [ ] Game can finish without manual refresh.

---

# 53. Implementation order

Follow this order unless a concrete technical dependency requires a small deviation.

## Phase 1A — engine seat generalization

1. Find all assumptions around:
   - `human_seat`
   - `HUMAN`
   - `player_0`
   - single-human initialization
2. Allow all four seats to define controller type and name.
3. Preserve current solo behavior through compatibility tests.
4. Add unit tests.

Do not touch frontend yet.

---

## Phase 1B — GameSession and registry

1. Introduce `GameSession`.
2. Introduce seat representation.
3. Introduce registry/service.
4. Move game runtime state out of scattered HTTP globals where practical.
5. Add per-game lock.
6. Keep current solo endpoints working.

---

## Phase 1C — authorization

1. Generate seat tokens.
2. Resolve token → seat → player.
3. Protect multiplayer routes.
4. Remove trust in client-provided `player_id`.
5. Add authorization tests.

---

## Phase 1D — server-driven bots

1. Extract a server-side "advance until human input" orchestration function.
2. Call it after room start.
3. Call it after every accepted human decision.
4. Stop only when human input is required or game ends.
5. Add integration tests.

---

## Phase 1E — event log and filtering

1. Append ordered event batches.
2. Implement `since=revision`.
3. Add player-specific filtering.
4. Add hidden-information tests.
5. Ensure polling never mutates state.

---

## Phase 1F — fake-human HTTP simulator

1. Implement external HTTP clients.
2. Run 2H+2B.
3. Run 3H+1B.
4. Run 4H.
5. Run many seeded games.
6. Introduce randomized delays.
7. Introduce concurrency tests.

**Do not start major frontend multiplayer work until this phase is green.**

---

## Phase 2 — lobby frontend

1. Multiplayer entry screen.
2. Create room.
3. Join room.
4. Lobby seat display.
5. Start game.
6. Local token storage.

---

## Phase 3 — multiplayer game frontend

1. Remove single-human assumptions.
2. Remove client-driven `/advance`.
3. Add polling.
4. Consume player view.
5. Consume all visible events.
6. Reuse playback system.
7. Convert blocking confirmations to local-only.
8. Show waiting/current-player state.

---

## Phase 4 — reconnect and robustness

1. Reload reconnect.
2. Persist active game snapshots.
3. Backend restart recovery.
4. inactive-room cleanup.
5. explicit leave.
6. deployment safety.

---

## Phase 5 — optional product features

Only after the above is stable:

```text
timers
bot takeover
public queue
accounts
rankings
spectators
public replay
chat
async games
SSE/WebSockets
multi-worker scaling
Redis
```

---

# 54. Things Claude Code must NOT do

Do not:

- rewrite the rules engine;
- create a separate multiplayer rules implementation;
- move rule logic into React;
- trust `player_id` supplied by the client;
- send raw `GameState` to browsers;
- send raw unfiltered events;
- expose another player's view;
- make polling advance the game;
- keep bot advancement browser-driven;
- solve concurrency with `expected_revision` alone;
- use one global lock for all games;
- introduce Redis in phase 1;
- introduce WebSockets in phase 1;
- introduce SSE in phase 1;
- build accounts before nickname/token rooms work;
- build matchmaking before private rooms work;
- build rankings before complete multiplayer games work;
- build chat before complete multiplayer games work;
- build spectator mode before information filtering is proven;
- preserve Undo in multiplayer just because solo has it;
- redesign game mechanics to simplify networking;
- silently break solo mode;
- depend on multiple backend workers with RAM-only state;
- leak card IDs in logs or telemetry.

---

# 55. Refactoring policy

Prefer small, testable refactors.

If an existing function mixes:

```text
HTTP parsing
game lookup
authorization
state mutation
bot advancement
serialization
```

split responsibilities incrementally.

Do not perform cosmetic broad rewrites while implementing multiplayer.

Avoid unrelated renames and formatting churn.

Every structural change should have a multiplayer reason or a clear testability benefit.

---

# 56. Compatibility policy

Existing tests are valuable.

Current backend has a large test suite and simulation tooling.

Run relevant existing tests after each structural step.

A multiplayer refactor is not successful if it makes current game behavior subtly diverge.

Treat existing deterministic/replay tests as regression protection.

---

# 57. Error model

Prefer explicit typed errors.

Examples:

```text
room_not_found
room_full
room_already_started
room_not_ready
invalid_token
seat_not_found
not_your_turn
stale_revision
invalid_decision
game_finished
game_not_started
```

Do not expose internal stack traces to clients.

Frontend should be able to distinguish:

```text
temporary sync issue
```

from:

```text
illegal user action
```

---

# 58. Observability

Add useful server logs without leaking secrets.

Useful:

```text
game_id
room_code
revision
seat_index
player_id
controller_type
command type
event count
game status
```

Never log:

```text
raw seat token
full private hand
deck order
RNG state
other hidden state
```

---

# 59. Data model naming

Prefer terms consistently:

```text
room        = pre-game/lobby session and its lifecycle
game        = active authoritative match
seat        = one of four positions
player_id   = engine identity such as player_0
nickname    = display name
seat_token  = secret authorization credential
controller  = HUMAN or BOT
revision    = authoritative state version
event batch = events generated by one authoritative segment
```

Do not use "player" ambiguously for account, seat, nickname and engine ID in the same module.

---

# 60. Definition of done — backend multiplayer core

Backend core is done only when:

1. A room can be created.
2. 2–4 humans can occupy seats.
3. Remaining seats become bots.
4. Every human receives a unique secret token.
5. Game starts from the room configuration.
6. Human commands are authorized by token.
7. Client-supplied `player_id` cannot impersonate another seat.
8. Commands are protected by per-game locking.
9. Stale revisions are rejected.
10. Bots advance automatically server-side.
11. Server stops at the next human decision.
12. Events are logged.
13. Events can be requested incrementally.
14. Events are filtered per viewer.
15. Views are filtered per viewer.
16. Hidden-card leakage tests pass.
17. 2H+2B full HTTP simulation passes.
18. 3H+1B full HTTP simulation passes.
19. 4H full HTTP simulation passes.
20. Existing solo tests remain green.

---

# 61. Definition of done — first playable multiplayer

First playable multiplayer is done only when four separate browser contexts can:

1. create/join the same room;
2. see the same public lobby;
3. start the game;
4. see their own private hand and not others';
5. see correct player nicknames/colors;
6. act only when allowed;
7. receive other players' actions automatically;
8. receive bot actions automatically;
9. play through Rissa;
10. play through Poker;
11. resolve Job decisions;
12. progress through all turns and rounds;
13. finish the game;
14. see final scoring;
15. reload the page and recover the same seat during the game.

No public matchmaking or accounts are required for this milestone.

---

# 62. First coding task

The first concrete coding task should be:

> Generalize game initialization from one `human_seat` to four explicit seat/controller configurations, while preserving the existing solo creation behavior through a compatibility wrapper and tests.

Then proceed immediately to:

> Introduce `GameSession`/registry and per-game locking.

Do not begin with React.

Do not begin with WebSockets.

Do not begin with database persistence.

---

# 63. Expected agent workflow

For each implementation step:

1. inspect the relevant existing code first;
2. identify current invariants and tests;
3. make the smallest coherent change;
4. add or update tests;
5. run targeted tests;
6. run broader regression tests where practical;
7. summarize:
   - files changed;
   - architectural change;
   - tests added;
   - tests run;
   - known remaining limitations;
8. only then proceed to the next phase.

Do not batch all multiplayer work into one giant patch.

---

# 64. Decision rule when this document and code differ

If the current code contradicts an assumption in this document:

1. do not force the document's assumption blindly;
2. inspect the real code path;
3. preserve the architectural principles in this file;
4. adapt the implementation;
5. document the discrepancy.

The critical principles are:

```text
server authority
seat-token authorization
hidden-information isolation
per-game serialization
server-driven bots
incremental event delivery
determinism
no multiplayer rules fork
```

Implementation details may change.

---

# 65. Final priority order

When trade-offs arise, optimize in this order:

1. game-state correctness;
2. hidden-information security;
3. deterministic behavior;
4. concurrency safety;
5. recoverability;
6. simplicity;
7. frontend smoothness;
8. latency;
9. scalability.

For the first version, a simple architecture that safely supports a few simultaneous games is better than a sophisticated distributed architecture that is harder to verify.

---

# 66. Short version

If only ten rules are remembered, remember these:

1. **Do not rewrite the game rules.**
2. **The server owns the authoritative state.**
3. **A seat token, not `player_id`, determines who the player is.**
4. **Never expose raw state or unfiltered events.**
5. **Use one lock per game.**
6. **Bots advance on the server.**
7. **Stop automatic progression only when a human decision is required.**
8. **Use polling first.**
9. **Prove multiplayer with fake HTTP human clients before React.**
10. **Do not add accounts, WebSockets, matchmaking or ranking until the core works.**
