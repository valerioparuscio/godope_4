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
  instruction: string;
}

export const TUTORIAL_SCENARIOS: TutorialScenario[] = [
  {
    id: 'grit',
    title: 'Scegli la Grinta',
    instruction: 'A ogni round scegli quanta Grinta usare: clicca un numero nella pillola in alto.',
  },
  {
    id: 'place_criminal',
    title: 'Piazza un Criminale',
    instruction: 'Clicca un Quartiere illuminato sul tabellone per piazzare lì un Criminale dal tuo Covo.',
  },
  {
    id: 'move_criminal',
    title: 'Sposta un Criminale',
    instruction: 'Clicca la pedina illuminata, poi il Quartiere di destinazione tra quelli illuminati.',
  },
  {
    id: 'buy_dope',
    title: 'Compra Dope (con Grinta 3)',
    instruction:
      'Con Grinta 3 puoi comprare fino a 3 volte in un colpo solo: clicca ogni pedina illuminata che vuoi usare, poi premi "Conferma".',
  },
  {
    id: 'brawl_card',
    title: 'Gioca una carta in Rissa',
    instruction:
      'Durante una Rissa, clicca una carta nella mano in basso a destra per giocarla coperta (o "Passa" se non vuoi giocarne nessuna).',
  },
];
