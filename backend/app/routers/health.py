"""GET /health (CLAUDE.md §6) with freshness monitoring (api-research §6.5).

Degraded when the DB is unreachable or any ingestion-written table is stale:
fixtures beyond FRESHNESS_THRESHOLD_MINUTES, standings/scorer_stats beyond 10
minutes. Tables are only checked once they have data — an empty pre-seed table
is not "stale"."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import Fixture, IngestionRun, ScorerStat, Standing
from app.schemas.responses import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()

VERSION = "1.0.0"


# GET + HEAD: uptime monitors (e.g. UptimeRobot) probe with HEAD by default;
# a GET-only route answers 405 and gets flagged "down". HEAD runs the same
# handler and returns 200 with the body stripped.
@router.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    settings = get_settings()
    stale_tables: list[str] = []
    ingestion_last_run: datetime | None = None

    try:
        now = datetime.now(UTC)
        checks = (
            ("fixtures", func.max(Fixture.last_updated_at), timedelta(minutes=settings.FRESHNESS_THRESHOLD_MINUTES)),
            ("standings", func.max(Standing.updated_at), timedelta(minutes=10)),
            ("scorer_stats", func.max(ScorerStat.updated_at), timedelta(minutes=10)),
        )
        for table_name, expression, threshold in checks:
            latest = (await session.execute(select(expression))).scalar_one_or_none()
            if latest is None:
                continue
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=UTC)
            if now - latest > threshold:
                stale_tables.append(table_name)

        ingestion_last_run = (
            await session.execute(
                select(func.max(IngestionRun.finished_at)).where(IngestionRun.status == "ok")
            )
        ).scalar_one_or_none()

        db_status = "ok"
    except Exception:
        logger.exception("health_db_check_failed")
        db_status = "error"

    degraded = db_status == "error" or bool(stale_tables)
    return HealthResponse(
        status="degraded" if degraded else "ok",
        db=db_status,
        stale_tables=stale_tables or None,
        ingestion_last_run=ingestion_last_run,
        version=VERSION,
    )
