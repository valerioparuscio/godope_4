import type { RulePage } from '../types';

export const CHARACTERS_PAGES: RulePage[] = [
  {
    slug: 'characters/criminal',
    title: 'Criminale',
    summary: 'Il Criminale è la tua pedina base: piazzalo nei Quartieri per comprare, vendere, corrompere e fare Risse.',
    keywords: ['criminale', 'pedina', 'gang'],
    cosaSuccede: [
      'Vendendo Merce o vincendo una Rissa in un Quartiere, un Criminale può evolvere in Link presso il Contact di quel Quartiere.',
      'Spostandosi nel Den, un Criminale diventa un Gambler.',
      'Se arrestato, un Criminale diventa un Rat e finisce in Jail.',
    ],
    attenzione: ['Ogni pedina ha sempre un solo ruolo alla volta: non è mai contemporaneamente Criminale e Link.'],
    related: ['characters/link', 'locations/jail', 'events/brawl'],
  },
  {
    slug: 'characters/link',
    title: 'Link',
    summary:
      'Un Link è una pedina evoluta, agganciata a uno dei 3 livelli di un Contact: conta come presenza in entrambi i Quartieri di quel Contact.',
    keywords: ['link', 'gancio', 'contact', 'evoluzione'],
    cosaServe: [
      'Un Criminale che ha venduto Merce o vinto una Rissa (oppure un Gambler che vince un Poker, o un Rat che causa un’Evasione — evolvono in Link per una via diversa).',
    ],
    cosaSuccede: [
      'Il nuovo Link entra sempre al livello 1: se è occupato, la pedina già presente scorre al livello 2 (e quella al 2 al livello 3); chi esce dal livello 3 torna al Covo del proprio proprietario.',
      'Un Link conta come presenza Criminale in ENTRAMBI i Quartieri del suo Contact, per comprare, vendere, corrompere e per le Risse.',
      'Puoi spendere un Link per un’azione extra (una volta per round) tra quelle del suo Contact: torna subito al Covo nel momento in cui lo scegli.',
    ],
    attenzione: [
      'I 3 livelli di un Contact sono condivisi tra TUTTI i giocatori: non possono mai esistere due Link di due giocatori diversi allo stesso livello dello stesso Contact.',
    ],
    related: ['characters/criminal', 'actions/buy-dope', 'actions/sell-dope'],
  },
];
