// Easy Price board art v17 (BOARD_v17.webp, 2026-10-27) and its variant BOARD_v17_C.webp (the one in use
// since the same day, a different city background): where the Hoods, Den and Jail sit - identical on
// both, checked on the 17_C art too, no pixel off. The rest
// of the board (Contact headers, Spots, Link tracks, price dials, Job grid, money track, turn track,
// Gamble panel) is exactly where it was on the previous Easy Price art — checked by cross-correlating
// the two images region by region: no shift at all.
//
// Measured on the art, not eyeballed: each Hood's five petal circles and the Den's six bubbles were
// found by matching the old layout's own geometry (the shapes did not change size or form, only place)
// against the new image's edge map, then each circle refined on its own; the Jail's four discs by
// blob-detecting the dark circles (slot index 0-3 = the circle printed "1".."4"). A Hood's centre is
// the centroid of its petals, the Jail's the middle of its four discs, as in the standard layout.

import type { Point } from './board-layout';

// hood_id -> centre of its dope-pile circle.
export const EASY_PRICE_HOOD_POSITION: Record<string, Point> = {
  hood_q1: { xPct: 26.87, yPct: 79.76 },
  hood_q2: { xPct: 23.75, yPct: 48.68 },
  hood_q3: { xPct: 36.63, yPct: 45.67 },
  hood_q4: { xPct: 40.17, yPct: 70.13 },
  hood_q5: { xPct: 53.84, yPct: 41.09 },
  hood_q6: { xPct: 53.89, yPct: 83.46 },
  hood_q7: { xPct: 68.09, yPct: 45.70 },
  hood_q8: { xPct: 67.81, yPct: 77.90 },
  hood_q9: { xPct: 78.66, yPct: 63.50 },
  hood_q10: { xPct: 84.50, yPct: 41.24 },
};

// hood_id -> its 5 petals (same order as the standard layout's).
export const EASY_PRICE_HOOD_PETAL_POSITION: Record<string, Point[]> = {
  hood_q1: [
    { xPct: 22.83, yPct: 77.03 },
    { xPct: 26.82, yPct: 71.72 },
    { xPct: 30.95, yPct: 77.03 },
    { xPct: 29.45, yPct: 86.39 },
    { xPct: 24.28, yPct: 86.61 },
  ],
  hood_q2: [
    { xPct: 19.69, yPct: 46.03 },
    { xPct: 23.68, yPct: 40.62 },
    { xPct: 27.80, yPct: 46.03 },
    { xPct: 26.35, yPct: 55.29 },
    { xPct: 21.24, yPct: 55.41 },
  ],
  hood_q3: [
    { xPct: 32.58, yPct: 43.15 },
    { xPct: 36.67, yPct: 37.75 },
    { xPct: 40.70, yPct: 43.06 },
    { xPct: 39.10, yPct: 52.32 },
    { xPct: 34.08, yPct: 52.06 },
  ],
  hood_q4: [
    { xPct: 36.08, yPct: 67.62 },
    { xPct: 40.22, yPct: 62.22 },
    { xPct: 44.25, yPct: 67.53 },
    { xPct: 42.65, yPct: 76.79 },
    { xPct: 37.63, yPct: 76.52 },
  ],
  hood_q5: [
    { xPct: 49.73, yPct: 38.59 },
    { xPct: 53.87, yPct: 33.19 },
    { xPct: 57.85, yPct: 38.31 },
    { xPct: 56.35, yPct: 47.47 },
    { xPct: 51.38, yPct: 47.88 },
  ],
  hood_q6: [
    { xPct: 49.84, yPct: 80.80 },
    { xPct: 53.88, yPct: 75.49 },
    { xPct: 57.95, yPct: 80.80 },
    { xPct: 56.45, yPct: 90.07 },
    { xPct: 51.34, yPct: 90.18 },
  ],
  hood_q7: [
    { xPct: 64.08, yPct: 43.03 },
    { xPct: 68.07, yPct: 37.72 },
    { xPct: 72.15, yPct: 43.03 },
    { xPct: 70.60, yPct: 52.29 },
    { xPct: 65.53, yPct: 52.41 },
  ],
  hood_q8: [
    { xPct: 63.74, yPct: 75.23 },
    { xPct: 67.78, yPct: 69.92 },
    { xPct: 71.90, yPct: 75.23 },
    { xPct: 70.35, yPct: 84.49 },
    { xPct: 65.28, yPct: 84.61 },
  ],
  hood_q9: [
    { xPct: 74.68, yPct: 60.83 },
    { xPct: 78.62, yPct: 55.52 },
    { xPct: 82.70, yPct: 60.83 },
    { xPct: 81.20, yPct: 70.09 },
    { xPct: 76.13, yPct: 70.21 },
  ],
  hood_q10: [
    { xPct: 80.48, yPct: 38.59 },
    { xPct: 84.47, yPct: 33.28 },
    { xPct: 88.55, yPct: 38.59 },
    { xPct: 87.05, yPct: 47.85 },
    { xPct: 81.93, yPct: 47.88 },
  ],
};

export const EASY_PRICE_DEN_POSITION: Point = { xPct: 59.13, yPct: 61.78 };

export const EASY_PRICE_DEN_SLOT_POSITION: Point[] = [
  { xPct: 56.79, yPct: 54.67 },
  { xPct: 61.31, yPct: 54.63 },
  { xPct: 63.47, yPct: 61.65 },
  { xPct: 61.46, yPct: 69.03 },
  { xPct: 57.00, yPct: 68.79 },
  { xPct: 54.76, yPct: 61.88 },
];

export const EASY_PRICE_JAIL_CENTER: Point = { xPct: 84.71, yPct: 78.06 };

// slot index (0-3) -> the disc printed with that number plus one.
export const EASY_PRICE_JAIL_SLOT_POSITION: Point[] = [
  { xPct: 81.69, yPct: 88.85 },
  { xPct: 87.75, yPct: 88.60 },
  { xPct: 87.75, yPct: 77.93 },
  { xPct: 87.64, yPct: 67.25 },
];
