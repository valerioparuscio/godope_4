import type { DecisionOptionResponse, PendingDecisionResponse } from '../types';

interface DecisionPanelProps {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
}

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

export function DecisionPanel({ decision, selected, onToggle, onSubmit, submitting }: DecisionPanelProps) {
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
