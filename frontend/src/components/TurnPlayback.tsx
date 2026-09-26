import { useEffect, useMemo, useState } from 'react';
import { criminalAssetsForPlayer, dopeSoundUrl, playerColorForId, playerColorLabelForId } from '../assets';
import {
  bannerActionForGroup,
  collectActionItems,
  MERGE_KINDS,
  resolveOfficerTypes,
  textForGroup,
  type ActionItem,
  type BannerAction,
} from '../log-narration';
import { JAIL_EVASION_HOLD_MS } from '../jail-evasion';
import { playSound } from '../sound';
import type { GameEventResponse, GameViewResponse } from '../types';

export interface TurnBeat {
  key: string;
  text: string;
  playerId: string;
  // The mockup-style verb/icons/preposition/cost content for this beat
  // (designer's mockups, 2026-09-17) — undefined only for the "Turno
  // giocatore X" header beat, which has no single action behind it and
  // falls back to plain `text`.
  banner?: BannerAction;
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
  // Set only when this segment's own events include a Jail Evasion
  // (jail-evasion.ts::buildJailEvasionHoldView) — revealed for
  // JAIL_EVASION_HOLD_MS once this segment's beats finish, *before*
  // `view` itself (the real, already-evacuated state) gets revealed.
  holdView?: GameViewResponse;
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
      banner: bannerActionForGroup(kind, group, view),
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
  paused = false,
}: {
  segments: PlaybackSegment[];
  onApplyView: (view: GameViewResponse) => void;
  onDone: () => void;
  // Freezes playback entirely — no beat advances, no segment's view gets
  // revealed, nothing narrates further — for as long as this is true
  // (App.tsx: `outcomeQueue.length > 0`, an unconfirmed Rissa/Poker/
  // Retata/Turno popup). Game designer, 2026-09-26: "senza quell'ok dato
  // dal giocatore il gioco non deve proseguire" — reported as the bot
  // already visibly playing the next turn underneath a still-open recap
  // popup, because this component's own pacing never knew that popup
  // existed. Checked first, before every other branch, so a paused
  // segment boundary can't sneak an empty-beats segment's view through
  // on the same tick it gets revealed.
  paused?: boolean;
}) {
  const [segmentIndex, setSegmentIndex] = useState(0);
  const [beatIndex, setBeatIndex] = useState(0);
  // Which segmentIndex's own holdView (if any) has already been revealed
  // — an index rather than a plain boolean so it's inherently scoped to
  // *this* segment and never needs a separate reset effect (a boolean
  // left over `true` from the previous segment could otherwise skip a
  // brand new segment's own hold on the very next render, before a reset
  // effect even got a chance to run).
  const [holdRevealedSegmentIndex, setHoldRevealedSegmentIndex] = useState<number | null>(null);

  const segment = segments[segmentIndex];
  const beats = segment?.beats ?? [];
  const holdAlreadyRevealed = holdRevealedSegmentIndex === segmentIndex;

  useEffect(() => {
    if (paused) return;
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
      // Jail Evasion (game designer, 2026-09-26: "quando il quarto pawn
      // va in prigione, ci deve restare 2 secondi") — reveal the
      // still-full-Jail snapshot first, holding there for
      // JAIL_EVASION_HOLD_MS (BoardView.tsx pulses every occupied Jail
      // slot's own pawn whenever it sees all of them filled at once, a
      // state that otherwise never survives long enough to render) —
      // *then* reveal the real, already-evacuated `segment.view`.
      if (segment.holdView && !holdAlreadyRevealed) {
        const timer = setTimeout(() => {
          onApplyView(segment.holdView!);
          setHoldRevealedSegmentIndex(segmentIndex);
        }, 0);
        return () => clearTimeout(timer);
      }
      const timer = setTimeout(
        () => {
          onApplyView(segment.view);
          setSegmentIndex((s) => s + 1);
          setBeatIndex(0);
        },
        segment.holdView ? JAIL_EVASION_HOLD_MS : 0,
      );
      return () => clearTimeout(timer);
    }
    const timer = setTimeout(() => setBeatIndex((b) => b + 1), BEAT_DURATION_MS);
    return () => clearTimeout(timer);
  }, [segmentIndex, beatIndex, segments.length, beats.length, paused, holdAlreadyRevealed]);

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
  const banner = beat.banner;
  return (
    <div
      className={`bot-turn-banner bot-turn-banner--${color}`}
      key={`${segmentIndex}-${beat.key}`}
      title={beat.text}
    >
      {segmentPortraitUrl && (
        <img src={segmentPortraitUrl} alt="" className="bot-turn-banner__portrait" />
      )}
      {banner ? (
        <div className="bot-turn-banner__row">
          <span className="bot-turn-banner__verb">{banner.verb}</span>
          {banner.subjectDotCount > 0 && (
            <span className="bot-turn-banner__dots">
              {Array.from({ length: banner.subjectDotCount }, (_, i) => (
                <span key={i} className="bot-turn-banner__dot" />
              ))}
            </span>
          )}
          {banner.subjectIcons.map((icon, i) => (
            <img key={i} src={icon.src} alt={icon.alt} className="bot-turn-banner__icon" />
          ))}
          {banner.preposition && <span className="bot-turn-banner__preposition">{banner.preposition}</span>}
          {banner.trailingIcons.map((icon, i) => (
            <img key={i} src={icon.src} alt={icon.alt} className="bot-turn-banner__icon" />
          ))}
          {banner.costLabel && <span className="bot-turn-banner__cost">{banner.costLabel}</span>}
        </div>
      ) : (
        <span className="bot-turn-banner__header-text">{beat.text}</span>
      )}
    </div>
  );
}
