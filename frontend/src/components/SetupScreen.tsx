import { useState } from 'react';

interface SetupScreenProps {
  onStart: (seed: number, humanSeat: number) => void;
  starting: boolean;
  error: string | null;
}

export function SetupScreen({ onStart, starting, error }: SetupScreenProps) {
  const [seed, setSeed] = useState(() => Math.floor(Math.random() * 1_000_000));
  const [humanSeat, setHumanSeat] = useState(0);

  return (
    <div className="setup-screen">
      <h1>DOPE</h1>
      <p>1 giocatore umano contro 3 bot.</p>
      <label>
        Seed
        <input
          type="number"
          value={seed}
          onChange={(e) => setSeed(Number(e.target.value))}
        />
      </label>
      <label>
        Il tuo seat
        <select value={humanSeat} onChange={(e) => setHumanSeat(Number(e.target.value))}>
          <option value={0}>player_0</option>
          <option value={1}>player_1</option>
          <option value={2}>player_2</option>
          <option value={3}>player_3</option>
        </select>
      </label>
      <button disabled={starting} onClick={() => onStart(seed, humanSeat)}>
        {starting ? 'Creazione...' : 'Nuova partita'}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
