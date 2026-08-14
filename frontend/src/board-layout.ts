// Percentage-of-image coordinates (0-100, relative to BOARD_BACKGROUND's
// own width/height) for every interactive/markable region on the board
// art. Keep this file as the one place to touch if the board art is ever
// replaced/repositioned; components should never hardcode a %.
//
// Re-measured 2026-08-14 from the game designer's own calibration overlay
// (frontend/src/assets/board/board_calibration.png — a copy of the board
// with a yellow circle hand-placed on every pawn slot: 50 Hood petals, 6
// Jail, 6 Den, 15 Link-track). Detected programmatically (flood-fill on
// the marker color, connected-component centroids) rather than eyeballed
// — the prior eyeballed pass was off by enough to miss the small petal
// circles entirely. Every Hood's 5 petals now measure identical radii
// from their own centroid (4.86/7.98/4.89/7.09/7.19, matching to within
// 0.01% across all 10) — strong confirmation the flower art is uniform
// and this data is internally consistent.

export interface Point {
  xPct: number;
  yPct: number;
}

// hood_id -> center of its central dope-pile circle (centroid of its own
// 5 petals below, so it's exactly consistent with them).
export const HOOD_POSITION: Record<string, Point> = {
  hood_q1: { xPct: 23.18, yPct: 67.16 },
  hood_q2: { xPct: 35.06, yPct: 79.61 },
  hood_q3: { xPct: 36.65, yPct: 45.66 },
  hood_q4: { xPct: 45.66, yPct: 65.21 },
  hood_q5: { xPct: 50.01, yPct: 41.35 },
  hood_q6: { xPct: 53.97, yPct: 83.56 },
  hood_q7: { xPct: 60.68, yPct: 58.37 },
  hood_q8: { xPct: 67.85, yPct: 77.9 },
  hood_q9: { xPct: 73.84, yPct: 55.25 },
  hood_q10: { xPct: 84.57, yPct: 41.18 },
};

// hood_id -> its 5 petal centers (absolute positions, not offsets — the
// designer's calibration marks each one directly). Order is arbitrary
// (petal index has no game meaning), just consistent per hood.
export const HOOD_PETAL_POSITION: Record<string, Point[]> = {
  hood_q1: [
    { xPct: 19.11, yPct: 64.49 },
    { xPct: 23.1, yPct: 59.18 },
    { xPct: 27.28, yPct: 64.49 },
    { xPct: 25.78, yPct: 73.75 },
    { xPct: 20.61, yPct: 73.87 },
  ],
  hood_q2: [
    { xPct: 31.0, yPct: 76.94 },
    { xPct: 34.99, yPct: 71.63 },
    { xPct: 39.16, yPct: 76.94 },
    { xPct: 37.66, yPct: 86.2 },
    { xPct: 32.5, yPct: 86.32 },
  ],
  hood_q3: [
    { xPct: 32.58, yPct: 42.99 },
    { xPct: 36.57, yPct: 37.68 },
    { xPct: 40.75, yPct: 42.99 },
    { xPct: 39.25, yPct: 52.25 },
    { xPct: 34.08, yPct: 52.37 },
  ],
  hood_q4: [
    { xPct: 41.59, yPct: 62.54 },
    { xPct: 45.58, yPct: 57.23 },
    { xPct: 49.76, yPct: 62.54 },
    { xPct: 48.26, yPct: 71.8 },
    { xPct: 43.09, yPct: 71.92 },
  ],
  hood_q5: [
    { xPct: 45.94, yPct: 38.68 },
    { xPct: 49.93, yPct: 33.37 },
    { xPct: 54.11, yPct: 38.68 },
    { xPct: 52.61, yPct: 47.94 },
    { xPct: 47.44, yPct: 48.06 },
  ],
  hood_q6: [
    { xPct: 49.91, yPct: 80.89 },
    { xPct: 53.9, yPct: 75.58 },
    { xPct: 58.07, yPct: 80.89 },
    { xPct: 56.57, yPct: 90.16 },
    { xPct: 51.41, yPct: 90.27 },
  ],
  hood_q7: [
    { xPct: 56.61, yPct: 55.7 },
    { xPct: 60.6, yPct: 50.39 },
    { xPct: 64.78, yPct: 55.7 },
    { xPct: 63.28, yPct: 64.96 },
    { xPct: 58.11, yPct: 65.08 },
  ],
  hood_q8: [
    { xPct: 63.79, yPct: 75.23 },
    { xPct: 67.78, yPct: 69.92 },
    { xPct: 71.95, yPct: 75.23 },
    { xPct: 70.45, yPct: 84.49 },
    { xPct: 65.28, yPct: 84.61 },
  ],
  hood_q9: [
    { xPct: 69.77, yPct: 52.58 },
    { xPct: 73.76, yPct: 47.27 },
    { xPct: 77.94, yPct: 52.58 },
    { xPct: 76.44, yPct: 61.84 },
    { xPct: 71.27, yPct: 61.96 },
  ],
  hood_q10: [
    { xPct: 80.5, yPct: 38.51 },
    { xPct: 84.49, yPct: 33.2 },
    { xPct: 88.67, yPct: 38.51 },
    { xPct: 87.17, yPct: 47.77 },
    { xPct: 82.0, yPct: 47.89 },
  ],
};

export const DEN_POSITION: Point = { xPct: 23.26, yPct: 41.34 };

// The Den's own 6 gambler slots (absolute positions, same calibration
// source as everything else here — not a computed circle).
export const DEN_SLOT_POSITION: Point[] = [
  { xPct: 20.95, yPct: 34.2 },
  { xPct: 25.47, yPct: 34.16 },
  { xPct: 27.63, yPct: 41.18 },
  { xPct: 25.52, yPct: 48.56 },
  { xPct: 21.11, yPct: 48.42 },
  { xPct: 18.87, yPct: 41.51 },
];

export const JAIL_CENTER: Point = { xPct: 82.5, yPct: 77.18 };

// slot index (0-5, matches PublicJailSlotResponse.index) -> position.
export const JAIL_SLOT_POSITION: Point[] = [
  { xPct: 82.42, yPct: 66.47 },
  { xPct: 87.4, yPct: 71.89 },
  { xPct: 87.44, yPct: 82.39 },
  { xPct: 82.53, yPct: 87.94 },
  { xPct: 77.56, yPct: 82.56 },
  { xPct: 77.65, yPct: 71.84 },
];

// spot_id -> its dope-pile marker, in the Contact header's own "which 2
// Dope types this Contact's Spots accept" icon row (the board draws no
// separate Spot shape elsewhere — this row *is* where each Spot's stock
// is shown). Order/identity cross-checked against data/contacts.json's
// spot_id -> accepted_dope_type (left icon = *_1, right icon = *_2 for
// every Contact, confirmed by matching each icon's own dope type against
// the data file).
export const SPOT_POSITION: Record<string, Point> = {
  spot_artisti_1: { xPct: 20.67, yPct: 22.71 },
  spot_artisti_2: { xPct: 27.57, yPct: 22.76 },
  spot_studenti_1: { xPct: 35.53, yPct: 22.76 },
  spot_studenti_2: { xPct: 42.43, yPct: 22.81 },
  spot_manager_1: { xPct: 50.59, yPct: 22.71 },
  spot_manager_2: { xPct: 57.5, yPct: 22.76 },
  spot_preti_1: { xPct: 65.43, yPct: 22.9 },
  spot_preti_2: { xPct: 72.33, yPct: 22.95 },
  spot_politici_1: { xPct: 80.32, yPct: 22.76 },
  spot_politici_2: { xPct: 87.22, yPct: 22.81 },
};

// contact_id -> its 3 Link-level slot centers (the "●→●●→●●●" track under
// each Contact's header), index 0 = level 1 .. index 2 = level 3. These 3
// slots are shared by all players (a level holds at most one pawn at a
// time — RULES_CANONICAL.md, confirmed 2026-08-02 the Link track isn't
// per-player), so a single position per level is enough.
export const CONTACT_LINK_SLOT_POSITION: Record<string, Point[]> = {
  artisti: [
    { xPct: 19.4, yPct: 13.25 },
    { xPct: 24.31, yPct: 13.3 },
    { xPct: 29.46, yPct: 13.46 },
  ],
  studenti: [
    { xPct: 34.17, yPct: 13.2 },
    { xPct: 39.08, yPct: 13.25 },
    { xPct: 44.23, yPct: 13.42 },
  ],
  manager: [
    { xPct: 49.05, yPct: 13.2 },
    { xPct: 53.96, yPct: 13.25 },
    { xPct: 59.12, yPct: 13.42 },
  ],
  preti: [
    { xPct: 63.91, yPct: 13.11 },
    { xPct: 68.82, yPct: 13.16 },
    { xPct: 73.97, yPct: 13.32 },
  ],
  politici: [
    { xPct: 78.79, yPct: 13.25 },
    { xPct: 83.7, yPct: 13.3 },
    { xPct: 88.85, yPct: 13.46 },
  ],
};

// The two "GAMBLE" launch slots, top-left of the board (matches
// game_config.json's poker_max_matches_per_turn: 2) — a launched match's
// Gamble card is shown here, in launch order (index 0 = left/first).
export const GAMBLE_SLOT_POSITION: Point[] = [
  { xPct: 4.3, yPct: 14 },
  { xPct: 12.7, yPct: 14 },
];

const MONEY_TRACK_Y = 96.6;
const MONEY_TRACK_X0 = 2.19;
const MONEY_TRACK_STEP = 3.11;

// Money track only prints 0-30 on the board; higher amounts clamp to the
// last cell rather than running off the art.
export function moneyTrackPosition(amount: number): Point {
  const clamped = Math.max(0, Math.min(30, amount));
  return { xPct: MONEY_TRACK_X0 + clamped * MONEY_TRACK_STEP, yPct: MONEY_TRACK_Y };
}
