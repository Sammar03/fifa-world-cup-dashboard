"""Run the data-correctness checks manually (CLAUDE.md §3, api-research §6).

Prints DB invariants, runs the football-data.org reconciliation if a key is
configured, and reports verified/unverified fixture counts.

Usage (repo root):  python scripts/validate_data.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.ingestion.fetcher import fetch_fd_finished_matches  # noqa: E402
from app.models import Fixture, Goal, Standing, Team  # noqa: E402
from app.reconciliation.checker import reconcile  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("validate")


async def main() -> None:
    async with SessionLocal() as session:
        teams = (await session.execute(select(func.count()).select_from(Team))).scalar_one()
        fixtures = (await session.execute(select(func.count()).select_from(Fixture))).scalar_one()
        finished = (
            await session.execute(
                select(func.count()).select_from(Fixture).where(Fixture.status == "finished")
            )
        ).scalar_one()
        print(f"teams={teams} fixtures={fixtures} finished={finished}")

        # Invariant: goal rows per finished fixture should equal the scoreline sum.
        mismatches = 0
        finished_rows = (
            (await session.execute(select(Fixture).where(Fixture.status == "finished")))
            .scalars()
            .all()
        )
        for fixture in finished_rows:
            goal_count = (
                await session.execute(
                    select(func.count()).select_from(Goal).where(Goal.fixture_id == fixture.id)
                )
            ).scalar_one()
            expected = (fixture.home_score or 0) + (fixture.away_score or 0)
            if goal_count != expected:
                mismatches += 1
                print(
                    f"  WARN goal-count mismatch fixture={fixture.id} "
                    f"score_sum={expected} goal_rows={goal_count}"
                )
        print(f"goal-count check: {len(finished_rows) - mismatches}/{len(finished_rows)} consistent")

        # Invariant: every group has exactly 4 standings rows once aggregated.
        group_counts = (
            await session.execute(
                select(Standing.group_label, func.count()).group_by(Standing.group_label)
            )
        ).all()
        bad_groups = [group for group, count in group_counts if count != 4]
        print(f"standings groups: {len(group_counts)} (expected 12), uneven: {bad_groups or 'none'}")

        # Cross-source reconciliation (skips with a warning when keyless)
        fd_matches = await fetch_fd_finished_matches()
        flags = await reconcile(session, fd_matches)
        await session.commit()

        verified = (
            await session.execute(
                select(func.count()).select_from(Fixture).where(Fixture.verified.is_(True))
            )
        ).scalar_one()
        print(
            f"reconciliation: verified={verified}/{finished} finished fixtures, "
            f"flags_this_run={flags}, source={'football-data' if fd_matches else 'UNAVAILABLE (no key)'}"
        )


if __name__ == "__main__":
    asyncio.run(main())
