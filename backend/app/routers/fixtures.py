"""GET /fixtures and GET /fixtures/{id} (CLAUDE.md §6). Reads Postgres only."""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import AIInsight, Fixture, Goal, LineupEntry, MatchStat, Team
from app.routers.common import fixture_out
from app.schemas.responses import (
    AIInsightOut,
    FixtureDetailResponse,
    FixturesResponse,
    GoalOut,
    LineupOut,
    LineupPlayerOut,
    MatchStatsOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fixtures", response_model=FixturesResponse)
async def list_fixtures(
    date_param: str | None = Query(default=None, alias="date"),
    status: Literal["scheduled", "live", "finished"] | None = None,
    session: AsyncSession = Depends(get_session),
) -> FixturesResponse:
    try:
        query = select(Fixture).order_by(Fixture.kickoff_at.asc())
        if date_param is not None:
            try:
                day = date.fromisoformat(date_param)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD") from exc
            start = datetime(day.year, day.month, day.day, tzinfo=UTC)
            query = query.where(
                Fixture.kickoff_at >= start, Fixture.kickoff_at < start + timedelta(days=1)
            )
        if status is not None:
            query = query.where(Fixture.status == status)

        fixtures = (await session.execute(query)).scalars().all()
        teams = (await session.execute(select(Team))).scalars().all()
        teams_by_id = {team.id: team for team in teams}

        items = [fixture_out(fixture, teams_by_id) for fixture in fixtures]
        return FixturesResponse(
            fixtures=[item for item in items if item is not None],
            generated_at=datetime.now(UTC),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("fixtures_list_failed")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get("/fixtures/{fixture_id}", response_model=FixtureDetailResponse)
async def fixture_detail(
    fixture_id: int, session: AsyncSession = Depends(get_session)
) -> FixtureDetailResponse:
    try:
        fixture = await session.get(Fixture, fixture_id)
        if fixture is None:
            raise HTTPException(status_code=404, detail="Fixture not found")

        teams = (await session.execute(select(Team))).scalars().all()
        teams_by_id = {team.id: team for team in teams}
        out = fixture_out(fixture, teams_by_id)
        if out is None:
            raise HTTPException(status_code=404, detail="Fixture not found")

        stats_rows = (
            (await session.execute(select(MatchStat).where(MatchStat.fixture_id == fixture.id)))
            .scalars()
            .all()
        )
        stats = [
            MatchStatsOut(
                team_id=row.team_id,
                possession=float(row.possession) if row.possession is not None else None,
                shots=row.shots,
                shots_on_target=row.shots_on_target,
                corners=row.corners,
                fouls=row.fouls,
                yellow_cards=row.yellow_cards,
                red_cards=row.red_cards,
            )
            for row in stats_rows
            if row.team_id is not None
        ]

        goal_rows = (
            (
                await session.execute(
                    select(Goal).where(Goal.fixture_id == fixture.id).order_by(Goal.minute.asc())
                )
            )
            .scalars()
            .all()
        )
        goals = [
            GoalOut(
                id=row.id,
                fixture_id=fixture.id,
                team_id=row.team_id,
                player_name=row.player_name or "Unknown",
                minute=row.minute if row.minute is not None else 0,
                type=row.type if row.type in ("regular", "own_goal", "penalty") else "regular",
            )
            for row in goal_rows
            if row.team_id is not None
        ]

        lineup_rows = (
            (await session.execute(select(LineupEntry).where(LineupEntry.fixture_id == fixture.id)))
            .scalars()
            .all()
        )
        lineups: list[LineupOut] | None = None
        if lineup_rows:
            by_team: dict[int, list[LineupEntry]] = {}
            for entry in lineup_rows:
                by_team.setdefault(entry.team_id, []).append(entry)
            lineups = [
                LineupOut(
                    team_id=team_id,
                    formation=entries[0].formation,
                    players=[
                        LineupPlayerOut(
                            player_name=entry.player_name,
                            number=entry.number,
                            position=entry.position,
                            is_starter=entry.is_starter,
                        )
                        for entry in sorted(entries, key=lambda e: (not e.is_starter, e.number or 99))
                    ],
                )
                for team_id, entries in by_team.items()
            ]

        # Cached insight for the fixture's effective state; a live match shows
        # its pre-match preview. Served from the DB cache at 0 ms (CLAUDE.md §4.6).
        insight_state = "finished" if fixture.status == "finished" else "scheduled"
        insight_row = (
            await session.execute(
                select(AIInsight).where(
                    AIInsight.fixture_id == fixture.id, AIInsight.state == insight_state
                )
            )
        ).scalar_one_or_none()
        insight = None
        if insight_row is not None:
            insight = AIInsightOut(
                content=insight_row.content,
                state=insight_row.state,
                model=insight_row.model,
                prompt_version=insight_row.prompt_version,
            )
            logger.debug("ai_insight_served fixture=%s state=%s cache=hit", fixture.id, insight_state)

        return FixtureDetailResponse(
            fixture=out, stats=stats, goals=goals, lineups=lineups, insight=insight
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("fixture_detail_failed fixture=%s", fixture_id)
        raise HTTPException(status_code=500, detail="Internal server error") from None
