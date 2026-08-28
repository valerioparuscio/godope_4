import { playerTeamNameForId, POKER_SYMBOL_COLOR, POKER_SYMBOL_LABEL, skillAssetUrl } from '../assets';
import type { DecisionOptionResponse, GameViewResponse, PendingDecisionResponse } from '../types';

interface DecisionPanelProps {
  decision: PendingDecisionResponse;
  view: GameViewResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
  stagedCorruptionAction?: string | null;
  onStageCorruptionAction?: (action: string | null) => void;
}

function playerLabel(playerId: string): string {
  return playerTeamNameForId(playerId);
}

const CORRUPTION_ACTION_LABEL: Record<string, string> = {
  move: 'Sposta',
  arrest: 'Arresta',
  confiscate: 'Requisisci',
};

const ACTION_TYPE_LABEL: Record<string, string> = {
  place_criminal: 'Piazza',
  move_criminal: 'Sposta',
  buy_dope: 'Acquista',
  sell_dope: 'Vendi',
  corrupt_officer: 'Corrompi',
  buy_officer: 'Compra',
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
  'corrupt_officer',
  'buy_officer',
] as const;

// Package-select decisions answered entirely by clicking targets on the
// board (BoardView's own dedicated components or its generic
// BoardHighlights) — this panel only ever needs a heading, a one-line
// hint, and the Confirm/Passa button that already existed at the bottom
// of the plain fallback, never the raw option list with its
// JSON.stringify(payload) dump.
const BOARD_PACKAGE_LABEL: Record<string, string> = {
  ...ACTION_TYPE_LABEL,
  place_poker_bet: 'Piazza la puntata',
  play_marketing_card: 'Gioca Marketing',
};

const BOARD_PACKAGE_HINT: Record<string, string> = {
  place_criminal: 'Clicca un Quartiere illuminato sul tabellone.',
  move_criminal: 'Clicca un Criminale illuminato, poi la sua destinazione.',
  buy_dope: 'Clicca una pedina illuminata sul tabellone per comprare.',
  sell_dope: 'Clicca una pedina illuminata sul tabellone per vendere.',
  corrupt_officer: 'Clicca un Cop/Fed illuminato sul tabellone.',
  buy_officer: 'Clicca un Cop/Fed illuminato sul tabellone.',
  place_poker_bet: 'Clicca una carta Gamble illuminata sul tabellone.',
  play_marketing_card: 'Clicca un gettone prezzo illuminato sul tabellone.',
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
  selected,
  onToggle,
  onSubmit,
  submitting,
  stagedCorruptionAction,
  onStageCorruptionAction,
}: DecisionPanelProps) {
  const isValidSelection =
    selected.length >= decision.min_selections && selected.length <= decision.max_selections;
  const isPass = selected.length === 0 && decision.can_pass;
  const canSubmit = (isValidSelection || isPass) && !submitting;
  const buttonLabel = selected.length === 0 && decision.can_pass ? 'Passa' : 'Conferma';

  if (decision.decision_type === 'choose_grit_action') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Quanta Grinta vuoi usare?</h3>
        {decision.options.length > 0 ? (
          <QuickButtons
            options={decision.options}
            render={(option) => String(option.payload.grit_value)}
            onSubmit={onSubmit}
            submitting={submitting}
          />
        ) : (
          decision.can_pass && (
            <div className="decision-panel__quick-buttons">
              <button disabled={submitting} onClick={() => onSubmit([])}>
                Passa
              </button>
            </div>
          )
        )}
      </div>
    );
  }

  if (decision.decision_type === 'choose_action_type') {
    const optionByActionType = new Map(
      decision.options.map((option) => [option.payload.action_type as string, option]),
    );
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Che azione fai?</h3>
        {decision.options.length > 0 ? (
          <div className="decision-panel__quick-buttons">
            {ACTION_TYPE_ORDER.map((actionType) => {
              const option = optionByActionType.get(actionType);
              return (
                <button
                  key={actionType}
                  disabled={!option || submitting}
                  onClick={() => option && onSubmit([option.option_id])}
                >
                  {ACTION_TYPE_LABEL[actionType]}
                </button>
              );
            })}
          </div>
        ) : (
          decision.can_pass && (
            <div className="decision-panel__quick-buttons">
              <button disabled={submitting} onClick={() => onSubmit([])}>
                Passa
              </button>
            </div>
          )
        )}
      </div>
    );
  }

  if (decision.decision_type === 'corruption_action') {
    const groups: Record<string, DecisionOptionResponse[]> = { move: [], arrest: [], confiscate: [] };
    for (const option of decision.options) {
      const action = option.payload.action as string;
      (groups[action] ??= []).push(option);
    }
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Che azione fa l'ufficiale corrotto?</h3>
        <div className="decision-panel__quick-buttons">
          {(['move', 'arrest', 'confiscate'] as const)
            .filter((action) => groups[action].length > 0)
            .map((action) => (
              <button
                key={action}
                disabled={submitting}
                className={stagedCorruptionAction === action ? 'decision-panel__quick-buttons--staged' : undefined}
                onClick={() => {
                  if (groups[action].length === 1) {
                    onSubmit([groups[action][0].option_id]);
                  } else {
                    onStageCorruptionAction?.(stagedCorruptionAction === action ? null : action);
                  }
                }}
              >
                {CORRUPTION_ACTION_LABEL[action]}
              </button>
            ))}
          {decision.can_pass && (
            <button disabled={submitting} onClick={() => onSubmit([])}>
              Fine
            </button>
          )}
        </div>
        {stagedCorruptionAction && (
          <p>Scegli il bersaglio sul tabellone.</p>
        )}
      </div>
    );
  }

  if (decision.decision_type === 'spend_link_for_extra_action') {
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

  if (decision.decision_type === 'evolve_sale_link' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Vuoi evolvere il Criminale in Link?</h3>
        <QuickButtons
          options={decision.options}
          render={(option) => (option.payload.evolve ? 'Sì' : 'No')}
          onSubmit={onSubmit}
          submitting={submitting}
        />
      </div>
    );
  }

  if (decision.decision_type === 'choose_brawl_loser_reward' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Che ricompensa vuoi?</h3>
        <QuickButtons
          options={decision.options}
          render={(option) => (option.payload.reward_type === 'money' ? 'Soldi' : 'Carta')}
          onSubmit={onSubmit}
          submitting={submitting}
        />
      </div>
    );
  }

  if (decision.decision_type === 'choose_raid_first_player' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Chi parte per primo nella Retata?</h3>
        <QuickButtons
          options={decision.options}
          render={(option) => playerLabel(option.payload.chosen_first_player_id as string)}
          onSubmit={onSubmit}
          submitting={submitting}
        />
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

  if (decision.decision_type === 'assign_brawl_guns' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>A chi assegni le Pistole?</h3>
        <QuickButtons
          options={decision.options}
          render={(option) => playerLabel(option.payload.target_player_id as string)}
          onSubmit={onSubmit}
          submitting={submitting}
        />
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
          <button disabled={!canSubmit} onClick={() => onSubmit(selected)}>
            Conferma
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
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Vuoi lanciare un Poker?</h3>
        {decision.options.length > 0 && <p>Clicca una carta Gamble nella mano in basso a destra, oppure passa.</p>}
        <div className="decision-panel__quick-buttons">
          <button disabled={submitting} onClick={() => onSubmit([])}>
            Passa
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
            <button disabled={!canSubmit} onClick={() => onSubmit(selected)}>
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
          <button disabled={!canSubmit} onClick={() => onSubmit(selected)}>
            Conferma
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type === 'choose_marketing_card') {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Con quale carta fai Marketing?</h3>
        <p>Clicca una carta nella mano in basso a destra, oppure passa.</p>
        <div className="decision-panel__quick-buttons">
          <button disabled={submitting} onClick={() => onSubmit([])}>
            Passa
          </button>
        </div>
      </div>
    );
  }

  if (decision.decision_type in BOARD_PACKAGE_HINT) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>{BOARD_PACKAGE_LABEL[decision.decision_type] ?? decision.decision_type}</h3>
        <p>
          {BOARD_PACKAGE_HINT[decision.decision_type]}
          {decision.max_selections > 1 && ` (${selected.length}/${decision.max_selections})`}
        </p>
        <div className="decision-panel__quick-buttons">
          <button disabled={!canSubmit} onClick={() => onSubmit(selected)}>
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
