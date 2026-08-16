// Mirrors backend/src/dope_engine/adapters/http/schemas.py 1:1. Hand-written
// (no codegen) — the schema is small and stable; keep this in sync by hand
// whenever schemas.py changes.

export interface CreateGameResponse {
  game_id: string;
  revision: number;
  status: string;
}

export interface DomainErrorResponse {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface DecisionOptionResponse {
  option_id: string;
  label_key: string;
  payload: Record<string, unknown>;
}

export interface PendingDecisionResponse {
  decision_id: string;
  player_id: string;
  decision_type: string;
  prompt_key: string;
  options: DecisionOptionResponse[];
  min_selections: number;
  max_selections: number;
  can_pass: boolean;
}

export interface PublicPlayerResponse {
  player_id: string;
  seat_index: number;
  controller_type: string;
  display_name: string;
  money: number;
  hand_card_count: number;
  dope_counts: Record<string, number>;
  poker_chip_count: number;
  pawn_ids: string[];
  skill_ids: string[];
  available_grit_values: number[];
}

export interface PublicHoodResponse {
  hood_id: string;
  contact_id: string;
  adjacent_hood_ids: string[];
  revealed: boolean;
  criminal_pawn_ids: string[];
  dope_stack: string[];
  cop_ids: string[];
  capacity: number;
}

export interface PublicSpotResponse {
  spot_id: string;
  contact_id: string;
  accepted_dope_type: string;
  adjacent_spot_ids: string[];
  sold_dope_tokens: string[];
  fed_ids: string[];
  capacity: number;
}

export interface PublicPawnResponse {
  pawn_id: string;
  owner_player_id: string;
  role: string;
  hood_id: string | null;
  contact_id: string | null;
  link_level: number | null;
}

export interface PublicOfficerResponse {
  officer_id: string;
  officer_type: string;
  location_type: string;
  hood_id: string | null;
  spot_id: string | null;
  owner_player_id: string | null;
}

export interface PublicJailSlotResponse {
  index: number;
  rat_pawn_id: string | null;
  confiscated_dope_type: string | null;
}

export interface PublicJobBoardCellResponse {
  job_id: string;
  column_index: number;
  player_id: string | null;
  stained: boolean;
}

export interface PublicJobProgressResponse {
  tier_piles: Record<number, string[]>;
  revealed_job_id_by_tier: Record<number, string | null>;
}

export interface FinalScoreBreakdownResponse {
  money_track_position_points: number;
  clean_reputation_points: number;
  stained_reputation_points: number;
  contact_majority_points: number;
  base_chip_points: number;
  skill_points: number;
  total_points: number;
  tie_break_clean_reputation: number;
}

export interface FinalScoreResponse {
  breakdown_by_player: Record<string, FinalScoreBreakdownResponse>;
  winner_ids: string[];
}

export interface LastRaidOutcomeResponse {
  raid_card_id: string;
  escaping_team: string[];
  caught_team: string[];
}

export interface LastBrawlOutcomeResponse {
  hood_id: string;
  winner_id: string | null;
  loser_ids: string[];
  force_by_player_id: Record<string, number>;
}

export interface LastPokerMatchOutcomeResponse {
  match_id: string;
  winner_id: string | null;
  tied_ids: string[];
  loser_ids: string[];
  cash_won: number;
  jackpot_carried: number;
}

export interface GameViewResponse {
  game_id: string;
  revision: number;
  rules_version: string;
  status: string;
  phase: string;
  active_step: string;
  turn_index: number;
  action_round_index: number;
  current_player_id: string;
  first_player_id: string;
  viewing_player_id: string;
  players: PublicPlayerResponse[];
  own_hand_card_ids: string[];
  pending_decision: PendingDecisionResponse | null;
  hoods: PublicHoodResponse[];
  spots: PublicSpotResponse[];
  pawns: PublicPawnResponse[];
  den_gambler_pawn_ids: string[];
  current_price_by_dope_type: Record<string, number>;
  officers: PublicOfficerResponse[];
  jail_slots: PublicJailSlotResponse[];
  job_board: PublicJobBoardCellResponse[];
  job_progress_by_player: Record<string, PublicJobProgressResponse>;
  remaining_skill_count_by_contact: Record<string, number>;
  raid_card_id: string | null;
  raid_lost_occurrences_count: number;
  last_raid_outcome: LastRaidOutcomeResponse | null;
  last_brawl_outcome: LastBrawlOutcomeResponse | null;
  last_poker_outcomes: LastPokerMatchOutcomeResponse[];
  final_score: FinalScoreResponse | null;
  poker_launched_card_ids: string[];
}

// A generic {event_type, ...fields} dict, one per domain event — the
// backend serializes every DomainEvent dataclass field verbatim (see
// app.py's _serialize_event), so this only types the shared envelope;
// event-specific fields are read via payload[key] where needed.
export interface GameEventResponse {
  event_type: string;
  event_id: string;
  game_id: string;
  revision: number;
  [key: string]: unknown;
}

export interface CommandResultResponse {
  ok: boolean;
  view: GameViewResponse | null;
  error: DomainErrorResponse | null;
  events: GameEventResponse[];
}
