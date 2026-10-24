// Shapes of the multiplayer API (docs/api/multiplayer.md) — rooms and seats only for now; the
// in-game shapes (view, events, answers) arrive with the game screen.

export type RoomStatus = 'lobby' | 'running' | 'finished' | 'closed';

export interface SeatResponse {
  seat_index: number;
  player_id: string;
  controller_type: 'human' | 'bot';
  nickname: string | null;
  /** A human seat somebody has taken (a bot seat is always occupied). */
  occupied: boolean;
  is_host: boolean;
  left: boolean;
}

export interface RoomResponse {
  room_code: string;
  status: RoomStatus;
  ruleset: string;
  human_seats: number;
  bot_policy: string;
  game_id: string | null;
  seats: SeatResponse[];
  /** The caller's own seat — only when the request carried a valid token for this room. */
  me: SeatResponse | null;
}

export interface CredentialsResponse {
  room_code: string;
  game_id: string | null;
  seat_index: number;
  player_id: string;
  seat_token: string;
}

export interface LeaveResponse {
  room: RoomResponse | null;
}

/** What the browser keeps to get its seat back after a reload. The token is a secret: it lives
 *  in local storage only — never in a URL, a log or anything shared. */
export interface StoredSeat {
  room_code: string;
  game_id: string | null;
  seat_token: string;
  seat_index: number;
  player_id: string;
  nickname: string;
}
