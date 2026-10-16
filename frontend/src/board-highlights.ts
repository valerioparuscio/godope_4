import type { GameEventResponse, GameViewResponse } from './types';

// What to make flash on the board for a moment when a step's result is revealed
// (game designer, 2026-10-16): the price tokens that moved — shown sliding slowly from the
// old price to the new one while they flash — and the launched Poker card.
export interface BoardHighlights {
  // Dope type -> the price its token was at before the step.
  priceFrom: Record<string, number>;
  pokerCard: boolean;
}

export const BOARD_HIGHLIGHT_MS = 3000;

export function buildBoardHighlights(
  events: GameEventResponse[],
  priorView: GameViewResponse,
): BoardHighlights | undefined {
  const priceFrom: Record<string, number> = {};
  for (const event of events) {
    if (event.event_type !== 'PriceChanged') continue;
    const dopeType = event.dope_type as string;
    const before = priorView.current_price_by_dope_type[dopeType];
    if (before !== undefined) priceFrom[dopeType] = before;
  }
  const pokerCard = events.some((e) => e.event_type === 'PokerLaunched');
  if (Object.keys(priceFrom).length === 0 && !pokerCard) return undefined;
  return { priceFrom, pokerCard };
}
