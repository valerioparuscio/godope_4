import { EVENT_SOUNDS, SOUND_EFFECTS, type EventSoundCategory } from './assets';
import type { GameEventResponse } from './types';

const audioCache = new Map<string, HTMLAudioElement>();

export function randomSoundUrls(category: EventSoundCategory): string[] {
  const choices = EVENT_SOUNDS[category];
  return choices.length ? [choices[Math.floor(Math.random() * choices.length)]] : [];
}

export function soundEffectUrls(name: string): string[] {
  return SOUND_EFFECTS[name] ? [SOUND_EFFECTS[name]] : [];
}

const MOVE_EVENTS = new Set([
  'CriminalMoved', 'OfficerMoved', 'PawnBecameGambler', 'GamblerBecameCriminal',
  'GamblerEvictedFromDen', 'LinkLevelChanged', 'LinkPawnReturnedToBase', 'PawnDefeatedInBrawl',
]);
const CARD_EVENTS = new Set([
  'CardDrawn', 'CardsDiscarded', 'MarketingCardPlayed', 'CustomerCardBoostPlayed',
  'PokerCardRevealed', 'BrawlCardRevealed', 'SkillDrawn', 'SkillDiscarded',
]);

function awardsMoney(event: GameEventResponse): boolean {
  return (event.event_type === 'DopeSold' && Number(event.price_received) > 0)
    || (event.event_type === 'PokerMatchResolved' && Number(event.cash_won) > 0)
    || (event.event_type === 'BrawlTriggerTollCollected' && Number(event.amount) > 0)
    || (event.event_type === 'BrawlLoserRewardChosen' && event.reward_type === 'money')
    || (event.event_type === 'JobBonusClaimed' && event.bonus_type === 'money');
}

// One random clip per action package, even when it places several pawns
// or handles multiple officers, so simultaneous events do not stack voices.
export function actionSoundUrlsForEvents(events: GameEventResponse[]): string[] {
  const urls: string[] = [];
  if (events.some((e) => e.event_type === 'CriminalPlaced')) {
    urls.push(...randomSoundUrls('recruit'));
  }
  if (events.some((e) => ['CopEnteredHood', 'OfficerCorruptionStarted', 'OfficerBought'].includes(e.event_type))) {
    urls.push(...randomSoundUrls('police'));
  }
  const types = new Set(events.map((e) => e.event_type));
  if (events.some((e) => MOVE_EVENTS.has(e.event_type))) urls.push(...soundEffectUrls('move'));
  if (types.has('DopeBought') || types.has('OfficerBought')) urls.push(...soundEffectUrls('buy'));
  if (events.some(awardsMoney)) urls.push(...soundEffectUrls('coins'));
  if (events.some((e) => CARD_EVENTS.has(e.event_type)
    || (e.event_type === 'BrawlLoserRewardChosen' && e.reward_type === 'card' && e.stolen_card_id))) {
    urls.push(...soundEffectUrls('cards_shuffle'));
  }
  if (events.some((e) => (e.event_type === 'PokerBetsPlaced' && Array.isArray(e.match_ids) && e.match_ids.length > 0)
    || (e.event_type === 'BrawlLoserRewardChosen' && e.reward_type === 'poker_chip'))) {
    urls.push(...soundEffectUrls('pker_chips'));
  }
  if (types.has('BrawlStarted')) urls.push(...soundEffectUrls('guns'));
  if (types.has('PawnArrested')) urls.push(...soundEffectUrls('jail_enter'));
  if (types.has('JailEscapeTriggered')) urls.push(...soundEffectUrls('escape'));
  if (types.has('JobCompleted')) {
    urls.push(...soundEffectUrls('job_done'), ...randomSoundUrls('job'));
  }
  return urls;
}

// Actions already accompanied by a narrated bot beat must not play again
// when the board reveals the segment. Secondary events still sound there.
export function soundUrlsForPlaybackEvents(events: GameEventResponse[], actingPlayerId: string): string[] {
  const narrated = new Set([
    'CriminalPlaced', 'CriminalMoved', 'DopeBought', 'DopeSold', 'OfficerCorruptionStarted',
  ]);
  return actionSoundUrlsForEvents(events.filter((e) => !(
    (narrated.has(e.event_type) && e.player_id === actingPlayerId)
    || (e.event_type === 'OfficerBought' && e.buyer_player_id === actingPlayerId)
  )));
}

// Plays a short (<=2s) sound effect, reusing one HTMLAudioElement per URL
// (rewound via currentTime, not re-created) so rapid repeats — e.g. a
// batch buy of the same Dope type — don't pile up new Audio objects.
export function playSound(url: string): void {
  let audio = audioCache.get(url);
  if (!audio) {
    audio = new Audio(url);
    audioCache.set(url, audio);
  } else {
    audio.currentTime = 0;
  }
  // Browsers reject play() when it's not triggered by a user gesture —
  // every call site here is downstream of a click (SetupScreen's "Nuova
  // partita", a decision submit), so this should never actually reject;
  // still, never let it surface as an unhandled rejection / console error.
  void audio.play().catch(() => {});
}
