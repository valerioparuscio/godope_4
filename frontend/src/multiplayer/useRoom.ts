import { useEffect, useState } from 'react';
import { MultiplayerApiError, getRoom } from './api';
import type { RoomResponse, StoredSeat } from './types';

/** How often a waiting player asks the server about the room (docs/architecture/GPT_MULTIPLAYER.md
 *  §18: polling first). */
export const ROOM_POLL_INTERVAL_MS = 1500;

export interface RoomWatch {
  room: RoomResponse | null;
  /** The server can't be reached right now (the last known room stays on screen). */
  connectionLost: boolean;
  /** The seat is gone for good: the room no longer exists or this token isn't in it any more. */
  seatLost: boolean;
  /** Replaces what is shown with a fresher room (e.g. the answer to "start"). */
  setRoom: (room: RoomResponse) => void;
}

/** Follows the room `seat` sits in: asks about it every `ROOM_POLL_INTERVAL_MS` until the game
 *  has started (from there on the game screen takes over) or the seat is lost. */
export function useRoom(seat: StoredSeat | null): RoomWatch {
  const [room, setRoomState] = useState<RoomResponse | null>(null);
  const [connectionLost, setConnectionLost] = useState(false);
  const [seatLost, setSeatLost] = useState(false);

  const code = seat?.room_code ?? null;
  const token = seat?.seat_token ?? null;

  useEffect(() => {
    setRoomState(null);
    setConnectionLost(false);
    setSeatLost(false);
    if (!code || !token) return () => undefined;

    let timer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    async function poll(): Promise<void> {
      if (stopped || !code || !token) return;
      let keepPolling = true;
      try {
        const latest = await getRoom(code, token);
        if (stopped) return;
        setConnectionLost(false);
        if (latest.me === null) {
          setSeatLost(true);
          keepPolling = false;
        } else {
          setRoomState(latest);
          keepPolling = latest.status === 'lobby';
        }
      } catch (error) {
        if (stopped) return;
        if (error instanceof MultiplayerApiError && error.status === 404) {
          setSeatLost(true); // the room is gone (e.g. the server restarted)
          keepPolling = false;
        } else {
          setConnectionLost(true);
        }
      }
      if (keepPolling && !stopped) timer = setTimeout(poll, ROOM_POLL_INTERVAL_MS);
    }

    void poll();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [code, token]);

  return {
    room,
    connectionLost,
    seatLost,
    setRoom: (fresh) => setRoomState(fresh),
  };
}
