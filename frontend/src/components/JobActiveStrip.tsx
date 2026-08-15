import { JOB_ASSET, playerColorForId } from '../assets';
import type { GameViewResponse } from '../types';

interface JobActiveStripProps {
  view: GameViewResponse;
}

// One compact row of every player's revealed Jobs (up to 3 tiers x 4
// players = 12 cards) — shares the top line with RaidBanner (designer's
// request, 2026-08-16), each player's group boxed in that player's own
// red/blu/green/yellow (assets/index.ts::playerColorForId, same
// convention as the sidebar player cards) and labeled by seat number
// 1-4, not the raw 0-indexed player_id.
export function JobActiveStrip({ view }: JobActiveStripProps) {
  return (
    <div className="job-active-strip">
      {Object.entries(view.job_progress_by_player).map(([playerId, progress]) => {
        const seatIndex = view.players.find((p) => p.player_id === playerId)?.seat_index ?? 0;
        return (
          <div
            key={playerId}
            className={`job-active-strip__group job-active-strip__group--${playerColorForId(playerId)}`}
          >
            <span className="job-active-strip__player-label">P{seatIndex + 1}</span>
            {Object.entries(progress.revealed_job_id_by_tier)
              .filter(([, jobId]) => jobId)
              .map(([tier, jobId]) => (
                <img
                  key={tier}
                  src={JOB_ASSET[jobId as string]}
                  alt={jobId as string}
                  title={`${playerId} · Tier ${tier}: ${jobId}`}
                  className="job-active-strip__card"
                />
              ))}
          </div>
        );
      })}
    </div>
  );
}
