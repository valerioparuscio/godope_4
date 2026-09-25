import { useEffect, useState } from 'react';
import { advanceGame, answerDecision, createTutorialGame, getView } from '../api';
import { TUTORIAL_SCENARIOS } from '../tutorial/scenarios';
import type { GameViewResponse } from '../types';
import { BoardView } from './BoardView';
import { DecisionPanel } from './DecisionPanel';
import { HandDrawer } from './HandDrawer';
import { OutcomeModal } from './OutcomeModal';
import { PlayerStrip } from './PlayerStrip';

interface TutorialModalProps {
  open: boolean;
  onClose: () => void;
}

// Safety cap on the bot-advance loop below — a Rissa's own declare/
// assign/reward round-robin is a handful of steps, never dozens.
const MAX_ADVANCE_STEPS = 12;

// Each card is a real, playable sandbox game (game designer, 2026-09-24:
// "sarebbe meglio se si potesse cliccare realmente, come se ciascuna
// scheda fosse una mini partita che fa solo quella mossa") — created via
// createTutorialGame, then driven with the exact same BoardView/
// DecisionPanel/HandDrawer components and answerDecision call a real
// game uses.
//
// Most cards stop dead on the human's own single move. A card marked
// `resolvesWith` instead keeps running: it advances the bots, hands each
// further step back to the human, and finishes on the event's own recap
// popup (the same OutcomeModal a real game shows) — the Rissa card needs
// the other 3 participants to declare before it can resolve.
export function TutorialModal({ open, onClose }: TutorialModalProps) {
  const [index, setIndex] = useState(0);
  const [gameId, setGameId] = useState<string | null>(null);
  const [view, setView] = useState<GameViewResponse | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [stagedCorruptionAction, setStagedCorruptionAction] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scenario = TUTORIAL_SCENARIOS[index];

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setSelected([]);
    setStagedCorruptionAction(null);
    setDone(false);
    setError(null);
    setView(null);
    setGameId(null);
    (async () => {
      try {
        const created = await createTutorialGame(scenario.id);
        if (cancelled) return;
        setGameId(created.game_id);
        const freshView = await getView(created.game_id, 'player_0');
        if (cancelled) return;
        setView(freshView);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, index]);

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
    if (!gameId || !view?.pending_decision) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await answerDecision(
        gameId,
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
          const advanced = await advanceGame(gameId, 'player_0');
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

  if (!open) return null;

  const isLast = index + 1 >= TUTORIAL_SCENARIOS.length;

  return (
    <div className="tutorial-overlay">
      <div className="tutorial-modal">
        <div className="tutorial-modal__header">
          <span className="tutorial-modal__progress">
            {index + 1}/{TUTORIAL_SCENARIOS.length}
          </span>
          <h3>{scenario.title}</h3>
          <button className="tutorial-modal__close" onClick={onClose} aria-label="Chiudi tutorial">
            ×
          </button>
        </div>
        <p className="tutorial-modal__instruction">{scenario.instruction}</p>
        {error && <p className="error">{error}</p>}

        {view && (
          <>
            {/* On top, same place the real game keeps it (the top strip):
                at the bottom, the hand drawer's floating card panel covered
                its "Conferma" button, so a hand-card package (discarding
                2 cards) could be selected but never confirmed. */}
            {!done && view.pending_decision && (
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
            )}
            {done && <p className="tutorial-modal__outcome">✓ {scenario.outcome}</p>}
            <div className="tutorial-modal__play-area">
              {/* The player's own board, so the effect of the move is
                  visible there too (designer, 2026-09-24: "dopo buy il
                  numero di dope disponibili aumenta sulla plancia") —
                  pulsed once the move resolves to point at what changed. */}
              <div
                className={
                  'tutorial-modal__sidebar' +
                  (done ? ' tutorial-modal__sidebar--changed' : '')
                }
              >
                <span className="tutorial-modal__sidebar-label">La tua plancia</span>
                <PlayerStrip view={view} decision={null} onlyPlayerId="player_0" />
              </div>
              <div className="tutorial-modal__board">
                <BoardView
                  view={view}
                  decision={done ? null : view.pending_decision}
                  selected={selected}
                  onToggle={toggleSelected}
                  onSubmit={handleAnswer}
                  stagedCorruptionAction={stagedCorruptionAction}
                />
              </div>
            </div>
            <HandDrawer
              view={view}
              decision={done ? null : view.pending_decision}
              selected={selected}
              onToggle={toggleSelected}
              onSubmit={handleAnswer}
            />
            {/* The same blocking recap a real game shows (Rissa/Poker/
                Retata) — its own overlay sits above this modal's. */}
            <OutcomeModal view={view} />
          </>
        )}

        <div className="tutorial-modal__footer">
          {done ? (
            <button className="tutorial-modal__next" onClick={goNext}>
              {isLast ? 'Fatto! Chiudi il tutorial' : 'Fatto! Prossima scheda →'}
            </button>
          ) : (
            <button className="tutorial-modal__skip" onClick={goNext}>
              {isLast ? 'Salta e chiudi' : 'Salta questa scheda'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
