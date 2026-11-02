import type { TextKey } from '../i18n';

// RulesHome's "Come faccio a...?" / "Cosa succede se...?" shortcut lists
// (game designer's spec §6) — trimmed to only the questions a v1 slug can
// actually answer. Extend both lists as content/*.ts is backfilled; a
// question pointing at a slug with no page yet would be a dead link, so
// don't add one ahead of its content. The questions' words are in i18n/texts/rules.ts.
export interface QuickLink {
  question: TextKey;
  slug: string;
}

export const HOW_DO_I_LINKS: QuickLink[] = [
  { question: 'rules.how.buy', slug: 'actions/buy-dope' },
  { question: 'rules.how.sell', slug: 'actions/sell-dope' },
  { question: 'rules.how.link', slug: 'characters/link' },
  { question: 'rules.how.launchPoker', slug: 'events/poker' },
  { question: 'rules.how.joinPoker', slug: 'events/poker' },
  { question: 'rules.how.manipulateCop', slug: 'police/cop' },
  { question: 'rules.how.manipulateFed', slug: 'police/fed' },
  { question: 'rules.how.bribe', slug: 'police/cop' },
  { question: 'rules.how.job', slug: 'jobs/job' },
  { question: 'rules.how.rep', slug: 'jobs/reputation' },
  { question: 'rules.how.extra', slug: 'characters/link' },
];

export const WHAT_IF_LINKS: QuickLink[] = [
  { question: 'rules.if.brawl', slug: 'events/brawl' },
  { question: 'rules.if.dopeOut', slug: 'actions/buy-dope' },
  { question: 'rules.if.spotFull', slug: 'actions/sell-dope' },
  { question: 'rules.if.jailFull', slug: 'locations/jail-evasion' },
  { question: 'rules.if.criminalArrested', slug: 'locations/jail' },
  { question: 'rules.if.linkArrested', slug: 'police/fed' },
  { question: 'rules.if.pokerLost', slug: 'events/poker' },
  { question: 'rules.if.jobDone', slug: 'jobs/job' },
  { question: 'rules.if.raidLost', slug: 'raids/raid' },
  { question: 'rules.if.roundEnds', slug: 'basics/round' },
  { question: 'rules.if.turnEnds', slug: 'basics/game-structure' },
];
