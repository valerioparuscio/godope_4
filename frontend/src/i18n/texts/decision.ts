import { defineTexts } from '../define';

// The decision panel: questions, hints and buttons for every kind of choice the game asks.
export const decisionTexts = defineTexts({
  'common.back': { it: 'Indietro', en: 'Back' },
  'common.skip': { it: 'Salta', en: 'Skip' },
  'common.confirm': { it: 'Conferma', en: 'Confirm' },
  'common.noThanks': { it: 'No, grazie', en: 'No, thanks' },
  'common.no': { it: 'No', en: 'No' },
  'common.done': { it: 'Fine', en: 'Done' },
  'common.card': { it: 'Carta', en: 'Card' },

  'decision.verb.grit': { it: 'GRINTA', en: 'GRIT' },
  'decision.verb.action': { it: 'AZIONE', en: 'ACTION' },

  // Brawl rewards
  'decision.brawlReward.money': { it: 'Soldi', en: 'Money' },
  'decision.brawlReward.card': { it: 'Carta', en: 'Card' },
  'decision.brawlReward.dope': { it: 'Merce', en: 'Dope' },
  'decision.brawlReward.poker_chip': { it: 'Chip Poker', en: 'Poker Chip' },
  'decision.brawl.aLoser': { it: 'uno sconfitto', en: 'a loser' },
  'decision.brawl.alsoDope': { it: 'Oltre alla carta, quale Merce vuoi da {loser}?', en: 'Besides the card, which Dope do you want from {loser}?' },
  'decision.brawl.whichDope': { it: 'Quale Merce vuoi da {loser}?', en: 'Which Dope do you want from {loser}?' },
  'decision.brawl.whichReward': { it: 'Che ricompensa vuoi da {loser}?', en: 'What reward do you want from {loser}?' },

  // Manipulating Cops and Feds
  'decision.maneuver.question': { it: "Che azione fa l'ufficiale manovrato?", en: 'What does the manipulated officer do?' },
  'decision.maneuver.move': { it: 'Sposta', en: 'Move' },
  'decision.maneuver.arrest': { it: 'Arresta', en: 'Arrest' },
  'decision.maneuver.confiscate': { it: 'Requisisci', en: 'Confiscate' },
  'decision.maneuver.arrestAndFree': {
    it: 'Arresta un Criminale di {a} e libera un Rat di {b}',
    en: 'Arrest a Criminal of {a} and free a Rat of {b}',
  },
  'decision.maneuver.freeRat': { it: 'Libera un Rat di {a} nel Quartiere', en: 'Free a Rat of {a} in the Hood' },
  'decision.maneuver.pickTarget': { it: 'Scegli il bersaglio sul tabellone.', en: 'Pick the target on the board.' },

  // Links
  'decision.link.pick': { it: 'Scegli un gancio da usare', en: 'Pick a Link to use' },
  'decision.link.question': { it: "Vuoi spendere un Gancio per un'azione extra?", en: 'Spend a Link for an extra action?' },
  'decision.link.hint': { it: 'Clicca un Gancio illuminato sul tabellone, oppure salta.', en: 'Click a lit-up Link on the board, or skip.' },
  'decision.brawlLink.question': { it: 'Vuoi far evolvere un Criminale in Link?', en: 'Evolve a Criminal into a Link?' },
  'decision.brawlLink.hint': { it: 'Clicca una pedina illuminata sul tabellone, oppure passa.', en: 'Click a lit-up pawn on the board, or pass.' },
  'decision.evolve.question': { it: 'Vuoi evolvere in Link?', en: 'Evolve into a Link?' },
  'decision.evolve.yes': { it: 'Evolvi in Link', en: 'Evolve into a Link' },
  'decision.evolve.contact': { it: 'Link {contact}', en: '{contact} Link' },

  'decision.relocation.question': { it: 'Dove va il Criminale sconfitto?', en: 'Where does the defeated Criminal go?' },
  'decision.relocation.hint': { it: 'Clicca un Quartiere non ancora rivelato sul tabellone.', en: 'Click a Hood that is not revealed yet on the board.' },

  // Jobs
  'decision.job.reward': { it: 'Scegli il premio del Job', en: 'Pick the Job reward' },
  'decision.job.rewardHint': { it: 'Clicca una colonna libera illuminata sul tabellone.', en: 'Click a lit-up free column on the board.' },
  'decision.job.discardSkill': { it: 'Hai già 3 Skill: quale scarti per prendere quella nuova?', en: 'You already have 3 Skills: which one do you discard to take the new one?' },
  'decision.job.bonusInstead': { it: 'Al posto del Gancio, scegli il bonus:', en: 'Instead of the Link, pick the bonus:' },
  'decision.job.bonusMoney': { it: '3$', en: '$3' },
  'decision.job.bonusCards': { it: '2 Carte', en: '2 Cards' },

  // Card follow-ups after a move, a placement or a Brawl
  'decision.followup.title.badge_hunt': { it: 'Carta: sposti un Cop di questo Quartiere? (1$)', en: 'Card: move a Cop out of this Hood? (1$)' },
  'decision.followup.title.den_swap': { it: 'Carta: scambi posto con un Gambler avversario?', en: 'Card: swap places with an enemy Gambler?' },
  'decision.followup.title.aftershock': { it: 'Carta: vuoi corrompere il Cop appena arrivato? (7$)', en: 'Card: bribe the Cop that just arrived? (7$)' },
  'decision.followup.title.follow_me': { it: 'Carta: vuoi piazzare qui 1 Criminale gratis?', en: 'Card: place 1 Criminal here for free?' },
  'decision.followup.title.badge_hire': { it: 'Carta: vuoi corrompere un Cop dove hai piazzato? (7$)', en: 'Card: bribe a Cop where you placed? (7$)' },
  'decision.followup.title.expansion': { it: 'Carta: vuoi spostare 1 Criminale appena piazzato? (gratis)', en: 'Card: move 1 Criminal you just placed? (free)' },
  'decision.followup.title.decoy': { it: 'Carta: fai entrare 1 Cop in un Quartiere dove hai piazzato', en: 'Card: bring 1 Cop into a Hood where you placed' },
  'decision.followup.title.full_control': { it: 'Carta: vuoi corrompere gratis uno degli ufficiali manovrati?', en: 'Card: bribe one of the manipulated officers for free?' },
  'decision.followup.title.escort': { it: 'Carta: vuoi spostare 1 Criminale insieme al Cop? (gratis)', en: 'Card: move 1 Criminal along with the Cop? (free)' },
  'decision.followup.title.backroom': { it: 'Carta: il Criminale va nel Den (peschi una carta a caso)', en: 'Card: the Criminal goes to the Den (you draw a random card)' },
  'decision.followup.title.vacancy': { it: 'Carta: vuoi spostare gratis un tuo Criminale nel Quartiere del Cop corrotto?', en: 'Card: move one of your Criminals to the bribed Cop’s Hood for free?' },
  'decision.followup.title.fixer': { it: 'Carta: vuoi far salire di un livello il tuo Link?', en: 'Card: raise your Link one level?' },
  'decision.followup.title.connection': { it: 'Carta: vuoi far diventare Link il Criminale che ha corrotto?', en: 'Card: turn the Criminal who bribed into a Link?' },
  'decision.followup.title.last_job': { it: 'Carta: vuoi arrestare un Criminale del Quartiere del Cop?', en: 'Card: arrest a Criminal in the Cop’s Hood?' },
  'decision.followup.title.cover': { it: 'Carta: vuoi piazzare qui 1 Criminale? (2$)', en: 'Card: place 1 Criminal here? (2$)' },

  'decision.followup.hint.badge_hunt': { it: 'Clicca il Quartiere illuminato dove spostare il Cop.', en: 'Click the lit-up Hood to move the Cop to.' },
  'decision.followup.hint.den_swap': { it: 'Clicca il Gambler illuminato con cui scambiare posto.', en: 'Click the lit-up Gambler to swap places with.' },
  'decision.followup.hint.follow_me': { it: 'Clicca il Quartiere illuminato per piazzarci 1 Criminale.', en: 'Click the lit-up Hood to place 1 Criminal there.' },
  'decision.followup.hint.badge_hire': { it: 'Clicca il Cop illuminato da corrompere.', en: 'Click the lit-up Cop to bribe.' },
  'decision.followup.hint.expansion': { it: 'Clicca il Quartiere illuminato dove spostarlo.', en: 'Click the lit-up Hood to move it to.' },
  'decision.followup.hint.decoy': { it: 'Clicca il Quartiere illuminato dove far entrare il Cop.', en: 'Click the lit-up Hood to bring the Cop into.' },
  'decision.followup.hint.full_control': { it: "Clicca l'ufficiale illuminato da corrompere.", en: 'Click the lit-up officer to bribe.' },
  'decision.followup.hint.escort': { it: 'Clicca il Criminale illuminato da spostare insieme al Cop.', en: 'Click the lit-up Criminal to move along with the Cop.' },
  'decision.followup.hint.vacancy': { it: 'Clicca il Criminale illuminato da spostare nel Quartiere del Cop.', en: 'Click the lit-up Criminal to move to the Cop’s Hood.' },
  'decision.followup.hint.last_job': { it: 'Clicca il Criminale illuminato da arrestare.', en: 'Click the lit-up Criminal to arrest.' },
  'decision.followup.hint.cover': { it: 'Clicca il Quartiere illuminato per piazzarci 1 Criminale.', en: 'Click the lit-up Hood to place 1 Criminal there.' },
  'decision.followup.expansionPawn': { it: 'Clicca il Criminale illuminato da spostare, poi il Quartiere di destinazione.', en: 'Click the lit-up Criminal to move, then the destination Hood.' },

  'decision.followup.button.aftershock': { it: 'Corrompi il Cop', en: 'Bribe the Cop' },
  'decision.followup.button.fixer': { it: 'Sali di livello', en: 'Level up' },
  'decision.followup.button.connection': { it: 'Diventa Link', en: 'Become a Link' },
  'decision.followup.button.backroom': { it: 'Vai nel Den', en: 'Go to the Den' },

  // A Buy/Sell card's follow-up, asked as an ordinary Place/Move decision
  'decision.cardFollowup.title.place': { it: 'Carta: piazza 1 Criminale', en: 'Card: place 1 Criminal' },
  'decision.cardFollowup.hint.place': { it: 'Clicca un Quartiere illuminato, tra quelli dove hai acquistato o venduto.', en: 'Click a lit-up Hood, among those where you bought or sold.' },
  'decision.cardFollowup.title.den': { it: 'Carta: manda 1 Criminale nel Den', en: 'Card: send 1 Criminal to the Den' },
  'decision.cardFollowup.hint.den': { it: 'Clicca il Criminale illuminato che vuoi mandare nel Den, poi il Den.', en: 'Click the lit-up Criminal you want to send to the Den, then the Den.' },
  'decision.cardFollowup.title.move': { it: 'Carta: sposta 1 Criminale', en: 'Card: move 1 Criminal' },
  'decision.cardFollowup.hint.move': { it: 'Clicca un Criminale illuminato, poi la sua destinazione.', en: 'Click a lit-up Criminal, then its destination.' },
  'decision.cardFollowup.title.buy': { it: 'Carta: 1 Criminale appena piazzato può acquistare', en: 'Card: 1 Criminal just placed may buy' },
  'decision.cardFollowup.hint.buy': { it: 'Clicca il Criminale illuminato che compra, oppure passa.', en: 'Click the lit-up Criminal that buys, or pass.' },

  // The actions answered on the board
  'decision.package.play_marketing_card': { it: 'Gioca Marketing', en: 'Play Marketing' },
  'decision.packageHint.place_criminal': { it: 'Clicca un Quartiere illuminato sul tabellone.', en: 'Click a lit-up Hood on the board.' },
  'decision.packageHint.move_criminal': { it: 'Clicca un Criminale illuminato, poi la sua destinazione.', en: 'Click a lit-up Criminal, then its destination.' },
  'decision.packageHint.buy_dope': { it: 'Clicca una pedina illuminata sul tabellone per comprare.', en: 'Click a lit-up pawn on the board to buy.' },
  'decision.packageHint.sell_dope': { it: 'Clicca una pedina illuminata sul tabellone per vendere.', en: 'Click a lit-up pawn on the board to sell.' },
  'decision.packageHint.maneuver_officer': { it: 'Clicca un Cop/Fed illuminato sul tabellone.', en: 'Click a lit-up Cop/Fed on the board.' },
  'decision.packageHint.corrupt_officer': { it: 'Clicca un Cop/Fed illuminato sul tabellone.', en: 'Click a lit-up Cop/Fed on the board.' },
  'decision.packageHint.play_marketing_card': { it: 'Usa + e − accanto ai prezzi: ogni clic usa uno Stonk.', en: 'Use + and − next to the prices: each click uses one Stonk.' },
  'decision.marketingStrict': {
    it: 'Usa + e − accanto ai prezzi: ogni Stonk sposta di un livello una Merce diversa. Usali tutti ({n}).',
    en: 'Use + and − next to the prices: each Stonk moves a different Dope one level. Use them all ({n}).',
  },
  'decision.unavailable.moved': { it: '✓ già spostato in questa azione', en: '✓ already moved in this action' },
  'decision.unavailable.noDestination': { it: '✕ nessuna destinazione libera', en: '✕ no free destination' },

  // Raid, REP, hand
  'decision.raidFirst': { it: 'Chi parte per primo nella Retata?', en: 'Who goes first in the Raid?' },
  'decision.stain.question': { it: 'Vuoi macchiare una REP per $5?', en: 'Stain a REP for $5?' },
  'decision.stain.yes': { it: 'Sì, macchia', en: 'Yes, stain' },
  'decision.discard.title': { it: 'Scarta {n} carte dalla mano', en: 'Discard {n} cards from your hand' },
  'decision.discard.hint': { it: 'Clicca le carte da scartare nella mano in basso a destra ({selected}/{n}).', en: 'Click the cards to discard in the hand at the bottom right ({selected}/{n}).' },

  // Poker
  'decision.pokerBet.question': { it: 'Partecipi alla partita a poker?', en: 'Join the Poker match?' },
  'decision.pokerBet.join': { it: 'Partecipa', en: 'Join' },
  'decision.brawlCard.question': { it: 'Vuoi giocare una carta nella Rissa?', en: 'Play a card in the Brawl?' },
  'decision.brawlCard.hint': { it: 'Clicca una carta nella mano in basso a destra, oppure passa.', en: 'Click a card in the hand at the bottom right, or pass.' },
  'decision.launchPoker.question': { it: 'Vuoi lanciare un Poker?', en: 'Launch a Poker?' },
  'decision.launchPoker.dialog': { it: 'Lancia un Poker', en: 'Launch a Poker' },
  'decision.launchPoker.title': { it: 'Partita a poker?', en: 'Poker match?' },
  'decision.launchPoker.askGambler': {
    it: 'Mandi anche una pedina dal Covo al Den, a fare il Gambler? Peschi una carta dei Preti.',
    en: 'Do you also send a pawn from your Base to the Den as a Gambler? You draw a Reverends card.',
  },
  'decision.launchPoker.play': { it: 'Gioca!', en: 'Play!' },
  'decision.launchPoker.playSend': { it: 'Gioca e manda una pedina nel Den', en: 'Play and send a pawn to the Den' },
  'decision.launchPoker.playStay': { it: 'Gioca senza mandare una pedina', en: 'Play without sending a pawn' },
  'decision.launchPoker.denFull': { it: 'Il Den è pieno: nessuna pedina può andarci.', en: 'The Den is full: no pawn can go there.' },
  'decision.launchPoker.noPawn': { it: 'Non hai pedine nel Covo da mandare nel Den.', en: 'You have no pawns in Base to send to the Den.' },
  'decision.boost.dialog': { it: "Potenzia l'azione", en: 'Boost the action' },
  'decision.boost.useCard': { it: "Usa {card} per potenziare l'azione", en: 'Use {card} to boost the action' },
  'decision.pokerCards.title': { it: 'Scegli fino a {max} carte per il Poker', en: 'Pick up to {max} cards for the Poker' },
  'decision.pokerCards.hint': {
    it: 'Clicca le carte nella mano in basso a destra ({selected}/{max}). Restano coperte finché tutti hanno scelto.',
    en: 'Click the cards in the hand at the bottom right ({selected}/{max}). They stay face down until everyone has picked.',
  },
  'decision.pokerCard.title': { it: 'Scegli la carta per il Poker', en: 'Pick the card for the Poker' },
  'decision.pokerCard.hint': {
    it: 'Clicca una carta nella mano in basso a destra: resta coperta finché tutti hanno scelto.',
    en: 'Click a card in the hand at the bottom right: it stays face down until everyone has picked.',
  },
  'decision.pokerSymbols.title': { it: 'Scegli 2 simboli tra quelli delle tue carte', en: 'Pick 2 symbols among those of your cards' },
  'decision.pokerSymbols.hint': { it: 'Clicca 2 simboli ({selected}/{max}).', en: 'Click 2 symbols ({selected}/{max}).' },

  // Marketing and bribes paid in Dope
  'decision.marketing.dialog': { it: 'Carte Marketing', en: 'Marketing cards' },
  'decision.marketing.useCard': { it: 'Usa {card} per Marketing', en: 'Use {card} for Marketing' },
  'decision.payoff.question': { it: 'Chi vuoi corrompere, e come paghi?', en: 'Who do you want to bribe, and how do you pay?' },
  'decision.payoff.hoodShort': { it: 'Q', en: 'H' },
  'decision.payoff.payDope': { it: 'paga 1 {dope}', en: 'pay 1 {dope}' },
  'decision.payoff.payMoney': { it: 'paga i soldi', en: 'pay money' },
  'decision.officer.fed': { it: 'Fed', en: 'Fed' },
  'decision.officer.cop': { it: 'Cop', en: 'Cop' },

  // Plain fallback
  'decision.noOptions': { it: 'Nessuna opzione disponibile.', en: 'No option available.' },
  'decision.pickRange': { it: 'Seleziona da {min} a {max} opzioni.', en: 'Pick from {min} to {max} options.' },
});
