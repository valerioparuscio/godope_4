import { actionTypeAssetUrl, GRIT_ICON } from '../assets';
import { t } from '../i18n';
import type { HumanActionPlan } from '../types';

const ACTIONS = [
  ['place_criminal', 'action.place_criminal'], ['move_criminal', 'action.move_criminal'],
  ['buy_dope', 'action.buy_dope'], ['sell_dope', 'action.sell_dope'],
  ['maneuver_officer', 'action.maneuver_officer'], ['corrupt_officer', 'action.corrupt_officer'],
] as const;

export function ActionChooser({ plan, disabled, onStage, onPass, action, onSelectAction, onSelectLink }: {
  plan: HumanActionPlan;
  disabled: boolean;
  onStage: (selections: string[][]) => void;
  onPass: () => void;
  action: string | null;
  onSelectAction: (action: string | null) => void;
  onSelectLink: () => void;
}) {
  const decision = plan.view.pending_decision!;
  const grit = plan.grit;
  const selectedGrit = plan.selected_grit;
  const linkAvailable = plan.optional.some((option) => option.kind === 'link');
  const options = selectedGrit !== null && grit
    ? grit.action_options[String(selectedGrit)] ?? []
    : grit ? Object.values(grit.action_options).flat() : decision.options;

  function chooseGrit(optionId: string, value: number) {
    if (!grit) return;
    const actionOption = grit.action_options[String(value)]?.find((option) => option.payload.action_type === action);
    onStage([...grit.prefix, [optionId], ...(actionOption ? [[actionOption.option_id]] : [])]);
  }

  return (
    <div className={'action-chooser' + (grit ? '' : ' action-chooser--actions-only')
      + (action ? ' action-chooser--action-picked' : '')}>
      {grit && <div className="action-chooser__box action-chooser__box--grit">
        <span className="action-chooser__label">{t('chooser.grit')}</span>
        <div className="decision-pill__options">
          {[1, 2, 3].map((value) => {
            const option = grit.decision.options.find((item) => Number(item.payload.grit_value) === value);
            const compatible = !action || grit.action_options[String(value)]?.some((item) => item.payload.action_type === action);
            return <button key={value} className="decision-pill__grit-button"
              disabled={disabled || !option || !compatible} aria-pressed={selectedGrit === value}
              aria-label={t('chooser.gritN', { n: value })}
              onClick={() => option && chooseGrit(option.option_id, value)}>
              <img src={GRIT_ICON[value]} alt="" className="grit-icon" />
            </button>;
          })}
        </div>
      </div>}
      {!action && (
        <button type="button" className="action-chooser__box action-chooser__box--link"
          disabled={disabled || !linkAvailable} onClick={onSelectLink}>
          <span className="action-chooser__label">{t('chooser.link')}</span>
          <span className="action-chooser__star" aria-hidden="true">✱</span>
        </button>
      )}
      <div className="action-chooser__box action-chooser__box--actions">
        <span className="action-chooser__label">{t('chooser.actions')}</span>
        <div className="decision-pill__options">
          {ACTIONS.map(([type, labelKey]) => {
            const label = t(labelKey);
            const option = options.find((item) => item.payload.action_type === type);
            return <button key={type} className="decision-pill__action-button" title={label} aria-label={label}
              disabled={disabled || !option} aria-pressed={action === type}
              onClick={() => {
                if (decision.decision_type === 'choose_action_type' && option) {
                  onStage([...plan.prefix, [option.option_id]]);
                } else onSelectAction(action === type ? null : type);
              }}>
              <img src={actionTypeAssetUrl(type)} alt="" data-action={type} /><span className="action-chooser__action-name">{label}</span></button>;
          })}
          {decision.can_pass && <button className="decision-pill__pass" disabled={disabled} onClick={onPass}>{t('common.pass')}</button>}
        </div>
      </div>
    </div>
  );
}
