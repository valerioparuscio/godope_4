// Tutorial cards (game designer, 2026-09-24): "una sequenza di operazioni
// di gioco di prova da raccontare a un nuovo giocatore" — the interface,
// not the rules (those live in the Regolamento instead). Each `id` here
// must match a scenario id the backend knows about
// (backend/src/dope_engine/application/tutorial.py::TUTORIAL_SCENARIO_IDS)
// — `TutorialModal.tsx` creates a real sandbox game from it.
//
// Pilot (5 of the ~20 cards discussed with the designer): one of each
// distinct interaction *shape* already in the frontend, before building
// the rest.
export interface TutorialScenario {
  id: string;
  title: string;
  /** What to do — shown before the move. */
  instruction: string;
  /** What just changed — shown after it, pointing at the visible effect
   *  on the board and on the player's own panel (designer, 2026-09-24:
   *  the card has to *show* the outcome, not just accept the click). */
  outcome: string;
}

export const TUTORIAL_SCENARIOS: TutorialScenario[] = [
  {
    id: 'grit',
    title: 'Scegli la Grinta',
    instruction: 'A ogni round scegli quanta Grinta usare: clicca un numero nella pillola in alto.',
    outcome:
      'Hai speso quel segnalino Grinta: nel round successivo potrai usare solo i valori che ti restano.',
  },
  {
    id: 'place_criminal',
    title: 'Piazza un Criminale',
    instruction: 'Clicca un Quartiere illuminato sul tabellone per piazzare lì un Criminale dal tuo Covo.',
    outcome:
      'Il Criminale è ora sul tabellone, nel Quartiere che hai scelto — e ti è costato 2$.',
  },
  {
    id: 'move_criminal',
    title: 'Sposta un Criminale',
    instruction: 'Clicca la pedina illuminata, poi il Quartiere di destinazione tra quelli illuminati.',
    outcome: 'La pedina si è spostata: ora è nel Quartiere di destinazione che hai scelto.',
  },
  {
    id: 'buy_dope',
    title: 'Compra Dope (con Grinta 3)',
    instruction:
      'Con Grinta 3 puoi comprare fino a 3 volte in un colpo solo: clicca ogni pedina illuminata che vuoi usare, poi premi "Conferma".',
    outcome:
      'La Merce comprata è finita nel tuo Covo: guarda la tua plancia qui a sinistra, il numero di Dope è aumentato.',
  },
  {
    id: 'brawl_card',
    title: 'Gioca una carta in Rissa',
    instruction:
      'Durante una Rissa, clicca una carta nella mano in basso a destra per giocarla coperta (o "Passa" se non vuoi giocarne nessuna).',
    outcome:
      'La carta è stata giocata coperta: resta segreta finché tutti i partecipanti non hanno dichiarato.',
  },
];
