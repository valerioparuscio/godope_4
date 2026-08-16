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

// A decision submission now fires two sequential calls — /decisions/answer
// (dispatch-only) then /advance (progresses bots) — since the backend
// stopped bundling both into one response (2026-08-16, so the human's own
// move can render before bots' narration instead of after). Waiting for
// "any API call" would resolve on the *first* of the two and read the
// DOM while /advance is still in flight; wait for /advance specifically,
// since it's always the last call any given step fires.
function isAdvanceCall(url) {
  return url.includes('/advance');
}

// A command's own dispatch-only view can genuinely have no
// pending_decision for the human at all (their move landed, it's now a
// bot's turn) — in that case the panel shows "In attesa..." instead of
// .decision-panel for however long the *next* /advance's bot-turn
// narration overlay (.turn-playback, 2026-08-16) takes to play out
// (2s/beat, can be several beats), so waitForSelector('.decision-panel')
// must come *after* waiting for that overlay to clear, not before — and
// since React needs a tick to actually mount the overlay after the
// network response resolves, check for it once with a brief settle delay
// first rather than racing an empty DOM.
async function waitForPlaybackThenDecision(page) {
  await page.waitForTimeout(150);
  const overlay = page.locator('.turn-playback');
  if ((await overlay.count()) > 0) {
    if (process.env.SMOKE_LOG_PLAYBACK) {
      let lastText = null;
      while ((await overlay.count()) > 0) {
        const text = await overlay.locator('.turn-playback__card').textContent().catch(() => null);
        if (text && text !== lastText) {
          console.log('  [playback]', text);
          lastText = text;
        }
        await page.waitForTimeout(150);
      }
    }
    await page.waitForSelector('.turn-playback', { state: 'detached', timeout: 60000 });
  }
  await page.waitForSelector('.decision-panel, .finished-screen', { timeout: 15000 });
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

  // choose_grit_action / choose_action_type / corruption_action /
  // spend_link_for_extra_action / choose_brawl_link_evolution /
  // choose_brawl_relocation_destination render as one-click quick
  // buttons and/or board highlights (see DecisionPanel.tsx) instead of
  // the generic checkbox list + confirm button. Most button clicks
  // submit immediately, but some (corruption_action's "Sposta"/"Arresta"
  // with >1 target) instead *stage* the sub-action and wait for a
  // follow-up click on a glowing `.board-highlight`; some decisions
  // (e.g. relocation with candidates) have *no* button at all, only
  // board highlights — so this can't assume a button exists to click
  // first.
  if (await page.locator('.decision-panel--quick').count()) {
    // hand_discard / play_brawl_card / launch_poker / play_poker_card
    // answer through clickable cards in the (auto-opened) hand drawer
    // instead of the quick-buttons row — hand_discard's own button is a
    // Confirm that starts disabled until enough cards are picked; the
    // other three have no button of their own for the "pick a card"
    // case at all (only a Passa, when skipping is legal).
    const clickableCards = page.locator('.hand-drawer__card--clickable');
    const cardCount = await clickableCards.count();
    if (cardCount > 0) {
      const confirmButton = page.locator('.decision-panel__quick-buttons button', { hasText: 'Conferma' });
      if (await confirmButton.count()) {
        for (let i = 0; i < cardCount && !(await confirmButton.isEnabled()); i++) {
          await clickableCards.nth(i).click();
          await page.waitForTimeout(50);
        }
        await Promise.all([
          page.waitForResponse((res) => isAdvanceCall(res.url())),
          confirmButton.click(),
        ]);
      } else {
        await Promise.all([
          page.waitForResponse((res) => isAdvanceCall(res.url())),
          clickableCards.first().click(),
        ]);
      }
      await waitForPlaybackThenDecision(page);
      continue;
    }

    const buttonCount = await page.locator('.decision-panel__quick-buttons button').count();
    if (buttonCount === 0) {
      await page.waitForSelector('.board-highlight', { timeout: 5000 });
      await Promise.all([
        page.waitForResponse((res) => isAdvanceCall(res.url())),
        page.locator('.board-highlight').first().click(),
      ]);
    } else {
      // choose_action_type now always renders all 6 action-type buttons
      // in a fixed order (designer's request, 2026-08-16), some disabled
      // (already used this turn / no legal targets) — pick the first
      // *enabled* one there instead of blindly `.first()`, which could
      // land on a disabled button that will never become clickable. Package
      // decisions whose single Confirm button legitimately starts disabled
      // (waiting for a board pick) have zero enabled buttons at this point,
      // so this falls back to the old `.first()` behavior for those.
      const enabledButtons = page.locator('.decision-panel__quick-buttons button:enabled');
      const primaryButton =
        (await enabledButtons.count()) > 0
          ? enabledButtons.first()
          : page.locator('.decision-panel__quick-buttons button').first();
      if (!(await primaryButton.isEnabled())) {
        // Package decisions answered entirely on the board (place/move
        // Criminal, buy/sell Dope, corrupt/buy Officer, place a Poker bet,
        // play Marketing) render this same Confirm button, but it starts
        // disabled until at least one board target is picked — click
        // highlights (re-querying each time, since two-stage flows like
        // Move/Sell Dope swap what's glowing after the first click) until
        // it enables. Two-stage flows also render a `--selected` "cancel
        // current staging" highlight ahead of the real targets in the DOM
        // (click it to unstage) — exclude it, or the loop would just keep
        // clicking that instead of ever reaching a real destination.
        const pickable = page.locator('.board-highlight:not(.board-highlight--selected)');
        for (let i = 0; i < 6 && !(await primaryButton.isEnabled()); i++) {
          await page.waitForSelector('.board-highlight:not(.board-highlight--selected)', { timeout: 5000 });
          await pickable.first().click();
          await page.waitForTimeout(50);
        }
        await Promise.all([
          page.waitForResponse((res) => isAdvanceCall(res.url())),
          primaryButton.click(),
        ]);
      } else {
        const responsePromise = page.waitForResponse((res) => isAdvanceCall(res.url()), { timeout: 3000 }).catch(() => null);
        await primaryButton.click();
        const response = await responsePromise;
        if (!response) {
          // No request fired — the click staged a sub-action instead of
          // submitting one; its board targets are now glowing.
          await page.waitForSelector('.board-highlight', { timeout: 5000 });
          await Promise.all([
            page.waitForResponse((res) => isAdvanceCall(res.url())),
            page.locator('.board-highlight').first().click(),
          ]);
        }
      }
    }
    await waitForPlaybackThenDecision(page);
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
    page.waitForResponse((res) => isAdvanceCall(res.url())),
    page.locator('.decision-panel button').click(),
  ]);
  await waitForPlaybackThenDecision(page);
}

await browser.close();

if (!finished) {
  throw new Error(`Game did not reach the finished screen within ${MAX_STEPS} steps`);
}

console.log('OK: full game reached the finished screen through the real browser UI.');
