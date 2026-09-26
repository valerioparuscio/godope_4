import type { GameEventResponse, GameViewResponse } from './types';

// A Jail Evasion (RULES_CANONICAL.md §A1) resolves atomically on the
// backend — the moment the 4th Rat fills the last slot, the same command
// already returns every Rat to base (or, for the triggering one, evolves
// it into a Politici Link) — so there's no view anywhere in the normal
// response stream where the Jail actually sits full. The game designer
// wants exactly that moment held on screen for 2s, with all 4 pawns
// pulsing, before they animate off to their real destinations (2026-09-26:
// "quando il quarto pawn va in prigione, ci deve restare 2 secondi,
// intanto le 4 pedine iniziano a gonfiarsi e sgonfiarsi").
//
// Reconstructed here rather than asked of the backend: `priorView` (the
// state right before this command/segment) already has the *other* 3
// Rats correctly seated — arrest_pawn's own synchronous evasion means
// they were never seen anywhere else — so the only thing missing is the
// 4th (triggering) pawn's own arrest, synthesized from its matching
// `JailEscapeTriggered` event.
export function buildJailEvasionHoldView(
  events: GameEventResponse[],
  priorView: GameViewResponse,
): GameViewResponse | null {
  const triggered = events.find((e) => e.event_type === 'JailEscapeTriggered');
  if (!triggered) return null;
  const triggeringPawnId = triggered.triggering_pawn_id as string;

  const freeSlot = priorView.jail_slots.find((s) => s.rat_pawn_id === null);
  if (!freeSlot) return null; // defensive: shouldn't happen if this really is the 4th

  return {
    ...priorView,
    pawns: priorView.pawns.map((p) =>
      p.pawn_id === triggeringPawnId
        ? { ...p, role: 'rat', hood_id: null, contact_id: null, link_level: null }
        : p,
    ),
    jail_slots: priorView.jail_slots.map((s) =>
      s.index === freeSlot.index ? { ...s, rat_pawn_id: triggeringPawnId } : s,
    ),
    hoods: priorView.hoods.map((h) => ({
      ...h,
      criminal_pawn_ids: h.criminal_pawn_ids.filter((id) => id !== triggeringPawnId),
    })),
  };
}

export const JAIL_EVASION_HOLD_MS = 2000;

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
