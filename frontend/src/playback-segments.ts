// How one step of the game (what a bot did, what another player did) becomes a segment the
// turn playback narrates and then reveals: the beats to say, the board to show after them, the
// flights and flashes that go with it. Shared by the solo game (one `advance` call per bot action)
// and the multiplayer game (one event batch per action), so both tell it the same way.

import type { LogEntry } from './components/ActionLogDrawer';
import { skillUsesFromEvents, type SkillUse } from './components/SkillUsePopup';
import {
  buildTurnBeats,
  settleMsForEvents,
  type PlaybackSegment,
} from './components/TurnPlayback';
import { playerTeamNameForId } from './assets';
import { buildBoardHighlights } from './board-highlights';
import { buildDopeTransfers } from './dope-transfers';
import { buildJailEvasionHoldView } from './jail-evasion';
import { describeActionEvents, describeOutcomeEvents } from './log-narration';
import { buildOfficerEntries, buildOfficerPurchases } from './officer-entries';
import { actionSoundUrlsForEvents, soundUrlsForPlaybackEvents } from './sound';
import type { GameEventResponse, GameViewResponse } from './types';

// Combines the action-line and outcome-line narration (log-narration.ts)
// into one LogEntry[] batch for a single response's events — ids are
// scoped to that response's own revision (strictly increasing per game),
// so they stay unique across the whole game without a separate counter.
export function makeLogEntries(
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

export interface NarratedStep {
  segment: PlaybackSegment;
  skillUses: SkillUse[];
  logEntries: LogEntry[];
  /** Who has just been narrated, or `lastNarratedPlayerId` again when the step had nothing to say. */
  narratedPlayerId: string | null;
}

/** One acted step: `previousView` is the board before it, `view` the board after it. A segment is
 *  one *action*: the "Turno di X" header belongs only to the first narrated segment of a turn,
 *  which is what `lastNarratedPlayerId` is for. */
export function narrateStep(args: {
  events: GameEventResponse[];
  actingPlayerId: string;
  previousView: GameViewResponse;
  view: GameViewResponse;
  lastNarratedPlayerId: string | null;
}): NarratedStep {
  const { events, actingPlayerId, previousView, view, lastNarratedPlayerId } = args;
  const holdView = buildJailEvasionHoldView(events, previousView) ?? undefined;
  const beats = buildTurnBeats(events, actingPlayerId, view, lastNarratedPlayerId !== actingPlayerId);
  return {
    segment: {
      beats,
      settleMs: settleMsForEvents(events),
      view,
      dopeTransfers: buildDopeTransfers(events, previousView),
      officerEntries: buildOfficerEntries(events, view),
      officerPurchases: buildOfficerPurchases(events, previousView, view),
      highlights: buildBoardHighlights(events, previousView),
      viewSoundUrls: soundUrlsForPlaybackEvents(
        holdView ? events.filter((e) => e.event_type !== 'PawnArrested') : events,
        actingPlayerId,
      ),
      holdSoundUrls: holdView
        ? actionSoundUrlsForEvents(events.filter((e) => e.event_type === 'PawnArrested'))
        : undefined,
      holdView,
    },
    skillUses: skillUsesFromEvents(events),
    logEntries: makeLogEntries(events, actingPlayerId, view),
    narratedPlayerId: beats.length > 0 ? actingPlayerId : lastNarratedPlayerId,
  };
}

/** The player is about to pick their Grit / Link: the turn has really passed to them (not that
 *  they were pulled into a Rissa or Poker in the middle of somebody else's turn). */
export function startsTurnOf(view: GameViewResponse, playerId: string): boolean {
  const decisionType = view.pending_decision?.decision_type;
  return (
    view.status !== 'finished' &&
    view.current_player_id === playerId &&
    (decisionType === 'choose_grit_action' || decisionType === 'spend_link_for_extra_action')
  );
}

/** "Turno di <squadra>" for the player's own turn, as a segment of its own. */
export function turnHeaderSegment(view: GameViewResponse, playerId: string): PlaybackSegment {
  return {
    beats: [
      {
        key: 'turn-header',
        text: `Turno di ${playerTeamNameForId(playerId)}`,
        playerId,
      },
    ],
    view,
    settleMs: 0,
  };
}
