import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';

// Run with the local backend and Vite running. Screenshots stay untracked.
await mkdir('../debug_failures', { recursive: true });

const browser = await chromium.launch({ headless: true });
try {
const page = await browser.newPage();
await page.addInitScript(() => localStorage.setItem('dope_tutorial_v2_seen', 'true'));
await page.route('**/api/v1/games', async route => {
  if (route.request().method() !== 'POST') return route.continue();
  const data = route.request().postDataJSON();
  await route.continue({ postData: JSON.stringify({ ...data, seed: 42 }) });
});
await page.goto('http://127.0.0.1:5173/game/');
await page.locator('input').fill('Layout test');
await page.getByRole('button', { name: 'GIOCA', exact: true }).click();
await page.locator('.app').waitFor();
await page.locator('[data-outcome="turn_start"]').waitFor();
await page.locator('.outcome-modal__ok').click();
await page.locator('[data-outcome="raid_start"]').waitFor();
for (const [width, height] of [[1280,800], [390,844], [320,568], [960,540]]) {
  await page.setViewportSize({ width, height });
  await page.waitForTimeout(400);
  const popup = await page.locator('[data-outcome="raid_start"]').boundingBox();
  assert.ok(popup.x >= 0 && popup.y >= 0 && popup.x + popup.width <= width && popup.y + popup.height <= height, 'Raid announcement outside viewport');
  assert.ok(await page.locator('.raid-announcement__card').evaluate(img => img.complete && img.naturalWidth > 0), 'Missing raid card');
  await page.screenshot({ path: `../debug_failures/raid-announcement-${width}.png` });
}
await page.locator('.outcome-modal__ok').click();
for (let i = 0; i < 25; i++) {
  if (await page.locator('.outcome-modal__ok').count()) await page.locator('.outcome-modal__ok').click();
  if (await page.locator('.action-chooser').count()) break;
  await page.waitForTimeout(500);
}
await page.locator('.action-chooser').waitFor();
assert.equal(await page.locator('.top-strip__optional-actions button:has-text("Fine turno")').count(), 0, 'Fine turno is still in the optional controls');
assert.equal(await page.locator('.top-strip__optional-actions button:has-text("Ganci")').count(), 0, 'Ganci is still in the optional controls');
assert.equal(await page.locator('.action-chooser__box--link').count(), 1, 'Gancio is missing from the main controls');
assert.deepEqual(await page.locator('.action-chooser__box--grit .decision-pill__grit-button').allTextContents(), ['1', '2', '3']);
assert.equal(await page.locator('.human-controls__end-turn').count(), 0, 'Fine turno appeared before it became available');
for (const [width, height] of [[1920,1080],[1700,1000],[1440,900],[1280,800],[1024,768],[820,1180],[768,1024],[760,900],[680,900],[390,844],[320,568],[1280,600],[960,540],[800,400]]) {
  await page.setViewportSize({ width, height });
  await page.waitForTimeout(150);
  const result = await page.evaluate(() => {
    const rect = (selector) => {
      const r = document.querySelector(selector).getBoundingClientRect();
      return { x:r.x, y:r.y, width:r.width, height:r.height, right:r.right, bottom:r.bottom };
    };
    const buttons = [...document.querySelectorAll('.top-strip button')].map(el => ({ name:el.textContent.trim(), rect:el.getBoundingClientRect() }));
    const overlaps = [];
    for (let i=0;i<buttons.length;i++) for (let j=i+1;j<buttons.length;j++) {
      const a=buttons[i].rect, b=buttons[j].rect;
      if (Math.min(a.right,b.right)-Math.max(a.left,b.left)>1 && Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1) overlaps.push([buttons[i].name,buttons[j].name]);
    }
    const main = document.querySelector('.human-controls__main');
    const sidebar = rect('.app__sidebar');
    const raid = rect('.app__sidebar .raid-banner');
    const strip = rect('.app__sidebar .player-strip');
    const shares = [...document.querySelectorAll('.app__sidebar .player-card')].map(el => ({
      human: el.classList.contains('player-card--big'),
      share: (el.getBoundingClientRect().height + 4) / sidebar.height,
    }));
    const primaryWidth = rect('.top-strip__primary-buttons .hand-drawer__toggle').width;
    const optionalWidths = [...document.querySelectorAll('.top-strip__optional-button')].map(el => el.getBoundingClientRect().width);
    const optionOverflow = [...document.querySelectorAll('.top-strip__optional-button')].some(el => el.scrollHeight > el.clientHeight + 1);
    return { board:rect('.board-view'), control:rect('.human-controls'), primary:rect('.top-strip__primary-buttons'), overlaps, mainOverflow:main.scrollWidth-main.clientWidth, appOverflow:document.querySelector('.app').scrollWidth-innerWidth,
      primaryWidth, optionalWidths, optionOverflow,
      raidShare: raid.height/sidebar.height, spacerShare:(strip.y-raid.bottom)/sidebar.height, shares };
  });
  console.log(width,height,JSON.stringify(result));
  await page.screenshot({path:`../debug_failures/layout-${width}-${height}.png`,fullPage:true});
  assert.equal(result.overlaps.length,0,'Overlapping buttons');
  if (result.control.width > 680) {
    assert.ok(Math.abs(result.primary.y - result.control.y) < 2 && result.primary.right <= result.control.x - 2,
      'Carte and Skill are not immediately left of the main bar');
  }
  assert.ok(result.mainOverflow<=1,'Primary actions need horizontal scroll');
  assert.ok(result.appOverflow<=1,'Game overflows horizontally');
  assert.ok(result.optionalWidths.every(value => Math.abs(value - result.primaryWidth) < 2), 'Optional buttons differ in width from Carte and Skill');
  assert.equal(result.optionOverflow, false, 'Optional button content overflows');
  assert.ok(Math.abs(result.board.width/result.board.height-8070/4200)<0.01,'Board distorted');
  assert.ok(Math.abs(result.raidShare-0.25)<0.001, 'Raid allocation');
  assert.ok(Math.abs(result.spacerShare-0.1)<0.001, 'Sidebar spacer');
  for (const card of result.shares) assert.ok(Math.abs(card.share-(card.human ? 0.25 : 0.4/3))<0.001, 'Player allocation');
}
await page.locator('.action-chooser').evaluate(chooser => {
  chooser.classList.add('action-chooser--actions-only');
  chooser.querySelector('.action-chooser__box--grit').style.display = 'none';
});
for (const [width, height] of [[1280, 800], [390, 844], [320, 568]]) {
  await page.setViewportSize({ width, height });
  const widths = await page.locator('.action-chooser').evaluate(chooser => ({
    chooser: chooser.getBoundingClientRect().width,
    link: chooser.querySelector('.action-chooser__box--link').getBoundingClientRect(),
    actions: chooser.querySelector('.action-chooser__box--actions').getBoundingClientRect().width,
  }));
  assert.ok(widths.link.width + widths.actions >= widths.chooser - 8, 'Extra-action choices do not fill the bar');
  await page.screenshot({ path: `../debug_failures/extra-action-choices-${width}.png` });
}
await page.locator('.action-chooser').evaluate(chooser => {
  chooser.querySelector('.action-chooser__box--grit').style.display = '';
  chooser.classList.remove('action-chooser--actions-only');
});
// Preview the conditional control's layout at the same sizes it had in the
// optional row; the real visibility condition is driven by canEndTurn.
await page.locator('.human-controls__body').evaluate(body => {
  body.closest('.human-controls').classList.replace('human-controls--choosing', 'human-controls--action');
  body.classList.add('human-controls__body--end-turn');
  const main = body.querySelector('.human-controls__main');
  main.querySelector('.action-chooser').style.display = 'none';
  const message = document.createElement('div');
  message.className = 'decision-message-shell decision-message-shell--preview';
  message.innerHTML = '<div class="human-controls__guidance"><h3>Scegli un gancio da usare</h3></div>';
  main.append(message);
  const button = document.createElement('button');
  button.className = 'human-controls__end-turn';
  button.textContent = 'Fine turno';
  body.append(button);
});
for (const [width, height, expectedHeight] of [[1280, 800, 146], [390, 844, 48], [320, 568, 48]]) {
  await page.setViewportSize({ width, height });
  const bounds = await page.locator('.human-controls__end-turn').boundingBox();
  const bar = await page.locator('.human-controls').boundingBox();
  const primaryWidth = (await page.locator('.top-strip__primary-buttons .hand-drawer__toggle').first().boundingBox()).width;
  const heading = await page.locator('.decision-message-shell--preview h3').boundingBox();
  assert.ok(Math.abs(bounds.width - 2 * primaryWidth) < 2 && Math.abs(bounds.height - expectedHeight) < 2, 'Fine turno has the wrong size');
  assert.ok(Math.abs(bounds.x + bounds.width / 2 - (bar.x + bar.width / 2)) < 2, 'Fine turno is not centered');
  assert.ok(bounds.x >= bar.x && bounds.x + bounds.width <= bar.x + bar.width && bounds.y >= bar.y && bounds.y + bounds.height <= bar.y + bar.height, 'Fine turno is outside the main bar');
  await page.screenshot({ path: `../debug_failures/end-turn-layout-${width}.png` });
  assert.ok(heading.x + heading.width <= bounds.x - 2, 'Gancio title overlaps Fine turno');
}
await page.locator('.human-controls__body').evaluate(body => {
  body.closest('.human-controls').classList.replace('human-controls--action', 'human-controls--choosing');
  body.querySelector('.human-controls__end-turn').remove();
  body.querySelector('.decision-message-shell--preview').remove();
  body.querySelector('.action-chooser').style.display = '';
  body.classList.remove('human-controls__body--end-turn');
});
await page.setViewportSize({ width: 390, height: 844 });
const initialBoard = await page.locator('.board-view').boundingBox();
await page.getByRole('button', { name: 'Piazza', exact: true }).click();
await page.getByRole('button', { name: 'Piazza', exact: true }).and(page.locator('[aria-pressed="true"]')).waitFor();
assert.equal(await page.locator('.action-chooser__box--link:has-text("GANCIO")').count(), 0, 'Gancio remains after choosing an action');
assert.equal(await page.locator('.action-chooser__box--confirm').count(), 0, 'An extra confirmation appeared before the action details');
const planned = page.waitForResponse(r => r.url().includes('/plan') && r.request().method() === 'POST');
await page.locator('.decision-pill__grit-button:not(:disabled)').last().click();
const planResponse = await planned;
const plan = await planResponse.json();
if (plan.view.pending_decision?.decision_type === 'play_customer_card_boost') {
  await page.getByRole('button', { name: 'No, grazie', exact: true }).click();
}
await page.locator('.human-controls--action .decision-panel').waitFor();
assert.equal(await page.locator('.human-controls__round-link').count(), 0, 'Gancio replaced the selected action details');
for (const [width, height] of [[1280, 800], [390, 844], [320, 568]]) {
  await page.setViewportSize({ width, height });
  const message = await page.locator('.human-controls--action .decision-panel').evaluate(panel => {
    const title = panel.querySelector('h3');
    const hint = panel.querySelector('p');
    const button = panel.querySelector('.decision-panel__quick-buttons button');
    const bounds = button.getBoundingClientRect();
    const bar = panel.closest('.human-controls').getBoundingClientRect();
    const progress = panel.parentElement.querySelector('.decision-message-shell__progress');
    return {
      titleSize: parseFloat(getComputedStyle(title).fontSize),
      hintSize: parseFloat(getComputedStyle(hint).fontSize),
      buttonSize: parseFloat(getComputedStyle(button).fontSize),
      buttonGlyphSize: parseFloat(getComputedStyle(button, '::after').fontSize),
      buttonHeight: bounds.height,
      buttonInsideBar: bounds.top >= bar.top && bounds.bottom <= bar.bottom,
      titleRight: title.getBoundingClientRect().right,
      progressLeft: progress.getBoundingClientRect().left,
      progressRight: progress.getBoundingClientRect().right,
      buttonLeft: bounds.left,
      progressText: progress.textContent.trim(),
    };
  });
  await page.screenshot({ path: `../debug_failures/decision-message-${width}.png` });
  assert.ok(message.titleSize >= 24 && message.hintSize >= 14, 'Decision message is too small');
  assert.ok((message.buttonSize >= 15 || message.buttonGlyphSize >= 24) && message.buttonHeight >= 100, 'Decision button is too small');
  assert.ok(message.buttonInsideBar, 'Decision button is outside the bar');
  assert.equal(message.progressText, '0/3', 'Wrong initial package progress');
  assert.ok(message.titleRight <= message.progressLeft + 1 && message.progressRight <= message.buttonLeft + 1, 'Message columns overlap');
}
await page.setViewportSize({ width: 390, height: 844 });
const twoChoiceLayout = await page.locator('.decision-panel__quick-buttons').evaluate(group => {
  const first = group.querySelector('button');
  const originalText = first.textContent;
  const originalLabel = first.getAttribute('data-bar-label');
  first.textContent = 'Soldi';
  first.removeAttribute('data-bar-label');
  const second = first.cloneNode(true);
  second.textContent = 'Carta';
  group.append(second);
  const panel = group.closest('.decision-panel').getBoundingClientRect();
  const widths = [...group.querySelectorAll('button')].map(button => button.getBoundingClientRect().width / panel.width);
  second.remove();
  first.textContent = originalText;
  if (originalLabel !== null) first.setAttribute('data-bar-label', originalLabel);
  return widths;
});
assert.ok(twoChoiceLayout.every(share => Math.abs(share - 0.15) < 0.02), 'Two choices do not have 15% width each');
assert.deepEqual(await page.locator('.board-view').boundingBox(), initialBoard, 'Decision moved the board');
assert.ok(await page.locator('.board-highlight').count(), 'No playable board targets');
await page.locator('.board-highlight').first().click();
assert.equal((await page.locator('.decision-message-shell__progress').textContent()).trim(), '1/3', 'Selecting a target did not advance package progress');
await page.locator('.board-highlight').nth(1).click();
assert.equal((await page.locator('.decision-message-shell__progress').textContent()).trim(), '2/3', 'Second target did not advance package progress');
await page.locator('.board-highlight').nth(2).click();
assert.equal((await page.locator('.decision-message-shell__progress').textContent()).trim(), '3/3', 'Third target did not complete package progress');
assert.ok(await page.locator('.decision-panel__quick-buttons button').isEnabled(), 'Cannot confirm selection');
await page.getByRole('button', { name: 'Torna indietro' }).click();
assert.equal((await page.locator('.decision-message-shell__progress').textContent()).trim(), '0/3', 'Undoing a target did not restore package progress');
assert.ok(await page.locator('.decision-panel__quick-buttons button').isDisabled(), 'Back did not clear the staged selection');
for (const width of [320, 768, 1280]) {
  await page.setViewportSize({ width, height: 700 });
  for (const [toggle, panel] of [
    ['.hand-drawer > button', '.hand-drawer__panel'],
    ['.skills-drawer > button', '.skills-drawer__panel'],
    ['.action-log-drawer > button', '.action-log-drawer__panel'],
    ['button:has-text("Regolamento")', '.rules-modal'],
  ]) {
    await page.locator(toggle).click();
    const r = await page.locator(panel).boundingBox();
    assert.ok(r.x >= 0 && r.x + r.width <= width + 1 && r.y >= 0 && r.y + r.height <= 701, `${panel} outside viewport at ${width}`);
    if (panel === '.rules-modal') await page.locator('.rules-modal__close').click();
    else await page.locator(toggle).click();
  }
}
await page.locator('.board-highlight').first().click();
await page.locator('.decision-panel__quick-buttons button').click();
await page.locator('.human-controls--playback .bot-turn-banner').waitFor({ timeout: 20000 });
for (const [width, height] of [[1280, 800], [390, 844]]) {
  await page.setViewportSize({ width, height });
  await page.waitForTimeout(250);
  const playbackBounds = await page.evaluate(() => {
    const panel = document.querySelector('.human-controls--playback').getBoundingClientRect();
    const banner = document.querySelector('.human-controls--playback .bot-turn-banner').getBoundingClientRect();
    const style = getComputedStyle(document.querySelector('.human-controls--playback'));
    const innerWidth = panel.width - parseFloat(style.borderLeftWidth) - parseFloat(style.borderRightWidth);
    const innerHeight = panel.height - parseFloat(style.borderTopWidth) - parseFloat(style.borderBottomWidth);
    return { innerWidth, bannerWidth: banner.width, bannerHeight: banner.height, innerHeight, mainVisible: !!document.querySelector('.human-controls--playback .human-controls__main') };
  });
  assert.ok(Math.abs(playbackBounds.innerWidth-playbackBounds.bannerWidth) < 2, 'Narration does not fill the main bar');
  assert.ok(Math.abs(playbackBounds.innerHeight-playbackBounds.bannerHeight) < 2, 'Narration does not fill the main bar height');
  assert.equal(playbackBounds.mainVisible, false, 'Decision controls remain under narration');
  await page.screenshot({ path: `../debug_failures/playback-${width}.png` });
}
await page.locator('.human-controls--playback .bot-turn-banner__row').waitFor({ timeout: 6000 });
assert.ok(await page.locator('.bot-turn-banner__pawn').count() > 0, 'Place/move beat has no player pawn');
assert.ok(await page.locator('.bot-turn-banner__pawn').first().evaluate(img => img.complete && img.naturalWidth > 0), 'Player pawn did not load');
await page.screenshot({ path: '../debug_failures/playback-action-390.png' });
console.log('Action selection, stable board and popup bounds passed.');
} finally {
await browser.close();
}
