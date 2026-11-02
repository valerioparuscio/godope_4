import { defineTexts } from '../define';

// The blocking recap popups: Poker, Raid, Brawl, new Turn, Raid announcement.
export const outcomeTexts = defineTexts({
  'outcome.victory': { it: 'Vittoria', en: 'Victory' },
  'outcome.defeat': { it: 'Sconfitta', en: 'Defeat' },
  'outcome.ok': { it: 'OK', en: 'OK' },
  'outcome.continue': { it: 'Continua', en: 'Continue' },
  'outcome.startPoker': { it: 'Inizia!', en: 'Start!' },
  'outcome.ready': { it: 'Pronti!', en: 'Ready!' },

  // Poker
  'poker.over': { it: 'Poker concluso', en: 'Poker finished' },
  'poker.getsLink': { it: 'Ottiene un Link Preti', en: 'Gets a Reverends Link' },
  'poker.tie': { it: 'Pareggio — jackpot riportato', en: 'Tie — jackpot carried over' },
  'poker.toJail': { it: 'Va in prigione', en: 'Goes to Jail' },
  'poker.cancelled': { it: 'Poker annullato', en: 'Poker cancelled' },
  'poker.nobodyBet': { it: 'Nessuno ha puntato: la partita non si gioca.', en: 'Nobody bet: the match is not played.' },
  'poker.aboutToStart': { it: 'Sta per iniziare una partita a Poker!', en: 'A Poker match is about to start!' },
  'poker.shape.poker': { it: 'Poker', en: 'Four of a Kind' },
  'poker.shape.full': { it: 'Full', en: 'Full House' },
  'poker.shape.tris': { it: 'Tris', en: 'Three of a Kind' },
  'poker.shape.two_pair': { it: 'Doppia Coppia', en: 'Two Pair' },
  'poker.shape.pair': { it: 'Coppia', en: 'Pair' },
  'poker.shape.five_different': { it: '5 Diversi', en: '5 Different' },
  'poker.color.rosa': { it: 'Rosa', en: 'Pink' },
  'poker.color.arancione': { it: 'Arancione', en: 'Orange' },
  'poker.color.verde': { it: 'Verde', en: 'Green' },
  'poker.color.grigio': { it: 'Grigio', en: 'Gray' },
  'poker.color.azzurro': { it: 'Azzurro', en: 'Blue' },

  // Raid recap
  'raidOutcome.title': { it: 'È arrivata la retata {suffix}', en: 'The Raid {suffix} has arrived' },
  'raidOutcome.and': { it: ' e ', en: ' and ' },
  'raidOutcome.escape': { it: 'sfuggono', en: 'escape' },
  'raidOutcome.caught': { it: 'vengono presi', en: 'are caught' },
  'raidOutcome.stains': { it: '{player} macchia {n} REP', en: '{player} stains {n} REP' },
  'raidOutcome.replaced': { it: 'Cambio di programmi: nuova retata', en: 'Change of plans: new Raid' },

  // Raid announcement at the start of the turn
  'raidStart.eyebrow': { it: 'Turno {n} · Allerta in città', en: 'Turn {n} · City on alert' },
  'raidStart.title': { it: 'Retata', en: 'Raid' },
  'raidStart.incoming': { it: 'in arrivo', en: 'incoming' },
  'raidStart.cardAlt': { it: 'Carta Retata {suffix}', en: 'Raid card {suffix}' },
  'raidStart.toEscape': { it: 'Per sfuggire alla Retata', en: 'To escape the Raid' },
  'raidStart.lessDopeValue': { it: 'Meno valore di Merci', en: 'Less Dope value' },
  'raidStart.less': { it: 'Meno', en: 'Less' },
  'raidStart.more': { it: 'Più', en: 'More' },
  'raidStart.getReady': {
    it: 'Prepara la tua gang: questo è l’obiettivo della squadra per il turno.',
    en: 'Get your gang ready: this is the team’s goal for the turn.',
  },

  // Brawl
  'brawl.over': { it: 'Rissa conclusa', en: 'Brawl over' },
  'brawl.loot': { it: 'Bottino', en: 'Loot' },
  'brawl.takesFrom': { it: 'prende da', en: 'takes from' },
  'brawl.lootCard': { it: 'una carta', en: 'a card' },
  'brawl.lootNoCard': { it: 'nessuna carta (mano vuota)', en: 'no card (empty hand)' },
  'brawl.lootChip': { it: 'una Chip Poker', en: 'a Poker Chip' },
  'brawl.lootDope': { it: 'una Merce ({name})', en: 'a Dope ({name})' },

  'turnStart.label': { it: 'Turno', en: 'Turn' },
});
