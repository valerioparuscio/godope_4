import { useEffect, useRef, useState } from 'react';
import type { GameViewResponse } from '../types';

interface QueuedPopup {
  id: string;
  title: string;
  lines: string[];
}

function playerLabel(view: GameViewResponse, playerId: string): string {
  return view.players.find((p) => p.player_id === playerId)?.display_name ?? playerId;
}

function raidPopup(view: GameViewResponse): QueuedPopup | null {
  const outcome = view.last_raid_outcome;
  if (!outcome) return null;
  return {
    id: `raid:${JSON.stringify(outcome)}`,
    title: `Retata conclusa (${outcome.raid_card_id})`,
    lines: [
      `Sfuggono: ${outcome.escaping_team.map((id) => playerLabel(view, id)).join(', ') || '-'}`,
      `Catturati (REP macchiata): ${
        outcome.caught_team.map((id) => playerLabel(view, id)).join(', ') || '-'
      }`,
    ],
  };
}

function brawlPopup(view: GameViewResponse): QueuedPopup | null {
  const outcome = view.last_brawl_outcome;
  if (!outcome) return null;
  const forceLines = Object.entries(outcome.force_by_player_id).map(
    ([playerId, force]) => `${playerLabel(view, playerId)}: forza ${force}`,
  );
  return {
    id: `brawl:${JSON.stringify(outcome)}`,
    title: `Rissa conclusa (${outcome.hood_id})`,
    lines: [
      outcome.winner_id ? `Vince: ${playerLabel(view, outcome.winner_id)}` : 'Nessun vincitore',
      ...(outcome.loser_ids.length > 0
        ? [`Sconfitti: ${outcome.loser_ids.map((id) => playerLabel(view, id)).join(', ')}`]
        : []),
      ...forceLines,
    ],
  };
}

function pokerPopup(view: GameViewResponse): QueuedPopup | null {
  const outcomes = view.last_poker_outcomes;
  if (outcomes.length === 0) return null;
  return {
    id: `poker:${JSON.stringify(outcomes)}`,
    title: 'Poker concluso',
    lines: outcomes.map((match, i) => {
      if (match.winner_id) {
        return `Partita ${i + 1}: vince ${playerLabel(view, match.winner_id)} (+$${match.cash_won})`;
      }
      if (match.tied_ids.length > 0) {
        const names = match.tied_ids.map((id) => playerLabel(view, id)).join(', ');
        return `Partita ${i + 1}: pareggio tra ${names} — jackpot riportato`;
      }
      return `Partita ${i + 1}: nessun vincitore`;
    }),
  };
}

// Dismissible recap popups for Brawl/Poker/Raid conclusions (designer's
// request, 2026-08-16, replacing the inline "Occorrenze perse" banner
// text) — each of the 3 outcome fields on the view is compared against
// the last one already shown (by JSON content, since the same shape can
// legitimately recur — e.g. a repeated raid_card_id — but never with the
// exact same result twice), so a popup only queues once per genuinely
// new resolution, not on every unrelated view refresh.
export function ResultPopups({ view }: { view: GameViewResponse }) {
  const [queue, setQueue] = useState<QueuedPopup[]>([]);
  const shownIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    const candidates = [raidPopup(view), brawlPopup(view), pokerPopup(view)].filter(
      (p): p is QueuedPopup => p !== null,
    );
    const fresh = candidates.filter((p) => !shownIds.current.has(p.id));
    if (fresh.length === 0) return;
    for (const p of fresh) shownIds.current.add(p.id);
    setQueue((prev) => [...prev, ...fresh]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view.last_raid_outcome, view.last_brawl_outcome, view.last_poker_outcomes]);

  if (queue.length === 0) return null;

  function dismiss(id: string) {
    setQueue((prev) => prev.filter((p) => p.id !== id));
  }

  return (
    <div className="result-popups">
      {queue.map((popup) => (
        <div key={popup.id} className="result-popup">
          <button
            className="result-popup__close"
            onClick={() => dismiss(popup.id)}
            aria-label="Chiudi"
          >
            ×
          </button>
          <h4>{popup.title}</h4>
          <ul>
            {popup.lines.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
