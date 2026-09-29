import { HOOD_POSITION, SPOT_POSITION, type Point } from './board-layout';
import type { GameEventResponse, GameViewResponse } from './types';

export const OFFICER_ENTRY_DURATION_MS = 450;

export interface OfficerEntry {
  id: string;
  officerId: string;
  officerType: 'cop' | 'fed';
  destination: Point;
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
