import { useEffect, useRef, useState } from 'react';
import { advanceGame, advanceTutorialStage, answerDecision, createTutorialGame, getView } from '../api';
import { RaidBanner } from './RaidBanner';
import { SkillsDrawer } from './SkillsDrawer';
import { TutorialMarkers } from './TutorialMarkers';
import { TutorialMessage } from './TutorialMessage';
import { TutorialSheet } from './TutorialSheet';
import './TutorialGame.css';
import { collectFreshMatchOutcomes, type QueuedOutcome } from '../outcome-queue';
import { TUTORIAL_SCENARIOS } from '../tutorial/scenarios';
import type { GameViewResponse } from '../types';
import { BoardView } from './BoardView';
import { DecisionPanel } from './DecisionPanel';
import { HandDrawer } from './HandDrawer';
import { OutcomeModal } from './OutcomeModal';
import { PlayerStrip } from './PlayerStrip';

interface TutorialGameProps {
  onClose: () => void;
}

// Safety cap on the bot-advance loop below — a Rissa's own declare/
// assign/reward round-robin is a handful of steps, never dozens.
const MAX_ADVANCE_STEPS = 12;

// The tutorial is ONE running game (game designer, 2026-10-02): the sandbox
// is created once, and each card only patches the *next stage* on top of it
// (`advanceTutorialStage`), so the board never reloads between cards. Going
// back rebuilds the game and replays the stages up to that card.
export function TutorialGame({ onClose }: TutorialGameProps) {
  const [index, setIndex] = useState(0);
  const [view, setView] = useState<GameViewResponse | null>(null);
  // Which card `view` was staged for — until it catches up with `index` the
  // old board stays on screen, but no decision or lesson text is shown.
  const [readyIndex, setReadyIndex] = useState<number | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [stagedCorruptionAction, setStagedCorruptionAction] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(true);
  // Rissa/Poker/Retata recap, same blocking OutcomeModal a real game
  // shows (App.tsx's own `outcome-queue.ts`) — no "Turno N" announcement
  // here (`collectFreshMatchOutcomes`, not the full `collectFreshOutcomes`).
  const [outcomeQueue, setOutcomeQueue] = useState<QueuedOutcome[]>([]);
  const shownOutcomeIds = useRef<Set<string>>(new Set());
  const gameId = useRef<string | null>(null);
  // The card the running game is currently staged for; going *back* is the
  // only move that can't be patched forward.
  const stagedIndex = useRef(-1);

  const scenario = TUTORIAL_SCENARIOS[index];
  const ready = readyIndex === index;

  useEffect(() => {
    let cancelled = false;
    setSelected([]);
    setStagedCorruptionAction(null);
    setDone(false);
    setError(null);
    setSheetOpen(true);
    (async () => {
      try {
        if (gameId.current === null || index < stagedIndex.current) {
          // Fresh game for the first card, then every later card's stage in
          // order — what going back to card `index` would have looked like.
          const first = TUTORIAL_SCENARIOS[0].stage!;
          const created = await createTutorialGame(first);
          gameId.current = created.game_id;
          stagedIndex.current = 0;
          if (cancelled) return;
        }
        const id = gameId.current!;
        while (stagedIndex.current < index) {
          const next = TUTORIAL_SCENARIOS[stagedIndex.current + 1];
          if (next.stage) await advanceTutorialStage(id, next.stage);
          stagedIndex.current += 1;
          if (cancelled) return;
        }
        const freshView = await getView(id, 'player_0');
        if (cancelled) return;
        setView(freshView);
        setReadyIndex(index);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [index]);

  useEffect(() => {
    if (!view) return;
    const fresh = collectFreshMatchOutcomes(view, shownOutcomeIds.current);
    if (fresh.length > 0) setOutcomeQueue((prev) => [...prev, ...fresh]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view?.last_brawl_outcome, view?.last_poker_outcome, view?.last_raid_outcome]);

  function dismissOutcome() {
    setOutcomeQueue((prev) => prev.slice(1));
  }

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

  async function handleAnswer(selectedOptionIds: string[]) {
    if (submitting || !gameId.current || !view?.pending_decision) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await answerDecision(
        gameId.current,
        'player_0',
        view.pending_decision.decision_id,
        selectedOptionIds,
      );
      if (!result.ok) {
        setError(result.error?.message ?? 'Mossa non valida, riprova.');
        return;
      }
      // Apply the post-move view so the card actually *shows* what the
      // move did — the pawn standing in its new Hood, the Dope count on
      // the player's own board going up (game designer, 2026-09-24:
      // "dopo che l'utente clicca non mostra l'esito"). Without this the
      // board stayed frozen on the pre-move state.
      let nextView = result.view ?? view;
      setSelected([]);
      setStagedCorruptionAction(null);

      // Let the bots answer first when the card needs it (a Rissa's other
      // participants declaring). `pending_decision` is only ever populated
      // for its *own* player, so a non-null one means the human's turn.
      if (scenario.advanceBots) {
        for (let step = 0; step < MAX_ADVANCE_STEPS && !nextView.pending_decision; step += 1) {
          const advanced = await advanceGame(gameId.current, 'player_0');
          if (!advanced.ok || !advanced.view) break;
          nextView = advanced.view;
        }
      }

      // The card goes on only while the human's next decision is still
      // part of the same move (its `followUps`) — anything else is the
      // game carrying on past the lesson, so the card is done.
      const next = nextView.pending_decision;
      const stillPlaying = !!next && (scenario.followUps ?? []).includes(next.decision_type);

      setView(nextView);
      if (!stillPlaying) setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  function goNext() {
    if (index + 1 < TUTORIAL_SCENARIOS.length) {
      setIndex((i) => i + 1);
    } else {
      onClose();
    }
  }

  function goBack() {
    if (index > 0) setIndex((i) => i - 1);
  }


  const isLast = index + 1 >= TUTORIAL_SCENARIOS.length;
  // Observation steps hide the sandbox decision until the next lesson.
  const isObserve = !!scenario.observeOnly;
  const finished = done || isObserve;
  const liveDecision = finished || !ready ? null : (view?.pending_decision ?? null);

  const blocked = submitting || (!ready && !error) || outcomeQueue.length > 0;
  const guidance = liveDecision && scenario.decisionInstructions?.[liveDecision.decision_type];
  // Once the move is done the outcome text may point at other things.
  const activeMarkers = !ready ? [] : done ? (scenario.outcomeMarkers ?? scenario.markers ?? []) : (scenario.markers ?? []);
  const message = !ready ? '' : done ? scenario.outcome : guidance || scenario.instruction;

  return (
    <div className="app tutorial-game" aria-label="Partita tutorial">
      <aside className="app__sidebar">
        {view && <>
          <RaidBanner view={view} />
          <PlayerStrip view={view} decision={liveDecision} selected={selected} onToggle={toggleSelected} />
          <TutorialMarkers markers={activeMarkers.filter((a) => a.area === 'sidebar')} />
        </>}
      </aside>
      <div className="app__play-area human-theme--red">
        <div className="top-strip">
          <div className="top-strip__primary-buttons" aria-label="Carte e Skill">
            {view && <>
              <HandDrawer view={view} decision={liveDecision} selected={selected}
                onToggle={toggleSelected} onSubmit={handleAnswer} />
              <SkillsDrawer view={view} humanPlayerId="player_0" />
              <TutorialMarkers markers={activeMarkers.filter((a) => a.area === 'toolbar')} />
            </>}
          </div>
          <div className={'top-strip__decision-area human-controls tutorial-game__controls' + (liveDecision ? ' tutorial-game__controls--interactive' : '') + (!message ? ' tutorial-game__controls--title-only' : '')}>
            <div className="tutorial-game__heading">
              <span>Tutorial · {index + 1}/{TUTORIAL_SCENARIOS.length}</span>
              <strong>{scenario.title}</strong>
            </div>
            {message && <TutorialMessage text={message} interactive={!!liveDecision} />}
            {error && <p className="error" role="alert">{error}</p>}
            {!ready && !error && <p role="status">Preparo il tabellone…</p>}
            {view && liveDecision && <div className={'tutorial-game__decision' + (
              ['place_criminal', 'move_criminal', 'buy_dope', 'sell_dope', 'corrupt_officer', 'buy_officer'].includes(liveDecision.decision_type)
                ? ' tutorial-game__decision--board' : ''
            )}><DecisionPanel decision={liveDecision} view={view}
              selected={selected} onToggle={toggleSelected} onSubmit={handleAnswer}
              guidanceInCorner
              submitting={submitting} stagedCorruptionAction={stagedCorruptionAction}
              onStageCorruptionAction={setStagedCorruptionAction} /></div>}
          </div>
          <nav className="top-strip__optional-actions tutorial-game__navigation" aria-label="Percorso tutorial">
            <button disabled={index === 0 || submitting || outcomeQueue.length > 0} onClick={goBack}>← Indietro</button>
            {ready && scenario.sheet && !sheetOpen && finished &&
              <button onClick={() => setSheetOpen(true)}>Riapri scheda</button>}
            <button disabled={blocked} onClick={goNext}>
              {isLast ? 'Concludi tutorial' : finished ? 'Avanti →' : 'Salta →'}
            </button>
          </nav>
          <div className="top-strip__buttons">
            <button className="hand-drawer__toggle top-strip__button--secondary" onClick={onClose}>Esci dal tutorial</button>
          </div>
        </div>
        <div className="app__main">
          <div className="app__board-wrapper">
            {view && <BoardView view={view} decision={liveDecision} selected={selected}
              onToggle={toggleSelected} onSubmit={handleAnswer}
              stagedCorruptionAction={stagedCorruptionAction}
              activeBrawlHoodId={view.active_brawl_hood_id}
              activeBrawlParticipantIds={view.active_brawl_participant_ids}
              activeBrawlResolved={view.active_brawl_resolved}
              overlay={<TutorialMarkers markers={activeMarkers.filter((a) => !a.area || a.area === 'board')} />} />}
            {ready && finished && scenario.sheet && sheetOpen &&
              <TutorialSheet sheet={scenario.sheet} onClose={() => setSheetOpen(false)} />}
          </div>
        </div>
      </div>
      <OutcomeModal current={outcomeQueue[0] ?? null} onDismiss={dismissOutcome} />
    </div>
  );
}
