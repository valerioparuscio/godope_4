import { startBackgroundUrl } from '../assets';

interface SetupScreenProps {
  onStart: (seed: number, humanSeat: number) => void;
  starting: boolean;
  error: string | null;
}

// Redesigned (designer's request, 2026-08-18): full-bleed cover art, one
// big centered "Inizia" button, no seed/seat pickers — those were only
// ever useful for debugging/replaying a specific game, not to a player
// starting a normal match, so they're now decided silently instead:
// a fresh random seed each time (still fully deterministic once picked,
// same as before — just not player-facing), and the human always seated
// at player_0.
export function SetupScreen({ onStart, starting, error }: SetupScreenProps) {
  const background = startBackgroundUrl();

  function handleStart() {
    const seed = Math.floor(Math.random() * 1_000_000);
    onStart(seed, 0);
  }

  return (
    <div
      className="setup-screen"
      style={background ? { backgroundImage: `url(${background})` } : undefined}
    >
      <div className="setup-screen__content">
        <button className="setup-screen__start" disabled={starting} onClick={handleStart}>
          {starting ? 'Creazione...' : 'Inizia'}
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
