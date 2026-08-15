import { RAID_ASSET } from '../assets';
import type { GameViewResponse } from '../types';

interface BoardSummaryProps {
  view: GameViewResponse;
}

export function BoardSummary({ view }: BoardSummaryProps) {
  return (
    <div className="board-summary">
      <section>
        <h3>Retata</h3>
        {view.raid_card_id ? (
          <div className="raid-card">
            <img
              src={RAID_ASSET[view.raid_card_id]}
              alt={view.raid_card_id}
              className="raid-card__image"
            />
            <p>Occorrenze perse: {view.raid_lost_occurrences_count}</p>
          </div>
        ) : (
          <p>Nessuna Retata rivelata.</p>
        )}
        {view.last_raid_outcome && (
          <p className="raid-outcome">
            Ultima Retata ({view.last_raid_outcome.raid_card_id}): vince{' '}
            {view.last_raid_outcome.escaping_team.join(' + ')} — macchiati{' '}
            {view.last_raid_outcome.caught_team.join(' + ')}
          </p>
        )}
      </section>
    </div>
  );
}
