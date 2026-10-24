import type { StoredSeat } from './types';

// Local storage can be missing or throw (private window, blocked site data): everything here is
// best-effort, and the lobby works without it — the player just can't resume after a reload.

const SEAT_KEY = 'dope_mp_seat_v1';
const NICKNAME_KEY = 'dope_mp_nickname_v1';

export function loadSeat(): StoredSeat | null {
  try {
    const raw = localStorage.getItem(SEAT_KEY);
    if (!raw) return null;
    const seat = JSON.parse(raw) as Partial<StoredSeat>;
    if (
      typeof seat.room_code === 'string' &&
      typeof seat.seat_token === 'string' &&
      typeof seat.seat_index === 'number' &&
      typeof seat.player_id === 'string'
    ) {
      return {
        room_code: seat.room_code,
        game_id: typeof seat.game_id === 'string' ? seat.game_id : null,
        seat_token: seat.seat_token,
        seat_index: seat.seat_index,
        player_id: seat.player_id,
        nickname: typeof seat.nickname === 'string' ? seat.nickname : '',
      };
    }
  } catch {
    // unreadable: treat as no seat
  }
  return null;
}

export function saveSeat(seat: StoredSeat): void {
  try {
    localStorage.setItem(SEAT_KEY, JSON.stringify(seat));
  } catch {
    // best-effort only
  }
}

export function clearSeat(): void {
  try {
    localStorage.removeItem(SEAT_KEY);
  } catch {
    // best-effort only
  }
}

export function loadNickname(): string {
  try {
    return localStorage.getItem(NICKNAME_KEY) ?? '';
  } catch {
    return '';
  }
}

export function saveNickname(nickname: string): void {
  try {
    localStorage.setItem(NICKNAME_KEY, nickname);
  } catch {
    // best-effort only
  }
}
