import type { RulePage } from '../types';

export const BASICS_PAGES: RulePage[] = [
  {
    slug: 'basics/game-structure',
    title: 'Struttura della partita',
    summary:
      'Una partita dura 3 turni. Ogni turno è diviso in 3 round di azioni, seguiti dalla Resa dei Conti.',
    keywords: ['turno', 'turni', 'round', 'struttura', 'fasi', 'soffiata', 'resa dei conti'],
    cosaSuccede: [
      'Ogni turno si apre con la Soffiata: si scopre una carta Retata e si sceglie il primo giocatore del turno.',
      'Seguono 3 round di Azione: in ciascuno, ogni giocatore assegna un segnalino Grinta e fa agire le proprie pedine.',
      "Se un giocatore ha lanciato una partita a Poker in un round, si risolve alla fine di quello stesso round, prima di iniziare il round successivo.",
      'Dopo il terzo round si passa alla Resa dei Conti: si verifica chi cade nella Retata di quel turno.',
    ],
    attenzione: [
      'La partita NON dura 4 turni: sono sempre 3 turni da 3 round ciascuno (i "4 giorni" della premessa del gioco sono solo narrativi).',
    ],
    related: ['basics/round', 'events/poker', 'raids/raid'],
  },
  {
    slug: 'basics/round',
    title: 'Il round',
    summary: "In ogni round assegni un segnalino Grinta a un'azione e la fai eseguire da alcune pedine.",
    keywords: ['round', 'grinta', 'azione', 'azione extra', 'link', 'scarto'],
    cosaFai: [
      'Scegli uno dei tuoi 3 segnalini Grinta (valori 1, 2 e 3) e assegnalo a una delle 6 azioni base.',
      "Se vuoi, gioca una o più carte per potenziare l'azione scelta o per fare Marketing.",
      'Fai agire fino al valore del segnalino scelto: ogni pedina che partecipa esegue una copia della stessa azione, dalla propria posizione.',
      "Se hai un Link libero, puoi anche spendere un'azione extra, prima o dopo l'azione principale.",
      'Scarta carte finché non ne hai al massimo 5 in mano.',
    ],
    attenzione: [
      "Il valore della Grinta è un MASSIMO, non un numero obbligatorio: puoi far agire anche una sola pedina pur avendo scelto il segnalino da 3.",
      'Nei 3 round dello stesso turno non puoi scegliere due volte la stessa azione base: usi per forza 3 azioni diverse tra le 6 (l’azione extra da Link fa eccezione, può ripetersi).',
    ],
    related: ['basics/game-structure', 'actions/buy-dope'],
  },
  {
    slug: 'basics/goal',
    title: 'Obiettivo',
    summary:
      'Sei il Boss di una Gang che cerca di farsi spazio nel malaffare cittadino: vince chi accumula più Respect (REP) a fine partita.',
    keywords: ['obiettivo', 'respect', 'rep', 'vittoria', 'boss', 'gang'],
    cosaSuccede: [
      "Completi Job per guadagnare REP, gestendo Criminali, Merce e Contatti per costruire il tuo giro d'affari.",
      'A fine partita il denaro, le REP, le maggioranze presso i Contact, le Chip nel Covo e le Skill si convertono tutte in punti.',
      'Vince chi totalizza più punti; in caso di parità vince chi ha più REP non macchiate; se la parità persiste, la vittoria è condivisa.',
    ],
    related: ['basics/game-structure', 'jobs/reputation', 'scoring/final-score'],
  },
];
