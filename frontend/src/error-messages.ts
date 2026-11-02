import { t, tDyn } from './i18n';
import type { DomainErrorResponse } from './types';

// The text (see i18n/texts/errors.ts, `error.<code>`) for the DomainError codes a player can
// realistically hit through the real UI (races against a stale view, funds/capacity that
// changed since the last render, a Skill/limit already used this round).
// Codes that normally only fire for an unvalidated/bot client (a client
// picking outside its own offered options) are deliberately left out —
// they fall back to the generic text instead of being enumerated
// one by one, since a real player using the offered UI should rarely if
// ever see them.

// `error` is either the full backend error (a DomainErrorResponse, for
// every setError call fed from a CommandResultResponse) or a raw string
// (the 2 catch-block call sites in App.tsx, a network/JS exception with
// no `code` to look up) — both render through here so the sidebar's
// single `.error` paragraph never needs its own type-narrowing logic.
export function friendlyErrorMessage(error: DomainErrorResponse | string): string {
  if (typeof error === 'string') return error;

  if (error.code === 'insufficient_funds') {
    const required = error.details?.required;
    const available = error.details?.available;
    if (typeof required === 'number' && typeof available === 'number') {
      return t('error.insufficient_funds_detail', { required, available });
    }
  }

  return tDyn(`error.${error.code}`) ?? t('error.generic');
}
