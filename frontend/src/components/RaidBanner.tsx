import { RAID_ASSET } from '../assets';
import type { GameViewResponse } from '../types';

interface RaidBannerProps {
  view: GameViewResponse;
}

// The "occorrenze perse"/"ultima Retata" recap text this banner used to
// print inline is gone (designer's request, 2026-08-16: "non serve a
// niente") — how the last Raid/Brawl/Poker went is now a dismissible
// popup instead (see ResultPopup), driven by the same view.last_raid_outcome
// this banner used to render itself.
export function RaidBanner({ view }: RaidBannerProps) {
  return (
    <div className="raid-banner">
      {view.raid_card_id ? (
        <img
          src={RAID_ASSET[view.raid_card_id]}
          alt={view.raid_card_id}
          className="raid-banner__image"
        />
      ) : (
        <span className="raid-banner__text">Nessuna Retata rivelata.</span>
      )}
    </div>
  );
}
