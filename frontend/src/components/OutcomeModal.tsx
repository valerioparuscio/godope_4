import type { LastBrawlOutcomeResponse, LastPokerMatchOutcomeResponse, LastRaidOutcomeResponse } from '../types';
import type { QueuedOutcome } from '../outcome-queue';
import {
  pawnAssetForPlayer,
  playerColorLabelForId,
  POKER_HAND_SHAPE_LABEL,
  POKER_HAND_SHAPE_RANK,
  POKER_SYMBOL_COLOR,
  RAID_SCORE_UNIT_BY_CRITERION,
  RAID_TITLE_SUFFIX_BY_CRITERION,
} from '../assets';

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

// Redesigned (game designer's request, 2026-09-24: "vorrei che venissero
// mostrati i simboli della mano di ciascun giocatore, come ora viene fatto
// per il vincitore, mettendo in ordine di punteggio") — one row per
// participant instead of 3 separate winner/tied/losers sections, every
// row showing that player's own 5-symbol hand and shape, sorted strongest
// to weakest via `shape_by_player_id` (`POKER_HAND_SHAPE_RANK` for the
// display order only — winner_id/tied_ids/loser_ids, still the backend's
// own call, decide who actually won).
function PokerOutcomeBody({ outcome }: { outcome: LastPokerMatchOutcomeResponse }) {
  const playerIds = Object.keys(outcome.hands_by_player_id).sort((a, b) => {
    const rankA = POKER_HAND_SHAPE_RANK[outcome.shape_by_player_id[a]] ?? 99;
    const rankB = POKER_HAND_SHAPE_RANK[outcome.shape_by_player_id[b]] ?? 99;
    return rankA - rankB;
  });
  return (
    <>
      <h3>Poker concluso</h3>
      {playerIds.map((id) => {
        const shape = outcome.shape_by_player_id[id];
        const shapeLabel = shape ? (POKER_HAND_SHAPE_LABEL[shape] ?? shape) : null;
        const isWinner = outcome.winner_id === id;
        const isTied = outcome.tied_ids.includes(id);
        const isArrested = outcome.arrested_loser_ids.includes(id);
        return (
          <PawnRow key={id} playerId={id}>
            <strong>{playerColorLabelForId(id)}</strong>
            {shapeLabel && <> — {shapeLabel}</>}
            <SymbolDots symbols={outcome.hands_by_player_id[id] ?? []} />
            <div>
              {isWinner && (
                <>
                  Vince
                  {outcome.cash_won > 0 && <> +${outcome.cash_won}</>}
                  {outcome.winner_evolved_to_link && ', ottiene un Link Preti'}
                </>
              )}
              {!isWinner && isTied && 'Pareggio — jackpot riportato'}
              {!isWinner && !isTied && (
                <>
                  Sconfitto
                  {isArrested && ' e va in prigione'}
                </>
              )}
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
function BrawlOutcomeBody({ outcome }: { outcome: LastBrawlOutcomeResponse }) {
  const participantIds = Object.keys(outcome.force_by_player_id).sort(
    (a, b) => (outcome.force_by_player_id[b] ?? 0) - (outcome.force_by_player_id[a] ?? 0),
  );
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
            <strong>{playerColorLabelForId(id)}</strong>
            <ForceBreakdown playerId={id} pawnCount={pawns} gunTotal={guns} total={total} />
            {isWinner && ' — Vince'}
            {isLoser && ' — Sconfitto'}
          </PawnRow>
        );
      })}
    </>
  );
}

function TurnStartOutcomeBody({ turnIndex }: { turnIndex: number }) {
  return (
    <div className="outcome-modal__turn-start">
      <span className="outcome-modal__turn-start-label">Turno</span>
      <span className="outcome-modal__turn-start-number">{turnIndex}</span>
    </div>
  );
}

// "Spezza il flusso" before *any* Poker match plays out, whether or not
// the human is one of its Gamblers (game designer, 2026-09-26) — distinct
// from DecisionPanel's own "Partita a poker?" popup, which only ever
// appears for the human's *own* choice to launch one.
function PokerStartOutcomeBody() {
  return <h3>Sta per iniziare una partita a Poker!</h3>;
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
// stateless presentation of whatever `current` App.tsx hands it.
export function OutcomeModal({
  current,
  onDismiss,
}: {
  current: QueuedOutcome | null;
  onDismiss: () => void;
}) {
  if (!current) return null;

  return (
    <div className="outcome-modal-overlay">
      <div
        className={
          'outcome-modal' + (current.kind === 'turn_start' ? ' outcome-modal--turn-start' : '')
        }
        key={current.id}
      >
        {current.kind === 'poker' && <PokerOutcomeBody outcome={current.outcome} />}
        {current.kind === 'raid' && <RaidOutcomeBody outcome={current.outcome} />}
        {current.kind === 'brawl' && <BrawlOutcomeBody outcome={current.outcome} />}
        {current.kind === 'turn_start' && <TurnStartOutcomeBody turnIndex={current.turnIndex} />}
        {current.kind === 'poker_start' && <PokerStartOutcomeBody />}
        <button className="outcome-modal__ok" onClick={onDismiss} aria-label="Continua">
          {current.kind === 'poker_start' ? 'Inizia!' : 'OK'}
        </button>
      </div>
    </div>
  );
}
