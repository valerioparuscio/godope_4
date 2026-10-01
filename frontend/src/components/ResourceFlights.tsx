import { useLayoutEffect, useState, type CSSProperties } from 'react';
import { createPortal } from 'react-dom';
import { DOPE_ASSET, OFFICER_ASSET } from '../assets';
import type { Point } from '../board-layout';
import { DOPE_TRANSFER_DURATION_MS, type DopeTransfer } from '../dope-transfers';
import { type OfficerPurchase } from '../officer-entries';

interface Flight {
  id: string;
  src: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  size: number;
  count: number;
}

function center(rect: DOMRect) {
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
}

function boardPosition(board: DOMRect, point: Point | null) {
  if (!point) return null;
  return { x: board.left + board.width * point.xPct / 100,
    y: board.top + board.height * point.yPct / 100 };
}

function resourcePosition(playerId: string | null, resource: string) {
  if (!playerId) return null;
  const card = [...document.querySelectorAll<HTMLElement>('.app__sidebar .player-card')]
    .find((element) => element.dataset.playerId === playerId);
  const item = [...(card?.querySelectorAll<HTMLElement>('.player-card__stat-item') ?? [])]
    .find((element) => element.dataset.resourceKey === resource);
  const icon = item?.querySelector('img');
  return icon ? center(icon.getBoundingClientRect()) : null;
}

export function ResourceFlights({ dopeTransfers, officerPurchases }: {
  dopeTransfers: DopeTransfer[];
  officerPurchases: OfficerPurchase[];
}) {
  const [flights, setFlights] = useState<Flight[]>([]);

  useLayoutEffect(() => {
    const boardElement = document.querySelector('.app__play-area .board-view');
    if (!boardElement) return;
    const board = boardElement.getBoundingClientRect();
    const next: Flight[] = [];
    for (const transfer of dopeTransfers) {
      if (!transfer.playerId) continue;
      const from = transfer.destination === 'base'
        ? boardPosition(board, transfer.from)
        : resourcePosition(transfer.playerId, transfer.dopeType);
      const to = transfer.destination === 'base'
        ? resourcePosition(transfer.playerId, transfer.dopeType)
        : boardPosition(board, transfer.to);
      if (from && to) next.push({ id: transfer.id, src: DOPE_ASSET[transfer.dopeType],
        fromX: from.x, fromY: from.y, toX: to.x, toY: to.y,
        size: Math.max(22, Math.min(56, board.width * 0.049)), count: transfer.count });
    }
    for (const purchase of officerPurchases) {
      const from = purchase.from
        ? boardPosition(board, purchase.from) : resourcePosition(purchase.fromPlayerId, 'cops');
      const to = purchase.to
        ? boardPosition(board, purchase.to) : resourcePosition(purchase.toPlayerId, 'cops');
      if (from && to) next.push({ id: purchase.id, src: OFFICER_ASSET[purchase.officerType],
        fromX: from.x, fromY: from.y, toX: to.x, toY: to.y,
        size: Math.max(22, Math.min(42, board.width * 0.034)), count: 1 });
    }
    setFlights(next);
    if (next.length === 0) return;
    const timer = window.setTimeout(() => setFlights([]), DOPE_TRANSFER_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, [dopeTransfers, officerPurchases]);

  return createPortal(<div className="resource-flights" aria-hidden="true">
    {flights.map((flight) => <div key={flight.id} className="resource-flights__token" style={{
      left: flight.toX, top: flight.toY, width: flight.size,
      '--flight-from-x': `${flight.fromX}px`, '--flight-from-y': `${flight.fromY}px`,
    } as CSSProperties}>
      <img src={flight.src} alt="" />
      {flight.count > 1 && <span>{flight.count}</span>}
    </div>)}
  </div>, document.body);
}
