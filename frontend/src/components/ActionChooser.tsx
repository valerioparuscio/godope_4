import { actionTypeAssetUrl } from '../assets';
import type { HumanActionPlan } from '../types';

const ACTIONS = [
  ['place_criminal', 'Piazza'], ['move_criminal', 'Sposta'],
  ['buy_dope', 'Acquista'], ['sell_dope', 'Vendi'],
  ['corrupt_officer', 'Corrompi'], ['buy_officer', 'Compra'],
] as const;

export function ActionChooser({ plan, disabled, onStage, onPass, action, onSelectAction }: {
  plan: HumanActionPlan;
  disabled: boolean;
  onStage: (selections: string[][]) => void;
  onPass: () => void;
  action: string | null;
  onSelectAction: (action: string | null) => void;
}) {
  const decision = plan.view.pending_decision!;
  const grit = plan.grit;
  const selectedGrit = plan.selected_grit;
  const options = selectedGrit !== null && grit
    ? grit.action_options[String(selectedGrit)] ?? []
    : grit ? Object.values(grit.action_options).flat() : decision.options;

  function chooseGrit(optionId: string, value: number) {
    if (!grit) return;
    const actionOption = grit.action_options[String(value)]?.find((option) => option.payload.action_type === action);
    onStage([...grit.prefix, [optionId], ...(actionOption ? [[actionOption.option_id]] : [])]);
  }

  return (
    <div className="action-chooser">
      <div className="action-chooser__box action-chooser__box--grit">
        <span className="action-chooser__label">GRINTA</span>
        <div className="decision-pill__options">
          {grit ? grit.decision.options.map((option) => {
            const value = Number(option.payload.grit_value);
            const compatible = !action || grit.action_options[String(value)]?.some((item) => item.payload.action_type === action);
            return <button key={option.option_id} className="decision-pill__grit-button"
              disabled={disabled || !compatible} aria-pressed={selectedGrit === value}
              onClick={() => chooseGrit(option.option_id, value)}>{value}</button>;
          }) : <span className="action-chooser__extra">Gancio</span>}
        </div>
      </div>
      <div className="action-chooser__box action-chooser__box--actions">
        <span className="action-chooser__label">AZIONI</span>
        <div className="decision-pill__options">
          {ACTIONS.map(([type, label]) => {
            const option = options.find((item) => item.payload.action_type === type);
            return <button key={type} className="decision-pill__action-button" title={label} aria-label={label}
              disabled={disabled || !option} aria-pressed={action === type}
              onClick={() => {
                if (decision.decision_type === 'choose_action_type' && option) {
                  onStage([...plan.prefix, [option.option_id]]);
                } else onSelectAction(action === type ? null : type);
              }}><img src={actionTypeAssetUrl(type)} alt="" /><span className="action-chooser__action-name">{label}</span></button>;
          })}
          {decision.can_pass && <button className="decision-pill__pass" disabled={disabled} onClick={onPass}>Passa</button>}
        </div>
      </div>
    </div>
  );
}
