"""Pydantic boundary models for ESPN responses (api-research.md §2, §6.4).

Shapes verified against the live API on 2026-06-12. ESPN is unofficial and
undocumented: everything that is not strictly required is Optional, and every
consumer must tolerate missing fields. Live verification found one deviation
from docs/api-research.md: finished matches report status.type.id "28" /
STATUS_FULL_TIME (not "3" / STATUS_FINAL). The normalizer therefore maps on
status.type.state ("pre"|"in"|"post") first and falls back to the documented ids.
"""

from pydantic import BaseModel, ConfigDict


class _Permissive(BaseModel):
    model_config = ConfigDict(extra="ignore")


# --- Scoreboard ---------------------------------------------------------------


class EspnStatusType(_Permissive):
    id: str | None = None
    name: str | None = None
    state: str | None = None  # pre | in | post
    completed: bool | None = None


class EspnStatus(_Permissive):
    type: EspnStatusType | None = None
    displayClock: str | None = None  # e.g. "45'", "90'+8'"
    period: int | None = None


class EspnTeam(_Permissive):
    displayName: str | None = None
    abbreviation: str | None = None
    logo: str | None = None


class EspnCompetitor(_Permissive):
    id: str | None = None  # ESPN team id
    team: EspnTeam | None = None
    score: str | None = None  # STRING — parse with int(score) if score else None
    homeAway: str | None = None  # "home" | "away"


class EspnVenueAddress(_Permissive):
    city: str | None = None


class EspnVenue(_Permissive):
    fullName: str | None = None
    address: EspnVenueAddress | None = None


class EspnAthlete(_Permissive):
    id: str | None = None
    displayName: str | None = None
    jersey: str | None = None
    position: str | None = None  # raw ESPN abbreviation, e.g. "CM-R"


class EspnDetailClock(_Permissive):
    displayValue: str | None = None  # "9'"


class EspnDetailTeam(_Permissive):
    id: str | None = None


class EspnDetail(_Permissive):
    """A timeline event: goal, card, substitution…"""

    clock: EspnDetailClock | None = None
    team: EspnDetailTeam | None = None
    scoringPlay: bool | None = None
    penaltyKick: bool | None = None
    ownGoal: bool | None = None
    shootout: bool | None = None
    redCard: bool | None = None
    yellowCard: bool | None = None
    athletesInvolved: list[EspnAthlete] = []


class EspnCompetition(_Permissive):
    venue: EspnVenue | None = None
    competitors: list[EspnCompetitor] = []
    details: list[EspnDetail] = []


class EspnEvent(_Permissive):
    id: str  # required — without it we cannot key the fixture
    date: str | None = None  # ISO8601, e.g. "2026-06-11T19:00Z"
    name: str | None = None
    status: EspnStatus | None = None
    competitions: list[EspnCompetition] = []


class EspnScoreboard(_Permissive):
    events: list[EspnEvent] = []


# --- Match summary (stats + lineups) -------------------------------------------


class EspnStatistic(_Permissive):
    name: str | None = None
    displayValue: str | None = None


class EspnBoxscoreTeamInfo(_Permissive):
    id: str | None = None


class EspnBoxscoreTeam(_Permissive):
    team: EspnBoxscoreTeamInfo | None = None
    statistics: list[EspnStatistic] = []


class EspnBoxscore(_Permissive):
    teams: list[EspnBoxscoreTeam] = []


class EspnRosterPosition(_Permissive):
    abbreviation: str | None = None


class EspnRosterEntry(_Permissive):
    starter: bool | None = None
    jersey: str | None = None
    position: EspnRosterPosition | None = None
    athlete: EspnAthlete | None = None


class EspnRosterTeam(_Permissive):
    id: str | None = None


class EspnRoster(_Permissive):
    team: EspnRosterTeam | None = None
    formation: str | None = None
    roster: list[EspnRosterEntry] = []


class EspnKeyEvent(_Permissive):
    """A play-by-play event. For scoring plays, `text` carries the full prose —
    including the assist provider, e.g. "Goal! … Assisted by Lee Kang-In." —
    which is the only place ESPN exposes assists (structured fields omit them;
    verified live 2026-06-13)."""

    scoringPlay: bool | None = None
    clock: EspnDetailClock | None = None
    text: str | None = None


class EspnSummary(_Permissive):
    boxscore: EspnBoxscore | None = None
    rosters: list[EspnRoster] = []
    keyEvents: list[EspnKeyEvent] = []
