import type { RulePage } from '../types';

export const LOCATIONS_PAGES: RulePage[] = [
  {
    slug: 'locations/jail',
    title: 'Jail',
    summary: "La Jail ha 4 posti. Quando si occupa il quarto, scatta subito l'Evasione.",
    keywords: ['jail', 'prigione', 'commissariato', 'rat', 'arresto', 'slot', 'evasione'],
    cosaSuccede: [
      'Un Criminale o un Link arrestato diventa un Rat e occupa il primo slot libero della Jail (da 1 a 4).',
      'Se sullo stesso arresto viene anche confiscata una Merce, resta associata a quel Rat, nel suo slot.',
      'I Rat possono corrompere Cops in qualunque Quartiere, non solo restando in Jail.',
    ],
    attenzione: [
      'La Jail NON ha 6 posti: sono sempre e solo 4 slot.',
      "Quando il quarto slot si riempie, l'Evasione scatta immediatamente — anche nel mezzo della risoluzione di un'altra meccanica, come una Rissa o un Poker.",
    ],
    related: ['locations/jail-evasion', 'characters/criminal', 'police/cop'],
  },
  {
    slug: 'locations/jail-evasion',
    title: 'Evasione',
    summary:
      "Quando il quarto Rat entra in Jail, tutti i Rat evadono e tornano ai propri Covi con la Merce che avevano addosso.",
    keywords: ['evasione', 'jail', 'rat', 'link', 'politici', 'fuga'],
    cosaSuccede: [
      'I 4 Rat lasciano la Jail: 3 tornano al Covo del proprio proprietario come pedine libere, portando con sé l’eventuale Merce confiscata nel loro slot.',
      "Il quarto Rat — quello che ha causato l'Evasione riempiendo l'ultimo slot — non torna come pedina libera: evolve direttamente in Link dai Politici.",
      'La Jail resta vuota, pronta per i prossimi arresti.',
    ],
    attenzione: [
      "L'Evasione può scattare per un arresto dovuto a qualunque causa — non solo una corruzione, anche per esempio un Gambler sconfitto al Poker.",
    ],
    related: ['locations/jail', 'characters/link', 'events/poker'],
  },
];
