// Percentage-of-image coordinates (0-100, relative to BOARD_BACKGROUND's
// own width/height) for every interactive/markable region on the board
// art. Measured against frontend/src/assets/board/BOARD_v14_b.png
// (8070x4200) by cropping+gridding the image and cross-checking each
// mark against the actual artwork — see scratchpad script history,
// 2026-08-02. Keep this file as the one place to touch if the board art
// is ever replaced/repositioned; components should never hardcode a %.
//
// HOOD_POSITION corrected 2026-08-03: the original pass (eyeballed off a
// gridded screenshot) was off by 1-5% on several hoods — enough to miss
// the small petal circles entirely, reported by the game designer after
// playtesting. Re-measured programmatically: flood-fill each hood's
// interior outward from the old estimate, bounded by the flower's own
// white outline stroke (a consistent, distinctive edge regardless of the
// hood's own color), then take the filled region's centroid — immune to
// the eyeballing error that caused the original numbers, and verified
// visually afterwards (crosshair crops) against every one of the 10.

export interface Point {
  xPct: number;
  yPct: number;
}

// hood_id -> center of its 5-petal criminal ring / central dope pile.
export const HOOD_POSITION: Record<string, Point> = {
  hood_q1: { xPct: 23.28, yPct: 67.28 },
  hood_q2: { xPct: 35.15, yPct: 79.87 },
  hood_q3: { xPct: 36.37, yPct: 44.31 },
  hood_q4: { xPct: 44.96, yPct: 64.06 },
  hood_q5: { xPct: 50.0, yPct: 40.97 },
  hood_q6: { xPct: 53.91, yPct: 83.4 },
  hood_q7: { xPct: 60.75, yPct: 58.04 },
  hood_q8: { xPct: 67.96, yPct: 78.01 },
  hood_q9: { xPct: 73.49, yPct: 55.16 },
  hood_q10: { xPct: 84.19, yPct: 39.95 },
};

// A hood's 5 petals, as offsets from HOOD_POSITION's center, for placing
// up to 5 criminal pawns. Order is arbitrary (petal index has no game
// meaning) — index 0 = top, then clockwise.
export const HOOD_PETAL_OFFSET: Point[] = [
  { xPct: 0, yPct: -8.9 },
  { xPct: 7.2, yPct: -3.8 },
  { xPct: 5.3, yPct: 5.5 },
  { xPct: -5.3, yPct: 5.5 },
  { xPct: -7.2, yPct: -3.8 },
];

export const DEN_POSITION: Point = { xPct: 23.3, yPct: 41.0 };

export const JAIL_CENTER: Point = { xPct: 82.5, yPct: 72.7 };

// slot index (0-5, matches PublicJailSlotResponse.index) -> position.
export const JAIL_SLOT_POSITION: Point[] = [
  { xPct: 82.5, yPct: 64.0 },
  { xPct: 87.4, yPct: 68.2 },
  { xPct: 87.4, yPct: 78.1 },
  { xPct: 82.5, yPct: 82.6 },
  { xPct: 77.3, yPct: 78.1 },
  { xPct: 77.3, yPct: 68.2 },
];

// contact_id -> its 3 Link-level slot centers (the "●→●●→●●●" track under
// each Contact's header), index 0 = level 1 .. index 2 = level 3. These 3
// slots are shared by all players (a level holds at most one pawn at a
// time — RULES_CANONICAL.md, confirmed 2026-08-02 the Link track isn't
// per-player), so a single position per level is enough.
const LINK_TRACK_Y = 11.7;
const LINK_LEVEL_STEP_X = 5.0;
const CONTACT_LINK1_X: Record<string, number> = {
  artisti: 20.76,
  studenti: 35.65,
  manager: 50.53,
  preti: 65.42,
  politici: 80.3,
};

export const CONTACT_LINK_SLOT_POSITION: Record<string, Point[]> = Object.fromEntries(
  Object.entries(CONTACT_LINK1_X).map(([contactId, x1]) => [
    contactId,
    [0, 1, 2].map((i) => ({ xPct: x1 + i * LINK_LEVEL_STEP_X, yPct: LINK_TRACK_Y })),
  ]),
);

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
