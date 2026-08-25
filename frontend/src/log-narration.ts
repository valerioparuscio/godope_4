// Shared Italian narration helpers for turn events — extracted from
// TurnPlayback.tsx (which still owns the timed "one beat on screen" popup
// UI) so ActionLogDrawer.tsx can reuse the exact same phrasing for a
// persistent, all-players action log instead of TurnPlayback's own
// bots-only, one-beat-at-a-time narration.
import { playerColorLabelForId, POKER_HAND_SHAPE_LABEL, RAID_CRITERION_LABEL } from './assets';
import type { GameEventResponse, GameViewResponse } from './types';

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

export type ActionItem =
  | { kind: 'place'; hoodId: string }
  | { kind: 'move'; fromHoodId: string; toHoodId: string }
  | { kind: 'buy'; hoodId: string; dopeType: string }
  | { kind: 'sell'; spotId: string; dopeType: string }
  | { kind: 'corrupt'; officerType: string; actions: string[] }
  | { kind: 'buy_officer'; officerType: string }
  | { kind: 'pass' };

// Kinds that merge into one combined line when several in a row belong to
// the same acting player (e.g. 3 CriminalPlaced -> one "piazza 3
// criminali" line) — "corrupt" deliberately isn't included: each
// corrupted officer gets its own tally and its own line, even back to
// back, since a merged tally across 2 different officers (maybe one Cop,
// one Fed) would misrepresent which officer did what.
export const MERGE_KINDS = new Set(['place', 'move', 'buy', 'sell', 'buy_officer', 'pass']);

// Walks a batch of raw events into `ActionItem`s. PawnArrested.player_id
// is the *victim's* owner, not the corrupting player (rules/jail.py) — an
// arrest via corruption is folded into that corruption's own tally
// instead (via CorruptionActionApplied, which *does* carry the actor's
// id), rather than emitted as a separate, wrongly-attributed line.
export function collectActionItems(
  events: GameEventResponse[],
  actingPlayerId: string,
): ActionItem[] {
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
        // by the caller (resolveOfficerTypes) via view.officers afterward.
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

// OfficerBought's officer_type has to come from view.officers (not the
// event itself, which only has officer_id) — resolved in a second pass,
// matched positionally against the buy_officer items collected above
// (both walk the same events in the same order).
export function resolveOfficerTypes(
  items: ActionItem[],
  events: GameEventResponse[],
  actingPlayerId: string,
  view: GameViewResponse,
): ActionItem[] {
  const officerTypeById = new Map(view.officers.map((o) => [o.officer_id, o.officer_type]));
  let officerBoughtIndex = 0;
  const boughtOfficerIds = events
    .filter((e) => e.event_type === 'OfficerBought' && e.buyer_player_id === actingPlayerId)
    .map((e) => e.officer_id as string);
  return items.map((item) => {
    if (item.kind !== 'buy_officer') return item;
    const officerId = boughtOfficerIds[officerBoughtIndex++];
    return { ...item, officerType: officerTypeById.get(officerId ?? '') ?? '' };
  });
}

export function textForGroup(kind: ActionItem['kind'], group: ActionItem[], view: GameViewResponse): string {
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

// One log line per merged action-group for a batch of events belonging to
// a single acting player — same grouping/phrasing TurnPlayback.tsx's own
// buildTurnBeats uses for its popups, but returns *every* line instead of
// a single "current beat" to show and discard, and is called for the
// human's own move too (buildTurnBeats only ever narrates bot segments).
export function describeActionEvents(
  events: GameEventResponse[],
  actingPlayerId: string,
  view: GameViewResponse,
): string[] {
  const items = collectActionItems(events, actingPlayerId);
  const resolvedItems = resolveOfficerTypes(items, events, actingPlayerId, view);
  if (resolvedItems.length === 0) return [];

  const lines: string[] = [];
  const colorLabel = playerColorLabelForId(actingPlayerId);
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
    lines.push(`${colorLabel} ${textForGroup(kind, group, view)}`);
  }
  return lines;
}

// One log line per Poker/Raid/Brawl resolution found in this batch of
// events — read from `view`'s own already-structured outcome fields
// (same source OutcomeModal.tsx's popups use), not re-derived from the
// raw event payloads, so the log's wording stays consistent with what the
// player already saw in the popup for that same outcome.
export function describeOutcomeEvents(events: GameEventResponse[], view: GameViewResponse): string[] {
  const lines: string[] = [];

  if (events.some((e) => e.event_type === 'BrawlResolved') && view.last_brawl_outcome) {
    const outcome = view.last_brawl_outcome;
    const winner = outcome.winner_id ? playerColorLabelForId(outcome.winner_id) : null;
    const losers = outcome.loser_ids.map(playerColorLabelForId).join(', ');
    lines.push(
      winner
        ? `Rissa in un Quartiere: vince ${winner}${losers ? `, sconfitto ${losers}` : ''}`
        : 'Rissa in un Quartiere: nessun vincitore',
    );
  }

  const resolvedMatchIds = new Set(
    events.filter((e) => e.event_type === 'PokerMatchResolved').map((e) => e.match_id as string),
  );
  for (const outcome of view.last_poker_outcomes) {
    if (!resolvedMatchIds.has(outcome.match_id)) continue;
    if (outcome.winner_id) {
      const shape = outcome.top_hand_shape ? (POKER_HAND_SHAPE_LABEL[outcome.top_hand_shape] ?? outcome.top_hand_shape) : '';
      lines.push(`Poker: vince ${playerColorLabelForId(outcome.winner_id)} (${shape}), +$${outcome.cash_won}`);
    } else if (outcome.tied_ids.length > 0) {
      lines.push(`Poker: pareggio tra ${outcome.tied_ids.map(playerColorLabelForId).join(', ')}, jackpot riportato`);
    }
  }

  if (events.some((e) => e.event_type === 'RaidResolved') && view.last_raid_outcome) {
    const outcome = view.last_raid_outcome;
    const criterion = RAID_CRITERION_LABEL[outcome.escape_criterion] ?? outcome.escape_criterion;
    const escaping = outcome.escaping_team.map(playerColorLabelForId).join(', ');
    const caught = outcome.caught_team.map(playerColorLabelForId).join(', ');
    lines.push(`Retata (${criterion}): scappano ${escaping} — catturati ${caught}`);
  }

  return lines;
}
