// Turns what the server reports (event batches, each with the board right after it) into what the
// screen plays: the same segments the solo game builds from its bot cascade, so another player's
// action is narrated and revealed exactly like a bot's.

import type { LogEntry } from '../components/ActionLogDrawer';
import type { SkillUse } from '../components/SkillUsePopup';
import type { PlaybackSegment } from '../components/TurnPlayback';
import { narrateStep, startsTurnOf, turnHeaderSegment } from '../playback-segments';
import type { GameViewResponse } from '../types';
import type { EventBatchResponse } from './types';

export interface Ingested {
  segments: PlaybackSegment[];
  skillUses: SkillUse[];
  logEntries: LogEntry[];
  /** The board after the last step that had one (`previousView` if none did). */
  finalView: GameViewResponse;
  /** Revision of the last batch taken into account: the next poll starts from there. */
  lastRevision: number;
  /** Who was narrated last: a turn's "Turno di X" header is said once, not on every action. */
  lastNarratedPlayerId: string | null;
}

/** Plays `batches` after `previousView`, skipping those at or before `afterRevision` (a poll that
 *  was already in flight when the answer to our own move came back). A batch too old to still have
 *  its board is passed over: the next one that has it shows the game as it was then. */
export function ingestBatches(args: {
  batches: EventBatchResponse[];
  afterRevision: number;
  previousView: GameViewResponse;
  lastNarratedPlayerId: string | null;
  myPlayerId: string;
}): Ingested {
  const { batches, afterRevision, myPlayerId } = args;
  const segments: PlaybackSegment[] = [];
  const skillUses: SkillUse[] = [];
  const logEntries: LogEntry[] = [];
  let view = args.previousView;
  let narrated = args.lastNarratedPlayerId;
  let revision = afterRevision;

  for (const batch of batches) {
    if (batch.revision_to <= revision) continue;
    revision = batch.revision_to;
    if (!batch.view) continue;

    if (batch.segment_type === 'seat_left') {
      const leaver = batch.view.players.find((p) => p.player_id === batch.actor_player_id);
      logEntries.push({
        id: `${batch.view.revision}-left`,
        text: `${leaver?.display_name ?? 'Un giocatore'} ha lasciato la partita: ora gioca un bot.`,
      });
      segments.push({ beats: [], view: batch.view, settleMs: 0 });
      view = batch.view;
      continue;
    }

    const step = narrateStep({
      events: batch.events,
      actingPlayerId: batch.actor_player_id ?? batch.view.current_player_id,
      previousView: view,
      view: batch.view,
      lastNarratedPlayerId: narrated,
    });
    narrated = step.narratedPlayerId;
    segments.push(step.segment);
    skillUses.push(...step.skillUses);
    logEntries.push(...step.logEntries);
    view = batch.view;
  }

  // The turn has really passed to the player: say so, like the solo game does.
  if (segments.length > 0 && startsTurnOf(view, myPlayerId)) {
    segments.push(turnHeaderSegment(view, myPlayerId));
  }
  return {
    segments,
    skillUses,
    logEntries,
    finalView: view,
    lastRevision: revision,
    lastNarratedPlayerId: narrated,
  };
}
