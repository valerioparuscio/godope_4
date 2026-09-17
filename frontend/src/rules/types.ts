// Content model for the in-game rules/tutorial modal (game designer's
// spec, 2026-09-18: docs/rules/DOPE_WEB_REGOLAMENTO_POPUP_SPEC.md §8/§10)
// — plain strings, not markdown or rich-text runs, matching how
// Tutorial.tsx's TUTORIAL_STEPS already authors content. RuleText stays
// a named alias rather than being inlined everywhere so a future switch
// to richer inline-linked runs is a type change here plus one renderer,
// not an interface rewrite.

// Only the 9 namespaces v1 content actually uses (spec §7's own index
// goes much wider long-term — market/cards/marketing/grit/glossary/etc.
// — extending this union later is a one-line additive edit).
export type RuleCategorySlug =
  | 'basics'
  | 'actions'
  | 'characters'
  | 'locations'
  | 'police'
  | 'events'
  | 'jobs'
  | 'raids'
  | 'scoring';

export const RULE_CATEGORY_LABEL: Record<RuleCategorySlug, string> = {
  basics: 'Regole base',
  actions: 'Azioni',
  characters: 'Personaggi',
  locations: 'Luoghi',
  police: 'Polizia e Jail',
  events: 'Poker e Risse',
  jobs: 'Job e Reputazione',
  raids: 'Retate',
  scoring: 'Punteggio',
};

// A page's category is its slug's own first path segment ("locations/jail"
// -> "locations") — derived rather than stored a second time, so the two
// can never drift apart.
export function categoryOfSlug(slug: string): RuleCategorySlug {
  return slug.split('/')[0] as RuleCategorySlug;
}

export interface RuleImage {
  src: string;
  alt: string;
  caption?: string;
}

export type RuleText = string;

export interface RulePage {
  slug: string;
  title: string;
  // "Sintesi" — the only required section: every list surface (search
  // results, category index, quick-links) needs it, so making it
  // required avoids `?? ''` fallbacks scattered across components.
  summary: RuleText;
  keywords?: string[];
  images?: RuleImage[];
  cosaServe?: RuleText[];
  cosaFai?: RuleText[];
  cosaSuccede?: RuleText[];
  attenzione?: RuleText[];
  esempio?: RuleText;
  // "Vedi anche" — slugs, resolved through RULE_PAGE_BY_SLUG at render time.
  related?: string[];
}
