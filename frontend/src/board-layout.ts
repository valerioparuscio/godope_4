// Percentage-of-image coordinates (0-100, relative to BOARD_BACKGROUND's
// own width/height) for every interactive/markable region on the board
// art. Measured against frontend/src/assets/board/BOARD_v14_b.png
// (8070x4200) by cropping+gridding the image and cross-checking each
// mark against the actual artwork — see scratchpad script history,
// 2026-08-02. Keep this file as the one place to touch if the board art
// is ever replaced/repositioned; components should never hardcode a %.

export interface Point {
  xPct: number;
  yPct: number;
}

// hood_id -> center of its 5-petal criminal ring / central dope pile.
export const HOOD_POSITION: Record<string, Point> = {
  hood_q1: { xPct: 23.6, yPct: 62.6 },
  hood_q2: { xPct: 35.4, yPct: 78.2 },
  hood_q3: { xPct: 36.5, yPct: 44.0 },
  hood_q4: { xPct: 44.7, yPct: 64.1 },
  hood_q5: { xPct: 50.0, yPct: 40.0 },
  hood_q6: { xPct: 53.75, yPct: 80.5 },
  hood_q7: { xPct: 60.8, yPct: 57.0 },
  hood_q8: { xPct: 68.9, yPct: 75.7 },
  hood_q9: { xPct: 73.5, yPct: 54.7 },
  hood_q10: { xPct: 83.8, yPct: 38.7 },
};

// A hood's 5 petals, as offsets from HOOD_POSITION's center, for placing
// up to 5 criminal pawns. Order is arbitrary (petal index has no game
// meaning) — index 0 = top, then clockwise.
export const HOOD_PETAL_OFFSET: Point[] = [
  { xPct: 0, yPct: -5.8 },
  { xPct: 4.8, yPct: -1.8 },
  { xPct: 3.0, yPct: 4.6 },
  { xPct: -3.0, yPct: 4.6 },
  { xPct: -4.8, yPct: -1.8 },
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

const MONEY_TRACK_Y = 96.6;
const MONEY_TRACK_X0 = 2.19;
const MONEY_TRACK_STEP = 3.11;

// Money track only prints 0-30 on the board; higher amounts clamp to the
// last cell rather than running off the art.
export function moneyTrackPosition(amount: number): Point {
  const clamped = Math.max(0, Math.min(30, amount));
  return { xPct: MONEY_TRACK_X0 + clamped * MONEY_TRACK_STEP, yPct: MONEY_TRACK_Y };
}
