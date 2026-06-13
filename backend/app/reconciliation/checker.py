"""Two-source score reconciliation (CLAUDE.md §5.3 step 6, api-research.md §6.1).

For every finished fixture, compare the ESPN score (already upserted on the
fixture) against football-data.org. Match → verified=true. Mismatch →
verified=false, both values logged, ESPN (primary) still served. A mismatch
persisting beyond RECONCILIATION_SCORE_MISMATCH_ALERT_AFTER consecutive runs
escalates to a CRITICAL log (api-research §9). A cross-check failure never
blocks the ingestion run.

football-data fixtures are joined to ours via the unordered pair of 3-letter
team codes plus a 24-hour kickoff window (api-research §5).
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingestion.schemas.football_data import FDMatchesResponse
from app.models import ExternalIdMap, Fixture, Team

logger = logging.getLogger(__name__)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite (tests) returns naive datetimes; everything here compares in UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _parse_fd_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


async def reconcile(session: AsyncSession, fd_matches: FDMatchesResponse | None) -> int:
    """Returns the number of fixtures flagged unverified this run."""
    if fd_matches is None:
        logger.warning("reconciliation_skipped reason=no_football_data")
        return 0

    settings = get_settings()
    teams = (await session.execute(select(Team))).scalars().all()
    team_by_id = {team.id: team for team in teams}
    team_by_code = {team.code: team for team in teams if team.code}

    # fd match lookup: unordered code pair → list of (kickoff, home_tla, scores)
    fd_index: dict[frozenset[str], list[tuple[datetime | None, str, int, int]]] = {}
    for match in fd_matches.matches:
        if match.homeTeam is None or match.awayTeam is None:
            continue
        home_tla, away_tla = match.homeTeam.tla, match.awayTeam.tla
        full_time = match.score.fullTime if match.score else None
        if not home_tla or not away_tla or full_time is None:
            continue
        if full_time.home is None or full_time.away is None:
            continue
        fd_index.setdefault(frozenset({home_tla, away_tla}), []).append(
            (_parse_fd_date(match.utcDate), home_tla, full_time.home, full_time.away)
        )
        # Record football-data team ids in the cross-source map (api-research §5).
        for fd_team in (match.homeTeam, match.awayTeam):
            local = team_by_code.get(fd_team.tla or "")
            if local is not None and fd_team.id is not None:
                await _ensure_team_map(session, local.id, str(fd_team.id))

    finished = (
        (await session.execute(select(Fixture).where(Fixture.status == "finished")))
        .scalars()
        .all()
    )

    flags = 0
    now = datetime.now(UTC)
    for fixture in finished:
        home = team_by_id.get(fixture.home_team_id)
        away = team_by_id.get(fixture.away_team_id)
        if home is None or away is None or not home.code or not away.code:
            continue

        candidates = fd_index.get(frozenset({home.code, away.code}), [])
        fd_score: tuple[int, int] | None = None
        for kickoff, home_tla, fd_home, fd_away in candidates:
            fixture_kickoff = _aware(fixture.kickoff_at)
            if (
                kickoff is not None
                and fixture_kickoff is not None
                and abs(kickoff - fixture_kickoff) > timedelta(hours=24)
            ):
                continue
            # Orient to our home team in case fd swapped home/away.
            fd_score = (fd_home, fd_away) if home_tla == home.code else (fd_away, fd_home)
            break

        if fd_score is None:
            # One source hasn't reported yet — unverified, not an alert.
            fixture.verified = False
            continue

        espn_score = (fixture.home_score, fixture.away_score)
        if espn_score == fd_score:
            fixture.verified = True
            fixture.verified_at = now
            fixture.mismatch_count = 0
        else:
            fixture.verified = False
            fixture.mismatch_count += 1
            flags += 1
            logger.warning(
                "score_mismatch fixture_id=%s espn=%s football_data=%s",
                fixture.id,
                espn_score,
                fd_score,
            )
            if fixture.mismatch_count >= settings.RECONCILIATION_SCORE_MISMATCH_ALERT_AFTER:
                logger.critical(
                    "persistent_score_mismatch fixture_id=%s espn=%s football_data=%s runs=%s",
                    fixture.id,
                    espn_score,
                    fd_score,
                    fixture.mismatch_count,
                )

    await session.flush()
    return flags


async def _ensure_team_map(session: AsyncSession, internal_id: int, fd_id: str) -> None:
    existing = (
        await session.execute(
            select(ExternalIdMap).where(
                ExternalIdMap.entity_type == "team",
                ExternalIdMap.source == "football_data",
                ExternalIdMap.external_id == fd_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            ExternalIdMap(
                internal_id=internal_id,
                entity_type="team",
                source="football_data",
                external_id=fd_id,
            )
        )
