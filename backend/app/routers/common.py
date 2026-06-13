"""Shared response builders used by multiple routers. No business logic in
the frontend (CLAUDE.md §7.2) — and none duplicated across route files either."""

from app.models import Fixture, Team
from app.schemas.responses import FixtureOut, TeamRef


def team_ref(team: Team) -> TeamRef:
    return TeamRef(
        id=team.id,
        name=team.name,
        code=team.code or "",
        group_label=team.group_label or "",
        flag_url=team.flag_url,
    )


def fixture_out(fixture: Fixture, teams_by_id: dict[int, Team]) -> FixtureOut | None:
    """None when the fixture cannot be represented (missing team or kickoff) —
    callers skip it rather than erroring the whole list."""
    home = teams_by_id.get(fixture.home_team_id) if fixture.home_team_id else None
    away = teams_by_id.get(fixture.away_team_id) if fixture.away_team_id else None
    if home is None or away is None or fixture.kickoff_at is None:
        return None
    return FixtureOut(
        id=fixture.id,
        home_team=team_ref(home),
        away_team=team_ref(away),
        kickoff_at=fixture.kickoff_at,
        venue=fixture.venue,
        status=fixture.status,
        home_score=fixture.home_score,
        away_score=fixture.away_score,
        group_label=fixture.group_label,
        round=fixture.round,
        minute=fixture.minute if fixture.status == "live" else None,
        verified=fixture.verified,
    )
