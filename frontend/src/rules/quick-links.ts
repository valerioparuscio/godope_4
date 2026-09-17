// RulesHome's "Come faccio a...?" / "Cosa succede se...?" shortcut lists
// (game designer's spec §6) — trimmed to only the questions a v1 slug can
// actually answer. Extend both lists as content/*.ts is backfilled; a
// question pointing at a slug with no page yet would be a dead link, so
// don't add one ahead of its content.
export interface QuickLink {
  question: string;
  slug: string;
}

export const HOW_DO_I_LINKS: QuickLink[] = [
  { question: 'Comprare Dope?', slug: 'actions/buy-dope' },
  { question: 'Lanciare un Poker?', slug: 'events/poker' },
  { question: 'Partecipare al Poker?', slug: 'events/poker' },
];

export const WHAT_IF_LINKS: QuickLink[] = [
  { question: 'finisce la Dope in un mercato?', slug: 'actions/buy-dope' },
  { question: 'il quarto posto della Jail viene occupato?', slug: 'locations/jail-evasion' },
  { question: 'perdo un Poker?', slug: 'events/poker' },
  { question: 'termina un round?', slug: 'basics/round' },
  { question: 'termina un turno?', slug: 'basics/game-structure' },
];
