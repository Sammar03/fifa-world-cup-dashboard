"""Unit tests for two-source reconciliation (CLAUDE.md §13, api-research §6)."""

from datetime import UTC, datetime

from app.ingestion.schemas.football_data import FDMatchesResponse
from app.models import Fixture, Team
from app.reconciliation.checker import reconcile


async def _seed(db, home_score=2, away_score=0) -> Fixture:
    home = Team(external_id="t1", name="Mexico", code="MEX", group_label="A")
    away = Team(external_id="t2", name="South Africa", code="RSA", group_label="A")
    db.add_all([home, away])
    await db.flush()
    fixture = Fixture(
        external_id="e1",
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_at=datetime(2026, 6, 11, 19, 0, tzinfo=UTC),
        status="finished",
        home_score=home_score,
        away_score=away_score,
    )
    db.add(fixture)
    await db.commit()
    return fixture


def _fd_payload(home=2, away=0) -> FDMatchesResponse:
    return FDMatchesResponse.model_validate(
        {
            "matches": [
                {
                    "id": 555,
                    "utcDate": "2026-06-11T19:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 10, "name": "Mexico", "tla": "MEX"},
                    "awayTeam": {"id": 20, "name": "South Africa", "tla": "RSA"},
                    "score": {"fullTime": {"home": home, "away": away}},
                }
            ]
        }
    )


async def test_reconciliation_marks_agreement_verified(db):
    fixture = await _seed(db)
    flags = await reconcile(db, _fd_payload(home=2, away=0))
    await db.commit()
    await db.refresh(fixture)
    assert flags == 0
    assert fixture.verified is True
    assert fixture.verified_at is not None
    assert fixture.mismatch_count == 0


async def test_reconciliation_flags_mismatch(db):
    fixture = await _seed(db)
    flags = await reconcile(db, _fd_payload(home=1, away=1))  # disagrees with ESPN 2-0
    await db.commit()
    await db.refresh(fixture)
    assert flags == 1
    assert fixture.verified is False  # ESPN still served, but flagged
    assert fixture.mismatch_count == 1


async def test_reconciliation_missing_source_stays_unverified(db):
    fixture = await _seed(db)
    flags = await reconcile(db, FDMatchesResponse.model_validate({"matches": []}))
    await db.commit()
    await db.refresh(fixture)
    assert flags == 0
    assert fixture.verified is False


async def test_reconciliation_skips_when_fd_unavailable(db):
    fixture = await _seed(db)
    flags = await reconcile(db, None)  # keyless mode
    await db.commit()
    await db.refresh(fixture)
    assert flags == 0
    assert fixture.verified is False
