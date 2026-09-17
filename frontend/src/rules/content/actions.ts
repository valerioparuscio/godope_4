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
  {
    slug: 'actions/sell-dope',
    title: 'Vendere Dope',
    summary:
      'Un Criminale o un Link vende Merce dal Covo al Punto di Vendita del proprio Contact, incassandone il prezzo.',
    keywords: ['vendere', 'vendita', 'dope', 'merce', 'spot', 'punto di vendita', 'prezzo', 'stonk'],
    cosaServe: [
      'Un Criminale o un Link nel Quartiere, con il relativo Punto di Vendita non occupato da Fed.',
      'La Merce da vendere già presente nel tuo Covo.',
    ],
    cosaFai: [
      'Scegli il Criminale (o il Link) che venderà.',
      'Se vuoi, prima della vendita gioca una carta con Stonk per modificare di 1 il prezzo di una Merce a tua scelta.',
      'Incassi il prezzo corrente: la Merce passa dal Covo al Punto di Vendita.',
    ],
    cosaSuccede: [
      'Il prezzo di quella Merce scende di 1 dopo la vendita.',
      'Vendendo una sola unità, puoi scegliere se far evolvere il Criminale che ha venduto in Link.',
      'Vendendo più unità nello stesso pacchetto, prendi automaticamente un Link del livello pari al numero di Merci vendute.',
      'Se il Punto di Vendita si riempie (3 Merci), viene svuotato ed entra un Fed.',
    ],
    attenzione: [
      'Un Fed presente nel Punto di Vendita blocca la vendita.',
      'Con un Link non serve scegliere il Quartiere: i due Quartieri dello stesso Contact condividono sempre lo stesso Punto di Vendita.',
    ],
    related: ['actions/buy-dope', 'characters/link', 'police/fed'],
  },
];
