import { useEffect, useMemo, useState } from 'react';
import {
  criminalAssetsForPlayer,
  playerColorForId,
  playerTeamNameForId,
  startBackgroundUrl,
} from '../assets';
import { LeaderboardModal } from './LeaderboardModal';
import { TutorialGame } from './TutorialGame';

interface SetupScreenProps {
  onStart: (seed: number, humanSeat: number, nickname: string) => void;
  starting: boolean;
  error: string | null;
}

// A new key (not the old, removed Tutorial.tsx's `dope_tutorial_seen_v1`,
// per the same reasoning already noted when RulesModal replaced that
// tour): existing players already have the old key set and would never
// see this new, differently-shaped tutorial automatically otherwise.
const TUTORIAL_SEEN_STORAGE_KEY = 'dope_tutorial_v2_seen';

function hasSeenTutorial(): boolean {
  try {
    return localStorage.getItem(TUTORIAL_SEEN_STORAGE_KEY) === 'true';
  } catch {
    return true; // private/blocked storage: don't force it open every visit
  }
}

function markTutorialSeen(): void {
  try {
    localStorage.setItem(TUTORIAL_SEEN_STORAGE_KEY, 'true');
  } catch {
    // best-effort only
  }
}

// Redesigned (designer's request, 2026-08-18): full-bleed cover art, one
// big centered "GIOCA" button (2026-08-23, was "Inizia"), no seed/seat
// pickers — those were only
// ever useful for debugging/replaying a specific game, not to a player
// starting a normal match, so they're now decided silently instead:
// a fresh random seed each time (still fully deterministic once picked,
// same as before — just not player-facing). The seat is no longer fixed
// at player_0: after the nickname, an intermediate screen asks which gang
// (= colour = seat) the human plays (designer's request, 2026-10-02).
//
// Nickname (designer's request, 2026-08-23): required to play, saved to
// the backend's persistence db only — it does not change the in-game
// team-name labels ("Blue Bandits" etc.), which stay as-is.
export function SetupScreen({ onStart, starting, error }: SetupScreenProps) {
  const background = startBackgroundUrl();
  const [nickname, setNickname] = useState('');
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const [leaderboardOpen, setLeaderboardOpen] = useState(false);
  const [choosingGang, setChoosingGang] = useState(false);
  // One random criminal face per gang, picked once per mount so it doesn't
  // flicker on re-render. Gang = seat: colors are fixed per seat, so choosing
  // a colour is choosing `human_seat`.
  const gangChoices = useMemo(
    () =>
      [0, 1, 2, 3].map((seat) => {
        const playerId = `player_${seat}`;
        const portraits = criminalAssetsForPlayer(playerId);
        return {
          seat,
          color: playerColorForId(playerId),
          teamName: playerTeamNameForId(playerId),
          portrait: portraits.length
            ? portraits[Math.floor(Math.random() * portraits.length)]
            : null,
        };
      }),
    [],
  );
  const canStart = nickname.trim().length > 0 && !starting;

  // Opens automatically the first time (game designer, 2026-09-24: "un
  // bottone tutorial che si apre automaticamente la prima volta") — a
  // deliberate one-time nudge, not shown again once dismissed.
  useEffect(() => {
    if (!hasSeenTutorial()) {
      setTutorialOpen(true);
      markTutorialSeen();
    }
  }, []);

  function handleStart() {
    if (!canStart) return;
    setChoosingGang(true);
  }

  function handlePickGang(seat: number) {
    if (starting) return;
    const seed = Math.floor(Math.random() * 1_000_000);
    onStart(seed, seat, nickname.trim());
  }

  if (tutorialOpen) {
    return <TutorialGame onClose={() => setTutorialOpen(false)} />;
  }

  if (choosingGang) {
    return (
      <div
        className="setup-screen"
        style={background ? { backgroundImage: `url(${background})` } : undefined}
      >
        <div className="setup-screen__content">
          <h2 className="setup-screen__gang-title">Scegli la tua gang</h2>
          <div className="setup-screen__gangs">
            {gangChoices.map((gang) => (
              <button
                key={gang.seat}
                type="button"
                className={`setup-screen__gang player-card--${gang.color}`}
                disabled={starting}
                onClick={() => handlePickGang(gang.seat)}
              >
                {gang.portrait && (
                  <img src={gang.portrait} alt="" className="setup-screen__gang-face" />
                )}
                <span className="setup-screen__gang-name">{gang.teamName}</span>
              </button>
            ))}
          </div>
          <button
            className="setup-screen__tutorial"
            type="button"
            disabled={starting}
            onClick={() => setChoosingGang(false)}
          >
            Indietro
          </button>
          {starting && <p>Creazione...</p>}
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    );
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
        <div className="setup-screen__actions">
          <button className="setup-screen__start" disabled={!canStart} onClick={handleStart}>
            {starting ? 'Creazione...' : 'GIOCA'}
          </button>
          <button
            className="setup-screen__tutorial"
            type="button"
            onClick={() => setTutorialOpen(true)}
          >
            Tutorial
          </button>
          <button
            className="setup-screen__leaderboard"
            type="button"
            onClick={() => setLeaderboardOpen(true)}
          >
            Classifica
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
      <LeaderboardModal open={leaderboardOpen} onClose={() => setLeaderboardOpen(false)} />
    </div>
  );
}
