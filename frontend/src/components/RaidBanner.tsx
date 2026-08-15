import { RAID_ASSET } from '../assets';
import type { GameViewResponse } from '../types';

interface RaidBannerProps {
  view: GameViewResponse;
}

export function RaidBanner({ view }: RaidBannerProps) {
  return (
    <div className="raid-banner">
      {view.raid_card_id ? (
        <>
          <img
            src={RAID_ASSET[view.raid_card_id]}
            alt={view.raid_card_id}
            className="raid-banner__image"
          />
          <span className="raid-banner__text">
            Occorrenze perse: {view.raid_lost_occurrences_count}
            {view.last_raid_outcome && (
              <>
                {' · '}Ultima Retata ({view.last_raid_outcome.raid_card_id}): vince{' '}
                {view.last_raid_outcome.escaping_team.join(' + ')} — macchiati{' '}
                {view.last_raid_outcome.caught_team.join(' + ')}
              </>
            )}
          </span>
        </>
      ) : (
        <span className="raid-banner__text">Nessuna Retata rivelata.</span>
      )}
    </div>
  );
}
