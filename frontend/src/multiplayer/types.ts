// Shapes of the multiplayer API (docs/api/multiplayer.md): rooms and seats, then the game itself
// (the player's view, the event log, answers).

import type { GameEventResponse, GameViewResponse } from '../types';

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
  /** Not answering: a bot plays this seat until its player comes back. */
  away?: boolean;
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

/** What one step of the game produced (a human's command, a bot's action...), already filtered for
 *  this player: hidden cards are `null`. `view` is this player's board right after the step. */
export interface EventBatchResponse {
  index: number;
  revision_from: number;
  revision_to: number;
  actor_player_id: string | null;
  segment_type:
    | 'game_start'
    | 'human_command'
    | 'bot_segment'
    | 'seat_left'
    | 'seat_away'
    | 'seat_returned';
  events: GameEventResponse[];
  /** null when the step is too old to still have its board: the client jumps to the next one. */
  view: GameViewResponse | null;
}

export interface MultiplayerViewResponse {
  room: RoomResponse;
  me: SeatResponse;
  revision: number;
  status: string;
  awaiting_player_id: string | null;
  view: GameViewResponse;
}

export interface EventsResponse {
  game_id: string;
  from_revision: number;
  current_revision: number;
  status: string;
  awaiting_player_id: string | null;
  requires_refresh: boolean;
  batches: EventBatchResponse[];
  view: GameViewResponse | null;
}

export interface AnswerResponse {
  ok: boolean;
  revision: number;
  status: string;
  awaiting_player_id: string | null;
  batches: EventBatchResponse[];
  view: GameViewResponse;
}
