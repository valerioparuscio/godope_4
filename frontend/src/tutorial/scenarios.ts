import { CONTACT_HEADER_RECT, CONTACT_LINK_SLOT_POSITION, DEN_POSITION, HOOD_POSITION, HOOD_PETAL_POSITION, JAIL_CENTER, JOB_BOARD_CELL_POSITION, SPOT_POSITION, TURN_TRACK_POSITION, moneyTrackPosition, officerBadgePoint, type Point } from '../board-layout';

export interface TutorialMarker extends Point { label: string; area?: 'board' | 'sidebar' | 'toolbar'; target?: string;
  /** Caption side; by default it flips to the left on the right third of the area. */
  labelSide?: 'left' | 'right'; }
/** A temporary info card laid over the board; keep rows short, the type stays large. */
export interface TutorialSheet {
  title: string;
  items?: { label: string; text: string }[];
  /** A grid instead of a list; an empty first column header is the row-label column. */
  table?: { columns: string[]; rows: string[][] };
  /** Rows set apart below the main list (a different kind of information). */
  footer?: { label: string; text: string }[];
}
export interface TutorialScenario {
  /** Unique per card. The whole tutorial is ONE running game: a card only
   *  changes the board when it names a `stage`, and that stage is patched
   *  on top of the game as the previous cards left it. */
  id: string;
  stage?: string;
  title: string;
  instruction: string;
  outcome: string;
  observeOnly?: boolean;
  followUps?: string[];
  advanceBots?: boolean;
  markers?: TutorialMarker[];
  sheet?: TutorialSheet;
  decisionInstructions?: Record<string, string>;
}
const arrow = (point: Point, label: string): TutorialMarker => ({ ...point, label });
const covo: TutorialMarker = { area: 'sidebar', xPct: 55, yPct: 49, label: 'Il tuo Covo', target: '[data-player-id="player_0"] .player-card__inventory' };
const retata: TutorialMarker = { area: 'sidebar', xPct: 45, yPct: 15, label: 'Retata', target: '.raid-banner__intro' };
const artisti = arrow(CONTACT_HEADER_RECT.artisti, 'Cliente');
const gancio = arrow(CONTACT_LINK_SLOT_POSITION.artisti[0], 'Gancio');
const quartiere = arrow(HOOD_POSITION.hood_q1, 'Merci');
// Cops and Feds are small badges: the asterisk sits well clear of them (below
// and to the side) instead of on top, where it would hide them completely.
const copCaption = arrow({ xPct: officerBadgePoint(HOOD_POSITION.hood_q1).xPct - 4.5, yPct: officerBadgePoint(HOOD_POSITION.hood_q1).yPct + 3.5 }, 'Cops');
const fedCaption = arrow({ xPct: officerBadgePoint(SPOT_POSITION.spot_artisti_1).xPct, yPct: officerBadgePoint(SPOT_POSITION.spot_artisti_1).yPct + 5 }, 'Feds');
const prezzi: TutorialMarker = { xPct: 94, yPct: 54, label: 'Prezzi' };

export const TUTORIAL_SCENARIOS: TutorialScenario[] = [
  // ── 1-10 · Il tabellone e le regole base (guarda) ────────────────────────
  {
    id: 'welcome', stage: 'intro', title: 'Benvenuti a DOPE', observeOnly: true,
    instruction: 'Quattro gang si contendono la città.', outcome: '',
  },
  {
    id: 'goal', title: 'Vince chi fa più punti', observeOnly: true,
    instruction: 'I punti arrivano da sei fonti diverse.', outcome: '',
    markers: [
      // JOBS on the Job names right of the grid, REP inside the grid itself.
      arrow({ xPct: 14, yPct: 63.94 }, 'JOBS'), arrow(JOB_BOARD_CELL_POSITION.job_05[1], 'REP'), { ...retata, label: 'RETATE' },
      arrow(moneyTrackPosition(15), 'SOLDI'), { ...covo, label: 'COVO' }, { ...artisti, label: 'CLIENTI' },
      { area: 'toolbar', xPct: 75, yPct: 50, label: 'SKILL', target: '.skills-drawer .hand-drawer__toggle', labelSide: 'right' },
    ],
    sheet: {
      title: 'Da dove vengono i punti', items: [
        { label: 'Jobs', text: 'fino a 18 punti (ciascun Job completato dà una REP che vale 2 punti)' },
        { label: 'Retate', text: 'fino a −6 punti (perdere una Retata fa macchiare le REP, e le REP macchiate valgono 1 solo punto)' },
        { label: 'Soldi', text: 'fino a 4 punti' },
        { label: 'Covo', text: 'fino a 6 punti (1 punto ogni 3 Chip, tra Merci, Chip e Cops)' },
        { label: 'Clienti', text: 'fino a 5 punti (1 per ogni maggioranza presso un Cliente)' },
        { label: 'Skill', text: 'fino a 3 punti (1 per carta Skill)' },
      ],
    },
  },
  {
    id: 'turns', title: '3 Turni, 3 Round', observeOnly: true,
    instruction: 'Una partita dura 3 Turni. Ogni Turno ha 3 Round.', outcome: '',
    markers: [arrow(TURN_TRACK_POSITION[2], 'Segna Turno')],
  },
  {
    id: 'hoods', title: 'Quartieri e Merci', observeOnly: true,
    instruction: 'Al centro dei Quartieri trovi le Merci da comprare. Attorno stanno i Criminali.', outcome: '',
    markers: [quartiere, arrow({ xPct: HOOD_PETAL_POSITION.hood_q1[1].xPct, yPct: HOOD_PETAL_POSITION.hood_q1[1].yPct - 5 }, 'Quartiere')],
  },
  {
    id: 'prices', title: 'I prezzi delle Merci', observeOnly: true,
    instruction: 'Ogni Merce ha un prezzo indicato a destra della board. Comprare lo alza, vendere lo abbassa.', outcome: '',
    markers: [prezzi],
  },
  {
    id: 'covo', title: 'Il tuo Covo', observeOnly: true,
    instruction: 'Qui tieni Merci, Poliziotti comprati e Chip Poker. Vedi i Job attivi.', outcome: '', markers: [covo],
  },
  {
    id: 'customers', title: 'I Clienti', observeOnly: true,
    instruction: 'Ogni Cliente controlla 2 Quartieri e compra solo certe Merci.', outcome: '', markers: [artisti],
    sheet: {
      title: 'I 5 Clienti',
      table: {
        columns: ['', 'Merci che compra', 'Azioni extra', 'Carte'],
        rows: [
          ['Artisti', 'Camaleonte, Polpo', 'Acquistare, Vendere', 'Acquistare, Vendere'],
          ['Studenti', 'Camaleonte, Rana', 'Muovere', 'Muovere (fare Rissa)'],
          ['Manager', 'Gufo, Camaleonte', 'Piazzare', 'Piazzare'],
          ['Preti', 'Rana, Polpo', 'Piazzare, Acquistare, Vendere, Corrompere', 'Poker'],
          ['Politici', 'Rana, Gufo', 'Corrompere, Comprare Cops e Feds', 'Corrompere, Comprare Cops e Feds'],
        ],
      },
    },
  },
  {
    id: 'spots', title: 'Punti vendita', observeOnly: true,
    instruction: 'Vendi le Merci nei punti vendita (PdV) del Cliente giusto. Ne entrano 3 per PdV.', outcome: '',
    markers: [arrow(SPOT_POSITION.spot_artisti_1, 'PdV')],
  },
  {
    id: 'grit', title: 'La Grinta', observeOnly: true,
    instruction: 'Ogni Round scegli quanta Grinta usare: 1, 2 o 3. Ogni Grinta attiva 1 Criminale.', outcome: '',
  },
  {
    id: 'actions', title: 'Le sei azioni', observeOnly: true,
    instruction: 'Con la Grinta scegli una di queste sei azioni. Ora le proviamo una per una.', outcome: '',
    sheet: {
      title: 'Le sei azioni', items: [
        { label: '1 · Piazza', text: 'dal Covo al Quartiere, 2$ e pesca una carta' },
        { label: '2 · Sposta', text: 'in un Quartiere vicino o nel Den, e pesca una carta. Se riempi il Quartiere fai Rissa.' },
        { label: '3 · Acquista', text: 'Merci dove hai Criminali' },
        { label: '4 · Vendi', text: 'Merci a un PdV da un Quartiere dello stesso colore dove hai Criminali' },
        { label: '5 · Corrompi', text: 'Dai fino a 3 ordini a un Poliziotto, 1$ ciascuno. (Sposta, Arresta, Requisisci)' },
        { label: '6 · Compra Poliziotti', text: '7$, e finisce nel tuo Covo. Oppure 7$ e rimetti in gioco da un Covo avversario.' },
      ],
    },
  },

  // ── 11-22 · Si gioca: le azioni sul tabellone ────────────────────────────
  {
    id: 'pick-grit', stage: 'grit', title: 'Tocca a te: scegli la Grinta',
    instruction: 'Scegli una Grinta, poi un’azione. Qualunque tu scelga, poi le proviamo tutte.',
    outcome: 'Ottimo. Ora proviamo le sei azioni sul tabellone.', followUps: ['choose_action_type'],
  },
  {
    id: 'place', stage: 'place_criminal', title: '1 · Piazza',
    instruction: 'Costa 2$ e peschi una carta del Cliente. Scegli un Quartiere illuminato e conferma.',
    outcome: 'Il Criminale è nel Quartiere: 2$ pagati, una carta pescata.',
  },
  {
    id: 'drawn-card', title: 'La carta pescata', observeOnly: true,
    instruction: 'Ogni Quartiere dà carte del suo Cliente. Le trovi nella tua Mano, in alto.', outcome: '',
    markers: [{ area: 'toolbar', xPct: 25, yPct: 50, label: 'Mano', target: '.top-strip__primary-buttons .hand-drawer__toggle' }],
  },
  {
    id: 'move', stage: 'move_criminal', title: '2 · Sposta',
    instruction: 'Scegli la pedina, poi un luogo vicino illuminato e conferma. Pescherai ancora.',
    outcome: 'La pedina ha raggiunto la destinazione.', markers: [arrow(HOOD_PETAL_POSITION.hood_q1[0], 'Criminale')],
  },
  {
    id: 'buy', stage: 'buy_dope', title: '3 · Acquista Merci',
    instruction: 'Acquista una Merce in un Quartiere dove hai un Criminale. Con Grinta 3 scegli fino a 3 Criminali diversi e conferma.',
    outcome: 'Le Merci sono nel Covo, e il loro prezzo è salito.', markers: [quartiere, covo],
  },
  {
    id: 'price-up', title: 'Il prezzo è salito', observeOnly: true,
    instruction: 'Ogni acquisto alza il prezzo di quella Merce. Controlla il bordo destro.', outcome: '',
    markers: [prezzi, covo],
  },
  {
    id: 'sell', stage: 'sell_dope', title: '4 · Vendi',
    instruction: 'Scegli un Criminale in un Quartiere, vendi una Merce dal Covo a un PdV compatibile, poi conferma. Incassi e il prezzo scende.',
    outcome: 'Incassato. Se hai evoluto il Criminale, ora è un Gancio.', followUps: ['evolve_sale_link'],
    markers: [arrow(SPOT_POSITION.spot_artisti_1, 'PdV'), gancio],
    decisionInstructions: { evolve_sale_link: 'Vendita riuscita: il Criminale può diventare Gancio del Cliente. Vuoi?' },
  },
  {
    id: 'marketing', title: 'Marketing', observeOnly: true,
    instruction: 'Prima di Acquistare o Vendere puoi scartare una carta per cambiare i prezzi con gli Stonk.', outcome: '',
    markers: [prezzi, { area: 'toolbar', xPct: 25, yPct: 50, label: 'Mano', target: '.top-strip__primary-buttons .hand-drawer__toggle' }],
    sheet: {
      title: 'Il Marketing', items: [
        { label: 'Quando', text: 'prima di Acquista o Vendita' },
        { label: 'Come', text: 'scarti una carta che ha degli Stonk' },
        { label: 'Effetto', text: 'ogni Stonk cambia di 1 il prezzo di una Merce, in su o in giù' },
        { label: 'Più Stonk', text: 'puoi dividerli come vuoi tra Merci diverse, o sulla stessa' },
      ],
    },
  },
  {
    id: 'officers', stage: 'corrupt_officer', title: 'Cops e Feds', observeOnly: true,
    instruction: 'I Cops bloccano gli acquisti nel Quartiere, i Feds le vendite nel PdV. Si possono corrompere.', outcome: '',
    markers: [copCaption, fedCaption],
  },
  {
    id: 'corrupt', title: '5 · Corrompi',
    instruction: 'Scegli il Poliziotto e conferma. Poi dai ordini diversi: Sposta, Arresta o Requisisci.',
    outcome: 'Il Poliziotto ha obbedito: guarda cosa è cambiato.', followUps: ['corruption_action'], markers: [copCaption],
  },
  {
    id: 'jobs', stage: 'job_reward', title: 'I Jobs', observeOnly: true,
    instruction: 'Hai Jobs attivi nella plancia. Le tue mosse servono anche a completarli.', outcome: '',
    markers: [arrow(JOB_BOARD_CELL_POSITION.job_02[1], 'Job')],
    sheet: {
      title: 'I 9 Jobs', items: [
        { label: 'Liv. 1', text: 'Vinci 1 Rissa · Hai 1 Cop o Fed · Criminali in 6 Quartieri' },
        { label: 'Liv. 2', text: 'Hai 2 Rats · 4 Merci nel Covo, una per tipo · Hai 4 Ganci' },
        { label: 'Liv. 3', text: 'Hai 2 Chip Poker · Tutti i 10 Criminali in gioco · Hai 30 dollari o più' },
      ],
    },
  },
  {
    id: 'job-rewards', title: 'I premi dei Jobs', observeOnly: true,
    instruction: 'Completi un Job: ottieni 1 REP e scegli un premio. Poi se ne rivela un altro.', outcome: '',
    markers: [covo, arrow(JOB_BOARD_CELL_POSITION.job_02[1], 'Premi')],
    sheet: {
      title: 'Premi dei Jobs', items: [
        { label: 'Skill', text: 'Abilità permanente del Cliente del Job, +1 punto vittoria' },
        { label: 'Gancio', text: 'Presso il Cliente del Job' },
        { label: '2 Carte', text: 'Pescate dal mazzo del Cliente del Job' },
        { label: '3 Dollari', text: 'Subito in cassa' },
      ],
    },
  },
  {
    id: 'buy-officer', title: '6 · Compra Poliziotti',
    instruction: 'Scegli il Poliziotto e conferma: 7$ e va nel Covo. Poi, forse, un Job si completa.',
    outcome: 'Il Poliziotto è nel tuo Covo.', markers: [copCaption, covo],
    followUps: ['choose_job_reward', 'choose_job_bonus_alternative', 'choose_skill_to_discard'],
    decisionInstructions: { choose_job_reward: 'Job completato! Scegli una colonna: premio e REP insieme.' },
  },

  // ── 23-29 · Retate, Primo Giocatore, Ganci ───────────────────────────────
  {
    id: 'raids', stage: 'first_player_raid', title: 'Le Retate', observeOnly: true,
    instruction: 'A inizio Turno si rivela una Retata, a fine Turno si risolve. Chi perde macchia delle REP.', outcome: '',
    markers: [retata],
    sheet: {
      title: 'Sfugge alla Retata la squadra che ha…', items: [
        { label: 'Retata 1', text: 'più Ganci con i Clienti' },
        { label: 'Retata 2', text: 'più Criminali in prigione' },
        { label: 'Retata 3', text: 'meno valore di Merci' },
        { label: 'Retata 4', text: 'più Poker vinti' },
        { label: 'Retata 5', text: 'più Cops comprati' },
        { label: 'Retata 6', text: 'più dollari' },
        { label: 'Retata 7', text: 'più Criminali nei Quartieri' },
      ],
      footer: [
        { label: 'Primo Turno', text: 'La Retata macchia 1 REP' },
        { label: 'Secondo Turno', text: 'La Retata macchia 2 REP' },
        { label: 'Terzo Turno', text: 'La Retata macchia 3 REP' },
      ],
    },
  },
  {
    id: 'first-player', title: 'Il Primo Giocatore',
    instruction: 'Il tuo Gancio dai Preti è il più alto: scegli tu chi gioca per primo in questo Turno.',
    outcome: 'Scelto. Le squadre della Retata seguono quest’ordine: 1°+4° contro 2°+3°.', markers: [retata],
  },
  {
    id: 'roles', stage: 'criminal_states', title: 'I tuoi uomini', observeOnly: true,
    instruction: 'Una pedina cambia ruolo secondo dove si trova: Quartiere, Cliente, Den o Jail.', outcome: '',
    markers: [arrow(HOOD_POSITION.hood_q1, 'Criminale'), gancio, arrow(DEN_POSITION, 'Gambler'), arrow(JAIL_CENTER, 'Rat')],
    sheet: {
      title: 'I 4 ruoli di una pedina', items: [
        { label: 'Criminale', text: 'in un Quartiere: conta 1' },
        { label: 'Gancio', text: 'presso un Cliente: conta 1 in ogni Quartiere del Cliente. Puoi consumarlo per 1 azione extra' },
        { label: 'Gambler', text: 'nel Den: gioca a Poker' },
        { label: 'Rat', text: 'in Jail (4 posti): conta come un Criminale ovunque per Corrompere Cops' },
      ],
    },
  },
  {
    id: 'links', title: 'Ganci: presenza e punti', observeOnly: true,
    instruction: 'Un Gancio vale come un Criminale in entrambi i Quartieri del Cliente. E conta 2 nel calcolo delle maggioranze a fine partita.', outcome: '',
    markers: [gancio, arrow(HOOD_POSITION.hood_q1, 'Quartiere'), arrow(HOOD_POSITION.hood_q2, 'Quartiere')],
  },
  {
    id: 'links-how', title: 'Come si ottiene un Gancio', observeOnly: true,
    instruction: 'Entra sempre al livello 1 e spinge in avanti gli altri.', outcome: '',
    markers: [gancio, arrow(CONTACT_LINK_SLOT_POSITION.preti[0], 'Poker'), arrow(CONTACT_LINK_SLOT_POSITION.politici[0], 'Evasione')],
    sheet: {
      title: 'Come ottenere Ganci', items: [
        { label: 'Vendita', text: 'Cliente del Quartiere' },
        { label: 'Vittoria in Rissa', text: 'Cliente del Quartiere' },
        { label: 'Poker vinto', text: 'sempre dai Preti' },
        { label: 'Evasione (4° Rat)', text: 'sempre dai Politici' },
        { label: 'Premio Job', text: 'Cliente del Job' },
      ],
    },
  },
  {
    id: 'extra', stage: 'spend_link', title: 'Azione extra',
    instruction: 'Clicca il Gancio per spenderlo: 1 azione extra per Round. Oppure passa.',
    outcome: 'Il Gancio è tornato al Covo e hai fatto l’azione extra.',
    followUps: ['choose_action_type', 'buy_dope', 'sell_dope', 'evolve_sale_link'], markers: [gancio],
  },
  {
    id: 'links-actions', title: 'Cosa fa ogni Cliente', observeOnly: true,
    instruction: 'Il livello del Gancio è la Grinta; il Cliente decide quali azioni extra puoi fare.', outcome: '',
    markers: Object.entries(CONTACT_LINK_SLOT_POSITION).map(([contact, positions]) => arrow(positions[1], contact.charAt(0).toUpperCase() + contact.slice(1))),
    sheet: {
      title: 'Azione extra per Cliente', items: [
        { label: 'Artisti', text: 'Acquista o Vendi' },
        { label: 'Studenti', text: 'Sposta' },
        { label: 'Manager', text: 'Piazza' },
        { label: 'Politici', text: 'Corrompi o Compra Poliziotti' },
        { label: 'Preti', text: 'Piazza, Acquista, Vendi o Corrompi' },
      ],
    },
  },

  // ── 30-40 · Rissa, Jail, Poker e fine del Round ──────────────────────────
  {
    id: 'brawl-start', stage: 'brawl_trigger', title: 'Scoppia una Rissa', observeOnly: true,
    instruction: 'Il 5° Criminale spostato in un Quartiere scatena la Rissa. Conta la forza di ogni gang presente.', outcome: '',
    markers: [arrow(HOOD_POSITION.hood_q1, 'Rissa')],
  },
  {
    id: 'brawl-card', title: 'Gioca una carta',
    instruction: 'Forza = Criminali + Ganci + Pistole della carta. Gioca la carta dalla Mano, o passa.',
    outcome: 'Rissa conclusa: guarda il risultato e gli spostamenti sul tabellone.', advanceBots: true,
    followUps: ['choose_brawl_loser_reward', 'choose_brawl_link_evolution', 'choose_brawl_relocation_destination'],
    markers: [arrow(HOOD_POSITION.hood_q1, 'Rissa')],
    decisionInstructions: {
      choose_brawl_loser_reward: 'Hai vinto: da ogni sconfitto prendi 2$ o 1 carta.',
      choose_brawl_link_evolution: 'Puoi trasformare un tuo Criminale in Gancio. Scegli, o passa.',
      choose_brawl_relocation_destination: 'Scegli dove mandare gli sconfitti. Poi entra un Cop.',
    },
  },
  {
    id: 'brawl-after', title: 'Dopo la Rissa', observeOnly: true,
    instruction: 'Chi vince incassa, può creare un Gancio e manda via gli sconfitti.', outcome: '',
    sheet: {
      title: 'Il vincitore della Rissa', items: [
        { label: '1 · Ricompensa', text: '2$ o 1 carta da ogni sconfitto' },
        { label: '2 · Gancio', text: 'un suo Criminale può evolvere' },
        { label: '3 · Scaccia', text: 'manda gli sconfitti altrove' },
        { label: '4 · Cop', text: 'entra nel Quartiere' },
      ],
    },
  },
  {
    id: 'jail', stage: 'jail_near_full', title: 'La Jail ha 4 posti', observeOnly: true,
    instruction: 'Gli arrestati diventano Rat. Ci sono già 3 prigionieri: ne manca uno.', outcome: '',
    markers: [arrow(JAIL_CENTER, '3 posti occupati')],
  },
  {
    id: 'escape', stage: 'jail_evasion', title: '4° prigioniero = Evasione', observeOnly: true,
    instruction: 'Scatta subito: tutti tornano ai Covi con la loro Merce. Il 4° diventa Gancio dei Politici.', outcome: '',
    markers: [arrow(JAIL_CENTER, 'Jail vuota'), arrow(CONTACT_LINK_SLOT_POSITION.politici[0], 'Nuovo Gancio')],
  },
  {
    id: 'den', title: 'Il Den', observeOnly: true,
    instruction: 'Chi entra nel Den diventa Gambler. I Gambler giocano a Poker.', outcome: '',
    markers: [arrow(DEN_POSITION, 'Den')],
  },
  {
    id: 'poker-rules', stage: 'poker', title: 'Il Poker', observeOnly: true,
    instruction: 'Una carta Gamble apre il Poker. Se ne gioca uno per Round, risolto a fine Round.', outcome: '',
    markers: [arrow(DEN_POSITION, 'Gambler'), { xPct: 12.7, yPct: 14, label: 'Gamble' }],
    sheet: {
      title: 'Come funziona il Poker', items: [
        { label: 'Banco', text: '3 simboli comuni' },
        { label: 'Tu', text: 'giochi una carta: 2 simboli' },
        { label: 'Vince', text: 'incassa la posta, mette una Chip nel Covo, prende un Gancio dai Preti' },
        { label: 'Perde', text: 'i Gambler sconfitti sono arrestati' },
      ],
    },
  },
  {
    id: 'poker-play', title: 'Punta e gioca',
    instruction: 'Hai un Gambler nel Den: punta, poi gioca una carta per unire i suoi simboli al banco.',
    outcome: 'Poker concluso: guarda chi ha vinto e cosa è successo ai Gambler.',
    advanceBots: true, followUps: ['play_poker_card', 'choose_poker_symbols'],
    markers: [arrow(DEN_POSITION, 'Gambler')],
    decisionInstructions: { play_poker_card: 'Hai puntato: scegli una carta dalla Mano per unirla al banco.' },
  },
  {
    id: 'card-uses', title: 'A cosa servono le carte', observeOnly: true,
    instruction: 'Ogni carta ha un solo uso per volta: scegli quello giusto al momento giusto.', outcome: '',
    sheet: {
      title: 'Gli usi di una carta', items: [
        { label: 'Pistole', text: 'forza extra in una Rissa' },
        { label: 'Simboli', text: 'per il Poker' },
        { label: 'Stonk', text: 'cambiano i prezzi (Marketing)' },
        { label: 'Potenziamento', text: '+1 Grinta all’azione del Cliente' },
      ],
    },
  },
  {
    id: 'hand-limit', stage: 'hand_discard', title: 'Fine Turno: massimo 5 carte',
    instruction: 'Hai troppe carte. Scegli quali scartare e conferma.',
    outcome: 'Mano a posto: restano al massimo 5 carte.',
  },
  {
    id: 'finish', title: 'Ora tocca a te', observeOnly: true,
    instruction: 'Hai visto tutto il necessario. Il resto lo scopri giocando.', outcome: '',
    sheet: {
      title: 'Riepilogo di un Round', items: [
        { label: '1', text: 'Scegli Grinta e azione' },
        { label: '2', text: 'Usa carte e Gancio' },
        { label: '3', text: 'Il Poker si risolve a fine Round' },
        { label: '4', text: 'A fine Turno: Retata e max 5 carte' },
        { label: '5', text: 'Dopo 3 Turni: vince chi ha più punti' },
      ],
    },
  },
];
