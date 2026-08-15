import { DOPE_ASSET, pawnAssetForPlayer, playerColorForId, skillAssetUrl } from '../assets';
import type { GameViewResponse } from '../types';

interface PlayerStripProps {
  view: GameViewResponse;
}

// Money and REP are already shown on the board itself (money-track token,
// Job-grid REP tokens) — the sidebar box only needs what isn't visible
// there, including how many Cops/Feds this player has bought.
function officersOwnedCount(view: GameViewResponse, playerId: string): number {
  return view.officers.filter((o) => o.owner_player_id === playerId).length;
}

export function PlayerStrip({ view }: PlayerStripProps) {
  return (
    <div className="player-strip">
      {view.players.map((p) => (
        <div
          key={p.player_id}
          className={
            'player-card' +
            ` player-card--${playerColorForId(p.player_id)}` +
            (p.player_id === view.current_player_id ? ' player-card--active' : '')
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
          <div className="player-card__stats">
            <span>Mano: {p.hand_card_count}</span>
            <span>Grit: {p.available_grit_values.join(', ') || '-'}</span>
            <span>Chip poker: {p.poker_chip_count}</span>
            <span>Cops: {officersOwnedCount(view, p.player_id)}</span>
          </div>
          <div className="player-card__dope">
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
