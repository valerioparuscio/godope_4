import type { RulePage } from '../types';

export const JOBS_PAGES: RulePage[] = [
  {
    slug: 'jobs/job',
    title: 'Job',
    summary:
      'Ogni giocatore possiede tutti e 9 i Job, divisi in 3 mazzetti (uno per tier): completarli guadagna REP e un bonus a scelta.',
    keywords: ['job', 'respect', 'rep', 'skill', 'bonus', 'tier'],
    cosaFai: [
      'Tieni sempre scoperto 1 Job per ciascuno dei tuoi 3 mazzetti (tier 1/2/3).',
      'Quando soddisfi il requisito di un Job scoperto, lo completi: piazzi un segnalino R nella riga di quel Job, in una colonna libera a tua scelta (Skill, Link, 2 carte, o niente).',
      'Scopri subito la prossima carta dello stesso mazzetto.',
    ],
    cosaSuccede: [
      'Il colore del Job indica presso quale Contact incassi il bonus scelto.',
      'Le colonne sono condivise: se un altro giocatore ha già completato lo stesso Job, potrai scegliere solo tra le colonne ancora libere su quella riga.',
    ],
    attenzione: [
      'La maggior parte dei Job guarda il tuo stato ATTUALE, non quanto hai accumulato nel tempo: per esempio i Rat contano solo quelli davvero in Jail ora, i Cop/Fed solo quelli nel tuo Covo ora.',
      'Fa eccezione il Job "Vinci 1 Rissa": conta solo le Risse vinte DOPO che il Job è stato scoperto, non quelle vinte prima.',
    ],
    related: ['jobs/reputation', 'events/brawl', 'characters/link'],
  },
  {
    slug: 'jobs/reputation',
    title: 'REP',
    summary: 'La REP è il segnalino R che guadagni completando un Job: vale 2 punti pulita, 1 punto se macchiata.',
    keywords: ['rep', 'reputazione', 'macchiare', 'stained', 'respect'],
    cosaSuccede: [
      'Ogni Job completato piazza un tuo segnalino R sul tabellone: vale 2 punti a fine partita finché resta pulito.',
      'Una Retata persa macchia REP a testa: 1 alla prima Retata persa in partita, 2 alla seconda, 3 alla terza — girando sul retro altrettanti tuoi segnalini R già piazzati.',
      'Un segnalino macchiato vale solo 1 punto e non può mai tornare pulito.',
    ],
    cosaFai: ['Se hai 2 dollari o meno, puoi macchiarti volontariamente una REP per incassare 5 dollari.'],
    attenzione: [
      'Puoi macchiare (per Retata o volontariamente) solo REP che hai già: se non ne hai abbastanza di pulite, macchi quelle che puoi e basta, nessuna penalità aggiuntiva.',
    ],
    related: ['jobs/job', 'raids/raid', 'scoring/final-score'],
  },
];
