# FIFA World Cup Intelligence Dashboard

Live fixtures, self-computed standings, scorer leaderboards, team stats, and
AI match insights for the 2026 World Cup — built as a portfolio project that
demonstrates four competencies end to end:

| Competency | Where to look |
|---|---|
| **AI engineering** | [backend/app/ai/](backend/app/ai/) — multi-provider client ([providers.py](backend/app/ai/providers.py)), versioned prompt file ([prompts/match_insight_v1.txt](backend/app/ai/prompts/match_insight_v1.txt)), cached generation with budget breaker ([insights.py](backend/app/ai/insights.py), [budget.py](backend/app/ai/budget.py)) |
| **API integration** | [backend/app/ingestion/fetcher.py](backend/app/ingestion/fetcher.py) — ESPN + football-data.org + openfootball, timeouts/retries/rate-limit spacing, Pydantic validation at every boundary ([ingestion/schemas/](backend/app/ingestion/schemas/)) |
| **Data processing** | [backend/app/ingestion/](backend/app/ingestion/) — fetch → validate → normalize → upsert → aggregate → reconcile → enrich ([scheduler.py](backend/app/ingestion/scheduler.py)); two-source reconciliation in [reconciliation/checker.py](backend/app/reconciliation/checker.py) |
| **Dashboard development** | [frontend/](frontend/) — Next.js 15 App Router, Server Components, live polling, responsive |

## Architecture (ADR-002: cache-first)

```
ESPN ──┐
football-data ──┼──> ingestion job (APScheduler) ──> PostgreSQL ──> FastAPI GET ──> Next.js
openfootball ──┘          └──> LLM (insights, cached)
```

The frontend **never** calls a third-party API or the LLM. The ingestion job is
the only thing that does, on a 60 s cadence (30 s while a match is live).
Standings are never taken from a provider — they are recomputed from finished
fixtures and cross-checked against football-data.org (ADR-003). Finished scores
are verified across two sources; disagreements are flagged, logged, and served
with `verified: false` (api-research §6).

## Local setup

Prereqs: Python 3.11+, Node 20+, Docker Desktop.

```bash
# 1. Environment
cp .env.example .env          # set INGEST_SECRET; keys optional (see Keyless mode)

# 2. Database
docker compose up -d postgres

# 3. Backend (from repo root)
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt
cd backend && ../.venv/Scripts/alembic upgrade head && cd ..

# 4. Seed (openfootball + ESPN — no keys needed)
.venv/Scripts/python scripts/seed.py

# 5. Run backend  (port 8001 in this workspace; 8000 default elsewhere)
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --port 8001

# 6. Frontend
cd frontend && npm install && npm run dev
#    frontend/.env.local: NEXT_PUBLIC_USE_MOCKS=false, NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
```

Verify: `python scripts/check_keys.py` (validates both API keys + live response
shapes, loud on auth failure), `BASE_URL=http://localhost:8001 bash
scripts/smoke_test.sh`, and `python scripts/validate_data.py`. Tests:
`cd backend && pytest` (24 tests), `cd frontend && npm test`.

## Keyless mode (no FOOTBALL_DATA_API_KEY / AI_API_KEY)

The app runs fully on the two keyless sources, with documented degradations:

- **Scorers** fall back to a local derivation (goals from the ESPN timeline,
  appearances from lineups). Assists show 0 — football-data.org is the assists
  source. Adding the (free) key upgrades the leaderboard automatically.
- **Reconciliation** is skipped with a WARNING; finished fixtures stay
  `verified: false` (the UI treats this as a trust indicator, not an error).
- **AI insights** are skipped with a WARNING; the insight block simply doesn't
  render (it never blocks the page).

## AI provider selection

Set three env vars — nothing else changes (owner decision 2026-06-12):

```bash
AI_PROVIDER=groq                      # groq | gemini | openrouter | anthropic | openai
AI_MODEL=llama-3.3-70b-versatile
AI_API_KEY=...
```

Groq/OpenRouter speak the OpenAI dialect; Anthropic and Gemini have their own
wire formats — all implemented with plain httpx in
[providers.py](backend/app/ai/providers.py). Every call logs model, tokens,
latency, and cache hit/miss; `AI_DAILY_BUDGET_USD` is a hard daily circuit
breaker.

## Operational notes

- `POST /ingest` (header `X-Ingest-Secret`) triggers a manual run; the
  scheduler otherwise self-chains.
- `GET /health` reports DB status, per-table freshness (`stale_tables`), and
  the last successful ingestion run.
- ESPN deviation discovered in live verification (2026-06-12): finished
  matches report `status.type.id "28" / STATUS_FULL_TIME`, not the documented
  `"3" / STATUS_FINAL`. The normalizer maps on `status.type.state`
  (`pre|in|post`) first, with the documented ids as fallback.
- The 2026 openfootball file has **no team codes** — `team1/team2` are plain
  names and knockouts use tokens (`W101`, `1A`). The seed translates tokens to
  ESPN placeholder team names and matches fixtures by name-pair + kickoff
  window; ESPN is the id authority.

## Deploy

Frontend → Vercel (set `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_USE_MOCKS=false`).
Backend + Postgres → Railway/Render/Fly via [backend/Dockerfile](backend/Dockerfile);
run `alembic upgrade head` and `scripts/seed.py` once, set all `.env` values
(`ENVIRONMENT=production`, `CORS_ORIGINS=<vercel-domain>`). Pre-deploy:
checklist in CLAUDE.md §14.
