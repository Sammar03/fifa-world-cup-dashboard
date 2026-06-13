"""Unit tests for AI insight caching + output parsing (CLAUDE.md §13, §8.2)."""

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.ai import insights
from app.ai.providers import AIResult
from app.models import AIInsight, Fixture, Team


def _ai_result(text: str) -> AIResult:
    return AIResult(text=text, input_tokens=100, output_tokens=50, latency_ms=300, model="test-model")


async def _seed_finished_fixture(db) -> Fixture:
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
        home_score=2,
        away_score=0,
    )
    db.add(fixture)
    await db.commit()
    return fixture


async def test_ai_insight_cached_not_regenerated(db, monkeypatch):
    await _seed_finished_fixture(db)
    monkeypatch.setattr(insights.providers, "ai_available", lambda: True)

    calls = 0

    async def fake_completer(prompt: str) -> AIResult:
        nonlocal calls
        calls += 1
        return _ai_result('{"insight": "Mexico controlled the match and won 2-0 with ease."}')

    first = await insights.enrich(db, completer=fake_completer)
    await db.commit()
    second = await insights.enrich(db, completer=fake_completer)
    await db.commit()

    assert first == 1
    assert second == 0  # cached — not regenerated (CLAUDE.md §9: 0 ms on read)
    assert calls == 1
    count = (await db.execute(select(func.count()).select_from(AIInsight))).scalar_one()
    assert count == 1


async def test_enrich_skips_without_api_key(db, monkeypatch):
    await _seed_finished_fixture(db)
    monkeypatch.setattr(insights.providers, "ai_available", lambda: False)

    async def exploding_completer(prompt: str) -> AIResult:
        raise AssertionError("must not be called without a key")

    assert await insights.enrich(db, completer=exploding_completer) == 0


async def test_parse_failure_skips_caching(db, monkeypatch):
    await _seed_finished_fixture(db)
    monkeypatch.setattr(insights.providers, "ai_available", lambda: True)

    async def bad_completer(prompt: str) -> AIResult:
        return _ai_result("Sorry, I cannot produce JSON today.")

    generated = await insights.enrich(db, completer=bad_completer)
    assert generated == 0
    count = (await db.execute(select(func.count()).select_from(AIInsight))).scalar_one()
    assert count == 0


def test_parse_insight_accepts_fenced_json():
    fenced = '```json\n{"insight": "A tight game decided by one moment of quality."}\n```'
    assert insights.parse_insight(fenced).startswith("A tight game")


def test_parse_insight_rejects_garbage():
    assert insights.parse_insight("not json at all") is None
    assert insights.parse_insight('{"wrong_key": "x"}') is None
    assert insights.parse_insight('{"insight": ""}') is None  # min_length guard
