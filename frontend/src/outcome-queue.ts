import type {
  GameViewResponse,
  LastBrawlOutcomeResponse,
  LastPokerMatchOutcomeResponse,
  LastRaidOutcomeResponse,
} from './types';

export interface PokerOutcomeItem {
  kind: 'poker';
  id: string;
  outcome: LastPokerMatchOutcomeResponse;
}

export interface RaidOutcomeItem {
  kind: 'raid';
  id: string;
  outcome: LastRaidOutcomeResponse;
}

export interface BrawlOutcomeItem {
  kind: 'brawl';
  id: string;
  outcome: LastBrawlOutcomeResponse;
}

export interface TurnStartItem {
  kind: 'turn_start';
  id: string;
  turnIndex: number;
}

export interface PokerStartItem {
  kind: 'poker_start';
  id: string;
}

export type QueuedOutcome =
  | PokerOutcomeItem
  | RaidOutcomeItem
  | BrawlOutcomeItem
  | TurnStartItem
  | PokerStartItem;

export interface OutcomeTracker {
  shownIds: Set<string>;
  // 0 (below the engine's own 1-based turn_index) so the very first view
  // of a fresh game still queues a "Turno 1" announcement — "ogni turno",
  // taken literally, includes the first one (game designer, 2026-09-26).
  lastSeenTurnIndex: number;
}

export function createOutcomeTracker(): OutcomeTracker {
  return { shownIds: new Set(), lastSeenTurnIndex: 0 };
}

// Brawl/Poker/Raid recaps only, deduped by `shownIds` — the part
// `TutorialModal` also needs (each sandbox card is its own isolated
// mini-game, never a multi-turn narrative, so a "Turno N" announcement
// firing every time a fresh card's sandbox loads at turn_index 1 would
// just be noise there — `collectFreshOutcomes` below is the real game's
// own superset, for App.tsx). Order matches the turn's own flow
// (RULES_CANONICAL.md §B: a round's own Brawl, then its Poker match,
// then — at the turn's very end — its Raid).
export function collectFreshMatchOutcomes(
  view: GameViewResponse,
  shownIds: Set<string>,
): QueuedOutcome[] {
  const fresh: QueuedOutcome[] = [];

  if (view.last_brawl_outcome) {
    const id = `brawl:${JSON.stringify(view.last_brawl_outcome)}`;
    if (!shownIds.has(id)) {
      shownIds.add(id);
      fresh.push({ kind: 'brawl', id, outcome: view.last_brawl_outcome });
    }
  }
  if (view.last_poker_outcome) {
    const id = `poker:${view.last_poker_outcome.match_id}`;
    if (!shownIds.has(id)) {
      shownIds.add(id);
      fresh.push({ kind: 'poker', id, outcome: view.last_poker_outcome });
    }
  }
  if (view.last_raid_outcome) {
    const id = `raid:${JSON.stringify(view.last_raid_outcome)}`;
    if (!shownIds.has(id)) {
      shownIds.add(id);
      fresh.push({ kind: 'raid', id, outcome: view.last_raid_outcome });
    }
  }

  return fresh;
}

// The full queue for a real game (App.tsx): every match outcome above,
// plus a "Turno N" announcement — closing out the *previous* turn before
// announcing the new one, so "Turno N+1" always appears last when both
// land in the same view update (e.g. the last round's Raid resolving in
// the same response that already reveals the next turn's own first Raid
// card). Marks each item shown on `tracker` as it's collected — a later
// call with a view that still carries the same last_X_outcome (the
// backend only clears these on the *next* occurrence, not right after)
// never re-queues it.
export function collectFreshOutcomes(
  view: GameViewResponse,
  tracker: OutcomeTracker,
): QueuedOutcome[] {
  const fresh: QueuedOutcome[] = [];

  // A Poker match about to play out — launched by *any* player, bot or
  // human — pauses the same way a Rissa/Poker/Retata recap already does,
  // rather than blurring past invisibly during bot auto-advance (game
  // designer, 2026-09-26: "un popup prima che ogni partita a poker
  // inizi, anche se non sono presente, giusto per spezzare il flusso e
  // far cliccare al giocatore umano l'avvio della partita a poker").
  // Real game only (App.tsx), not TutorialModal's own isolated cards —
  // its Poker card's whole point is already teaching the launch_poker
  // step itself, so a second, unrelated "click to start" gate right
  // after would just be redundant. Deduped by card id, like every other
  // item here: `poker_launched_card_id` stays set for the match's entire
  // bets/cards/reveal, so this only fires once per match, at the view
  // where it first appears. Checked *before* collectFreshMatchOutcomes
  // (whose own `last_poker_outcome` reflects the *result*) so a launch
  // and its own resolution landing in the very same batch — a match with
  // no human participant can run start-to-finish inside one `/advance`
  // — still queue in the right chronological order.
  if (view.poker_launched_card_id) {
    const id = `poker_start:${view.poker_launched_card_id}`;
    if (!tracker.shownIds.has(id)) {
      tracker.shownIds.add(id);
      fresh.push({ kind: 'poker_start', id });
    }
  }

  fresh.push(...collectFreshMatchOutcomes(view, tracker.shownIds));

  if (view.turn_index > tracker.lastSeenTurnIndex) {
    fresh.push({ kind: 'turn_start', id: `turn:${view.turn_index}`, turnIndex: view.turn_index });
  }
  tracker.lastSeenTurnIndex = view.turn_index;

  return fresh;
}
