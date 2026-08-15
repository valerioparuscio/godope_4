import { JOB_ASSET } from '../assets';
import type { GameViewResponse } from '../types';

interface JobActiveStripProps {
  view: GameViewResponse;
}

// One compact row of every player's revealed Jobs (up to 3 tiers x 4
// players = 12 cards), right under the player boards — moved out of
// BoardSummary and shrunk so all 12 fit on a single row (2026-08-15).
export function JobActiveStrip({ view }: JobActiveStripProps) {
  return (
    <div className="job-active-strip">
      {Object.entries(view.job_progress_by_player).map(([playerId, progress]) => (
        <div key={playerId} className="job-active-strip__group">
          <span className="job-active-strip__player-label">{playerId}</span>
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
      ))}
    </div>
  );
}
