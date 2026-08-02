import type { GameViewResponse } from '../types';

interface PlayerStripProps {
  view: GameViewResponse;
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
            {p.player_id === view.current_player_id ? '▶ ' : ''}
            {p.display_name} ({p.controller_type})
          </div>
          <div>${p.money}</div>
          <div>Mano: {p.hand_card_count}</div>
          <div>Grit rimasti: {p.available_grit_values.join(', ') || '-'}</div>
          <div>Chip poker: {p.poker_chip_count}</div>
          <div>Skill: {p.skill_ids.length}</div>
        </div>
      ))}
    </div>
  );
}
