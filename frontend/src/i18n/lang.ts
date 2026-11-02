import { useSyncExternalStore } from 'react';
import type { Lang } from './define';

// The language of the interface (game designer, 2026-11-03: an English version, picked with a
// button on the start screen). It is only presentation: rules, saves, replays and the other
// players' screens are untouched. Remembered in this browser; Italian until the player picks.
const STORAGE_KEY = 'dope_lang';

function readSaved(): Lang {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'it';
  } catch {
    return 'it'; // private/blocked storage: just don't remember it
  }
}

let current: Lang = readSaved();
const listeners = new Set<() => void>();

function applyToDocument(lang: Lang): void {
  if (typeof document !== 'undefined') document.documentElement.lang = lang;
}
applyToDocument(current);

export function getLang(): Lang {
  return current;
}

export function setLang(lang: Lang): void {
  if (lang === current) return;
  current = lang;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // best-effort only
  }
  applyToDocument(lang);
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The current language, re-rendering the caller when it changes. Called once near the root (App),
 *  which re-renders everything below it, so most components can just call `t()`. */
export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getLang, getLang);
}
