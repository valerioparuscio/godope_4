import { BASE_URL } from '../api';
import type { HumanActionPlan } from '../types';
import type {
  AnswerResponse,
  CredentialsResponse,
  EventsResponse,
  LeaveResponse,
  MultiplayerViewResponse,
  RoomResponse,
} from './types';

/** A refusal from the multiplayer API: `code` is the stable identifier (docs/api/multiplayer.md),
 *  `status` the HTTP status; a network failure is not one of these (it stays a TypeError). */
export class MultiplayerApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'MultiplayerApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    let code = 'http_error';
    let message = `${response.status} ${response.statusText}`;
    let details: Record<string, unknown> = {};
    try {
      const body = (await response.json()) as {
        error?: string;
        message?: string;
        details?: Record<string, unknown>;
        detail?: unknown;
      };
      if (typeof body.error === 'string') {
        code = body.error;
        message = body.message ?? message;
        details = body.details ?? {};
      } else if (response.status === 422) {
        code = 'invalid_request';
      }
    } catch {
      // not JSON: keep the HTTP status text
    }
    throw new MultiplayerApiError(response.status, code, message, details);
  }
  return response.json() as Promise<T>;
}

const room = (code: string) => `/api/v1/rooms/${encodeURIComponent(code)}`;

/** Multiplayer plays the Easy Price rules, with the most capable bots on the empty seats. */
export function createRoom(nickname: string, humanSeats: number): Promise<CredentialsResponse> {
  return request<CredentialsResponse>('/api/v1/rooms', {
    method: 'POST',
    body: JSON.stringify({
      ruleset: 'easy_price',
      human_seats: humanSeats,
      bot_policy: 'heuristic',
      nickname,
    }),
  });
}

export function joinRoom(code: string, nickname: string): Promise<CredentialsResponse> {
  return request<CredentialsResponse>(`${room(code)}/join`, {
    method: 'POST',
    body: JSON.stringify({ nickname }),
  });
}

/** The room as everybody sees it; with the caller's token it also says which seat is theirs. */
export function getRoom(code: string, token?: string): Promise<RoomResponse> {
  return request<RoomResponse>(room(code), {}, token);
}

export function startRoom(code: string, token: string): Promise<RoomResponse> {
  return request<RoomResponse>(`${room(code)}/start`, { method: 'POST' }, token);
}

export function leaveRoom(code: string, token: string): Promise<LeaveResponse> {
  return request<LeaveResponse>(`${room(code)}/leave`, { method: 'POST' }, token);
}

// --- the game itself (docs/api/multiplayer.md, "Partita"). Everything is the caller's own: the
// seat token says who is asking, there is no player id to send.

const game = (gameId: string) => `/api/v1/mp/games/${encodeURIComponent(gameId)}`;

/** The caller's view of the game as it is right now. */
export function getGameView(gameId: string, token: string): Promise<MultiplayerViewResponse> {
  return request<MultiplayerViewResponse>(`${game(gameId)}/view`, {}, token);
}

/** What happened after revision `since`, one batch per step, each with the board right after it
 *  (so the bots can be replayed one action at a time). Never moves the game. */
export function getEvents(gameId: string, token: string, since: number): Promise<EventsResponse> {
  return request<EventsResponse>(
    `${game(gameId)}/events?since=${since}&include_view=true&include_views=true`,
    {},
    token,
  );
}

export function answerGameDecision(
  gameId: string,
  token: string,
  answer: {
    decisionId: string;
    expectedRevision: number;
    selectedOptionIds: string[];
    preparatorySelections: string[][];
  },
): Promise<AnswerResponse> {
  return request<AnswerResponse>(
    `${game(gameId)}/decisions/answer`,
    {
      method: 'POST',
      body: JSON.stringify({
        decision_id: answer.decisionId,
        expected_revision: answer.expectedRevision,
        selected_option_ids: answer.selectedOptionIds,
        preparatory_selections: answer.preparatorySelections,
      }),
    },
    token,
  );
}

export function planGameDecision(
  gameId: string,
  token: string,
  decisionId: string,
  selections: string[][],
): Promise<HumanActionPlan> {
  return request<HumanActionPlan>(
    `${game(gameId)}/decisions/plan`,
    { method: 'POST', body: JSON.stringify({ decision_id: decisionId, selections }) },
    token,
  );
}

export function leaveGame(gameId: string, token: string): Promise<LeaveResponse> {
  return request<LeaveResponse>(`${game(gameId)}/leave`, { method: 'POST' }, token);
}
