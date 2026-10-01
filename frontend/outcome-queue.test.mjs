import { test } from 'node:test';
import assert from 'node:assert/strict';
import { collectFreshOutcomes, collectFreshMatchOutcomes, createOutcomeTracker } from './src/outcome-queue.ts';

const view = (overrides = {}) => ({
  turn_index: 1, status: 'active', raid_card_id: 'raid_04',
  raid_standings: { escape_criterion: 'most_poker_wins' },
  ...overrides,
});

test('turn announcement precedes raid, updates do not repeat either', () => {
  const tracker = createOutcomeTracker();
  const items = collectFreshOutcomes(view(), tracker);
  assert.deepEqual(items.map(x => x.kind), ['turn_start', 'raid_start']);
  assert.equal(items[1].raidCardId, 'raid_04');
  assert.equal(items[1].criterion, 'most_poker_wins');
  assert.deepEqual(collectFreshOutcomes(view(), tracker), []);
  assert.deepEqual(collectFreshOutcomes(view({ turn_index: 2 }), tracker).map(x => x.kind), ['turn_start', 'raid_start']);
});

test('raid result precedes the next turn and its newly revealed raid', () => {
  const tracker = createOutcomeTracker();
  collectFreshOutcomes(view(), tracker);
  const items = collectFreshOutcomes(view({ turn_index: 2, raid_card_id: 'raid_06', last_raid_outcome: { turn_index: 1 } }), tracker);
  assert.deepEqual(items.map(x => x.kind), ['raid', 'turn_start', 'raid_start']);
  assert.equal(items[2].raidCardId, 'raid_06');
});

test('waits for the revealed raid and does not announce one at game end', () => {
  const tracker = createOutcomeTracker();
  assert.deepEqual(collectFreshOutcomes(view({ raid_card_id: null }), tracker).map(x => x.kind), ['turn_start']);
  assert.deepEqual(collectFreshOutcomes(view(), tracker).map(x => x.kind), ['raid_start']);
  assert.deepEqual(collectFreshOutcomes(view({ status: 'finished' }), createOutcomeTracker()).filter(x => x.kind === 'raid_start'), []);
});

test('tutorial match queue excludes turn and raid announcements', () => {
  assert.deepEqual(collectFreshMatchOutcomes(view(), new Set()), []);
});
