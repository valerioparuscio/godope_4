// Shared Italian narration helpers for turn events — extracted from
// TurnPlayback.tsx (which still owns the timed "one beat on screen" popup
// UI) so ActionLogDrawer.tsx can reuse the exact same phrasing for a
// persistent, all-players action log instead of TurnPlayback's own
// bots-only, one-beat-at-a-time narration.
import {
  actionTypeAssetUrl,
  DOPE_ASSET,
  hoodContactAssetUrl,
  OFFICER_ASSET,
  pawnAssetForPlayer,
  playerColorLabelForId,
  POKER_HAND_SHAPE_LABEL,
  RAID_CRITERION_LABEL,
} from './assets';
import marketingIcon from './assets/actions/MARKET W.png';
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

// What one corruption sub-action actually did, read from the events the
// backend emits right before its CorruptionActionApplied (OfficerMoved,
// PawnArrested, DopeConfiscated — rules/officers.py::_apply_*).
export interface CorruptionStep {
  action: string;
  hoodId?: string;
  spotId?: string;
  arrestedOwnerIds: string[];
  dopeTypes: string[];
}

function joinWithE(parts: string[]): string {
  if (parts.length <= 1) return parts.join('');
  return `${parts.slice(0, -1).join(', ')} e ${parts[parts.length - 1]}`;
}

function describeCorruptionStep(step: CorruptionStep, view: GameViewResponse): string {
  if (step.action === 'move') {
    if (step.hoodId) return `si sposta in un quartiere ${hoodContact(step.hoodId, view)}`;
    if (step.spotId) return `si sposta in uno spot ${spotContact(step.spotId, view)}`;
    return 'si sposta';
  }
  if (step.action === 'arrest') {
    const owners = Array.from(new Set(step.arrestedOwnerIds.map(playerColorLabelForId)));
    const n = step.arrestedOwnerIds.length;
    if (n === 0) return 'arresta';
    return `arresta ${n === 1 ? 'una pedina' : `${n} pedine`} di ${owners.join(', ')}`;
  }
  if (step.action === 'confiscate') {
    return step.dopeTypes.length > 0 ? `requisisce ${dopeSummary(step.dopeTypes)}` : 'requisisce';
  }
  return step.action;
}

// "requisisce una rana, arresta una pedina di Rosso e si sposta in un
// quartiere preti" — in the order the sub-actions actually happened.
function corruptionDetail(steps: CorruptionStep[], view: GameViewResponse): string {
  return joinWithE(steps.map((s) => describeCorruptionStep(s, view)));
}

export type ActionItem =
  | { kind: 'place'; hoodId: string; cost?: number }
  | { kind: 'move'; fromHoodId: string; toHoodId: string }
  | { kind: 'buy'; hoodId: string; dopeType: string; pricePaid: number }
  | { kind: 'sell'; spotId: string; dopeType: string; priceReceived: number }
  | { kind: 'corrupt'; officerType: string; actions: CorruptionStep[] }
  | { kind: 'use_link'; contactId: string; level: number }
  | { kind: 'buy_officer'; officerType: string; price: number }
  | { kind: 'pass' }
  // What powers or accompanies an action (narrated *with* it, never as lines
  // of their own): the Grit it was played with, a card played to boost it, a
  // Marketing card (its total Stonk count), a launched Poker.
  | { kind: 'grit'; value: number }
  | { kind: 'boost' }
  | { kind: 'marketing'; stonks: number }
  | { kind: 'poker_launch' };

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
  let openCorruption: { officerType: string; actions: CorruptionStep[] } | null = null;
  let pendingStep: Omit<CorruptionStep, 'action'> = { arrestedOwnerIds: [], dopeTypes: [] };

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
          pendingStep = { arrestedOwnerIds: [], dopeTypes: [] };
        }
        break;
      case 'OfficerMoved':
        if (openCorruption) {
          pendingStep.hoodId = (event.hood_id as string | null) ?? undefined;
          pendingStep.spotId = (event.spot_id as string | null) ?? undefined;
        }
        break;
      case 'PawnArrested':
        if (openCorruption) pendingStep.arrestedOwnerIds.push(eventPlayerId as string);
        break;
      case 'DopeConfiscated':
        if (openCorruption) pendingStep.dopeTypes.push(event.dope_type as string);
        break;
      case 'CorruptionActionApplied':
        if (openCorruption && eventPlayerId === actingPlayerId) {
          openCorruption.actions.push({ action: event.action as string, ...pendingStep });
        }
        pendingStep = { arrestedOwnerIds: [], dopeTypes: [] };
        break;
      case 'GritActionChosen':
        if (eventPlayerId === actingPlayerId) {
          items.push({ kind: 'grit', value: event.grit_value as number });
        }
        break;
      case 'CustomerCardBoostPlayed':
        if (eventPlayerId === actingPlayerId) items.push({ kind: 'boost' });
        break;
      case 'MarketingCardPlayed':
        if (eventPlayerId === actingPlayerId) {
          const allocations = (event.allocations as [string, number][] | undefined) ?? [];
          items.push({
            kind: 'marketing',
            stonks: allocations.reduce((sum, [, delta]) => sum + Math.abs(delta), 0),
          });
        }
        break;
      case 'PokerLaunched':
        if (eventPlayerId === actingPlayerId) items.push({ kind: 'poker_launch' });
        break;
      case 'LinkSpentForExtraAction':
        if (eventPlayerId === actingPlayerId) {
          items.push({
            kind: 'use_link',
            contactId: event.contact_id as string,
            level: event.link_level as number,
          });
        }
        break;
      case 'OfficerCorruptionResolved':
        flushCorruption();
        break;
      case 'CriminalPlaced':
        if (eventPlayerId === actingPlayerId) {
          items.push({
            kind: 'place',
            hoodId: event.hood_id as string,
            cost: event.cost as number | undefined, // missing on an older backend
          });
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
          items.push({
            kind: 'buy',
            hoodId: event.hood_id as string,
            dopeType: event.dope_type as string,
            pricePaid: event.price_paid as number,
          });
        }
        break;
      case 'DopeSold':
        if (eventPlayerId === actingPlayerId) {
          items.push({
            kind: 'sell',
            spotId: event.spot_id as string,
            dopeType: event.dope_type as string,
            priceReceived: event.price_received as number,
          });
        }
        break;
      case 'OfficerBought':
        // OfficerBought uses buyer_player_id/seller_player_id, not
        // player_id — officer_type isn't on the event at all, resolved
        // by the caller (resolveOfficerTypes) via view.officers afterward.
        if (event.buyer_player_id === actingPlayerId) {
          items.push({ kind: 'buy_officer', officerType: '', price: event.price as number });
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

function hoodContact(hoodId: string, view: GameViewResponse): string {
  return view.hoods.find((h) => h.hood_id === hoodId)?.contact_id ?? hoodId;
}

function spotContact(spotId: string, view: GameViewResponse): string {
  return view.spots.find((s) => s.spot_id === spotId)?.contact_id ?? spotId;
}

/** What an action is played with: the round's Grit, or a spent Link. */
export type ActionPower =
  | { kind: 'grit'; value: number }
  | { kind: 'link'; contactId: string; level: number };

/** One narrated action: its (merged) items, what powered it and the extras
 *  that came with it (a boost card, Marketing, a Poker launch). */
export type ExtraMarker = { kind: 'boost' } | { kind: 'marketing'; stonks: number };

export interface ActionGroup {
  kind: ActionItem['kind'];
  group: ActionItem[];
  power?: ActionPower;
  extras: ExtraMarker[];
}

function extrasText(extras: ExtraMarker[]): string[] {
  return extras.map((extra) =>
    extra.kind === 'boost' ? "gioca una carta per potenziare l'azione" : `gioca Marketing da ${extra.stonks}`,
  );
}

const CONTACT_LABEL: Record<string, { name: string; article: string }> = {
  artisti: { name: 'Artisti', article: 'gli' },
  studenti: { name: 'Studenti', article: 'gli' },
  manager: { name: 'Manager', article: 'i' },
  preti: { name: 'Preti', article: 'i' },
  politici: { name: 'Politici', article: 'i' },
};

export function powerText(power: ActionPower): string {
  if (power.kind === 'grit') return `Grinta ${power.value}`;
  const contact = CONTACT_LABEL[power.contactId];
  return `un Gancio di livello ${power.level} con ${contact ? `${contact.article} ${contact.name}` : power.contactId}`;
}

// Turns the flat list of events-as-items into one entry per action: the
// Grit / Link that powers it and the boost / Marketing / Poker that go with
// it are folded into the action that follows them, instead of being lines of
// their own.
export function buildActionGroups(items: ActionItem[]): ActionGroup[] {
  const groups: ActionGroup[] = [];
  let power: ActionPower | undefined;
  let extras: ExtraMarker[] = [];
  let i = 0;
  while (i < items.length) {
    const item = items[i];
    if (item.kind === 'grit') {
      power = { kind: 'grit', value: item.value };
      i++;
      continue;
    }
    if (item.kind === 'use_link') {
      power = { kind: 'link', contactId: item.contactId, level: item.level };
      i++;
      continue;
    }
    if (item.kind === 'boost') {
      extras.push({ kind: 'boost' });
      i++;
      continue;
    }
    if (item.kind === 'marketing') {
      extras.push({ kind: 'marketing', stonks: item.stonks });
      i++;
      continue;
    }
    if (item.kind === 'poker_launch') {
      // A Poker launch is announced on its own, ahead of the action it came with.
      groups.push({ kind: 'poker_launch', group: [item], extras: [] });
      i++;
      continue;
    }
    const kind = item.kind;
    const group: ActionItem[] = [item];
    i++;
    if (MERGE_KINDS.has(kind)) {
      while (i < items.length && items[i].kind === kind) {
        group.push(items[i]);
        i++;
      }
    }
    groups.push({ kind, group, power: kind === 'pass' ? undefined : power, extras });
    power = undefined;
    extras = [];
  }
  // A spent Link whose action never resolved is still worth a line of its own.
  if (power?.kind === 'link') {
    groups.push({
      kind: 'use_link',
      group: [{ kind: 'use_link', contactId: power.contactId, level: power.level }],
      extras,
    });
  }
  return groups;
}

// [present tense, infinitive] — "compra …" on its own, "usa Grinta 2 per
// acquistare …" when the action is introduced by what powers it.
const VERB_BY_KIND: Partial<Record<ActionItem['kind'], [string, string]>> = {
  place: ['piazza', 'piazzare'],
  move: ['sposta', 'spostare'],
  buy: ['compra', 'acquistare'],
  sell: ['vende', 'vendere'],
  corrupt: ['corrompe', 'corrompere'],
  buy_officer: ['compra', 'comprare'],
};

function actionObject(kind: ActionItem['kind'], group: ActionItem[], view: GameViewResponse): string {
  switch (kind) {
    case 'place': {
      const items = group as Extract<ActionItem, { kind: 'place' }>[];
      const n = items.length;
      return `${n} ${pluralize(n, 'criminale', 'criminali')} ${locationPhrase(items.map((i) => hoodContact(i.hoodId, view)))}`;
    }
    case 'move': {
      const items = group as Extract<ActionItem, { kind: 'move' }>[];
      if (items.length === 1) {
        return `da un quartiere ${hoodContact(items[0].fromHoodId, view)} a uno ${hoodContact(items[0].toHoodId, view)}`;
      }
      return `${items.length} criminali`;
    }
    case 'buy': {
      const items = group as Extract<ActionItem, { kind: 'buy' }>[];
      return `${dopeSummary(items.map((i) => i.dopeType))} ${locationPhrase(items.map((i) => hoodContact(i.hoodId, view)))}`;
    }
    case 'sell': {
      const items = group as Extract<ActionItem, { kind: 'sell' }>[];
      return `${dopeSummary(items.map((i) => i.dopeType))} ${locationPhrase(items.map((i) => spotContact(i.spotId, view)))}`;
    }
    case 'corrupt': {
      const item = group[0] as Extract<ActionItem, { kind: 'corrupt' }>;
      const detail = corruptionDetail(item.actions, view);
      const officer = officerLabel(item.officerType, 1);
      return detail ? `${officer}: ${detail}` : officer;
    }
    case 'buy_officer': {
      const items = group as Extract<ActionItem, { kind: 'buy_officer' }>[];
      const counts = new Map<string, number>();
      for (const i of items) counts.set(i.officerType, (counts.get(i.officerType) ?? 0) + 1);
      return Array.from(counts.entries()).map(([type, n]) => officerLabel(type, n)).join(' e ');
    }
    default:
      return '';
  }
}

export function textForGroup(
  kind: ActionItem['kind'],
  group: ActionItem[],
  view: GameViewResponse,
  power?: ActionPower,
  extras: ExtraMarker[] = [],
): string {
  let text: string;
  if (kind === 'pass') {
    text = 'passa';
  } else if (kind === 'poker_launch') {
    text = 'lancia un Poker';
  } else if (kind === 'use_link') {
    const item = group[0] as Extract<ActionItem, { kind: 'use_link' }>;
    text = `usa ${powerText({ kind: 'link', contactId: item.contactId, level: item.level })} per un'azione extra`;
  } else {
    const verbs = VERB_BY_KIND[kind];
    const object = actionObject(kind, group, view);
    if (!verbs) text = object;
    else if (power) text = `usa ${powerText(power)} per ${verbs[1]} ${object}`;
    else text = `${verbs[0]} ${object}`;
  }
  const extraLines = extrasText(extras);
  return extraLines.length > 0 ? `${text} (${extraLines.join(', ')})` : text;
}

export interface BannerIcon {
  src: string;
  alt: string;
}

// The bot-turn banner is picture-first (game designer, 2026-10-08): a row of
// units, one per target of the action — "[buy icon][Dope bought]" three times
// for a Grit-3 purchase, "[place icon][Hood's Client][-2$][card]" per placed
// Criminal — and almost no words.
export type BannerPart =
  | { kind: 'icon'; src: string; alt: string; variant?: 'dope' | 'white' }
  | { kind: 'text'; text: string }
  | { kind: 'star' } // the big asterisk that announces a spent Link
  | { kind: 'officer-action'; action: 'move' | 'arrest' | 'confiscate' }; // what a corrupted Cop/Fed did

export interface BannerUnit {
  // The separator drawn before this unit when it isn't the default "/" (a
  // corrupted officer's own orders follow the officer after a "|").
  lead?: string;
  actionIconSrc?: string;
  // True for the white place/move/buy/sell files, false for the dark ones.
  actionIconWhite?: boolean;
  parts: BannerPart[];
}

export interface BannerAction {
  // Before the units: a spent Link's Client icon, a played boost / Marketing.
  prefix: BannerPart[];
  units: BannerUnit[];
  // A plain line when the beat is words only (pass, Poker launch).
  text?: string;
  // A second line (kept for corruption, to be reworked).
  detailText?: string;
}

const ACTION_TYPE_BY_KIND: Partial<Record<ActionItem['kind'], string>> = {
  place: 'place_criminal',
  move: 'move_criminal',
  buy: 'buy_dope',
  sell: 'sell_dope',
  corrupt: 'corrupt_officer',
  buy_officer: 'buy_officer',
};

// These icon files are white line art; the others are dark.
const WHITE_ICON_ACTION_TYPES = new Set(['place_criminal', 'move_criminal', 'buy_dope', 'sell_dope']);

function actionUnit(kind: ActionItem['kind'], parts: BannerPart[]): BannerUnit {
  const actionType = ACTION_TYPE_BY_KIND[kind];
  return {
    actionIconSrc: actionType ? actionTypeAssetUrl(actionType) || undefined : undefined,
    actionIconWhite: actionType ? WHITE_ICON_ACTION_TYPES.has(actionType) : undefined,
    parts,
  };
}

function iconPart(src: string | undefined, alt: string, variant?: 'dope' | 'white'): BannerPart[] {
  return src ? [{ kind: 'icon', src, alt, variant }] : [];
}

// Cost of a single Cop/Fed corruption (CLAUDE.md §11.7) — fixed and never
// discounted, so safe as a presentation-layer constant.
const CORRUPTION_COST_BY_OFFICER_TYPE: Record<string, number> = { cop: 2, fed: 3 };

// "-2$" / "+5$"; a free purchase (price 0) still shows "0$".
function costText(amount: number | undefined): BannerPart[] {
  if (amount === undefined) return [];
  return [{ kind: 'text', text: amount === 0 ? '0$' : `${amount < 0 ? '-' : '+'}${Math.abs(amount)}$` }];
}

export function bannerActionForGroup(
  kind: ActionItem['kind'],
  group: ActionItem[],
  view: GameViewResponse,
  power?: ActionPower,
  extras: ExtraMarker[] = [],
): BannerAction {
  const prefix: BannerPart[] = [];
  if (power?.kind === 'link') {
    prefix.push({ kind: 'star' }, ...iconPart(hoodContactAssetUrl(power.contactId), power.contactId));
  }
  // (A boost card has no icon of its own any more: it stays in the log text.)
  for (const extra of extras) {
    if (extra.kind === 'marketing') {
      prefix.push(...iconPart(marketingIcon, 'Marketing', 'white'), { kind: 'text', text: String(extra.stonks) });
    }
  }
  const banner: BannerAction = { prefix, units: [] };

  switch (kind) {
    case 'place': {
      const items = group as Extract<ActionItem, { kind: 'place' }>[];
      banner.units = items.map((i) =>
        actionUnit('place', [
          ...iconPart(hoodContactAssetUrl(hoodContact(i.hoodId, view)), hoodContact(i.hoodId, view)),
          ...costText(i.cost === undefined ? undefined : -i.cost),
        ]),
      );
      break;
    }
    case 'move': {
      const items = group as Extract<ActionItem, { kind: 'move' }>[];
      banner.units = items.map((i) =>
        actionUnit('move', [
          ...iconPart(hoodContactAssetUrl(hoodContact(i.toHoodId, view)), hoodContact(i.toHoodId, view)),
        ]),
      );
      break;
    }
    case 'buy': {
      const items = group as Extract<ActionItem, { kind: 'buy' }>[];
      banner.units = items.map((i) =>
        actionUnit('buy', [...iconPart(DOPE_ASSET[i.dopeType], i.dopeType, 'dope'), ...costText(-i.pricePaid)]),
      );
      break;
    }
    case 'sell': {
      const items = group as Extract<ActionItem, { kind: 'sell' }>[];
      banner.units = items.map((i) =>
        actionUnit('sell', [...iconPart(DOPE_ASSET[i.dopeType], i.dopeType, 'dope'), ...costText(i.priceReceived)]),
      );
      break;
    }
    case 'buy_officer': {
      const items = group as Extract<ActionItem, { kind: 'buy_officer' }>[];
      banner.units = items.map((i) =>
        actionUnit('buy_officer', [
          ...iconPart(OFFICER_ASSET[i.officerType as 'cop' | 'fed'], i.officerType),
          ...costText(-i.price),
        ]),
      );
      break;
    }
    case 'corrupt': {
      // The officer and its cost, then one unit per order it was given:
      // [order icon] + where it went / whom it arrested / what it seized.
      const item = group[0] as Extract<ActionItem, { kind: 'corrupt' }>;
      banner.units = [
        actionUnit('corrupt', [
          ...iconPart(OFFICER_ASSET[item.officerType as 'cop' | 'fed'], item.officerType),
          ...costText(-(CORRUPTION_COST_BY_OFFICER_TYPE[item.officerType] ?? 0)),
        ]),
        ...item.actions.map((step, i): BannerUnit => {
          const kind = step.action === 'move' || step.action === 'arrest' ? step.action : 'confiscate';
          const targets: BannerPart[] =
            kind === 'move'
              ? iconPart(
                  hoodContactAssetUrl(step.hoodId ? hoodContact(step.hoodId, view) : spotContact(step.spotId ?? '', view)),
                  'destinazione',
                )
              : kind === 'arrest'
                ? step.arrestedOwnerIds.flatMap((ownerId) => iconPart(pawnAssetForPlayer(ownerId), 'pedina arrestata'))
                : step.dopeTypes.flatMap((dopeType) => iconPart(DOPE_ASSET[dopeType], dopeType, 'dope'));
          return { lead: i === 0 ? '|' : '/', parts: [{ kind: 'officer-action', action: kind }, ...targets] };
        }),
      ];
      break;
    }
    case 'use_link': {
      // A spent Link whose action never resolved: just the Client's icon.
      const item = group[0] as Extract<ActionItem, { kind: 'use_link' }>;
      banner.prefix = [{ kind: 'star' }, ...iconPart(hoodContactAssetUrl(item.contactId), item.contactId)];
      banner.text = 'Gancio usato';
      break;
    }
    case 'poker_launch':
      banner.text = 'Lancia un Poker';
      break;
    case 'pass':
      banner.text = 'Passa';
      break;
    default:
      break;
  }
  return banner;
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

  const colorLabel = playerColorLabelForId(actingPlayerId);
  const lines = buildActionGroups(resolvedItems).map(
    ({ kind, group, power, extras }) => `${colorLabel} ${textForGroup(kind, group, view, power, extras)}`,
  );
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
  const pokerOutcome = view.last_poker_outcome;
  if (pokerOutcome && resolvedMatchIds.has(pokerOutcome.match_id)) {
    if (pokerOutcome.winner_id) {
      const shape = pokerOutcome.top_hand_shape
        ? (POKER_HAND_SHAPE_LABEL[pokerOutcome.top_hand_shape] ?? pokerOutcome.top_hand_shape)
        : '';
      lines.push(
        `Poker: vince ${playerColorLabelForId(pokerOutcome.winner_id)} (${shape}), +$${pokerOutcome.cash_won}`,
      );
    } else if (pokerOutcome.tied_ids.length > 0) {
      lines.push(
        `Poker: pareggio tra ${pokerOutcome.tied_ids.map(playerColorLabelForId).join(', ')}, jackpot riportato`,
      );
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
