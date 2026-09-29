import { EVENT_SOUNDS, type EventSoundCategory } from './assets';
import type { GameEventResponse } from './types';

const audioCache = new Map<string, HTMLAudioElement>();

export function randomSoundUrls(category: EventSoundCategory): string[] {
  const choices = EVENT_SOUNDS[category];
  return choices.length ? [choices[Math.floor(Math.random() * choices.length)]] : [];
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
  return urls;
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
