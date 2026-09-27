import { useEffect, useRef, useState } from 'react';
import { MUSIC_TRACKS } from './assets';

const MUTED_STORAGE_KEY = 'dope_music_muted';
const VOLUME = 0.35;

function loadMutedPref(): boolean {
  try {
    return localStorage.getItem(MUTED_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function saveMutedPref(muted: boolean): void {
  try {
    localStorage.setItem(MUTED_STORAGE_KEY, String(muted));
  } catch {
    // best-effort only
  }
}

function shuffledIndices(): number[] {
  const order = MUSIC_TRACKS.map((_, i) => i);
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  return order;
}

// Cycles through MUSIC_TRACKS in shuffled order (reshuffled once
// exhausted, so a track never repeats until every other one has played)
// for as long as `active` is true — game designer, 2026-09-27: "ho messo
// 4 mp3 in asset, si possono mettere come sottofondo del gioco?". One
// persistent <audio> element (unlike sound.ts's own play-once cache,
// which is for short SFX and never loops); muted state survives a reload
// via localStorage, matching the app's other small per-visitor prefs
// (dope_tutorial_v2_seen).
export function useBackgroundMusic(active: boolean): { muted: boolean; toggleMuted: () => void } {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const orderRef = useRef<number[]>([]);
  const orderIndexRef = useRef(0);
  const [muted, setMuted] = useState(loadMutedPref);

  if (!audioRef.current && MUSIC_TRACKS.length > 0) {
    const audio = new Audio();
    audio.volume = VOLUME;
    audioRef.current = audio;
  }

  // A ref, not a plain function, so the "start playing" effect below can
  // call the *current* render's version without depending on it (it
  // never actually changes shape, just avoids an exhaustive-deps fight).
  const playNextTrackRef = useRef<() => void>(() => {});
  playNextTrackRef.current = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (orderIndexRef.current >= orderRef.current.length) {
      orderRef.current = shuffledIndices();
      orderIndexRef.current = 0;
    }
    const trackIndex = orderRef.current[orderIndexRef.current];
    orderIndexRef.current += 1;
    audio.src = MUSIC_TRACKS[trackIndex];
    void audio.play().catch(() => {});
  };

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.onended = () => playNextTrackRef.current();
    return () => {
      audio.onended = null;
    };
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (active && !muted) {
      if (!audio.src) playNextTrackRef.current();
      else void audio.play().catch(() => {});
    } else {
      audio.pause();
    }
  }, [active, muted]);

  useEffect(() => {
    saveMutedPref(muted);
  }, [muted]);

  return { muted, toggleMuted: () => setMuted((m) => !m) };
}
