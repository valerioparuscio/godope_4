// Card follow-ups (`move_followup` decisions, backend rules/move_followups.py) and how the player
// answers them. A choice that points at something on the board — a Hood, a pawn, a Cop/Fed — is
// made by clicking it where it is lit up (designer's request, 2026-10-22: they used to be plain
// buttons); the yes/no steps with nothing to point at (aftershock, fixer, connection, backroom)
// stay buttons.

export type FollowupTargetKind = 'hood' | 'pawn' | 'officer';

export interface FollowupTarget {
  kind: FollowupTargetKind;
  id: string;
}

// The payload field that names what the player clicks, per follow-up kind. `expansion` has a pawn
// too (which one moves): BoardView asks for it first when several can.
const TARGET_FIELD = new Map<string, { kind: FollowupTargetKind; field: string }>([
  ['badge_hunt', { kind: 'hood', field: 'destination_hood_id' }],
  ['decoy', { kind: 'hood', field: 'destination_hood_id' }],
  ['follow_me', { kind: 'hood', field: 'destination_hood_id' }],
  ['cover', { kind: 'hood', field: 'destination_hood_id' }],
  ['expansion', { kind: 'hood', field: 'destination_hood_id' }],
  ['vacancy', { kind: 'pawn', field: 'pawn_id' }],
  ['escort', { kind: 'pawn', field: 'pawn_id' }],
  ['last_job', { kind: 'pawn', field: 'pawn_id' }],
  ['den_swap', { kind: 'pawn', field: 'gambler_pawn_id' }],
  ['badge_hire', { kind: 'officer', field: 'officer_id' }],
  ['full_control', { kind: 'officer', field: 'officer_id' }],
]);

/** Whether this follow-up is answered by clicking a lit-up target on the board. */
export function isBoardFollowup(followup: string): boolean {
  return TARGET_FIELD.has(followup);
}

/** What the player clicks for one option of this follow-up, or null if it has no board target. */
export function followupTarget(followup: string, payload: Record<string, unknown>): FollowupTarget | null {
  const target = TARGET_FIELD.get(followup);
  const id = target ? payload[target.field] : undefined;
  return target && typeof id === 'string' ? { kind: target.kind, id } : null;
}
