import { useEffect, useState } from 'react';
import './App.css';
import { advanceGame, answerDecision, createGame, getView, undoLastCommand } from './api';
import { ActionLogDrawer, type LogEntry } from './components/ActionLogDrawer';
import { BoardView } from './components/BoardView';
import { DecisionPanel } from './components/DecisionPanel';
import { FinishedScreen } from './components/FinishedScreen';
import { HandDrawer } from './components/HandDrawer';
import { OutcomeModal } from './components/OutcomeModal';
import { PlayerStrip } from './components/PlayerStrip';
import { RaidBanner } from './components/RaidBanner';
import { SetupScreen } from './components/SetupScreen';
import { SkillsDrawer } from './components/SkillsDrawer';
import { skillUsesFromEvents, SkillUsePopup, type SkillUse } from './components/SkillUsePopup';
import { Tutorial } from './components/Tutorial';
import {
  buildTurnBeats,
  soundUrlsForDopeEvents,
  TurnPlayback,
  type PlaybackSegment,
} from './components/TurnPlayback';
import { friendlyErrorMessage } from './error-messages';
import { describeActionEvents, describeOutcomeEvents } from './log-narration';
import { playSound } from './sound';
import type { DomainErrorResponse, GameEventResponse, GameViewResponse } from './types';

type AppError = DomainErrorResponse | string;

const TUTORIAL_STORAGE_KEY = 'dope_tutorial_seen_v1';

// Browser storage can legitimately throw (private browsing, blocked site
// data) — never let a tutorial-visibility check break the app either way.
function hasSeenTutorial(): boolean {
  try {
    return localStorage.getItem(TUTORIAL_STORAGE_KEY) === '1';
  } catch {
    return true;
  }
}

function markTutorialSeen(): void {
  try {
    localStorage.setItem(TUTORIAL_STORAGE_KEY, '1');
  } catch {
    // Nothing to do if storage is unavailable — the tutorial just shows
    // again next time, which is harmless.
  }
}

// Combines the action-line and outcome-line narration (log-narration.ts)
// into one LogEntry[] batch for a single response's events — ids are
// scoped to that response's own revision (strictly increasing per game),
// so they stay unique across the whole game without a separate counter.
function makeLogEntries(
  events: GameEventResponse[],
  actingPlayerId: string,
  view: GameViewResponse,
): LogEntry[] {
  const lines = [
    ...describeActionEvents(events, actingPlayerId, view),
    ...describeOutcomeEvents(events, view),
  ];
  return lines.map((text, i) => ({ id: `${view.revision}-${i}`, text }));
}

interface ActiveGame {
  gameId: string;
  humanPlayerId: string;
}

// Resolve bots one turn-segment at a time (not the whole cascade in one
// shot) so the board can update after *each* bot instead of jumping
// straight to the fully-resolved end state once every bot has gone
// (designer's request, 2026-08-16). Each iteration's acting player is
// whoever current_player_id was *before* that call — the response's own
// view reflects who's up next. Shared between handleStart (a bot can go
// before the human's own first turn — /api/v1/games itself no longer
// auto-advances that either, 2026-08-16, so it needs the exact same
// narration this already gave every later bot cascade) and handleAnswer.
//
// No count cap: an end-of-turn transition (new TIP_OFF + up to 3 bots x 3
// rounds each + a full Poker phase) can legitimately need well more than
// a small fixed number of segments before it's the human's turn again. An
// earlier `segments.length < 50` cap here just abandoned the cascade
// mid-flight once hit, with nothing left to resume it — the game looked
// stuck (no decision panel, no error) rather than merely capped.
// GameService.advance() already bounds each individual call via its own
// max_steps.
async function resolveBotsAndNarrate(
  gameId: string,
  humanPlayerId: string,
  startingView: GameViewResponse,
  setError: (error: AppError) => void,
): Promise<{
  finalView: GameViewResponse;
  segments: PlaybackSegment[];
  skillUses: SkillUse[];
  logEntries: LogEntry[];
}> {
  const segments: PlaybackSegment[] = [];
  const skillUses: SkillUse[] = [];
  const logEntries: LogEntry[] = [];
  let latestView = startingView;
  while (latestView.status !== 'finished' && latestView.current_player_id !== humanPlayerId) {
    const actingPlayerId = latestView.current_player_id;
    const advanced = await advanceGame(gameId, humanPlayerId, true);
    if (!advanced.ok) {
      setError(advanced.error ?? 'Errore durante il turno degli avversari.');
      break;
    }
    if (!advanced.view) break;
    segments.push({
      beats: buildTurnBeats(advanced.events, actingPlayerId, advanced.view),
      view: advanced.view,
    });
    skillUses.push(...skillUsesFromEvents(advanced.events));
    logEntries.push(...makeLogEntries(advanced.events, actingPlayerId, advanced.view));
    latestView = advanced.view;
  }
  return { finalView: latestView, segments, skillUses, logEntries };
}

function App() {
  const [activeGame, setActiveGame] = useState<ActiveGame | null>(null);
  const [view, setView] = useState<GameViewResponse | null>(null);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [stagedCorruptionAction, setStagedCorruptionAction] = useState<string | null>(null);
  const [playbackSegments, setPlaybackSegments] = useState<PlaybackSegment[] | null>(null);
  const [skillUseQueue, setSkillUseQueue] = useState<SkillUse[]>([]);
  const [finishedOverlayClosed, setFinishedOverlayClosed] = useState(false);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  // Ids of the log entries added by the human's own most recent move, so
  // a successful undo (which only ever reverts that one move — the
  // backend's own undo_available already goes false the instant a bot
  // reacts afterward) can remove exactly those lines instead of leaving a
  // stale entry for a move that no longer happened.
  const [lastMoveEntryIds, setLastMoveEntryIds] = useState<string[]>([]);
  const [tutorialOpen, setTutorialOpen] = useState(() => !hasSeenTutorial());

  function closeTutorial() {
    markTutorialSeen();
    setTutorialOpen(false);
  }

  function dismissSkillUse(key: string) {
    setSkillUseQueue((prev) => prev.filter((u) => u.key !== key));
  }

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

  async function handleStart(seed: number, humanSeat: number, nickname: string) {
    setStarting(true);
    setError(null);
    try {
      const created = await createGame(seed, humanSeat, nickname);
      const humanPlayerId = `player_${humanSeat}`;
      const freshView = await getView(created.game_id, humanPlayerId);
      setActiveGame({ gameId: created.game_id, humanPlayerId });

      // A bot can go before the human's own first turn (turn order isn't
      // always human-first) — narrate that the same way any later bot
      // cascade is (designer's request, 2026-08-16: a bot going first
      // never got a "Turno giocatore X" popup at all, since
      // /api/v1/games used to auto-advance it silently in one shot).
      const { finalView, segments, skillUses, logEntries: botLogEntries } = await resolveBotsAndNarrate(
        created.game_id,
        humanPlayerId,
        freshView,
        setError,
      );
      if (skillUses.length > 0) setSkillUseQueue((prev) => [...prev, ...skillUses]);
      if (botLogEntries.length > 0) setLogEntries((prev) => [...prev, ...botLogEntries]);
      if (segments.length > 0) {
        setView(freshView);
        setPlaybackSegments(segments);
      } else {
        setView(finalView);
      }
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
        setError(result.error ?? 'Mossa non valida.');
        return;
      }
      // Dispatch-only: apply the human's own move immediately (so it's
      // visible/animates right away, e.g. a moved pawn sliding), *before*
      // asking the backend to progress bots (designer's request,
      // 2026-08-16: the human's own action was appearing only after the
      // bots' own narration, since both used to arrive in one response).
      if (!result.view) return;
      setView(result.view);
      soundUrlsForDopeEvents(result.events).forEach(playSound);
      const ownSkillUses = skillUsesFromEvents(result.events);
      if (ownSkillUses.length > 0) setSkillUseQueue((prev) => [...prev, ...ownSkillUses]);
      const ownLogEntries = makeLogEntries(result.events, activeGame.humanPlayerId, result.view);
      if (ownLogEntries.length > 0) {
        setLogEntries((prev) => [...prev, ...ownLogEntries]);
      }
      setLastMoveEntryIds(ownLogEntries.map((e) => e.id));

      const { finalView, segments, skillUses, logEntries: botLogEntries } = await resolveBotsAndNarrate(
        activeGame.gameId,
        activeGame.humanPlayerId,
        result.view,
        setError,
      );
      if (skillUses.length > 0) setSkillUseQueue((prev) => [...prev, ...skillUses]);
      if (botLogEntries.length > 0) setLogEntries((prev) => [...prev, ...botLogEntries]);
      if (segments.length > 0) {
        setPlaybackSegments(segments);
      } else {
        setView(finalView);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUndo() {
    if (!activeGame) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await undoLastCommand(activeGame.gameId, activeGame.humanPlayerId);
      if (!result.ok) {
        setError(result.error ?? 'Impossibile annullare la mossa.');
        return;
      }
      if (result.view) setView(result.view);
      if (lastMoveEntryIds.length > 0) {
        setLogEntries((prev) => prev.filter((e) => !lastMoveEntryIds.includes(e.id)));
        setLastMoveEntryIds([]);
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
    setFinishedOverlayClosed(false);
    setLogEntries([]);
    setLastMoveEntryIds([]);
  }

  if (!activeGame || !view) {
    return (
      <SetupScreen
        onStart={handleStart}
        starting={starting}
        error={error ? friendlyErrorMessage(error) : null}
      />
    );
  }

  return (
    <div className="app">
      <div className="top-strip">
        <RaidBanner view={view} />
      </div>

      <div className="app__main">
        <div className="app__sidebar">
          <PlayerStrip
            view={view}
            decision={view.status === 'finished' ? null : view.pending_decision}
            selected={selected}
            onToggle={toggleSelected}
          />
          <div className="app__decision-area">
            {error && <p className="error">{friendlyErrorMessage(error)}</p>}
            {view.status !== 'finished' && view.undo_available && !playbackSegments && (
              <button className="undo-button" onClick={handleUndo} disabled={submitting}>
                ↶ Annulla ultima mossa
              </button>
            )}
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

          <SkillsDrawer view={view} humanPlayerId={activeGame.humanPlayerId} />
          <HandDrawer
            view={view}
            decision={view.status === 'finished' ? null : view.pending_decision}
            selected={selected}
            onToggle={toggleSelected}
            onSubmit={handleAnswer}
          />
          <ActionLogDrawer entries={logEntries} />
          <button className="hand-drawer__toggle" onClick={() => setTutorialOpen(true)}>
            ? Tutorial
          </button>
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

      {view.status === 'finished' && !finishedOverlayClosed && (
        <div className="finished-overlay">
          <FinishedScreen
            view={view}
            onNewGame={handleNewGame}
            onClose={() => setFinishedOverlayClosed(true)}
          />
        </div>
      )}

      <SkillUsePopup queue={skillUseQueue} onShown={dismissSkillUse} />
      <OutcomeModal view={view} />
      <Tutorial open={tutorialOpen} onClose={closeTutorial} />

      {playbackSegments && (
        <TurnPlayback segments={playbackSegments} onApplyView={setView} onDone={handlePlaybackDone} />
      )}
    </div>
  );
}

export default App;
