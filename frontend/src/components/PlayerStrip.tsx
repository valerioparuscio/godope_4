import { DOPE_ASSET, OFFICER_ASSET, pawnAssetForPlayer, playerColorForId, skillAssetUrl } from '../assets';
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

export function PlayerStrip({ view, decision, selected = [], onToggle }: PlayerStripProps) {
  return (
    <div className="player-strip">
      {playersInTurnOrder(view).map((p) => (
        <div
          key={p.player_id}
          className={
            'player-card' +
            ` player-card--${playerColorForId(p.player_id)}` +
            (p.player_id === view.current_player_id ? ' player-card--active' : '')
          }
        >
          <div className="player-card__body">
            <div className="player-card__name">
              <img
                src={pawnAssetForPlayer(p.player_id)}
                alt=""
                className="inline-icon"
              />{' '}
              {p.player_id === view.current_player_id ? '▶ ' : ''}
              {p.display_name} ({p.controller_type})
            </div>
            {p.skill_ids.length > 0 && (
              <div className="player-card__skills">
                {p.skill_ids.map((skillId) => (
                  <img
                    key={skillId}
                    src={skillAssetUrl(skillId)}
                    alt={skillId}
                    title={skillId}
                    className="player-card__skill-icon"
                  />
                ))}
              </div>
            )}
            <div className="player-card__stats">
              <span>Mano: {p.hand_card_count}</span>
              <span>Chip poker: {p.poker_chip_count}</span>
              <span>Cops: {officersOwnedCount(view, p.player_id)}</span>
            </div>
            <div className="player-card__dope">
              {Object.entries(p.dope_counts).filter(([, count]) => count > 0).length === 0 ? (
                '-'
              ) : (
                Object.entries(p.dope_counts)
                  .filter(([, count]) => count > 0)
                  .map(([dopeType, count]) => (
                    <span key={dopeType} className="player-card__dope-item">
                      <img src={DOPE_ASSET[dopeType]} alt={dopeType} className="inline-icon" />
                      {count}
                    </span>
                  ))
              )}
            </div>
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
          </div>
          <div className="player-card__grit">
            {[1, 2, 3].map((value) => (
              <span
                key={value}
                className={
                  'player-card__grit-token' +
                  (p.available_grit_values.includes(value) ? '' : ' player-card__grit-token--used')
                }
              >
                {value}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
