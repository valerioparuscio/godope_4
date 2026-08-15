// One-off E2E smoke test (not part of the committed test suite): drives the
// real browser UI through a full game (1 human + 3 bots) to prove the
// React frontend <-> FastAPI backend pivot actually works end to end,
// clicking through every decision like a human would. Run manually with
// `node smoke-test.mjs` while both `python tools/run_backend.py` and
// `npm run dev` are running.
//
// Every action that triggers a backend call is paired with an explicit
// `page.waitForResponse(...)` for that exact call, rather than just
// awaiting the click — a plain click() only waits for the DOM event to
// dispatch, not for the fetch + React re-render that follows, so reading
// the next decision's DOM immediately after a click can race a still
// in-flight request and observe a stale (already-superseded) panel.
import { chromium } from 'playwright';

const BASE_URL = process.env.SMOKE_URL ?? 'http://127.0.0.1:5173';
const MAX_STEPS = 400;

function isApiCall(url) {
  return url.includes('/api/v1/games');
}

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('pageerror', (err) => console.log('[browser page error]', err));

await page.goto(BASE_URL);
await Promise.all([
  page.waitForResponse((res) => isApiCall(res.url())),
  page.getByRole('button', { name: 'Nuova partita' }).click(),
]);
// The setup flow fires two calls (create, then view) — wait for the app
// to settle on either a decision panel or the finished screen too.
await page.waitForSelector('.decision-panel, .finished-screen', { timeout: 15000 });

let finished = false;
for (let step = 0; step < MAX_STEPS; step++) {
  if (await page.locator('.finished-screen').count()) {
    finished = true;
    break;
  }

  if (await page.locator('.error').count()) {
    const text = await page.locator('.error').first().textContent();
    throw new Error(`UI surfaced an error at step ${step}: ${text}`);
  }

  // choose_grit_action / choose_action_type render as one-click quick
  // buttons (see DecisionPanel.tsx) instead of the generic checkbox list
  // + confirm button — each button submits its own option immediately.
  if (await page.locator('.decision-panel--quick').count()) {
    await Promise.all([
      page.waitForResponse((res) => isApiCall(res.url())),
      page.locator('.decision-panel__quick-buttons button').first().click(),
    ]);
    await page.waitForSelector('.decision-panel, .finished-screen', { timeout: 15000 });
    continue;
  }

  // "Seleziona da X a Y opzioni." — read the *minimum* required straight
  // from the rendered DecisionPanel copy rather than hardcoding option
  // counts, since some decisions (e.g. end-of-turn hand discard) require
  // more than one selection (min_selections == max_selections == overflow).
  const rangeText = await page
    .locator('.decision-panel p', { hasText: 'Seleziona da' })
    .textContent();
  const match = rangeText?.match(/Seleziona da (\d+) a (\d+)/);
  const minSelections = match ? Number(match[1]) : 0;

  const inputs = page.locator(
    '.decision-panel input[type="checkbox"], .decision-panel input[type="radio"]',
  );
  for (let i = 0; i < minSelections; i++) {
    await inputs.nth(i).click();
  }

  await Promise.all([
    page.waitForResponse((res) => isApiCall(res.url())),
    page.locator('.decision-panel button').click(),
  ]);
  await page.waitForSelector('.decision-panel, .finished-screen', { timeout: 15000 });
}

await browser.close();

if (!finished) {
  throw new Error(`Game did not reach the finished screen within ${MAX_STEPS} steps`);
}

console.log('OK: full game reached the finished screen through the real browser UI.');
