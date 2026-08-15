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
  onSubmit?: (selectedOptionIds: string[]) => void;
  stagedCorruptionAction?: string | null;
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
  pawnPoint: (pawnId: string) => Point | null,
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
    case 'buy_dope':
      return pawnPoint(payload.pawn_id as string);
    case 'place_poker_bet':
      return gambleSlotPoint(payload.card_id as string);
    case 'play_marketing_card':
      return marketingTargetPoint(payload.dope_type as string, payload.delta as number);
    default:
      return null;
  }
}

// Place/Corrupt/Buy Officer glow the whole Hood/officer badge; Buy Dope
// glows the specific pawn making the trade; Marketing glows the price
// track's own small token, so all three but the first get a smaller ring.
function highlightSizeFor(decisionType: string): number {
  if (decisionType === 'buy_dope') return PAWN_HIGHLIGHT_SIZE;
  if (decisionType === 'play_marketing_card') return PRICE_HIGHLIGHT_SIZE;
  return HIGHLIGHT_SIZE;
}

const HIGHLIGHT_SIZE = 7;
const PRICE_HIGHLIGHT_SIZE = 3.5;

function BoardHighlights({
  decision,
  selected,
  onToggle,
  officerLocation,
  pawnPoint,
  gambleSlotPoint,
  marketingTargetPoint,
}: {
  decision: PendingDecisionResponse;
  selected: string[];
  onToggle: (optionId: string) => void;
  officerLocation: Map<string, Point>;
  pawnPoint: (pawnId: string) => Point | null;
  gambleSlotPoint: (cardId: string) => Point | null;
  marketingTargetPoint: (dopeType: string, delta: number) => Point | null;
}) {
  const optionsByPointKey = new Map<string, { point: Point; options: DecisionOptionResponse[] }>();
  for (const option of decision.options) {
    const point = boardPointForOption(
      decision.decision_type,
      option,
      officerLocation,
      pawnPoint,
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

// Sell Dope: clicking a pawn sells immediately *unless* it has more than
// one legal (dope_type, Spot) option — which happens when the player
// holds both goods a Contact's 2 Spots accept and stands a Criminal in
// that Contact's Hood — in which case a second click on the Spot itself
// disambiguates which one (designer's request, 2026-08-16).
function SellDopeHighlights({
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

  const optionsByPawn = new Map<string, DecisionOptionResponse[]>();
  for (const option of decision.options) {
    const pawnId = option.payload.pawn_id as string;
    if (committedPawnIds.has(pawnId)) continue;
    const list = optionsByPawn.get(pawnId) ?? [];
    list.push(option);
    optionsByPawn.set(pawnId, list);
  }

  if (stagedPawnId && optionsByPawn.has(stagedPawnId)) {
    const stagedPoint = pawnBoardPoint(stagedPawnId, pawnsByHood, denGamblerPawnIds, pawnById);
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
        const point = pawnBoardPoint(pawnId, pawnsByHood, denGamblerPawnIds, pawnById);
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
  pawnsByHood,
  pawnById,
  denGamblerPawnIds,
}: {
  decision: PendingDecisionResponse;
  stagedAction: string;
  onSubmit: (selectedOptionIds: string[]) => void;
  pawnsByHood: Map<string, PublicPawnResponse[]>;
  pawnById: Map<string, PublicPawnResponse>;
  denGamblerPawnIds: string[];
}) {
  const options = decision.options.filter((o) => o.payload.action === stagedAction);
  return (
    <>
      {options.map((option) => {
        const targetId = option.payload.target_id as string | null;
        if (!targetId) return null;
        const point =
          stagedAction === 'move'
            ? (HOOD_POSITION[targetId] ?? SPOT_POSITION[targetId] ?? null)
            : pawnBoardPoint(targetId, pawnsByHood, denGamblerPawnIds, pawnById);
        if (!point) return null;
        const size = stagedAction === 'arrest' ? PAWN_HIGHLIGHT_SIZE : HIGHLIGHT_SIZE;
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
  pawnsByHood,
  pawnById,
  denGamblerPawnIds,
}: {
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
  pawnsByHood: Map<string, PublicPawnResponse[]>;
  pawnById: Map<string, PublicPawnResponse>;
  denGamblerPawnIds: string[];
}) {
  return (
    <>
      {decision.options.map((option) => {
        const pawnId = option.payload.pawn_id as string;
        const point = pawnBoardPoint(pawnId, pawnsByHood, denGamblerPawnIds, pawnById);
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
            style={{ left: `${point.xPct}%`, top: `${point.yPct}%`, width: `${HIGHLIGHT_SIZE}%` }}
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
function JobRewardHighlights({
  decision,
  onSubmit,
}: {
  decision: PendingDecisionResponse;
  onSubmit: (selectedOptionIds: string[]) => void;
}) {
  return (
    <>
      {decision.options.map((option) => {
        const jobId = option.payload.job_id as string;
        const columnIndex = option.payload.column_index as number;
        const point = JOB_BOARD_CELL_POSITION[jobId]?.[columnIndex];
        if (!point) return null;
        return (
          <div
            key={option.option_id}
            className="board-highlight"
            style={{
              left: `${point.xPct}%`,
              top: `${point.yPct}%`,
              width: `${JOB_CELL_HIGHLIGHT_SIZE}%`,
            }}
            onClick={() => onSubmit([option.option_id])}
            title={option.label_key}
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
  'sell_dope',
  'corruption_action',
  'spend_link_for_extra_action',
  'choose_brawl_link_evolution',
  'choose_brawl_relocation_destination',
  'choose_job_reward',
]);

export function BoardView({
  view,
  decision,
  selected,
  onToggle,
  onSubmit,
  stagedCorruptionAction,
}: BoardViewProps) {
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

      {decision && selected && onToggle && decision.decision_type === 'move_criminal' && (
        <MoveCriminalHighlights
          decision={decision}
          selected={selected}
          onToggle={onToggle}
          pawnsByHood={pawnsByHood}
          pawnById={pawnById}
          denGamblerPawnIds={view.den_gambler_pawn_ids}
        />
      )}
      {decision && selected && onToggle && decision.decision_type === 'sell_dope' && (
        <SellDopeHighlights
          decision={decision}
          selected={selected}
          onToggle={onToggle}
          pawnsByHood={pawnsByHood}
          pawnById={pawnById}
          denGamblerPawnIds={view.den_gambler_pawn_ids}
        />
      )}
      {decision && onSubmit && stagedCorruptionAction && decision.decision_type === 'corruption_action' && (
        <CorruptionActionHighlights
          decision={decision}
          stagedAction={stagedCorruptionAction}
          onSubmit={onSubmit}
          pawnsByHood={pawnsByHood}
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
          pawnsByHood={pawnsByHood}
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
            pawnPoint={(pawnId) => pawnBoardPoint(pawnId, pawnsByHood, view.den_gambler_pawn_ids, pawnById)}
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
