"""AI match insight generation + caching (CLAUDE.md §4.6, §8.2; step 7 of the
ingestion sequence).

Insights are generated ONLY here, in the ingestion job, and cached in
ai_insights keyed (fixture_id, state) — the request path reads the cache at
0 ms and never calls a provider. The prompt is a versioned file; the model must
return exactly {"insight": "..."} which is parsed with Pydantic. A parse
failure logs the raw response and skips caching — it never crashes the run.
"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import providers
from app.ai.budget import budget
from app.ai.providers import AIProviderError
from app.ingestion.aggregator import team_form
from app.models import AIInsight, Fixture, MatchStat, Standing, Team

logger = logging.getLogger(__name__)

PROMPT_VERSION = "match_insight_v1"
_PROMPT_PATH = Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.txt"
_prompt_template: str | None = None

# Max insights generated per ingestion run — keeps a single run fast and the
# first run (102 scheduled fixtures with no insight) from burning the budget.
GENERATION_CAP_PER_RUN = 8


class InsightPayload(BaseModel):
    insight: str = Field(min_length=10)


def _template() -> str:
    global _prompt_template
    if _prompt_template is None:
        _prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    return _prompt_template


def parse_insight(raw: str) -> str | None:
    """Strict parse of the model output. Tolerates markdown fences, nothing else."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return InsightPayload.model_validate(json.loads(text)).insight
    except (json.JSONDecodeError, ValidationError):
        logger.warning("ai_insight_parse_failed raw=%r", raw[:500])
        return None


async def _team_context(session: AsyncSession, team: Team | None) -> dict:
    if team is None:
        return {"name": "TBD"}
    standing = (
        await session.execute(select(Standing).where(Standing.team_id == team.id))
    ).scalar_one_or_none()
    return {
        "name": team.name,
        "group": team.group_label,
        "form_last5_oldest_to_newest": await team_form(session, team.id),
        "goals_for": standing.goals_for if standing else 0,
        "goals_against": standing.goals_against if standing else 0,
    }


async def _decisive_stat(session: AsyncSession, fixture: Fixture) -> str | None:
    """The single most significant stat difference between the two teams."""
    stats = (
        (await session.execute(select(MatchStat).where(MatchStat.fixture_id == fixture.id)))
        .scalars()
        .all()
    )
    by_team = {stat.team_id: stat for stat in stats}
    home, away = by_team.get(fixture.home_team_id), by_team.get(fixture.away_team_id)
    if home is None or away is None:
        return None

    best: tuple[float, str] | None = None
    for label, attr in (
        ("possession", "possession"),
        ("total shots", "shots"),
        ("shots on target", "shots_on_target"),
        ("corners", "corners"),
    ):
        home_value, away_value = getattr(home, attr), getattr(away, attr)
        if home_value is None or away_value is None:
            continue
        home_value, away_value = float(home_value), float(away_value)
        spread = abs(home_value - away_value) / max(home_value + away_value, 1.0)
        if best is None or spread > best[0]:
            best = (spread, f"{label}: home {home_value:g} vs away {away_value:g}")
    return best[1] if best else None


async def build_context(session: AsyncSession, fixture: Fixture, state: str) -> dict:
    home = await session.get(Team, fixture.home_team_id) if fixture.home_team_id else None
    away = await session.get(Team, fixture.away_team_id) if fixture.away_team_id else None
    context = {
        "match_type": "post_match" if state == "finished" else "pre_match",
        "home_team": await _team_context(session, home),
        "away_team": await _team_context(session, away),
    }
    if state == "finished":
        context["score"] = {"home": fixture.home_score, "away": fixture.away_score}
        decisive = await _decisive_stat(session, fixture)
        context["decisive_stat"] = decisive or "winning margin"
    return context


async def enrich(session: AsyncSession, completer=providers.complete) -> int:
    """Generate + cache insights for fixtures missing one for their current
    state. Returns the number generated. `completer` is injectable for tests."""
    if not providers.ai_available():
        logger.warning("ai_enrichment_skipped reason=no_api_key")
        return 0

    candidates = await _fixtures_missing_insight(session)
    generated = 0
    for fixture in candidates[:GENERATION_CAP_PER_RUN]:
        if not budget.allow():
            break
        state = fixture.status  # "scheduled" | "finished"
        context = await build_context(session, fixture, state)
        prompt = _template().format(context=json.dumps(context, ensure_ascii=False))
        try:
            result = await completer(prompt)
        except AIProviderError as exc:
            logger.warning("ai_call_failed fixture=%s state=%s error=%s", fixture.id, state, exc)
            continue
        budget.record(result.input_tokens, result.output_tokens)
        logger.info(
            "ai_call model=%s input_tokens=%s output_tokens=%s latency_ms=%s cache=miss "
            "fixture=%s state=%s daily_spend_usd=%.4f",
            result.model,
            result.input_tokens,
            result.output_tokens,
            result.latency_ms,
            fixture.id,
            state,
            budget.spent_usd,
        )
        insight = parse_insight(result.text)
        if insight is None:
            continue
        session.add(
            AIInsight(
                fixture_id=fixture.id,
                state=state,
                content=insight,
                model=result.model,
                prompt_version=PROMPT_VERSION,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
        )
        await session.flush()
        generated += 1
    return generated


async def _fixtures_missing_insight(session: AsyncSession) -> list[Fixture]:
    """Finished fixtures first (most recent kickoff first), then upcoming
    scheduled ones (soonest first). The cached-insight check IS the cache:
    a fixture+state with a row is never regenerated."""

    def _missing(status: str):
        return (
            select(Fixture)
            .where(
                Fixture.status == status,
                ~exists().where(
                    (AIInsight.fixture_id == Fixture.id) & (AIInsight.state == status)
                ),
            )
        )

    finished = (
        (await session.execute(_missing("finished").order_by(Fixture.kickoff_at.desc())))
        .scalars()
        .all()
    )
    scheduled = (
        (await session.execute(_missing("scheduled").order_by(Fixture.kickoff_at.asc())))
        .scalars()
        .all()
    )
    return [*finished, *scheduled]
