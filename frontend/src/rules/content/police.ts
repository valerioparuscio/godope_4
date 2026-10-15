import type { RulePage } from '../types';

export const POLICE_PAGES: RulePage[] = [
  {
    slug: 'police/cop',
    title: 'Cop',
    summary: 'Il Cop pattuglia un Quartiere: blocca gli acquisti finché non viene manovrato o rimandato in riserva.',
    keywords: ['cop', 'poliziotto', 'manovrare', 'manovra', 'corrompere', 'arresto'],
    cosaSuccede: [
      'Un Cop entra in gioco in un Quartiere quando scoppia una Rissa lì, o quando il mercato si svuota e si ricarica.',
      'Finché è presente, nessuno può comprare Merce in quel Quartiere.',
      'Un Cop senza Merce e senza Criminali nel Quartiere torna in riserva (non occupa uno slot della Jail).',
    ],
    cosaFai: [
      'Un Criminale, Link o Rat può manovrarlo pagando 1 dollaro per azione: spostarlo in un Quartiere adiacente, fargli arrestare un Criminale a scelta, o fargli requisire una Merce (il prezzo sale di 1).',
      'Puoi fargli compiere da 1 a 3 azioni diverse (mai la stessa due volte), fermandoti quando vuoi.',
    ],
    attenzione: [
      'Un Rat può manovrare Cops in qualunque Quartiere, non solo restando fermo in Jail.',
      'Puoi anche corrompere un Cop per 7 dollari, dal Quartiere o dal Covo di un altro giocatore, e portarlo nel tuo Covo.',
    ],
    related: ['police/fed', 'actions/buy-dope', 'locations/jail'],
  },
  {
    slug: 'police/fed',
    title: 'Fed',
    summary: 'Il Fed indaga in un Punto di Vendita: blocca le vendite finché non viene manovrato o rimandato in riserva.',
    keywords: ['fed', 'detective', 'manovrare', 'manovra', 'corrompere', 'arresto', 'spot'],
    cosaSuccede: [
      'Un Fed entra in gioco in un Punto di Vendita quando questo si riempie o si svuota di Merci.',
      'Finché è presente, nessuno può vendere in quel Punto di Vendita.',
      'Un Fed in un Punto di Vendita senza Merci e senza nessun Link di quel Contact torna in riserva.',
    ],
    cosaFai: [
      'Un Criminale, Link o Rat può manovrarlo pagando 1 dollaro per azione: spostarlo in un Punto di Vendita adiacente, fargli arrestare il Link di livello più basso del Contact, o fargli requisire una Merce (il prezzo sale di 1).',
      'Puoi fargli compiere da 1 a 3 azioni diverse (mai la stessa due volte), fermandoti quando vuoi.',
    ],
    attenzione: ['Puoi anche corrompere un Fed per 7 dollari, dal Punto di Vendita o dal Covo di un altro giocatore.'],
    related: ['police/cop', 'actions/sell-dope', 'characters/link'],
  },
];
