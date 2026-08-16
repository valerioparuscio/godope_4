import { useEffect, useState } from 'react';
import { playerColorLabelForId } from '../assets';
import type { GameEventResponse } from '../types';

export interface TurnBeat {
  key: string;
  text: string;
}

function plural(n: number, singular: string, pluralForm: string): string {
  return n === 1 ? singular : pluralForm;
}

// Only these event types get narrated (designer's request, 2026-08-16:
// bot turns shouldn't feel instant) — everything else (market/global
// events, the human's own actions, Poker/Brawl's own multi-step hidden
// flows) is left out of scope for now rather than guessed at.
const ACTION_LABELS: Record<string, (n: number) => string> = {
  CriminalPlaced: (n) => `piazza ${n} ${plural(n, 'criminale', 'criminali')}`,
  CriminalMoved: (n) => `sposta ${n} ${plural(n, 'criminale', 'criminali')}`,
  DopeBought: (n) => `acquista ${n} ${plural(n, 'dose', 'dosi')} di merce`,
  DopeSold: (n) => `vende ${n} ${plural(n, 'dose', 'dosi')} di merce`,
  PawnArrested: (n) => `arresta ${n} ${plural(n, 'criminale', 'criminali')}`,
  OfficerCorruptionStarted: (n) => `corrompe ${n} ${plural(n, 'agente', 'agenti')}`,
  OfficerBought: (n) => `compra ${n} ${plural(n, 'agente', 'agenti')}`,
  MainActionPassed: () => 'passa',
};

// Builds the "Turno giocatore X" + "X piazza N criminali" sequence from
// the raw event log a command response now carries (app.py's
// _serialize_event). PawnArrested.player_id is the *victim's* owner, not
// the corrupting player (rules/jail.py) — ActionTypeChosen.player_id
// (emitted for every main action, including "corrompi") is tracked
// separately as "who's currently acting" so an arrest still gets
// attributed to the actor, not whoever's pawn got jailed.
export function buildTurnBeats(events: GameEventResponse[], humanPlayerId: string): TurnBeat[] {
  let currentActorId: string | null = null;
  const attributed: { playerId: string; type: string }[] = [];

  for (const event of events) {
    if (event.event_type === 'ActionTypeChosen') {
      currentActorId = event.player_id as string;
    }
    if (!(event.event_type in ACTION_LABELS)) continue;
    const playerId =
      event.event_type === 'PawnArrested'
        ? currentActorId
        : ((event.player_id as string | undefined) ?? null);
    if (!playerId || playerId === humanPlayerId) continue;
    attributed.push({ playerId, type: event.event_type });
  }

  const beats: TurnBeat[] = [];
  let idx = 0;
  let lastPlayerId: string | null = null;
  let i = 0;
  while (i < attributed.length) {
    const { playerId, type } = attributed[i];
    if (playerId !== lastPlayerId) {
      beats.push({
        key: `beat-${idx++}`,
        text: `Turno giocatore ${playerColorLabelForId(playerId)}`,
      });
      lastPlayerId = playerId;
    }
    let count = 0;
    while (i < attributed.length && attributed[i].playerId === playerId && attributed[i].type === type) {
      count++;
      i++;
    }
    beats.push({
      key: `beat-${idx++}`,
      text: `${playerColorLabelForId(playerId)} ${ACTION_LABELS[type](count)}`,
    });
  }
  return beats;
}

const BEAT_DURATION_MS = 2000;

// Plays the beat queue one at a time (2s each, designer's request
// 2026-08-16), blocking interaction with the still-stale board/decision
// panel underneath until it's done — onDone is when the caller should
// finally apply the new view.
export function TurnPlayback({ beats, onDone }: { beats: TurnBeat[]; onDone: () => void }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (index >= beats.length) {
      onDone();
      return;
    }
    const timer = setTimeout(() => setIndex((i) => i + 1), BEAT_DURATION_MS);
    return () => clearTimeout(timer);
  }, [index, beats.length]);

  if (index >= beats.length) return null;
  const beat = beats[index];
  return (
    <div className="turn-playback">
      <div className="turn-playback__card" key={beat.key}>
        {beat.text}
      </div>
    </div>
  );
}
