import { t, tDyn } from '../i18n';
import { MultiplayerApiError } from './api';

// What the player reads when a multiplayer request is refused (codes: docs/api/multiplayer.md;
// the texts are in i18n/texts/errors.ts, `mpError.<code>`).

/** An error from a multiplayer call as a sentence for the player. */
export function multiplayerErrorMessage(error: unknown): string {
  if (error instanceof MultiplayerApiError) {
    return tDyn(`mpError.${error.code}`) ?? error.message;
  }
  return t('mpError.unreachable');
}
