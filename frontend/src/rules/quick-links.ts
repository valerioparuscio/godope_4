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
  { question: 'Vendere Dope?', slug: 'actions/sell-dope' },
  { question: 'Diventare Link?', slug: 'characters/link' },
  { question: 'Lanciare un Poker?', slug: 'events/poker' },
  { question: 'Partecipare al Poker?', slug: 'events/poker' },
  { question: 'Corrompere un Cop?', slug: 'police/cop' },
  { question: 'Corrompere un Fed?', slug: 'police/fed' },
  { question: 'Comprare un Cop/Fed?', slug: 'police/cop' },
  { question: 'Completare un Job?', slug: 'jobs/job' },
  { question: 'Ottenere REP?', slug: 'jobs/reputation' },
  { question: "Ottenere un'azione extra?", slug: 'characters/link' },
];

export const WHAT_IF_LINKS: QuickLink[] = [
  { question: 'entra un Criminale che fa scattare una Rissa?', slug: 'events/brawl' },
  { question: 'finisce la Dope in un mercato?', slug: 'actions/buy-dope' },
  { question: 'uno Spot si riempie?', slug: 'actions/sell-dope' },
  { question: 'il quarto posto della Jail viene occupato?', slug: 'locations/jail-evasion' },
  { question: 'arrestano il mio Criminale?', slug: 'locations/jail' },
  { question: 'arrestano il mio Link?', slug: 'police/fed' },
  { question: 'perdo un Poker?', slug: 'events/poker' },
  { question: 'completo un Job?', slug: 'jobs/job' },
  { question: 'perdo una Retata?', slug: 'raids/raid' },
  { question: 'termina un round?', slug: 'basics/round' },
  { question: 'termina un turno?', slug: 'basics/game-structure' },
];
