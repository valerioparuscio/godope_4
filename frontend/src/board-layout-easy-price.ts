// Easy Price board art v17_D (BOARD_v17_D.webp, 2026-10-30), the one in use: where its Hoods, Den and Jail
// sit, and the turn track. The Hood ids are the numbers printed on the art (the designer's numbered copy), and
// data_packs/easy_price/board.json follows them: the covered Hoods are 1, 3, 6, 8 and 10. Against the previous art
// (BOARD_v17_C.webp; its values are kept in board-layout-easy-price-v17c.ts) the pink and green Hoods, the Den
// (now top-left) and the Jail (a diamond of four discs, bottom-right) moved, Hood 9 shifted a little and the
// turn-track circles are 1.12% further right; Hoods 5, 6, 7, 8 and 10 did not move. The rest of the board
// (Contact headers, Spots, Link tracks, price dials, Job grid, money track, Gamble panel) is exactly where it
// was — cross-correlated region by region: no shift at all.
//
// Measured on the art, not eyeballed: each Hood's five petal circles and the Den's six bubbles were found by
// matching the previous layout's own geometry (the shapes did not change size or form, only place) against the
// new image's edge map, then each circle refined on its own; the Jail's four discs by blob-detecting the gray
// circles (slot index 0-3 = the disc printed "1".."4"); the turn track by the centres of its three circles. A
// Hood's centre is the centroid of its petals, the Jail's the middle of its four discs, as in the standard layout.

import type { Point } from './board-layout';

// hood_id -> centre of its dope-pile circle.
export const EASY_PRICE_HOOD_POSITION: Record<string, Point> = {
  hood_q1: { xPct: 23.36, yPct: 63.42 },
  hood_q2: { xPct: 30.59, yPct: 82.38 },
  hood_q3: { xPct: 38.88, yPct: 42.83 },
  hood_q4: { xPct: 42.83, yPct: 67.85 },
  hood_q5: { xPct: 53.84, yPct: 41.07 },
  hood_q6: { xPct: 53.90, yPct: 83.47 },
  hood_q7: { xPct: 68.08, yPct: 45.71 },
  hood_q8: { xPct: 67.81, yPct: 77.89 },
  hood_q9: { xPct: 78.06, yPct: 62.71 },
  hood_q10: { xPct: 84.50, yPct: 41.22 },
};

// hood_id -> its 5 petals (same order as the standard layout's).
export const EASY_PRICE_HOOD_PETAL_POSITION: Record<string, Point[]> = {
  hood_q1: [
    { xPct: 19.29, yPct: 60.76 },
    { xPct: 23.33, yPct: 55.44 },
    { xPct: 27.40, yPct: 60.76 },
    { xPct: 25.95, yPct: 70.02 },
    { xPct: 20.84, yPct: 70.14 },
  ],
  hood_q2: [
    { xPct: 26.51, yPct: 79.75 },
    { xPct: 30.55, yPct: 74.25 },
    { xPct: 34.68, yPct: 79.75 },
    { xPct: 33.18, yPct: 89.02 },
    { xPct: 28.01, yPct: 89.14 },
  ],
  hood_q3: [
    { xPct: 34.81, yPct: 40.29 },
    { xPct: 38.90, yPct: 34.99 },
    { xPct: 42.98, yPct: 40.20 },
    { xPct: 41.33, yPct: 49.46 },
    { xPct: 36.36, yPct: 49.19 },
  ],
  hood_q4: [
    { xPct: 38.75, yPct: 65.33 },
    { xPct: 42.89, yPct: 59.93 },
    { xPct: 46.92, yPct: 65.24 },
    { xPct: 45.32, yPct: 74.50 },
    { xPct: 40.25, yPct: 74.24 },
  ],
  hood_q5: [
    { xPct: 49.74, yPct: 38.60 },
    { xPct: 53.88, yPct: 33.10 },
    { xPct: 57.86, yPct: 38.32 },
    { xPct: 56.36, yPct: 47.48 },
    { xPct: 51.34, yPct: 47.89 },
  ],
  hood_q6: [
    { xPct: 49.85, yPct: 80.75 },
    { xPct: 53.89, yPct: 75.53 },
    { xPct: 57.96, yPct: 80.75 },
    { xPct: 56.46, yPct: 90.11 },
    { xPct: 51.35, yPct: 90.22 },
  ],
  hood_q7: [
    { xPct: 64.04, yPct: 43.04 },
    { xPct: 68.08, yPct: 37.73 },
    { xPct: 72.16, yPct: 43.04 },
    { xPct: 70.61, yPct: 52.30 },
    { xPct: 65.54, yPct: 52.42 },
  ],
  hood_q8: [
    { xPct: 63.78, yPct: 75.26 },
    { xPct: 67.77, yPct: 69.86 },
    { xPct: 71.89, yPct: 75.26 },
    { xPct: 70.34, yPct: 84.52 },
    { xPct: 65.27, yPct: 84.55 },
  ],
  hood_q9: [
    { xPct: 74.02, yPct: 60.10 },
    { xPct: 78.06, yPct: 54.79 },
    { xPct: 82.09, yPct: 60.10 },
    { xPct: 80.59, yPct: 69.26 },
    { xPct: 75.52, yPct: 69.29 },
  ],
  hood_q10: [
    { xPct: 80.48, yPct: 38.57 },
    { xPct: 84.47, yPct: 33.26 },
    { xPct: 88.55, yPct: 38.57 },
    { xPct: 87.05, yPct: 47.83 },
    { xPct: 81.93, yPct: 47.86 },
  ],
};

export const EASY_PRICE_DEN_POSITION: Point = { xPct: 23.23, yPct: 40.45 };

export const EASY_PRICE_DEN_SLOT_POSITION: Point[] = [
  { xPct: 20.81, yPct: 33.38 },
  { xPct: 25.43, yPct: 33.34 },
  { xPct: 27.59, yPct: 40.27 },
  { xPct: 25.53, yPct: 47.74 },
  { xPct: 21.12, yPct: 47.41 },
  { xPct: 18.88, yPct: 40.59 },
];

export const EASY_PRICE_JAIL_CENTER: Point = { xPct: 83.25, yPct: 83.91 };

// slot index (0-3) -> the disc printed with that number plus one (1 left, 2 bottom, 3 top, 4 right).
export const EASY_PRICE_JAIL_SLOT_POSITION: Point[] = [
  { xPct: 78.29, yPct: 83.99 },
  { xPct: 83.27, yPct: 89.24 },
  { xPct: 83.28, yPct: 78.57 },
  { xPct: 88.22, yPct: 83.82 },
];

// The three turn circles, 1.12% right of where the other boards have them (measured on both images).
export const EASY_PRICE_TURN_TRACK_POSITION: Record<number, Point> = {
  1: { xPct: 95.71, yPct: 6.07 },
  2: { xPct: 95.71, yPct: 13.57 },
  3: { xPct: 95.71, yPct: 21.08 },
};
