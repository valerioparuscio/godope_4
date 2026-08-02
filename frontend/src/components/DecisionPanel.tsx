import { useEffect, useState } from 'react';
import type { PendingDecisionResponse } from '../types';

interface DecisionPanelProps {
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
  submitting: boolean;
}

export function DecisionPanel({ decision, onSubmit, submitting }: DecisionPanelProps) {
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    setSelected([]);
  }, [decision.decision_id]);

  function toggle(optionId: string) {
    setSelected((prev) => {
      if (prev.includes(optionId)) {
        return prev.filter((id) => id !== optionId);
      }
      if (decision.max_selections === 1) {
        return [optionId];
      }
      if (prev.length >= decision.max_selections) {
        return prev;
      }
      return [...prev, optionId];
    });
  }

  const isValidSelection =
    selected.length >= decision.min_selections && selected.length <= decision.max_selections;
  const isPass = selected.length === 0 && decision.can_pass;
  const canSubmit = (isValidSelection || isPass) && !submitting;
  const buttonLabel = selected.length === 0 && decision.can_pass ? 'Passa' : 'Conferma';

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
                  onChange={() => toggle(option.option_id)}
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
