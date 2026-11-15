import { defineTexts } from '../define';

// Side panels, drawers, the Raid banner, the final score and the leaderboard.
export const screenTexts = defineTexts({
  'player.pawnsInBase': { it: 'Pedine nel Covo', en: 'Pawns in Base' },
  'player.pawnsInBaseCount': { it: '{n} pedine nel Covo', en: '{n} pawns in Base' },
  'player.bribeFromBase': { it: 'Corrompi questo agente dal Covo', en: 'Bribe this officer from their Base' },

  'hand.empty': { it: 'Nessuna carta.', en: 'No cards.' },
  'skills.empty': { it: 'Nessuna Skill.', en: 'No Skills.' },
  'logDrawer.empty': { it: 'Nessuna azione ancora.', en: 'No actions yet.' },

  'finished.title': { it: 'Partita finita', en: 'Game over' },
  'finished.winnersIntro': { it: 'And the winner is..', en: 'And the winner is..' },
  'finished.seeScores': { it: 'Vedi i punteggi', en: 'See the scores' },
  'finished.winners': { it: 'Vincitore/i:', en: 'Winner(s):' },
  'finished.noWinner': { it: 'nessuno', en: 'none' },
  'finished.noScore': { it: 'Punteggio non disponibile.', en: 'Score not available.' },
  'finished.newGame': { it: 'Nuova partita', en: 'New game' },
  'finished.col.player': { it: 'Giocatore', en: 'Player' },
  'finished.col.money': { it: 'Denaro', en: 'Money' },
  'finished.col.cleanRep': { it: 'REP pulite', en: 'Clean REP' },
  'finished.col.stainedRep': { it: 'REP macchiate', en: 'Stained REP' },
  'finished.col.majorities': { it: 'Maggioranze', en: 'Majorities' },
  'finished.col.chips': { it: 'Chips', en: 'Chips' },
  'finished.col.skills': { it: 'Skill', en: 'Skills' },
  'finished.col.total': { it: 'Totale', en: 'Total' },

  'leaderboard.unavailable': { it: 'Classifica non disponibile.', en: 'Leaderboard not available.' },
  'leaderboard.loading': { it: 'Caricamento...', en: 'Loading...' },
  'leaderboard.empty': { it: 'Nessun punteggio ancora registrato.', en: 'No scores recorded yet.' },

  // Raid banner (top-left panel)
  'raidBanner.label': { it: 'Retata e punteggi parziali', en: 'Raid and partial scores' },
  'raidBanner.heading': { it: 'Retata', en: 'Raid' },
  'raidBanner.none': { it: 'Nessuna Retata rivelata.', en: 'No Raid revealed.' },
  'raidBanner.provisionalTeams': { it: 'Squadre provvisorie', en: 'Provisional teams' },
  'raidBanner.dopeUnit': { it: '$ merci', en: '$ Dope' },

  'raid.title.most_links_with_contacts': { it: 'Retata dei Palazzi', en: 'Establishment Raid' },
  'raid.title.least_criminals_in_jail': { it: 'Retata dalla Prigione', en: 'Prison Raid' },
  'raid.title.least_dope_value': { it: 'Retata nei Covi', en: 'Stash Raid' },
  'raid.title.most_poker_wins': { it: 'Retata dell’Azzardo', en: 'Gambling Raid' },
  'raid.title.most_cops_bought': { it: 'Retata dei Corrotti', en: 'Corruption Raid' },
  'raid.title.least_money': { it: 'Retata Finanziaria', en: 'Financial Raid' },
  'raid.title.least_criminals_in_hoods': { it: 'Retata in Strada', en: 'Street Raid' },

  // What escaping needs, as the one big word printed on each Raid banner (the sign and the word are
  // highlighted and the line is fitted to the width of the box); the same in both languages.
  'raid.need.most_links_with_contacts': { it: '+ LINKS', en: '+ LINKS' },
  'raid.need.least_criminals_in_jail': { it: '- RATS', en: '- RATS' },
  'raid.need.least_dope_value': { it: '- DOPE', en: '- DOPE' },
  'raid.need.most_poker_wins': { it: '+ POKER', en: '+ POKER' },
  'raid.need.most_cops_bought': { it: '+ COPS', en: '+ COPS' },
  'raid.need.least_money': { it: '- CASH', en: '- CASH' },
  'raid.need.least_criminals_in_hoods': { it: '- CRIMES', en: '- CRIMES' },

  // What each criterion counts (Raid recap and log)
  'raid.criterion.most_links_with_contacts': { it: 'Ganci', en: 'Links' },
  'raid.criterion.least_criminals_in_jail': { it: 'Rats', en: 'Rats' },
  'raid.criterion.least_dope_value': { it: 'Valore Merci (minore)', en: 'Dope value (lower)' },
  'raid.criterion.most_poker_wins': { it: 'Chip Poker nel Covo', en: 'Poker Chips in Base' },
  'raid.criterion.most_cops_bought': { it: 'Cops/Feds posseduti', en: 'Cops/Feds owned' },
  'raid.criterion.least_money': { it: 'Denaro', en: 'Money' },
  'raid.criterion.least_criminals_in_hoods': { it: 'Criminali nei Quartieri', en: 'Criminals in Hoods' },

  // Compact unit next to each team's count
  'raid.unit.most_poker_wins': { it: 'chip', en: 'chips' },
  'raid.unit.most_cops_bought': { it: 'cops', en: 'cops' },
  'raid.unit.least_dope_value': { it: 'dope', en: 'dope' },
  'raid.unit.least_money': { it: 'cash', en: 'cash' },
  'raid.unit.most_links_with_contacts': { it: 'links', en: 'links' },
  'raid.unit.least_criminals_in_jail': { it: 'rat', en: 'rats' },
  'raid.unit.least_criminals_in_hoods': { it: 'crime', en: 'crimes' },

  // Themed suffix of the Raid recap title ("A Raid ... has arrived")
  'raid.suffix.most_poker_wins': { it: "dell'AZZARDO", en: 'on GAMBLING' },
  'raid.suffix.most_cops_bought': { it: 'dei CORROTTI', en: 'on the CORRUPT' },
  'raid.suffix.least_dope_value': { it: 'nei COVI', en: 'on STASHES' },
  'raid.suffix.least_money': { it: 'FINANZIARIA', en: 'on FINANCES' },
  'raid.suffix.most_links_with_contacts': { it: 'nei PALAZZI', en: 'on the ESTABLISHMENT' },
  'raid.suffix.least_criminals_in_jail': { it: 'dalla PRIGIONE', en: 'on the PRISON' },
  'raid.suffix.least_criminals_in_hoods': { it: 'in STRADA', en: 'on the STREETS' },
});
