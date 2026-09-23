import { useState } from 'react';
import { startBackgroundUrl } from '../assets';

interface SetupScreenProps {
  onStart: (seed: number, humanSeat: number, nickname: string) => void;
  starting: boolean;
  error: string | null;
}

// Redesigned (designer's request, 2026-08-18): full-bleed cover art, one
// big centered "GIOCA" button (2026-08-23, was "Inizia"), no seed/seat
// pickers — those were only
// ever useful for debugging/replaying a specific game, not to a player
// starting a normal match, so they're now decided silently instead:
// a fresh random seed each time (still fully deterministic once picked,
// same as before — just not player-facing), and the human always seated
// at player_0.
//
// Nickname (designer's request, 2026-08-23): required to play, saved to
// the backend's persistence db only — it does not change the in-game
// team-name labels ("Blue Bandits" etc.), which stay as-is.
export function SetupScreen({ onStart, starting, error }: SetupScreenProps) {
  const background = startBackgroundUrl();
  const [nickname, setNickname] = useState('');
  const canStart = nickname.trim().length > 0 && !starting;

  function handleStart() {
    if (!canStart) return;
    const seed = Math.floor(Math.random() * 1_000_000);
    onStart(seed, 0, nickname.trim());
  }

  return (
    <div
      className="setup-screen"
      style={background ? { backgroundImage: `url(${background})` } : undefined}
    >
      <div className="setup-screen__content">
        <input
          className="setup-screen__nickname"
          type="text"
          placeholder="Il tuo nickname"
          value={nickname}
          maxLength={32}
          disabled={starting}
          onChange={(e) => setNickname(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleStart();
          }}
        />
        <button className="setup-screen__start" disabled={!canStart} onClick={handleStart}>
          {starting ? 'Creazione...' : 'GIOCA'}
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
