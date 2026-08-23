import { useEffect, useRef, useState } from 'react';
import {
  BOARD_BACKGROUND,
  DOPE_ASSET,
  OFFICER_ASSET,
  PRICE_TOKEN_ASSET,
  cardAssetUrl,
  moneyMarkerAssetForPlayer,
  pawnAssetForPlayer,
  playerColorForId,
  repAssetForPlayer,
  type PlayerColor,
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
  MONEY_CELL_HEIGHT,
  MONEY_CELL_TOP,
  MONEY_CELL_WIDTH,
  PRICE_TOKEN_POSITION,
  SPOT_POSITION,
  moneyTrackLap,
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
  onSubmit?: (selectedOptionIds: string[]) => void;
  stagedCorruptionAction?: string | null;
}

function Token({
  point,
  src,
  alt,
  size = 5.5,
  className = '',
}: {
  point: Point;
  src: string;
  alt: string;
  size?: number;
  className?: string;
}) {
  return (
    <img
      src={src}
      alt={alt}
      className={className ? `board-token ${className}` : 'board-token'}
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
// Each Jail slot's own small inner circle (~2.1% of board width, measured
// against the raw board art — noticeably smaller than a normal pawn slot,
// designer's request 2026-08-16) is where a Rat renders, concentric with
// the slot's big circle (its confiscated Dope, at the normal DOPE_PILE_SIZE).
const JAIL_PAWN_SIZE = 2.1;
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

// A small count badge on a Cop/Fed badge's own bottom-right edge (mirrors
// DopePile's own badge placement relative to its icon) — only rendered
// when 2+ officers share a Hood/Spot (designer's request, 2026-08-17:
// "se in un quartiere ci sono 2+ cops, metti un numerino"), since a
// single officer is already unambiguous from the icon alone.
const OFFICER_BADGE_COUNT_OFFSET = OFFICER_BADGE_SIZE / 2;

function officerCountBadgePoint(pilePoint: Point): Point {
  const badge = officerBadgePoint(pilePoint);
  return {
    xPct: badge.xPct + OFFICER_BADGE_COUNT_OFFSET,
    yPct: badge.yPct + OFFICER_BADGE_COUNT_OFFSET,
  };
}

// Each of the 4 cash markers (assets/cash/{R,B,G,Y}.png, or its "+30"
// variant once a player loops past $30 — see moneyTrackLap) renders as a
// small colored dot inside its money-track cell, one per corner
// (designer's request, 2026-08-16: "metti sul cash 4 pallini colorati
// dentro il quadrato cash ma ai 4 angoli"), so all 4 stay visible
// whenever they share a cell.
// Bank-supply counter (designer's request, 2026-08-23): how far right of
// its Dope type's own fixed icon anchor the badge sits, toward the
// board's own right edge (anchors run ~93-95%, board edge is 100%) — a
// plain CSS `transform` offset (relative to the badge's own tiny size)
// wasn't enough separation, so this shifts the underlying board-relative
// point itself instead, same units as every other position on this
// board (a percentage of the board image's own width/height).
const SUPPLY_COUNT_OFFSET_PCT = 4.5;
const MONEY_DOT_SIZE = 1.1;
const MONEY_DOT_INSET_X = 0.6;
const MONEY_DOT_INSET_Y = 1.1;
const MONEY_DOT_CORNER_BY_COLOR: Record<PlayerColor, 'tl' | 'tr' | 'bl' | 'br'> = {
  red: 'tl',
  blu: 'tr',
  green: 'bl',
  yellow: 'br',
};

function moneyDotPoint(cellCenter: Point, color: PlayerColor): Point {
  const cellLeft = cellCenter.xPct - MONEY_CELL_WIDTH / 2;
  const cellRight = cellCenter.xPct + MONEY_CELL_WIDTH / 2;
  const cellTop = MONEY_CELL_TOP;
  const cellBottom = MONEY_CELL_TOP + MONEY_CELL_HEIGHT;
  const corner = MONEY_DOT_CORNER_BY_COLOR[color];
  return {
    xPct: corner === 'tl' || corner === 'bl' ? cellLeft + MONEY_DOT_INSET_X : cellRight - MONEY_DOT_INSET_X,
    yPct: corner === 'tl' || corner === 'tr' ? cellTop + MONEY_DOT_INSET_Y : cellBottom - MONEY_DOT_INSET_Y,
  };
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
// board (place a Hood, target an on-map officer, or — 2026-08-16 — a
// pawn already standing where a Buy is legal, always exactly 1 candidate
// dope type per pawn since a Hood has one top-of-stack good) — the
// designer asked that these be clicked directly on the board instead of
// picked from the text list. "move_criminal"/"sell_dope" get their own
// two-stage components below (pick the pawn, then disambiguate if it has
// more than one legal option) instead of this single-stage one. Others
// (which card to use, hand discards, Poker, ...) keep the plain list
// only, for now — being tackled one at a time.
function boardPointForOption(
  decisionType: string,
  option: DecisionOptionResponse,
  officerLocation: Map<string, Point>,
  gambleSlotPoint: (cardId: string) => Point | null,
  marketingTargetPoint: (dopeType: string, delta: number) => Point | null,
): Point | null {
  const payload = option.payload;
  switch (decisionType) {
    case 'place_criminal':
      return HOOD_POSITION[payload.hood_id as string] ?? null;
    case 'corrupt_officer':
    case 'buy_officer':
      return officerLocation.get(payload.officer_id as string) ?? null;
    case 'place_poker_bet':
      return gambleSlotPoint(payload.card_id as string);
    case 'play_marketing_card':
      return marketingTargetPoint(payload.dope_type as string, payload.delta as number);
    default:
      return null;
  }
}

// Place Criminal glows the whole Hood; Corrupt/Buy Officer glows the much
// smaller officer badge; Marketing glows the price track's own small
// token — each gets a ring sized to hug that specific target instead of
// one size for all (designer's request, 2026-08-16: hoods should halo
// the flower's own white outline, officers/goods a tight halo around the
// object itself, "un po più piccoli di adesso").
function highlightSizeFor(decisionType: string): number {
  if (decisionType === 'play_marketing_card') return PRICE_HIGHLIGHT_SIZE;
  if (decisionType === 'corrupt_officer' || decisionType === 'buy_officer') {
    return OFFICER_HIGHLIGHT_SIZE;
  }
  return HOOD_HIGHLIGHT_SIZE;
}

// A Hood's own 5-petal flower art is ~15% of board width across its outer
// white border (measured directly against the board art, 2026-08-16) —
// sized so the ring traces just outside that border instead of sitting
// well inside it on the flower's central hub.
const HOOD_HIGHLIGHT_SIZE = 16;
// Just outside a Cop/Fed badge (OFFICER_BADGE_SIZE 2.4) — a tight halo
// around the object itself, not a big ring swallowing its whole Hood.
const OFFICER_HIGHLIGHT_SIZE = 3.2;
// Much smaller than a Hood-sized ring (designer's request, 2026-08-16) —
// these sit right on top of the price track's own small token
// (PRICE_TOKEN_ASSET, rendered at 2.2%), so a full-size ring would
// swallow several of a track's neighboring steps at once.
const PRICE_HIGHLIGHT_SIZE = 2;

function BoardHighlights({
  decision,
  selected,
  onToggle,
  officerLocation,
  gambleSlotPoint,
  marketingTargetPoint,
}: {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  officerLocation: Map<string, Point>;
  gambleSlotPoint: (cardId: string) => Point | null;
  marketingTargetPoint: (dopeType: string, delta: number) => Point | null;
}) {
  const optionsByPointKey = new Map<string, { point: Point; options: DecisionOptionResponse[] }>();
  for (const option of decision.options) {
    const point = boardPointForOption(
      decision.decision_type,
      option,
      officerLocation,
      gambleSlotPoint,
      marketingTargetPoint,
    );
    if (!point) continue;
    const key = `${point.xPct},${point.yPct}`;
    const entry = optionsByPointKey.get(key) ?? { point, options: [] };
    entry.options.push(option);
    optionsByPointKey.set(key, entry);
  }
  if (optionsByPointKey.size === 0) return null;

  const size = highlightSizeFor(decision.decision_type);

  return (
    <>
      {Array.from(optionsByPointKey.entries()).map(([key, { point, options }]) => {
        const selectedHere = options.filter((o) => selected.includes(o.option_id));
        const unselectedHere = options.filter((o) => !selected.includes(o.option_id));
        function handleClick() {
          // Several duplicate options can share one point (e.g. stacking
          // multiple Stonks on the same Dope type/direction) — each click
          // adds one more, up to this point's own duplicates and the
          // decision's overall budget; once maxed, clicking again removes
          // the last one added instead, so repeated clicks step the count
          // up and back down rather than just toggling a single option.
          if (unselectedHere.length > 0 && selected.length < decision.max_selections) {
            onToggle(unselectedHere[0].option_id);
          } else if (selectedHere.length > 0) {
            onToggle(selectedHere[selectedHere.length - 1].option_id);
          }
        }
        const delta = options[0].payload.delta as number | undefined;
        const isMarketing = decision.decision_type === 'play_marketing_card';
        return (
          <div
            key={key}
            className={'board-highlight' + (selectedHere.length > 0 ? ' board-highlight--selected' : '')}
            style={{
              left: `${point.xPct}%`,
              top: `${point.yPct}%`,
              width: `${size}%`,
            }}
            onClick={handleClick}
            title={options[0].label_key}
          >
            {isMarketing && (
              <span className="board-highlight__symbol">{delta === 1 ? '+' : '−'}</span>
            )}
            {selectedHere.length > 0 && <span className="board-highlight__count">{selectedHere.length}</span>}
          </div>
        );
      })}
    </>
  );
}

// Where a Marketing Stonk allocation would land: one track step up/down
// from the type's current price token, per PRICE_TOKEN_POSITION's own
// discrete (price -> point) map. Clamped exactly like the backend's own
// step_price (steps beyond either end are legal no-ops, not errors), so
// an already-maxed/minned track just re-highlights the current token.
function marketingTargetPoint(
  dopeType: string,
  delta: number,
  currentPriceByDopeType: Record<string, number>,
): Point | null {
  const track = PRICE_TOKEN_POSITION[dopeType];
  if (!track) return null;
  const prices = Object.keys(track)
    .map(Number)
    .sort((a, b) => a - b);
  const index = prices.indexOf(currentPriceByDopeType[dopeType]);
  if (index < 0) return null;
  const targetIndex = Math.max(0, Math.min(prices.length - 1, index + delta));
  return track[prices[targetIndex]] ?? null;
}

// A tight halo around a pawn/Dope pile's own edge, not a big ring
// swallowing the whole petal (designer's request, 2026-08-16 — "un po
// più piccoli di adesso").
const PAWN_HIGHLIGHT_SIZE = 3.4;

// Where a specific pawn's own token currently sits on the board — the
// same slot logic BoardView's own rendering below uses for Criminal
// petals / Den slots, reused here so a highlight lands exactly on top of
// the pawn it refers to. `petalSlotByPawnId` is the *stable* per-pawn
// slot assignment (see `assignPetalSlots`), not a freshly-recomputed
// array index — using an index instead would make a highlight jump to a
// different petal whenever an unrelated pawn entered/left the same Hood.
function pawnBoardPoint(
  pawnId: string,
  petalSlotByPawnId: Map<string, number>,
  denGamblerPawnIds: string[],
  pawnById: Map<string, PublicPawnResponse>,
): Point | null {
  const pawn = pawnById.get(pawnId);
  if (!pawn) return null;
  if (pawn.role === 'criminal' && pawn.hood_id) {
    const petals = HOOD_PETAL_POSITION[pawn.hood_id];
    const slot = petalSlotByPawnId.get(pawnId);
    return petals && slot !== undefined ? (petals[slot] ?? null) : null;
  }
  if (pawn.role === 'gambler') {
    const index = denGamblerPawnIds.indexOf(pawnId);
    return index >= 0 ? (DEN_SLOT_POSITION[index] ?? null) : null;
  }
  if (pawn.role === 'link' && pawn.contact_id && pawn.link_level) {
    const slots = CONTACT_LINK_SLOT_POSITION[pawn.contact_id];
    return slots ? (slots[pawn.link_level - 1] ?? null) : null;
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
  petalSlotByPawnId,
  pawnById,
  denGamblerPawnIds,
}: {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  petalSlotByPawnId: Map<string, number>;
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
    const stagedPoint = pawnBoardPoint(stagedPawnId, petalSlotByPawnId, denGamblerPawnIds, pawnById);
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
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${HOOD_HIGHLIGHT_SIZE}%` }}
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
        const point = pawnBoardPoint(pawnId, petalSlotByPawnId, denGamblerPawnIds, pawnById);
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

// Sell Dope: clicking a pawn sells immediately *unless* it has more than
// one legal (dope_type, Spot) option — which happens when the player
// holds both goods a Contact's 2 Spots accept and stands a Criminal in
// that Contact's Hood — in which case a second click on the Spot itself
// disambiguates which one (designer's request, 2026-08-16).
function SellDopeHighlights({
  decision,
  selected,
  onToggle,
  petalSlotByPawnId,
  pawnById,
  denGamblerPawnIds,
}: {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  petalSlotByPawnId: Map<string, number>;
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

  const optionsByPawn = new Map<string, DecisionOptionResponse[]>();
  for (const option of decision.options) {
    const pawnId = option.payload.pawn_id as string;
    if (committedPawnIds.has(pawnId)) continue;
    const list = optionsByPawn.get(pawnId) ?? [];
    list.push(option);
    optionsByPawn.set(pawnId, list);
  }

  if (stagedPawnId && optionsByPawn.has(stagedPawnId)) {
    const stagedPoint = pawnBoardPoint(stagedPawnId, petalSlotByPawnId, denGamblerPawnIds, pawnById);
    const spotOptions = optionsByPawn.get(stagedPawnId) ?? [];
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
        {spotOptions.map((option) => {
          const point = SPOT_POSITION[option.payload.spot_id as string];
          if (!point) return null;
          return (
            <div
              key={option.option_id}
              className="board-highlight"
              style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${PAWN_HIGHLIGHT_SIZE}%` }}
              onClick={() => {
                onToggle(option.option_id);
                setStagedPawnId(null);
              }}
              title={option.label_key}
            />
          );
        })}
      </>
    );
  }

  return (
    <>
      {Array.from(optionsByPawn.entries()).map(([pawnId, options]) => {
        const point = pawnBoardPoint(pawnId, petalSlotByPawnId, denGamblerPawnIds, pawnById);
        if (!point) return null;
        return (
          <div
            key={pawnId}
            className="board-highlight"
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${PAWN_HIGHLIGHT_SIZE}%` }}
            onClick={() => {
              if (options.length === 1) {
                onToggle(options[0].option_id);
              } else {
                setStagedPawnId(pawnId);
              }
            }}
            title="Vendi da questo Criminale"
          />
        );
      })}
    </>
  );
}

// Buy Dope gets the same two-stage-conditional flow as Sell Dope above,
// but disambiguating by *Hood* instead of Spot: a Link counts as
// presence in both of its Contact's Hoods (game designer, 2026-08-15),
// and — unlike Sell Dope's Spots, which are Contact- not Hood-scoped —
// each Hood has its own independent stock/price, so a Link with legal
// stock at both needs a real choice. A Criminal always has exactly 1
// candidate Hood (its own location), so it still submits on the first
// click, same as before this existed.
function BuyDopeHighlights({
  decision,
  selected,
  onToggle,
  petalSlotByPawnId,
  pawnById,
  denGamblerPawnIds,
}: {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  petalSlotByPawnId: Map<string, number>;
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

  const optionsByPawn = new Map<string, DecisionOptionResponse[]>();
  for (const option of decision.options) {
    const pawnId = option.payload.pawn_id as string;
    if (committedPawnIds.has(pawnId)) continue;
    const list = optionsByPawn.get(pawnId) ?? [];
    list.push(option);
    optionsByPawn.set(pawnId, list);
  }

  if (stagedPawnId && optionsByPawn.has(stagedPawnId)) {
    const stagedPoint = pawnBoardPoint(stagedPawnId, petalSlotByPawnId, denGamblerPawnIds, pawnById);
    const hoodOptions = optionsByPawn.get(stagedPawnId) ?? [];
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
        {hoodOptions.map((option) => {
          const point = HOOD_POSITION[option.payload.hood_id as string];
          if (!point) return null;
          return (
            <div
              key={option.option_id}
              className="board-highlight"
              style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${HOOD_HIGHLIGHT_SIZE}%` }}
              onClick={() => {
                onToggle(option.option_id);
                setStagedPawnId(null);
              }}
              title={option.label_key}
            />
          );
        })}
      </>
    );
  }

  return (
    <>
      {Array.from(optionsByPawn.entries()).map(([pawnId, options]) => {
        const point = pawnBoardPoint(pawnId, petalSlotByPawnId, denGamblerPawnIds, pawnById);
        if (!point) return null;
        return (
          <div
            key={pawnId}
            className="board-highlight"
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${PAWN_HIGHLIGHT_SIZE}%` }}
            onClick={() => {
              if (options.length === 1) {
                onToggle(options[0].option_id);
              } else {
                setStagedPawnId(pawnId);
              }
            }}
            title="Compra da questa pedina"
          />
        );
      })}
    </>
  );
}

// Corruption sub-actions (designer's request, 2026-08-16): DecisionPanel
// renders the "Sposta / Arresta / Requisisci / Fine" button row (stage
// 1); once one of those with more than 1 candidate is staged, this glows
// its board targets — an adjacent Hood/Spot for "move", an arrestable
// pawn for "arrest" — clicking one submits the ChooseCorruptionAction
// immediately (this decision is always single-select, one action per
// command, unlike the multi-select packages the other highlights build
// up before a separate Confirm).
function CorruptionActionHighlights({
  decision,
  stagedAction,
  onSubmit,
  petalSlotByPawnId,
  pawnById,
  denGamblerPawnIds,
}: {
  decision: PendingDecisionResponse;
  stagedAction: string;
  onSubmit: (selectedOptionIds: string[]) => void;
  petalSlotByPawnId: Map<string, number>;
  pawnById: Map<string, PublicPawnResponse>;
  denGamblerPawnIds: string[];
}) {
  const options = decision.options.filter((o) => o.payload.action === stagedAction);
  return (
    <>
      {options.map((option) => {
        const targetId = option.payload.target_id as string | null;
        if (!targetId) return null;
        // A Cop's "move" targets a Hood (big ring); a Fed's targets a
        // Spot, which is a small icon like a pawn — same distinction
        // BuyDope/SellDope already draw between the two location types.
        const isHoodTarget = stagedAction === 'move' && HOOD_POSITION[targetId] !== undefined;
        const point = isHoodTarget
          ? HOOD_POSITION[targetId]
          : stagedAction === 'move'
            ? (SPOT_POSITION[targetId] ?? null)
            : pawnBoardPoint(targetId, petalSlotByPawnId, denGamblerPawnIds, pawnById);
        if (!point) return null;
        const size = isHoodTarget ? HOOD_HIGHLIGHT_SIZE : PAWN_HIGHLIGHT_SIZE;
        return (
          <div
            key={option.option_id}
            className="board-highlight"
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${size}%` }}
            onClick={() => onSubmit([option.option_id])}
            title={option.label_key}
          />
        );
      })}
    </>
  );
}

// Spend Link for an extra action: always single-select (payload has no
// further sub-choice), so clicking a glowing Link pawn on its track
// submits immediately — "Salta" (skip) lives in DecisionPanel instead,
// since it has no board target of its own.
function SpendLinkHighlights({
  decision,
  onSubmit,
}: {
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
}) {
  return (
    <>
      {decision.options.map((option) => {
        const contactId = option.payload.contact_id as string;
        const linkLevel = option.payload.link_level as number;
        const point = CONTACT_LINK_SLOT_POSITION[contactId]?.[linkLevel - 1];
        if (!point) return null;
        return (
          <div
            key={option.option_id}
            className="board-highlight"
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${PAWN_HIGHLIGHT_SIZE}%` }}
            onClick={() => onSubmit([option.option_id])}
            title={option.label_key}
          />
        );
      })}
    </>
  );
}

// Choose Brawl Link evolution: like Spend Link, always single-select —
// clicking a glowing own-pawn in the Brawl's Hood submits immediately;
// "Passa" (skip) lives in DecisionPanel.
function BrawlLinkEvolutionHighlights({
  decision,
  onSubmit,
  petalSlotByPawnId,
  pawnById,
  denGamblerPawnIds,
}: {
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
  petalSlotByPawnId: Map<string, number>;
  pawnById: Map<string, PublicPawnResponse>;
  denGamblerPawnIds: string[];
}) {
  return (
    <>
      {decision.options.map((option) => {
        const pawnId = option.payload.pawn_id as string;
        const point = pawnBoardPoint(pawnId, petalSlotByPawnId, denGamblerPawnIds, pawnById);
        if (!point) return null;
        return (
          <div
            key={option.option_id}
            className="board-highlight"
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${PAWN_HIGHLIGHT_SIZE}%` }}
            onClick={() => onSubmit([option.option_id])}
            title={option.label_key}
          />
        );
      })}
    </>
  );
}

// Choose Brawl relocation destination: an unrevealed Hood, so it has no
// art of its own on the board (BoardView's main render loop only draws
// revealed ones) — still glow a plain marker at its center so it's
// clickable, same immediate-submit single-select pattern as the other
// Brawl sub-decisions.
function BrawlRelocationHighlights({
  decision,
  onSubmit,
}: {
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
}) {
  return (
    <>
      {decision.options.map((option) => {
        const point = HOOD_POSITION[option.payload.hood_id as string];
        if (!point) return null;
        return (
          <div
            key={option.option_id}
            className="board-highlight"
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${HOOD_HIGHLIGHT_SIZE}%` }}
            onClick={() => onSubmit([option.option_id])}
            title={option.label_key}
          />
        );
      })}
    </>
  );
}

const JOB_CELL_HIGHLIGHT_SIZE = 3;

// Choose Job reward: the open columns on that Job's own row of the
// board's Job grid glow — clicking one submits immediately (always
// single-select, never skippable: claiming a reward is mandatory once a
// Job completes).
// A "bi-color" Job (job_def.contact_ids has 2 entries — 4 of the 9 Jobs,
// e.g. job_04 politici+preti) offers one option per (column, contact)
// combination, so the same board cell can have 2 options stacked at the
// identical position — clicking straight through to onSubmit like a
// single-contact Job would silently always pick whichever happened to
// render last in the DOM, with no way to choose the other Contact
// (designer's request, 2026-08-16: this must be a real choice). Mirrors
// Move/Sell/Buy's own two-stage-conditional pattern: click the cell,
// then — only when it actually has more than one Contact candidate —
// disambiguate by clicking one of the candidate Contacts' own link-track
// slots (the same "one anchor point per Contact" already used to render
// player Links).
function JobRewardHighlights({
  decision,
  onSubmit,
}: {
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
}) {
  // Keyed by job_id + " " + column_index (not a plain "_" join —
  // job_id already contains underscores itself, e.g. "job_04", which
  // broke a naive split('_') into the wrong parts).
  const [stagedCellKey, setStagedCellKey] = useState<string | null>(null);

  useEffect(() => {
    setStagedCellKey(null);
  }, [decision.decision_id]);

  const cellKey = (jobId: string, columnIndex: number) => `${jobId} ${columnIndex}`;

  const optionsByCell = new Map<string, DecisionOptionResponse[]>();
  for (const option of decision.options) {
    const jobId = option.payload.job_id as string;
    const columnIndex = option.payload.column_index as number;
    const key = cellKey(jobId, columnIndex);
    const list = optionsByCell.get(key) ?? [];
    list.push(option);
    optionsByCell.set(key, list);
  }

  if (stagedCellKey && optionsByCell.has(stagedCellKey)) {
    const contactOptions = optionsByCell.get(stagedCellKey) ?? [];
    const [jobId, columnIndexStr] = stagedCellKey.split(' ');
    const stagedPoint = JOB_BOARD_CELL_POSITION[jobId]?.[Number(columnIndexStr)];
    return (
      <>
        {stagedPoint && (
          <div
            className="board-highlight board-highlight--selected"
            style={{
              left: `${stagedPoint.xPct}%`,
              top: `${stagedPoint.yPct}%`,
              width: `${JOB_CELL_HIGHLIGHT_SIZE}%`,
            }}
            onClick={() => setStagedCellKey(null)}
            title="Annulla selezione"
          />
        )}
        {contactOptions.map((option) => {
          const contactId = option.payload.contact_id as string;
          const point = CONTACT_LINK_SLOT_POSITION[contactId]?.[0];
          if (!point) return null;
          return (
            <div
              key={option.option_id}
              className="board-highlight"
              style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${PAWN_HIGHLIGHT_SIZE}%` }}
              onClick={() => onSubmit([option.option_id])}
              title={option.label_key}
            />
          );
        })}
      </>
    );
  }

  return (
    <>
      {Array.from(optionsByCell.entries()).map(([key, options]) => {
        const jobId = options[0].payload.job_id as string;
        const columnIndex = options[0].payload.column_index as number;
        const point = JOB_BOARD_CELL_POSITION[jobId]?.[columnIndex];
        if (!point) return null;
        return (
          <div
            key={key}
            className="board-highlight"
            style={{
              left: `${point.xPct}%`,
              top: `${point.yPct}%`,
              width: `${JOB_CELL_HIGHLIGHT_SIZE}%`,
            }}
            onClick={() => {
              if (options.length === 1) {
                onSubmit([options[0].option_id]);
              } else {
                setStagedCellKey(key);
              }
            }}
            title={options[0].label_key}
          />
        );
      })}
    </>
  );
}

// Decision types with their own dedicated highlight component above,
// routed to explicitly further down — everything else falls back to the
// generic single-stage BoardHighlights (or, for decision types with no
// board-resolvable options at all, no highlight rendering whatsoever).
const DEDICATED_HIGHLIGHT_DECISION_TYPES = new Set([
  'move_criminal',
  'buy_dope',
  'sell_dope',
  'corruption_action',
  'spend_link_for_extra_action',
  'choose_brawl_link_evolution',
  'choose_brawl_relocation_destination',
  'choose_job_reward',
]);

// Which petal slot (0-4) each Criminal pawn renders at in its own Hood,
// kept stable across renders instead of recomputed from the pawn's
// current index among its Hood-mates (designer's request, 2026-08-17:
// "è possibile che un pawn non cambi posizione se ne entrano/escono
// altri?") — filtering `view.pawns` fresh every render and using the
// resulting array index as the petal slot meant a pawn with no move of
// its own could visually jump to a different petal whenever a *different*
// pawn arrived at or left the same Hood, since removing/adding an entry
// shifts every later index in the filtered list. A pawn now keeps
// whichever slot it was first assigned in that Hood for as long as it
// stays there; a newly-arriving pawn takes the lowest slot nobody
// currently in the Hood holds (which can reuse a slot just vacated by an
// unrelated pawn leaving, but never bumps an already-placed one).
function assignPetalSlots(
  slotsByHood: Map<string, Map<string, number>>,
  hoodId: string,
  pawns: PublicPawnResponse[],
): Map<string, number> {
  let slotByPawn = slotsByHood.get(hoodId);
  if (!slotByPawn) {
    slotByPawn = new Map();
    slotsByHood.set(hoodId, slotByPawn);
  }
  const currentPawnIds = new Set(pawns.map((p) => p.pawn_id));
  for (const pawnId of Array.from(slotByPawn.keys())) {
    if (!currentPawnIds.has(pawnId)) slotByPawn.delete(pawnId);
  }
  const usedSlots = new Set(slotByPawn.values());
  for (const pawn of pawns) {
    if (slotByPawn.has(pawn.pawn_id)) continue;
    let slot = 0;
    while (usedSlots.has(slot)) slot++;
    slotByPawn.set(pawn.pawn_id, slot);
    usedSlots.add(slot);
  }
  return slotByPawn;
}

export function BoardView({
  view,
  decision,
  selected,
  onToggle,
  onSubmit,
  stagedCorruptionAction,
}: BoardViewProps) {
  const petalSlotsRef = useRef<Map<string, Map<string, number>>>(new Map());
  const pawnsByHood = new Map<string, PublicPawnResponse[]>();
  for (const pawn of view.pawns) {
    if (pawn.role !== 'criminal' || !pawn.hood_id) continue;
    const list = pawnsByHood.get(pawn.hood_id) ?? [];
    list.push(pawn);
    pawnsByHood.set(pawn.hood_id, list);
  }
  // Flat pawn_id -> stable petal slot (0-4), one Hood's worth at a time —
  // both the token render loop below and `pawnBoardPoint` (used by every
  // board-highlight component) key off this instead of an array index,
  // so a pawn keeps its own petal regardless of who else enters/leaves
  // the same Hood.
  const petalSlotByPawnId = new Map<string, number>();
  for (const [hoodId, criminals] of pawnsByHood) {
    const slotByPawn = assignPetalSlots(petalSlotsRef.current, hoodId, criminals);
    for (const [pawnId, slot] of slotByPawn) petalSlotByPawnId.set(pawnId, slot);
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

      {/* Criminal pawns render as one flat, board-wide list (not nested
          inside each Hood's own block below) so a pawn moving between
          Hoods keeps the exact same DOM node across renders — React
          matches it by `key={pawn.pawn_id}` regardless of which Hood it
          logically belongs to now, letting .board-token--pawn's CSS
          transition animate the left/top change instead of the token
          just popping to its new spot (designer's request, 2026-08-16:
          "un'animazione della pedina che si muove da un quartiere a un
          altro"). */}
      {Array.from(pawnsByHood.entries()).flatMap(([hoodId, criminals]) => {
        const petals = HOOD_PETAL_POSITION[hoodId];
        if (!petals) return [];
        return criminals.flatMap((pawn) => {
          const slot = petalSlotByPawnId.get(pawn.pawn_id);
          if (slot === undefined || slot >= petals.length) return [];
          return [
            <Token
              key={pawn.pawn_id}
              point={petals[slot]}
              src={pawnAssetForPlayer(pawn.owner_player_id)}
              alt={pawn.pawn_id}
              size={PAWN_SIZE}
              className="board-token--pawn"
            />,
          ];
        });
      })}

      {view.hoods
        .filter((h) => h.revealed)
        .map((hood) => {
          const center = HOOD_POSITION[hood.hood_id];
          const petals = HOOD_PETAL_POSITION[hood.hood_id];
          if (!center || !petals) return null;
          return (
            <div key={hood.hood_id}>
              {hood.dope_stack.length > 0 && (
                <DopePile point={center} dopeType={hood.dope_stack[0]} count={hood.dope_stack.length} />
              )}
              {hood.cop_ids.length > 0 && (
                <>
                  <Token
                    point={officerBadgePoint(center)}
                    src={OFFICER_ASSET.cop}
                    alt={`${hood.cop_ids.length} cop(s)`}
                    size={OFFICER_BADGE_SIZE}
                  />
                  {hood.cop_ids.length > 1 && (
                    <CountBadge point={officerCountBadgePoint(center)} count={hood.cop_ids.length} />
                  )}
                </>
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
              <>
                <Token
                  point={officerBadgePoint(point)}
                  src={OFFICER_ASSET.fed}
                  alt={`${spot.fed_ids.length} fed(s)`}
                  size={OFFICER_BADGE_SIZE}
                />
                {spot.fed_ids.length > 1 && (
                  <CountBadge point={officerCountBadgePoint(point)} count={spot.fed_ids.length} />
                )}
              </>
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
        // Each Jail slot is one big circle (confiscated Dope, normal
        // size — same as everywhere else) with a smaller circle printed
        // concentrically inside it (the Rat pawn) — both share the
        // slot's own single calibrated center; the pawn renders after
        // the Dope so it sits on top, not offset left/right at matching
        // sizes like before (designer's request, 2026-08-16).
        return (
          <div key={slot.index}>
            {slot.confiscated_dope_type && (
              <Token
                point={point}
                src={DOPE_ASSET[slot.confiscated_dope_type]}
                alt={slot.confiscated_dope_type}
                size={DOPE_PILE_SIZE}
              />
            )}
            {ratPawn && (
              <Token
                point={point}
                src={pawnAssetForPlayer(ratPawn.owner_player_id)}
                alt={ratPawn.pawn_id}
                size={JAIL_PAWN_SIZE}
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

      {/* Bank-supply counter, near the printed Dope icon at each price
          track's own fixed end (designer's requests, 2026-08-23, in
          order: "vicino ai prezzi"; then "indipendente dal movimento del
          segnalino, tutto a sinistra vicino al bordo bianco della
          merce"; then corrected again — "vanno spostati a destra vicino
          al bordo del tabellone, mantieni l'altezza attuale"). Anchored
          to the track's *highest* price cell — where the board's own
          printed icon sits, confirmed against BOARD_v14_b.png (e.g.
          rana's {0,1,3,5}, icon at 5) — not the live current price, so
          this never moves as prices change and keeps the same height
          (`anchor.yPct`, untouched) the "a sinistra" version already
          had; only the X shifts, now right toward the board's own edge
          instead of left. How many units of that Dope type are still
          unplaced in the shared bank (`rules/economy.py::
          _restock_hood`'s own `min(3, banca rimasta)`), not per-Hood/
          per-player state. */}
      {Object.keys(PRICE_TOKEN_POSITION).map((dopeType) => {
        const track = PRICE_TOKEN_POSITION[dopeType];
        const maxPriceKey = Math.max(...Object.keys(track).map(Number));
        const anchor = track[maxPriceKey];
        if (!anchor) return null;
        const remaining = view.supply_remaining_by_dope_type[dopeType] ?? 0;
        return (
          <span
            key={dopeType}
            className="board-token board-supply-count"
            style={{
              left: `${anchor.xPct + SUPPLY_COUNT_OFFSET_PCT}%`,
              top: `${anchor.yPct}%`,
            }}
            title={`${dopeType}: ${remaining} in banca`}
          >
            {remaining}
          </span>
        );
      })}

      {view.players.map((player) => {
        const cellCenter = moneyTrackPosition(player.money);
        const lap = moneyTrackLap(player.money);
        const color = playerColorForId(player.player_id);
        const point = moneyDotPoint(cellCenter, color);
        return (
          <img
            key={player.player_id}
            src={moneyMarkerAssetForPlayer(player.player_id, lap >= 1)}
            alt={`${player.player_id}: $${player.money}`}
            className="board-token board-token--money-dot"
            style={{
              left: `${point.xPct}%`,
              top: `${point.yPct}%`,
              width: `${MONEY_DOT_SIZE}%`,
            }}
          />
        );
      })}

      {decision && selected && onToggle && decision.decision_type === 'move_criminal' && (
        <MoveCriminalHighlights
          decision={decision}
          selected={selected}
          onToggle={onToggle}
          petalSlotByPawnId={petalSlotByPawnId}
          pawnById={pawnById}
          denGamblerPawnIds={view.den_gambler_pawn_ids}
        />
      )}
      {decision && selected && onToggle && decision.decision_type === 'buy_dope' && (
        <BuyDopeHighlights
          decision={decision}
          selected={selected}
          onToggle={onToggle}
          petalSlotByPawnId={petalSlotByPawnId}
          pawnById={pawnById}
          denGamblerPawnIds={view.den_gambler_pawn_ids}
        />
      )}
      {decision && selected && onToggle && decision.decision_type === 'sell_dope' && (
        <SellDopeHighlights
          decision={decision}
          selected={selected}
          onToggle={onToggle}
          petalSlotByPawnId={petalSlotByPawnId}
          pawnById={pawnById}
          denGamblerPawnIds={view.den_gambler_pawn_ids}
        />
      )}
      {decision && onSubmit && stagedCorruptionAction && decision.decision_type === 'corruption_action' && (
        <CorruptionActionHighlights
          decision={decision}
          stagedAction={stagedCorruptionAction}
          onSubmit={onSubmit}
          petalSlotByPawnId={petalSlotByPawnId}
          pawnById={pawnById}
          denGamblerPawnIds={view.den_gambler_pawn_ids}
        />
      )}
      {decision && onSubmit && decision.decision_type === 'spend_link_for_extra_action' && (
        <SpendLinkHighlights decision={decision} onSubmit={onSubmit} />
      )}
      {decision && onSubmit && decision.decision_type === 'choose_brawl_link_evolution' && (
        <BrawlLinkEvolutionHighlights
          decision={decision}
          onSubmit={onSubmit}
          petalSlotByPawnId={petalSlotByPawnId}
          pawnById={pawnById}
          denGamblerPawnIds={view.den_gambler_pawn_ids}
        />
      )}
      {decision && onSubmit && decision.decision_type === 'choose_brawl_relocation_destination' && (
        <BrawlRelocationHighlights decision={decision} onSubmit={onSubmit} />
      )}
      {decision && onSubmit && decision.decision_type === 'choose_job_reward' && (
        <JobRewardHighlights decision={decision} onSubmit={onSubmit} />
      )}
      {decision &&
        selected &&
        onToggle &&
        !DEDICATED_HIGHLIGHT_DECISION_TYPES.has(decision.decision_type) && (
          <BoardHighlights
            decision={decision}
            selected={selected}
            onToggle={onToggle}
            officerLocation={officerLocation}
            gambleSlotPoint={(cardId) => {
              const i = view.poker_launched_card_ids.indexOf(cardId);
              return i >= 0 ? (GAMBLE_SLOT_POSITION[i] ?? null) : null;
            }}
            marketingTargetPoint={(dopeType, delta) =>
              marketingTargetPoint(dopeType, delta, view.current_price_by_dope_type)
            }
          />
        )}
    </div>
  );
}
