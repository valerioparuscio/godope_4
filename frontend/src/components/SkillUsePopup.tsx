import { useEffect } from 'react';
import { playerColorLabelForId, skillAssetUrl } from '../assets';
import type { GameEventResponse } from '../types';

export interface SkillUse {
  key: string;
  skillId: string;
  playerId: string;
}

// Pulled out of a raw event batch (the human's own dispatch, or one
// bot's narrated segment) wherever it's discovered — `SkillEffectApplied`
// only ever fires from `rules/skills.py`'s own resolution-time call
// sites (backend), never merely because a player owns a Skill.
export function skillUsesFromEvents(events: GameEventResponse[]): SkillUse[] {
  return events
    .filter((e) => e.event_type === 'SkillEffectApplied')
    .map((e) => ({
      key: e.event_id,
      skillId: e.skill_id as string,
      playerId: e.player_id as string,
    }));
}

const SKILL_POPUP_DURATION_MS = 1000;

// A 1-second popup showing the used Skill's own card art (designer's
// request, 2026-08-22: "vorrei che nel momento in cui una skill viene
// usata, esca un pop up per 1 secondo con la carta della skill") —
// queued from both the human's own move and every bot's narrated turn.
// Deliberately decoupled from TurnPlayback's own beat timing (which
// would need a whole new beat kind for a purely decorative flourish): it
// just drains its own queue on a fixed 1s cadence in the background, so
// a bot's skill popup can land slightly out of step with that bot's own
// narrated text beat.
export function SkillUsePopup({
  queue,
  onShown,
}: {
  queue: SkillUse[];
  onShown: (key: string) => void;
}) {
  const current = queue[0];

  useEffect(() => {
    if (!current) return;
    const timer = setTimeout(() => onShown(current.key), SKILL_POPUP_DURATION_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.key]);

  if (!current) return null;
  const url = skillAssetUrl(current.skillId);
  if (!url) return null;

  return (
    <div className="skill-use-popup" key={current.key}>
      <img src={url} alt={current.skillId} className="skill-use-popup__card" />
      <div className="skill-use-popup__label">{playerColorLabelForId(current.playerId)}</div>
    </div>
  );
}
