import { useEffect, useMemo, useState } from 'react';
import {
  actionTypeAssetUrl,
  criminalAssetsForPlayer,
  dopeSoundUrl,
  playerColorForId,
  playerColorLabelForId,
} from '../assets';
import {
  ACTION_TYPE_BY_KIND,
  collectActionItems,
  iconsForGroup,
  MERGE_KINDS,
  resolveOfficerTypes,
  textForGroup,
  type ActionIcon,
  type ActionItem,
} from '../log-narration';
import { playSound } from '../sound';
import type { GameEventResponse, GameViewResponse } from '../types';

export interface TurnBeat {
  key: string;
  text: string;
  playerId: string;
  // The action-type icon (already used by DecisionPanel.tsx's own "Che
  // azione fai?" buttons) and the "object" icons for this beat's group
  // (Dope/officer/Hood icons) — both undefined for the "Turno giocatore
  // X" header beat, which has no single action behind it.
  actionType?: string;
  icons?: ActionIcon[];
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
    {
      key: 'turn-header',
      text: `Turno giocatore ${playerColorLabelForId(actingPlayerId)}`,
      playerId: actingPlayerId,
    },
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
      playerId: actingPlayerId,
      actionType: ACTION_TYPE_BY_KIND[kind],
      icons: iconsForGroup(kind, group, view),
      soundUrls: soundUrlsForGroup(kind, group),
    });
  }
  return beats;
}

const BEAT_DURATION_MS = 2000;

// Plays each segment's beats (2s each, designer's request), revealing
// that segment's view as soon as its beats finish and *before* moving on
// to the next segment — so bot turns appear one at a time instead of all
// at once at the end. Rendered by App.tsx as a fixed overlay, centered at
// the top of the board (designer's request, 2026-09-17: tinted with the
// acting bot's own player color, a random criminal portrait, the
// action-type icon plus per-action "object" icons — allowed to partially
// cover the board, unlike the 2026-09-07 inline placement it replaces).
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

  // One random portrait per segment (not per beat), so the same bot's
  // face stays put across all its beats within a single turn — re-rolled
  // only when segmentIndex actually changes to a new bot's segment.
  const segmentPortraitUrl = useMemo(() => {
    const playerId = segments[segmentIndex]?.beats[0]?.playerId;
    if (!playerId) return '';
    const options = criminalAssetsForPlayer(playerId);
    if (options.length === 0) return '';
    return options[Math.floor(Math.random() * options.length)];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segmentIndex]);

  if (segmentIndex >= segments.length || beatIndex >= beats.length) return null;
  const beat = beats[beatIndex];
  const color = playerColorForId(beat.playerId);
  const actionIconUrl = beat.actionType ? actionTypeAssetUrl(beat.actionType) : '';
  return (
    <div className={`bot-turn-banner bot-turn-banner--${color}`} key={`${segmentIndex}-${beat.key}`}>
      {segmentPortraitUrl && (
        <img src={segmentPortraitUrl} alt="" className="bot-turn-banner__portrait" />
      )}
      <div className="bot-turn-banner__body">
        <div className="bot-turn-banner__text-row">
          {actionIconUrl && (
            <img src={actionIconUrl} alt="" className="bot-turn-banner__action-icon" />
          )}
          <span className="bot-turn-banner__text">{beat.text}</span>
        </div>
        {beat.icons && beat.icons.length > 0 && (
          <div className="bot-turn-banner__object-icons">
            {beat.icons.map((icon, i) => (
              <img key={i} src={icon.src} alt={icon.alt} className="bot-turn-banner__object-icon" />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
