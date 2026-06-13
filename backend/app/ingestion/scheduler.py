"""Ingestion orchestration + APScheduler setup (CLAUDE.md §5.3, §12).

run_ingestion() executes the seven steps IN ORDER:
  1 fetch → 2 validate (Pydantic in fetcher) → 3 normalize → 4 upsert
  → 5 aggregate → 6 reconcile → 7 enrich (AI)

Failures degrade, never crash: a source returning None skips its step; the
scheduler wrapper catches everything, counts consecutive failures, and emits a
CRITICAL log at 5 (CLAUDE.md §12). Scheduling is a self-chaining one-shot job:
after each run the next one is queued at LIVE_POLL_INTERVAL_SECONDS if any
fixture is live, else INGEST_INTERVAL_SECONDS (api-research §2).
"""

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.insights import enrich
from app.config import get_settings
from app.database import SessionLocal
from app.ingestion import fetcher
from app.ingestion.aggregator import aggregate
from app.ingestion.normalizer import normalize_event, normalize_summary
from app.ingestion.upsert import (
    apply_assists,
    load_team_cache,
    replace_goals,
    replace_lineups,
    upsert_fixture,
    upsert_match_stats,
)
from app.models import Fixture, IngestionRun
from app.reconciliation.checker import reconcile

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_consecutive_failures = 0

# ESPN /summary calls per run, hard cap (api-research §8 call budget: 0–5).
SUMMARY_CALL_CAP = 5


async def _scoreboard_window(session: AsyncSession) -> str:
    """YYYYMMDD-YYYYMMDD spanning all seeded fixtures (one ESPN call covers
    the whole tournament — verified live 2026-06-12)."""
    low, high = (
        await session.execute(select(func.min(Fixture.kickoff_at), func.max(Fixture.kickoff_at)))
    ).one()
    if low is None or high is None:
        today = datetime.now(UTC)
        low, high = today - timedelta(days=1), today + timedelta(days=1)
    return f"{low:%Y%m%d}-{high:%Y%m%d}"


async def _summary_targets(session: AsyncSession) -> list[Fixture]:
    """Live fixtures (every run) first, then finished fixtures not yet summary-
    synced (stats + lineups + assists), most recent first. summary_synced_at is
    reset to NULL on a status change, so each finished match gets exactly one
    final summary pass and is then skipped — keeping the run within the 5-call
    summary budget (api-research §8)."""
    live = (
        (await session.execute(select(Fixture).where(Fixture.status == "live")))
        .scalars()
        .all()
    )
    finished_unsynced = (
        (
            await session.execute(
                select(Fixture)
                .where(
                    Fixture.status == "finished",
                    Fixture.summary_synced_at.is_(None),
                )
                .order_by(Fixture.kickoff_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [*live, *finished_unsynced][:SUMMARY_CALL_CAP]


async def run_ingestion() -> IngestionRun:
    async with SessionLocal() as session:
        run = IngestionRun()
        session.add(run)
        await session.flush()

        # Steps 1–4: scoreboard → validate → normalize → upsert
        fixtures_updated = 0
        scoreboard = await fetcher.fetch_espn_scoreboard(await _scoreboard_window(session))
        if scoreboard is not None:
            cache = await load_team_cache(session)
            for event in scoreboard.events:
                try:
                    normalized = normalize_event(event)
                    fixture, _ = await upsert_fixture(session, normalized, cache)
                    await replace_goals(session, fixture, normalized, cache)
                    fixtures_updated += 1
                except Exception:
                    logger.warning("event_ingest_failed event=%s", event.id, exc_info=True)

            # Stats + lineups for live / recently finished fixtures
            for fixture in await _summary_targets(session):
                summary = await fetcher.fetch_espn_summary(fixture.external_id)
                if summary is None:
                    continue
                normalized_summary = normalize_summary(summary)
                await upsert_match_stats(session, fixture, normalized_summary.stats, cache)
                await replace_lineups(session, fixture, normalized_summary.lineups, cache)
                await apply_assists(session, fixture, normalized_summary.assists)
                fixture.summary_synced_at = datetime.now(UTC)
        else:
            logger.warning("espn_scoreboard_unavailable — serving last cached data")

        # Secondary source (cross-check + scorers); calls spaced 7 s in fetcher
        fd_matches = await fetcher.fetch_fd_finished_matches()
        fd_standings = await fetcher.fetch_fd_standings()
        fd_scorers = await fetcher.fetch_fd_scorers()

        # Step 5: aggregate
        await aggregate(session, fd_standings, fd_scorers)

        # Step 6: reconcile
        reconciliation_flags = await reconcile(session, fd_matches)

        # Step 7: enrich
        insights_generated = await enrich(session)

        run.finished_at = datetime.now(UTC)
        run.status = "ok"
        run.fixtures_updated = fixtures_updated
        run.insights_generated = insights_generated
        run.reconciliation_flags = reconciliation_flags
        await session.commit()

        logger.info(
            "ingestion_run_complete id=%s fixtures=%s insights=%s flags=%s duration_s=%.1f",
            run.id,
            fixtures_updated,
            insights_generated,
            reconciliation_flags,
            (run.finished_at - run.started_at).total_seconds()
            if run.started_at
            else -1,
        )
        return run


async def _any_live(session: AsyncSession) -> bool:
    return (
        await session.execute(select(Fixture.id).where(Fixture.status == "live").limit(1))
    ).scalar_one_or_none() is not None


async def _scheduled_job() -> None:
    global _consecutive_failures
    try:
        await run_ingestion()
        _consecutive_failures = 0
    except Exception:
        _consecutive_failures += 1
        logger.error("ingestion_run_failed consecutive=%s", _consecutive_failures, exc_info=True)
        if _consecutive_failures >= 5:
            logger.critical("ingestion_failing consecutive_failures=%s", _consecutive_failures)
    finally:
        await _schedule_next()


async def _schedule_next() -> None:
    settings = get_settings()
    try:
        async with SessionLocal() as session:
            live = await _any_live(session)
    except Exception:
        live = False
    seconds = settings.LIVE_POLL_INTERVAL_SECONDS if live else settings.INGEST_INTERVAL_SECONDS
    scheduler.add_job(
        _scheduled_job,
        trigger="date",
        run_date=datetime.now(UTC) + timedelta(seconds=seconds),
        id="ingestion",
        replace_existing=True,
    )


def start_scheduler() -> None:
    scheduler.start()
    scheduler.add_job(
        _scheduled_job,
        trigger="date",
        run_date=datetime.now(UTC) + timedelta(seconds=3),
        id="ingestion",
        replace_existing=True,
    )
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
