import { test } from 'node:test';
import assert from 'node:assert/strict';
import { largestFreeRect } from './src/tutorial/free-rect.ts';

const area = { left: 0, top: 0, right: 1000, bottom: 600 };
const options = { margin: 0, pad: 0, minWidth: 100, minHeight: 100 };
const box = (left, top, right, bottom) => ({ left, top, right, bottom });
const touches = (a, b) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;

test('with nothing in the way the whole area is free', () => {
  assert.deepEqual(largestFreeRect(area, [], options), area);
});

test('the margin keeps the rectangle off the edges', () => {
  assert.deepEqual(largestFreeRect(area, [], { ...options, margin: 20 }), box(20, 20, 980, 580));
});

test('a label on the left leaves the big block to its right', () => {
  const label = box(0, 300, 200, 360);
  const free = largestFreeRect(area, [label], options);
  assert.ok(free);
  assert.equal(touches(free, label), false);
  // the block right of the label (800x600) beats the one above it (1000x300)
  assert.deepEqual(free, box(200, 0, 1000, 600));
});

test('labels on several sides leave the middle', () => {
  const labels = [box(0, 0, 150, 60), box(0, 250, 150, 310), box(400, 540, 600, 600), box(850, 250, 1000, 310)];
  const free = largestFreeRect(area, labels, options);
  assert.ok(free);
  for (const label of labels) assert.equal(touches(free, label), false);
  assert.ok((free.right - free.left) * (free.bottom - free.top) >= 600 * 400);
});

test('the padding grows every obstacle', () => {
  const label = box(0, 300, 200, 360);
  const free = largestFreeRect(area, [label], { ...options, pad: 10 });
  assert.deepEqual(free, box(210, 0, 1000, 600));
});

test('an obstacle outside the area is ignored', () => {
  assert.deepEqual(largestFreeRect(area, [box(1200, 0, 1400, 100)], options), area);
});

test('no room for a card that big gives null', () => {
  const wall = [box(0, 0, 460, 600), box(540, 0, 1000, 600)];
  assert.equal(largestFreeRect(area, wall, options), null); // the 80-wide gap is narrower than minWidth
});
