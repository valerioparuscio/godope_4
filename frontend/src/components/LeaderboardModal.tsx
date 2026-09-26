import { useEffect, useState } from 'react';
import { getLeaderboard } from '../api';
import type { LeaderboardEntryResponse } from '../types';

interface LeaderboardModalProps {
  open: boolean;
  onClose: () => void;
}

// Arcade-style "classifica" (game designer, 2026-09-26: "un pulsante che
// visualizza la classifica pescando dal db... stile arcade anni 90") —
// top 10 finished-game scores from the Supabase persistence db
// (backend/.../persistence/db.py::fetch_leaderboard), fetched fresh every
// time this opens rather than cached, since it's meant to reflect
// whatever anyone has played since the last time it was checked.
export function LeaderboardModal({ open, onClose }: LeaderboardModalProps) {
  const [entries, setEntries] = useState<LeaderboardEntryResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setEntries(null);
    setError(null);
    getLeaderboard()
      .then((res) => {
        if (!cancelled) setEntries(res.entries);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="leaderboard-overlay">
      <div className="leaderboard-modal">
        <button className="leaderboard-modal__close" onClick={onClose} aria-label="Chiudi">
          ×
        </button>
        <h2 className="leaderboard-modal__title">HIGH SCORES</h2>
        {error && <p className="leaderboard-modal__status">Classifica non disponibile.</p>}
        {!error && entries === null && (
          <p className="leaderboard-modal__status">Caricamento...</p>
        )}
        {!error && entries !== null && entries.length === 0 && (
          <p className="leaderboard-modal__status">Nessun punteggio ancora registrato.</p>
        )}
        {!error && entries !== null && entries.length > 0 && (
          <ol className="leaderboard-modal__list">
            {entries.map((entry, i) => (
              <li key={i} className="leaderboard-modal__row">
                <span className="leaderboard-modal__rank">{String(i + 1).padStart(2, '0')}</span>
                <span className="leaderboard-modal__name">
                  {entry.nickname}
                  {entry.winner ? ' ★' : ''}
                </span>
                <span className="leaderboard-modal__score">{entry.total_points}</span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
