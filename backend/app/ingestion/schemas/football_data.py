"""Pydantic boundary models for football-data.org v4 (api-research.md §3).

Integer scores (unlike ESPN's strings). `score.fullTime` can be null for
unplayed matches. The scorers endpoint returns `playedMatches`, mapped to the
internal `matches_played`.
"""

from pydantic import BaseModel, ConfigDict


class _Permissive(BaseModel):
    model_config = ConfigDict(extra="ignore")


class FDTeam(_Permissive):
    id: int | None = None
    name: str | None = None
    tla: str | None = None  # 3-letter code, e.g. "BRA"


class FDScorePart(_Permissive):
    home: int | None = None
    away: int | None = None


class FDScore(_Permissive):
    fullTime: FDScorePart | None = None


class FDMatch(_Permissive):
    id: int | None = None
    utcDate: str | None = None
    status: str | None = None  # SCHEDULED | TIMED | IN_PLAY | PAUSED | FINISHED
    homeTeam: FDTeam | None = None
    awayTeam: FDTeam | None = None
    score: FDScore | None = None


class FDMatchesResponse(_Permissive):
    matches: list[FDMatch] = []


class FDTableRow(_Permissive):
    team: FDTeam | None = None
    points: int | None = None
    won: int | None = None
    draw: int | None = None
    lost: int | None = None
    goalsFor: int | None = None
    goalsAgainst: int | None = None
    goalDifference: int | None = None


class FDStandingGroup(_Permissive):
    group: str | None = None  # e.g. "GROUP_A"
    table: list[FDTableRow] = []


class FDStandingsResponse(_Permissive):
    standings: list[FDStandingGroup] = []


class FDPlayer(_Permissive):
    id: int | None = None
    name: str | None = None
    position: str | None = None


class FDScorer(_Permissive):
    player: FDPlayer | None = None
    team: FDTeam | None = None
    goals: int | None = None
    assists: int | None = None
    playedMatches: int | None = None


class FDScorersResponse(_Permissive):
    scorers: list[FDScorer] = []
