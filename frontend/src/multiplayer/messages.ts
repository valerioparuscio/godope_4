import { MultiplayerApiError } from './api';

// What the player reads when a multiplayer request is refused (codes: docs/api/multiplayer.md).
const MESSAGE_BY_CODE: Record<string, string> = {
  invalid_request: 'I dati inseriti non sono validi.',
  room_not_found: 'Non esiste una stanza con questo codice.',
  room_full: 'La stanza è piena.',
  room_already_started: 'La partita in questa stanza è già iniziata.',
  room_closed: "L'host ha chiuso la stanza.",
  room_not_ready: 'Non tutti i posti sono ancora occupati.',
  nickname_taken: "In questa stanza c'è già qualcuno con questo nickname.",
  forbidden: "Solo l'host può avviare la partita.",
  invalid_token: 'La tua sessione in questa stanza non è più valida.',
};

/** An error from a multiplayer call as a sentence for the player. */
export function multiplayerErrorMessage(error: unknown): string {
  if (error instanceof MultiplayerApiError) {
    return MESSAGE_BY_CODE[error.code] ?? error.message;
  }
  return 'Impossibile raggiungere il server. Controlla la connessione e riprova.';
}
