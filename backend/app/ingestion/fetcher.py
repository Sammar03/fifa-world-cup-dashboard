"""HTTP calls to the three approved sources (api-research.md §2–4, §8).

Every call has a timeout, bounded retries with exponential backoff, and never
raises past this module's public functions without the caller expecting it.
football-data.org calls are spaced 7 s apart by the caller (10 req/min limit).
No other module performs HTTP — and the request path NEVER reaches this file
(CLAUDE.md §5.1).
"""

import asyncio
import logging

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.ingestion.schemas.espn import EspnScoreboard, EspnSummary
from app.ingestion.schemas.football_data import (
    FDMatchesResponse,
    FDScorersResponse,
    FDStandingsResponse,
)
from app.ingestion.schemas.openfootball import OFWorldCup

logger = logging.getLogger(__name__)

USER_AGENT = "WorldCupDashboard/1.0 (portfolio project)"

# Spacing between consecutive football-data.org calls (api-research.md §3).
FOOTBALL_DATA_CALL_SPACING_SECONDS = 7


async def _get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    timeout_seconds: int,
    retries: int,
) -> dict | None:
    """GET with timeout + exponential backoff. Returns None on final failure."""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                await asyncio.sleep(2**attempt)  # 1s, 2s, 4s…
    logger.warning("fetch_failed url=%s error=%s", url, last_error)
    return None


# --- ESPN (primary, no key) ----------------------------------------------------


async def fetch_espn_scoreboard(dates_range: str) -> EspnScoreboard | None:
    """One call returns every fixture in the range (verified live: all 104 events).

    `dates_range` format: YYYYMMDD-YYYYMMDD.
    """
    settings = get_settings()
    raw = await _get_json(
        f"{settings.ESPN_API_BASE_URL}/scoreboard",
        headers={"User-Agent": USER_AGENT},
        params={"dates": dates_range, "limit": "200"},
        timeout_seconds=settings.ESPN_TIMEOUT_SECONDS,
        retries=settings.ESPN_MAX_RETRIES,
    )
    if raw is None:
        return None
    try:
        return EspnScoreboard.model_validate(raw)
    except ValidationError as exc:
        logger.warning("espn_scoreboard_validation_failed error=%s", exc)
        return None


async def fetch_espn_summary(espn_event_id: str) -> EspnSummary | None:
    """Match summary: boxscore stats + rosters. Fields may be absent pre-match."""
    settings = get_settings()
    raw = await _get_json(
        f"{settings.ESPN_API_BASE_URL}/summary",
        headers={"User-Agent": USER_AGENT},
        params={"event": espn_event_id},
        timeout_seconds=settings.ESPN_TIMEOUT_SECONDS,
        retries=settings.ESPN_MAX_RETRIES,
    )
    if raw is None:
        return None
    try:
        return EspnSummary.model_validate(raw)
    except ValidationError as exc:
        logger.warning("espn_summary_validation_failed event=%s error=%s", espn_event_id, exc)
        return None


# --- football-data.org (secondary, keyed) ---------------------------------------


def _fd_available() -> bool:
    key = get_settings().FOOTBALL_DATA_API_KEY
    return bool(key) and key != "your_key_here"


async def _fd_get(path: str, params: dict[str, str] | None = None) -> dict | None:
    settings = get_settings()
    return await _get_json(
        f"{settings.FOOTBALL_DATA_BASE_URL}{path}",
        headers={"X-Auth-Token": settings.FOOTBALL_DATA_API_KEY, "User-Agent": USER_AGENT},
        params=params,
        timeout_seconds=settings.FOOTBALL_DATA_TIMEOUT_SECONDS,
        retries=settings.FOOTBALL_DATA_MAX_RETRIES,
    )


async def fetch_fd_finished_matches() -> FDMatchesResponse | None:
    if not _fd_available():
        logger.warning("football_data_skipped reason=no_api_key")
        return None
    raw = await _fd_get("/competitions/WC/matches", {"status": "FINISHED"})
    if raw is None:
        return None
    try:
        return FDMatchesResponse.model_validate(raw)
    except ValidationError as exc:
        logger.warning("fd_matches_validation_failed error=%s", exc)
        return None


async def fetch_fd_standings() -> FDStandingsResponse | None:
    if not _fd_available():
        return None
    await asyncio.sleep(FOOTBALL_DATA_CALL_SPACING_SECONDS)
    raw = await _fd_get("/competitions/WC/standings")
    if raw is None:
        return None
    try:
        return FDStandingsResponse.model_validate(raw)
    except ValidationError as exc:
        logger.warning("fd_standings_validation_failed error=%s", exc)
        return None


async def fetch_fd_scorers(limit: int = 50) -> FDScorersResponse | None:
    if not _fd_available():
        return None
    await asyncio.sleep(FOOTBALL_DATA_CALL_SPACING_SECONDS)
    raw = await _fd_get("/competitions/WC/scorers", {"limit": str(limit)})
    if raw is None:
        return None
    try:
        return FDScorersResponse.model_validate(raw)
    except ValidationError as exc:
        logger.warning("fd_scorers_validation_failed error=%s", exc)
        return None


# --- openfootball (seed only) ----------------------------------------------------


async def fetch_openfootball() -> OFWorldCup:
    """Seed source. Unlike the runtime fetchers this FAILS LOUDLY: a broken seed
    must stop the seed script, not half-populate the database (api-research §4)."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            settings.OPENFOOTBALL_WORLDCUP_URL, headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
        return OFWorldCup.model_validate(response.json())
