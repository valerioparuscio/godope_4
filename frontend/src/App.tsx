import { useEffect, useMemo, useRef, useState } from 'react';
import './App.css';
import './responsive.css';
import './popup-theme.css';
import { ToolbarButtonContent } from './components/ToolbarButtonContent';
import { ToolbarMenu } from './components/ToolbarMenu';
import { advanceGame, answerDecision, createGame, getView, undoLastCommand } from './api';
import { BOARD_HIGHLIGHT_MS, buildBoardHighlights, type BoardHighlights } from './board-highlights';
import { ActionLogDrawer, type LogEntry } from './components/ActionLogDrawer';
import { BoardView } from './components/BoardView';
import { ResourceFlights } from './components/ResourceFlights';
import { DecisionPanel } from './components/DecisionPanel';
import { ActionChooser } from './components/ActionChooser';
import { useHumanActionPlan, type PlanFn } from './useHumanActionPlan';
import { FinishedScreen } from './components/FinishedScreen';
import { HandDrawer } from './components/HandDrawer';
import { OutcomeModal } from './components/OutcomeModal';
import { PlayerStrip } from './components/PlayerStrip';
import { RaidBanner } from './components/RaidBanner';
import { RulesModal } from './components/rules/RulesModal';
import { MultiplayerConnecting, MultiplayerWaiting } from './components/MultiplayerGame';
import { MultiplayerLobby } from './components/MultiplayerLobby';
import { SetupScreen } from './components/SetupScreen';
import { SkillsDrawer } from './components/SkillsDrawer';
import { skillUsesFromEvents, SkillUsePopup, type SkillUse } from './components/SkillUsePopup';
import {
  soundUrlsForDopeEvents,
  TurnPlayback,
  type PlaybackSegment,
} from './components/TurnPlayback';
import { playerColorForId } from './assets';
import { applyBoardLayout } from './board-layout';
import { friendlyErrorMessage } from './error-messages';
import { buildDopeTransfers, type DopeTransfer } from './dope-transfers';
import { buildOfficerEntries, buildOfficerPurchases, type OfficerEntry, type OfficerPurchase } from './officer-entries';
import { buildJailEvasionHoldView, JAIL_EVASION_HOLD_MS, sleep } from './jail-evasion';
import { makeLogEntries, narrateStep, startsTurnOf, turnHeaderSegment } from './playback-segments';
import { collectFreshOutcomes, createOutcomeTracker, type QueuedOutcome } from './outcome-queue';
import { actionSoundUrlsForEvents, playSound } from './sound';
import type { DomainErrorResponse, GameEventResponse, GameViewResponse, Ruleset } from './types';
import {
  MultiplayerApiError,
  answerGameDecision,
  getEvents,
  getGameView,
  isTransientFailure,
  leaveGame,
  planGameDecision,
} from './multiplayer/api';
import { ingestBatches } from './multiplayer/ingest';
import { roomCodeFromUrl } from './multiplayer/link';
import { multiplayerErrorMessage } from './multiplayer/messages';
import { clearSeat, loadSeat } from './multiplayer/storage';
import type { EventBatchResponse, StoredSeat } from './multiplayer/types';
import { useBackgroundMusic } from './useBackgroundMusic';

type AppError = DomainErrorResponse | string;

const ACTION_PACKAGE_TYPES = new Set([
  'place_criminal', 'move_criminal', 'buy_dope', 'sell_dope',
  'maneuver_officer', 'corrupt_officer',
  // Marketing too: the top message shows how many Stonks are spent ("1/4").
  'play_marketing_card',
]);

// How often a multiplayer screen asks the server what happened (it never moves the game).
const MP_POLL_INTERVAL_MS = 1000;
// Starting the game screen while the server is restarting: this many more tries, this far apart.
const MP_START_RETRIES = 6;
const MP_START_RETRY_MS = 2000;
const MP_RESTORED_NOTICE =
  'La partita è stata ripristinata dal server: le ultime mosse potrebbero essere andate perse.';

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
    const step = narrateStep({
      events: advanced.events,
      actingPlayerId,
      previousView: latestView,
      view: advanced.view,
      lastNarratedPlayerId,
    });
    lastNarratedPlayerId = step.narratedPlayerId;
    segments.push(step.segment);
    skillUses.push(...step.skillUses);
    logEntries.push(...step.logEntries);
    latestView = advanced.view;
  }
  // "Turno di <squadra>" before the human's own turn too — when the turn really
  // passes to them (after bots acted, or at the very start of the game) and
  // they are about to pick their Grit / Link, not when they were pulled into a
  // Rissa or Poker mid-way through a bot's turn.
  if (startsTurnOf(latestView, humanPlayerId) && (segments.length > 0 || announceFirstHumanTurn)) {
    segments.push(turnHeaderSegment(latestView, humanPlayerId));
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
  const [boardHighlights, setBoardHighlights] = useState<BoardHighlights | undefined>(undefined);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [stagedAction, setStagedAction] = useState<string | null>(null);
  const [stagedManeuverAction, setStagedManeuverAction] = useState<string | null>(null);
  const [playbackSegments, setPlaybackSegments] = useState<PlaybackSegment[] | null>(null);
  // Multiplayer (docs/architecture/GPT_MULTIPLAYER.md, phase 3): the seat this browser plays from,
  // and how far into the server's log it has got. The server plays the bots and every other
  // human; this screen only asks what happened since `lastRevisionRef`, replays it like a bot
  // cascade, and answers when the decision in front of it is ours.
  const [mp, setMp] = useState<{ seat: StoredSeat } | null>(null);
  const [mpConnectionLost, setMpConnectionLost] = useState(false);
  const lastRevisionRef = useRef(0);
  const lastViewRef = useRef<GameViewResponse | null>(null);
  const lastNarratedRef = useRef<string | null>(null);
  const submittingRef = useRef(false);
  const mpPlanFn = useMemo<PlanFn | undefined>(() => {
    const seat = mp?.seat;
    if (!seat || !seat.game_id) return undefined;
    const gameId = seat.game_id;
    return (_view, decisionId, selections) =>
      planGameDecision(gameId, seat.seat_token, decisionId, selections);
  }, [mp]);
  const planner = useHumanActionPlan(
    rawView,
    !playbackSegments &&
      (mp ? !!rawView?.pending_decision : rawView?.current_player_id === activeGame?.humanPlayerId),
    mpPlanFn,
  );
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
  // The multiplayer lobby, instead of the start screen. A shared link (`?stanza=F7KQ`) opens it
  // straight away, on that room.
  // A browser that still holds a multiplayer seat goes back to it after a reload.
  const [lobby, setLobby] = useState<{
    nickname: string;
    linkedRoom: string | null;
    resumeOnly: boolean;
  } | null>(() => {
    const linkedRoom = roomCodeFromUrl();
    if (linkedRoom) return { nickname: '', linkedRoom, resumeOnly: false };
    return loadSeat() ? { nickname: '', linkedRoom: null, resumeOnly: true } : null;
  });
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
    highlights?: BoardHighlights;
  } | null>(null);

  function updateOutcomeQueue(next: QueuedOutcome[]) {
    outcomeQueueRef.current = next;
    setOutcomeQueue(next);
  }

  function showView(newView: GameViewResponse, transfers?: DopeTransfer[], entries?: OfficerEntry[], purchases?: OfficerPurchase[], highlights?: BoardHighlights) {
    setView(newView);
    setDopeTransfers(transfers ?? []);
    setOfficerEntries(entries ?? []);
    setOfficerPurchases(purchases ?? []);
    setBoardHighlights(highlights);
  }

  // The flash on the board lasts a moment, then clears.
  useEffect(() => {
    if (!boardHighlights) return;
    const timer = setTimeout(() => setBoardHighlights(undefined), BOARD_HIGHLIGHT_MS);
    return () => clearTimeout(timer);
  }, [boardHighlights]);

  function applyView(newView: GameViewResponse, transfers?: DopeTransfer[], entries?: OfficerEntry[], purchases?: OfficerPurchase[], highlights?: BoardHighlights) {
    const fresh = collectFreshOutcomes(newView, outcomeTracker.current);
    const hasResult = fresh.some((o) => o.kind === 'brawl' || o.kind === 'poker' || o.kind === 'poker_fizzle' || o.kind === 'raid');
    if (fresh.length > 0) updateOutcomeQueue([...outcomeQueueRef.current, ...fresh]);
    if (hasResult || (heldView.current && outcomeQueueRef.current.length > 0)) {
      heldView.current = { view: newView, transfers, entries, purchases, highlights };
      return;
    }
    showView(newView, transfers, entries, purchases, highlights);
  }

  function dismissOutcome() {
    const next = outcomeQueueRef.current.slice(1);
    updateOutcomeQueue(next);
    const held = heldView.current;
    if (next.length === 0 && held) {
      heldView.current = null;
      showView(held.view, held.transfers, held.entries, held.purchases, held.highlights);
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
    setStagedManeuverAction(null);
  }, [decisionId, planner.optionalKind, planner.plan]);

  // TEMP DIAGNOSTIC (bug report 2026-08-27: "compra" leaves the player
  // stuck, can't pass/undo) — remove once reproduced. Dumps the exact
  // decision + undo_available to the console whenever it happens live.
  useEffect(() => {
    if (view?.pending_decision?.decision_type === 'corrupt_officer') {
      // eslint-disable-next-line no-console
      console.log('[corrupt_officer debug]', JSON.stringify({
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

  // The human's own move, shown right away: a Jail Evasion it triggers is held for 2s first (see
  // jail-evasion.ts), then the board it produced with its Dope/officer flights, flashes, sounds,
  // Skill popups and log lines. `base` is the board before the move; returns the log lines added.
  async function showOwnMove(
    events: GameEventResponse[],
    newView: GameViewResponse,
    base: GameViewResponse,
    actingPlayerId: string,
  ): Promise<LogEntry[]> {
    const held = buildJailEvasionHoldView(events, base);
    if (held) {
      applyView(held);
      actionSoundUrlsForEvents(events.filter((e) => e.event_type === 'PawnArrested')).forEach(playSound);
      await sleep(JAIL_EVASION_HOLD_MS);
    }
    applyView(newView, buildDopeTransfers(events, base),
      buildOfficerEntries(events, newView),
      buildOfficerPurchases(events, base, newView),
      buildBoardHighlights(events, base));
    soundUrlsForDopeEvents(events).forEach(playSound);
    actionSoundUrlsForEvents(
      held ? events.filter((e) => e.event_type !== 'PawnArrested') : events,
    ).forEach(playSound);
    const ownSkillUses = skillUsesFromEvents(events);
    if (ownSkillUses.length > 0) setSkillUseQueue((prev) => [...prev, ...ownSkillUses]);
    const ownLogEntries = makeLogEntries(events, actingPlayerId, newView);
    if (ownLogEntries.length > 0) {
      setLogEntries((prev) => [...prev, ...ownLogEntries]);
    }
    return ownLogEntries;
  }

  // ---- multiplayer -------------------------------------------------------------------------

  // Back to the start screen, forgetting the seat if the game is really gone.
  function endMultiplayer(message: string | null, forgetSeat: boolean) {
    if (forgetSeat) clearSeat();
    submittingRef.current = false;
    setMp(null);
    setMpConnectionLost(false);
    setPlaybackSegments(null);
    handleNewGame();
    if (message) setError(message);
  }

  async function handleMultiplayerGameStart(seat: StoredSeat, fresh: boolean) {
    if (!seat.game_id) return;
    setLobby(null);
    setMp({ seat });
    setActiveGame({ gameId: seat.game_id, humanPlayerId: seat.player_id });
    setError(null);
    try {
      // A server that is restarting answers "try again" for a moment: wait for it rather than
      // giving the seat up.
      const gameId = seat.game_id;
      const snapshot = await getGameView(gameId, seat.seat_token).catch(async (failure: unknown) => {
        let lastFailure = failure;
        for (let attempt = 0; attempt < MP_START_RETRIES && isTransientFailure(lastFailure); attempt++) {
          await sleep(MP_START_RETRY_MS);
          try {
            return await getGameView(gameId, seat.seat_token);
          } catch (again) {
            lastFailure = again;
          }
        }
        throw lastFailure;
      });
      const first = snapshot.view;
      outcomeTracker.current = createOutcomeTracker();
      // A game joined again after a reload has history behind it: that is not news to announce.
      if (!fresh) collectFreshOutcomes(first, outcomeTracker.current);
      lastRevisionRef.current = snapshot.revision;
      lastViewRef.current = first;
      lastNarratedRef.current = null;
      applyView(first);
      if (startsTurnOf(first, seat.player_id)) {
        setPlaybackSegments([turnHeaderSegment(first, seat.player_id)]);
      }
    } catch (failure) {
      endMultiplayer(
        multiplayerErrorMessage(failure),
        failure instanceof MultiplayerApiError && !isTransientFailure(failure),
      );
    }
  }

  // The server holds less than this screen has seen (it came back from an older snapshot after a
  // restart): its board is the truth, whatever was played on top of it is gone.
  function resyncMultiplayer(freshView: GameViewResponse, revision: number) {
    lastRevisionRef.current = revision;
    lastViewRef.current = freshView;
    lastNarratedRef.current = null;
    heldView.current = null;
    setPlaybackSegments(null);
    applyView(freshView);
    setError(MP_RESTORED_NOTICE);
    // A notice, not an error to act on: it goes by itself (a move of the player clears it too).
    setTimeout(() => setError((current) => (current === MP_RESTORED_NOTICE ? null : current)), 8000);
  }

  // What the server says happened (a poll, or the rest of the answer to our own move): replayed one
  // step at a time, like a bot cascade. Steps already taken into account are skipped.
  function playIngested(
    batches: EventBatchResponse[],
    fallbackView: GameViewResponse | null,
    currentRevision: number,
  ) {
    const previous = lastViewRef.current;
    if (!mp || !previous) return;
    const result = ingestBatches({
      batches,
      afterRevision: lastRevisionRef.current,
      previousView: previous,
      lastNarratedPlayerId: lastNarratedRef.current,
      myPlayerId: mp.seat.player_id,
    });
    lastRevisionRef.current = Math.max(result.lastRevision, 0);
    lastNarratedRef.current = result.lastNarratedPlayerId;
    if (result.segments.length > 0) {
      lastViewRef.current = result.finalView;
      setPlaybackSegments((prev) => [...(prev ?? []), ...result.segments]);
      if (result.skillUses.length > 0) setSkillUseQueue((prev) => [...prev, ...result.skillUses]);
      if (result.logEntries.length > 0) setLogEntries((prev) => [...prev, ...result.logEntries]);
    } else if (fallbackView && fallbackView.revision > previous.revision) {
      // Every step was too old to still have its board: show the game as it is now.
      lastViewRef.current = fallbackView;
      lastRevisionRef.current = currentRevision;
      applyView(fallbackView);
    }
  }

  async function submitMultiplayer(selectedOptionIds: string[]) {
    const seat = mp?.seat;
    const decision = rawView?.pending_decision;
    if (!seat || !seat.game_id || !rawView || !decision) return;
    submittingRef.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const result = await answerGameDecision(seat.game_id, seat.seat_token, {
        decisionId: decision.decision_id,
        expectedRevision: rawView.revision,
        selectedOptionIds,
        preparatorySelections: planner.prefix,
      });
      // Our own step first, right away; whatever the bots did after it is replayed.
      const [own, ...rest] = result.batches;
      if (own?.view) {
        lastRevisionRef.current = own.revision_to;
        lastViewRef.current = own.view;
        await showOwnMove(own.events, own.view, rawView, seat.player_id);
        playIngested(rest, result.view, result.revision);
      } else {
        lastRevisionRef.current = result.revision;
        lastViewRef.current = result.view;
        applyView(result.view);
      }
    } catch (failure) {
      if (failure instanceof MultiplayerApiError && failure.status === 401) {
        endMultiplayer(multiplayerErrorMessage(failure), true);
        return;
      }
      // "The game moved on" is not an error to dwell on: the next poll catches us up.
      setError(multiplayerErrorMessage(failure));
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  async function handleLeaveMultiplayer(askFirst: boolean) {
    const seat = mp?.seat;
    if (!seat) return;
    if (
      askFirst &&
      view?.status !== 'finished' &&
      !window.confirm('Uscire dalla partita? Il tuo posto passerà a un bot.')
    ) {
      return;
    }
    if (seat.game_id) {
      try {
        await leaveGame(seat.game_id, seat.seat_token);
      } catch {
        // The seat may already be gone: leaving is the goal anyway.
      }
    }
    endMultiplayer(null, true);
  }

  // Polling: ask what happened since the last step we know of, every second, until the game is over.
  // The handlers are read through a ref so the loop always calls the current ones.
  const mpLatest = useRef({
    playIngested,
    resync: resyncMultiplayer,
    onConnection: (_ok: boolean) => {},
    onSessionLost: () => {},
  });
  useEffect(() => {
    mpLatest.current = {
      playIngested,
      resync: resyncMultiplayer,
      onConnection: (ok) => setMpConnectionLost(!ok),
      onSessionLost: () =>
        endMultiplayer('La partita non esiste più o hai perso il tuo posto.', true),
    };
  });
  const mpGameId = mp?.seat.game_id ?? null;
  const mpToken = mp?.seat.seat_token ?? null;
  useEffect(() => {
    if (!mpGameId || !mpToken) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function tick() {
      if (stopped || !mpGameId || !mpToken) return;
      let again = true;
      // While our own answer is in flight, the answer brings the news.
      if (!submittingRef.current && lastViewRef.current) {
        try {
          const response = await getEvents(mpGameId, mpToken, lastRevisionRef.current);
          if (stopped) return;
          if (!submittingRef.current) {
            if (response.requires_refresh && response.view) {
              mpLatest.current.resync(response.view, response.current_revision);
            } else {
              mpLatest.current.playIngested(response.batches, response.view, response.current_revision);
            }
            mpLatest.current.onConnection(true);
            if (response.status === 'finished') again = false;
          }
        } catch (failure) {
          if (stopped) return;
          if (failure instanceof MultiplayerApiError && (failure.status === 401 || failure.status === 404)) {
            mpLatest.current.onSessionLost();
            return;
          }
          mpLatest.current.onConnection(false);
        }
      }
      if (again && !stopped) timer = setTimeout(tick, MP_POLL_INTERVAL_MS);
    }
    void tick();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [mpGameId, mpToken]);

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
    if (mp) {
      // What is on screen while the others' moves are being replayed is the past: not answerable.
      if (!playbackSegments) await submitMultiplayer(selectedOptionIds);
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
      const ownLogEntries = await showOwnMove(
        result.events,
        result.view,
        rawView,
        activeGame.humanPlayerId,
      );
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
    if (selected.length > 0 || stagedManeuverAction) {
      setSelected([]);
      setStagedManeuverAction(null);
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

  // Menu "Home": back to the start page (new game, tutorial, leaderboard). A
  // game still in progress is abandoned, so ask first.
  function handleGoHome() {
    if (mp) {
      void handleLeaveMultiplayer(true);
      return;
    }
    if (view?.status !== 'finished'
      && !window.confirm('Tornare alla home? La partita in corso andrà persa.')) return;
    setPlaybackSegments(null);
    handleNewGame();
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

  if (mp && (!activeGame || !view)) {
    return <MultiplayerConnecting message="Collego la partita…" />;
  }

  if (!activeGame && lobby) {
    return (
      <MultiplayerLobby
        initialNickname={lobby.nickname}
        initialRoomCode={lobby.linkedRoom}
        resumeOnly={lobby.resumeOnly}
        onBack={() => setLobby(null)}
        onGameStart={(seat, fresh) => void handleMultiplayerGameStart(seat, fresh)}
      />
    );
  }

  if (!activeGame || !view) {
    return (
      <SetupScreen
        onStart={handleStart}
        onMultiplayer={(nickname) => setLobby({ nickname, linkedRoom: null, resumeOnly: false })}
        starting={starting}
        error={error ? friendlyErrorMessage(error) : null}
      />
    );
  }

  const choosingAction = !!planner.plan && !planner.optionalKind &&
    ['choose_grit_action', 'choose_action_type'].includes(view.pending_decision?.decision_type ?? '');
  const canGoBack = !!planner.optionalKind || selected.length > 0 || !!stagedManeuverAction ||
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
                {mp && mpConnectionLost && <p className="error">Connessione persa: riprovo…</p>}
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
                            stagedManeuverAction={stagedManeuverAction}
                            onStageManeuverAction={setStagedManeuverAction}
                          />
                          {ACTION_PACKAGE_TYPES.has(view.pending_decision.decision_type) && view.pending_decision.max_selections > 0 && (
                            <div className="decision-message-shell__progress" aria-label={`${selected.length} di ${view.pending_decision.max_selections} scelte effettuate`}>
                              {selected.length}/{view.pending_decision.max_selections}
                            </div>
                          )}
                        </div>
                      ) : mp ? <MultiplayerWaiting view={view} /> : null)}
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
            <button className="hand-drawer__toggle top-strip__button--secondary" onClick={handleGoHome}>
              <ToolbarButtonContent icon="home" label="Home" />
            </button>
          </ToolbarMenu>
        </div>

        <div className="app__main">
          <div className="app__board-wrapper">
            <BoardView
              dopeTransfers={dopeTransfers}
              officerEntries={officerEntries}
              officerPurchases={officerPurchases}
              highlights={boardHighlights}
              view={view}
              decision={view.status === 'finished' ? null : view.pending_decision}
              selected={selected}
              onToggle={toggleSelected}
              onSubmit={handleAnswer}
              stagedManeuverAction={stagedManeuverAction}
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
            onNewGame={mp ? () => void handleLeaveMultiplayer(false) : handleNewGame}
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
