"""POST /ingest — internal trigger, INGEST_SECRET header required (CLAUDE.md §6,
§11). 401 on absent or wrong secret. The secret is never logged."""

import logging
import secrets

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.ingestion.scheduler import run_ingestion
from app.schemas.responses import IngestResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(
    x_ingest_secret: str | None = Header(default=None),
) -> IngestResponse:
    expected = get_settings().INGEST_SECRET
    if x_ingest_secret is None or not secrets.compare_digest(x_ingest_secret, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        run = await run_ingestion()
    except Exception:
        logger.exception("manual_ingest_failed")
        raise HTTPException(status_code=500, detail="Ingestion failed") from None
    return IngestResponse(
        status="ok",
        fixtures_updated=run.fixtures_updated,
        insights_generated=run.insights_generated,
        reconciliation_flags=run.reconciliation_flags,
    )
