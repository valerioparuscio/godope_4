import { defineTexts } from '../define';

// The action log and the bot-turn narration: one short sentence per action, in the language's own grammar.
export const logTexts = defineTexts({
  'log.and': { it: ' e ', en: ' and ' },

  // "a frog" / "3 frogs"
  'log.dope.one.rana': { it: 'una rana', en: 'a frog' },
  'log.dope.many.rana': { it: '{n} rane', en: '{n} frogs' },
  'log.dope.one.camaleonte': { it: 'un camaleonte', en: 'a chameleon' },
  'log.dope.many.camaleonte': { it: '{n} camaleonti', en: '{n} chameleons' },
  'log.dope.one.polpo': { it: 'un polpo', en: 'an octopus' },
  'log.dope.many.polpo': { it: '{n} polpi', en: '{n} octopuses' },
  'log.dope.one.gufo': { it: 'un gufo', en: 'an owl' },
  'log.dope.many.gufo': { it: '{n} gufi', en: '{n} owls' },

  'log.inContactHood': { it: 'in un quartiere {contact}', en: 'in a {contact} Hood' },
  'log.inDifferentHoods': { it: 'in quartieri diversi', en: 'in different Hoods' },
  'log.criminalCount.one': { it: '{count} criminale', en: '{count} Criminal' },
  'log.criminalCount.other': { it: '{count} criminali', en: '{count} Criminals' },
  'log.moveFromTo': { it: 'da un quartiere {from} a uno {to}', en: 'from a {from} Hood to a {to} Hood' },
  'log.officer.one': { it: 'un {label}', en: 'a {label}' },
  'log.officer.many': { it: '{n} {label}', en: '{n} {label}' },

  // What a manipulated officer did
  'log.maneuver.moveHood': { it: 'si sposta in un quartiere {contact}', en: 'moves to a {contact} Hood' },
  'log.maneuver.moveSpot': { it: 'si sposta in uno spot {contact}', en: 'moves to a {contact} Spot' },
  'log.maneuver.move': { it: 'si sposta', en: 'moves' },
  'log.maneuver.arrest': { it: 'arresta', en: 'arrests' },
  'log.maneuver.arrestOne': { it: 'arresta una pedina di {owners}', en: 'arrests a pawn of {owners}' },
  'log.maneuver.arrestMany': { it: 'arresta {n} pedine di {owners}', en: 'arrests {n} pawns of {owners}' },
  'log.maneuver.confiscateDope': { it: 'requisisce {dope}', en: 'confiscates {dope}' },
  'log.maneuver.confiscate': { it: 'requisisce', en: 'confiscates' },

  'log.extra.boost': { it: "gioca una carta per potenziare l'azione", en: 'plays a card to boost the action' },
  'log.extra.marketing': { it: 'gioca Marketing da {n}', en: 'plays Marketing for {n}' },

  'log.power.grit': { it: 'Grinta {n}', en: 'Grit {n}' },
  'log.power.link': { it: 'un Gancio di livello {level} con {contact}', en: 'a level {level} Link with {contact}' },
  // Italian puts an article before the Contact's name
  'log.contactWith.artisti': { it: 'gli Artisti', en: 'the Bohemians' },
  'log.contactWith.studenti': { it: 'gli Studenti', en: 'the Bookheads' },
  'log.contactWith.manager': { it: 'i Manager', en: 'the Briefcases' },
  'log.contactWith.preti': { it: 'i Preti', en: 'the Reverends' },
  'log.contactWith.politici': { it: 'i Politici', en: 'the Politicians' },

  'log.verb.place': { it: 'piazza', en: 'places' },
  'log.verb.move': { it: 'sposta', en: 'moves' },
  'log.verb.buy': { it: 'compra', en: 'buys' },
  'log.verb.sell': { it: 'vende', en: 'sells' },
  'log.verb.maneuver': { it: 'manovra', en: 'manipulates' },
  'log.verb.corrupt_officer': { it: 'corrompe', en: 'bribes' },
  'log.verbInf.place': { it: 'piazzare', en: 'place' },
  'log.verbInf.move': { it: 'spostare', en: 'move' },
  'log.verbInf.buy': { it: 'acquistare', en: 'buy' },
  'log.verbInf.sell': { it: 'vendere', en: 'sell' },
  'log.verbInf.maneuver': { it: 'manovrare', en: 'manipulate' },
  'log.verbInf.corrupt_officer': { it: 'corrompere', en: 'bribe' },
  'log.usesFor': { it: 'usa {power} per {verb} {object}', en: 'uses {power} to {verb} {object}' },
  'log.usesLinkExtra': { it: "usa {power} per un'azione extra", en: 'uses {power} for an extra action' },
  'log.pass': { it: 'passa', en: 'passes' },
  'turn.usesLink': { it: 'usa un gancio', en: 'uses a Link' },
  'turn.launchesPoker': { it: 'lancia un poker', en: 'launches a Poker' },
  'turn.doesMarketing': { it: 'fa marketing', en: 'does Marketing' },
  'log.launchPoker': { it: 'lancia un Poker', en: 'launches a Poker' },

  // Banner texts and image descriptions
  'log.banner.destination': { it: 'destinazione', en: 'destination' },
  'log.banner.arrestedPawn': { it: 'pedina arrestata', en: 'arrested pawn' },
  'log.banner.linkUsed': { it: 'Gancio usato', en: 'Link used' },
  'log.banner.launchPoker': { it: 'Lancia un Poker', en: 'Launches a Poker' },
  'log.banner.pass': { it: 'Passa', en: 'Passes' },

  // Results found in a batch of events
  'log.brawl.win': { it: 'Rissa in un Quartiere: vince {winner}', en: 'Brawl in a Hood: {winner} wins' },
  'log.brawl.losers': { it: ', sconfitto {losers}', en: ', {losers} defeated' },
  'log.brawl.noWinner': { it: 'Rissa in un Quartiere: nessun vincitore', en: 'Brawl in a Hood: no winner' },
  'log.poker.win': { it: 'Poker: vince {winner} ({shape})', en: 'Poker: {winner} wins ({shape})' },
  'log.poker.tie': { it: 'Poker: pareggio tra {players}, jackpot riportato', en: 'Poker: tie between {players}, jackpot carried over' },
  'log.raid': { it: 'Retata ({criterion}): scappano {escaping} — catturati {caught}', en: 'Raid ({criterion}): {escaping} escape — {caught} caught' },
});
