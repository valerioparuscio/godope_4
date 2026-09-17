import type { RulePage } from '../types';

export const EVENTS_PAGES: RulePage[] = [
  {
    slug: 'events/poker',
    title: 'Poker',
    summary:
      'Una carta Gamble dei Preti lancia una partita a Poker: al massimo una per round, risolta alla fine di quel round.',
    keywords: ['poker', 'gamble', 'preti', 'den', 'gambler', 'chip', 'scommettere', 'puntata'],
    cosaServe: [
      'Un Criminale arrivato al Den, dove diventa un Gambler.',
      "Una carta Gamble (solo i Preti la offrono) da giocare nel round dell'azione a cui è associata.",
    ],
    cosaFai: [
      "Gioca la carta Gamble nel round dell'azione a cui è associata: incassi 3 dollari e mandi un Criminale dal Covo al Den, se c'è posto, pescando una carta.",
      "Alla fine del round, se hai almeno un Gambler nel Den, decidi se puntare posizionando una tua Chip sulla partita.",
      "Se hai puntato, riveli una carta non-Gamble: i suoi 2 simboli si aggiungono ai 3 del banco comune, per una mano da 5.",
    ],
    cosaSuccede: [
      'Si vince nell’ordine: 5 colori diversi > Poker > Full > Tris > Doppia coppia > Coppia.',
      'Il vincitore incassa 2 dollari per ogni Chip puntata, ne banca una nel Covo, ed evolve un Gambler in Link dai Preti.',
      'Ogni sconfitto manda il proprio Gambler in Jail.',
      'In caso di pareggio totale, le Chip restano in gioco e si sommano al piatto della prossima partita lanciata da chiunque.',
    ],
    attenzione: [
      "Si può lanciare UNA sola partita per round, condivisa da tutto il tavolo: se qualcuno l'ha già lanciata, nessun altro può farlo nello stesso round, nemmeno lui stesso.",
      'La partita si risolve SEMPRE alla fine del round in cui è stata lanciata, mai a fine turno.',
      "Chi ha già 3 Chip nel Covo può continuare a puntare prendendole da lì.",
    ],
    esempio:
      "Round 2 del tuo turno: giochi la carta Gamble associata a Comprare Dope, mentre esegui quell'azione. A fine round, tu e un avversario con un Gambler nel Den puntate entrambi. Rivelate le carte: il tuo Full batte la sua Coppia, incassi le Chip e un tuo Gambler diventa Link dai Preti.",
    related: ['actions/buy-dope', 'locations/jail', 'basics/game-structure'],
  },
  {
    slug: 'events/brawl',
    title: 'Rissa',
    summary: 'Quando il quinto Criminale entra in un Quartiere, scoppia la Rissa tra tutti i giocatori presenti.',
    keywords: ['rissa', 'pistole', 'brawl', 'forza', 'combattimento'],
    cosaSuccede: [
      'Partecipa chi ha almeno un Criminale fisicamente nel Quartiere; i Link del Contact si sommano alla forza di chi già partecipa.',
      'A turno, i partecipanti giocano una carta coperta con delle Pistole, poi le rivelano assegnandole a sé o a un altro.',
      'Si somma Criminali + Link + Pistole (può scendere sotto zero): il totale più alto vince, il più basso perde.',
      'Il vincitore ruba 2 dollari o 1 carta a ogni sconfitto, può far evolvere un suo Criminale in Link, e manda via un Criminale di ogni sconfitto.',
      'Dopo la Rissa entra un Cop nel Quartiere.',
    ],
    attenzione: [
      'Piazzare un Criminale non fa mai scattare la Rissa: solo uno spostamento che porta il quinto Criminale può innescarla, quindi un piazzamento che la causerebbe è illegale.',
      'In caso di pareggio tra i possibili sconfitti, perdono tutti; in caso di pareggio tra i possibili vincitori, vince chi ha giocato meno Pistole, poi chi ha innescato la Rissa, poi l’ordine di turno.',
    ],
    related: ['characters/link', 'locations/jail', 'police/cop'],
  },
];
