import { useState } from 'react';
import './App.css';
import { answerDecision, createGame, getView } from './api';
import { BoardSummary } from './components/BoardSummary';
import { DecisionPanel } from './components/DecisionPanel';
import { FinishedScreen } from './components/FinishedScreen';
import { HandView } from './components/HandView';
import { PlayerStrip } from './components/PlayerStrip';
import { SetupScreen } from './components/SetupScreen';
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
      if (result.view) setView(result.view);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
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
      <header>
        <h1>DOPE</h1>
        <p>
          Turno {view.turn_index} · Round {view.action_round_index} · Fase {view.phase} · Step{' '}
          {view.active_step}
        </p>
      </header>

      <PlayerStrip view={view} />
      <HandView view={view} />
      <BoardSummary view={view} />

      {error && <p className="error">{error}</p>}

      {view.status === 'finished' ? (
        <FinishedScreen view={view} onNewGame={handleNewGame} />
      ) : view.pending_decision ? (
        <DecisionPanel
          decision={view.pending_decision}
          onSubmit={handleAnswer}
          submitting={submitting}
        />
      ) : (
        <p>In attesa...</p>
      )}
    </div>
  );
}

export default App;
