import { useState } from 'react';
import { startBackgroundUrl } from '../assets';

interface SetupScreenProps {
  onStart: (seed: number, humanSeat: number, nickname: string, botPolicy: string) => void;
  starting: boolean;
  error: string | null;
}

// "basi per bot più intelligenti" (2026-08-25): a new HeuristicBot exists
// alongside RandomLegalBot (backend/src/dope_engine/bots/policies.py) —
// selectable here so it can be played against, not only exercised by
// tests/sweeps. Default stays "random_legal" (unchanged live behavior)
// until the game designer decides otherwise after trying the new one.
const BOT_POLICY_OPTIONS: { value: string; label: string }[] = [
  { value: 'random_legal', label: 'Casuale' },
  { value: 'heuristic', label: 'Intelligente' },
];

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
  const [botPolicy, setBotPolicy] = useState('random_legal');
  const canStart = nickname.trim().length > 0 && !starting;

  function handleStart() {
    if (!canStart) return;
    const seed = Math.floor(Math.random() * 1_000_000);
    onStart(seed, 0, nickname.trim(), botPolicy);
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
        <div className="setup-screen__bot-policy">
          {BOT_POLICY_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={
                'setup-screen__bot-policy-option' +
                (botPolicy === opt.value ? ' setup-screen__bot-policy-option--selected' : '')
              }
              disabled={starting}
              onClick={() => setBotPolicy(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <button className="setup-screen__start" disabled={!canStart} onClick={handleStart}>
          {starting ? 'Creazione...' : 'GIOCA'}
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
