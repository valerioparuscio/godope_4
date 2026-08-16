const audioCache = new Map<string, HTMLAudioElement>();

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
