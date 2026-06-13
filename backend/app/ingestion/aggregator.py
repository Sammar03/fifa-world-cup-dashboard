"""Recomputes derived tables from raw tables (CLAUDE.md §5.3 step 5, ADR-003).

Standings are NEVER taken from a provider — they are recomputed from finished
fixtures every run, then diffed against football-data.org standings; any points
difference logs CRITICAL (it means an aggregator bug or source data error).

Scorer stats come from football-data.org (sole scorer source, api-research §7).
In keyless development mode they degrade to a local derivation from the goals +
lineups tables (goals counted, assists unknown → 0) so the page is not empty;
position and GK clean sheets are derived from ESPN lineup data in both modes
(owner decision 2026-06-12).

The computation core is pure functions over plain values — unit-testable with
no DB (tests/test_aggregator.py).
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.schemas.football_data import FDScorersResponse, FDStandingsResponse
from app.models import Fixture, Goal, LineupEntry, Player, ScorerStat, Standing, Team

logger = logging.getLogger(__name__)


# --- Pure core ------------------------------------------------------------------


@dataclass
class StandingTotals:
    team_id: int
    group_label: str
    team_name: str = ""
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


@dataclass
class FixtureResult:
    """The minimal fixture view the standings computation needs."""

    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int


def compute_standings(
    results: list[FixtureResult],
    team_groups: dict[int, str],
    team_names: dict[int, str] | None = None,
) -> list[StandingTotals]:
    """Points from finished fixtures only: win 3, draw 1 (api-research §6.3)."""
    names = team_names or {}
    totals: dict[int, StandingTotals] = {
        team_id: StandingTotals(team_id=team_id, group_label=group, team_name=names.get(team_id, ""))
        for team_id, group in team_groups.items()
    }

    for result in results:
        home = totals.get(result.home_team_id)
        away = totals.get(result.away_team_id)
        for side, scored, conceded in (
            (home, result.home_score, result.away_score),
            (away, result.away_score, result.home_score),
        ):
            if side is None:
                continue
            side.played += 1
            side.goals_for += scored
            side.goals_against += conceded
            if scored > conceded:
                side.won += 1
                side.points += 3
            elif scored == conceded:
                side.drawn += 1
                side.points += 1
            else:
                side.lost += 1

    return list(totals.values())


def fifa_sort_key(totals: StandingTotals) -> tuple[int, int, int, str]:
    """Official FIFA 2026 group tiebreaker (ADR-003):
    points DESC → goal diff DESC → goals for DESC → team name ASC."""
    return (-totals.points, -totals.goal_diff, -totals.goals_for, totals.team_name)


def sort_group(rows: list[StandingTotals]) -> list[StandingTotals]:
    return sorted(rows, key=fifa_sort_key)


def form_from_results(results: list[str], limit: int = 5) -> list[str]:
    """Last up-to-`limit` of a chronological W/D/L list, oldest → newest."""
    return results[-limit:]


async def team_form(session: "AsyncSession", team_id: int, limit: int = 5) -> list[str]:
    """W/D/L chips for a team's finished fixtures, oldest → newest (frontend
    Standing.form / TeamResponse.form). Shared by routers and AI context."""
    fixtures = (
        (
            await session.execute(
                select(Fixture)
                .where(
                    Fixture.status == "finished",
                    Fixture.home_score.is_not(None),
                    Fixture.away_score.is_not(None),
                    (Fixture.home_team_id == team_id) | (Fixture.away_team_id == team_id),
                )
                .order_by(Fixture.kickoff_at.asc())
            )
        )
        .scalars()
        .all()
    )
    results = []
    for fixture in fixtures:
        if fixture.home_team_id == team_id:
            scored, conceded = fixture.home_score, fixture.away_score
        else:
            scored, conceded = fixture.away_score, fixture.home_score
        results.append("W" if scored > conceded else "D" if scored == conceded else "L")
    return form_from_results(results, limit)


async def all_team_forms(session: "AsyncSession", limit: int = 5) -> dict[int, list[str]]:
    """Form for every team in one fixtures scan — avoids N+1 on /standings."""
    fixtures = (
        (
            await session.execute(
                select(Fixture)
                .where(
                    Fixture.status == "finished",
                    Fixture.home_score.is_not(None),
                    Fixture.away_score.is_not(None),
                )
                .order_by(Fixture.kickoff_at.asc())
            )
        )
        .scalars()
        .all()
    )
    histories: dict[int, list[str]] = {}
    for fixture in fixtures:
        for team_id, scored, conceded in (
            (fixture.home_team_id, fixture.home_score, fixture.away_score),
            (fixture.away_team_id, fixture.away_score, fixture.home_score),
        ):
            if team_id is None:
                continue
            result = "W" if scored > conceded else "D" if scored == conceded else "L"
            histories.setdefault(team_id, []).append(result)
    return {team_id: form_from_results(history, limit) for team_id, history in histories.items()}


@dataclass
class ScorerRow:
    player_external_id: str
    player_name: str
    team_id: int | None
    goals: int = 0
    assists: int = 0
    matches_played: int = 0
    position: str | None = None
    clean_sheets: int | None = None
    fd_team_tla: str | None = field(default=None)


# --- DB orchestration -------------------------------------------------------------


def _map_fd_position(raw: str | None) -> str | None:
    if not raw:
        return None
    lowered = raw.lower()
    if "keeper" in lowered:
        return "GK"
    if "defen" in lowered or "back" in lowered:
        return "DF"
    if "midfield" in lowered:
        return "MF"
    if "forward" in lowered or "offence" in lowered or "winger" in lowered or "striker" in lowered:
        return "FW"
    return None


async def aggregate(
    session: AsyncSession,
    fd_standings: FDStandingsResponse | None = None,
    fd_scorers: FDScorersResponse | None = None,
) -> None:
    await _recompute_standings(session, fd_standings)
    await _recompute_scorer_stats(session, fd_scorers)


async def _recompute_standings(
    session: AsyncSession, fd_standings: FDStandingsResponse | None
) -> None:
    teams = (await session.execute(select(Team).where(Team.group_label.is_not(None)))).scalars().all()
    team_groups = {team.id: team.group_label for team in teams if team.group_label}
    team_names = {team.id: team.name for team in teams}
    team_by_code = {team.code: team for team in teams if team.code}

    finished = (
        (
            await session.execute(
                select(Fixture).where(
                    Fixture.status == "finished",
                    Fixture.home_score.is_not(None),
                    Fixture.away_score.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    results = [
        FixtureResult(
            home_team_id=fixture.home_team_id,
            away_team_id=fixture.away_team_id,
            home_score=fixture.home_score,
            away_score=fixture.away_score,
        )
        for fixture in finished
        if fixture.home_team_id is not None and fixture.away_team_id is not None
    ]

    rows = compute_standings(results, team_groups, team_names)

    await session.execute(delete(Standing))
    now = datetime.now(UTC)
    for row in rows:
        session.add(
            Standing(
                team_id=row.team_id,
                group_label=row.group_label,
                played=row.played,
                won=row.won,
                drawn=row.drawn,
                lost=row.lost,
                goals_for=row.goals_for,
                goals_against=row.goals_against,
                points=row.points,
                updated_at=now,
            )
        )
    await session.flush()

    # Cross-check vs football-data.org (api-research §6.3): any points difference
    # is CRITICAL — either our aggregator is wrong or the source data is.
    if fd_standings is not None:
        ours = {row.team_id: row for row in rows}
        for group in fd_standings.standings:
            for entry in group.table:
                if entry.team is None or not entry.team.tla or entry.points is None:
                    continue
                team = team_by_code.get(entry.team.tla)
                if team is None:
                    continue
                local = ours.get(team.id)
                if local is not None and local.points != entry.points:
                    logger.critical(
                        "standings_points_mismatch team=%s ours=%s football_data=%s",
                        team.code,
                        local.points,
                        entry.points,
                    )


async def _recompute_scorer_stats(
    session: AsyncSession, fd_scorers: FDScorersResponse | None
) -> None:
    espn_positions, espn_positions_token = await _espn_positions_by_name(session)
    gk_clean_sheets, gk_clean_sheets_token = await _gk_clean_sheets(session)
    espn_assists, espn_assists_token, espn_assist_names = await _espn_assists(session)
    appearances = await _appearances_by_name(session)
    team_by_name = await _team_by_lineup_name(session)

    if fd_scorers is not None and fd_scorers.scorers:
        rows = await _scorer_rows_from_fd(session, fd_scorers)
    else:
        rows = await _scorer_rows_from_local(session)

    # ESPN keyEvents are the assist source of record (football-data free tier
    # returns null for most goals). Override each scorer's assists with the
    # ESPN-derived count when we have one for that name.
    for row in rows:
        espn = _lookup_by_name(espn_assists, espn_assists_token, row.player_name)
        if espn is not None:
            row.assists = espn

    covered = {_name_key(r.player_name) for r in rows}

    # Scorer feeds only list players with goals, so goalkeepers never appear and
    # the frontend's GK-only clean-sheets board would always be empty. Append
    # lineup-derived GK rows (0 goals) for keepers not already present.
    rows.extend(await _goalkeeper_rows(session, existing=covered))

    # Players who assisted but did not score won't be in the scorer feed — add
    # them so the Assists board is complete (position from ESPN lineups). Dedup
    # by token key so a scorer listed under a different name order (football-data
    # "In-beom Hwang" vs ESPN assist "Hwang In-Beom") is not added twice.
    covered_tokens = {_token_key(r.player_name) for r in rows}
    rows.extend(
        _assist_only_rows(
            espn_assists, espn_assist_names, appearances, team_by_name, covered_tokens
        )
    )

    await session.execute(delete(ScorerStat))
    now = datetime.now(UTC)
    for row in rows:
        position = row.position or _lookup_by_name(
            espn_positions, espn_positions_token, row.player_name
        )
        clean_sheets = (
            _lookup_by_name(gk_clean_sheets, gk_clean_sheets_token, row.player_name)
            if position == "GK"
            else None
        )
        player = await _get_or_create_player(
            session, row.player_external_id, row.player_name, row.team_id, position
        )
        session.add(
            ScorerStat(
                player_id=player.id,
                goals=row.goals,
                assists=row.assists,
                matches_played=row.matches_played,
                position=position,
                clean_sheets=clean_sheets,
                updated_at=now,
            )
        )
    await session.flush()


def _name_key(name: str) -> str:
    return name.strip().lower()


def _token_key(name: str) -> str:
    """Order-independent name key: football-data writes "In-beom Hwang" while
    ESPN lineups write "Hwang In-Beom". Sorting the tokens makes both collapse
    to the same key so position / clean-sheet enrichment matches across sources."""
    return " ".join(sorted(_name_key(name).replace("-", " ").split()))


def _lookup_by_name(table: dict, token_table: dict, name: str):
    """Exact name first, then order-independent token match."""
    hit = table.get(_name_key(name))
    if hit is not None:
        return hit
    return token_table.get(_token_key(name))


async def _espn_positions_by_name(session: AsyncSession) -> tuple[dict[str, str], dict[str, str]]:
    """Position by player name from ESPN lineups, as (exact-key, token-key) maps."""
    entries = (
        await session.execute(
            select(LineupEntry.player_name, LineupEntry.position).where(
                LineupEntry.position.is_not(None)
            )
        )
    ).all()
    exact = {_name_key(name): position for name, position in entries if name}
    token = {_token_key(name): position for name, position in entries if name}
    return exact, token


async def _espn_assists(
    session: AsyncSession,
) -> tuple[dict[str, int], dict[str, int], dict[str, str]]:
    """Assist tallies per player from goals.assist_player_name (ESPN keyEvents):
    (exact-key count, token-key count, exact-key → original display name)."""
    rows = (
        await session.execute(
            select(Goal.assist_player_name).where(Goal.assist_player_name.is_not(None))
        )
    ).all()
    exact: dict[str, int] = {}
    token: dict[str, int] = {}
    display: dict[str, str] = {}
    for (name,) in rows:
        if not name:
            continue
        exact[_name_key(name)] = exact.get(_name_key(name), 0) + 1
        token[_token_key(name)] = token.get(_token_key(name), 0) + 1
        display.setdefault(_name_key(name), name.strip())
    return exact, token, display


async def _appearances_by_name(session: AsyncSession) -> dict[str, int]:
    """Distinct fixtures each player appeared in (from lineups), by name key."""
    rows = (
        await session.execute(
            select(LineupEntry.player_name, func.count(func.distinct(LineupEntry.fixture_id)))
            .group_by(LineupEntry.player_name)
        )
    ).all()
    return {_name_key(name): count for name, count in rows if name}


async def _team_by_lineup_name(session: AsyncSession) -> dict[str, int]:
    """Team id per player from lineups, by token key — lets assist-only players
    (not in the scorer feed) carry their team on the board."""
    rows = (
        await session.execute(select(LineupEntry.player_name, LineupEntry.team_id))
    ).all()
    return {_token_key(name): team_id for name, team_id in rows if name and team_id}


def _assist_only_rows(
    espn_assists: dict[str, int],
    display: dict[str, str],
    appearances: dict[str, int],
    team_by_name: dict[str, int],
    covered_tokens: set[str],
) -> list[ScorerRow]:
    """Rows for players who assisted but did not score (not in the scorer feed).
    `covered_tokens` holds order-independent name keys already in the row set so a
    player who also scored (possibly under a different name order) isn't doubled."""
    rows = []
    for name_key, assists in espn_assists.items():
        name = display.get(name_key, name_key.title())
        token = _token_key(name)
        if token in covered_tokens:
            continue
        rows.append(
            ScorerRow(
                player_external_id=f"assist-{name_key}",
                player_name=name,
                team_id=team_by_name.get(token),
                goals=0,
                assists=assists,
                matches_played=appearances.get(name_key, 1),
            )
        )
        covered_tokens.add(token)
    return rows


async def _gk_clean_sheets(session: AsyncSession) -> tuple[dict[str, int], dict[str, int]]:
    """Clean sheets per goalkeeper (GK in the lineup, team conceded 0 in a
    finished fixture). Returns (exact-key, token-key) maps. Owner decision
    2026-06-12. Every GK who played gets a 0 entry so a keeper who has played
    but kept no clean sheet shows 0 rather than null on the GK board."""
    rows = (
        await session.execute(
            select(LineupEntry.player_name, Fixture.home_team_id, Fixture.home_score,
                   Fixture.away_score, LineupEntry.team_id)
            .join(Fixture, Fixture.id == LineupEntry.fixture_id)
            .where(LineupEntry.position == "GK", Fixture.status == "finished")
        )
    ).all()
    counts: dict[str, int] = {}
    token_counts: dict[str, int] = {}
    for player_name, home_team_id, home_score, away_score, team_id in rows:
        if home_score is None or away_score is None or not player_name:
            continue
        conceded = away_score if team_id == home_team_id else home_score
        increment = 1 if conceded == 0 else 0
        key, tkey = _name_key(player_name), _token_key(player_name)
        counts[key] = counts.get(key, 0) + increment
        token_counts[tkey] = token_counts.get(tkey, 0) + increment
    return counts, token_counts


async def _scorer_rows_from_fd(
    session: AsyncSession, fd_scorers: FDScorersResponse
) -> list[ScorerRow]:
    teams = (await session.execute(select(Team))).scalars().all()
    team_by_code = {team.code: team for team in teams if team.code}
    rows = []
    for scorer in fd_scorers.scorers:
        if scorer.player is None or not scorer.player.name:
            continue
        team = team_by_code.get(scorer.team.tla) if scorer.team and scorer.team.tla else None
        rows.append(
            ScorerRow(
                player_external_id=f"fd-{scorer.player.id}" if scorer.player.id else "",
                player_name=scorer.player.name,
                team_id=team.id if team else None,
                goals=scorer.goals or 0,
                assists=scorer.assists or 0,
                matches_played=scorer.playedMatches or 0,
                position=_map_fd_position(scorer.player.position),
            )
        )
    return rows


async def _goalkeeper_rows(session: AsyncSession, existing: set[str]) -> list[ScorerRow]:
    entries = (
        await session.execute(
            select(
                LineupEntry.player_name,
                LineupEntry.team_id,
                func.count(func.distinct(LineupEntry.fixture_id)),
            )
            .where(LineupEntry.position == "GK")
            .group_by(LineupEntry.player_name, LineupEntry.team_id)
        )
    ).all()
    rows = []
    for player_name, team_id, appearances in entries:
        if not player_name or _name_key(player_name) in existing:
            continue
        rows.append(
            ScorerRow(
                player_external_id=f"local-{_name_key(player_name)}",
                player_name=player_name,
                team_id=team_id,
                goals=0,
                assists=0,
                matches_played=appearances,
                position="GK",
            )
        )
    return rows


async def _scorer_rows_from_local(session: AsyncSession) -> list[ScorerRow]:
    """Keyless fallback: goals from our own goals table (ESPN timeline), matches
    played from lineup appearances. Assists are unknown locally → 0."""
    goal_rows = (
        await session.execute(
            select(Goal.player_name, Goal.team_id, func.count())
            .where(Goal.player_name.is_not(None), Goal.type != "own_goal")
            .group_by(Goal.player_name, Goal.team_id)
        )
    ).all()
    appearances = (
        await session.execute(
            select(LineupEntry.player_name, func.count(func.distinct(LineupEntry.fixture_id)))
            .group_by(LineupEntry.player_name)
        )
    ).all()
    appearance_map = {_name_key(name): count for name, count in appearances if name}

    rows = []
    for player_name, team_id, goal_count in goal_rows:
        rows.append(
            ScorerRow(
                player_external_id=f"local-{_name_key(player_name)}",
                player_name=player_name,
                team_id=team_id,
                goals=goal_count,
                assists=0,
                matches_played=appearance_map.get(_name_key(player_name), 1),
            )
        )
    return rows


async def _get_or_create_player(
    session: AsyncSession,
    external_id: str,
    name: str,
    team_id: int | None,
    position: str | None,
):
    key = external_id or f"name-{_name_key(name)}"
    player = (
        await session.execute(select(Player).where(Player.external_id == key))
    ).scalar_one_or_none()
    if player is None:
        player = Player(external_id=key, name=name, team_id=team_id, position=position)
        session.add(player)
        await session.flush()
        return player
    if position and not player.position:
        player.position = position
    if team_id is not None and player.team_id is None:
        player.team_id = team_id
    return player
