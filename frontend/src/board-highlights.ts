import type { GameEventResponse } from './types';

// What to make flash on the board for a moment when a step's result is revealed
// (game designer, 2026-10-16): the price tokens that moved and the launched Poker card.
export interface BoardHighlights {
  priceDopeTypes: string[];
  pokerCard: boolean;
}

export const BOARD_HIGHLIGHT_MS = 2400;

export function buildBoardHighlights(events: GameEventResponse[]): BoardHighlights | undefined {
  const priceDopeTypes = Array.from(new Set(
    events.filter((e) => e.event_type === 'PriceChanged').map((e) => e.dope_type as string),
  ));
  const pokerCard = events.some((e) => e.event_type === 'PokerLaunched');
  if (priceDopeTypes.length === 0 && !pokerCard) return undefined;
  return { priceDopeTypes, pokerCard };
}
