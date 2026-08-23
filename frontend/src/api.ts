import type { CommandResultResponse, CreateGameResponse, GameViewResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export function createGame(
  seed: number,
  humanSeat: number,
  nickname: string,
): Promise<CreateGameResponse> {
  return request<CreateGameResponse>('/api/v1/games', {
    method: 'POST',
    body: JSON.stringify({ seed, human_seat: humanSeat, nickname }),
  });
}

export function getView(gameId: string, playerId: string): Promise<GameViewResponse> {
  return request<GameViewResponse>(
    `/api/v1/games/${gameId}/view?player_id=${encodeURIComponent(playerId)}`,
  );
}

export function answerDecision(
  gameId: string,
  playerId: string,
  decisionId: string,
  selectedOptionIds: string[],
): Promise<CommandResultResponse> {
  return request<CommandResultResponse>(`/api/v1/games/${gameId}/decisions/answer`, {
    method: 'POST',
    body: JSON.stringify({
      player_id: playerId,
      decision_id: decisionId,
      selected_option_ids: selectedOptionIds,
    }),
  });
}

// Dispatch-only (backend/.../decisions/answer no longer auto-advances,
// 2026-08-16): the caller applies the view from answerDecision itself
// first — so the human's own move shows immediately — then calls this
// separately (repeatedly, with singlePlayerSegment, when narrating bot
// turns one at a time) to progress bots, narrating whatever events come
// back before applying *this* view. singlePlayerSegment=true stops as
// soon as one bot's own turn-segment finishes (not the whole cascade),
// so the caller can render/narrate each bot before asking for the next
// one instead of the board jumping straight to the final state.
export function advanceGame(
  gameId: string,
  playerId: string,
  singlePlayerSegment = false,
): Promise<CommandResultResponse> {
  const params = new URLSearchParams({ player_id: playerId });
  if (singlePlayerSegment) params.set('single_player_segment', 'true');
  return request<CommandResultResponse>(`/api/v1/games/${gameId}/advance?${params}`, {
    method: 'POST',
  });
}

// Reverts the single most recent move (designer's request, 2026-08-22:
// "vorrei introdurre la possibilità di annullare scelte, ad esempio la
// scelta dell'azione, se selezionata per sbaglio") — only ever available
// while `view.undo_available` is true, which the backend already scopes
// to "nothing else, bots included, has happened since".
export function undoLastCommand(gameId: string, playerId: string): Promise<CommandResultResponse> {
  const params = new URLSearchParams({ player_id: playerId });
  return request<CommandResultResponse>(`/api/v1/games/${gameId}/undo?${params}`, {
    method: 'POST',
  });
}
