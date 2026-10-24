import { useEffect, useState } from 'react';
import { playerColorForId, playerTeamNameForId, startBackgroundUrl } from '../assets';
import type { GameViewResponse } from '../types';
import './MultiplayerGame.css';

// Waiting this long for the same player earns a word about what happens if they are gone.
const SLOW_TURN_HINT_MS = 20_000;

/** Whose turn it is while it is not ours: shown where the decision panel would be. */
export function MultiplayerWaiting({ view }: { view: GameViewResponse }) {
  const current = view.players.find((p) => p.player_id === view.current_player_id);
  const color = playerColorForId(view.current_player_id);
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    setSlow(false);
    const timer = setTimeout(() => setSlow(true), SLOW_TURN_HINT_MS);
    return () => clearTimeout(timer);
  }, [view.current_player_id]);
  return (
    <div className={`mp-waiting mp-waiting--${color}`} role="status" aria-live="polite">
      <span className="mp-waiting__dot" aria-hidden="true" />
      <span className="mp-waiting__text">
        Tocca a <strong>{current?.display_name ?? 'un altro giocatore'}</strong>
        {' · '}
        {playerTeamNameForId(view.current_player_id)}
      </span>
      {slow && (
        <span className="mp-waiting__hint">
          Se non risponde, dopo un po' un bot gioca al suo posto.
        </span>
      )}
    </div>
  );
}

/** Shown from the moment the room starts until the first view of the game arrives. */
export function MultiplayerConnecting({ message }: { message: string }) {
  const background = startBackgroundUrl();
  return (
    <div
      className="setup-screen"
      style={background ? { backgroundImage: `url(${background})` } : undefined}
    >
      <p className="mp-connecting">{message}</p>
    </div>
  );
}
