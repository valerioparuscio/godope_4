import { t, tDyn } from './i18n';
import type { GameEventResponse } from './types';

export interface Notice {
  key: string;
  text: string;
}

// What the human's own move says in words about a step of a card that could not be done
// (`CardEffectSkipped`, backend rules/move_followups.py): the step used to vanish with no word at
// all and the card looked broken (game designer, 2026-11-16: "non puoi piazzare perché non hai
// soldi"). Only the player's own events: a bot's skipped step is no news to the human.
export function noticesFromEvents(events: GameEventResponse[], playerId: string): Notice[] {
  return events
    .filter((e) => e.event_type === 'CardEffectSkipped' && e.player_id === playerId)
    .map((e) => ({
      key: e.event_id,
      text: t('notice.cardSkipped', {
        effect: tDyn(`notice.effect.${String(e.effect)}`) ?? t('notice.effect.unknown'),
        reason: tDyn(`notice.reason.${String(e.reason)}`) ?? t('notice.reason.no_target'),
      }),
    }));
}
