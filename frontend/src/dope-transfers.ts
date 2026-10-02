import {
  HOOD_POSITION, JAIL_SLOT_POSITION, PLAYER_BASE_POINT, SPOT_POSITION, type Point,
} from './board-layout';
import type { GameEventResponse, GameViewResponse } from './types';

export const DOPE_TRANSFER_DURATION_MS = 800;

export interface DopeTransfer {
  id: string;
  dopeType: string;
  from: Point;
  to: Point;
  destination: 'base' | 'spot' | 'jail';
  destinationId: string;
  playerId?: string;
  count: number;
}

// Use events rather than inventory differences: a purchase can restock a Hood
// and a sale can clear a Spot in the same response, hiding the transfer entirely.
export function buildDopeTransfers(
  events: GameEventResponse[],
  priorView: GameViewResponse,
): DopeTransfer[] {
  const transfers: DopeTransfer[] = [];
  const officerPoints = new Map<string, Point>();
  for (const officer of priorView.officers) {
    const point = officer.hood_id ? HOOD_POSITION[officer.hood_id]
      : officer.spot_id ? SPOT_POSITION[officer.spot_id] : undefined;
    if (point) officerPoints.set(officer.officer_id, point);
  }
  let confiscations: GameEventResponse[] = [];

  function add(
    event: GameEventResponse,
    from: Point | undefined,
    to: Point | undefined,
    destination: DopeTransfer['destination'],
    destinationId: string,
    playerId?: string,
  ) {
    if (!from || !to) return;
    const dopeType = event.dope_type as string;
    const existing = transfers.find((t) => t.dopeType === dopeType
      && t.from.xPct === from.xPct && t.from.yPct === from.yPct
      && t.destination === destination && t.destinationId === destinationId);
    if (existing) existing.count++;
    else transfers.push({ id: event.event_id, dopeType, from, to, destination, destinationId, playerId, count: 1 });
  }

  for (const event of events) {
    switch (event.event_type) {
      case 'DopeBought':
        add(event, HOOD_POSITION[event.hood_id as string], PLAYER_BASE_POINT[event.player_id as string],
          'base', event.player_id as string, event.player_id as string);
        break;
      case 'DopeSold':
        add(event, PLAYER_BASE_POINT[event.player_id as string], SPOT_POSITION[event.spot_id as string],
          'spot', event.spot_id as string, event.player_id as string);
        break;
      case 'DopeRecovered':
        // Evasion / Rat release: the slot's confiscated Dope flies from
        // the Jail slot to its owner's Covo, like a purchase does from a Hood.
        add(event, JAIL_SLOT_POSITION[event.jail_slot_index as number],
          PLAYER_BASE_POINT[event.player_id as string],
          'base', event.player_id as string, event.player_id as string);
        break;
      case 'OfficerMoved':
      case 'CopEnteredHood':
      case 'FedEnteredSpot': {
        const point = event.hood_id ? HOOD_POSITION[event.hood_id as string]
          : SPOT_POSITION[event.spot_id as string];
        if (point) officerPoints.set(event.officer_id as string, point);
        break;
      }
      case 'DopeConfiscated':
        confiscations.push(event);
        break;
      case 'CorruptionActionApplied':
        // The action summary follows its confiscation events. Keep the officer's
        // last position even if emptying the Hood has sent it back to reserve.
        if (event.action === 'confiscate') {
          for (const confiscation of confiscations) {
            const slot = confiscation.jail_slot_index as number;
            add(confiscation, officerPoints.get(event.officer_id as string), JAIL_SLOT_POSITION[slot],
              'jail', String(slot));
          }
        }
        confiscations = [];
        break;
    }
  }
  return transfers;
}
