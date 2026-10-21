import type { RulePage } from '../types';

export const VARIANTS_PAGES: RulePage[] = [
  {
    slug: 'variants/easy-price',
    title: 'Variante Easy Price',
    summary:
      'Prezzi a quattro livelli che non cambiano a ogni acquisto o vendita, ma solo quando un Punto di Vendita si riempie, un Quartiere si svuota o con il Marketing. Il Poker non dà più soldi.',
    keywords: ['easy price', 'variante', 'prezzi', 'marketing', 'stonk', 'poker', 'modalità'],
    cosaServe: ['Scegli "Easy Price" nella schermata iniziale: le altre regole restano quelle del gioco Big.'],
    cosaFai: [
      'Ogni Merce ha quattro prezzi, dal più basso al più alto: Rana 0-1-2-3, Camaleonte 2-3-4-6, Polpo 4-5-7-9, Gufo 6-8-10-13.',
      'Tutte le Merci partono dal prezzo più basso: Rana 0, Camaleonte 2, Polpo 4, Gufo 6.',
    ],
    cosaSuccede: [
      'Acquistare, vendere o requisire non cambia i prezzi.',
      'Quando un Punto di Vendita si riempie, il prezzo della sua Merce va subito al livello più basso.',
      'Quando un Quartiere si svuota (anche per una requisizione), il prezzo della sua Merce va subito al livello più alto.',
      'Il Marketing funziona come nel gioco Big: ogni Stonk sposta di un livello il prezzo di una Merce a scelta, e puoi dividerli tra Merci diverse o sommarli sulla stessa.',
      'Il lancio del Poker non dà più soldi. Il vincitore incassa 2$ per ogni giocatore che ha partecipato (lui compreso): i soldi arrivano dalla banca, gli sconfitti non perdono nulla. In caso di pareggio nessuno incassa e i premi si accumulano: chi vince la partita successiva prende anche 2$ per ogni Chip riportata. Restano le Chip, i Link e le altre ricompense.',
      'Nella Rissa il vincitore ruba sempre una carta a ogni sconfitto: non si sceglie più tra soldi e carta. Le carte con un premio extra restano e si aggiungono: SHAKE DOWN prende anche 4$, TAKE THE POT anche una Chip Poker, SPOILS anche una Merce a scelta. Se lo sconfitto non ha carte in mano non si ruba nulla.',
    ],
    attenzione: [
      'Il prezzo 0 della Rana è un prezzo vero: comprarla non costa nulla.',
      'Il riempimento o lo svuotamento conta solo nel momento in cui avviene: il Marketing può spostare il prezzo subito dopo.',
    ],
    related: ['actions/buy-dope', 'actions/sell-dope', 'events/poker', 'events/brawl'],
  },
];
