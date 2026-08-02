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

export function createGame(seed: number, humanSeat: number): Promise<CreateGameResponse> {
  return request<CreateGameResponse>('/api/v1/games', {
    method: 'POST',
    body: JSON.stringify({ seed, human_seat: humanSeat }),
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
