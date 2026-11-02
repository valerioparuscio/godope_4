import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { TUTORIAL_EN } from './src/tutorial/en.ts';

const scenarios = readFileSync(new URL('./src/tutorial/scenarios.ts', import.meta.url), 'utf8');

test('every English entry is keyed by a sentence that is still in scenarios.ts', () => {
  const stale = Object.keys(TUTORIAL_EN).filter((italian) => !scenarios.includes(italian));
  assert.deepEqual(stale, [], 'these Italian sentences are no longer in scenarios.ts (renamed or removed)');
});

test('no English entry is empty', () => {
  const empty = Object.entries(TUTORIAL_EN).filter(([, english]) => english.trim() === '').map(([italian]) => italian);
  assert.deepEqual(empty, []);
});
