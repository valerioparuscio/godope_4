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

// A real decision submission always fires /decisions/answer (2026-08-16:
// dispatch-only now, no longer bundled with the bot cascade) — but *not*
// always /advance after it, since advance only runs at all when it's no
// longer the human's turn (e.g. an extra action keeps it their turn, no
// bot cascade follows at all that step). So /decisions/answer is the only
// reliable "did a submission actually happen" signal — waiting for
// /advance instead would hang forever on any step that doesn't trigger
// one, indistinguishable from a click that only staged a sub-action.
function isAnswerCall(url) {
  return url.includes('/decisions/answer');
}

// A command's own dispatch-only view can genuinely have no
// pending_decision for the human at all (their move landed, it's now a
// bot's turn) — in that case the panel shows "In attesa..." instead of
// .decision-panel for however long it takes to (a) collect that bot
// cascade's segments (App.tsx calls /advance once per bot turn-segment,
// in a loop, *before* any narration overlay ever mounts — an end-of-turn
// transition needing many segments can legitimately take a while just to
// collect, with nothing visible yet) and then (b) play the narration
// overlay (.turn-playback, 2026-08-16) out at 2s/beat. Wait patiently for
// *whichever* of "an overlay showed up" or "a real decision/error showed
// up directly" happens first, rather than assuming one short settle delay
// is enough to tell which path this step took.
async function waitForPlaybackThenDecision(page) {
  await page.waitForSelector('.turn-playback, .decision-panel, .finished-screen, .error', {
    timeout: 120000,
  });
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
    await page.waitForSelector('.turn-playback', { state: 'detached', timeout: 120000 });
    // .error is a valid outcome too (a caught exception can leave
    // pending_decision null with no overlay ever appearing) — without
    // this, that case just times out here looking like a genuine hang.
    await page.waitForSelector('.decision-panel, .finished-screen, .error', { timeout: 15000 });
  }
}

const browser = await chromium.launch();
const page = await browser.newPage();
page.on('pageerror', (err) => console.log('[browser page error]', err));
if (process.env.SMOKE_DEBUG_NET) {
  page.on('console', (msg) => console.log('[console.' + msg.type() + ']', msg.text()));
  page.on('request', (req) => {
    if (req.url().includes('/api/v1/games')) console.log('[REQ START]', req.method(), req.url());
  });
  page.on('requestfinished', async (req) => {
    if (req.url().includes('/api/v1/games')) {
      const resp = await req.response();
      console.log('[REQ DONE]', req.method(), req.url(), '->', resp ? resp.status() : '?');
    }
  });
}

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
          page.waitForResponse((res) => isAnswerCall(res.url())),
          confirmButton.click(),
        ]);
      } else {
        await Promise.all([
          page.waitForResponse((res) => isAnswerCall(res.url())),
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
        page.waitForResponse((res) => isAnswerCall(res.url())),
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
          page.waitForResponse((res) => isAnswerCall(res.url())),
          primaryButton.click(),
        ]);
      } else {
        // Corruption_action's "Sposta"/"Arresta" with >1 target *stages*
        // instead of submitting (a `.board-highlight--selected` "cancel"
        // marker appears, board.tsx's own two-stage pattern) — detected
        // here via that DOM marker, not by racing "did *some*
        // /decisions/answer response arrive within N ms": a still-settling
        // response from an *earlier* step (a slow bot cascade genuinely
        // needing more than a fixed race window, 2026-08-16) could
        // otherwise get misattributed to *this* click, wrongly concluding
        // it submitted when it only staged — leaving the real submission
        // never sent and the app correctly, permanently waiting on it.
        await primaryButton.click();
        await page.waitForTimeout(200);
        if (await page.locator('.board-highlight--selected').count()) {
          await page.waitForSelector('.board-highlight:not(.board-highlight--selected)', { timeout: 5000 });
          await page.locator('.board-highlight:not(.board-highlight--selected)').first().click();
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
    page.waitForResponse((res) => isAnswerCall(res.url())),
    page.locator('.decision-panel button').click(),
  ]);
  await waitForPlaybackThenDecision(page);
}

await browser.close();

if (!finished) {
  throw new Error(`Game did not reach the finished screen within ${MAX_STEPS} steps`);
}

console.log('OK: full game reached the finished screen through the real browser UI.');
