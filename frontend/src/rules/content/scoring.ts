import type { RulePage } from '../types';

export const SCORING_PAGES: RulePage[] = [
  {
    slug: 'scoring/final-score',
    title: 'Punteggio finale',
    summary: 'A fine partita denaro, REP, maggioranze, Chip e Skill si convertono tutti in punti: vince chi ne totalizza di più.',
    keywords: ['punteggio', 'punti', 'vittoria', 'maggioranza', 'chip'],
    cosaSuccede: [
      'La posizione sul tracciato del denaro vale punti: 4 per il 1°, 3 per il 2°, 2 per il 3°, 1 per il 4° (in caso di parità di denaro, tutti i pareggiati prendono il valore più basso tra le posizioni in gioco).',
      'Ogni REP pulita vale 2 punti, ogni REP macchiata 1 punto.',
      'Presso ogni Contact, chi ha la maggiore presenza (Criminali = 1, Link = 2) prende 1 punto; in caso di parità nessuno lo prende.',
      'Ogni 3 Chip nel Covo, anche di tipo diverso, valgono 1 punto.',
      'Ogni Skill posseduta vale 1 punto.',
    ],
    attenzione: [
      'In caso di parità di punti totali, vince chi ha più REP non macchiate; se la parità persiste, la vittoria è condivisa.',
    ],
    related: ['jobs/reputation', 'basics/game-structure'],
  },
];
