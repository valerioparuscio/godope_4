// Tutorial cards (game designer, 2026-09-24): "una sequenza di operazioni
// di gioco di prova da raccontare a un nuovo giocatore" — the interface,
// not the rules (those live in the Regolamento instead). Each `id` here
// must match a scenario id the backend knows about
// (backend/src/dope_engine/application/tutorial.py::TUTORIAL_SCENARIO_IDS)
// — `TutorialModal.tsx` creates a real sandbox game from it.
export interface TutorialScenario {
  /** Backend scenario id used to build the sandbox
   *  (`application/tutorial.py::TUTORIAL_SCENARIO_IDS`). Ignored when
   *  `continuesPrevious` is true — kept anyway, as documentation of
   *  which backend state this step is narrating. */
  id: string;
  title: string;
  /** What to do — shown before the move. */
  instruction: string;
  /** What just changed — shown after it, pointing at the visible effect
   *  on the board and on the player's own panel (designer, 2026-09-24:
   *  the card has to *show* the outcome, not just accept the click). */
  outcome: string;
  /** Decision types that continue this *same* card instead of ending it
   *  — e.g. corruption's own "Sposta / Arresta / Requisisci" step right
   *  after picking the officer. Without these, a card whose real flow
   *  has more than one step stopped halfway through (its outcome text
   *  then described something the learner never actually did). */
  followUps?: string[];
  /** Let the bots answer in between the human's steps — a Rissa needs
   *  the other participants to declare before it can resolve and show
   *  its recap popup. */
  advanceBots?: boolean;
  /** Info-only card: nothing to click on the board, just numbered
   *  markers pointing at board areas plus a legend explaining each. */
  info?: TutorialInfo;
  /** "GUARDA" card (tutorial_istruzioni.md §2.2): the player only reads
   *  and confirms, there's nothing to click — no DecisionPanel/HandDrawer
   *  shown, footer reads "Ho capito", and it counts as complete the
   *  instant its sandbox loads. Unlike `info`, doesn't require board
   *  markers/a legend — a plain narrated board state is enough. */
  observeOnly?: boolean;
  /** Chains this card onto the *same* sandbox game the previous card
   *  left off in, instead of creating a fresh one — for sequences whose
   *  whole point is watching one game state evolve across several
   *  screens (game designer, 2026-09-26: "il sandbox può proseguire in
   *  più step"), e.g. a Rissa's trigger → cards → reward → Gancio →
   *  relocation. The first card of such a chain still creates the
   *  sandbox normally (`continuesPrevious` left unset/false there); its
   *  own `id` still names the scenario id used to build the state on
   *  the backend, `application/tutorial.py::TUTORIAL_SCENARIO_IDS`. */
  continuesPrevious?: boolean;
}

export interface TutorialMarker {
  /** Matches the number at the start of the legend line it explains. */
  n: number;
  /** Board position, in % of the board image (same space as
   *  board-layout.ts). */
  xPct: number;
  yPct: number;
}

export interface TutorialInfo {
  markers: TutorialMarker[];
  legend: string[];
}

export const TUTORIAL_SCENARIOS: TutorialScenario[] = [
  {
    id: 'intro',
    title: 'Benvenuto in DOPE',
    instruction:
      'Quattro gang si contendono la città: muovono Criminali, fanno affari, costruiscono Ganci e cercano di aumentare il proprio Respect. Ma tra Cops, Risse, Poker e Retate, la città non resta tranquilla a lungo.',
    outcome: '',
    observeOnly: true,
  },
  {
    id: 'goal',
    title: 'Lo scopo di DOPE: fare più punti',
    instruction:
      'La partita dura 3 turni: alla fine vince chi ha più punti (a parità, chi ha più REP pulite). Ecco da dove arrivano, indicati sul tabellone e sulla tua plancia.',
    outcome: '',
    continuesPrevious: true,
    info: {
      markers: [
        { n: 1, xPct: 50, yPct: 96.6 },
        { n: 2, xPct: 5.8, yPct: 63 },
        { n: 3, xPct: 52, yPct: 13.3 },
      ],
      legend: [
        '1 · Tracciato del denaro (in basso): a fine partita il più ricco prende 4 punti, il secondo 3, poi 2 e 1.',
        '2 · Tabella dei Job (a sinistra): ogni Job completato ti dà una REP — 2 punti se resta pulita, 1 se una Retata la macchia.',
        "3 · Contact (in alto): per ognuno dei 5, chi ha più presenza nei suoi Quartieri (Criminale = 1, Gancio = 2) prende 1 punto; se c'è pareggio, nessuno.",
        '4 · La tua plancia (a sinistra): ogni 3 oggetti nel Covo — Merci, Poliziotti comprati e Chip del Poker, anche misti — valgono 1 punto.',
        '5 · Skill: ogni Skill che possiedi vale 1 punto. Le ottieni scegliendo la colonna Skill nella tabella dei Job.',
      ],
    },
  },
  {
    id: 'intro',
    title: 'Struttura della partita',
    instruction:
      'Una partita dura 3 Turni. Ogni Turno contiene 3 Round. Il contatore in alto ti dice sempre in quale Turno e Round ti trovi.',
    outcome: '',
    continuesPrevious: true,
    observeOnly: true,
  },
  {
    id: 'first_player_raid',
    title: 'Primo Giocatore e Retata',
    instruction:
      "All'inizio di ogni nuovo Turno si rivela la Retata e si sceglie il Primo Giocatore: chi ha il Link più alto presso i Preti decide chi lo sarà, anche un altro giocatore, non per forza sé stesso (se nessuno ha un Link dai Preti, resta chi lo era prima). Tu hai il Link più alto: clicca uno dei 4 giocatori per sceglierlo.",
    outcome:
      'Il Primo Giocatore è stato scelto: agirà per primo in questo Turno, e lo stesso ordine servirà a dividere le squadre nella Retata appena rivelata.',
  },
  {
    id: 'criminal_states',
    title: 'Dove possono stare i tuoi uomini',
    instruction:
      'I tuoi uomini possono trovarsi in situazioni molto diverse. Guarda la tua plancia e il tabellone: hai un Criminale nel Quartiere, un Gancio presso un Contact, un Gambler nel Den e un Rat in Jail, tutti allo stesso momento.',
    outcome: '',
    observeOnly: true,
    info: {
      markers: [
        { n: 1, xPct: 23.18, yPct: 67.16 },
        { n: 2, xPct: 19.4, yPct: 13.25 },
        { n: 3, xPct: 23.26, yPct: 41.34 },
        { n: 4, xPct: 87.5, yPct: 88.8 },
      ],
      legend: [
        '1 · Criminale: nel Quartiere, pronto a comprare, vendere o corrompere.',
        '2 · Gancio: presso un Contact, dopo una vendita — conta doppio per la maggioranza e può dare azioni extra.',
        '3 · Gambler: nel Den, dove è entrato per giocare a Poker.',
        '4 · Rat: arrestato, in uno dei 4 posti della Jail.',
      ],
    },
  },
  {
    id: 'job_reward',
    title: 'Completa un Job e scegli il premio',
    instruction:
      'Il tuo Job di livello 1 chiede di possedere 1 Poliziotto. Compra il Poliziotto illuminato e premi "Conferma": il Job si completa e devi mettere la tua REP nella sua riga della tabella. Clicca una delle 4 colonne illuminate — Skill (+1 punto), Gancio, 2 carte o 3$ — per scegliere il premio.',
    outcome:
      'Job completato: la tua REP è nella tabella (2 punti a fine partita, se non viene macchiata) e hai ricevuto il premio della colonna che hai scelto. Al suo posto si scopre un nuovo Job.',
    followUps: ['choose_job_reward', 'choose_job_bonus_alternative', 'choose_skill_to_discard'],
  },
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
    instruction:
      'Clicca un Quartiere illuminato sul tabellone, poi premi "Conferma" per piazzare lì un Criminale dal tuo Covo.',
    outcome: 'Il Criminale è ora sul tabellone, nel Quartiere che hai scelto — e ti è costato 2$.',
  },
  {
    id: 'move_criminal',
    title: 'Sposta un Criminale',
    instruction:
      'Clicca la pedina illuminata, poi il Quartiere di destinazione tra quelli illuminati, poi "Conferma".',
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
    id: 'sell_dope',
    title: 'Vendi Dope (e ottieni un Gancio)',
    instruction:
      'Clicca una pedina illuminata per vendere lì la tua Merce (se quel Contact ne accetta più di un tipo, clicca anche lo Spot che si illumina), poi "Conferma". Subito dopo ti chiederà se trasformare il Criminale in un Gancio.',
    outcome:
      'La Merce è passata dal Covo allo Spot e hai incassato. Se hai detto Sì, il Criminale è diventato un Gancio: lo vedi sulla pista del Contact, in alto.',
    followUps: ['evolve_sale_link'],
  },
  {
    id: 'spend_link',
    title: 'Spendi un Gancio',
    instruction:
      'Hai un Gancio: cliccalo sulla sua pista per spendere un\'azione extra, oppure premi "Salta" per tenerlo.',
    outcome:
      "Il Gancio speso torna nel Covo e ti dà subito un'azione extra, in più rispetto a quella del round.",
  },
  {
    id: 'corrupt_officer',
    title: 'Corrompi un Poliziotto',
    instruction:
      'Clicca il Poliziotto illuminato e premi "Conferma". Poi scegli cosa fargli fare (Sposta / Arresta / Requisisci) e, se serve, clicca il bersaglio sul tabellone. Ogni ordine costa 1$: premi "Fine" quando hai finito.',
    outcome: 'Il Poliziotto corrotto ha eseguito i tuoi ordini, e ognuno ti è costato 1$.',
    followUps: ['corruption_action'],
  },
  {
    id: 'buy_officer',
    title: 'Compra un Poliziotto',
    instruction:
      'Clicca il Poliziotto illuminato sul tabellone e premi "Conferma" per comprarlo e portartelo nel Covo (7$).',
    outcome:
      'Il Poliziotto è ora tuo: lo vedi nel contatore COPS della tua plancia, qui a sinistra.',
  },
  {
    id: 'brawl_trigger',
    title: 'Scoppia una Rissa',
    instruction:
      'Il Quartiere illuminato è diventato troppo affollato: ci sono 5 Criminali, e scoppia una Rissa — ogni Boss coinvolto conta la propria forza presente lì. Clicca una carta nella mano in basso a destra per giocarla coperta (o "Passa"): le sue Pistole si aggiungono sempre alla tua forza, mai a quella di un avversario.',
    outcome:
      'La Rissa si è risolta: il popup di resoconto mostra la forza di ciascun giocatore (pedine + pistole proprie) e chi ha vinto.',
    advanceBots: true,
  },
  {
    id: 'brawl_trigger',
    title: 'Ricompensa della Rissa',
    instruction:
      'Hai vinto: ora puoi sfruttare il controllo ottenuto. Per ogni sconfitto scegli cosa prendergli — 2$ oppure 1 carta.',
    outcome: 'Hai incassato la tua ricompensa da ogni sconfitto.',
    continuesPrevious: true,
    followUps: ['choose_brawl_loser_reward'],
  },
  {
    id: 'brawl_trigger',
    title: 'Creare un Gancio',
    instruction:
      'Puoi trasformare una delle pedine evidenziate in un Gancio presso questo Contact. Scegline una, oppure premi "Passa" per restare Criminale.',
    outcome: 'Se hai scelto una pedina, è diventata un Gancio: la vedi sulla pista del Contact, in alto.',
    continuesPrevious: true,
  },
  {
    id: 'brawl_trigger',
    title: 'Mandare via gli sconfitti',
    instruction:
      'Ora decidi dove mandare gli sconfitti. I Quartieri evidenziati sono destinazioni valide: scegline uno per ciascuno.',
    outcome: 'Gli sconfitti sono stati rimandati nei Quartieri che hai scelto, ed entra un Cop nel Quartiere della Rissa.',
    continuesPrevious: true,
  },
  {
    id: 'jail_near_full',
    title: 'La Jail ha solo 4 posti',
    instruction:
      'Un Criminale arrestato finisce in Jail come Rat. Guarda: la Jail ha solo 4 posti, e sono già 3 occupati. Se un quarto Criminale viene arrestato, scatta subito un\'Evasione.',
    outcome: '',
    observeOnly: true,
    info: {
      markers: [{ n: 1, xPct: 85.05, yPct: 78.1 }],
      legend: ['1 · Jail: 4 posti, 3 già occupati — un quarto arresto la farà scattare.'],
    },
  },
  {
    id: 'jail_evasion',
    title: 'Evasione',
    instruction:
      "Il quarto ingresso in Jail fa scattare immediatamente un'Evasione: i 4 Rat tornano tutti ai rispettivi Covi, ciascuno portando con sé la Merce confiscata nel proprio posto. La Jail è appena tornata vuota.",
    outcome: '',
    observeOnly: true,
    info: {
      markers: [{ n: 1, xPct: 85.05, yPct: 78.1 }],
      legend: ["1 · Jail, di nuovo vuota: 4° prigioniero = Evasione."],
    },
  },
  {
    id: 'hand_discard',
    title: 'Scarta le carte in eccesso',
    instruction:
      'A fine turno puoi tenere al massimo 5 carte: clicca nella mano in basso a destra le 2 da scartare, poi "Conferma".',
    outcome: 'Le carte scelte sono state scartate: la tua mano è tornata al limite di 5.',
  },
];
