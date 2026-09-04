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

// Jail redesigned from 6 slots to 4 on the new board art (BOARD_v15_
// GODOPE_4.webp, 2026-09-02) — position shifted too, not just the count;
// re-measured directly against the new image (blob-detecting the 4 dark
// circles), same technique as the Job grid below.
export const JAIL_CENTER: Point = { xPct: 85.05, yPct: 78.1 };

// slot index (0-3, matches PublicJailSlotResponse.index) -> position.
// The board art itself prints "1".."4" on the 4 circles, taken as the
// authoritative index->position mapping (index 0 = the circle printed
// "1", etc.) rather than an assumed reading order.
export const JAIL_SLOT_POSITION: Point[] = [
  { xPct: 87.5, yPct: 88.8 },
  { xPct: 82.68, yPct: 83.42 },
  { xPct: 82.63, yPct: 72.79 },
  { xPct: 87.41, yPct: 67.4 },
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

// dope_type -> { price -> position } for each price on that Dope's own
// track (right edge of the board, one wheel per type) — matches
// data/dope_types.json's price_track values exactly (confirmed by
// reading each track's printed numbers against the data file, 2026-08-14).
// Placing the type's own token (assets/index.ts::PRICE_TOKEN_ASSET) at
// current_price_by_dope_type[type] replaces a separate price table.
// Re-measured 2026-08-15 after the designer flagged the tokens as
// off-center: the earlier manual crop-reading pass (a uniform +0.7/+0.7
// "best guess" correction, never independently re-verified — see the
// class-level history) was wrong by up to ~1-2% on several entries.
// Redone by cropping a single frame around each dial wide enough to show
// several of its number-circles at once, overlaying a crosshair at the
// candidate point, and reading the true circle center directly off that
// image (checked against a second, independently-seeded crop wherever two
// dials' numbers shared a frame — every entry agreed within ~0.3%).
export const PRICE_TOKEN_POSITION: Record<string, Record<number, Point>> = {
  rana: {
    0: { xPct: 93.31, yPct: 32.174 },
    1: { xPct: 92.115, yPct: 35.176 },
    3: { xPct: 92.79, yPct: 39.02 },
    5: { xPct: 93.365, yPct: 42.282 },
  },
  camaleonte: {
    2: { xPct: 93.969, yPct: 47.605 },
    3: { xPct: 92.698, yPct: 50.671 },
    4: { xPct: 92.34, yPct: 53.99 },
    6: { xPct: 92.63, yPct: 57.19 },
    8: { xPct: 93.84, yPct: 60.23 },
  },
  polpo: {
    3: { xPct: 94.365, yPct: 62.763 },
    4: { xPct: 92.875, yPct: 65.55 },
    5: { xPct: 92.646, yPct: 68.508 },
    7: { xPct: 92.51, yPct: 72.012 },
    9: { xPct: 92.906, yPct: 75.166 },
    11: { xPct: 94.729, yPct: 76.377 },
  },
  gufo: {
    4: { xPct: 94.898, yPct: 79.865 },
    6: { xPct: 93.43, yPct: 81.592 },
    8: { xPct: 92.45, yPct: 83.844 },
    10: { xPct: 92.24, yPct: 87.147 },
    12: { xPct: 92.52, yPct: 89.85 },
    14: { xPct: 93.81, yPct: 92.6 },
  },
};

// The board's own printed "1/2/3" turn track, top-right corner — keyed by
// GameViewResponse.turn_index (1-based, matches game_config.json's
// num_turns: 3 and the board's own "R1/R2/R3" labels). Read the same way
// as PRICE_TOKEN_POSITION above: crop tight around the track, overlay a
// crosshair at the candidate point, confirm it lands centered on the
// printed circle. First pass (2026-08-24) was visibly off-center in the
// real browser (designer's report) — re-measured at 4x zoom against each
// circle's own true edges (a coarser 25px-grid read had been off by
// ~20-25px); re-verified all three land centered this time.
export const TURN_TRACK_POSITION: Record<number, Point> = {
  1: { xPct: 94.594, yPct: 6.066 },
  2: { xPct: 94.594, yPct: 13.574 },
  3: { xPct: 94.594, yPct: 21.081 },
};

// The single "GAMBLE" launch slot, top-left of the board (2026-09-04
// redesign: one shared Gamble slot per action round, replacing the old
// 2-slots-per-turn layout) — the round's own launched match's Gamble
// card, if any, is shown here. Uses the old layout's *second* slot
// position (user's call, 2026-09-04) rather than the first.
export const GAMBLE_SLOT_POSITION: Point[] = [{ xPct: 12.7, yPct: 14 }];

// The physical Job board grid, top-left of the board, below the GAMBLE
// panel: 9 rows x 4 columns (game_config.json's job_board_column_bonuses:
// skill/link/two_cards/money). A completed Job's REP token goes in
// [job_id][column_index]. Rows are now grouped by tier on the new board
// art (BOARD_v15_GODOPE_4.webp, 2026-09-02), each group visibly separated
// by a gap — no longer a straight job_01..job_09 sequence, so row order
// is this explicit list rather than a generated `job_0{n}` sequence (a
// Job's board row was never actually derived from jobs.json's own file
// order, just from job_id's numeric suffix — this replaces that
// assumption entirely, so re-ordering jobs.json alone would do nothing
// without this list matching it). Measured directly from the new board
// art (blob-detecting each cell's white square outline, same technique
// as before — jobs.json's own tier field: job_01/02/07 tier 1, job_04/
// 05/06 tier 2, job_03/08/09 tier 3).
const JOB_BOARD_ROW_ORDER = [
  'job_01',
  'job_02',
  'job_07',
  'job_04',
  'job_05',
  'job_06',
  'job_03',
  'job_08',
  'job_09',
];
// Column 4's own x was originally measured with a crop that clipped its
// right edge (found and corrected 2026-09-02: REP tokens there rendered
// visibly left of center) — 803.5/8070, not the truncated box's 748.5/8070.
const JOB_BOARD_COLUMN_X = [1.617, 4.405, 7.181, 9.957];
const JOB_BOARD_ROW_Y = [37.75, 43.464, 49.226, 58.226, 63.94, 69.702, 78.726, 84.44, 90.202];
export const JOB_BOARD_CELL_POSITION: Record<string, Point[]> = Object.fromEntries(
  JOB_BOARD_ROW_ORDER.map((jobId, rowIndex) => [
    jobId,
    JOB_BOARD_COLUMN_X.map((xPct) => ({ xPct, yPct: JOB_BOARD_ROW_Y[rowIndex] })),
  ]),
);

const MONEY_TRACK_Y = 96.6;
const MONEY_TRACK_X0 = 2.19;
const MONEY_TRACK_STEP = 3.11;

// Each money-track cell's own rounded-square box, measured directly
// against the board art (2026-08-16, same pixel-scan technique as the Job
// grid above): ~82px wide x ~81px tall at (3200x1665). Exposed so a cash
// marker can be sized to fill the cell exactly (designer's request:
// "ogni token occupa tutta la larghezza della casella cash e 1/4 della
// altezza") instead of being a small centered icon.
export const MONEY_CELL_WIDTH = 2.6;
export const MONEY_CELL_HEIGHT = 4.9;
export const MONEY_CELL_TOP = 94.8;

// Money track only prints $0-30 (31 cells) on the board. Past $30 the
// marker wraps back to cell 0 and switches to its "+30" variant (see
// assets/index.ts's moneyMarkerAssetForPlayer) rather than clamping to the
// last cell — designer's request, 2026-08-16.
export function moneyTrackLap(amount: number): number {
  return Math.floor(Math.max(0, amount) / 31);
}

export function moneyTrackPosition(amount: number): Point {
  const position = Math.max(0, amount) % 31;
  return { xPct: MONEY_TRACK_X0 + position * MONEY_TRACK_STEP, yPct: MONEY_TRACK_Y };
}
