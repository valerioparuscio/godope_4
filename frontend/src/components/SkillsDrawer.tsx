import { useState } from 'react';
import { skillAssetUrl } from '../assets';
import type { GameViewResponse } from '../types';

interface SkillsDrawerProps {
  view: GameViewResponse;
  humanPlayerId: string;
}

// Only the human's own Skills, sitting right above HandDrawer.tsx's own
// "Carte" toggle (designer's request, 2026-08-23: "togli i pulsanti
// skill dei bot, e metti quello del player human sopra il bottone delle
// carte, stessa dimensione") — replaces the per-player-card SKILLS(n)
// button PlayerStrip.tsx used to render for all 4 players. Reuses
// .hand-drawer__toggle verbatim for the button so the two stay pixel-
// identical in size without duplicating/drifting CSS values.
export function SkillsDrawer({ view, humanPlayerId }: SkillsDrawerProps) {
  const [open, setOpen] = useState(false);
  const skillIds = view.players.find((p) => p.player_id === humanPlayerId)?.skill_ids ?? [];

  return (
    <div className="skills-drawer">
      {open && (
        <div className="skills-drawer__panel">
          {skillIds.length === 0 ? (
            <p>Nessuna Skill.</p>
          ) : (
            <div className="player-card__skills">
              {skillIds.map((skillId) => (
                <img
                  key={skillId}
                  src={skillAssetUrl(skillId)}
                  alt={skillId}
                  title={skillId}
                  className="player-card__skill-icon"
                />
              ))}
            </div>
          )}
        </div>
      )}
      <button className="hand-drawer__toggle" onClick={() => setOpen((v) => !v)}>
        SKILLS ({skillIds.length}) {open ? '▾' : '▴'}
      </button>
    </div>
  );
}
