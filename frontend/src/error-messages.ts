import type { DomainErrorResponse } from './types';

// Italian text for the DomainError codes a player can realistically hit
// through the real UI (races against a stale view, funds/capacity that
// changed since the last render, a Skill/limit already used this round).
// Codes that normally only fire for an unvalidated/bot client (a client
// picking outside its own offered options) are deliberately left out —
// they fall back to GENERIC_FALLBACK below instead of being enumerated
// one by one, since a real player using the offered UI should rarely if
// ever see them.
const ERROR_MESSAGE_BY_CODE: Partial<Record<string, string>> = {
  // Stale view / concurrent update races.
  revision_mismatch: 'La partita è andata avanti nel frattempo — riprova.',
  wrong_phase: 'Questa mossa non è più possibile in questa fase — riprova.',
  wrong_active_step: 'Questa mossa non è più possibile adesso — riprova.',

  // Money — insufficient_funds itself is handled specially below (it
  // interpolates error.details.required/available when present), this is
  // only the fallback text if those details are ever missing.
  insufficient_funds: 'Non hai abbastanza soldi per questa mossa.',

  // Capacity full.
  den_full: 'Il Den è pieno.',
  den_full_for_player: 'Non hai più spazio nel Den.',
  hood_capacity_exceeded: 'Il Quartiere è pieno.',
  spot_full: 'Il Punto di Vendita è pieno.',
  base_inventory_full: 'Il Covo non ha più spazio per questa Merce.',
  jail_full: 'Il Commissariato è pieno.',
  jail_confiscation_full: 'Il Commissariato non ha più spazio per la Merce confiscata.',
  base_officer_cap_reached: 'Il Covo ha già 3 Cops/Feds.',

  // No presence / no stock / blocked.
  no_presence: 'Non hai una pedina lì per farlo.',
  hood_has_no_dope: 'Non c’è più Merce in questo Quartiere.',
  spot_has_no_dope: 'Non c’è più Merce in questo Punto di Vendita.',
  no_dope_to_sell: 'Non hai questa Merce nel Covo.',
  hood_blocked_by_cop: 'Un Cop blocca questo Quartiere.',
  spot_blocked_by_fed: 'Un Fed blocca questo Punto di Vendita.',

  // Already used this round/turn.
  action_type_already_used_this_turn: 'Hai già usato questo tipo di azione in questo turno.',
  extra_action_already_used: 'Hai già usato la tua azione extra in questo turno.',
  gamble_limit_reached_this_round: 'Hai già giocato una carta Gamble in questo round.',
  poker_match_limit_reached_this_turn: 'Hai già lanciato il massimo di partite Poker in questo turno.',

  // Hand/card state changed underneath.
  card_not_in_hand: 'Questa carta non è più in mano tua — riprova.',
  card_not_eligible_for_marketing: 'Questa carta non è idonea per Marketing.',
  card_action_type_mismatch: 'Questa carta non corrisponde all’azione di questo round.',
  not_a_gamble_card: 'Questa carta non è una carta Gamble.',

  // Misc realistic cases.
  grit_value_unavailable: 'Questo valore di Grinta non è più disponibile.',
  cannot_stain_for_cash: 'Non puoi macchiare una REP per soldi adesso.',
  dope_type_not_accepted: 'Questo Punto di Vendita non accetta questo tipo di Merce.',
};

const GENERIC_FALLBACK = 'Questa mossa non è più valida — riprova.';

// `error` is either the full backend error (a DomainErrorResponse, for
// every setError call fed from a CommandResultResponse) or a raw string
// (the 2 catch-block call sites in App.tsx, a network/JS exception with
// no `code` to look up) — both render through here so the sidebar's
// single `.error` paragraph never needs its own type-narrowing logic.
export function friendlyErrorMessage(error: DomainErrorResponse | string): string {
  if (typeof error === 'string') return error;

  if (error.code === 'insufficient_funds') {
    const required = error.details?.required;
    const available = error.details?.available;
    if (typeof required === 'number' && typeof available === 'number') {
      return `Servono $${required}, ne hai $${available}.`;
    }
  }

  return ERROR_MESSAGE_BY_CODE[error.code] ?? GENERIC_FALLBACK;
}
