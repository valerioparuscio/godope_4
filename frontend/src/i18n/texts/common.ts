import { defineTexts } from '../define';

// Words used all over the interface. The English terms follow the English card, skill and Raid art
// (game designer, 2026-11-03): Hood, Base (the Covo), Dope (the Merci), Grit, Link, Raid, Brawl, Den,
// Jail, Rat, Gambler, Cop/Fed; the five Contacts take the names printed on the board.
export const commonTexts = defineTexts({
  // Player colours (the seat's colour names the player in the narration)
  'color.red': { it: 'Rosso', en: 'Red' },
  'color.blu': { it: 'Blu', en: 'Blue' },
  'color.green': { it: 'Verde', en: 'Green' },
  'color.yellow': { it: 'Giallo', en: 'Yellow' },

  // Dope
  'dope.rana': { it: 'Rana', en: 'Frog' },
  'dope.camaleonte': { it: 'Camaleonte', en: 'Chameleon' },
  'dope.polpo': { it: 'Polpo', en: 'Octopus' },
  'dope.gufo': { it: 'Gufo', en: 'Owl' },

  // Contacts (the Clienti)
  'contact.artisti': { it: 'Artisti', en: 'Bohemians' },
  'contact.studenti': { it: 'Studenti', en: 'Bookheads' },
  'contact.manager': { it: 'Manager', en: 'Briefcases' },
  'contact.preti': { it: 'Preti', en: 'Reverends' },
  'contact.politici': { it: 'Politici', en: 'Politicians' },

  // The six actions
  'action.place_criminal': { it: 'Piazza', en: 'Place' },
  'action.move_criminal': { it: 'Sposta', en: 'Move' },
  'action.buy_dope': { it: 'Acquista', en: 'Buy' },
  'action.sell_dope': { it: 'Vendi', en: 'Sell' },
  'action.maneuver_officer': { it: 'Manovra', en: 'Manipulate' },
  'action.corrupt_officer': { it: 'Corrompi', en: 'Bribe' },

  // Section titles of the action chooser
  'chooser.grit': { it: 'GRINTA', en: 'GRIT' },
  'chooser.link': { it: 'GANCIO', en: 'LINK' },
  'chooser.actions': { it: 'AZIONI', en: 'ACTIONS' },
  'chooser.gritN': { it: 'Grinta {n}', en: 'Grit {n}' },

  'common.pass': { it: 'Passa', en: 'Pass' },
  'common.close': { it: 'Chiudi', en: 'Close' },
  'common.cards': { it: 'Carte', en: 'Cards' },
  'common.skills': { it: 'Skill', en: 'Skills' },
  'common.log': { it: 'Log', en: 'Log' },
  'common.cops': { it: 'Cops', en: 'Cops' },
  'common.pokerChips': { it: 'Chip poker', en: 'Poker Chips' },
});
