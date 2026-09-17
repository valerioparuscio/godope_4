import type { RulePage } from '../types';
import { ACTIONS_PAGES } from './actions';
import { BASICS_PAGES } from './basics';
import { CHARACTERS_PAGES } from './characters';
import { EVENTS_PAGES } from './events';
import { JOBS_PAGES } from './jobs';
import { LOCATIONS_PAGES } from './locations';
import { POLICE_PAGES } from './police';
import { RAIDS_PAGES } from './raids';
import { SCORING_PAGES } from './scoring';

// All 9 category files are imported here from day one, even the ones
// still empty stubs — backfilling content later is then just "add array
// entries to an already-wired file," never "create a file and remember
// to register it."
export const ALL_RULE_PAGES: RulePage[] = [
  ...BASICS_PAGES,
  ...ACTIONS_PAGES,
  ...CHARACTERS_PAGES,
  ...LOCATIONS_PAGES,
  ...POLICE_PAGES,
  ...EVENTS_PAGES,
  ...JOBS_PAGES,
  ...RAIDS_PAGES,
  ...SCORING_PAGES,
];

// Same Object.fromEntries(...) construction already used throughout
// assets/index.ts for its own id -> asset lookups.
export const RULE_PAGE_BY_SLUG: Record<string, RulePage> = Object.fromEntries(
  ALL_RULE_PAGES.map((page) => [page.slug, page]),
);

// Dev-only integrity check: a typo'd `related` slug (or one not
// backfilled yet) can't be caught by tsc, since slug/related are plain
// strings — this at least surfaces it immediately in the console instead
// of silently rendering a dead "Vedi anche" link.
if (import.meta.env.DEV) {
  for (const page of ALL_RULE_PAGES) {
    for (const relatedSlug of page.related ?? []) {
      if (!RULE_PAGE_BY_SLUG[relatedSlug]) {
        console.warn(`[rules] ${page.slug} → slug correlato mancante "${relatedSlug}"`);
      }
    }
  }
}
