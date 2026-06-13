# ADR-001: ESPN as primary live source, football-data.org as cross-check, openfootball as seed

**Status:** Accepted
**Date:** 2026-06-12
**References:** `docs/api-research.md` §1–§9, `CLAUDE.md` §5.4, §10

---

## Context

The dashboard needs free, reasonably real-time FIFA World Cup 2026 data within a
1-day build budget, with no per-user third-party calls. The requirement is
explicit: *"If the data is not correct, there is no point of the dashboard."* No
single free provider covers live scores, detailed match stats, lineups,
standings, and a scorer leaderboard at once — and none should be trusted alone.

Candidates considered: API-Football (rich but the free tier is restrictive and
rate-limited), football-data.org (stable, official, free-forever core, but
delayed scores and no detailed stats on the free tier), ESPN's unofficial public
JSON API (fast, complete, no key — but undocumented and no SLA), and
openfootball (public-domain fixture/team data, hand-updated, not real-time).

## Decision

Use three sources with distinct, non-overlapping roles:

| Role | Source | Auth | Provides |
|---|---|---|---|
| **Primary live feed** | ESPN public JSON API (`fifa.world`) | none | live scores, match stats, lineups, goal timeline, venue, flags |
| **Secondary / cross-check** | football-data.org v4 (`WC`) | free API key | standings cross-check, scorer leaderboard + assists, finished-result verification |
| **Canonical seed** | openfootball/worldcup.json (2026) | none | groups, 48 teams, venues, the 104-fixture schedule backbone |

Scorers and assists come **only** from football-data.org (ESPN does not expose
them). Detailed stats (possession, shots, corners, cards) come **only** from
ESPN (football-data.org free tier does not provide them). The ingestion job
calls all three; the frontend calls none of them.

## Consequences

**Positive**
- Free, fast, no key for the primary live feed; the 1-day target is realistic.
- Two independent sources enable score reconciliation (see ADR-003 and
  api-research §6) — the visible "data correctness" story.
- Each source plays to its strength; gaps in one are covered by another.

**Negative / risks**
- ESPN is unofficial, undocumented, and can change without notice (it has moved
  base URLs before). Mitigation: validate every response with Pydantic, guard
  every field access with `.get()`/`Optional`, and keep football-data.org as a
  score-verification fallback (api-research §2, §9).
- football-data.org free tier is 10 req/min and score-delayed. Mitigation: at
  most 3 calls per run, spaced ~7s; used for verification, not live scores.
- Three different ID spaces. Mitigation: an `external_id_map` table reconciles
  teams (by 3-letter code) and fixtures (by team codes + date window),
  api-research §5.

**Failover** is defined in api-research §9 and must be followed exactly — do not
improvise if a source breaks mid-tournament.
