import { useEffect, useRef, useState } from 'react';
import {
  pawnAssetForPlayer,
  playerColorLabelForId,
  POKER_HAND_SHAPE_LABEL,
  POKER_SYMBOL_COLOR,
  RAID_SCORE_UNIT_BY_CRITERION,
  RAID_TITLE_SUFFIX_BY_CRITERION,
} from '../assets';
import type {
  GameViewResponse,
  LastBrawlOutcomeResponse,
  LastPokerMatchOutcomeResponse,
  LastRaidOutcomeResponse,
} from '../types';

interface PokerOutcomeItem {
  kind: 'poker';
  id: string;
  outcome: LastPokerMatchOutcomeResponse;
}

interface RaidOutcomeItem {
  kind: 'raid';
  id: string;
  outcome: LastRaidOutcomeResponse;
}

interface BrawlOutcomeItem {
  kind: 'brawl';
  id: string;
  outcome: LastBrawlOutcomeResponse;
}

type QueuedOutcome = PokerOutcomeItem | RaidOutcomeItem | BrawlOutcomeItem;

function PawnRow({ playerId, children }: { playerId: string; children: React.ReactNode }) {
  return (
    <div className="outcome-modal__row">
      <img src={pawnAssetForPlayer(playerId)} alt={playerColorLabelForId(playerId)} className="outcome-modal__pawn" />
      <div>{children}</div>
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

function PokerOutcomeBody({ outcome }: { outcome: LastPokerMatchOutcomeResponse }) {
  const shapeLabel = outcome.top_hand_shape ? (POKER_HAND_SHAPE_LABEL[outcome.top_hand_shape] ?? outcome.top_hand_shape) : null;
  return (
    <>
      <h3>Poker concluso</h3>
      {outcome.winner_id && (
        <PawnRow playerId={outcome.winner_id}>
          <strong>{playerColorLabelForId(outcome.winner_id)}</strong> vince con {shapeLabel}
          <SymbolDots symbols={outcome.hands_by_player_id[outcome.winner_id] ?? []} />
          <div>
            +${outcome.cash_won}
            {outcome.winner_evolved_to_link && ', ottiene un Link Preti'}
          </div>
        </PawnRow>
      )}
      {outcome.tied_ids.length > 0 && (
        <div className="outcome-modal__row">
          <div className="outcome-modal__pawn-stack">
            {outcome.tied_ids.map((id) => (
              <img key={id} src={pawnAssetForPlayer(id)} alt={playerColorLabelForId(id)} className="outcome-modal__pawn" />
            ))}
          </div>
          <div>
            Pareggio con {shapeLabel} tra {outcome.tied_ids.map(playerColorLabelForId).join(', ')} — jackpot riportato
          </div>
        </div>
      )}
      {outcome.loser_ids.map((id) => (
        <PawnRow key={id} playerId={id}>
          {playerColorLabelForId(id)} perde
          {outcome.arrested_loser_ids.includes(id) ? ' e va in prigione' : ''}
        </PawnRow>
      ))}
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
        — <span className="outcome-modal__team-names">{teamIds.map(playerColorLabelForId).join(' e ')}</span>{' '}
        <strong
          className={
            'outcome-modal__verdict' +
            (escaped ? ' outcome-modal__verdict--escape' : ' outcome-modal__verdict--caught')
          }
        >
          {escaped ? 'sfuggono' : 'vengono presi'}
        </strong>
        {stainDetail && <div className="outcome-modal__stain-detail">{stainDetail}</div>}
      </div>
    </div>
  );
}

function RaidOutcomeBody({ outcome }: { outcome: LastRaidOutcomeResponse }) {
  const titleSuffix = RAID_TITLE_SUFFIX_BY_CRITERION[outcome.escape_criterion] ?? '';
  const scoreUnit = RAID_SCORE_UNIT_BY_CRITERION[outcome.escape_criterion] ?? '';
  const stainDetail = outcome.caught_team
    .map((id) => {
      const stained = outcome.stain_count_applied[id] ?? 0;
      return stained > 0 ? `${playerColorLabelForId(id)} macchia ${stained} REP` : null;
    })
    .filter((s): s is string => s !== null)
    .join(', ');
  return (
    <>
      <h3 className="outcome-modal__title--raid">È arrivata la retata {titleSuffix}</h3>
      <RaidTeamRow
        teamIds={outcome.escaping_team}
        escaped
        score={outcome.escaping_team_total}
        scoreUnit={scoreUnit}
      />
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

function pluralize(n: number, singular: string, plural: string): string {
  return n === 1 ? singular : plural;
}

function BrawlOutcomeBody({ outcome }: { outcome: LastBrawlOutcomeResponse }) {
  const participantIds = Object.keys(outcome.force_by_player_id);
  return (
    <>
      <h3>Rissa conclusa</h3>
      {participantIds.map((id) => {
        const pawns = outcome.pawn_count_by_player_id[id] ?? 0;
        const guns = outcome.gun_total_by_player_id[id] ?? 0;
        const total = outcome.force_by_player_id[id] ?? 0;
        const isWinner = outcome.winner_id === id;
        const isLoser = outcome.loser_ids.includes(id);
        return (
          <PawnRow key={id} playerId={id}>
            <strong>{playerColorLabelForId(id)}</strong>: {pawns} {pluralize(pawns, 'pedina', 'pedine')}
            {guns !== 0 && (
              <>
                {' '}
                {guns > 0 ? '+' : '−'} {Math.abs(guns)} {pluralize(Math.abs(guns), 'pistola', 'pistole')}
              </>
            )}{' '}
            = {total}
            {isWinner && ' — Vince'}
            {isLoser && ' — Sconfitto'}
          </PawnRow>
        );
      })}
    </>
  );
}

// Blocking, must-confirm recap for Poker matches, Raids and Rissas
// (designer's request, 2026-08-23: "vorrei dei pulsanti che compaiono e
// che devo schiacciare per confermare la fine di un poker... sotto un
// bottone OK. stessa cosa per le retate", extended the same day to
// Rissas — "per ciascun partecipante deve essere chiaro il punteggio di
// pawns +/- pistole, il totale, il vincitore e lo sconfitto") — replaces
// the dismissible corner popup ResultPopup.tsx used to render for all
// three (now removed entirely, nothing left to show there). One outcome
// at a time, centered, blocking interaction until the confirm button is
// clicked — a right arrow ("→", designer's request 2026-09-05, was a
// plain "OK") — same dedup-by-content idea ResultPopup.tsx used to rely
// on, since a Poker
// match_id is always unique but a Raid's raid_card_id or a Brawl's own
// Hood can each legitimately recur with a genuinely different result in
// a later turn.
export function OutcomeModal({ view }: { view: GameViewResponse }) {
  const [queue, setQueue] = useState<QueuedOutcome[]>([]);
  const shownIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    // Pushed in the same order the turn's own flow resolves them
    // (RULES_CANONICAL.md §B: ACTION_PHASE's own Brawls and, at each
    // round's own end, its single Poker match if launched, then
    // SHOWDOWN_PHASE's Raid) — when a whole batch of outcomes lands in
    // one view update (e.g. that round's Poker match plus the turn's own
    // Raid, both resolved before the human's next decision), this is
    // also the order they get queued and shown in (designer's request,
    // 2026-08-23: "i messaggi popup ... sono poker, retata"). Raid pushed
    // last matters even though it's a single value, not a loop: it used
    // to be pushed first here. At most one Poker outcome can ever be
    // pending at once (2026-09-04 redesign: one shared Gamble slot per
    // round), so it's a single value here too, not a loop.
    const candidates: QueuedOutcome[] = [];
    if (view.last_brawl_outcome) {
      candidates.push({
        kind: 'brawl',
        id: `brawl:${JSON.stringify(view.last_brawl_outcome)}`,
        outcome: view.last_brawl_outcome,
      });
    }
    if (view.last_poker_outcome) {
      candidates.push({
        kind: 'poker',
        id: `poker:${view.last_poker_outcome.match_id}`,
        outcome: view.last_poker_outcome,
      });
    }
    if (view.last_raid_outcome) {
      candidates.push({
        kind: 'raid',
        id: `raid:${JSON.stringify(view.last_raid_outcome)}`,
        outcome: view.last_raid_outcome,
      });
    }
    const fresh = candidates.filter((c) => !shownIds.current.has(c.id));
    if (fresh.length === 0) return;
    for (const c of fresh) shownIds.current.add(c.id);
    setQueue((prev) => [...prev, ...fresh]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view.last_raid_outcome, view.last_brawl_outcome, view.last_poker_outcome]);

  const current = queue[0];
  if (!current) return null;

  function dismiss() {
    setQueue((prev) => prev.slice(1));
  }

  return (
    <div className="outcome-modal-overlay">
      <div className="outcome-modal" key={current.id}>
        {current.kind === 'poker' && <PokerOutcomeBody outcome={current.outcome} />}
        {current.kind === 'raid' && <RaidOutcomeBody outcome={current.outcome} />}
        {current.kind === 'brawl' && <BrawlOutcomeBody outcome={current.outcome} />}
        <button className="outcome-modal__ok" onClick={dismiss} aria-label="Continua">
          →
        </button>
      </div>
    </div>
  );
}
