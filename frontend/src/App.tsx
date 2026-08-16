import { useEffect, useState } from 'react';
import './App.css';
import { answerDecision, createGame, getView } from './api';
import { BoardView } from './components/BoardView';
import { DecisionPanel } from './components/DecisionPanel';
import { FinishedScreen } from './components/FinishedScreen';
import { HandDrawer } from './components/HandDrawer';
import { JobActiveStrip } from './components/JobActiveStrip';
import { PlayerStrip } from './components/PlayerStrip';
import { RaidBanner } from './components/RaidBanner';
import { ResultPopups } from './components/ResultPopup';
import { SetupScreen } from './components/SetupScreen';
import { buildTurnBeats, TurnPlayback, type TurnBeat } from './components/TurnPlayback';
import type { GameViewResponse } from './types';

interface ActiveGame {
  gameId: string;
  humanPlayerId: string;
}

function App() {
  const [activeGame, setActiveGame] = useState<ActiveGame | null>(null);
  const [view, setView] = useState<GameViewResponse | null>(null);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [stagedCorruptionAction, setStagedCorruptionAction] = useState<string | null>(null);
  const [playbackBeats, setPlaybackBeats] = useState<TurnBeat[] | null>(null);
  const [pendingView, setPendingView] = useState<GameViewResponse | null>(null);

  const decisionId = view?.pending_decision?.decision_id;
  useEffect(() => {
    setSelected([]);
    setStagedCorruptionAction(null);
  }, [decisionId]);

  function toggleSelected(optionId: string) {
    const decision = view?.pending_decision;
    if (!decision) return;
    setSelected((prev) => {
      if (prev.includes(optionId)) return prev.filter((id) => id !== optionId);
      if (decision.max_selections === 1) return [optionId];
      if (prev.length >= decision.max_selections) return prev;
      return [...prev, optionId];
    });
  }

  async function handleStart(seed: number, humanSeat: number) {
    setStarting(true);
    setError(null);
    try {
      const created = await createGame(seed, humanSeat);
      const humanPlayerId = `player_${humanSeat}`;
      const freshView = await getView(created.game_id, humanPlayerId);
      setActiveGame({ gameId: created.game_id, humanPlayerId });
      setView(freshView);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  }

  async function handleAnswer(selectedOptionIds: string[]) {
    if (!activeGame || !view?.pending_decision) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await answerDecision(
        activeGame.gameId,
        activeGame.humanPlayerId,
        view.pending_decision.decision_id,
        selectedOptionIds,
      );
      if (!result.ok) {
        setError(result.error?.message ?? 'Mossa non valida.');
        return;
      }
      if (result.view) {
        // Opponent turns shouldn't feel instant (designer's request,
        // 2026-08-16): if the bot/automatic cascade this command
        // triggered did anything narratable, hold the stale view on
        // screen and play a "Turno giocatore X" / "X piazza N
        // criminali" beat sequence first — TurnPlayback applies
        // result.view itself once the queue finishes (onDone below).
        const beats = buildTurnBeats(result.events, activeGame.humanPlayerId);
        if (beats.length > 0) {
          setPendingView(result.view);
          setPlaybackBeats(beats);
        } else {
          setView(result.view);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handlePlaybackDone() {
    if (pendingView) setView(pendingView);
    setPendingView(null);
    setPlaybackBeats(null);
  }

  function handleNewGame() {
    setActiveGame(null);
    setView(null);
    setError(null);
  }

  if (!activeGame || !view) {
    return <SetupScreen onStart={handleStart} starting={starting} error={error} />;
  }

  return (
    <div className="app">
      <div className="top-strip">
        <RaidBanner view={view} />
        <JobActiveStrip view={view} />
      </div>

      <div className="app__main">
        <div className="app__sidebar">
          <PlayerStrip view={view} />
          <div className="app__decision-area">
            {error && <p className="error">{error}</p>}
            {view.status !== 'finished' &&
              (view.pending_decision ? (
                <DecisionPanel
                  decision={view.pending_decision}
                  view={view}
                  selected={selected}
                  onToggle={toggleSelected}
                  onSubmit={handleAnswer}
                  submitting={submitting}
                  stagedCorruptionAction={stagedCorruptionAction}
                  onStageCorruptionAction={setStagedCorruptionAction}
                />
              ) : (
                <p>In attesa...</p>
              ))}
          </div>
        </div>

        <div className="app__board-wrapper">
          <BoardView
            view={view}
            decision={view.status === 'finished' ? null : view.pending_decision}
            selected={selected}
            onToggle={toggleSelected}
            onSubmit={handleAnswer}
            stagedCorruptionAction={stagedCorruptionAction}
          />
        </div>
      </div>

      <HandDrawer
        view={view}
        decision={view.status === 'finished' ? null : view.pending_decision}
        selected={selected}
        onToggle={toggleSelected}
        onSubmit={handleAnswer}
      />

      {view.status === 'finished' && (
        <div className="finished-overlay">
          <FinishedScreen view={view} onNewGame={handleNewGame} />
        </div>
      )}

      <ResultPopups view={view} />

      {playbackBeats && <TurnPlayback beats={playbackBeats} onDone={handlePlaybackDone} />}
    </div>
  );
}

export default App;
