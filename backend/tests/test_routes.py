"""Integration tests for the API routes (CLAUDE.md §13)."""

from datetime import UTC, datetime

from app.models import Fixture, Team


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in ("ok", "degraded")
    assert payload["db"] == "ok"
    assert payload["version"]


async def test_fixtures_endpoint(client, db):
    home = Team(external_id="espn-100", name="Brazil", code="BRA", group_label="C")
    away = Team(external_id="espn-200", name="Germany", code="GER", group_label="C")
    db.add_all([home, away])
    await db.flush()
    db.add(
        Fixture(
            external_id="evt-1",
            home_team_id=home.id,
            away_team_id=away.id,
            kickoff_at=datetime(2026, 6, 15, 18, 0, tzinfo=UTC),
            venue="MetLife Stadium",
            status="scheduled",
            group_label="C",
            round="Group stage",
        )
    )
    await db.commit()

    response = await client.get("/fixtures")
    assert response.status_code == 200
    payload = response.json()
    assert "generated_at" in payload
    assert len(payload["fixtures"]) == 1
    fixture = payload["fixtures"][0]
    # Contract fields the frontend types/index.ts depends on
    assert fixture["home_team"]["code"] == "BRA"
    assert fixture["away_team"]["name"] == "Germany"
    assert fixture["status"] == "scheduled"
    assert fixture["home_score"] is None
    assert fixture["verified"] is False
    assert fixture["minute"] is None

    # date filter: matching day vs another day
    on_day = await client.get("/fixtures?date=2026-06-15")
    assert len(on_day.json()["fixtures"]) == 1
    off_day = await client.get("/fixtures?date=2026-06-16")
    assert off_day.json()["fixtures"] == []


async def test_fixture_detail_404(client):
    response = await client.get("/fixtures/99999")
    assert response.status_code == 404


async def test_query_returns_501_stub(client):
    response = await client.post("/query", json={"question": "Who is the top scorer?"})
    assert response.status_code == 501  # BACKLOG-001


async def test_ingest_requires_secret(client):
    response = await client.post("/ingest")
    assert response.status_code == 401
    response = await client.post("/ingest", headers={"X-Ingest-Secret": "wrong"})
    assert response.status_code == 401
