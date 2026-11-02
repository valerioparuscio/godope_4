import { defineTexts } from '../define';

// Tooltips and screen-reader labels on the board.
export const boardTexts = defineTexts({
  'board.background': { it: 'Tabellone', en: 'Board' },
  'board.hiddenHood': { it: 'Quartiere nascosto', en: 'Hidden Hood' },
  'board.turnN': { it: 'Turno {n}', en: 'Turn {n}' },
  'board.copFromJail': { it: 'Cop dalla Jail', en: 'Cop from the Jail' },
  'board.fedFromJail': { it: 'Fed dalla Jail', en: 'Fed from the Jail' },
  'board.inBank': { it: '{dope}: {n} in banca', en: '{dope}: {n} in the bank' },
  'board.resetMarketing': { it: 'Azzera', en: 'Reset' },
  'board.lowerPrice': { it: 'Abbassa il prezzo: {dope}', en: 'Lower the price: {dope}' },
  'board.raisePrice': { it: 'Alza il prezzo: {dope}', en: 'Raise the price: {dope}' },
  'board.cancelSelection': { it: 'Annulla selezione', en: 'Cancel selection' },
  'board.moveThisCriminal': { it: 'Sposta questo Criminale', en: 'Move this Criminal' },
  'board.sellFromCriminal': { it: 'Vendi da questo Criminale', en: 'Sell from this Criminal' },
  'board.bribeFromPawn': { it: 'Corrompi da questa pedina', en: 'Bribe from this pawn' },
  'board.chooseContact': { it: 'Scegli il cliente: {contact}', en: 'Pick the Contact: {contact}' },
  'board.mark.moved': {
    it: 'Già spostato in questa azione: non si può spostare di nuovo.',
    en: 'Already moved in this action: it cannot move again.',
  },
  'board.mark.noDestination': {
    it: 'Nessuna destinazione libera: quartieri adiacenti non scoperti o pieni, o già 4 tuoi Criminali, e il Den non è disponibile.',
    en: 'No free destination: adjacent Hoods are not revealed or are full, or you already have 4 Criminals there, and the Den is not available.',
  },
});
