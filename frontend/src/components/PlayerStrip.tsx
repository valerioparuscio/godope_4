import {
  DOPE_ASSET,
  JOB_ASSET,
  OFFICER_ASSET,
  playerColorForId,
  playerTeamNameForId,
  pokerChipAssetForPlayer,
} from '../assets';
import type { GameViewResponse, PendingDecisionResponse } from '../types';

interface PlayerStripProps {
  view: GameViewResponse;
  decision?: PendingDecisionResponse | null;
  selected?: string[];
  onToggle?: (optionId: string) => void;
}

// Money and REP are already shown on the board itself (money-track token,
// Job-grid REP tokens) — the sidebar box only needs what isn't visible
// there, including how many Cops/Feds this player has bought.
function officersOwnedCount(view: GameViewResponse, playerId: string): number {
  return view.officers.filter((o) => o.owner_player_id === playerId).length;
}

// Ordered starting from this *game-turn*'s first player, then the rest in
// seat order — re-anchored only at the start of a turn or when a new
// first player is chosen (Raid Link tie-break), not on every single
// player-to-player handoff within a turn (designer's clarification,
// 2026-08-16: "i player panel si riarrangiano all'inizio turno e quando
// si sceglie il nuovo primo giocatore" — corrects an earlier
// `current_player_id`-based version, which reordered on every player
// switch instead). `first_player_id` is already public per-turn state
// (`GameState.first_player_id`, threaded through `PlayerGameView` and
// `GameViewResponse` untouched by this component).
function playersInTurnOrder(view: GameViewResponse) {
  const bySeat = [...view.players].sort((a, b) => a.seat_index - b.seat_index);
  const firstIndex = bySeat.findIndex((p) => p.player_id === view.first_player_id);
  if (firstIndex <= 0) return bySeat;
  return [...bySeat.slice(firstIndex), ...bySeat.slice(0, firstIndex)];
}

// A `buy_officer` option whose target officer is sitting in *another
// player's* Covo (`destination` set — see legal_actions.py::
// _buy_officer_options's own docstring: `destination === null` means the
// officer is already on the map instead) has no Hood/Spot position for
// BoardView's own highlights to render at, so it was never clickable at
// all for a human before (bug report, 2026-08-17: "comprare cops da
// altri giocatori non implementato... i bot lo fanno, ma il giocatore
// umano non ha modo di farlo"). Rendered here instead, as a small
// clickable badge on the *owning* player's own card — one per distinct
// officer_type available from them, with a count badge if more than one.
function buyOfficerFromBaseOptions(
  view: GameViewResponse,
  decision: PendingDecisionResponse | null | undefined,
  ownerId: string,
) {
  if (!decision || decision.decision_type !== 'buy_officer') return [];
  const officerById = new Map(view.officers.map((o) => [o.officer_id, o]));
  return decision.options.filter((option) => {
    if (option.payload.destination == null) return false;
    const officer = officerById.get(option.payload.officer_id as string);
    return officer?.owner_player_id === ownerId;
  });
}

const DOPE_STAT_ITEMS = (p: GameViewResponse['players'][number]) => [
  { key: 'rana', icon: DOPE_ASSET.rana, alt: 'rana', count: p.dope_counts.rana ?? 0 },
  {
    key: 'camaleonte',
    icon: DOPE_ASSET.camaleonte,
    alt: 'camaleonte',
    count: p.dope_counts.camaleonte ?? 0,
  },
  { key: 'polpo', icon: DOPE_ASSET.polpo, alt: 'polpo', count: p.dope_counts.polpo ?? 0 },
  { key: 'gufo', icon: DOPE_ASSET.gufo, alt: 'gufo', count: p.dope_counts.gufo ?? 0 },
];

function officerChipStatItems(view: GameViewResponse, p: GameViewResponse['players'][number]) {
  return [
    {
      key: 'cops',
      icon: OFFICER_ASSET.cop,
      alt: 'Cops',
      count: officersOwnedCount(view, p.player_id),
      detached: true,
    },
    {
      key: 'chip',
      icon: pokerChipAssetForPlayer(p.player_id),
      alt: 'Chip poker',
      count: p.poker_chip_count,
    },
  ];
}

function StatItem({
  item,
}: {
  item: { key: string; icon: string; alt: string; count: number; detached?: boolean };
}) {
  return (
    <div
      className={'player-card__stat-item' + (item.detached ? ' player-card__stat-item--detached' : '')}
    >
      <img src={item.icon} alt={item.alt} className="inline-icon" />
      <span>{item.count}</span>
    </div>
  );
}

export function PlayerStrip({ view, decision, selected = [], onToggle }: PlayerStripProps) {
  return (
    <div className="player-strip">
      {playersInTurnOrder(view).map((p) => {
        // Bigger layout for the human's own card only (designer's request,
        // 2026-08-27 — first scoped to "il giocatore rosso", then
        // clarified as "il player umano": always seat 0 today since
        // SetupScreen hardcodes humanSeat=0, but keyed off
        // viewing_player_id rather than color so it still tracks the
        // human correctly if that ever changes): taller card, full-width
        // Job icons, and the Dope/Cops/Chip stats split into their own two
        // rows (170%-sized Dope icons on the first) instead of the other 3
        // cards' single combined row.
        const isBig = p.player_id === view.viewing_player_id;
        return (
          <div
            key={p.player_id}
            className={
              'player-card' +
              ` player-card--${playerColorForId(p.player_id)}` +
              (isBig ? ' player-card--big' : '') +
              (p.player_id === view.current_player_id ? ' player-card--active' : '')
            }
          >
            <div className="player-card__body">
              <div className="player-card__name-row">
                <div className="player-card__name">
                  {p.player_id === view.current_player_id ? '▶ ' : ''}
                  {playerTeamNameForId(p.player_id)}
                </div>
                <div className="player-card__grit">
                  {[1, 2, 3].map((value) => (
                    <span
                      key={value}
                      className={
                        'player-card__grit-token' +
                        (p.available_grit_values.includes(value)
                          ? ''
                          : ' player-card__grit-token--used')
                      }
                    >
                      {value}
                    </span>
                  ))}
                </div>
              </div>
              {(() => {
                const byTier = view.job_progress_by_player[p.player_id]?.revealed_job_id_by_tier ?? {};
                const tiers = Object.keys(byTier)
                  .map(Number)
                  .sort((a, b) => a - b);
                if (tiers.every((tier) => !byTier[tier])) return null;
                return (
                  <div className={'player-card__jobs' + (isBig ? ' player-card__jobs--wide' : '')}>
                    {/* One slot per tier, in tier order, even once a tier's
                        pile is exhausted and stays empty for good — a Job
                        keeps the same position/size it's always had instead
                        of the remaining ones bunching left and (on the big
                        card) growing to fill the gap (designer's request,
                        2026-08-27: "quando restano 2 jobs, non aggregarli a
                        sinistra e non ingrandirli"). */}
                    {tiers.map((tier) => {
                      const jobId = byTier[tier];
                      if (!jobId) {
                        return (
                          <div
                            key={`empty-${tier}`}
                            className="job-active-strip__card job-active-strip__card--empty"
                          />
                        );
                      }
                      return (
                        <img
                          key={jobId}
                          src={JOB_ASSET[jobId]}
                          alt={jobId}
                          title={jobId}
                          className="job-active-strip__card"
                        />
                      );
                    })}
                  </div>
                );
              })()}
              {buyOfficerFromBaseOptions(view, decision, p.player_id).length > 0 && (
                <div className="player-card__buy-officer">
                  {buyOfficerFromBaseOptions(view, decision, p.player_id).map((option) => {
                    const officer = view.officers.find(
                      (o) => o.officer_id === option.payload.officer_id,
                    );
                    const isSelected = selected.includes(option.option_id);
                    return (
                      <img
                        key={option.option_id}
                        src={OFFICER_ASSET[officer?.officer_type === 'fed' ? 'fed' : 'cop']}
                        alt={option.label_key}
                        title="Compra questo agente dal Covo"
                        className={
                          'player-card__buy-officer-icon' +
                          (isSelected ? ' player-card__buy-officer-icon--selected' : '')
                        }
                        onClick={() => onToggle?.(option.option_id)}
                      />
                    );
                  })}
                </div>
              )}
              {isBig ? (
                <>
                  <div className="player-card__stats player-card__stats--dope-big">
                    {DOPE_STAT_ITEMS(p).map((item) => (
                      <StatItem key={item.key} item={item} />
                    ))}
                  </div>
                  <div className="player-card__stats">
                    {officerChipStatItems(view, p).map((item) => (
                      <StatItem key={item.key} item={item} />
                    ))}
                  </div>
                </>
              ) : (
                <div className="player-card__stats">
                  {/* Single row, icon on top and its own count below
                      (designer's request, 2026-08-23: "le 6 icone... su una
                      unica riga, con sotto ciascuno il suo contatore") — was
                      a 2x2 Dope grid + a detached Cops/Chip column; Cops/Chip
                      keep a bit of extra left margin (--detached) as the
                      same visual separation an earlier request asked for. */}
                  {[...DOPE_STAT_ITEMS(p), ...officerChipStatItems(view, p)].map((item) => (
                    <StatItem key={item.key} item={item} />
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
