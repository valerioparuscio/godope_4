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

- `npm run build` — type-checks (`tsc -b`) and bundles.
- `node smoke-test.mjs` — headless end-to-end smoke test (Playwright):
  plays a full game through the real UI and asserts it reaches the
  finished screen. Requires both servers above to be running; override the
  frontend URL with `SMOKE_URL` if not on the Vite default.
