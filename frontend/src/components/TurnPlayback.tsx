import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import { OfficerActionIcon } from './OfficerActionIcon';
import { criminalAssetsForPlayer, dopeSoundUrl, playerColorForId, playerTeamNameForId } from '../assets';
import {
  collectActionItems,
  MERGE_KINDS,
  resolveOfficerTypes,
  type ActionItem,
  type BannerAction,
  type BannerPart,
} from '../log-narration';
import { JAIL_EVASION_HOLD_MS } from '../jail-evasion';
import type { DopeTransfer } from '../dope-transfers';
import type { OfficerEntry, OfficerPurchase } from '../officer-entries';
import { playSound, randomSoundUrls, soundEffectUrls } from '../sound';
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
  dopeTransfers?: DopeTransfer[];
  officerEntries?: OfficerEntry[];
  officerPurchases?: OfficerPurchase[];
  // How long to let the revealed result play out on the board (Dope flying to
  // the Covo, pawns sliding…) before the next action's message appears.
  settleMs?: number;
  // Secondary event effects play when the board reveals the result.
  viewSoundUrls?: string[];
  holdSoundUrls?: string[];
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
  if (kind === 'place') return randomSoundUrls('recruit');
  if (kind === 'move') return soundEffectUrls('move');
  if (kind === 'corrupt') return randomSoundUrls('police');
  if (kind === 'buy_officer') return [...soundEffectUrls('buy'), ...randomSoundUrls('police')];
  if (kind === 'buy') {
    return [...soundEffectUrls('buy'),
      ...dopeSoundUrlsFor((group as Extract<ActionItem, { kind: 'buy' }>[]).map((i) => i.dopeType))];
  }
  if (kind === 'sell') {
    const sales = group as Extract<ActionItem, { kind: 'sell' }>[];
    return [...(sales.some((i) => i.priceReceived > 0) ? soundEffectUrls('coins') : []),
      ...dopeSoundUrlsFor(sales.map((i) => i.dopeType))];
  }
  return undefined;
}

// What a bot message says for each kind of action: just its name, as on the
// human's own action buttons (ActionChooser.tsx).
const ACTION_NAME: Partial<Record<ActionItem['kind'], string>> = {
  place: 'Piazza',
  move: 'Sposta',
  buy: 'Acquista',
  sell: 'Vendi',
  corrupt: 'Corrompi',
  buy_officer: 'Compra',
  pass: 'Passa',
};

// Builds the beat list for one segment (already known to belong to a single
// acting player — game_service.py's single_player_segment). Since 2026-10-08
// the bot messages are single words, one message per thing the bot does, in the
// order it does it: "Turno di <squadra>" (first action of its turn only), then
// "Gancio", "Poker", "Marketing" and finally the action's name — each on screen
// for BEAT_DURATION_MS (2 s). Grit, targets and a boost card are not mentioned. A
// segment with nothing to say gives an empty list, so no empty "Turno" card is
// shown either.
export function buildTurnBeats(
  events: GameEventResponse[],
  actingPlayerId: string,
  view: GameViewResponse,
  includeHeader = true,
): TurnBeat[] {
  const items = resolveOfficerTypes(
    collectActionItems(events, actingPlayerId),
    events,
    actingPlayerId,
    view,
  );
  const beats: TurnBeat[] = [];
  const push = (text: string, soundUrls?: string[]) =>
    beats.push({ key: `beat-${beats.length}`, text, playerId: actingPlayerId, soundUrls });

  let i = 0;
  while (i < items.length) {
    const item = items[i];
    i++;
    if (item.kind === 'use_link') {
      push('Gancio');
    } else if (item.kind === 'poker_launch') {
      push('Poker');
    } else if (item.kind === 'marketing') {
      push('Marketing');
    } else if (item.kind === 'grit' || item.kind === 'boost') {
      // no message of their own
    } else {
      const kind = item.kind;
      const group: ActionItem[] = [item];
      if (MERGE_KINDS.has(kind)) {
        while (i < items.length && items[i].kind === kind) {
          group.push(items[i]);
          i++;
        }
      }
      push(ACTION_NAME[kind] ?? '', soundUrlsForGroup(kind, group));
    }
  }

  if (beats.length === 0) return [];
  if (includeHeader) {
    beats.unshift({
      key: 'turn-header',
      text: `Turno di ${playerTeamNameForId(actingPlayerId)}`,
      playerId: actingPlayerId,
    });
  }
  return beats;
}

// How long a segment's revealed result is left to play out before the next
// message: Dope flying to the Covo takes the longest, pawns sliding less.
export function settleMsForEvents(events: GameEventResponse[]): number {
  const types = new Set(events.map((e) => e.event_type));
  if (types.has('DopeBought') || types.has('DopeSold') || types.has('OfficerBought')) return 1800;
  if (types.has('CriminalPlaced') || types.has('CriminalMoved') || types.has('PawnArrested')) return 1200;
  return 600;
}

// One piece of a banner unit: an icon, a short text ("-2$") or the Link asterisk.
function BannerPartView({ part }: { part: BannerPart }) {
  if (part.kind === 'icon') {
    return (
      <img
        src={part.src}
        alt={part.alt}
        className={'bot-turn-banner__icon' + (part.variant === 'dope' ? ' bot-turn-banner__icon--dope' : '')
          + (part.variant === 'white' ? ' bot-turn-banner__icon--white' : '')}
      />
    );
  }
  if (part.kind === 'text') return <span className="bot-turn-banner__cost">{part.text}</span>;
  if (part.kind === 'officer-action') {
    return <OfficerActionIcon action={part.action} className="bot-turn-banner__officer-action" />;
  }
  return <span className="bot-turn-banner__star" aria-label="Gancio">✱</span>;
}

// Every message — the "Turno di …" header included — stays on screen for two seconds.
const BEAT_DURATION_MS = 2000;

// Plays each segment's beats (3s each, designer's request), revealing
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
  onApplyView: (view: GameViewResponse, transfers?: DopeTransfer[], entries?: OfficerEntry[], purchases?: OfficerPurchase[]) => void;
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
  const playedSoundBeat = useRef<string | null>(null);
  // Which segmentIndex's own holdView (if any) has already been revealed
  // — an index rather than a plain boolean so it's inherently scoped to
  // *this* segment and never needs a separate reset effect (a boolean
  // left over `true` from the previous segment could otherwise skip a
  // brand new segment's own hold on the very next render, before a reset
  // effect even got a chance to run).
  const [holdRevealedSegmentIndex, setHoldRevealedSegmentIndex] = useState<number | null>(null);
  // Same idea for the segment's own result: once revealed the board gets
  // `settleMs` to animate before the next action's message.
  const [revealedSegmentIndex, setRevealedSegmentIndex] = useState<number | null>(null);

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
          segment.holdSoundUrls?.forEach(playSound);
          setHoldRevealedSegmentIndex(segmentIndex);
        }, 0);
        return () => clearTimeout(timer);
      }
      if (revealedSegmentIndex !== segmentIndex) {
        const timer = setTimeout(
          () => {
            onApplyView(segment.view, segment.dopeTransfers, segment.officerEntries, segment.officerPurchases);
            segment.viewSoundUrls?.forEach(playSound);
            setRevealedSegmentIndex(segmentIndex);
          },
          segment.holdView ? JAIL_EVASION_HOLD_MS : 0,
        );
        return () => clearTimeout(timer);
      }
      const timer = setTimeout(
        () => {
          setSegmentIndex((s) => s + 1);
          setBeatIndex(0);
        },
        beats.length > 0 ? (segment.settleMs ?? 0) : 0,
      );
      return () => clearTimeout(timer);
    }
    const timer = setTimeout(() => setBeatIndex((b) => b + 1), BEAT_DURATION_MS);
    return () => clearTimeout(timer);
  }, [segmentIndex, beatIndex, segments.length, beats.length, paused, holdAlreadyRevealed, revealedSegmentIndex]);

  // Separate effect (its own StrictMode-safe cancellable timer) so a
  // beat's sound plays exactly once, right as that beat becomes the one
  // on screen — not tied to the lifecycle effect above, which has its own
  // unrelated branches.
  useEffect(() => {
    if (paused || segmentIndex >= segments.length || beatIndex >= beats.length) return;
    const soundKey = `${segmentIndex}:${beatIndex}`;
    if (playedSoundBeat.current === soundKey) return;
    const urls = beats[beatIndex].soundUrls;
    if (!urls || urls.length === 0) return;
    const timer = setTimeout(() => {
      playedSoundBeat.current = soundKey;
      urls.forEach(playSound);
    }, 0);
    return () => clearTimeout(timer);
    // Deliberately not depending on `beats`/`urls` themselves (a new
    // array reference every render): segmentIndex+beatIndex alone already
    // uniquely identify which beat this is, matching the lifecycle
    // effect above — depending on the array would re-fire on every
    // unrelated re-render instead of once per beat.
  }, [segmentIndex, beatIndex, segments.length, beats.length, paused]);

  // One random portrait per segment (not per beat), so the same bot's
  // face stays put across all its beats within a single turn — re-rolled
  // only when segmentIndex actually changes to a new bot's segment.
  const portraitPlayerId = segments[segmentIndex]?.beats[0]?.playerId;
  const segmentPortraitUrl = useMemo(() => {
    const playerId = portraitPlayerId;
    if (!playerId) return '';
    const options = criminalAssetsForPlayer(playerId);
    if (options.length === 0) return '';
    return options[Math.floor(Math.random() * options.length)];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [portraitPlayerId]);

  // While paused (a Rissa/Poker/Retata/Turno popup awaiting the player's
  // OK) the *next* beat must not be visible either: the segment whose
  // reveal queued that popup has already advanced `segmentIndex` to the
  // following bot's first beat in the same render, so without this its
  // banner showed underneath the still-open popup.
  if (paused || segmentIndex >= segments.length || beatIndex >= beats.length) return null;
  const beat = beats[beatIndex];
  const color = playerColorForId(beat.playerId);
  const banner = beat.banner;
  return (
    <div
      className={`bot-turn-banner bot-turn-banner--${color}`}
      data-units={banner ? banner.units.length : 0}
      key={`${segmentIndex}-${beat.key}`}
      title={beat.text}
    >
      {/* Cuts the faint translucent backdrop out of the white icon files (alpha
          below ~40% goes, the rest becomes solid) — see .bot-turn-banner__icon--white. */}
      <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true" focusable="false">
        <filter id="bot-icon-solid">
          <feComponentTransfer>
            <feFuncA type="linear" slope="4" intercept="-1.6" />
          </feComponentTransfer>
        </filter>
      </svg>
      {segmentPortraitUrl && (
        <img src={segmentPortraitUrl} alt="" className="bot-turn-banner__portrait" />
      )}
      {banner ? (
        <div className="bot-turn-banner__content">
          <div className="bot-turn-banner__row">
            {banner.prefix.length > 0 && (
              <>
                {banner.prefix.map((part, i) => <BannerPartView key={`p${i}`} part={part} />)}
                {(banner.units.length > 0 || banner.text) && <span className="bot-turn-banner__sep" aria-hidden="true">|</span>}
              </>
            )}
            {banner.units.map((unit, i) => (
              <Fragment key={`u${i}`}>
                {i > 0 && <span className="bot-turn-banner__sep" aria-hidden="true">{unit.lead ?? '/'}</span>}
                <span className="bot-turn-banner__unit">
                  {unit.actionIconSrc && (
                    <img
                      src={unit.actionIconSrc}
                      alt=""
                      className={'bot-turn-banner__action-icon ' +
                        (unit.actionIconWhite ? 'bot-turn-banner__action-icon--light' : 'bot-turn-banner__action-icon--dark')}
                    />
                  )}
                  {unit.parts.map((part, j) => <BannerPartView key={j} part={part} />)}
                </span>
              </Fragment>
            ))}
            {banner.text && <span className="bot-turn-banner__verb">{banner.text}</span>}
          </div>
          {banner.detailText && <div className="bot-turn-banner__detail">{banner.detailText}</div>}
        </div>
      ) : (
        <span className="bot-turn-banner__header-text">{beat.text}</span>
      )}
    </div>
  );
}
