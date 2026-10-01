import { chromium } from 'playwright';
import assert from 'node:assert/strict';

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
  await page.locator('input').fill('Flight test');
  await page.getByRole('button', { name: 'GIOCA', exact: true }).click();
  await page.locator('.app__sidebar .player-card[data-player-id="player_0"] [data-resource-key="rana"] img').waitFor();

  for (const size of [{ width: 1280, height: 800 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(size);
    const positions = await page.evaluate(async () => {
      const { default: React } = await import('/game/node_modules/.vite/deps/react.js');
      const { default: ReactDOM } = await import('/game/node_modules/.vite/deps/react-dom_client.js');
      const { ResourceFlights } = await import('/game/src/components/ResourceFlights.tsx');
      const mount = document.createElement('div');
      document.body.append(mount);
      const root = ReactDOM.createRoot(mount);
      const center = element => {
        const rect = element.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
      };
      const card = document.querySelector('.app__sidebar .player-card[data-player-id="player_0"]');
      const board = document.querySelector('.app__play-area .board-view');
      const dopeTarget = center(card.querySelector('[data-resource-key="rana"] img'));
      const dopeSource = center(card.querySelector('[data-resource-key="camaleonte"] img'));
      const copTarget = center(card.querySelector('[data-resource-key="cops"] img'));
      const blueCard = document.querySelector('.app__sidebar .player-card[data-player-id="player_1"]');
      const copSource = center(blueCard.querySelector('[data-resource-key="cops"] img'));
      const boardCenter = center(board);
      root.render(React.createElement(ResourceFlights, {
        dopeTransfers: [{ id: 'test-dope', dopeType: 'rana', from: { xPct: 50, yPct: 50 },
          to: { xPct: -3, yPct: 15 }, destination: 'base', destinationId: 'player_0',
          playerId: 'player_0', count: 1 },
        { id: 'test-sale', dopeType: 'camaleonte', from: { xPct: -3, yPct: 15 },
          to: { xPct: 50, yPct: 50 }, destination: 'spot', destinationId: 'test-spot',
          playerId: 'player_0', count: 1 }],
        officerPurchases: [{ id: 'test-cop', officerType: 'cop', from: { xPct: 50, yPct: 50 },
          fromPlayerId: null, to: null, toPlayerId: 'player_0' },
        { id: 'test-cop-sale', officerType: 'cop', from: null,
          fromPlayerId: 'player_1', to: { xPct: 50, yPct: 50 }, toPlayerId: null }],
      }));
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const tokens = [...document.querySelectorAll('.resource-flights__token')].map(token => {
        token.getAnimations().forEach(animation => animation.finish());
        const rendered = center(token);
        return {
          toX: parseFloat(token.style.left), toY: parseFloat(token.style.top),
          fromX: parseFloat(token.style.getPropertyValue('--flight-from-x')),
          fromY: parseFloat(token.style.getPropertyValue('--flight-from-y')),
          renderedX: rendered.x, renderedY: rendered.y,
        };
      });
      root.unmount();
      mount.remove();
      return { tokens, dopeTarget, dopeSource, copTarget, copSource, boardCenter };
    });
    assert.equal(positions.tokens.length, 4);
    const paths = [
      [positions.tokens[0], positions.boardCenter, positions.dopeTarget],
      [positions.tokens[1], positions.dopeSource, positions.boardCenter],
      [positions.tokens[2], positions.boardCenter, positions.copTarget],
      [positions.tokens[3], positions.copSource, positions.boardCenter],
    ];
    for (const [token, source, target] of paths) {
      assert.ok(Math.abs(token.toX - target.x) < 1 && Math.abs(token.toY - target.y) < 1);
      assert.ok(Math.abs(token.fromX - source.x) < 1 && Math.abs(token.fromY - source.y) < 1);
      assert.ok(Math.abs(token.renderedX - target.x) < 1 && Math.abs(token.renderedY - target.y) < 1);
    }
  }
  console.log('Resource flights start and end on the matching player-board icons at both widths.');
} finally {
  await browser.close();
}
