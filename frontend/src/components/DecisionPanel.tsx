import type { DecisionOptionResponse, PendingDecisionResponse } from '../types';

interface DecisionPanelProps {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
  stagedCorruptionAction?: string | null;
  onStageCorruptionAction?: (action: string | null) => void;
}

const CORRUPTION_ACTION_LABEL: Record<string, string> = {
  move: 'Sposta',
  arrest: 'Arresta',
  confiscate: 'Requisisci',
};

const ACTION_TYPE_LABEL: Record<string, string> = {
  place_criminal: 'Piazza Criminale',
  move_criminal: 'Sposta Criminale',
  buy_dope: 'Compra Dope',
  sell_dope: 'Vendi Dope',
  corrupt_officer: 'Corrompi Cop/Fed',
  buy_officer: 'Compra Cop/Fed',
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

  if (decision.decision_type === 'choose_grit_action' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Quanta Grinta vuoi usare?</h3>
        <QuickButtons
          options={decision.options}
          render={(option) => String(option.payload.grit_value)}
          onSubmit={onSubmit}
          submitting={submitting}
        />
      </div>
    );
  }

  if (decision.decision_type === 'choose_action_type' && decision.options.length > 0) {
    return (
      <div className="decision-panel decision-panel--quick">
        <h3>Che azione fai?</h3>
        <QuickButtons
          options={decision.options}
          render={(option) => ACTION_TYPE_LABEL[option.payload.action_type as string] ?? String(option.payload.action_type)}
          onSubmit={onSubmit}
          submitting={submitting}
        />
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
