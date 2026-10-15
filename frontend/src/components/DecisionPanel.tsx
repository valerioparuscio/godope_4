import { useState } from 'react';
import {
  actionTypeAssetUrl,
  cardAssetUrl,
  DOPE_ASSET,
  GRIT_ICON,
  playerColorForId,
  playerTeamNameForId,
  POKER_SYMBOL_COLOR,
  POKER_SYMBOL_LABEL,
  skillAssetUrl,
} from '../assets';
import type { DecisionOptionResponse, GameViewResponse, PendingDecisionResponse } from '../types';
import { OfficerActionIcon } from './OfficerActionIcon';

interface DecisionPanelProps {
  decision: PendingDecisionResponse;
  view: GameViewResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
  compactOptional?: boolean;
  guidanceInCorner?: boolean;
  stagedManeuverAction?: string | null;
  onStageManeuverAction?: (action: string | null) => void;
}

// What each Rissa reward button says: money or a card, plus the two theft rewards a
// "FIGHT!!" card unlocks (a Dope / a Poker Chip taken from the loser's Covo).
const BRAWL_REWARD_LABEL: Record<string, string> = {
  money: 'Soldi',
  card: 'Carta',
  dope: 'Merce',
  poker_chip: 'Chip Poker',
};

const DOPE_NAME_LABEL: Record<string, string> = {
  rana: 'Rana',
  camaleonte: 'Camaleonte',
  polpo: 'Polpo',
  gufo: 'Gufo',
};

// Rissa reward picker. Every option targets the same loser (with several losers the
// decision is asked once per loser, so the title names whose reward this is). The
// Dope reward has one option per type the loser holds: "Merce" opens a second
// message to pick which one (or takes it straight away when there is only one).
function BrawlRewardPanel({
  decision,
  onSubmit,
  submitting,
}: {
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
}) {
  const [choosingDope, setChoosingDope] = useState(false);
  const loserId = decision.options[0].payload.loser_player_id as string | undefined;
  const loserName = loserId ? (
    <span className={`decision-panel__loser decision-panel__loser--${playerColorForId(loserId)}`}>
      {playerLabel(loserId)}
    </span>
  ) : 'uno sconfitto';
  const dopeOptions = decision.options.filter((o) => o.payload.reward_type === 'dope');
  const otherOptions = decision.options.filter((o) => o.payload.reward_type !== 'dope');

  if (choosingDope && dopeOptions.length > 1) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Quale Merce vuoi da {loserName}?</h3>
        <div className="decision-panel__quick-buttons">
          {dopeOptions.map((option) => (
            <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
              {DOPE_NAME_LABEL[option.payload.dope_type as string] ?? 'Merce'}
            </button>
          ))}
          <button disabled={submitting} onClick={() => setChoosingDope(false)}>
            Indietro
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="decision-panel decision-panel--quick">
      <h3>Che ricompensa vuoi da {loserName}?</h3>
      <div className="decision-panel__quick-buttons">
        {otherOptions.map((option) => (
          <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
            {BRAWL_REWARD_LABEL[option.payload.reward_type as string] ?? 'Carta'}
          </button>
        ))}
        {dopeOptions.length > 0 && (
          <button
            disabled={submitting}
            onClick={() => (dopeOptions.length === 1 ? onSubmit([dopeOptions[0].option_id]) : setChoosingDope(true))}
          >
            {BRAWL_REWARD_LABEL.dope}
          </button>
        )}
      </div>
    </div>
  );
}

function playerLabel(playerId: string): string {
  return playerTeamNameForId(playerId);
}

const MANEUVER_ACTION_LABEL: Record<string, string> = {
  move: 'Sposta',
  arrest: 'Arresta',
  confiscate: 'Requisisci',
};

const ACTION_TYPE_LABEL: Record<string, string> = {
  place_criminal: 'Piazza',
  move_criminal: 'Sposta',
  buy_dope: 'Acquista',
  sell_dope: 'Vendi',
  maneuver_officer: 'Manovra',
  corrupt_officer: 'Corrompi',
};

// Same fixed order every round (designer's request, 2026-08-16: "così ci
// stanno tutti in posizione fissa") — all 6 action types always render,
// so the row never reflows as choices become unavailable; only the
// legal_actions.py-qualifying ones (in decision.options) are clickable.
const ACTION_TYPE_ORDER = [
  'place_criminal',
  'move_criminal',
  'buy_dope',
  'sell_dope',
  'maneuver_officer',
  'corrupt_officer',
] as const;

// Package-select decisions answered entirely by clicking targets on the
// board (BoardView's own dedicated components or its generic
// BoardHighlights) — this panel only ever needs a heading, a one-line
// hint, and the Confirm/Passa button that already existed at the bottom
// of the plain fallback, never the raw option list with its
// JSON.stringify(payload) dump.
const BOARD_PACKAGE_LABEL: Record<string, string> = {
  ...ACTION_TYPE_LABEL,
  play_marketing_card: 'Gioca Marketing',
};

// A Buy/Sell card's follow-up (cards 11/19 place, 14/16 Den, 17 move) is asked as an ordinary
// Place/Move decision whose `context.card_followup` says which one; these replace its title/hint.
const CARD_FOLLOWUP_TEXT: Record<string, { title: string; hint: string }> = {
  place: {
    title: 'Carta: piazza 1 Criminale',
    hint: 'Clicca un Quartiere illuminato, tra quelli dove hai acquistato o venduto.',
  },
  den: {
    title: 'Carta: manda 1 Criminale nel Den',
    hint: 'Clicca il Criminale illuminato che vuoi mandare nel Den, poi il Den.',
  },
  move: {
    title: 'Carta: sposta 1 Criminale',
    hint: 'Clicca un Criminale illuminato, poi la sua destinazione.',
  },
};

const BOARD_PACKAGE_HINT: Record<string, string> = {
  place_criminal: 'Clicca un Quartiere illuminato sul tabellone.',
  move_criminal: 'Clicca un Criminale illuminato, poi la sua destinazione.',
  buy_dope: 'Clicca una pedina illuminata sul tabellone per comprare.',
  sell_dope: 'Clicca una pedina illuminata sul tabellone per vendere.',
  maneuver_officer: 'Clicca un Cop/Fed illuminato sul tabellone.',
  corrupt_officer: 'Clicca un Cop/Fed illuminato sul tabellone.',
  play_marketing_card: 'Usa + e − accanto ai prezzi: ogni clic usa uno Stonk.',
};

// The two decisions that fire every single action round (how much Grit,
// then which action) get a dedicated one-click button row instead of the
// generic checkbox list below — clicking submits immediately since both
// are always single-select with no "pass".
function QuickButtons({
  options,
  render,
  onSubmit,
  submitting,
}: {
  options: DecisionOptionResponse[];
  render: (option: DecisionOptionResponse) => string;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
}) {
  return (
    <div className="decision-panel__quick-buttons">
      {options.map((option) => (
        <button
          key={option.option_id}
          disabled={submitting}
          onClick={() => onSubmit([option.option_id])}
        >
          {render(option)}
        </button>
      ))}
    </div>
  );
}

export function DecisionPanel({
  decision,
  view,
  selected,
  onToggle,
  onSubmit,
  submitting,
  compactOptional,
  guidanceInCorner,
  stagedManeuverAction,
  onStageManeuverAction,
}: DecisionPanelProps) {
  const [marketingCardOpenedFor, setMarketingCardOpenedFor] = useState<string | null>(null);
  const isValidSelection =
    selected.length >= decision.min_selections && selected.length <= decision.max_selections;
  const isPass = selected.length === 0 && decision.can_pass;
  const canSubmit = (isValidSelection || isPass) && !submitting;
  const buttonLabel = selected.length === 0 && decision.can_pass ? 'Passa' : 'Conferma';

  if (decision.decision_type === 'choose_grit_action') {
    return (
      <div className="decision-pill">
        <span className="decision-pill__verb">GRINTA</span>
        <div className="decision-pill__options">
          {decision.options.length > 0 ? (
            decision.options.map((option) => (
              <button
                key={option.option_id}
                className="decision-pill__grit-button"
                disabled={submitting}
                onClick={() => onSubmit([option.option_id])}
              >
                <img
                  src={GRIT_ICON[Number(option.payload.grit_value)]}
                  alt={`Grinta ${option.payload.grit_value}`}
                  className="grit-icon"
                />
              </button>
            ))
          ) : (
            decision.can_pass && (
              <button className="decision-pill__pass" disabled={submitting} onClick={() => onSubmit([])}>
                Passa
              </button>
            )
          )}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_action_type') {
    const optionByActionType = new Map(
      decision.options.map((option) => [option.payload.action_type as string, option]),
    );
    return (
      <div className="decision-pill">
        <span className="decision-pill__verb">AZIONE</span>
        <div className="decision-pill__options">
          {decision.options.length > 0 ? (
            ACTION_TYPE_ORDER.map((actionType) => {
              const option = optionByActionType.get(actionType);
              return (
                <button
                  key={actionType}
                  className="decision-pill__action-button"
                  disabled={!option || submitting}
                  onClick={() => option && onSubmit([option.option_id])}
                  title={ACTION_TYPE_LABEL[actionType]}
                >
                  <img src={actionTypeAssetUrl(actionType)} alt={ACTION_TYPE_LABEL[actionType]} data-action={actionType} />
                </button>
              );
            })
          ) : (
            decision.can_pass && (
              <button className="decision-pill__pass" disabled={submitting} onClick={() => onSubmit([])}>
                Passa
              </button>
            )
          )}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'maneuver_action') {
    const groups: Record<string, DecisionOptionResponse[]> = { move: [], arrest: [], confiscate: [] };
    for (const option of decision.options) {
      const action = option.payload.action as string;
      (groups[action] ??= []).push(option);
    }
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Che azione fa l'ufficiale manovrato?</h3>
        <div className="decision-panel__quick-buttons">
          {(['move', 'arrest', 'confiscate'] as const)
            .filter((action) => groups[action].length > 0)
            .map((action) => (
              <button
                key={action}
                disabled={submitting}
                className={'decision-panel__officer-action'
                  + (stagedManeuverAction === action ? ' decision-panel__quick-buttons--staged' : '')}
                aria-label={MANEUVER_ACTION_LABEL[action]}
                title={MANEUVER_ACTION_LABEL[action]}
                onClick={() => {
                  if (groups[action].length === 1) {
                    onSubmit([groups[action][0].option_id]);
                  } else {
                    onStageManeuverAction?.(stagedManeuverAction === action ? null : action);
                  }
                }}
              >
                <OfficerActionIcon action={action === 'move' ? 'move' : action === 'arrest' ? 'arrest' : 'confiscate'} />
                <span className="decision-panel__officer-action-name">{MANEUVER_ACTION_LABEL[action]}</span>
              </button>
            ))}
          {decision.can_pass && (
            <button disabled={submitting} onClick={() => onSubmit([])}>
              Fine
            </button>
          )}
        </div>
        {stagedManeuverAction && (
          <p>Scegli il bersaglio sul tabellone.</p>
        )}
      </div>
    );
  }

  if (decision.decision_type === 'spend_link_for_extra_action') {
    if (compactOptional) return (
      <div className={guidanceInCorner ? 'human-controls__guidance' : 'decision-panel'}>
        <h3>Scegli un gancio da usare</h3>
      </div>
    );
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Vuoi spendere un Gancio per un'azione extra?</h3>
        {decision.options.length > 0 && <p>Clicca un Gancio illuminato sul tabellone, oppure salta.</p>}
        <div className="decision-panel__quick-buttons">
          <button disabled={submitting} onClick={() => onSubmit([])}>
            Salta
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_brawl_link_evolution') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Vuoi far evolvere un Criminale in Link?</h3>
        {decision.options.length > 0 && <p>Clicca una pedina illuminata sul tabellone, oppure passa.</p>}
        <div className="decision-panel__quick-buttons">
          <button disabled={submitting} onClick={() => onSubmit([])}>
            Passa
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_brawl_relocation_destination') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Dove va il Criminale sconfitto?</h3>
        {decision.options.length > 0 ? (
          <p>Clicca un Quartiere non ancora rivelato sul tabellone.</p>
        ) : (
          <div className="decision-panel__quick-buttons">
            <button disabled={submitting} onClick={() => onSubmit([])}>
              Passa
            </button>
          </div>
        )}
      </div>
    );
  }

  if (decision.decision_type === 'choose_job_reward') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Scegli il premio del Job</h3>
        <p>Clicca una colonna libera illuminata sul tabellone.</p>
      </div>
    );
  }

  if (decision.decision_type === 'choose_skill_to_discard') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Hai già 3 Skill: quale scarti per prendere quella nuova?</h3>
        <div className="decision-panel__skill-discard-options">
          {decision.options.map((option) => {
            const skillId = String(option.payload.skill_id ?? '');
            return (
              <img
                key={option.option_id}
                src={skillAssetUrl(skillId)}
                alt={skillId}
                title={skillId}
                className="player-card__skill-icon decision-panel__skill-discard-icon"
                onClick={() => !submitting && onSubmit([option.option_id])}
              />
            );
          })}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_job_bonus_alternative') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Al posto del Gancio, scegli il bonus:</h3>
        <QuickButtons
          options={decision.options}
          render={(option) =>
            option.payload.bonus_type === 'money' ? '3$' : '2 Carte'
          }
          onSubmit={onSubmit}
          submitting={submitting}
        />
      </div>
    );
  }

  if (decision.decision_type === 'evolve_sale_link' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Vuoi evolvere in Link?</h3>
        <QuickButtons
          options={decision.options}
          render={(option) => {
            if (!option.payload.evolve) return 'No, grazie';
            // Card CONNECTION: one "yes" per Client, the Link may be of any of them.
            if (decision.options.filter((o) => o.payload.evolve).length > 1) {
              const contact = String(option.payload.contact_id ?? '');
              return `Link ${contact.charAt(0).toUpperCase()}${contact.slice(1)}`;
            }
            return 'Evolvi in Link';
          }}
          onSubmit={onSubmit}
          submitting={submitting}
        />
      </div>
    );
  }

  if (decision.decision_type === 'choose_brawl_loser_reward' && decision.options.length > 0) {
    // Every option of one decision targets the same loser; with several losers the
    // decision is asked once per loser, so name whose reward this is.
    return <BrawlRewardPanel key={decision.decision_id} decision={decision} onSubmit={onSubmit} submitting={submitting} />;
  }

  if (decision.decision_type === 'choose_raid_first_player' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick decision-panel--teams">
        <h3>Chi parte per primo nella Retata?</h3>
        {/* One button per gang, in its own colour, two per row. It is a regular
            quick-buttons group so the message shell places it in its button column. */}
        <div className="decision-panel__quick-buttons decision-panel__quick-buttons--teams">
          {decision.options.map((option) => {
            const playerId = option.payload.chosen_first_player_id as string;
            return (
              <button
                key={option.option_id}
                className={`decision-panel__team-button decision-panel__team-button--${playerColorForId(playerId)}`}
                disabled={submitting}
                onClick={() => onSubmit([option.option_id])}
              >
                {playerLabel(playerId)}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'stain_reputation_for_money') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Vuoi macchiare una REP per $5?</h3>
        <div className="decision-panel__quick-buttons">
          {decision.options.map((option) => (
            <button key={option.option_id} disabled={submitting} onClick={() => onSubmit([option.option_id])}>
              Sì, macchia
            </button>
          ))}
          <button disabled={submitting} onClick={() => onSubmit([])}>
            No
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'hand_discard') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Scarta {decision.min_selections} carte dalla mano</h3>
        <p>
          Clicca le carte da scartare nella mano in basso a destra ({selected.length}/
          {decision.min_selections}).
        </p>
        <div className="decision-panel__quick-buttons">
          <button data-bar-label="Conferma" disabled={!canSubmit} onClick={() => onSubmit(selected)}>
            Conferma
          </button>
        </div>
      </div>
    );
  }

  // Joining a launched Poker match (designer's request, 2026-10-02): just
  // two bar buttons instead of clicking a ring on the Gamble card on the
  // board. There is always exactly one option (the current match).
  if (decision.decision_type === 'place_poker_bet') {
    const betOption = decision.options[0];
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Partecipi alla partita a poker?</h3>
        <div className="decision-panel__quick-buttons">
          <button
            data-bar-label="Partecipa"
            disabled={submitting || !betOption || decision.max_selections < 1}
            onClick={() => betOption && onSubmit([betOption.option_id])}
          >
            Partecipa
          </button>
          <button data-bar-label="Passa" disabled={submitting} onClick={() => onSubmit([])}>
            Passa
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'play_brawl_card') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Vuoi giocare una carta nella Rissa?</h3>
        {decision.options.length > 0 && <p>Clicca una carta nella mano in basso a destra, oppure passa.</p>}
        <div className="decision-panel__quick-buttons">
          <button disabled={submitting} onClick={() => onSubmit([])}>
            Passa
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'launch_poker') {
    // Nothing eligible to actually launch with (no matching Gamble card
    // in hand right now) — nothing for a "Gioca!" button to do, so this
    // stays the old, easy-to-ignore inline prompt instead of interrupting
    // with a popup over a choice that isn't really there.
    if (decision.options.length === 0) {
      return (
        <div className="decision-panel decision-panel--quick">
          <h3>Vuoi lanciare un Poker?</h3>
          <div className="decision-panel__quick-buttons">
            <button disabled={submitting} onClick={() => onSubmit([])}>
              Passa
            </button>
          </div>
        </div>
      );
    }
    // A real, blocking popup instead (game designer, 2026-09-26: "vorrei
    // che prima di risolvere il poker uscisse un popup che mi dicesse
    // 'Partita a poker?' e io la avvio con un tasto 'Gioca!'") — reuses
    // OutcomeModal's own overlay/card shell for visual consistency with
    // every other blocking popup already in the game. Usually exactly one
    // eligible Gamble card (one big "Gioca!"); the Preti-3 Skill can make
    // more than one match at once, so each gets its own card + button
    // rather than guessing which one "Gioca!" alone would mean.
    return (
      <div className="outcome-modal-overlay">
        <div className="outcome-modal launch-poker-modal" role="dialog" aria-modal="true" aria-label="Lancia un Poker">
          <h3>Partita a poker?</h3>
          <div className="launch-poker-modal__cards">
            {decision.options.map((option) => {
              const cardId = option.payload.card_id as string;
              return (
                <button
                  key={option.option_id}
                  className="launch-poker-modal__card-button"
                  disabled={submitting}
                  onClick={() => onSubmit([option.option_id])}
                >
                  <img src={cardAssetUrl(cardId)} alt={cardId} className="launch-poker-modal__card-img" />
                  <span>Gioca!</span>
                </button>
              );
            })}
          </div>
          <button
            className="launch-poker-modal__decline"
            disabled={submitting}
            onClick={() => onSubmit([])}
          >
            No, grazie
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'play_customer_card_boost') {
    return (
      <div className="outcome-modal-overlay">
        <div className="outcome-modal launch-poker-modal" role="dialog" aria-modal="true" aria-label="Potenzia l'azione">
          <div className="launch-poker-modal__cards">
            {decision.options.map((option) => {
              const cardId = option.payload.card_id as string;
              return (
                <button
                  key={option.option_id}
                  className="launch-poker-modal__card-button"
                  disabled={submitting}
                  aria-label={`Usa ${cardId} per potenziare l'azione`}
                  onClick={() => onSubmit([option.option_id])}
                >
                  <img src={cardAssetUrl(cardId)} alt={cardId} className="launch-poker-modal__card-img" />
                </button>
              );
            })}
          </div>
          <button className="launch-poker-modal__decline" disabled={submitting} onClick={() => onSubmit([])}>
            No, grazie
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'play_poker_card') {
    // §A10 Preti-1 lets a bettor reveal 2 cards instead of 1
    // (max_selections becomes 2) — the single-card case still submits
    // the instant a card is clicked (HandDrawer), but 2 cards need an
    // explicit Confirm, same pattern as hand_discard.
    if (decision.max_selections > 1) {
      return (
        <div className="decision-panel decision-panel--quick">
          <h3>Scegli fino a {decision.max_selections} carte da rivelare per il Poker</h3>
          <p>
            Clicca le carte nella mano in basso a destra ({selected.length}/
            {decision.max_selections}).
          </p>
          <div className="decision-panel__quick-buttons">
            <button data-bar-label="Conferma" disabled={!canSubmit} onClick={() => onSubmit(selected)}>
              Conferma
            </button>
          </div>
        </div>
      );
    }
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Scegli la carta da rivelare per il Poker</h3>
        <p>Clicca una carta nella mano in basso a destra.</p>
      </div>
    );
  }

  if (decision.decision_type === 'choose_poker_symbols') {
    // §A10 Preti-1's second step: no standalone art exists for the 5
    // Poker symbol colors (the flower icon only ever appears printed on
    // a customer card), so each of the 4 revealed instances is a plain
    // colored dot — click to toggle, exactly 2 must end up selected.
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Scegli 2 simboli tra quelli rivelati</h3>
        <p>
          Clicca 2 simboli ({selected.length}/{decision.max_selections}).
        </p>
        <ul className="decision-panel__symbols">
          {decision.options.map((option) => {
            const symbol = String(option.payload.symbol ?? '');
            const isSelected = selected.includes(option.option_id);
            return (
              <li key={option.option_id}>
                <button
                  type="button"
                  className={
                    'decision-panel__symbol-dot' +
                    (isSelected ? ' decision-panel__symbol-dot--selected' : '')
                  }
                  style={{ backgroundColor: POKER_SYMBOL_COLOR[symbol] ?? '#495057' }}
                  title={POKER_SYMBOL_LABEL[symbol] ?? symbol}
                  aria-label={POKER_SYMBOL_LABEL[symbol] ?? symbol}
                  disabled={submitting}
                  onClick={() => onToggle(option.option_id)}
                />
              </li>
            );
          })}
        </ul>
        <div className="decision-panel__quick-buttons">
          <button data-bar-label="Conferma" disabled={!canSubmit} onClick={() => onSubmit(selected)}>
            Conferma
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_reinforce_discard') {
    // Cards "REINFORCE": discard one Dope from the Covo and place as many
    // Criminals as its current price. The backend only offers the types
    // actually held, so each button is one of those — icon + that number.
    return (
      <div className="decision-panel decision-panel--quick">
        <div className={guidanceInCorner ? 'human-controls__guidance' : undefined}>
          <h3>Quale Merce scarti?</h3>
          <p>Piazzi tanti Criminali quanto il suo prezzo (il numero sul pulsante).</p>
        </div>
        <div className="decision-panel__quick-buttons">
          {decision.options.map((option) => {
            const dopeType = String(option.payload.dope_type);
            const price = view.current_price_by_dope_type[dopeType];
            return (
              <button
                key={option.option_id}
                className="decision-panel__dope-button"
                disabled={submitting}
                title={`Scarta ${dopeType}: piazzi ${price} Criminali`}
                onClick={() => onSubmit([option.option_id])}
              >
                <img src={DOPE_ASSET[dopeType]} alt={dopeType} />
                <span>{price}</span>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_marketing_card' ||
    (compactOptional && decision.decision_type === 'play_marketing_card' && marketingCardOpenedFor !== decision.decision_id)) {
    const cardOptions = [...new Map(decision.options.map((option) => [String(option.payload.card_id), option])).values()];
    return (
      <div className="outcome-modal-overlay">
        <div className="outcome-modal launch-poker-modal" role="dialog" aria-modal="true" aria-label="Carte Marketing">
          <div className="launch-poker-modal__cards">
            {cardOptions.map((option) => {
              const cardId = String(option.payload.card_id);
              return <button key={cardId} className="launch-poker-modal__card-button" disabled={submitting}
                aria-label={`Usa ${cardId} per Marketing`}
                onClick={() => {
                  if (decision.decision_type === 'choose_marketing_card') onSubmit([option.option_id]);
                  else setMarketingCardOpenedFor(decision.decision_id);
                }}>
                <img src={cardAssetUrl(cardId)} alt={cardId} className="launch-poker-modal__card-img" />
              </button>;
            })}
          </div>
          <button className="launch-poker-modal__decline" disabled={submitting} onClick={() => onSubmit([])}>
            No, grazie
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type in BOARD_PACKAGE_HINT) {
    const followup = CARD_FOLLOWUP_TEXT[String(decision.context?.card_followup ?? '')];
    return (
      <div className="decision-panel decision-panel--quick">
        <div className={guidanceInCorner ? 'human-controls__guidance' : undefined}>
        <h3>{followup?.title ?? BOARD_PACKAGE_LABEL[decision.decision_type] ?? decision.decision_type}</h3>
        <p>
          {followup?.hint ?? BOARD_PACKAGE_HINT[decision.decision_type]}
        </p>
        </div>
        <div className="decision-panel__quick-buttons">
          <button data-bar-label={buttonLabel} disabled={!canSubmit} onClick={() => onSubmit(selected)}>
            {buttonLabel}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="decision-panel">
      <h3>{decision.prompt_key}</h3>
      {decision.options.length === 0 ? (
        <p>Nessuna opzione disponibile.</p>
      ) : (
        <ul className="decision-panel__options">
          {decision.options.map((option) => (
            <li key={option.option_id}>
              <label>
                <input
                  type={decision.max_selections === 1 ? 'radio' : 'checkbox'}
                  name="decision-option"
                  checked={selected.includes(option.option_id)}
                  onChange={() => onToggle(option.option_id)}
                />
                {option.label_key} {JSON.stringify(option.payload)}
              </label>
            </li>
          ))}
        </ul>
      )}
      <p>
        Seleziona da {decision.min_selections} a {decision.max_selections} opzioni.
      </p>
      <button disabled={!canSubmit} onClick={() => onSubmit(selected)}>
        {buttonLabel}
      </button>
    </div>
  );
}
