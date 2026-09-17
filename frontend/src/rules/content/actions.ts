import type { RulePage } from '../types';

export const ACTIONS_PAGES: RulePage[] = [
  {
    slug: 'actions/buy-dope',
    title: 'Comprare Dope',
    summary: 'Un Criminale o un Link compra Merce nel proprio Quartiere, pagandone il prezzo corrente.',
    keywords: ['comprare', 'acquisto', 'dope', 'merce', 'mercato', 'prezzo', 'stonk'],
    cosaServe: [
      'Un Criminale o un Link nel Quartiere, con almeno una Merce disponibile e nessun Cop presente.',
      'Denaro sufficiente a coprire il prezzo.',
    ],
    cosaFai: [
      'Scegli il Criminale (o il Link, in uno dei due Quartieri del suo Contact) che farà l’acquisto.',
      'Se vuoi, prima di comprare gioca una carta con Stonk per modificare di 1 il prezzo di una Merce a tua scelta.',
      'Paga il prezzo corrente della Merce: passa dal Quartiere al tuo Covo.',
    ],
    cosaSuccede: [
      "Il prezzo di quella Merce sale di 1 dopo l'acquisto.",
      "Se il Quartiere resta senza quella Merce, si ricarica (fino a 3, o quel che resta nella banca condivisa) ed entra un Cop.",
      "Comprando più Merci nello stesso Quartiere nello stesso round, l'aumento dei prezzi si applica tutto insieme, alla fine del pacchetto.",
    ],
    attenzione: [
      'Un Cop presente nel Quartiere blocca l’acquisto.',
      "Con un Link, se ha scorta legale in entrambi i Quartieri del suo Contact, scegli tu da quale comprare — a differenza della vendita, qui il Quartiere conta.",
    ],
    related: ['actions/sell-dope', 'characters/link', 'police/cop'],
  },
];
