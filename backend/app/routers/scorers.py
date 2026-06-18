"""GET /scorers (CLAUDE.md §6, §4.3). Default sort: goals DESC, ties broken by
fewer matches played, then more assists."""

import logging
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Player, ScorerStat, Team
from app.schemas.responses import ScorersResponse, ScorerStatOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/scorers", response_model=ScorersResponse)
async def scorers(
    sort: Literal["goals", "assists", "clean_sheets"] = "goals",
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> ScorersResponse:
    try:
        rows = (
            await session.execute(
                select(ScorerStat, Player, Team)
                .join(Player, Player.id == ScorerStat.player_id)
                .outerjoin(Team, Team.id == Player.team_id)
            )
        ).all()

        items: list[ScorerStatOut] = []
        updated_at: datetime | None = None
        for stat, player, team in rows:
            updated_at = updated_at or stat.updated_at
            items.append(
                ScorerStatOut(
                    rank=0,  # assigned after sorting
                    player_name=player.name,
                    team_name=team.name if team else "",
                    team_code=(team.code or "") if team else "",
                    position=stat.position or "—",
                    goals=stat.goals,
                    assists=stat.assists,
                    clean_sheets=stat.clean_sheets,
                    matches_played=stat.matches_played,
                )
            )

        if sort == "goals":
            items.sort(key=lambda s: (-s.goals, s.matches_played, -s.assists, s.player_name))
        elif sort == "assists":
            items.sort(key=lambda s: (-s.assists, s.matches_played, -s.goals, s.player_name))
        else:  # clean_sheets — goalkeeper board (others have null clean_sheets and
            # never appear in the goals/assists top-N, so they need their own sort)
            items = [s for s in items if s.clean_sheets is not None]
            items.sort(key=lambda s: (-(s.clean_sheets or 0), s.matches_played, s.player_name))

        items = items[:limit]
        for index, item in enumerate(items):
            item.rank = index + 1

        return ScorersResponse(scorers=items, updated_at=updated_at or datetime.now(UTC))
    except HTTPException:
        raise
    except Exception:
        logger.exception("scorers_failed")
        raise HTTPException(status_code=500, detail="Internal server error") from None
