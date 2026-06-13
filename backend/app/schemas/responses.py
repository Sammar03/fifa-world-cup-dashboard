"""API response schemas (CLAUDE.md §6).

These mirror frontend/src/types/index.ts FIELD FOR FIELD — that file is the
realized contract the UI was built against. Fully typed: no dict, no Any.
Datetimes serialize as ISO8601 with UTC offset, which the frontend's
`new Date(...)` parses directly.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

FixtureStatus = Literal["scheduled", "live", "finished"]


class TeamRef(BaseModel):
    id: int
    name: str
    code: str  # "" when unknown (bracket placeholders keep ESPN slot codes)
    group_label: str  # "" for knockout placeholder teams
    flag_url: str | None


class FixtureOut(BaseModel):
    id: int
    home_team: TeamRef
    away_team: TeamRef
    kickoff_at: datetime
    venue: str | None
    status: FixtureStatus
    home_score: int | None
    away_score: int | None
    group_label: str | None
    round: str | None
    minute: int | None
    verified: bool


class MatchStatsOut(BaseModel):
    team_id: int
    possession: float | None
    shots: int | None
    shots_on_target: int | None
    corners: int | None
    fouls: int | None
    yellow_cards: int | None
    red_cards: int | None


class GoalOut(BaseModel):
    id: int
    fixture_id: int
    team_id: int
    player_name: str
    minute: int
    type: Literal["regular", "own_goal", "penalty"]


class LineupPlayerOut(BaseModel):
    player_name: str
    number: int | None
    position: str | None
    is_starter: bool


class LineupOut(BaseModel):
    team_id: int
    formation: str | None
    players: list[LineupPlayerOut]


class AIInsightOut(BaseModel):
    content: str
    state: Literal["scheduled", "finished"]
    model: str
    prompt_version: str


class StandingOut(BaseModel):
    team: TeamRef
    group_label: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    form: list[Literal["W", "D", "L"]]


class ScorerStatOut(BaseModel):
    rank: int
    player_name: str
    team_name: str
    team_code: str
    position: str  # "—" when not derivable (no lineup data yet)
    goals: int
    assists: int
    clean_sheets: int | None
    matches_played: int


class TeamAggregateOut(BaseModel):
    matches_played: int
    goals_for: int
    goals_against: int
    goal_diff: int
    clean_sheets: int
    possession_avg: float | None
    shots: int | None
    shots_on_target: int | None
    corners: int | None
    yellow_cards: int | None
    red_cards: int | None


class QueryEvidence(BaseModel):
    metric: str
    value: float | int | str
    team: str | None = None
    player: str | None = None


# --- Envelopes -------------------------------------------------------------------


class FixturesResponse(BaseModel):
    fixtures: list[FixtureOut]
    generated_at: datetime


class FixtureDetailResponse(BaseModel):
    fixture: FixtureOut
    stats: list[MatchStatsOut]
    goals: list[GoalOut]
    lineups: list[LineupOut] | None = None
    insight: AIInsightOut | None = None


class StandingsResponse(BaseModel):
    standings: list[StandingOut]
    group: str
    updated_at: datetime


class ScorersResponse(BaseModel):
    scorers: list[ScorerStatOut]
    updated_at: datetime


class TeamResponse(BaseModel):
    team: TeamRef
    stats: TeamAggregateOut
    form: list[Literal["W", "D", "L"]]


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    evidence: QueryEvidence | None
    supported: bool


class IngestResponse(BaseModel):
    status: str
    fixtures_updated: int
    insights_generated: int
    reconciliation_flags: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: Literal["ok", "error"]
    stale_tables: list[str] | None = None
    ingestion_last_run: datetime | None = None
    version: str | None = None
