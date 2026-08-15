import { DOPE_ASSET, pawnAssetForPlayer, skillAssetUrl } from '../assets';
import type { GameViewResponse } from '../types';

interface PlayerStripProps {
  view: GameViewResponse;
}

// A player's REP total (2 points per clean token, 1 per stained — RULES_
// CANONICAL.md SS D6) isn't sent as its own field, but it's exactly the
// job_board cells claimed by that player, which the view already has.
function repPoints(view: GameViewResponse, playerId: string): { clean: number; stained: number } {
  let clean = 0;
  let stained = 0;
  for (const cell of view.job_board) {
    if (cell.player_id !== playerId) continue;
    if (cell.stained) stained += 1;
    else clean += 1;
  }
  return { clean, stained };
}

export function PlayerStrip({ view }: PlayerStripProps) {
  return (
    <div className="player-strip">
      {view.players.map((p) => (
        <div
          key={p.player_id}
          className={
            'player-card' + (p.player_id === view.current_player_id ? ' player-card--active' : '')
          }
        >
          <div className="player-card__name">
            <img
              src={pawnAssetForPlayer(p.player_id)}
              alt=""
              className="inline-icon"
            />{' '}
            {p.player_id === view.current_player_id ? '▶ ' : ''}
            {p.display_name} ({p.controller_type})
          </div>
          {p.skill_ids.length > 0 && (
            <div className="player-card__skills">
              {p.skill_ids.map((skillId) => (
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
          <div>${p.money}</div>
          {(() => {
            const { clean, stained } = repPoints(view, p.player_id);
            return (
              <div>
                REP: {clean * 2 + stained} ({clean} pulite, {stained} macchiate)
              </div>
            );
          })()}
          <div>Mano: {p.hand_card_count}</div>
          <div>Grit rimasti: {p.available_grit_values.join(', ') || '-'}</div>
          <div>Chip poker: {p.poker_chip_count}</div>
          <div className="player-card__dope">
            Merci nel Covo:{' '}
            {Object.entries(p.dope_counts).filter(([, count]) => count > 0).length === 0 ? (
              '-'
            ) : (
              Object.entries(p.dope_counts)
                .filter(([, count]) => count > 0)
                .map(([dopeType, count]) => (
                  <span key={dopeType} className="player-card__dope-item">
                    <img src={DOPE_ASSET[dopeType]} alt={dopeType} className="inline-icon" />
                    {count}
                  </span>
                ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
