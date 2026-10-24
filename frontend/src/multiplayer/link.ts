// The shareable room link: the game's own address plus `?stanza=<code>`. It carries the room code
// only — never a seat token (a code lets someone ask to join, it doesn't give them anyone's seat).

export const ROOM_PARAM = 'stanza';
export const ROOM_CODE_LENGTH = 4;

/** Upper-cases a typed code and drops anything that can't be in one. */
export function cleanRoomCode(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, ROOM_CODE_LENGTH);
}

/** The room code in the address bar (`?stanza=F7KQ`), if there is a well-formed one. */
export function roomCodeFromUrl(): string | null {
  try {
    const raw = new URL(window.location.href).searchParams.get(ROOM_PARAM);
    const code = raw ? cleanRoomCode(raw) : '';
    return code.length === ROOM_CODE_LENGTH ? code : null;
  } catch {
    return null;
  }
}

export function shareLink(roomCode: string): string {
  return `${window.location.origin}${window.location.pathname}?${ROOM_PARAM}=${roomCode}`;
}

/** Takes `?stanza=` out of the address bar once it has been used. */
export function dropRoomParamFromUrl(): void {
  try {
    const url = new URL(window.location.href);
    if (url.searchParams.has(ROOM_PARAM)) {
      url.searchParams.delete(ROOM_PARAM);
      window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
  } catch {
    // cosmetic only
  }
}
