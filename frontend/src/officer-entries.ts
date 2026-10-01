import { HOOD_POSITION, SPOT_POSITION, officerBadgePoint, type Point } from './board-layout';
import type { GameEventResponse, GameViewResponse } from './types';

export const OFFICER_ENTRY_DURATION_MS = 450;

export interface OfficerEntry {
  id: string;
  officerId: string;
  officerType: 'cop' | 'fed';
  destination: Point;
}

export interface OfficerPurchase {
  id: string;
  officerId: string;
  officerType: 'cop' | 'fed';
  from: Point | null;
  fromPlayerId: string | null;
  to: Point | null;
  toPlayerId: string | null;
}

export function buildOfficerPurchases(
  events: GameEventResponse[],
  priorView: GameViewResponse,
  view: GameViewResponse,
): OfficerPurchase[] {
  const before = new Map(priorView.officers.map((officer) => [officer.officer_id, officer]));
  const after = new Map(view.officers.map((officer) => [officer.officer_id, officer]));
  return events.flatMap((event) => {
    if (event.event_type !== 'OfficerBought') return [];
    const officerId = event.officer_id as string;
    const prior = before.get(officerId);
    const current = after.get(officerId);
    if (!prior || !current) return [];
    const fromPile = prior.hood_id ? HOOD_POSITION[prior.hood_id]
      : prior.spot_id ? SPOT_POSITION[prior.spot_id] : null;
    const toPile = current.hood_id ? HOOD_POSITION[current.hood_id]
      : current.spot_id ? SPOT_POSITION[current.spot_id] : null;
    return [{
      id: event.event_id,
      officerId,
      officerType: current.officer_type === 'fed' ? 'fed' as const : 'cop' as const,
      from: fromPile ? officerBadgePoint(fromPile) : null,
      fromPlayerId: prior.owner_player_id,
      to: toPile ? officerBadgePoint(toPile) : null,
      toPlayerId: current.owner_player_id,
    }];
  });
}

// Animate actual reserve entries, keeping setup/load and already-present
// officers still. An officer removed again in this segment has no arrival.
export function buildOfficerEntries(
  events: GameEventResponse[],
  view: GameViewResponse,
): OfficerEntry[] {
  const entries = new Map<string, OfficerEntry>();
  const officers = new Map(view.officers.map((officer) => [officer.officer_id, officer]));
  for (const event of events) {
    if (event.event_type !== 'CopEnteredHood' && event.event_type !== 'FedEnteredSpot') continue;
    const officerId = event.officer_id as string;
    const officer = officers.get(officerId);
    if (!officer) continue;
    const destination = officer.hood_id ? HOOD_POSITION[officer.hood_id]
      : officer.spot_id ? SPOT_POSITION[officer.spot_id] : undefined;
    if (!destination) continue;
    if (officer.hood_id && !view.hoods.some((h) => h.hood_id === officer.hood_id && h.revealed)) continue;
    entries.set(officerId, {
      id: event.event_id,
      officerId,
      officerType: officer.officer_type === 'fed' ? 'fed' : 'cop',
      destination,
    });
  }
  return [...entries.values()];
}
