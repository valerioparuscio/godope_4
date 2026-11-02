import type {
  BrawlRewardResponse,
  LastBrawlOutcomeResponse,
  LastPokerMatchOutcomeResponse,
  LastRaidOutcomeResponse,
} from '../types';
import type { QueuedOutcome } from '../outcome-queue';
import {
  pawnAssetForPlayer,
  playerColorLabelForId,
  pokerHandShapeLabel,
  POKER_HAND_SHAPE_RANK,
  POKER_SYMBOL_COLOR,
  raidScoreUnit,
  raidTitleSuffix,
  raidBannerUrl,
  raidCriterionLabel,
} from '../assets';

function PawnRow({ playerId, children, result }: { playerId: string; children: React.ReactNode; result?: 'W' | 'L' }) {
  return (
    <div className="outcome-modal__row">
      <img src={pawnAssetForPlayer(playerId)} alt={playerColorLabelForId(playerId)} className="outcome-modal__pawn" />
      <div>{children}</div>
      {result && (
        <span
          className={`outcome-modal__result-badge outcome-modal__result-badge--${result === 'W' ? 'win' : 'loss'}`}
          aria-label={result === 'W' ? t('outcome.victory') : t('outcome.defeat')}
          title={result === 'W' ? t('outcome.victory') : t('outcome.defeat')}
        >
          {result}
        </span>
      )}
    </div>
  );
}

function SymbolDots({ symbols }: { symbols: string[] }) {
  return (
    <div className="outcome-modal__symbols">
      {symbols.map((s, i) => (
        <span key={i} className="outcome-modal__symbol-dot" style={{ backgroundColor: POKER_SYMBOL_COLOR[s] ?? '#495057' }} />
      ))}
    </div>
  );
}

// Matches poker_color_tiebreak_order in data/game_config.json.
const POKER_COLOR_ORDER = ['arancione', 'grigio', 'azzurro', 'verde', 'rosa'];

function pokerSortKey(shape: string, symbols: string[]): number[] {
  const rank = POKER_HAND_SHAPE_RANK[shape] ?? 99;
  if (shape === 'five_different') return [rank];
  const counts = new Map<string, number>();
  for (const symbol of symbols) counts.set(symbol, (counts.get(symbol) ?? 0) + 1);
  const colors = [...counts].map(([color, count]) => ({
    count,
    rank: POKER_COLOR_ORDER.includes(color) ? POKER_COLOR_ORDER.indexOf(color) : 99,
  })).sort((a, b) => b.count - a.count || a.rank - b.rank);
  return [rank, ...colors.map((color) => color.rank)];
}

// Sort by hand strength, including dominant colors and remaining symbols.
// The backend outcome still determines victory, defeat and ties.
function PokerOutcomeBody({ outcome }: { outcome: LastPokerMatchOutcomeResponse }) {
  const playerIds = Object.keys(outcome.hands_by_player_id).sort((a, b) => {
    const keyA = pokerSortKey(outcome.shape_by_player_id[a], outcome.hands_by_player_id[a]);
    const keyB = pokerSortKey(outcome.shape_by_player_id[b], outcome.hands_by_player_id[b]);
    for (let i = 0; i < Math.max(keyA.length, keyB.length); i++) {
      const difference = (keyA[i] ?? 99) - (keyB[i] ?? 99);
      if (difference) return difference;
    }
    return 0;
  });
  return (
    <>
      <h3>{t('poker.over')}</h3>
      {playerIds.map((id) => {
        const shape = outcome.shape_by_player_id[id];
        const shapeLabel = shape ? (pokerHandShapeLabel(shape) ?? shape) : null;
        const isWinner = outcome.winner_id === id;
        const isTied = outcome.tied_ids.includes(id);
        const isLoser = outcome.loser_ids.includes(id);
        const isArrested = outcome.arrested_loser_ids.includes(id);
        return (
          <PawnRow key={id} playerId={id} result={isWinner ? 'W' : isLoser ? 'L' : undefined}>
            <strong>{playerColorLabelForId(id)}</strong>
            {shapeLabel && <> — {shapeLabel}</>}
            <SymbolDots symbols={outcome.hands_by_player_id[id] ?? []} />
            <div>
              {isWinner && (
                <>
                  {outcome.cash_won > 0 && <> +${outcome.cash_won}</>}
                  {outcome.winner_evolved_to_link && <div>{t('poker.getsLink')}</div>}
                </>
              )}
              {!isWinner && isTied && t('poker.tie')}
              {isLoser && isArrested && t('poker.toJail')}
            </div>
          </PawnRow>
        );
      })}
    </>
  );
}

// One row per *team* (RULES_CANONICAL.md §D4: Raid teams are always the
// 2 pairs "1+4 contro 2+3"), not one row per player — teammates who
// played together belong on the same line, with their shared outcome
// as the most prominent thing on it (designer's request, 2026-09-05:
// "mettendo sulla stessa riga i giocatori che hanno giocato assieme e
// dando più risalto all'esito per ciascuna coppia"). Each row shows only
// *that* team's own score under the criterion, not a "3 vs 1" comparison
// (2nd request, same day: "farei vedere solo il punteggio loro, non
// quello vs gli altri") — the escaping (winning) team's row always comes
// first.
function RaidTeamRow({
  teamIds,
  escaped,
  score,
  scoreUnit,
  stainDetail,
}: {
  teamIds: readonly string[];
  escaped: boolean;
  score: number;
  scoreUnit: string;
  stainDetail?: string;
}) {
  return (
    <div className="outcome-modal__row outcome-modal__row--team">
      <div className="outcome-modal__pawn-stack">
        {teamIds.map((id) => (
          <img key={id} src={pawnAssetForPlayer(id)} alt={playerColorLabelForId(id)} className="outcome-modal__pawn" />
        ))}
      </div>
      <div>
        <span className="outcome-modal__team-score">
          {score} {scoreUnit}
        </span>{' '}
        — <span className="outcome-modal__team-names">{teamIds.map(playerColorLabelForId).join(t('raidOutcome.and'))}</span>{' '}
        <strong
          className={
            'outcome-modal__verdict' +
            (escaped ? ' outcome-modal__verdict--escape' : ' outcome-modal__verdict--caught')
          }
        >
          {escaped ? t('raidOutcome.escape') : t('raidOutcome.caught')}
        </strong>
        {stainDetail && <div className="outcome-modal__stain-detail">{stainDetail}</div>}
      </div>
    </div>
  );
}

function RaidOutcomeBody({ outcome }: { outcome: LastRaidOutcomeResponse }) {
  const titleSuffix = raidTitleSuffix(outcome.escape_criterion) ?? '';
  const scoreUnit = raidScoreUnit(outcome.escape_criterion) ?? '';
  const stainDetail = outcome.caught_team
    .map((id) => {
      const stained = outcome.stain_count_applied[id] ?? 0;
      return stained > 0 ? t('raidOutcome.stains', { player: playerColorLabelForId(id), n: stained }) : null;
    })
    .filter((s): s is string => s !== null)
    .join(', ');
  return (
    <>
      <h3 className="outcome-modal__title--raid">{t('raidOutcome.title', { suffix: titleSuffix })}</h3>
      {outcome.escaping_team.length > 0 ? (
        <RaidTeamRow
          teamIds={outcome.escaping_team}
          escaped
          score={outcome.escaping_team_total}
          scoreUnit={scoreUnit}
        />
      ) : (
        // A tie: nobody escapes (all 4 gangs are caught), so no empty "winners" row — one line says so instead.
        <div className="outcome-modal__row outcome-modal__row--team">
          <strong className="outcome-modal__verdict outcome-modal__verdict--caught">{t('raidOutcome.allCaught')}</strong>
        </div>
      )}
      <RaidTeamRow
        teamIds={outcome.caught_team}
        escaped={false}
        score={outcome.caught_team_total}
        scoreUnit={scoreUnit}
        stainDetail={stainDetail || undefined}
      />
    </>
  );
}

// One icon per unit instead of a bare count (game designer, 2026-09-24:
// "vorrei che venisse esplicitato il conteggio mostrando simboli dei
// pawns + pistole positive bianche e pistole negative rosse, con numero
// finale") — this game has no dedicated Gun art asset yet, so a Gun unit
// renders as a small coloured dot (white for a positive adjustment, red
// for negative), the same visual language `SymbolDots` already uses for
// Poker's own per-unit symbols.
function ForceBreakdown({
  playerId,
  pawnCount,
  gunTotal,
  total,
}: {
  playerId: string;
  pawnCount: number;
  gunTotal: number;
  total: number;
}) {
  return (
    <div className="outcome-modal__force">
      {Array.from({ length: pawnCount }, (_, i) => (
        <img
          key={`pawn_${i}`}
          src={pawnAssetForPlayer(playerId)}
          alt=""
          className="outcome-modal__force-pawn"
        />
      ))}
      {Array.from({ length: Math.abs(gunTotal) }, (_, i) => (
        <span
          key={`gun_${i}`}
          className={
            'outcome-modal__gun-dot ' +
            (gunTotal > 0 ? 'outcome-modal__gun-dot--positive' : 'outcome-modal__gun-dot--negative')
          }
        />
      ))}
      <span className="outcome-modal__force-total">= {total}</span>
    </div>
  );
}

// Redesigned (same request, 2026-09-24: sorted strongest to weakest, the
// winner always on top and the loser(s) at the bottom) — sorts by each
// participant's own force_by_player_id total, the backend's own final
// number, not something recomputed here.
// "Easy Price": the winner always steals a card from each defeated participant, plus whatever his
// own card adds (money, a Poker Chip, a Dope).
function lootText(reward: BrawlRewardResponse): string {
  const parts = [reward.stole_card ? t('brawl.lootCard') : t('brawl.lootNoCard')];
  if (reward.money > 0) parts.push(`${reward.money}$`);
  if (reward.poker_chip) parts.push(t('brawl.lootChip'));
  if (reward.dope_type) parts.push(t('brawl.lootDope', { name: tDyn(`dope.${reward.dope_type}`) ?? reward.dope_type }));
  return parts.join(' + ');
}

function BrawlOutcomeBody({ outcome }: { outcome: LastBrawlOutcomeResponse }) {
  const participantIds = Object.keys(outcome.force_by_player_id).sort(
    (a, b) => (outcome.force_by_player_id[b] ?? 0) - (outcome.force_by_player_id[a] ?? 0),
  );
  return (
    <>
      <h3>{t('brawl.over')}</h3>
      {participantIds.map((id) => {
        const pawns = outcome.pawn_count_by_player_id[id] ?? 0;
        const guns = outcome.gun_total_by_player_id[id] ?? 0;
        const total = outcome.force_by_player_id[id] ?? 0;
        const isWinner = outcome.winner_id === id;
        const isLoser = outcome.loser_ids.includes(id);
        return (
          <PawnRow key={id} playerId={id} result={isWinner ? 'W' : isLoser ? 'L' : undefined}>
            <strong>{playerColorLabelForId(id)}</strong>
            <ForceBreakdown playerId={id} pawnCount={pawns} gunTotal={guns} total={total} />
          </PawnRow>
        );
      })}
      {(outcome.rewards ?? []).length > 0 && outcome.winner_id && (
        <div className="outcome-modal__loot">
          <p className="outcome-modal__loot-title">{t('brawl.loot')}</p>
          {(outcome.rewards ?? []).map((reward) => (
            <p key={reward.loser_id} className="outcome-modal__loot-line">
              <strong>{playerColorLabelForId(outcome.winner_id as string)}</strong> {t('brawl.takesFrom')}{' '}
              <strong>{playerColorLabelForId(reward.loser_id)}</strong>: {lootText(reward)}
            </p>
          ))}
        </div>
      )}
    </>
  );
}

function TurnStartOutcomeBody({ turnIndex }: { turnIndex: number }) {
  return (
    <div className="outcome-modal__turn-start">
      <span className="outcome-modal__turn-start-label">{t('turnStart.label')}</span>
      <span className="outcome-modal__turn-start-number">{turnIndex}</span>
    </div>
  );
}

function RaidStartOutcomeBody({ announcement }: {
  announcement: Extract<QueuedOutcome, { kind: 'raid_start' }>;
}) {
  const criterion = announcement.criterion ?? '';
  const suffix = raidTitleSuffix(criterion);
  const card = raidBannerUrl(announcement.raidCardId);
  return (
    <div className="raid-announcement">
      <p className="raid-announcement__eyebrow">{t('raidStart.eyebrow', { n: announcement.turnIndex })}</p>
      <h2 id="raid-announcement-title">{t('raidStart.title')} <span>{suffix ?? t('raidStart.incoming')}</span></h2>
      <div className="raid-announcement__content">
        {card && <img className="raid-announcement__card" src={card} alt={t('raidStart.cardAlt', { suffix: suffix ?? '' })} />}
        <div className="raid-announcement__brief">
          <p className="raid-announcement__eyebrow">{t('raidStart.toEscape')}</p>
          {criterion && <p className="raid-announcement__criterion">
            {criterion === 'least_dope_value'
              ? t('raidStart.lessDopeValue')
              : `${criterion.startsWith('least_') ? t('raidStart.less') : t('raidStart.more')} ${raidCriterionLabel(criterion) ?? criterion}`}
          </p>}
          <p>{t('raidStart.getReady')}</p>
        </div>
      </div>
    </div>
  );
}

// "Spezza il flusso" before *any* Poker match plays out, whether or not
// the human is one of its Gamblers (game designer, 2026-09-26) — distinct
// from DecisionPanel's own "Partita a poker?" popup, which only ever
// appears for the human's *own* choice to launch one.
function PokerFizzleOutcomeBody() {
  return (
    <>
      <h3>{t('poker.cancelled')}</h3>
      <p>{t('poker.nobodyBet')}</p>
    </>
  );
}

function PokerStartOutcomeBody() {
  return <h3>{t('poker.aboutToStart')}</h3>;
}

// Blocking, must-confirm recap for Poker matches, Raids, Rissas and now
// (2026-09-26) a new Turn's own start — "vorrei un bottone ok nelle
// finestre di rissa, risultato poker e risultato retate. senza quell'ok
// dato dal giocatore il gioco non deve proseguire" (game designer).
// Originally kept its own internal queue/dedup state (derived straight
// from `view.last_*_outcome`) — moved up to App.tsx (`outcome-queue.ts`,
// `applyView`) because that queue is only *half* the fix: the real bug
// reported was that `TurnPlayback`'s own bot-turn narration kept
// advancing underneath this modal regardless of whether it had been
// confirmed yet, since the two were entirely decoupled. App.tsx now
// computes the same queue and gates `TurnPlayback` on it
// (`paused={outcomeQueue.length > 0}`) in the same render pass that
// updates it — no reactive round-trip between sibling components for
// `TurnPlayback` to race ahead of. This component is now a plain,
// presentation of whatever `current` App.tsx hands it.
export function OutcomeModal({
  current,
  onDismiss,
}: {
  current: QueuedOutcome | null;
  onDismiss: () => void;
}) {
  const turnAnnouncementId = current?.kind === 'turn_start' ? current.id : null;
  useEffect(() => {
    if (!turnAnnouncementId) return;
    const timer = setTimeout(() => randomSoundUrls('turn').forEach(playSound), 0);
    return () => clearTimeout(timer);
  }, [turnAnnouncementId]);
  if (!current) return null;

  return (
    <div className="outcome-modal-overlay">
      <div
        className={
          'outcome-modal' + (current.kind === 'turn_start' ? ' outcome-modal--turn-start' : '') +
          (current.kind === 'raid_start' ? ' outcome-modal--raid-start' : '')
        }
        key={current.id}
        data-outcome={current.kind}
        role="dialog"
        aria-modal="true"
        aria-labelledby={current.kind === 'raid_start' ? 'raid-announcement-title' : undefined}
      >
        {current.kind === 'poker' && <PokerOutcomeBody outcome={current.outcome} />}
        {current.kind === 'raid' && <RaidOutcomeBody outcome={current.outcome} />}
        {current.kind === 'brawl' && <BrawlOutcomeBody outcome={current.outcome} />}
        {current.kind === 'turn_start' && <TurnStartOutcomeBody turnIndex={current.turnIndex} />}
        {current.kind === 'raid_start' && <RaidStartOutcomeBody announcement={current} />}
        {current.kind === 'raid_replaced' && <h3>{t('raidOutcome.replaced')}</h3>}
        {current.kind === 'poker_start' && <PokerStartOutcomeBody />}
        {current.kind === 'poker_fizzle' && <PokerFizzleOutcomeBody />}
        <button className="outcome-modal__ok" onClick={onDismiss} aria-label={t('outcome.continue')}>
          {current.kind === 'poker_start' ? t('outcome.startPoker') : current.kind === 'raid_start' ? t('outcome.ready') : t('outcome.ok')}
        </button>
      </div>
    </div>
  );
}
import { useEffect } from 'react';
import { t, tDyn } from '../i18n';
import { playSound, randomSoundUrls } from '../sound';
