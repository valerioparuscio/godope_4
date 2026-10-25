import { playerTeamNameForId } from './assets';
import type { GameViewResponse } from './types';

// The engine's own placeholder for a seat created without a nickname ("Player 1"...): not a name
// anybody chose, so it never stands in for the gang.
const DEFAULT_DISPLAY_NAME = /^Player \d+$/;

/** How a player is called on screen (game designer, 2026-10-25): a human by their nickname, in a
 *  solo game and in a multiplayer one; a bot by its gang name ("Blue Bandits"). The gang's colour,
 *  pawns and portraits stay the seat's own either way. */
export function playerNameForId(view: Pick<GameViewResponse, 'players'>, playerId: string): string {
  const player = view.players.find((p) => p.player_id === playerId);
  if (player?.controller_type === 'human') {
    const nickname = player.display_name.trim();
    if (nickname && !DEFAULT_DISPLAY_NAME.test(nickname)) return nickname;
  }
  return playerTeamNameForId(playerId);
}
