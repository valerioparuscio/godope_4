import type { RulePage } from '../types';

export const RAIDS_PAGES: RulePage[] = [
  {
    slug: 'raids/raid',
    title: 'Retata',
    summary: 'Ogni turno si scopre una carta Retata: la squadra che perde secondo il suo criterio macchia la reputazione.',
    keywords: ['retata', 'raid', 'squadra', 'macchiare', 'preti'],
    cosaSuccede: [
      'Chi ha il Link più alto presso i Preti sceglie il primo giocatore del turno, il che fissa anche le due squadre: 1°+4° contro 2°+3°.',
      'Alla fine del turno si sommano, per ogni squadra, i valori del criterio di quella carta (per esempio "più Ganci con i Clienti") tra i due compagni.',
      'La squadra col totale migliore sfugge; l’altra cade e ogni suo componente macchia la propria REP. In caso di parità, cadono tutti e 4.',
    ],
    attenzione: ['Se nessuno ha un Link ai Preti quel turno, resta primo giocatore chi lo era nel turno precedente.'],
    related: ['jobs/reputation', 'characters/link', 'basics/game-structure'],
  },
];
