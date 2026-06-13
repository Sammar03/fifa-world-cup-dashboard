"""DB write operations (CLAUDE.md §5.3 step 4).

Portable select-then-write upserts (no dialect-specific ON CONFLICT) — the data
volume is tiny (48+ teams, 104 fixtures) and the same code runs on Postgres in
production and SQLite in tests. Callers own the transaction; nothing here commits.

Ownership rules:
- The seed (openfootball) owns group_label and round on fixtures, and group_label
  on teams — ingestion never overwrites them.
- ESPN owns kickoff_at, venue, status, scores, minute, goals, stats, lineups.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.normalizer import (
    NormalizedFixture,
    NormalizedLineup,
    NormalizedTeam,
)
from app.models import Fixture, Goal, LineupEntry, MatchStat, Player, Team

logger = logging.getLogger(__name__)


async def load_team_cache(session: AsyncSession) -> dict[str, Team]:
    """All teams keyed by external_id (ESPN team id)."""
    teams = (await session.execute(select(Team))).scalars().all()
    return {team.external_id: team for team in teams}


async def upsert_team(
    session: AsyncSession, normalized: NormalizedTeam, cache: dict[str, Team]
) -> Team:
    team = cache.get(normalized.external_id)
    if team is None:
        team = Team(
            external_id=normalized.external_id,
            name=normalized.name,
            code=normalized.code,
            flag_url=normalized.flag_url,
        )
        session.add(team)
        await session.flush()
        cache[normalized.external_id] = team
        return team

    team.name = normalized.name or team.name
    team.code = normalized.code or team.code
    team.flag_url = normalized.flag_url or team.flag_url
    team.updated_at = datetime.now(UTC)
    return team


async def upsert_fixture(
    session: AsyncSession,
    normalized: NormalizedFixture,
    cache: dict[str, Team],
) -> tuple[Fixture, str | None]:
    """Returns (fixture, previous_status). previous_status None for new rows.

    The status transition drives AI enrichment (step 7): an insight is generated
    when a fixture is seen in `scheduled` or `finished` without a cached insight.
    """
    home_team = await upsert_team(session, normalized.home, cache) if normalized.home else None
    away_team = await upsert_team(session, normalized.away, cache) if normalized.away else None

    fixture = (
        await session.execute(select(Fixture).where(Fixture.external_id == normalized.external_id))
    ).scalar_one_or_none()

    previous_status = fixture.status if fixture else None

    if fixture is None:
        fixture = Fixture(external_id=normalized.external_id, status=normalized.status)
        session.add(fixture)

    if home_team is not None:
        fixture.home_team_id = home_team.id
    if away_team is not None:
        fixture.away_team_id = away_team.id
    if normalized.kickoff_at is not None:
        fixture.kickoff_at = normalized.kickoff_at
    if normalized.venue:
        fixture.venue = normalized.venue
    # A status change (e.g. live → finished) invalidates the last summary sync,
    # so the new state gets one fresh stats/lineups/assists fetch.
    if previous_status is not None and previous_status != normalized.status:
        fixture.summary_synced_at = None
    fixture.status = normalized.status
    fixture.home_score = normalized.home.score if normalized.home else None
    fixture.away_score = normalized.away.score if normalized.away else None
    fixture.minute = normalized.minute
    fixture.last_updated_at = datetime.now(UTC)

    await session.flush()
    return fixture, previous_status


async def replace_goals(
    session: AsyncSession,
    fixture: Fixture,
    normalized: NormalizedFixture,
    cache: dict[str, Team],
) -> None:
    """ESPN scoreboard is the goal source — wholesale replace per fixture is
    idempotent and inherently deduplicated (BACKLOG DEBT-003).

    Assists come from a separate source (summary keyEvents, not the scoreboard),
    so any assist_player_name already attached is preserved across the refresh —
    keyed by (minute, scorer, type) — otherwise a scoreboard-only run would wipe
    assists for finished matches that no longer fetch a summary.
    """
    if not normalized.goals:
        return

    existing = (
        await session.execute(select(Goal).where(Goal.fixture_id == fixture.id))
    ).scalars().all()
    preserved_assists = {
        (row.minute, row.player_name, row.type): row.assist_player_name
        for row in existing
        if row.assist_player_name
    }

    await session.execute(delete(Goal).where(Goal.fixture_id == fixture.id))
    for goal in normalized.goals:
        team = cache.get(goal.team_external_id) if goal.team_external_id else None
        player_id = None
        if goal.player_external_id:
            player = await _upsert_player(
                session,
                external_id=goal.player_external_id,
                name=goal.player_name or "",
                team_id=team.id if team else None,
                position=None,
            )
            player_id = player.id if player else None
        session.add(
            Goal(
                fixture_id=fixture.id,
                player_id=player_id,
                player_name=goal.player_name,
                assist_player_name=preserved_assists.get((goal.minute, goal.player_name, goal.type)),
                team_id=team.id if team else None,
                minute=goal.minute,
                type=goal.type,
            )
        )
    await session.flush()


async def apply_assists(
    session: AsyncSession,
    fixture: Fixture,
    assists: list,
) -> None:
    """Attach assist providers (from summary keyEvents) to this fixture's goals,
    matching by minute. Called after replace_goals when a summary is processed."""
    if not assists:
        return
    goals = (
        await session.execute(select(Goal).where(Goal.fixture_id == fixture.id))
    ).scalars().all()
    by_minute: dict[int, Goal] = {g.minute: g for g in goals if g.minute is not None}
    for assist in assists:
        goal = by_minute.get(assist.minute)
        if goal is not None:
            goal.assist_player_name = assist.assister_name
    await session.flush()


async def upsert_match_stats(
    session: AsyncSession,
    fixture: Fixture,
    stats_by_team: dict[str, dict[str, float | int | None]],
    cache: dict[str, Team],
) -> None:
    for team_external_id, stats in stats_by_team.items():
        team = cache.get(team_external_id)
        if team is None:
            logger.warning(
                "match_stats_unknown_team fixture=%s espn_team=%s", fixture.id, team_external_id
            )
            continue
        row = (
            await session.execute(
                select(MatchStat).where(
                    MatchStat.fixture_id == fixture.id, MatchStat.team_id == team.id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = MatchStat(fixture_id=fixture.id, team_id=team.id)
            session.add(row)
        for column, value in stats.items():
            setattr(row, column, value)
    await session.flush()


async def replace_lineups(
    session: AsyncSession,
    fixture: Fixture,
    lineups: list[NormalizedLineup],
    cache: dict[str, Team],
) -> None:
    for lineup in lineups:
        team = cache.get(lineup.team_external_id)
        if team is None:
            logger.warning(
                "lineup_unknown_team fixture=%s espn_team=%s", fixture.id, lineup.team_external_id
            )
            continue
        await session.execute(
            delete(LineupEntry).where(
                LineupEntry.fixture_id == fixture.id, LineupEntry.team_id == team.id
            )
        )
        for entry in lineup.players:
            session.add(
                LineupEntry(
                    fixture_id=fixture.id,
                    team_id=team.id,
                    player_name=entry.player_name,
                    number=entry.number,
                    position=entry.position,
                    is_starter=entry.is_starter,
                    formation=lineup.formation,
                )
            )
            if entry.player_external_id:
                await _upsert_player(
                    session,
                    external_id=entry.player_external_id,
                    name=entry.player_name,
                    team_id=team.id,
                    position=entry.position,
                )
    await session.flush()


async def _upsert_player(
    session: AsyncSession,
    *,
    external_id: str,
    name: str,
    team_id: int | None,
    position: str | None,
) -> Player | None:
    if not external_id or not name:
        return None
    key = f"espn-{external_id}"
    player = (
        await session.execute(select(Player).where(Player.external_id == key))
    ).scalar_one_or_none()
    if player is None:
        player = Player(external_id=key, name=name, team_id=team_id, position=position)
        session.add(player)
        await session.flush()
        return player
    player.name = name or player.name
    player.team_id = team_id if team_id is not None else player.team_id
    if position:
        player.position = position
    player.updated_at = datetime.now(UTC)
    return player
