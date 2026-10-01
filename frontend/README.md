# DOPE frontend

React + Vite + TypeScript client for the DOPE engine (see the repo root
`CLAUDE.md` and `docs/architecture/decisions/0001-frontend-stack-react-vite.md`
for why). This first version is functional, not visual: no board art, no
card art yet — plain HTML tables. See CLAUDE.md section 15 for the
frontend's architectural responsibilities.

## Run it

1. Start the backend first (from the repo root):
   `python tools/run_backend.py --port 8000`
2. In this directory: `npm install` (first time only), then `npm run dev`.
3. Open the printed URL. If it's not `http://127.0.0.1:5173`, either update
   `app.py`'s CORS `allow_origins` or set `VITE_API_BASE_URL` to match your
   backend's actual host/port.

## Verify

- `node --test outcome-queue.test.mjs` checks turn/raid announcement order,
  deduplication, delayed reveals, and tutorial isolation (Node 24).

- `node responsive-check.mjs` checks 14 viewport sizes, toolbar overlap,
  horizontal overflow, board proportions and stability while choosing an
  action, and popup bounds. Requires the backend on port 8000 and Vite on
  port 5173. Screenshots are saved in `../debug_failures/` (not versioned).

- `npm run build` — type-checks (`tsc -b`) and bundles.
- `node smoke-test.mjs` — headless end-to-end smoke test (Playwright):
  plays a full game through the real UI and asserts it reaches the
  finished screen. Requires both servers above to be running; override the
  frontend URL with `SMOKE_URL` if not on the Vite default.

## Adaptive layout

`src/responsive.css` is loaded after the base styles. The play area's
container width determines whether the toolbar shares a row with the
controls, the fixed actions take their own row, or primary actions use a
3x2 grid. Ganci, Marketing, Poker, Fine turno and Torna indietro fill a
separate framed group; each is as wide as Carte and Skill at that size.
Carte and Skill fill their own framed group; Log, Regolamento and Musica
remain shorter beside it.
Control heights stay fixed within each layout so changing decisions does
not resize the board; longer decisions scroll inside the control panel.
During bot narration the main panel gives its full area to the acting
player's portrait and move, hiding decision controls until playback ends.
The sidebar reserves 25% for the raid, 10% for empty space, and 65% for
players: 25% for the human and 13.33% for each bot, including small card
gutters. Player cards keep turn order, including in portrait mode.
Narrow and portrait viewports stack the board and player information.
Short viewports allow the game to
scroll vertically. Floating panels are bounded by the viewport.

These are content-space thresholds, independent of device detection or
browser zoom. On very small screens the full board is necessarily small;
this change does not add independent board zoom/panning.
