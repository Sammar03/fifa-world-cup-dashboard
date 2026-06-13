"""GET /standings (CLAUDE.md §6). Self-computed standings only (ADR-003),
ordered by the official FIFA 2026 tiebreaker."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.ingestion.aggregator import all_team_forms
from app.models import Standing, Team
from app.routers.common import team_ref
from app.schemas.responses import StandingOut, StandingsResponse

logger = logging.getLogger(__name__)
router = APIRouter()

GROUPS = [chr(ordinal) for ordinal in range(ord("A"), ord("L") + 1)]


@router.get("/standings", response_model=StandingsResponse)
async def standings(
    group: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> StandingsResponse:
    try:
        if group is not None:
            group = group.upper()
            if group not in GROUPS:
                raise HTTPException(status_code=422, detail="group must be A–L")

        query = select(Standing)
        if group is not None:
            query = query.where(Standing.group_label == group)
        rows = (await session.execute(query)).scalars().all()

        teams = (await session.execute(select(Team))).scalars().all()
        teams_by_id = {team.id: team for team in teams}
        forms = await all_team_forms(session)

        items: list[StandingOut] = []
        for row in rows:
            team = teams_by_id.get(row.team_id)
            if team is None:
                continue
            items.append(
                StandingOut(
                    team=team_ref(team),
                    group_label=row.group_label,
                    played=row.played,
                    won=row.won,
                    drawn=row.drawn,
                    lost=row.lost,
                    goals_for=row.goals_for,
                    goals_against=row.goals_against,
                    goal_diff=row.goal_diff,
                    points=row.points,
                    form=forms.get(row.team_id, []),
                )
            )

        # FIFA 2026 tiebreaker: points → GD → GF → name (ADR-003), per group.
        items.sort(
            key=lambda s: (
                s.group_label,
                -s.points,
                -s.goal_diff,
                -s.goals_for,
                s.team.name,
            )
        )

        updated_at = (
            (await session.execute(select(Standing.updated_at).limit(1))).scalar_one_or_none()
            or datetime.now(UTC)
        )
        return StandingsResponse(standings=items, group=group or "ALL", updated_at=updated_at)
    except HTTPException:
        raise
    except Exception:
        logger.exception("standings_failed")
        raise HTTPException(status_code=500, detail="Internal server error") from None
