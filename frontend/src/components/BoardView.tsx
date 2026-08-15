import { useEffect, useState } from 'react';
import {
  BOARD_BACKGROUND,
  DOPE_ASSET,
  OFFICER_ASSET,
  PRICE_TOKEN_ASSET,
  cardAssetUrl,
  pawnAssetForPlayer,
  repAssetForPlayer,
} from '../assets';
import {
  CONTACT_LINK_SLOT_POSITION,
  DEN_POSITION,
  DEN_SLOT_POSITION,
  GAMBLE_SLOT_POSITION,
  HOOD_PETAL_POSITION,
  HOOD_POSITION,
  JAIL_SLOT_POSITION,
  JOB_BOARD_CELL_POSITION,
  PRICE_TOKEN_POSITION,
  SPOT_POSITION,
  moneyTrackPosition,
  type Point,
} from '../board-layout';
import type {
  DecisionOptionResponse,
  GameViewResponse,
  PendingDecisionResponse,
  PublicPawnResponse,
} from '../types';

interface BoardViewProps {
  view: GameViewResponse;
  decision?: PendingDecisionResponse | null;
  selected?: string[];
  onToggle?: (optionId: string) => void;
}

function Token({ point, src, alt, size = 5.5 }: { point: Point; src: string; alt: string; size?: number }) {
  return (
    <img
      src={src}
      alt={alt}
      className="board-token"
      style={{
        left: `${point.xPct}%`,
        top: `${point.yPct}%`,
        width: `${size}%`,
      }}
    />
  );
}

function CountBadge({ point, count }: { point: Point; count: number }) {
  return (
    <div
      className="board-count-badge"
      style={{ left: `${point.xPct}%`, top: `${point.yPct}%` }}
    >
      {count}
    </div>
  );
}

const PAWN_SIZE = 2.8;
// Measured against the game designer's own calibration overlay
// (board_calibration_2.png, 2026-08-14): a dope pile — at a Hood's
// center or on a Spot, same visual treatment — should render at ~4.9%
// of board width, not the earlier 5.8%.
const DOPE_PILE_SIZE = 4.9;
const DOPE_PILE_BADGE_OFFSET = 1.9;
// A Cop/Fed badge sits on the dope pile's own bottom-left edge, i.e. a
// point at 45° from the pile's center, at its radius — per the game
// designer (2026-08-14): "un cerchietto che va dal centro del cerchio
// merci, fino al suo bordo in basso a sinistra a 45 gradi".
const OFFICER_BADGE_OFFSET = (DOPE_PILE_SIZE / 2) * Math.SQRT1_2;
const OFFICER_BADGE_SIZE = 2.4;

function officerBadgePoint(pilePoint: Point): Point {
  return { xPct: pilePoint.xPct - OFFICER_BADGE_OFFSET, yPct: pilePoint.yPct + OFFICER_BADGE_OFFSET };
}

function DopePile({ point, dopeType, count }: { point: Point; dopeType: string; count: number }) {
  return (
    <>
      <Token point={point} src={DOPE_ASSET[dopeType]} alt={`${count}x ${dopeType}`} size={DOPE_PILE_SIZE} />
      <CountBadge
        point={{ xPct: point.xPct + DOPE_PILE_BADGE_OFFSET, yPct: point.yPct + DOPE_PILE_BADGE_OFFSET }}
        count={count}
      />
    </>
  );
}

// Only these decision types have every option resolvable to a spot on the
// board (place a Hood, target an on-map officer) — the designer asked
// that these be clicked directly on the board instead of picked from the
// text list (2026-08-15). "move_criminal" gets its own two-stage
// component below (pick the pawn, then its destination) instead of this
// single-stage one. Others (which card to use, hand discards, Poker, ...)
// keep the plain list only.
function boardPointForOption(
  decisionType: string,
  option: DecisionOptionResponse,
  officerLocation: Map<string, Point>,
): Point | null {
  const payload = option.payload;
  switch (decisionType) {
    case 'place_criminal':
      return HOOD_POSITION[payload.hood_id as string] ?? null;
    case 'corrupt_officer':
    case 'buy_officer':
      return officerLocation.get(payload.officer_id as string) ?? null;
    default:
      return null;
  }
}

const HIGHLIGHT_SIZE = 7;

function BoardHighlights({
  decision,
  selected,
  onToggle,
  officerLocation,
}: {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  officerLocation: Map<string, Point>;
}) {
  const optionsByPointKey = new Map<string, { point: Point; options: DecisionOptionResponse[] }>();
  for (const option of decision.options) {
    const point = boardPointForOption(decision.decision_type, option, officerLocation);
    if (!point) continue;
    const key = `${point.xPct},${point.yPct}`;
    const entry = optionsByPointKey.get(key) ?? { point, options: [] };
    entry.options.push(option);
    optionsByPointKey.set(key, entry);
  }
  if (optionsByPointKey.size === 0) return null;

  return (
    <>
      {Array.from(optionsByPointKey.entries()).map(([key, { point, options }]) => {
        const selectedHere = options.filter((o) => selected.includes(o.option_id));
        function handleClick() {
          if (selectedHere.length > 0) {
            onToggle(selectedHere[selectedHere.length - 1].option_id);
          } else {
            onToggle(options[0].option_id);
          }
        }
        return (
          <div
            key={key}
            className={'board-highlight' + (selectedHere.length > 0 ? ' board-highlight--selected' : '')}
            style={{
              left: `${point.xPct}%`,
              top: `${point.yPct}%`,
              width: `${HIGHLIGHT_SIZE}%`,
            }}
            onClick={handleClick}
            title={options[0].label_key}
          >
            {selectedHere.length > 0 && <span className="board-highlight__count">{selectedHere.length}</span>}
          </div>
        );
      })}
    </>
  );
}

const PAWN_HIGHLIGHT_SIZE = 4.2;

// Where a specific pawn's own token currently sits on the board — the
// same slot-index logic BoardView's own rendering below uses for
// Criminal petals / Den slots, reused here so a highlight lands exactly
// on top of the pawn it refers to.
function pawnBoardPoint(
  pawnId: string,
  pawnsByHood: Map<string, PublicPawnResponse[]>,
  denGamblerPawnIds: string[],
  pawnById: Map<string, PublicPawnResponse>,
): Point | null {
  const pawn = pawnById.get(pawnId);
  if (!pawn) return null;
  if (pawn.role === 'criminal' && pawn.hood_id) {
    const petals = HOOD_PETAL_POSITION[pawn.hood_id];
    const index = (pawnsByHood.get(pawn.hood_id) ?? []).findIndex((p) => p.pawn_id === pawnId);
    return petals && index >= 0 ? (petals[index] ?? null) : null;
  }
  if (pawn.role === 'gambler') {
    const index = denGamblerPawnIds.indexOf(pawnId);
    return index >= 0 ? (DEN_SLOT_POSITION[index] ?? null) : null;
  }
  return null;
}

// Move Criminal gets a two-stage click flow instead of the single-stage
// highlight above (designer's request, 2026-08-16): first the movable
// pawns themselves glow (skipping any already queued in this package),
// clicking one then glows *its* legal destinations, clicking one of
// those queues the move and returns to picking the next pawn — repeating
// once per remaining Grit, exactly like building the package from the
// text list would, just via the board instead.
function MoveCriminalHighlights({
  decision,
  selected,
  onToggle,
  pawnsByHood,
  pawnById,
  denGamblerPawnIds,
}: {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  pawnsByHood: Map<string, PublicPawnResponse[]>;
  pawnById: Map<string, PublicPawnResponse>;
  denGamblerPawnIds: string[];
}) {
  const [stagedPawnId, setStagedPawnId] = useState<string | null>(null);

  useEffect(() => {
    setStagedPawnId(null);
  }, [decision.decision_id]);

  const committedPawnIds = new Set(
    decision.options
      .filter((o) => selected.includes(o.option_id))
      .map((o) => o.payload.pawn_id as string),
  );

  if (stagedPawnId && !committedPawnIds.has(stagedPawnId)) {
    const stagedPoint = pawnBoardPoint(stagedPawnId, pawnsByHood, denGamblerPawnIds, pawnById);
    const destinationsByPointKey = new Map<
      string,
      { point: Point; options: DecisionOptionResponse[] }
    >();
    for (const option of decision.options) {
      if (option.payload.pawn_id !== stagedPawnId) continue;
      const dest = option.payload.destination_hood_id as string;
      const point = dest === 'den' ? DEN_POSITION : HOOD_POSITION[dest];
      if (!point) continue;
      const key = `${point.xPct},${point.yPct}`;
      const entry = destinationsByPointKey.get(key) ?? { point, options: [] };
      entry.options.push(option);
      destinationsByPointKey.set(key, entry);
    }

    return (
      <>
        {stagedPoint && (
          <div
            className="board-highlight board-highlight--selected"
            style={{
              left: `${stagedPoint.xPct}%`,
              top: `${stagedPoint.yPct}%`,
              width: `${PAWN_HIGHLIGHT_SIZE}%`,
            }}
            onClick={() => setStagedPawnId(null)}
            title="Annulla selezione"
          />
        )}
        {Array.from(destinationsByPointKey.entries()).map(([key, { point, options }]) => (
          <div
            key={key}
            className="board-highlight"
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${HIGHLIGHT_SIZE}%` }}
            onClick={() => {
              onToggle(options[0].option_id);
              setStagedPawnId(null);
            }}
            title={options[0].label_key}
          />
        ))}
      </>
    );
  }

  const candidatePawnIds = Array.from(
    new Set(
      decision.options
        .map((o) => o.payload.pawn_id as string)
        .filter((pid) => !committedPawnIds.has(pid)),
    ),
  );

  return (
    <>
      {candidatePawnIds.map((pawnId) => {
        const point = pawnBoardPoint(pawnId, pawnsByHood, denGamblerPawnIds, pawnById);
        if (!point) return null;
        return (
          <div
            key={pawnId}
            className="board-highlight"
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${PAWN_HIGHLIGHT_SIZE}%` }}
            onClick={() => setStagedPawnId(pawnId)}
            title="Sposta questo Criminale"
          />
        );
      })}
    </>
  );
}

export function BoardView({ view, decision, selected, onToggle }: BoardViewProps) {
  const pawnsByHood = new Map<string, PublicPawnResponse[]>();
  for (const pawn of view.pawns) {
    if (pawn.role !== 'criminal' || !pawn.hood_id) continue;
    const list = pawnsByHood.get(pawn.hood_id) ?? [];
    list.push(pawn);
    pawnsByHood.set(pawn.hood_id, list);
  }
  const pawnById = new Map(view.pawns.map((p) => [p.pawn_id, p]));

  const officerLocation = new Map<string, Point>();
  for (const officer of view.officers) {
    if (officer.hood_id && HOOD_POSITION[officer.hood_id]) {
      officerLocation.set(officer.officer_id, officerBadgePoint(HOOD_POSITION[officer.hood_id]));
    } else if (officer.spot_id && SPOT_POSITION[officer.spot_id]) {
      officerLocation.set(officer.officer_id, officerBadgePoint(SPOT_POSITION[officer.spot_id]));
    }
  }

  return (
    <div className="board-view">
      <img src={BOARD_BACKGROUND} alt="Tabellone" className="board-view__background" />

      {view.hoods
        .filter((h) => h.revealed)
        .map((hood) => {
          const center = HOOD_POSITION[hood.hood_id];
          const petals = HOOD_PETAL_POSITION[hood.hood_id];
          if (!center || !petals) return null;
          const criminals = pawnsByHood.get(hood.hood_id) ?? [];
          return (
            <div key={hood.hood_id}>
              {criminals.slice(0, 5).map((pawn, i) => (
                <Token
                  key={pawn.pawn_id}
                  point={petals[i]}
                  src={pawnAssetForPlayer(pawn.owner_player_id)}
                  alt={pawn.pawn_id}
                  size={PAWN_SIZE}
                />
              ))}
              {hood.dope_stack.length > 0 && (
                <DopePile point={center} dopeType={hood.dope_stack[0]} count={hood.dope_stack.length} />
              )}
              {hood.cop_ids.length > 0 && (
                <Token
                  point={officerBadgePoint(center)}
                  src={OFFICER_ASSET.cop}
                  alt={`${hood.cop_ids.length} cop(s)`}
                  size={OFFICER_BADGE_SIZE}
                />
              )}
            </div>
          );
        })}

      {view.spots.map((spot) => {
        const point = SPOT_POSITION[spot.spot_id];
        if (!point) return null;
        return (
          <div key={spot.spot_id}>
            {spot.sold_dope_tokens.length > 0 && (
              <DopePile
                point={point}
                dopeType={spot.accepted_dope_type}
                count={spot.sold_dope_tokens.length}
              />
            )}
            {spot.fed_ids.length > 0 && (
              <Token
                point={officerBadgePoint(point)}
                src={OFFICER_ASSET.fed}
                alt={`${spot.fed_ids.length} fed(s)`}
                size={OFFICER_BADGE_SIZE}
              />
            )}
          </div>
        );
      })}

      {view.den_gambler_pawn_ids.slice(0, 6).map((pawnId, i) => {
        const pawn = pawnById.get(pawnId);
        if (!pawn) return null;
        const point = DEN_SLOT_POSITION[i];
        if (!point) return null;
        return (
          <Token
            key={pawnId}
            point={point}
            src={pawnAssetForPlayer(pawn.owner_player_id)}
            alt={pawnId}
            size={PAWN_SIZE}
          />
        );
      })}

      {view.jail_slots.map((slot) => {
        const point = JAIL_SLOT_POSITION[slot.index];
        if (!point) return null;
        const ratPawn = slot.rat_pawn_id ? pawnById.get(slot.rat_pawn_id) : undefined;
        return (
          <div key={slot.index}>
            {ratPawn && (
              <Token
                point={{ xPct: point.xPct - 1.2, yPct: point.yPct }}
                src={pawnAssetForPlayer(ratPawn.owner_player_id)}
                alt={ratPawn.pawn_id}
                size={PAWN_SIZE}
              />
            )}
            {slot.confiscated_dope_type && (
              <Token
                point={{ xPct: point.xPct + 1.8, yPct: point.yPct }}
                src={DOPE_ASSET[slot.confiscated_dope_type]}
                alt={slot.confiscated_dope_type}
                size={2.8}
              />
            )}
          </div>
        );
      })}

      {view.pawns
        .filter((pawn) => pawn.role === 'link' && pawn.contact_id && pawn.link_level)
        .map((pawn) => {
          const slots = CONTACT_LINK_SLOT_POSITION[pawn.contact_id as string];
          const point = slots?.[(pawn.link_level as number) - 1];
          if (!point) return null;
          return (
            <Token
              key={pawn.pawn_id}
              point={point}
              src={pawnAssetForPlayer(pawn.owner_player_id)}
              alt={pawn.pawn_id}
              size={PAWN_SIZE}
            />
          );
        })}

      {view.poker_launched_card_ids.map((cardId, i) => {
        const point = GAMBLE_SLOT_POSITION[i];
        if (!point) return null;
        return (
          <Token
            key={cardId}
            point={point}
            src={cardAssetUrl(cardId)}
            alt={cardId}
            size={7}
          />
        );
      })}

      {view.job_board
        .filter((cell) => cell.player_id)
        .map((cell) => {
          const point = JOB_BOARD_CELL_POSITION[cell.job_id]?.[cell.column_index];
          if (!point) return null;
          return (
            <img
              key={`${cell.job_id}-${cell.column_index}`}
              src={repAssetForPlayer(cell.player_id as string)}
              alt={`${cell.player_id}: ${cell.job_id}`}
              className={'board-token' + (cell.stained ? ' rep-token--stained' : '')}
              style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: '1.9%' }}
            />
          );
        })}

      {Object.entries(view.current_price_by_dope_type).map(([dopeType, price]) => {
        const point = PRICE_TOKEN_POSITION[dopeType]?.[price];
        if (!point) return null;
        return (
          <Token
            key={dopeType}
            point={point}
            src={PRICE_TOKEN_ASSET[dopeType]}
            alt={`${dopeType}: $${price}`}
            size={2.2}
          />
        );
      })}

      {view.players.map((player, i) => {
        // Small per-player jitter (both axes) so tokens on the same money
        // value — the common case at game start — don't fully overlap.
        const point = moneyTrackPosition(player.money);
        const col = i % 2;
        const row = Math.floor(i / 2);
        return (
          <Token
            key={player.player_id}
            point={{
              xPct: point.xPct + (col === 0 ? -0.9 : 0.9),
              yPct: point.yPct - 2.2 - row * 2.2,
            }}
            src={repAssetForPlayer(player.player_id)}
            alt={`${player.player_id}: $${player.money}`}
            size={2.2}
          />
        );
      })}

      {decision &&
        selected &&
        onToggle &&
        (decision.decision_type === 'move_criminal' ? (
          <MoveCriminalHighlights
            decision={decision}
            selected={selected}
            onToggle={onToggle}
            pawnsByHood={pawnsByHood}
            pawnById={pawnById}
            denGamblerPawnIds={view.den_gambler_pawn_ids}
          />
        ) : (
          <BoardHighlights
            decision={decision}
            selected={selected}
            onToggle={onToggle}
            officerLocation={officerLocation}
          />
        ))}
    </div>
  );
}
