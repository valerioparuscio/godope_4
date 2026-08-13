import {
  BOARD_BACKGROUND,
  DOPE_ASSET,
  OFFICER_ASSET,
  cardAssetUrl,
  pawnAssetForPlayer,
  repAssetForPlayer,
} from '../assets';
import {
  CONTACT_LINK_SLOT_POSITION,
  DEN_POSITION,
  GAMBLE_SLOT_POSITION,
  HOOD_PETAL_OFFSET,
  HOOD_POSITION,
  JAIL_SLOT_POSITION,
  moneyTrackPosition,
  type Point,
} from '../board-layout';
import type { GameViewResponse, PublicPawnResponse } from '../types';

interface BoardViewProps {
  view: GameViewResponse;
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
const DOPE_PILE_SIZE = 5.8;

export function BoardView({ view }: BoardViewProps) {
  const pawnsByHood = new Map<string, PublicPawnResponse[]>();
  for (const pawn of view.pawns) {
    if (pawn.role !== 'criminal' || !pawn.hood_id) continue;
    const list = pawnsByHood.get(pawn.hood_id) ?? [];
    list.push(pawn);
    pawnsByHood.set(pawn.hood_id, list);
  }
  const pawnById = new Map(view.pawns.map((p) => [p.pawn_id, p]));

  return (
    <div className="board-view">
      <img src={BOARD_BACKGROUND} alt="Tabellone" className="board-view__background" />

      {view.hoods
        .filter((h) => h.revealed)
        .map((hood) => {
          const center = HOOD_POSITION[hood.hood_id];
          if (!center) return null;
          const criminals = pawnsByHood.get(hood.hood_id) ?? [];
          return (
            <div key={hood.hood_id}>
              {criminals.slice(0, 5).map((pawn, i) => {
                const offset = HOOD_PETAL_OFFSET[i];
                return (
                  <Token
                    key={pawn.pawn_id}
                    point={{ xPct: center.xPct + offset.xPct, yPct: center.yPct + offset.yPct }}
                    src={pawnAssetForPlayer(pawn.owner_player_id)}
                    alt={pawn.pawn_id}
                    size={PAWN_SIZE}
                  />
                );
              })}
              {hood.dope_stack.length > 0 && (
                <>
                  <Token
                    point={center}
                    src={DOPE_ASSET[hood.dope_stack[0]]}
                    alt={`${hood.dope_stack.length}x ${hood.dope_stack[0]}`}
                    size={DOPE_PILE_SIZE}
                  />
                  <CountBadge
                    point={{ xPct: center.xPct + 2.2, yPct: center.yPct + 2.2 }}
                    count={hood.dope_stack.length}
                  />
                </>
              )}
              {hood.cop_ids.length > 0 && (
                <Token
                  point={{ xPct: center.xPct + 6.5, yPct: center.yPct - 8 }}
                  src={OFFICER_ASSET.cop}
                  alt={`${hood.cop_ids.length} cop(s)`}
                  size={3}
                />
              )}
            </div>
          );
        })}

      {view.den_gambler_pawn_ids.slice(0, 6).map((pawnId, i) => {
        const pawn = pawnById.get(pawnId);
        if (!pawn) return null;
        const angle = (i / 6) * 2 * Math.PI;
        return (
          <Token
            key={pawnId}
            point={{
              xPct: DEN_POSITION.xPct + Math.cos(angle) * 6,
              yPct: DEN_POSITION.yPct + Math.sin(angle) * 6,
            }}
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
    </div>
  );
}
