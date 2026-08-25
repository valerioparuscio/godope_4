import { useEffect, useState } from 'react';
import { dopeSoundUrl, playerColorLabelForId } from '../assets';
import {
  collectActionItems,
  MERGE_KINDS,
  resolveOfficerTypes,
  textForGroup,
  type ActionItem,
} from '../log-narration';
import { playSound } from '../sound';
import type { GameEventResponse, GameViewResponse } from '../types';

export interface TurnBeat {
  key: string;
  text: string;
  // Played once, right as this beat becomes the one on screen (2026-08-16
  // designer's request: a short sound per Dope type on every buy/sell).
  soundUrls?: string[];
}

// One bot's own turn-segment (game_service.py's advance(...,
// single_player_segment=True)): the beats to narrate for it, and the
// view to reveal once they finish playing — kept separate per segment
// (rather than one flat beat list + a single final view) so the board
// updates after *each* bot instead of jumping straight to the fully
// resolved end state once every bot has gone (designer's request,
// 2026-08-16: "se tre bot di fila piazzano non vorrei vedere comparire
// tutte le pedine alla fine, ma dopo ogni singolo bot").
export interface PlaybackSegment {
  beats: TurnBeat[];
  view: GameViewResponse;
}

function dopeSoundUrlsFor(dopeTypes: string[]): string[] {
  const urls = new Set<string>();
  for (const dopeType of new Set(dopeTypes)) {
    const url = dopeSoundUrl(dopeType);
    if (url) urls.add(url);
  }
  return Array.from(urls);
}

// For the human's own action: its dispatch-only response's events never
// go through buildTurnBeats (that's for narrated bot segments only), but
// the same short sound should still play immediately when their own
// buy/sell applies (2026-08-16 designer's request covers *every*
// occurrence, not just narrated ones).
export function soundUrlsForDopeEvents(events: GameEventResponse[]): string[] {
  const dopeTypes = events
    .filter((e) => e.event_type === 'DopeBought' || e.event_type === 'DopeSold')
    .map((e) => e.dope_type as string);
  return dopeSoundUrlsFor(dopeTypes);
}

function soundUrlsForGroup(kind: ActionItem['kind'], group: ActionItem[]): string[] | undefined {
  if (kind === 'buy') {
    return dopeSoundUrlsFor((group as Extract<ActionItem, { kind: 'buy' }>[]).map((i) => i.dopeType));
  }
  if (kind === 'sell') {
    return dopeSoundUrlsFor((group as Extract<ActionItem, { kind: 'sell' }>[]).map((i) => i.dopeType));
  }
  return undefined;
}

// Builds the "X piazza N criminali" beat list for one segment (already
// known to belong to a single acting player — game_service.py's
// single_player_segment). A "Turno giocatore X" header is prepended only
// when there's something to say; a segment with nothing narratable
// (recognized action types) produces an empty list, so it's skipped
// silently rather than flashing an empty "Turno" card.
export function buildTurnBeats(
  events: GameEventResponse[],
  actingPlayerId: string,
  view: GameViewResponse,
): TurnBeat[] {
  const items = collectActionItems(events, actingPlayerId);
  const resolvedItems = resolveOfficerTypes(items, events, actingPlayerId, view);

  if (resolvedItems.length === 0) return [];

  const beats: TurnBeat[] = [
    { key: 'turn-header', text: `Turno giocatore ${playerColorLabelForId(actingPlayerId)}` },
  ];
  let idx = 0;
  let i = 0;
  while (i < resolvedItems.length) {
    const kind = resolvedItems[i].kind;
    const group = [resolvedItems[i]];
    i++;
    if (MERGE_KINDS.has(kind)) {
      while (i < resolvedItems.length && resolvedItems[i].kind === kind) {
        group.push(resolvedItems[i]);
        i++;
      }
    }
    beats.push({
      key: `beat-${idx++}`,
      text: `${playerColorLabelForId(actingPlayerId)} ${textForGroup(kind, group, view)}`,
      soundUrls: soundUrlsForGroup(kind, group),
    });
  }
  return beats;
}

const BEAT_DURATION_MS = 2000;

// Plays each segment's beats (2s each, designer's request), revealing
// that segment's view as soon as its beats finish and *before* moving on
// to the next segment — so bot turns appear one at a time instead of all
// at once at the end. Blocks interaction the whole time (the board/panel
// underneath are stale until each segment's onApplyView fires).
export function TurnPlayback({
  segments,
  onApplyView,
  onDone,
}: {
  segments: PlaybackSegment[];
  onApplyView: (view: GameViewResponse) => void;
  onDone: () => void;
}) {
  const [segmentIndex, setSegmentIndex] = useState(0);
  const [beatIndex, setBeatIndex] = useState(0);

  const segment = segments[segmentIndex];
  const beats = segment?.beats ?? [];

  useEffect(() => {
    // Every branch goes through setTimeout+clearTimeout, even the ones
    // with no real delay — React 18 StrictMode double-invokes an
    // effect's setup on mount (dev-only: mount -> cleanup -> mount again,
    // to help surface exactly this kind of bug) and a branch with no
    // cleanup at all would have its side effect (onDone, or
    // onApplyView+setSegmentIndex) run twice, silently advancing
    // segmentIndex by 2 and skipping a segment. Scheduling everything via
    // a cancellable timer means the first (StrictMode-only) invocation's
    // timer gets cancelled before it ever fires, same as the "counting
    // down a beat" branch already relied on.
    if (segmentIndex >= segments.length) {
      const timer = setTimeout(onDone, 0);
      return () => clearTimeout(timer);
    }
    if (beatIndex >= beats.length) {
      const timer = setTimeout(() => {
        onApplyView(segment.view);
        setSegmentIndex((s) => s + 1);
        setBeatIndex(0);
      }, 0);
      return () => clearTimeout(timer);
    }
    const timer = setTimeout(() => setBeatIndex((b) => b + 1), BEAT_DURATION_MS);
    return () => clearTimeout(timer);
  }, [segmentIndex, beatIndex, segments.length, beats.length]);

  // Separate effect (its own StrictMode-safe cancellable timer) so a
  // beat's sound plays exactly once, right as that beat becomes the one
  // on screen — not tied to the lifecycle effect above, which has its own
  // unrelated branches.
  useEffect(() => {
    if (segmentIndex >= segments.length || beatIndex >= beats.length) return;
    const urls = beats[beatIndex].soundUrls;
    if (!urls || urls.length === 0) return;
    const timer = setTimeout(() => urls.forEach(playSound), 0);
    return () => clearTimeout(timer);
    // Deliberately not depending on `beats`/`urls` themselves (a new
    // array reference every render): segmentIndex+beatIndex alone already
    // uniquely identify which beat this is, matching the lifecycle
    // effect above — depending on the array would re-fire on every
    // unrelated re-render instead of once per beat.
  }, [segmentIndex, beatIndex, segments.length, beats.length]);

  if (segmentIndex >= segments.length || beatIndex >= beats.length) return null;
  const beat = beats[beatIndex];
  return (
    <div className="turn-playback">
      <div className="turn-playback__card" key={`${segmentIndex}-${beat.key}`}>
        {beat.text}
      </div>
    </div>
  );
}
