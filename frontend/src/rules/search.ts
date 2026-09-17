import type { RulePage } from './types';

// Plain case-folded substring match over every text field a page has —
// no search library: at this content scale (under 100 pages) a
// per-keystroke .filter() is sub-millisecond, so a library would only
// add complexity for a non-problem.
export function searchRules(query: string, pages: RulePage[]): RulePage[] {
  const needle = query.trim().toLocaleLowerCase('it');
  if (needle === '') return [];
  return pages.filter((page) => haystackFor(page).includes(needle));
}

function haystackFor(page: RulePage): string {
  const parts = [
    page.title,
    page.summary,
    ...(page.keywords ?? []),
    ...(page.cosaServe ?? []),
    ...(page.cosaFai ?? []),
    ...(page.cosaSuccede ?? []),
    ...(page.attenzione ?? []),
    page.esempio ?? '',
  ];
  return parts.join(' \n ').toLocaleLowerCase('it');
}
