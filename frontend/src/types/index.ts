// Shared domain types. These mirror the FastAPI response contracts in
// CLAUDE.md §6 and the schema in §5.2. The frontend reads these shapes from the
// backend only (never from a third-party API directly).

export type FixtureStatus = "scheduled" | "live" | "finished";

export type GoalType = "regular" | "own_goal" | "penalty";

export type FormResult = "W" | "D" | "L";

/** A team as referenced inside fixtures, standings, and detail responses. */
export interface TeamRef {
  id: number;
  name: string;
  code: string; // 3-letter, e.g. "BRA"
  group_label: string;
  flag_url: string | null;
}

export interface Fixture {
  id: number;
  home_team: TeamRef;
  away_team: TeamRef;
  kickoff_at: string; // ISO8601 (UTC)
  venue: string | null;
  status: FixtureStatus;
  home_score: number | null;
  away_score: number | null;
  group_label: string | null;
  round: string | null;
  /** Live display clock in minutes (live only); null otherwise. */
  minute: number | null;
  /** Two-source reconciliation result (api-research §6.2). */
  verified: boolean;
}

export interface MatchStats {
  team_id: number;
  possession: number | null; // percentage
  shots: number | null;
  shots_on_target: number | null;
  corners: number | null;
  fouls: number | null;
  yellow_cards: number | null;
  red_cards: number | null;
}

export interface Goal {
  id: number;
  fixture_id: number;
  team_id: number;
  player_name: string;
  minute: number;
  type: GoalType;
}

export interface LineupPlayer {
  player_name: string;
  number: number | null;
  position: string | null;
  is_starter: boolean;
}

export interface Lineup {
  team_id: number;
  formation: string | null;
  players: LineupPlayer[];
}

export interface AIInsight {
  content: string;
  state: "scheduled" | "finished";
  model: string;
  prompt_version: string;
}

export interface Standing {
  team: TeamRef;
  group_label: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
  /** Last up-to-5 results, oldest → newest. */
  form: FormResult[];
}

export interface ScorerStat {
  rank: number;
  player_name: string;
  team_name: string;
  team_code: string;
  /** Playing position, e.g. "GK", "DF", "MF", "FW". */
  position: string;
  goals: number;
  assists: number;
  /** Clean sheets — counted for goalkeepers only; null for outfield players. */
  clean_sheets: number | null;
  matches_played: number;
}

export interface TeamAggregate {
  matches_played: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  clean_sheets: number;
  possession_avg: number | null;
  shots: number | null;
  shots_on_target: number | null;
  corners: number | null;
  yellow_cards: number | null;
  red_cards: number | null;
}

export interface QueryEvidence {
  metric: string;
  value: number | string;
  team?: string;
  player?: string;
}

// --- API response envelopes (CLAUDE.md §6) ----------------------------------

export interface FixturesResponse {
  fixtures: Fixture[];
  generated_at: string;
}

export interface FixtureDetailResponse {
  fixture: Fixture;
  stats: MatchStats[];
  goals: Goal[];
  lineups?: Lineup[] | null;
  insight?: AIInsight | null;
}

export interface StandingsResponse {
  standings: Standing[];
  group: string;
  updated_at: string;
}

export interface ScorersResponse {
  scorers: ScorerStat[];
  updated_at: string;
}

export interface TeamResponse {
  team: TeamRef;
  stats: TeamAggregate;
  form: FormResult[];
}

export interface QueryResponse {
  answer: string;
  evidence: QueryEvidence | null;
  supported: boolean;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  db: "ok" | "error";
  stale_tables?: string[];
  ingestion_last_run?: string;
  version?: string;
}
