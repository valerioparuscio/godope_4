// GENERATED from BOARD_v16_GODOPE_4_light_MARKER.png (game designer's marked
// copy of the light board, 2026-10-09; blob centroids of the red / yellow /
// magenta markers) by a one-off script — see board-layout.ts's `applyBoardLayout`.
// The Job grid, money track, Gamble slot and header panels were measured
// directly off BOARD_v16_GODOPE_4_LIGHT.webp (the Gamble slot is an estimate:
// the marked copy has no marker there).
import type { Point } from './board-layout';

export const SIMPLE_HOOD_POSITION: Record<string, Point> = {
  hood_q1: { xPct: 32.76, yPct: 45.1 },
  hood_q2: { xPct: 33.19, yPct: 80.79 },
  hood_q3: { xPct: 46.98, yPct: 42.72 },
  hood_q4: { xPct: 46.7, yPct: 71.57 },
  hood_q5: { xPct: 62.05, yPct: 51.6 },
  hood_q6: { xPct: 59.28, yPct: 82.26 },
  hood_q7: { xPct: 76.02, yPct: 43.55 },
  hood_q8: { xPct: 76.46, yPct: 81.0 },
};

export const SIMPLE_HOOD_PETAL_POSITION: Record<string, Point[]> = {
  hood_q1: [
    { xPct: 37.31, yPct: 42.02 },
    { xPct: 35.65, yPct: 52.29 },
    { xPct: 29.96, yPct: 52.5 },
    { xPct: 28.28, yPct: 42.07 },
    { xPct: 32.74, yPct: 36.17 },
  ],
  hood_q2: [
    { xPct: 33.28, yPct: 71.83 },
    { xPct: 37.86, yPct: 77.69 },
    { xPct: 36.2, yPct: 87.95 },
    { xPct: 30.51, yPct: 88.17 },
    { xPct: 28.82, yPct: 77.74 },
  ],
  hood_q3: [
    { xPct: 51.44, yPct: 39.6 },
    { xPct: 49.78, yPct: 49.86 },
    { xPct: 44.09, yPct: 50.07 },
    { xPct: 42.4, yPct: 39.64 },
    { xPct: 46.87, yPct: 33.74 },
  ],
  hood_q4: [
    { xPct: 46.7, yPct: 62.57 },
    { xPct: 51.28, yPct: 68.43 },
    { xPct: 49.62, yPct: 78.69 },
    { xPct: 43.93, yPct: 78.91 },
    { xPct: 42.24, yPct: 68.48 },
  ],
  hood_q5: [
    { xPct: 66.41, yPct: 48.57 },
    { xPct: 64.75, yPct: 58.83 },
    { xPct: 59.06, yPct: 59.05 },
    { xPct: 57.37, yPct: 48.62 },
    { xPct: 61.83, yPct: 42.72 },
  ],
  hood_q6: [
    { xPct: 63.83, yPct: 79.19 },
    { xPct: 62.17, yPct: 89.45 },
    { xPct: 56.48, yPct: 89.67 },
    { xPct: 54.8, yPct: 79.24 },
    { xPct: 59.26, yPct: 73.33 },
  ],
  hood_q7: [
    { xPct: 80.5, yPct: 40.55 },
    { xPct: 78.83, yPct: 50.81 },
    { xPct: 73.15, yPct: 51.02 },
    { xPct: 71.46, yPct: 40.59 },
    { xPct: 75.92, yPct: 34.69 },
  ],
  hood_q8: [
    { xPct: 80.86, yPct: 77.91 },
    { xPct: 79.19, yPct: 88.17 },
    { xPct: 73.51, yPct: 88.38 },
    { xPct: 71.82, yPct: 77.95 },
    { xPct: 76.28, yPct: 72.05 },
  ],
};

export const SIMPLE_DEN_POSITION: Point = { xPct: 22.93, yPct: 63.02 };

export const SIMPLE_DEN_SLOT_POSITION: Point[] = [
  { xPct: 25.5, yPct: 54.74 },
  { xPct: 27.97, yPct: 62.76 },
  { xPct: 25.63, yPct: 71.55 },
  { xPct: 20.45, yPct: 71.33 },
  { xPct: 17.79, yPct: 63.09 },
  { xPct: 20.23, yPct: 54.67 },
];

export const SIMPLE_JAIL_CENTER: Point = { xPct: 94.25, yPct: 74.96 };

// index 0 = the circle printed "1" (bottom), as on the standard board.
export const SIMPLE_JAIL_SLOT_POSITION: Point[] = [
  { xPct: 96.98, yPct: 87.02 },
  { xPct: 91.59, yPct: 80.81 },
  { xPct: 91.51, yPct: 68.91 },
  { xPct: 96.93, yPct: 63.09 },
];

export const SIMPLE_SPOT_POSITION: Record<string, Point> = {
  spot_artisti_1: { xPct: 28.22, yPct: 22.81 },
  spot_artisti_2: { xPct: 35.18, yPct: 22.74 },
  spot_manager_1: { xPct: 43.09, yPct: 22.81 },
  spot_manager_2: { xPct: 50.05, yPct: 22.74 },
  spot_preti_1: { xPct: 58.04, yPct: 22.67 },
  spot_preti_2: { xPct: 65.01, yPct: 22.59 },
  spot_politici_1: { xPct: 73.0, yPct: 22.81 },
  spot_politici_2: { xPct: 79.96, yPct: 22.74 },
};

export const SIMPLE_CONTACT_HEADER_RECT: Record<string, Point & { widthPct: number; heightPct: number }> = {
  artisti: { xPct: 31.9, yPct: 5.1, widthPct: 14.5, heightPct: 9.9 },
  manager: { xPct: 46.75, yPct: 5.1, widthPct: 14.5, heightPct: 9.9 },
  preti: { xPct: 61.6, yPct: 5.1, widthPct: 14.5, heightPct: 9.9 },
  politici: { xPct: 76.5, yPct: 5.1, widthPct: 14.5, heightPct: 9.9 },
};

export const SIMPLE_CONTACT_LINK_SLOT_POSITION: Record<string, Point[]> = {
  artisti: [
    { xPct: 26.93, yPct: 13.31 },
    { xPct: 31.83, yPct: 13.17 },
    { xPct: 36.93, yPct: 13.38 },
  ],
  manager: [
    { xPct: 41.76, yPct: 13.38 },
    { xPct: 46.67, yPct: 13.24 },
    { xPct: 51.76, yPct: 13.45 },
  ],
  preti: [
    { xPct: 56.59, yPct: 13.45 },
    { xPct: 61.5, yPct: 13.31 },
    { xPct: 66.59, yPct: 13.52 },
  ],
  politici: [
    { xPct: 71.51, yPct: 13.31 },
    { xPct: 76.42, yPct: 13.17 },
    { xPct: 81.51, yPct: 13.38 },
  ],
};

export const SIMPLE_PRICE_TOKEN_POSITION: Record<string, Record<number, Point>> = {
  rana: {
    0: { xPct: 89.99, yPct: 5.79 },
    1: { xPct: 88.96, yPct: 8.86 },
    3: { xPct: 89.09, yPct: 12.6 },
    5: { xPct: 90.05, yPct: 15.93 },
  },
  camaleonte: {
    2: { xPct: 90.71, yPct: 22.0 },
    3: { xPct: 89.42, yPct: 24.38 },
    4: { xPct: 88.93, yPct: 27.91 },
    6: { xPct: 89.34, yPct: 31.45 },
    8: { xPct: 90.67, yPct: 33.88 },
  },
  gufo: {
    4: { xPct: 91.71, yPct: 38.69 },
    6: { xPct: 90.19, yPct: 40.09 },
    8: { xPct: 89.12, yPct: 42.62 },
    10: { xPct: 89.02, yPct: 45.79 },
    12: { xPct: 89.36, yPct: 48.93 },
    14: { xPct: 90.63, yPct: 51.19 },
  },
};

export const SIMPLE_TURN_TRACK_POSITION: Record<number, Point> = {
  1: { xPct: 20.19, yPct: 4.41 },
  2: { xPct: 20.24, yPct: 13.76 },
  3: { xPct: 20.19, yPct: 23.71 },
};

export const SIMPLE_GAMBLE_SLOT_POSITION: Point[] = [{ xPct: 11.6, yPct: 81.7 }];

// Job grid rows (centres of the three tier groups' cells), same columns as the standard board.
export const SIMPLE_JOB_BOARD_ROW_Y = [9.167, 14.881, 20.643, 29.643, 35.357, 41.119, 50.143, 55.857, 61.619];

// Centre x of each dial's Dope picture (Marketing +/- controls).
export const SIMPLE_MARKETING_CONTROL_X = 92.2;

// The light board's Hoods are about 10% bigger than the standard ones (game designer): Dope piles, Criminals and hidden-Hood covers on them scale with it.
export const SIMPLE_HOOD_SCALE = 1.1;
