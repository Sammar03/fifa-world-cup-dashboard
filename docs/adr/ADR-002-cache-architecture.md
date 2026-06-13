# ADR-002: Cache-first architecture — the frontend never calls a third party

**Status:** Accepted
**Date:** 2026-06-12
**References:** `CLAUDE.md` §5.1, §9; `docs/prd.md` §11; `master-project-prompt.md` §6.2

---

## Context

The product must load in under 1.5 s, stay within free-tier rate limits, control
LLM cost, and remain stable during a live demo. The data sources (ESPN,
football-data.org) and the LLM are slow and/or rate-limited, and a per-user call
to any of them would make the app slow, fragile, and expensive — and would blow
the rate limits the moment more than a handful of people open it.

## Decision

Adopt a strict cache-first (ingest → store → serve) architecture:

```
External API / LLM  →  Scheduled ingestion job  →  PostgreSQL  →  FastAPI GETs  →  Frontend
```

- **The frontend never calls the football API. The frontend never calls the LLM.
  Ever.** It talks only to the FastAPI backend.
- FastAPI **GET** endpoints read **only** from PostgreSQL. No GET endpoint makes
  a live third-party call.
- All third-party calls happen in the scheduled ingestion job.
- AI match insights are generated **in the ingestion job** and cached in the
  `ai_insights` table, keyed by `(fixture_id, state)`. They are served from
  cache at 0 ms; a missing insight is simply not rendered, never a spinner on the
  request path.

Any server action or API route that calls a third party on the request path is
an architecture violation and must be removed.

## Consequences

**Positive**
- Fast: GET endpoints are DB reads (< 200 ms p95 target; hot paths < 10 ms).
- Rate-limit-safe: external call volume is bounded by the ingestion cadence
  (6–11 calls/run), independent of user traffic.
- Cost-controlled: one LLM call per match per state change, not per page view;
  plus a daily-budget circuit breaker.
- Demo-stable: if a source is down, the last cached data still serves.

**Negative / mitigations**
- Data is only as fresh as the last ingestion run. Mitigated by a 30–60 s
  cadence (30 s during live windows), a `last_updated_at` on every written
  table, freshness checks on `/health`, and a "data may be delayed" banner in
  the UI when `/health` reports `degraded` (api-research §6.5).
- A first page load before the first ingestion run shows seeded/empty states.
  Mitigated by seeding fixtures/teams from openfootball before go-live.
