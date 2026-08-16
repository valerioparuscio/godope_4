import { useEffect, useState } from 'react';
import { dopeSoundUrl, playerColorLabelForId } from '../assets';
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

function pluralize(n: number, singular: string, pluralForm: string): string {
  return n === 1 ? singular : pluralForm;
}

const DOPE_LABEL: Record<string, { singular: string; plural: string; article: string }> = {
  rana: { singular: 'rana', plural: 'rane', article: 'una' },
  camaleonte: { singular: 'camaleonte', plural: 'camaleonti', article: 'un' },
  polpo: { singular: 'polpo', plural: 'polpi', article: 'un' },
  gufo: { singular: 'gufo', plural: 'gufi', article: 'un' },
};

function dopeLabel(dopeType: string, count: number): string {
  const entry = DOPE_LABEL[dopeType];
  if (!entry) return `${count} ${dopeType}`;
  return count === 1 ? `${entry.article} ${entry.singular}` : `${count} ${entry.plural}`;
}

function dopeSummary(dopeTypes: string[]): string {
  const counts = new Map<string, number>();
  for (const t of dopeTypes) counts.set(t, (counts.get(t) ?? 0) + 1);
  return Array.from(counts.entries())
    .map(([type, n]) => dopeLabel(type, n))
    .join(' e ');
}

function locationPhrase(contacts: string[]): string {
  const unique = Array.from(new Set(contacts));
  if (unique.length === 1) return `in un quartiere ${unique[0]}`;
  return 'in quartieri diversi';
}

const OFFICER_TYPE_LABEL: Record<string, { singular: string; plural: string }> = {
  cop: { singular: 'Cop', plural: 'Cops' },
  fed: { singular: 'Fed', plural: 'Feds' },
};

function officerLabel(officerType: string, count: number): string {
  const entry = OFFICER_TYPE_LABEL[officerType];
  const label = entry ? (count === 1 ? entry.singular : entry.plural) : officerType;
  return count === 1 ? `un ${label}` : `${count} ${label}`;
}

const CORRUPTION_VERB: Record<string, string> = {
  move: 'spostare',
  arrest: 'arrestare',
  confiscate: 'requisire',
};

function corruptionTally(actions: string[]): string {
  const counts = new Map<string, number>();
  for (const action of actions) counts.set(action, (counts.get(action) ?? 0) + 1);
  return Array.from(counts.entries())
    .map(([action, n]) => `${CORRUPTION_VERB[action] ?? action} ${n} ${pluralize(n, 'volta', 'volte')}`)
    .join(' e ');
}

type ActionItem =
  | { kind: 'place'; hoodId: string }
  | { kind: 'move'; fromHoodId: string; toHoodId: string }
  | { kind: 'buy'; hoodId: string; dopeType: string }
  | { kind: 'sell'; spotId: string; dopeType: string }
  | { kind: 'corrupt'; officerType: string; actions: string[] }
  | { kind: 'buy_officer'; officerType: string }
  | { kind: 'pass' };

// Kinds that merge into one combined beat when several in a row belong
// to the same segment's player (e.g. 3 CriminalPlaced -> one "piazza 3
// criminali" beat) — "corrupt" deliberately isn't included: each
// corrupted officer gets its own tally and its own beat, even back to
// back, since a merged tally across 2 different officers (maybe one Cop,
// one Fed) would misrepresent which officer did what.
const MERGE_KINDS = new Set(['place', 'move', 'buy', 'sell', 'buy_officer', 'pass']);

// Walks one segment's raw events into `ActionItem`s. PawnArrested.player_id
// is the *victim's* owner, not the corrupting player (rules/jail.py) — an
// arrest via corruption is folded into that corruption's own tally
// instead (via CorruptionActionApplied, which *does* carry the actor's
// id), rather than emitted as a separate, wrongly-attributed beat.
function collectActionItems(events: GameEventResponse[], actingPlayerId: string): ActionItem[] {
  const items: ActionItem[] = [];
  let openCorruption: { officerType: string; actions: string[] } | null = null;

  const flushCorruption = () => {
    if (openCorruption) items.push({ kind: 'corrupt', ...openCorruption });
    openCorruption = null;
  };

  for (const event of events) {
    const eventPlayerId = event.player_id as string | undefined;
    switch (event.event_type) {
      case 'OfficerCorruptionStarted':
        flushCorruption();
        if (eventPlayerId === actingPlayerId) {
          openCorruption = { officerType: event.officer_type as string, actions: [] };
        }
        break;
      case 'CorruptionActionApplied':
        if (openCorruption && eventPlayerId === actingPlayerId) {
          openCorruption.actions.push(event.action as string);
        }
        break;
      case 'OfficerCorruptionResolved':
        flushCorruption();
        break;
      case 'CriminalPlaced':
        if (eventPlayerId === actingPlayerId) {
          items.push({ kind: 'place', hoodId: event.hood_id as string });
        }
        break;
      case 'CriminalMoved':
        if (eventPlayerId === actingPlayerId) {
          items.push({
            kind: 'move',
            fromHoodId: event.from_hood_id as string,
            toHoodId: event.to_hood_id as string,
          });
        }
        break;
      case 'DopeBought':
        if (eventPlayerId === actingPlayerId) {
          items.push({ kind: 'buy', hoodId: event.hood_id as string, dopeType: event.dope_type as string });
        }
        break;
      case 'DopeSold':
        if (eventPlayerId === actingPlayerId) {
          items.push({ kind: 'sell', spotId: event.spot_id as string, dopeType: event.dope_type as string });
        }
        break;
      case 'OfficerBought':
        // OfficerBought uses buyer_player_id/seller_player_id, not
        // player_id — officer_type isn't on the event at all, resolved
        // by the caller (buildTurnBeats) via view.officers afterward.
        if (event.buyer_player_id === actingPlayerId) {
          items.push({ kind: 'buy_officer', officerType: '' });
        }
        break;
      case 'MainActionPassed':
        if (eventPlayerId === actingPlayerId) {
          items.push({ kind: 'pass' });
        }
        break;
      default:
        break;
    }
  }
  flushCorruption();
  return items;
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

function textForGroup(kind: ActionItem['kind'], group: ActionItem[], view: GameViewResponse): string {
  const hoodContact = (hoodId: string) =>
    view.hoods.find((h) => h.hood_id === hoodId)?.contact_id ?? hoodId;
  const spotContact = (spotId: string) =>
    view.spots.find((s) => s.spot_id === spotId)?.contact_id ?? spotId;

  switch (kind) {
    case 'place': {
      const items = group as Extract<ActionItem, { kind: 'place' }>[];
      const n = items.length;
      return `piazza ${n} ${pluralize(n, 'criminale', 'criminali')} ${locationPhrase(items.map((i) => hoodContact(i.hoodId)))}`;
    }
    case 'move': {
      const items = group as Extract<ActionItem, { kind: 'move' }>[];
      if (items.length === 1) {
        return `sposta da un quartiere ${hoodContact(items[0].fromHoodId)} a uno ${hoodContact(items[0].toHoodId)}`;
      }
      return `sposta ${items.length} criminali`;
    }
    case 'buy': {
      const items = group as Extract<ActionItem, { kind: 'buy' }>[];
      return `compra ${dopeSummary(items.map((i) => i.dopeType))} ${locationPhrase(items.map((i) => hoodContact(i.hoodId)))}`;
    }
    case 'sell': {
      const items = group as Extract<ActionItem, { kind: 'sell' }>[];
      return `vende ${dopeSummary(items.map((i) => i.dopeType))} ${locationPhrase(items.map((i) => spotContact(i.spotId)))}`;
    }
    case 'corrupt': {
      const item = group[0] as Extract<ActionItem, { kind: 'corrupt' }>;
      const tally = corruptionTally(item.actions);
      const type = OFFICER_TYPE_LABEL[item.officerType]?.plural.toLowerCase() ?? item.officerType;
      return tally ? `corrompe ${type} e li fa ${tally}` : `corrompe ${type}`;
    }
    case 'buy_officer': {
      const items = group as Extract<ActionItem, { kind: 'buy_officer' }>[];
      const counts = new Map<string, number>();
      for (const i of items) counts.set(i.officerType, (counts.get(i.officerType) ?? 0) + 1);
      const parts = Array.from(counts.entries()).map(([type, n]) => officerLabel(type, n));
      return `compra ${parts.join(' e ')}`;
    }
    case 'pass':
      return 'passa';
  }
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

  // OfficerBought's officer_type has to come from view.officers (not the
  // event itself, which only has officer_id) — resolve it in a second
  // pass, matched positionally against the buy_officer items collected
  // above (both walk the same events in the same order).
  const officerTypeById = new Map(view.officers.map((o) => [o.officer_id, o.officer_type]));
  let officerBoughtIndex = 0;
  const boughtOfficerIds = events
    .filter((e) => e.event_type === 'OfficerBought' && e.buyer_player_id === actingPlayerId)
    .map((e) => e.officer_id as string);
  const resolvedItems: ActionItem[] = items.map((item) => {
    if (item.kind !== 'buy_officer') return item;
    const officerId = boughtOfficerIds[officerBoughtIndex++];
    return { ...item, officerType: officerTypeById.get(officerId ?? '') ?? '' };
  });

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
