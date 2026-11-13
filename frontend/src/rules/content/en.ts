import type { RulePage } from '../types';

// The English text of every rules page (game designer, 2026-11-03). Only the words are here: the slug,
// the images and the "see also" links of each page stay in the Italian files and are shared, so a
// page can never lose a link in one language. Terms follow the glossary of i18n/texts/common.ts
// (Hood, Base, Dope, Grit, Link, Raid, Brawl, Den, Jail, Rat, Gambler, Cop/Fed, Sales Spot).
type RulePageText = Pick<
  RulePage,
  'title' | 'summary' | 'keywords' | 'cosaServe' | 'cosaFai' | 'cosaSuccede' | 'attenzione' | 'esempio'
>;

export const RULE_PAGES_EN: Record<string, RulePageText> = {
  'basics/game-structure': {
    title: 'Game structure',
    summary: 'A game lasts 3 turns. Each turn is split into 3 rounds of actions, followed by the Showdown.',
    keywords: ['turn', 'turns', 'round', 'structure', 'phases', 'tip-off', 'showdown'],
    cosaSuccede: [
      'Every turn opens with the Tip-off: a Raid card is revealed and the first player of the turn is chosen.',
      'Then come 3 Action rounds: in each, every player assigns a Grit marker and makes their pawns act.',
      'If a player launched a Poker match in a round, it is resolved at the end of that same round, before the next round starts.',
      'After the third round comes the Showdown: it is checked who gets caught by that turn’s Raid.',
    ],
    attenzione: [
      'The game does NOT last 4 turns: it is always 3 turns of 3 rounds each (the "4 days" in the game’s intro are only narrative).',
    ],
  },
  'basics/round': {
    title: 'The round',
    summary: 'Each round you assign a Grit marker to an action and have some pawns carry it out.',
    keywords: ['round', 'grit', 'action', 'extra action', 'link', 'discard'],
    cosaFai: [
      'Pick one of your 3 Grit markers (values 1, 2 and 3) and assign it to one of the 6 base actions.',
      'If you want, play one or more cards to boost the chosen action or to do Marketing.',
      'Make up to as many pawns act as the marker’s value: each pawn that takes part performs a copy of the same action, from its own position.',
      'If you have a free Link, you can also spend an extra action, before or after the main action.',
      'Discard cards until you have at most 5 in hand.',
    ],
    attenzione: [
      'The Grit value is a MAXIMUM, not a required number: you can make just one pawn act even if you picked the 3 marker.',
      'In the 3 rounds of the same turn you cannot pick the same base action twice: you necessarily use 3 different ones out of the 6 (the Link extra action is the exception, it can repeat).',
    ],
  },
  'basics/goal': {
    title: 'Goal',
    summary: 'You are the Boss of a Gang trying to make room in the city’s underworld: whoever collects the most Respect (REP) at the end of the game wins.',
    keywords: ['goal', 'respect', 'rep', 'victory', 'boss', 'gang'],
    cosaSuccede: [
      'You complete Jobs to earn REP, managing Criminals, Dope and Contacts to build your business.',
      'At the end of the game money, REP, majorities with the Contacts, Chips in your Base and Skills are all converted into points.',
      'Whoever scores the most points wins; on a tie, whoever has more clean REP wins; if the tie persists, the victory is shared.',
    ],
  },

  'actions/buy-dope': {
    title: 'Buying Dope',
    summary: 'A Criminal or a Link buys Dope in its own Hood, paying the current price.',
    keywords: ['buy', 'purchase', 'dope', 'market', 'price', 'stonk'],
    cosaServe: [
      'A Criminal or a Link in the Hood, with at least one Dope available and no Cop present.',
      'Enough money to cover the price.',
    ],
    cosaFai: [
      'Pick the Criminal (or the Link, in one of its Contact’s two Hoods) that will make the purchase.',
      'If you want, before buying play a card with Stonks to change the price of a Dope of your choice by 1.',
      'Pay the Dope’s current price: it moves from the Hood to your Base.',
    ],
    cosaSuccede: [
      'The price of that Dope goes up by 1 after the purchase.',
      'If the Hood runs out of that Dope, it is restocked (up to 3, or whatever is left in the shared bank) and a Cop enters.',
      'When you buy several Dope in the same Hood in the same round, the price increases are all applied together, at the end of the package.',
    ],
    attenzione: [
      'A Cop in the Hood blocks the purchase.',
      'In the Easy Price variant buying does not change the price: it only goes to the maximum if the Hood is emptied.',
      'With a Link, if it can legally buy in both of its Contact’s Hoods, you choose which one to buy from — unlike selling, here the Hood matters.',
    ],
  },
  'actions/sell-dope': {
    title: 'Selling Dope',
    summary: 'A Criminal or a Link sells Dope from the Base to its Contact’s Sales Spot, collecting the price.',
    keywords: ['sell', 'sale', 'dope', 'spot', 'sales spot', 'price', 'stonk'],
    cosaServe: [
      'A Criminal or a Link in the Hood, with the matching Sales Spot not occupied by a Fed.',
      'The Dope to sell already in your Base.',
    ],
    cosaFai: [
      'Pick the Criminal (or the Link) that will sell.',
      'If you want, before the sale play a card with Stonks to change the price of a Dope of your choice by 1.',
      'You collect the current price: the Dope moves from the Base to the Sales Spot.',
    ],
    cosaSuccede: [
      'The price of that Dope goes down by 1 after the sale.',
      'When selling a single unit, you can choose whether to evolve the Criminal that sold into a Link.',
      'When selling several units in the same package, you automatically take a Link of the level equal to the number of Dope sold.',
      'If the Sales Spot fills up (3 Dope), it is emptied and a Fed enters. Its Dope goes back to the reserve.',
    ],
    attenzione: [
      'A Fed in the Sales Spot blocks the sale.',
      'In the Easy Price variant selling does not change the price: it only drops to the minimum if the Sales Spot fills up.',
      'With a Link you do not need to pick the Hood: the two Hoods of the same Contact always share the same Sales Spot.',
    ],
  },

  'characters/criminal': {
    title: 'Criminal',
    summary: 'The Criminal is your basic pawn: place it in Hoods to buy, sell, manipulate and fight Brawls.',
    keywords: ['criminal', 'pawn', 'gang'],
    cosaSuccede: [
      'By selling Dope or winning a Brawl in a Hood, a Criminal can evolve into a Link with that Hood’s Contact.',
      'By moving into the Den, a Criminal becomes a Gambler.',
      'If arrested, a Criminal becomes a Rat and ends up in Jail.',
    ],
    attenzione: ['Each pawn always has only one role at a time: it is never a Criminal and a Link at once.'],
  },
  'characters/link': {
    title: 'Link',
    summary: 'A Link is an evolved pawn, hooked to one of a Contact’s 3 levels: it counts as a presence in both of that Contact’s Hoods.',
    keywords: ['link', 'contact', 'evolution'],
    cosaServe: [
      'A Criminal that sold Dope or won a Brawl (or a Gambler that wins a Poker, or a Rat that causes a Jailbreak — they evolve into Links in a different way).',
    ],
    cosaSuccede: [
      'The new Link always enters at level 1: if it is occupied, the pawn already there slides to level 2 (and the one on 2 to level 3); whoever leaves level 3 goes back to its owner’s Base.',
      'A Link counts as a Criminal presence in BOTH of its Contact’s Hoods, to buy, sell, manipulate and for Brawls.',
      'You can spend a Link for an extra action (once per round) among those of its Contact: it goes back to your Base right when you choose it.',
    ],
    attenzione: [
      'A Contact’s 3 levels are shared among ALL players: there can never be two Links of two different players at the same level of the same Contact.',
    ],
  },

  'locations/jail': {
    title: 'Jail',
    summary: 'The Jail has 4 slots. When the fourth is occupied, the Jailbreak triggers immediately.',
    keywords: ['jail', 'prison', 'rat', 'arrest', 'slot', 'jailbreak', 'escape'],
    cosaSuccede: [
      'An arrested Criminal or Link becomes a Rat and takes the first free slot of the Jail (1 to 4).',
      'If a Dope is also confiscated in the same arrest, it stays associated with that Rat, in its slot.',
      'Rats can manipulate Cops in any Hood, not only while staying in Jail.',
    ],
    attenzione: [
      'The Jail does NOT have 6 slots: it is always and only 4 slots.',
      'When the fourth slot fills up, the Jailbreak triggers immediately — even in the middle of resolving another mechanic, like a Brawl or a Poker.',
    ],
  },
  'locations/jail-evasion': {
    title: 'Jailbreak',
    summary: 'When the fourth Rat enters the Jail, all the Rats break out and go back to their Bases with the Dope they had on them.',
    keywords: ['jailbreak', 'escape', 'jail', 'rat', 'link', 'politicians'],
    cosaSuccede: [
      'The 4 Rats leave the Jail: 3 go back to their owner’s Base as free pawns, bringing along any Dope confiscated in their slot.',
      'The fourth Rat — the one that caused the Jailbreak by filling the last slot — does not come back as a free pawn: it evolves directly into a Link with the Politicians.',
      'The Jail stays empty, ready for the next arrests.',
    ],
    attenzione: [
      'The Jailbreak can be triggered by an arrest from any cause — not only a manipulation, but also, for example, a Gambler that loses at Poker.',
    ],
  },

  'police/cop': {
    title: 'Cop',
    summary: 'The Cop patrols a Hood: it blocks purchases until it is manipulated or sent back to the reserve.',
    keywords: ['cop', 'police', 'manipulate', 'bribe', 'arrest'],
    cosaSuccede: [
      'A Cop enters play in a Hood when a Brawl breaks out there, or when the market runs out and is restocked.',
      'While it is there, nobody can buy Dope in that Hood.',
      'A Cop with no Dope and no Criminals in the Hood goes back to the reserve (it does not take a Jail slot).',
    ],
    cosaFai: [
      'A Criminal, Link or Rat can manipulate it by paying 1 dollar per action: move it to an adjacent Hood, make it arrest a Criminal of your choice, or make it confiscate a Dope (the price goes up by 1).',
      'You can make it perform 1 to 3 different actions (never the same one twice), stopping whenever you want.',
    ],
    attenzione: [
      'A Rat can manipulate Cops in any Hood, not only while sitting in Jail.',
      'You can also bribe a Cop for 7 dollars, from the Hood or from another player’s Base, and bring it to your Base.',
    ],
  },
  'police/fed': {
    title: 'Fed',
    summary: 'The Fed investigates in a Sales Spot: it blocks sales until it is manipulated or sent back to the reserve.',
    keywords: ['fed', 'detective', 'manipulate', 'bribe', 'arrest', 'spot'],
    cosaSuccede: [
      'A Fed enters play in a Sales Spot when it fills up or empties of Dope.',
      'While it is there, nobody can sell in that Sales Spot.',
      'A Fed in a Sales Spot with no Dope and no Link of that Contact goes back to the reserve.',
    ],
    cosaFai: [
      'A Criminal, Link or Rat can manipulate it by paying 1 dollar per action: move it to an adjacent Sales Spot, make it arrest the lowest-level Link of the Contact, or make it confiscate a Dope (the price goes up by 1).',
      'You can make it perform 1 to 3 different actions (never the same one twice), stopping whenever you want.',
    ],
    attenzione: ['You can also bribe a Fed for 7 dollars, from the Sales Spot or from another player’s Base.'],
  },

  'events/poker': {
    title: 'Poker',
    summary: 'A Reverends Gamble card launches a Poker match: at most one per round, resolved at the end of that round.',
    keywords: ['poker', 'gamble', 'reverends', 'den', 'gambler', 'chip', 'bet'],
    cosaServe: [
      'A Criminal that reached the Den, where it becomes a Gambler.',
      'A Gamble card (only the Reverends offer it) to play in the round of the action it is tied to.',
    ],
    cosaFai: [
      'Play the Gamble card in the round of the action it is tied to: you collect 3 dollars and choose whether to send a Criminal from your Base to the Den, if there is room: if you send it, you draw a card.',
      'At the end of the round, if you have at least one Gambler in the Den, you decide whether to bet by placing one of your Chips on the match.',
      'If you bet, you reveal a non-Gamble card: its 2 symbols are added to the 3 of the shared board, for a 5-symbol hand.',
    ],
    cosaSuccede: [
      'The winning order is: 5 different colors > Four of a Kind > Full House > Three of a Kind > Two Pair > Pair.',
      'The winner collects 2 dollars for every Chip bet, banks one in their Base, and evolves a Gambler into a Link with the Reverends.',
      'Every loser sends their Gambler to Jail.',
      'On a full tie, the Chips stay in play and are added to the pot of the next match launched by anyone.',
    ],
    attenzione: [
      'Only ONE match can be launched per round, shared by the whole table: if someone already launched it, nobody else can in the same round, not even they themselves.',
      'The match is ALWAYS resolved at the end of the round in which it was launched, never at the end of the turn.',
      'Whoever already has 3 Chips in their Base can keep betting by taking them from there.',
    ],
    esempio:
      'Round 2 of your turn: you play the Gamble card tied to Buying Dope, while you perform that action. At the end of the round, you and an opponent with a Gambler in the Den both bet. The cards are revealed: your Full House beats their Pair, you collect the Chips and one of your Gamblers becomes a Link with the Reverends.',
  },
  'events/brawl': {
    title: 'Brawl',
    summary: 'When the fifth Criminal enters a Hood, a Brawl breaks out between all the players there.',
    keywords: ['brawl', 'guns', 'force', 'fight'],
    cosaSuccede: [
      'Whoever has at least one Criminal physically in the Hood takes part; the Contact’s Links add to the force of whoever already takes part.',
      'In turn, the participants play a face-down card with Guns, then reveal them, assigning them to themselves or to someone else.',
      'Criminals + Links + Guns are added up (it can drop below zero): the highest total wins, the lowest loses.',
      'The winner steals 2 dollars or 1 card from each loser, can evolve one of their Criminals into a Link, and sends away one Criminal of each loser.',
      'After the Brawl a Cop enters the Hood.',
    ],
    attenzione: [
      'Placing a Criminal never triggers a Brawl: only a move that brings the fifth Criminal can trigger it, so a placement that would cause it is illegal.',
      'On a tie among the possible losers, they all lose; on a tie among the possible winners, whoever played fewer Guns wins, then whoever triggered the Brawl, then turn order.',
    ],
  },

  'jobs/job': {
    title: 'Job',
    summary: 'Each player owns all 9 Jobs, split into 3 small piles (one per tier): completing them earns REP and a bonus of your choice.',
    keywords: ['job', 'respect', 'rep', 'skill', 'bonus', 'tier'],
    cosaFai: [
      'Always keep 1 Job face up for each of your 3 piles (tier 1/2/3).',
      'When you meet the requirement of a face-up Job, you complete it: you place an R marker in that Job’s row, in a free column of your choice (Skill, Link, 2 cards, or nothing).',
      'Immediately reveal the next card of the same pile.',
    ],
    cosaSuccede: [
      'The Job’s color tells with which Contact you collect the chosen bonus.',
      'The columns are shared: if another player has already completed the same Job, you will only be able to choose among the columns still free on that row.',
    ],
    attenzione: [
      'Most Jobs look at your CURRENT state, not at what you accumulated over time: for example Rats only count the ones really in Jail now, Cops/Feds only the ones in your Base now.',
      'The "Win 1 Brawl" Job is the exception: it only counts Brawls won AFTER the Job was revealed, not the ones won before.',
    ],
  },
  'jobs/reputation': {
    title: 'REP',
    summary: 'REP is the R marker you earn by completing a Job: it is worth 2 points when clean, 1 point when stained.',
    keywords: ['rep', 'reputation', 'stain', 'stained', 'respect'],
    cosaSuccede: [
      'Every completed Job places one of your R markers on the board: it is worth 2 points at the end of the game as long as it stays clean.',
      'A lost Raid stains REP for each player: 1 on the first Raid lost in the game, 2 on the second, 3 on the third — flipping that many of your already placed R markers.',
      'A stained marker is worth only 1 point and can never become clean again.',
    ],
    cosaFai: ['If you have 2 dollars or less, you can voluntarily stain one REP to collect 5 dollars.'],
    attenzione: [
      'You can only stain (for a Raid or voluntarily) REP you already have: if you do not have enough clean ones, you stain the ones you can and that is it, no further penalty.',
    ],
  },

  'raids/raid': {
    title: 'Raid',
    summary: 'Every turn a Raid card is revealed: the team that loses according to its criterion stains its reputation.',
    keywords: ['raid', 'team', 'stain', 'reverends'],
    cosaSuccede: [
      'Whoever has the highest Link with the Reverends chooses the first player of the turn, which also sets the two teams: 1st+4th against 2nd+3rd.',
      'At the end of the turn, for each team, the values of that card’s criterion (for example "more Links with the Contacts") of the two teammates are added up.',
      'The team with the better total escapes; the other is caught and each of its members stains their REP. On a tie, all 4 are caught.',
    ],
    attenzione: ['If nobody has a Link with the Reverends that turn, whoever was first player in the previous turn stays first player.'],
  },

  'scoring/final-score': {
    title: 'Final score',
    summary: 'At the end of the game money, REP, majorities, Chips and Skills are all converted into points: whoever scores the most wins.',
    keywords: ['score', 'points', 'victory', 'majority', 'chip'],
    cosaSuccede: [
      'The position on the money track is worth points: 4 for 1st, 3 for 2nd, 2 for 3rd, 1 for 4th (on a money tie, everyone tied takes the lowest value among the positions involved).',
      'Every clean REP is worth 2 points, every stained REP 1 point.',
      'With each Contact, whoever has the greatest presence (Criminals = 1, Links = 2) takes 1 point; on a tie nobody takes it.',
      'Every 3 Chips in the Base, even of different types, are worth 1 point.',
      'Every Skill owned is worth 1 point.',
    ],
    attenzione: [
      'On a tie in total points, whoever has more clean REP wins; if the tie persists, the victory is shared.',
    ],
  },

  'variants/easy-price': {
    title: 'Easy Price variant',
    summary:
      'Four-level prices that do not change at every purchase or sale, but only when a Sales Spot fills up, a Hood empties, or through Marketing. Poker no longer gives money.',
    keywords: ['easy price', 'variant', 'prices', 'marketing', 'stonk', 'poker', 'mode'],
    cosaServe: ['Pick "Easy Price" on the start screen: the other rules stay those of the Big game.'],
    cosaFai: [
      'Every Dope has four prices, from lowest to highest: Frog 0-1-2-3, Chameleon 2-3-4-6, Octopus 4-5-7-9, Owl 6-8-10-13.',
      'All Dope start at the lowest price: Frog 0, Chameleon 2, Octopus 4, Owl 6.',
    ],
    cosaSuccede: [
      'Buying, selling or confiscating does not change prices.',
      'When a Sales Spot fills up, the price of its Dope immediately goes to the lowest level.',
      'When a Hood empties (even through a confiscation), the price of its Dope immediately goes to the highest level.',
      'Marketing works as in the Big game: each Stonk moves the price of a Dope of your choice by one level, and you can split them among different Dope or stack them on the same one.',
      'Launching a Poker no longer gives money. The winner collects 2$ for every player who took part (themselves included): the money comes from the bank, the losers lose nothing. On a tie nobody is paid and the prizes accumulate: whoever wins the next match also takes 2$ for every Chip carried over. The Chips, the Links and the other rewards stay.',
      'In a Brawl the winner always steals a card from each loser: there is no more choosing between money and a card. Cards with an extra prize stay and add to it: SHAKE DOWN also takes 4$, TAKE THE POT also a Poker Chip, SPOILS also a Dope of your choice. If the loser has no cards in hand, nothing is stolen.',
    ],
    attenzione: [
      'The Frog’s price 0 is a real price: buying it costs nothing.',
      'Filling up or emptying only counts at the moment it happens: Marketing can move the price right after.',
    ],
  },
};
