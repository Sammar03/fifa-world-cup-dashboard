"""Seed the database before the first ingestion run (api-research.md §4).

Merges two keyless sources:
- openfootball/worldcup.json — canonical backbone: group labels (A–L), rounds,
  team→group assignment. Validation failures abort loudly.
- ESPN scoreboard — stable external ids, team codes/flags, kickoff times (UTC),
  venues, current status/scores. ESPN is the id authority: teams.external_id is
  the ESPN team id and fixtures.external_id is the ESPN event id.

The 2026 openfootball edition (verified live 2026-06-12) has NO team codes:
team1/team2 are plain names ("Mexico") or placeholder tokens ("W101", "1A",
"3A/B/C/D/F"). ESPN models the same placeholders as teams ("Group A Winner",
abbreviation "1A"), so every openfootball token is translated to its ESPN
display name and fixtures are matched by (team-name pair, kickoff within 36 h)
— the 24 h window of api-research §5 plus slack for timezone-shifted dates.

Idempotent: rerunning updates in place via external ids.

Usage (repo root):  python scripts/seed.py
"""

import asyncio
import logging
import re
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.ingestion.fetcher import fetch_espn_scoreboard, fetch_openfootball  # noqa: E402
from app.ingestion.normalizer import NormalizedFixture, normalize_event  # noqa: E402
from app.ingestion.schemas.openfootball import OFMatch  # noqa: E402
from app.ingestion.upsert import load_team_cache, replace_goals, upsert_fixture  # noqa: E402
from app.models import ExternalIdMap, Team  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("seed")

# openfootball name → ESPN displayName, for the five teams that differ
# (verified against both live sources on 2026-06-12).
OPENFOOTBALL_TO_ESPN_NAME = {
    "Bosnia & Herzegovina": "Bosnia-Herzegovina",
    "Czech Republic": "Czechia",
    "DR Congo": "Congo DR",
    "Turkey": "Türkiye",
    "USA": "United States",
}

# Knockout bracket: openfootball W{n}/L{n} tokens use global match numbers;
# ESPN names the same slots per round. Derived from the openfootball schedule
# (R32 = matches 73–88, R16 = 89–96, QF = 97–100, SF = 101–102).
_WINNER_ROUNDS = [
    (73, 88, "Round of 32 {i} Winner"),
    (89, 96, "Round of 16 {i} Winner"),
    (97, 100, "Quarterfinal {i} Winner"),
    (101, 102, "Semifinal {i} Winner"),
]


def of_team_to_espn_name(token: str) -> str:
    """Translate an openfootball team string (real name or placeholder token)
    into the ESPN displayName used for matching."""
    if token in OPENFOOTBALL_TO_ESPN_NAME:
        return OPENFOOTBALL_TO_ESPN_NAME[token]

    match = re.fullmatch(r"([12])([A-L])", token)
    if match:
        rank, group = match.groups()
        return f"Group {group} Winner" if rank == "1" else f"Group {group} 2nd Place"

    if token.startswith("3") and "/" in token:
        return f"Third Place Group {token[1:]}"

    match = re.fullmatch(r"W(\d+)", token)
    if match:
        num = int(match.group(1))
        for low, high, template in _WINNER_ROUNDS:
            if low <= num <= high:
                return template.format(i=num - low + 1)

    match = re.fullmatch(r"L(10[12])", token)
    if match:
        return f"Semifinal {int(match.group(1)) - 100} Loser"

    return token  # plain team name identical in both sources


def parse_of_kickoff(date: str, time: str | None) -> datetime | None:
    """openfootball local time "13:00 UTC-6" → aware UTC datetime."""
    try:
        day = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return None
    if not time:
        return day.replace(tzinfo=UTC)
    match = re.fullmatch(r"(\d{1,2}):(\d{2}) UTC([+-]\d{1,2})", time)
    if not match:
        return day.replace(tzinfo=UTC)
    hour, minute, offset = int(match.group(1)), int(match.group(2)), int(match.group(3))
    local = day.replace(hour=hour, minute=minute, tzinfo=timezone(timedelta(hours=offset)))
    return local.astimezone(UTC)


def of_round_label(of_round: str) -> str:
    return "Group stage" if of_round.startswith("Matchday") else of_round


def of_match_key(of_match: OFMatch) -> frozenset[str]:
    return frozenset(
        of_team_to_espn_name(token).lower() for token in (of_match.team1, of_match.team2)
    )


def fixture_key(normalized: NormalizedFixture) -> frozenset[str] | None:
    if normalized.home is None or normalized.away is None:
        return None
    return frozenset({normalized.home.name.lower(), normalized.away.name.lower()})


async def _ensure_map(
    session: AsyncSession, internal_id: int, entity_type: str, source: str, external_id: str
) -> None:
    existing = (
        await session.execute(
            select(ExternalIdMap).where(
                ExternalIdMap.entity_type == entity_type,
                ExternalIdMap.source == source,
                ExternalIdMap.external_id == external_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            ExternalIdMap(
                internal_id=internal_id,
                entity_type=entity_type,
                source=source,
                external_id=external_id,
            )
        )
    else:
        existing.internal_id = internal_id


async def main() -> None:
    openfootball = await fetch_openfootball()  # fails loudly by design
    logger.info("openfootball ok: %s matches", len(openfootball.matches))

    dates = sorted(m.date for m in openfootball.matches)
    window = f"{dates[0].replace('-', '')}-{dates[-1].replace('-', '')}"
    scoreboard = await fetch_espn_scoreboard(window)
    if scoreboard is None or not scoreboard.events:
        raise SystemExit("ESPN scoreboard unavailable — seed aborted, nothing written")
    logger.info("espn scoreboard ok: %s events", len(scoreboard.events))

    # openfootball matches indexed by translated team-name pair
    of_index: dict[frozenset[str], list[OFMatch]] = {}
    for of_match in openfootball.matches:
        of_index.setdefault(of_match_key(of_match), []).append(of_match)

    fixtures_written = 0
    matched = 0
    unmatched: list[str] = []

    async with SessionLocal() as session:
        cache = await load_team_cache(session)

        for event in scoreboard.events:
            normalized = normalize_event(event)
            fixture, _ = await upsert_fixture(session, normalized, cache)
            await replace_goals(session, fixture, normalized, cache)
            fixtures_written += 1
            await _ensure_map(session, fixture.id, "fixture", "espn", normalized.external_id)

            key = fixture_key(normalized)
            candidates = of_index.get(key, []) if key else []
            best: OFMatch | None = None
            best_delta = timedelta(hours=36)
            for candidate in candidates:
                of_kickoff = parse_of_kickoff(candidate.date, candidate.time)
                if of_kickoff is None or normalized.kickoff_at is None:
                    continue
                delta = abs(of_kickoff - normalized.kickoff_at)
                if delta < best_delta:
                    best, best_delta = candidate, delta

            if best is None:
                unmatched.append(f"{event.id} {event.name}")
                continue

            matched += 1
            if best.group:
                fixture.group_label = best.group.removeprefix("Group ").strip()
            fixture.round = of_round_label(best.round)
            await _ensure_map(
                session,
                fixture.id,
                "fixture",
                "openfootball",
                f"{best.date}|{best.team1}|{best.team2}",
            )
            if best_delta > timedelta(hours=1):
                logger.warning(
                    "kickoff_disagreement espn=%s openfootball=%s|%s delta=%s",
                    normalized.kickoff_at,
                    best.date,
                    best.time,
                    best_delta,
                )

        # Team group labels from openfootball group-stage matches
        teams_by_name = {
            team.name.lower(): team
            for team in (await session.execute(select(Team))).scalars().all()
        }
        groups_assigned = 0
        for of_match in openfootball.matches:
            if not of_match.group:
                continue
            letter = of_match.group.removeprefix("Group ").strip()
            for token in (of_match.team1, of_match.team2):
                espn_name = of_team_to_espn_name(token).lower()
                team = teams_by_name.get(espn_name)
                if team is None:
                    logger.warning("team_unmatched openfootball=%r espn_name=%r", token, espn_name)
                    continue
                if team.group_label != letter:
                    team.group_label = letter
                    groups_assigned += 1
                await _ensure_map(session, team.id, "team", "openfootball", token)

        for team in teams_by_name.values():
            await _ensure_map(session, team.id, "team", "espn", team.external_id)

        await session.commit()

    logger.info(
        "seed complete: fixtures=%s matched_to_openfootball=%s group_labels_set=%s teams=%s",
        fixtures_written,
        matched,
        groups_assigned,
        len(teams_by_name),
    )
    if unmatched:
        logger.warning("unmatched_espn_events count=%s: %s", len(unmatched), "; ".join(unmatched))


if __name__ == "__main__":
    asyncio.run(main())
