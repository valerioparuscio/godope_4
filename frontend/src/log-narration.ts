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
  playerColorLabelForId,
  POKER_HAND_SHAPE_LABEL,
  RAID_CRITERION_LABEL,
} from './assets';
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
  | { kind: 'place'; hoodId: string }
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
export interface ActionGroup {
  kind: ActionItem['kind'];
  group: ActionItem[];
  power?: ActionPower;
  extras: string[];
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
  let extras: string[] = [];
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
      extras.push("gioca una carta per potenziare l'azione");
      i++;
      continue;
    }
    if (item.kind === 'marketing') {
      extras.push(`gioca Marketing da ${item.stonks}`);
      i++;
      continue;
    }
    if (item.kind === 'poker_launch') {
      extras.push('lancia un Poker');
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
  extras: string[] = [],
): string {
  let text: string;
  if (kind === 'pass') {
    text = 'passa';
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
  return extras.length > 0 ? `${text} (${extras.join(', ')})` : text;
}

export interface BannerIcon {
  src: string;
  alt: string;
  kind?: 'dope';
}

// Cost of a single Cop/Fed corruption (CLAUDE.md §11.7: "Cop: 2 dollari;
// Fed: 3 dollari") — fixed and never discounted, so safe to keep as a
// small presentation-layer constant here (no event field carries it,
// unlike OfficerBought.price which already reflects any real discount).
const CORRUPTION_COST_BY_OFFICER_TYPE: Record<string, number> = { cop: 2, fed: 3 };

// The bot-turn banner's own content for one merged group (designer's
// mockups, 2026-09-17: "SPOSTA [pedine] IN [quartieri]",
// "ACQUISTA [merci] A [costo]$" — a verb + subject icons, then a
// preposition + trailing icons/cost, no prose sentence). `place`/`move`
// have no per-type art for "what's moved" (a Criminal isn't typed the
// way a Dope token is), so their subject is a plain dot count instead of
// icons; every icon list is one entry per underlying item, not
// deduplicated. Jail/arrest icons are deliberately left out for now (no
// asset yet).
export interface BannerAction {
  verb: string;
  subjectDotCount: number;
  subjectIcons: BannerIcon[];
  preposition: string;
  trailingIcons: BannerIcon[];
  costLabel: string;
  // Optional second line under the main row (e.g. what a corruption did).
  detailText?: string;
  // What powers the action ("GRINTA 2", "GANCIO LV.2"), shown as a chip before
  // the verb, with the Link's Contact icon when it was a Link.
  // Grit value or Link level, shown as a number in a circle (like the action
  // icons); a Link also shows its Contact's icon.
  powerValue?: number;
  powerIconSrc?: string;
  // The action's own icon, shown before its verb; `actionIconWhite` says the
  // file is white line art (place/move/buy/sell) rather than dark.
  actionIconSrc?: string;
  actionIconWhite?: boolean;
}

const EMPTY_BANNER_ACTION: Omit<BannerAction, 'verb'> = {
  subjectDotCount: 0,
  subjectIcons: [],
  preposition: '',
  trailingIcons: [],
  costLabel: '',
};

export function bannerActionForGroup(
  kind: ActionItem['kind'],
  group: ActionItem[],
  view: GameViewResponse,
  power?: ActionPower,
  extras: string[] = [],
): BannerAction {
  const banner = baseBannerAction(kind, group, view);
  if (power) {
    banner.powerValue = power.kind === 'grit' ? power.value : power.level;
    if (power.kind === 'link') banner.powerIconSrc = hoodContactAssetUrl(power.contactId) || undefined;
  }
  const actionType = ACTION_TYPE_BY_KIND[kind];
  if (actionType) {
    banner.actionIconSrc = actionTypeAssetUrl(actionType) || undefined;
    banner.actionIconWhite = WHITE_ICON_ACTION_TYPES.has(actionType);
  }
  // The detail line reads as sentences: each part starts with a capital.
  const detail = [banner.detailText, ...extras]
    .filter((part): part is string => !!part)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1));
  banner.detailText = detail.length > 0 ? detail.join(' · ') : undefined;
  return banner;
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

function baseBannerAction(
  kind: ActionItem['kind'],
  group: ActionItem[],
  view: GameViewResponse,
): BannerAction {
  switch (kind) {
    case 'place': {
      const items = group as Extract<ActionItem, { kind: 'place' }>[];
      return {
        ...EMPTY_BANNER_ACTION,
        verb: 'Piazza',
        subjectDotCount: items.length,
        preposition: 'in',
        trailingIcons: items
          .map((i) => hoodContact(i.hoodId, view))
          .map((contactId) => ({ src: hoodContactAssetUrl(contactId), alt: contactId }))
          .filter((icon) => icon.src),
      };
    }
    case 'move': {
      const items = group as Extract<ActionItem, { kind: 'move' }>[];
      return {
        ...EMPTY_BANNER_ACTION,
        verb: 'Sposta',
        subjectDotCount: items.length,
        preposition: 'in',
        trailingIcons: items
          .map((i) => hoodContact(i.toHoodId, view))
          .map((contactId) => ({ src: hoodContactAssetUrl(contactId), alt: contactId }))
          .filter((icon) => icon.src),
      };
    }
    case 'buy': {
      const items = group as Extract<ActionItem, { kind: 'buy' }>[];
      return {
        ...EMPTY_BANNER_ACTION,
        verb: 'Acquista',
        subjectIcons: items
          .map((i) => ({ src: DOPE_ASSET[i.dopeType], alt: i.dopeType, kind: 'dope' as const }))
          .filter((icon) => icon.src),
        preposition: 'a',
        costLabel: `${items.reduce((sum, i) => sum + i.pricePaid, 0)}$`,
      };
    }
    case 'sell': {
      const items = group as Extract<ActionItem, { kind: 'sell' }>[];
      return {
        ...EMPTY_BANNER_ACTION,
        verb: 'Vende',
        subjectIcons: items
          .map((i) => ({ src: DOPE_ASSET[i.dopeType], alt: i.dopeType, kind: 'dope' as const }))
          .filter((icon) => icon.src),
        preposition: 'a',
        costLabel: `${items.reduce((sum, i) => sum + i.priceReceived, 0)}$`,
      };
    }
    case 'corrupt': {
      const item = group[0] as Extract<ActionItem, { kind: 'corrupt' }>;
      const src = OFFICER_ASSET[item.officerType as 'cop' | 'fed'];
      return {
        ...EMPTY_BANNER_ACTION,
        verb: 'Corrompe',
        subjectIcons: src ? [{ src, alt: item.officerType }] : [],
        preposition: 'a',
        costLabel: `${CORRUPTION_COST_BY_OFFICER_TYPE[item.officerType] ?? 0}$`,
        detailText: corruptionDetail(item.actions, view) || undefined,
      };
    }
    case 'use_link': {
      const item = group[0] as Extract<ActionItem, { kind: 'use_link' }>;
      const src = hoodContactAssetUrl(item.contactId);
      return {
        ...EMPTY_BANNER_ACTION,
        verb: 'Usa un Gancio',
        subjectIcons: src ? [{ src, alt: item.contactId }] : [],
        detailText: `livello ${item.level}: azione extra`,
      };
    }
    case 'buy_officer': {
      const items = group as Extract<ActionItem, { kind: 'buy_officer' }>[];
      return {
        ...EMPTY_BANNER_ACTION,
        verb: 'Compra',
        subjectIcons: items
          .map((i) => ({ src: OFFICER_ASSET[i.officerType as 'cop' | 'fed'], alt: i.officerType }))
          .filter((icon) => icon.src),
        preposition: 'a',
        costLabel: `${items.reduce((sum, i) => sum + i.price, 0)}$`,
      };
    }
    case 'pass':
      return { ...EMPTY_BANNER_ACTION, verb: 'Passa' };
    default:
      return { ...EMPTY_BANNER_ACTION, verb: '' };
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
