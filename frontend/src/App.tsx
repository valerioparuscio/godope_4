import { useEffect, useRef, useState } from 'react';
import './App.css';
import './responsive.css';
import './popup-theme.css';
import { ToolbarButtonContent } from './components/ToolbarButtonContent';
import { ToolbarMenu } from './components/ToolbarMenu';
import { advanceGame, answerDecision, createGame, getView, undoLastCommand } from './api';
import { ActionLogDrawer, type LogEntry } from './components/ActionLogDrawer';
import { BoardView } from './components/BoardView';
import { ResourceFlights } from './components/ResourceFlights';
import { DecisionPanel } from './components/DecisionPanel';
import { ActionChooser } from './components/ActionChooser';
import { useHumanActionPlan } from './useHumanActionPlan';
import { FinishedScreen } from './components/FinishedScreen';
import { HandDrawer } from './components/HandDrawer';
import { OutcomeModal } from './components/OutcomeModal';
import { PlayerStrip } from './components/PlayerStrip';
import { RaidBanner } from './components/RaidBanner';
import { RulesModal } from './components/rules/RulesModal';
import { SetupScreen } from './components/SetupScreen';
import { SkillsDrawer } from './components/SkillsDrawer';
import { skillUsesFromEvents, SkillUsePopup, type SkillUse } from './components/SkillUsePopup';
import {
  buildTurnBeats,
  settleMsForEvents,
  soundUrlsForDopeEvents,
  TurnPlayback,
  type PlaybackSegment,
} from './components/TurnPlayback';
import { playerColorForId, playerTeamNameForId } from './assets';
import { applyBoardLayout } from './board-layout';
import { friendlyErrorMessage } from './error-messages';
import { buildDopeTransfers, type DopeTransfer } from './dope-transfers';
import { buildOfficerEntries, buildOfficerPurchases, type OfficerEntry, type OfficerPurchase } from './officer-entries';
import { buildJailEvasionHoldView, JAIL_EVASION_HOLD_MS, sleep } from './jail-evasion';
import { describeActionEvents, describeOutcomeEvents } from './log-narration';
import { collectFreshOutcomes, createOutcomeTracker, type QueuedOutcome } from './outcome-queue';
import { actionSoundUrlsForEvents, playSound, soundUrlsForPlaybackEvents } from './sound';
import type { DomainErrorResponse, GameEventResponse, GameViewResponse, Ruleset } from './types';
import { useBackgroundMusic } from './useBackgroundMusic';

type AppError = DomainErrorResponse | string;

const ACTION_PACKAGE_TYPES = new Set([
  'place_criminal', 'move_criminal', 'buy_dope', 'sell_dope',
  'corrupt_officer', 'buy_officer',
  // Marketing too: the top message shows how many Stonks are spent ("1/4").
  'play_marketing_card',
]);

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
  // True for a brand-new game: the human's own first turn is announced even
  // when no bot played before it.
  announceFirstHumanTurn = false,
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
  // A segment is one *action* (see GameService.advance): the "Turno giocatore
  // X" header belongs only to the first narrated segment of a bot's turn.
  let lastNarratedPlayerId: string | null = null;
  while (latestView.status !== 'finished' && latestView.current_player_id !== humanPlayerId) {
    const actingPlayerId = latestView.current_player_id;
    const advanced = await advanceGame(gameId, humanPlayerId, true);
    if (!advanced.ok) {
      setError(advanced.error ?? 'Errore durante il turno degli avversari.');
      break;
    }
    if (!advanced.view) break;
    const holdView = buildJailEvasionHoldView(advanced.events, latestView) ?? undefined;
    const beats = buildTurnBeats(
      advanced.events,
      actingPlayerId,
      advanced.view,
      lastNarratedPlayerId !== actingPlayerId,
    );
    if (beats.length > 0) lastNarratedPlayerId = actingPlayerId;
    segments.push({
      beats,
      settleMs: settleMsForEvents(advanced.events),
      view: advanced.view,
      dopeTransfers: buildDopeTransfers(advanced.events, latestView),
      officerEntries: buildOfficerEntries(advanced.events, advanced.view),
      officerPurchases: buildOfficerPurchases(advanced.events, latestView, advanced.view),
      viewSoundUrls: soundUrlsForPlaybackEvents(
        holdView ? advanced.events.filter((e) => e.event_type !== 'PawnArrested') : advanced.events,
        actingPlayerId,
      ),
      holdSoundUrls: holdView
        ? actionSoundUrlsForEvents(advanced.events.filter((e) => e.event_type === 'PawnArrested'))
        : undefined,
      holdView,
    });
    skillUses.push(...skillUsesFromEvents(advanced.events));
    logEntries.push(...makeLogEntries(advanced.events, actingPlayerId, advanced.view));
    latestView = advanced.view;
  }
  // "Turno di <squadra>" before the human's own turn too — when the turn really
  // passes to them (after bots acted, or at the very start of the game) and
  // they are about to pick their Grit / Link, not when they were pulled into a
  // Rissa or Poker mid-way through a bot's turn.
  const decisionType = latestView.pending_decision?.decision_type;
  const humanTurnStarts =
    latestView.status !== 'finished' &&
    latestView.current_player_id === humanPlayerId &&
    (decisionType === 'choose_grit_action' || decisionType === 'spend_link_for_extra_action');
  if (humanTurnStarts && (segments.length > 0 || announceFirstHumanTurn)) {
    segments.push({
      beats: [
        {
          key: 'turn-header',
          text: `Turno di ${playerTeamNameForId(humanPlayerId)}`,
          playerId: humanPlayerId,
        },
      ],
      view: latestView,
      settleMs: 0,
    });
  }
  return { finalView: latestView, segments, skillUses, logEntries };
}

function App() {
  const [activeGame, setActiveGame] = useState<ActiveGame | null>(null);
  const { muted: musicMuted, toggleMuted: toggleMusicMuted } = useBackgroundMusic(!!activeGame);
  const [rawView, setView] = useState<GameViewResponse | null>(null);
  // Position tables for the active game mode, set before any child renders.
  applyBoardLayout(activeGame ? (rawView?.ruleset_id ?? 'standard') : 'standard');
  const [dopeTransfers, setDopeTransfers] = useState<DopeTransfer[]>([]);
  const [officerEntries, setOfficerEntries] = useState<OfficerEntry[]>([]);
  const [officerPurchases, setOfficerPurchases] = useState<OfficerPurchase[]>([]);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [stagedAction, setStagedAction] = useState<string | null>(null);
  const [stagedCorruptionAction, setStagedCorruptionAction] = useState<string | null>(null);
  const [playbackSegments, setPlaybackSegments] = useState<PlaybackSegment[] | null>(null);
  const planner = useHumanActionPlan(rawView, !playbackSegments && rawView?.current_player_id === activeGame?.humanPlayerId);
  const view = planner.view;
  const [skillUseQueue, setSkillUseQueue] = useState<SkillUse[]>([]);
  const [finishedOverlayClosed, setFinishedOverlayClosed] = useState(false);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  // Ids of the log entries added by each of the human's own last few
  // moves, most recent last, mirroring the backend's own undo stack
  // (raised from a single slot to up to 4, 2026-09-02) one-to-one: a
  // successful undo pops exactly the entries added by the move it just
  // reverted, so repeated undos peel the log back the same way they peel
  // the game state back, instead of leaving stale entries behind after
  // the 2nd+ undo. Reset to empty whenever a response's own
  // `undo_available` comes back false — the backend is the sole source
  // of truth for *when* the stack is invalidated (a bot's reaction, a
  // card draw/Skill grant/Hood reveal, or the last undo emptying it); the
  // frontend never re-derives that condition itself, only mirrors it.
  const [moveEntryIdsStack, setMoveEntryIdsStack] = useState<string[][]>([]);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [rulesInitialSlug, setRulesInitialSlug] = useState<string | null>(null);

  // Every Rissa/Poker/Retata recap and "Turno N" announcement waiting on
  // the player's own OK, oldest first — owned here (not by OutcomeModal
  // itself anymore) so `TurnPlayback` can be gated on it in the exact
  // same render pass it changes in (`paused={outcomeQueue.length > 0}`
  // below), with no reactive round-trip through a sibling component's own
  // effect for it to race ahead of (game designer, 2026-09-26: "senza
  // quell'ok dato dal giocatore il gioco non deve proseguire" — the bot
  // was visibly already playing the next turn under a still-open popup).
  const [outcomeQueue, setOutcomeQueue] = useState<QueuedOutcome[]>([]);
  const outcomeTracker = useRef(createOutcomeTracker());

  // The one place a fresh `GameViewResponse` — from the human's own move,
  // a bot cascade's final view, undo, or a TurnPlayback segment stepping
  // forward — enters app state, so every one of those sources feeds the
  // same outcome queue uniformly.
  // Brawl/Poker/Raid results hold back the board itself, not just the
  // popup: the recap shows over the *previous* board, and the real one
  // (winner's hook, losers in Jail...) is only revealed once the player
  // dismisses the last queued popup (game designer, 2026-10-01).
  const outcomeQueueRef = useRef<QueuedOutcome[]>([]);
  const heldView = useRef<{
    view: GameViewResponse;
    transfers?: DopeTransfer[];
    entries?: OfficerEntry[];
    purchases?: OfficerPurchase[];
  } | null>(null);

  function updateOutcomeQueue(next: QueuedOutcome[]) {
    outcomeQueueRef.current = next;
    setOutcomeQueue(next);
  }

  function showView(newView: GameViewResponse, transfers?: DopeTransfer[], entries?: OfficerEntry[], purchases?: OfficerPurchase[]) {
    setView(newView);
    setDopeTransfers(transfers ?? []);
    setOfficerEntries(entries ?? []);
    setOfficerPurchases(purchases ?? []);
  }

  function applyView(newView: GameViewResponse, transfers?: DopeTransfer[], entries?: OfficerEntry[], purchases?: OfficerPurchase[]) {
    const fresh = collectFreshOutcomes(newView, outcomeTracker.current);
    const hasResult = fresh.some((o) => o.kind === 'brawl' || o.kind === 'poker' || o.kind === 'poker_fizzle' || o.kind === 'raid');
    if (fresh.length > 0) updateOutcomeQueue([...outcomeQueueRef.current, ...fresh]);
    if (hasResult || (heldView.current && outcomeQueueRef.current.length > 0)) {
      heldView.current = { view: newView, transfers, entries, purchases };
      return;
    }
    showView(newView, transfers, entries, purchases);
  }

  function dismissOutcome() {
    const next = outcomeQueueRef.current.slice(1);
    updateOutcomeQueue(next);
    const held = heldView.current;
    if (next.length === 0 && held) {
      heldView.current = null;
      showView(held.view, held.transfers, held.entries, held.purchases);
      // Announcements (new turn, new Raid) held back while the results
      // above were still pending — now that the board shows them.
      const announcements = collectFreshOutcomes(held.view, outcomeTracker.current);
      if (announcements.length > 0) updateOutcomeQueue(announcements);
    }
  }

  function openRules(slug?: string) {
    setRulesInitialSlug(slug ?? null);
    setRulesOpen(true);
  }

  function dismissSkillUse(key: string) {
    setSkillUseQueue((prev) => prev.filter((u) => u.key !== key));
  }

  const decisionId = view?.pending_decision?.decision_id;
  useEffect(() => { setStagedAction(null); }, [rawView?.pending_decision?.decision_id]);
  useEffect(() => {
    setSelected([]);
    setStagedCorruptionAction(null);
  }, [decisionId, planner.optionalKind, planner.plan]);

  // TEMP DIAGNOSTIC (bug report 2026-08-27: "compra" leaves the player
  // stuck, can't pass/undo) — remove once reproduced. Dumps the exact
  // decision + undo_available to the console whenever it happens live.
  useEffect(() => {
    if (view?.pending_decision?.decision_type === 'buy_officer') {
      // eslint-disable-next-line no-console
      console.log('[buy_officer debug]', JSON.stringify({
        decision: view.pending_decision,
        undo_available: view.undo_available,
        current_player_id: view.current_player_id,
      }, null, 2));
    }
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

  async function handleStart(
    seed: number,
    humanSeat: number,
    nickname: string,
    ruleset: Ruleset,
  ) {
    setStarting(true);
    setError(null);
    try {
      const created = await createGame(seed, humanSeat, nickname, ruleset);
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
        true,
      );
      if (skillUses.length > 0) setSkillUseQueue((prev) => [...prev, ...skillUses]);
      if (botLogEntries.length > 0) setLogEntries((prev) => [...prev, ...botLogEntries]);
      if (segments.length > 0) {
        applyView(freshView);
        setPlaybackSegments(segments);
      } else {
        applyView(finalView);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  }

  async function handleAnswer(selectedOptionIds: string[]) {
    if (!activeGame || !rawView?.pending_decision || submitting || planner.loading) return;
    if (planner.optionalKind === 'marketing' && selectedOptionIds.length === 0) {
      planner.toggleOptional('marketing');
      return;
    }
    if (planner.plan && !planner.optionalKind && selectedOptionIds.length > 0 &&
      ['choose_grit_action', 'choose_action_type'].includes(view?.pending_decision?.decision_type ?? '')) {
      await planner.stage([...planner.prefix, selectedOptionIds]);
      return;
    }
    if (planner.plan && selectedOptionIds.length === 0 &&
      ['launch_poker', 'play_customer_card_boost'].includes(view?.pending_decision?.decision_type ?? '')) {
      await planner.stage([...planner.prefix, []]);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await answerDecision(
        activeGame.gameId,
        activeGame.humanPlayerId,
        rawView.pending_decision.decision_id,
        selectedOptionIds,
        planner.prefix,
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
      // Jail Evasion held for 2s first (see jail-evasion.ts) when the
      // human's own move is what triggered it — the bot-cascade path
      // right below gets the same treatment per-segment, via TurnPlayback.
      const held = buildJailEvasionHoldView(result.events, rawView);
      if (held) {
        applyView(held);
        actionSoundUrlsForEvents(result.events.filter((e) => e.event_type === 'PawnArrested')).forEach(playSound);
        await sleep(JAIL_EVASION_HOLD_MS);
      }
      applyView(result.view, buildDopeTransfers(result.events, rawView),
        buildOfficerEntries(result.events, result.view),
        buildOfficerPurchases(result.events, rawView, result.view));
      soundUrlsForDopeEvents(result.events).forEach(playSound);
      actionSoundUrlsForEvents(
        held ? result.events.filter((e) => e.event_type !== 'PawnArrested') : result.events,
      ).forEach(playSound);
      const ownSkillUses = skillUsesFromEvents(result.events);
      if (ownSkillUses.length > 0) setSkillUseQueue((prev) => [...prev, ...ownSkillUses]);
      const ownLogEntries = makeLogEntries(result.events, activeGame.humanPlayerId, result.view);
      if (ownLogEntries.length > 0) {
        setLogEntries((prev) => [...prev, ...ownLogEntries]);
      }
      setMoveEntryIdsStack(
        result.view.undo_available
          ? (prev) => [...prev, ownLogEntries.map((e) => e.id)]
          : [],
      );

      const { finalView, segments, skillUses, logEntries: botLogEntries } = await resolveBotsAndNarrate(
        activeGame.gameId,
        activeGame.humanPlayerId,
        result.view,
        setError,
      );
      if (skillUses.length > 0) setSkillUseQueue((prev) => [...prev, ...skillUses]);
      if (botLogEntries.length > 0) setLogEntries((prev) => [...prev, ...botLogEntries]);
      // Any bot dispatched during this cascade invalidates the backend's
      // whole undo stack (see App's own `moveEntryIdsStack` comment) —
      // `result.view` above only reflects the state right after the
      // human's own move, before bots got a chance to react, so it can't
      // tell us that on its own.
      if (!finalView.undo_available) setMoveEntryIdsStack([]);
      if (segments.length > 0) {
        setPlaybackSegments(segments);
      } else if (finalView !== result.view) {
        // No bot acted: `finalView` is the very view applied above together
        // with this move's Dope/officer transfers. Re-applying it without
        // them would reset those transfers before their flights could start
        // (e.g. Jail Dope flying back to the Covo on an Evasion).
        applyView(finalView);
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
      if (result.view) {
        setDopeTransfers([]);
        setOfficerEntries([]);
        applyView(result.view);
      }
      const undoneEntryIds = moveEntryIdsStack[moveEntryIdsStack.length - 1];
      if (undoneEntryIds && undoneEntryIds.length > 0) {
        setLogEntries((prev) => prev.filter((e) => !undoneEntryIds.includes(e.id)));
      }
      setMoveEntryIdsStack(
        result.view?.undo_available ? (prev) => prev.slice(0, -1) : [],
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleBack() {
    if (submitting || planner.loading || playbackSegments) return;
    if (planner.optionalKind) {
      planner.toggleOptional(planner.optionalKind);
      return;
    }
    if (selected.length > 0 || stagedCorruptionAction) {
      setSelected([]);
      setStagedCorruptionAction(null);
      return;
    }
    if (planner.plan) {
      const lastChoice = planner.prefix.findLastIndex((selection) => selection.length > 0);
      if (lastChoice >= 0) {
        setStagedAction(null);
        void planner.stage(planner.prefix.slice(0, lastChoice));
        return;
      }
    }
    if (stagedAction) { setStagedAction(null); return; }
    if (rawView?.undo_available) void handleUndo();
  }

  function handlePlaybackDone() {
    setPlaybackSegments(null);
  }

  function handleNewGame() {
    setActiveGame(null);
    setView(null);
    setDopeTransfers([]);
    setOfficerEntries([]);
    setError(null);
    setFinishedOverlayClosed(false);
    setLogEntries([]);
    setMoveEntryIdsStack([]);
    heldView.current = null;
    updateOutcomeQueue([]);
    outcomeTracker.current = createOutcomeTracker();
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

  const choosingAction = !!planner.plan && !planner.optionalKind &&
    ['choose_grit_action', 'choose_action_type'].includes(view.pending_decision?.decision_type ?? '');
  const canGoBack = !!planner.optionalKind || selected.length > 0 || !!stagedCorruptionAction ||
    !!stagedAction || planner.prefix.some((selection) => selection.length > 0) || !!rawView?.undo_available;
  const optionalChoices = planner.plan?.optional ?? [];
  const roundEndDecision = planner.plan?.view.pending_decision;
  const canEndTurn = roundEndDecision?.decision_type === 'spend_link_for_extra_action'
    && roundEndDecision.can_pass && (!planner.optionalKind || planner.optionalKind === 'link');
  const showEndTurn = canEndTurn && !submitting && !planner.loading && !playbackSegments
    && view.status !== 'finished';

  return (
    <div className="app">
      <aside className="app__sidebar">
        <RaidBanner view={view} />
        <PlayerStrip
          view={view}
          decision={view.status === 'finished' ? null : view.pending_decision}
          selected={selected}
          onToggle={toggleSelected}
        />
      </aside>

      <div className={`app__play-area human-theme--${playerColorForId(activeGame.humanPlayerId)}`}>
        <div className="top-strip">
          <div className="top-strip__primary-buttons" aria-label="Carte e Skill">
            <HandDrawer
              view={view}
              autoOpen={!planner.plan?.optional.some((option) => option.kind === 'marketing')}
              decision={view.status === 'finished' ? null : view.pending_decision}
              selected={selected}
              onToggle={toggleSelected}
              onSubmit={handleAnswer}
            />
            <SkillsDrawer view={view} humanPlayerId={activeGame.humanPlayerId} />
          </div>
          <div className={'top-strip__decision-area human-controls' + (playbackSegments ? ' human-controls--playback' : choosingAction ? ' human-controls--choosing' : ' human-controls--action')}>
            {playbackSegments && view.status !== 'finished' && (
              <TurnPlayback
                segments={playbackSegments}
                onApplyView={applyView}
                onDone={handlePlaybackDone}
                paused={outcomeQueue.length > 0}
              />
            )}
            {!playbackSegments && (
              <>
                {error && <p className="error">{friendlyErrorMessage(error)}</p>}
                {planner.error && <p className="error">{planner.error}</p>}
                <div className={'human-controls__body' + (showEndTurn ? ' human-controls__body--end-turn' : '')}>
                  <div className="human-controls__main">
                    {view.status !== 'finished' &&
                      (planner.loading && !planner.plan ? <p>Preparo le azioni…</p> : choosingAction && planner.plan ? (
                        <ActionChooser key={rawView?.pending_decision?.decision_id} plan={planner.plan}
                          disabled={submitting || planner.loading} onStage={planner.stage} onPass={() => handleAnswer([])}
                          action={stagedAction} onSelectAction={setStagedAction}
                          onSelectLink={() => planner.toggleOptional('link')} />
                      ) : canEndTurn && !planner.optionalKind ? (
                        <button type="button" className="action-chooser__box action-chooser__box--link human-controls__round-link"
                          disabled={submitting || planner.loading || !optionalChoices.some((option) => option.kind === 'link')}
                          onClick={() => planner.toggleOptional('link')}>GANCIO</button>
                      ) : view.pending_decision ? (
                        <div className="decision-message-shell">
                          <DecisionPanel
                            key={`${view.pending_decision.decision_id}:${planner.optionalKind ?? ''}`}
                            decision={view.pending_decision}
                            view={view}
                            selected={selected}
                            onToggle={toggleSelected}
                            onSubmit={handleAnswer}
                            submitting={submitting || planner.loading}
                            compactOptional={!!planner.optionalKind}
                            guidanceInCorner
                            stagedCorruptionAction={stagedCorruptionAction}
                            onStageCorruptionAction={setStagedCorruptionAction}
                          />
                          {ACTION_PACKAGE_TYPES.has(view.pending_decision.decision_type) && view.pending_decision.max_selections > 0 && (
                            <div className="decision-message-shell__progress" aria-label={`${selected.length} di ${view.pending_decision.max_selections} scelte effettuate`}>
                              {selected.length}/{view.pending_decision.max_selections}
                            </div>
                          )}
                        </div>
                      ) : null)}
                  </div>
                  {showEndTurn && (
                    <button className="human-controls__end-turn" onClick={() => handleAnswer([])}>
                      Fine turno
                    </button>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="top-strip__optional-actions" aria-label="Azioni aggiuntive">
            {(['marketing', 'poker'] as const).map((kind) => <button key={kind}
              className={`top-strip__optional-button top-strip__optional-button--tool top-strip__optional-button--${kind}`}
              disabled={submitting || planner.loading || !!playbackSegments || view.status === 'finished' || !optionalChoices.some((option) => option.kind === kind)}
              aria-pressed={planner.optionalKind === kind}
              onClick={() => planner.toggleOptional(kind)}>
              <ToolbarButtonContent icon={kind === 'marketing' ? 'stonk' : 'poker'}
                label={kind === 'marketing' ? 'Marketing' : 'Poker'} />
            </button>)}
            <button className="top-strip__optional-button top-strip__optional-button--back" title="Torna indietro" aria-label="Torna indietro"
              disabled={!canGoBack || submitting || planner.loading || !!playbackSegments || view.status === 'finished'}
              onClick={handleBack}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4 4 9l5 5M4 9h9a7 7 0 0 1 0 14" /></svg>
              <span>Torna indietro</span>
            </button>
          </div>

          <ToolbarMenu>
            <ActionLogDrawer entries={logEntries} />
            <button className="hand-drawer__toggle top-strip__button--secondary" onClick={() => openRules()}>
              <ToolbarButtonContent icon="rules" label="Regolamento" />
            </button>
            <button
              className="hand-drawer__toggle top-strip__button--secondary"
              onClick={toggleMusicMuted}
              aria-pressed={!musicMuted}
              aria-label={musicMuted ? 'Attiva musica' : 'Disattiva musica'}
            >
              <ToolbarButtonContent icon={musicMuted ? 'muted' : 'music'} label="Musica" />
            </button>
          </ToolbarMenu>
        </div>

        <div className="app__main">
          <div className="app__board-wrapper">
            <BoardView
              dopeTransfers={dopeTransfers}
              officerEntries={officerEntries}
              officerPurchases={officerPurchases}
              view={view}
              decision={view.status === 'finished' ? null : view.pending_decision}
              selected={selected}
              onToggle={toggleSelected}
              onSubmit={handleAnswer}
              stagedCorruptionAction={stagedCorruptionAction}
              activeBrawlHoodId={view.active_brawl_hood_id}
              activeBrawlParticipantIds={view.active_brawl_participant_ids}
              activeBrawlResolved={view.active_brawl_resolved}
            />
          </div>
        </div>

        <ResourceFlights dopeTransfers={dopeTransfers} officerPurchases={officerPurchases} />

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
      <OutcomeModal current={outcomeQueue[0] ?? null} onDismiss={dismissOutcome} />
      <RulesModal open={rulesOpen} initialSlug={rulesInitialSlug} onClose={() => setRulesOpen(false)} />
    </div>
  );
}

export default App;
