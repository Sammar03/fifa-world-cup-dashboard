"""GET /teams/{id} (CLAUDE.md §6, §4.4). Aggregates are served from data the
ingestion pipeline wrote — missing stat fields degrade to null, never crash."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.ingestion.aggregator import team_form
from app.models import Fixture, MatchStat, Standing, Team
from app.routers.common import team_ref
from app.schemas.responses import TeamAggregateOut, TeamResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def team_detail(
    team_id: int, session: AsyncSession = Depends(get_session)
) -> TeamResponse:
    try:
        team = await session.get(Team, team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found")

        standing = (
            await session.execute(select(Standing).where(Standing.team_id == team.id))
        ).scalar_one_or_none()

        finished = (
            (
                await session.execute(
                    select(Fixture).where(
                        Fixture.status == "finished",
                        Fixture.home_score.is_not(None),
                        Fixture.away_score.is_not(None),
                        (Fixture.home_team_id == team.id) | (Fixture.away_team_id == team.id),
                    )
                )
            )
            .scalars()
            .all()
        )
        clean_sheets = sum(
            1
            for fixture in finished
            if (fixture.away_score if fixture.home_team_id == team.id else fixture.home_score) == 0
        )

        stats_rows = (
            (await session.execute(select(MatchStat).where(MatchStat.team_id == team.id)))
            .scalars()
            .all()
        )

        def _sum(attribute: str) -> int | None:
            values = [getattr(row, attribute) for row in stats_rows if getattr(row, attribute) is not None]
            return sum(values) if values else None

        possession_values = [float(row.possession) for row in stats_rows if row.possession is not None]
        possession_avg = (
            round(sum(possession_values) / len(possession_values), 1) if possession_values else None
        )

        aggregate = TeamAggregateOut(
            matches_played=standing.played if standing else len(finished),
            goals_for=standing.goals_for if standing else 0,
            goals_against=standing.goals_against if standing else 0,
            goal_diff=standing.goal_diff if standing else 0,
            clean_sheets=clean_sheets,
            possession_avg=possession_avg,
            shots=_sum("shots"),
            shots_on_target=_sum("shots_on_target"),
            corners=_sum("corners"),
            yellow_cards=_sum("yellow_cards"),
            red_cards=_sum("red_cards"),
        )

        return TeamResponse(
            team=team_ref(team),
            stats=aggregate,
            form=await team_form(session, team.id),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("team_detail_failed team=%s", team_id)
        raise HTTPException(status_code=500, detail="Internal server error") from None
