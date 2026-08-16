import { useEffect, useState } from 'react';
import './App.css';
import { advanceGame, answerDecision, createGame, getView } from './api';
import { BoardView } from './components/BoardView';
import { DecisionPanel } from './components/DecisionPanel';
import { FinishedScreen } from './components/FinishedScreen';
import { HandDrawer } from './components/HandDrawer';
import { JobActiveStrip } from './components/JobActiveStrip';
import { PlayerStrip } from './components/PlayerStrip';
import { RaidBanner } from './components/RaidBanner';
import { ResultPopups } from './components/ResultPopup';
import { SetupScreen } from './components/SetupScreen';
import { buildTurnBeats, TurnPlayback, type PlaybackSegment } from './components/TurnPlayback';
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
  const [playbackSegments, setPlaybackSegments] = useState<PlaybackSegment[] | null>(null);

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
      // Dispatch-only: apply the human's own move immediately (so it's
      // visible/animates right away, e.g. a moved pawn sliding), *before*
      // asking the backend to progress bots (designer's request,
      // 2026-08-16: the human's own action was appearing only after the
      // bots' own narration, since both used to arrive in one response).
      if (!result.view) return;
      setView(result.view);

      // Resolve bots one turn-segment at a time (not the whole cascade in
      // one shot) so the board can update after *each* bot instead of
      // jumping straight to the fully-resolved end state once every bot
      // has gone (designer's request, 2026-08-16). Each iteration's
      // acting player is whoever current_player_id was *before* that
      // call — the response's own view reflects who's up next.
      //
      // No count cap here: an end-of-turn transition (new TIP_OFF + up to
      // 3 bots x 3 rounds each + a full Poker phase) can legitimately need
      // well more than a small fixed number of segments before it's the
      // human's turn again. An earlier `segments.length < 50` cap here
      // just abandoned the cascade mid-flight once hit, with nothing left
      // to resume it — the game looked stuck (no decision panel, no
      // error) rather than merely capped. GameService.advance() already
      // bounds each individual call via its own max_steps.
      const segments: PlaybackSegment[] = [];
      let latestView = result.view;
      while (latestView.status !== 'finished' && latestView.current_player_id !== activeGame.humanPlayerId) {
        const actingPlayerId = latestView.current_player_id;
        const advanced = await advanceGame(activeGame.gameId, activeGame.humanPlayerId, true);
        if (!advanced.ok) {
          setError(advanced.error?.message ?? 'Errore durante il turno degli avversari.');
          break;
        }
        if (!advanced.view) break;
        segments.push({
          beats: buildTurnBeats(advanced.events, actingPlayerId, advanced.view),
          view: advanced.view,
        });
        latestView = advanced.view;
      }

      if (segments.length > 0) {
        setPlaybackSegments(segments);
      } else {
        setView(latestView);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handlePlaybackDone() {
    setPlaybackSegments(null);
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

      {playbackSegments && (
        <TurnPlayback segments={playbackSegments} onApplyView={setView} onDone={handlePlaybackDone} />
      )}
    </div>
  );
}

export default App;
