# API Research & Data Correctness Strategy
## FIFA World Cup Intelligence Dashboard

**Status:** Approved — use these sources exactly as documented  
**Last updated:** 2026-06-12  
**Referenced by:** `CLAUDE.md §5.4`, `CLAUDE.md §10`, `docs/adr/ADR-001-api-sources.md`

> **The decision is final for MVP.** Do not introduce new data sources, swap providers, or change integration patterns without updating this document and creating a new ADR. If a source goes down or breaks, follow the failover procedure in §6 — do not improvise.

---

## 1. Decision Summary

Three sources are used. They have distinct, non-overlapping roles. No single source is trusted alone.

| Role | Source | Auth | Cost | Primary use |
|---|---|---|---|---|
| **Primary live feed** | ESPN public JSON API | None (no key) | Free | Live scores, match stats, lineups, goal timeline |
| **Secondary / cross-check** | football-data.org v4 | API key (free tier) | Free forever | Standings cross-check, scorer leaderboard, finished result verification |
| **Canonical fixture seed** | openfootball/worldcup.json | None (public domain) | Free | Group structure, team list, venues, fixture schedule backbone |

The frontend calls **none** of these. The ingestion job calls all three, writes to PostgreSQL, and that database is the only thing the frontend ever reads.

---

## 2. Source 1 — ESPN Public JSON API (Primary)

### Background
ESPN operates an unofficial, undocumented public JSON API that powers ESPN.com. It has no formal developer programme, no API key requirement, and no published SLA. It is used by thousands of developers because it is the fastest, most complete free sports data feed available. It covers FIFA World Cup 2026 under the slug `fifa.world`.

**This is an unofficial API. It can change without notice.** The integration must be defensive: parse with Pydantic, never assume field presence, and have football-data.org ready as a score-verification fallback if ESPN breaks mid-tournament.

### Base URLs

```
# Fixtures / scoreboard (live + scheduled + finished)
https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard

# Standings (note: different base path — v2 not site/v2)
https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings

# Match summary (stats, lineups, goal timeline)
https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={espn_event_id}

# Team info
https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams/{espn_team_id}
```

### Authentication
None. Plain GET requests. No headers required beyond a standard `User-Agent`.

```python
headers = {
    "User-Agent": "WorldCupDashboard/1.0 (portfolio project)"
}
```

### Rate limits
Not published. Community norm: treat as 100 requests/minute. The ingestion job must never exceed this. Do not call ESPN on the user request path — ever.

### Key response fields (scoreboard endpoint)

```json
{
  "events": [
    {
      "id": "string",                        // ESPN event ID — store as external_id
      "date": "ISO8601",                     // kickoff UTC
      "name": "string",                      // "Brazil vs Argentina"
      "status": {
        "type": {
          "id": "1|2|3",                     // 1=scheduled, 2=in_play, 3=finished
          "name": "STATUS_SCHEDULED|STATUS_IN_PROGRESS|STATUS_FINAL",
          "completed": true|false
        },
        "displayClock": "45'",               // live only
        "period": 1|2                        // live only
      },
      "competitions": [
        {
          "venue": { "fullName": "string", "address": { "city": "string" } },
          "competitors": [
            {
              "id": "string",                // ESPN team ID
              "team": { "displayName": "string", "abbreviation": "string", "logo": "url" },
              "score": "string",             // "2" — parse to int, default 0
              "homeAway": "home|away",
              "statistics": [...]            // present for finished/live matches
            }
          ],
          "details": [...]                   // goal events: minute, team, player, type
        }
      ]
    }
  ]
}
```

### Status mapping (normalizer must use this table — no guessing)

| ESPN `status.type.id` | ESPN `status.type.name` | Internal `status` value |
|---|---|---|
| `"1"` | `STATUS_SCHEDULED` | `scheduled` |
| `"2"` | `STATUS_IN_PROGRESS` | `live` |
| `"3"` | `STATUS_FINAL` | `finished` |

If `status.type.id` is not one of these three values, log at WARNING and default to `scheduled`. Never crash on an unknown status.

### Match summary endpoint — what it returns

Call `GET /summary?event={id}` for any fixture to retrieve:
- `boxscore.players` → lineups (if available; not always present for scheduled matches)
- `boxscore.teams[].statistics` → possession, shots, shots on target, corners, fouls, yellow cards, red cards
- `plays` → goal timeline (minute, scorer, team, type: `goal|own_goal|penalty`)
- `header.competitions[0].venue` → venue name

All of these fields may be absent for scheduled matches. Every field access must be guarded with `.get()` or a Pydantic `Optional` field — never a direct dict key.

### Known gotchas
- `score` is a **string**, not an integer. Parse with `int(score) if score else 0`.
- `statistics` is a list of `{ name, displayValue, ... }` dicts. Look up by `name`, never by index.
- The standings endpoint path is `apis/v2/...` not `apis/site/v2/...` — these are different. A 200 from the wrong path returns `{}`.
- ESPN has moved base URLs before (fantasy API moved in 2024). If calls start returning 404, check the URL before assuming the data is gone.
- Lineups are not available for all matches. The `players` key may be absent entirely.

### Ingestion schedule
- During live windows (a match has `status = live`): poll every `LIVE_POLL_INTERVAL_SECONDS` (default 30s)
- Otherwise: poll every `INGEST_INTERVAL_SECONDS` (default 60s)
- The scheduler checks for live matches first before deciding the interval

---

## 3. Source 2 — football-data.org v4 (Secondary / Cross-check)

### Background
football-data.org is a stable, officially maintained free football data API run by Daniel Freitag. It has been operating since 2013. The founder has publicly committed to keeping the core free tier free forever. FIFA World Cup is explicitly included in the free tier under competition code `WC`.

This is the accuracy anchor. It does not provide real-time scores, but its finished-match data and standings are authoritative and strongly typed. It is used to cross-check ESPN scores and to provide an independent standings feed.

### Registration
Register at https://www.football-data.org/client/register. The API key is sent by email immediately. It goes in `FOOTBALL_DATA_API_KEY`.

### Base URL

```
https://api.football-data.org/v4
```

### Authentication

```python
headers = {
    "X-Auth-Token": settings.FOOTBALL_DATA_API_KEY
}
```

### Free tier limits
- **10 requests per minute** (hard limit; 429 if exceeded)
- All endpoints available on free tier for the 12 included competitions (WC is included)
- Scores are **delayed** on the free tier — not real-time. This is fine: we use ESPN for live, and football-data.org for post-match verification.
- Lineups, cards, and detailed match stats are **not** available on the free tier (paid add-on)

### Key endpoints used in this project

```
GET /competitions/WC/matches
    ?status=FINISHED                     # only finished matches
    Returns: matches[].homeTeam.id, awayTeam.id, score.fullTime.home/away

GET /competitions/WC/standings
    Returns: standings[].table[].team.id, points, won, draw, lost,
             goalsFor, goalsAgainst, goalDifference

GET /competitions/WC/scorers
    ?limit=50
    Returns: scorers[].player.name, team.name, goals, assists, playedMatches
```

### Response shape (matches endpoint, finished)

```json
{
  "matches": [
    {
      "id": 12345,                        // football-data match ID — for cross-ref only
      "utcDate": "ISO8601",
      "status": "FINISHED",               // SCHEDULED | TIMED | IN_PLAY | PAUSED | FINISHED
      "homeTeam": { "id": 123, "name": "Brazil", "shortName": "Brazil", "tla": "BRA" },
      "awayTeam": { "id": 456, "name": "Argentina", "shortName": "Argentina", "tla": "ARG" },
      "score": {
        "fullTime": { "home": 2, "away": 1 },   // integers — not strings
        "halfTime": { "home": 1, "away": 0 }
      }
    }
  ]
}
```

Note: football-data.org uses integer scores (not strings like ESPN). Both must be normalised to the same internal type (`int | None`).

### Rate limit handling in the ingestion job
football-data.org allows 10 req/min. The job makes at most 3 calls per run (matches, standings, scorers). Space them with a 7-second sleep between calls:

```python
# In fetcher.py — football-data.org calls
await asyncio.sleep(7)   # never exceed 10 req/min
```

### Known gotchas
- The `status` field uses different values than ESPN (`FINISHED` vs `STATUS_FINAL`). Never compare status strings cross-source — use the normalised internal value.
- `score.fullTime` can be `null` for unplayed matches. Always guard: `score.get("fullTime") or {}`.
- The scorer endpoint returns `playedMatches` (not `matchesPlayed`). Map to internal `matches_played`.
- Team IDs from football-data.org are different from ESPN team IDs. The `id_mapping` table reconciles them — see §5.

---

## 4. Source 3 — openfootball/worldcup.json (Canonical Seed)

### Background
Public-domain JSON published on GitHub by Gerald Bauer. Contains the complete 2026 World Cup fixture list, 48 teams, 12 groups, and 16 stadiums. Updated ~daily by hand. Used only for seeding the database before ingestion begins — not for live updates.

### URL

```
https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json
```

No authentication. Standard GET.

### What it provides
- All 104 fixtures: home team, away team, kickoff time, venue, group/round
- 48 teams: name, code (3-letter), group assignment
- 12 group labels: A through L
- 16 venues: name, city, country

### What it does NOT provide
- Live scores (hand-updated ~daily, not real-time)
- Player data
- Match statistics

### Usage in this project
Run `scripts/seed.py` once before the first ingestion run to populate:
- `teams` table (all 48 teams with code and group)
- `fixtures` table (all 104 fixtures with kickoff time, venue, group, round)

After seeding, the ingestion job updates these records in place via `external_id`. The seed establishes the canonical fixture IDs that the ID mapping table (§5) uses to tie ESPN and football-data.org records together.

### Known gotchas
- Kickoff times in the JSON may be in local city time, not UTC. Convert to UTC on ingest. Verify against ESPN kickoff times after seeding.
- The JSON schema is not versioned. If it changes between runs, the seed script will fail loudly (Pydantic validation) — which is the correct behaviour.

---

## 5. Cross-Source ID Mapping

ESPN, football-data.org, and openfootball all use different team and match IDs. The reconciliation checker needs a mapping to join records across sources. This mapping is stored in the `external_id_map` table (created in the Alembic migration):

```sql
external_id_map (
  id              SERIAL PRIMARY KEY,
  internal_id     INTEGER NOT NULL,           -- our internal teams.id or fixtures.id
  entity_type     TEXT NOT NULL,              -- 'team' | 'fixture'
  source          TEXT NOT NULL,              -- 'espn' | 'football_data' | 'openfootball'
  external_id     TEXT NOT NULL,
  UNIQUE (entity_type, source, external_id)
)
```

### Building the mapping

The ID map is built during the first ingestion run:

1. **Teams:** match by `code` (3-letter abbreviation). ESPN uses `team.abbreviation`; football-data.org uses `team.tla`; openfootball uses `code`. All three should match (e.g. `"BRA"`, `"ENG"`). If a code doesn't match, log a WARNING and skip — do not guess.

2. **Fixtures:** match by `(home_team_code, away_team_code, date)`. The date must match within a 24-hour window to account for timezone differences in the raw data.

### Fallback if mapping fails
If a fixture cannot be mapped across sources (e.g. ESPN has it, football-data.org does not yet), mark `verified = false` and serve ESPN data only. Do not block the ingestion run.

---

## 6. Data Correctness Strategy

> **"If the data is not correct, there is no point of the dashboard."**
> This strategy is the implementation of that requirement.

### 6.1 The reconciliation pipeline (step 6 of the ingestion sequence)

After upsert (step 4), for every fixture with `status = finished`:

```python
# reconciliation/checker.py — pseudocode

for fixture in finished_fixtures:
    espn_score = get_score_from_espn_raw(fixture.external_id)
    fd_score   = get_score_from_fd_raw(fixture.external_id)

    if espn_score is None or fd_score is None:
        # One source hasn't reported yet — mark unverified, continue
        mark_unverified(fixture.id, reason="missing_source")
        continue

    if espn_score == fd_score:
        mark_verified(fixture.id)
    else:
        mark_unverified(fixture.id, reason="score_mismatch")
        log.warning(
            "score_mismatch",
            fixture_id=fixture.id,
            espn=espn_score,
            football_data=fd_score,
        )
        # Serve ESPN (primary) but flag the discrepancy
```

### 6.2 The `verified` column

Add `verified BOOLEAN DEFAULT FALSE` and `verified_at TIMESTAMPTZ` to the `fixtures` table (in the initial migration — not as a hotfix later).

The UI rule: if `verified = false`, the score or result is shown with a small `⚠ unverified` indicator. The data is still shown — it is not hidden. The indicator is a trust signal, not an error state.

### 6.3 Standings self-computation

**Never serve standings from a provider directly.** Always recompute from raw fixture data:

```python
# aggregator.py — standings recomputation

for each finished fixture:
    award points to home/away team based on score:
        home win  → home +3
        draw      → both +1
        away win  → away +3
    increment played, won, drawn, lost, goals_for, goals_against

sort each group by:
    1. points DESC
    2. goal_diff DESC
    3. goals_for DESC
    4. team name ASC  ← official FIFA 2026 tiebreaker (alphabetical)
```

After computing, diff the result against football-data.org standings endpoint. If a team's points differ by more than 0, log a CRITICAL warning — it indicates a bug in the aggregator or a data error in the source.

### 6.4 Pydantic validation at every boundary

Every ESPN response and every football-data.org response passes through a Pydantic model before any field is accessed. The models live in `backend/app/ingestion/schemas/` (separate from the API response schemas in `backend/app/schemas/`).

Required fields are `required` in the model. Optional fields use `Optional[T] = None`. If Pydantic raises a `ValidationError`, the record is:
1. Logged at WARNING with the raw payload
2. Skipped for this run
3. NOT written to the database

This is the boundary validation described in `master-project-prompt.md §8.1`.

### 6.5 Freshness monitoring

Every table that is written by the ingestion job has a `last_updated_at` column. The `/health` endpoint checks:

```python
# If any of these are stale, health returns degraded status
FRESHNESS_THRESHOLDS = {
    "fixtures":    timedelta(minutes=5),   # during live window
    "standings":   timedelta(minutes=10),
    "scorer_stats": timedelta(minutes=10),
}
```

If `now() - last_updated_at > threshold`, the health endpoint returns:
```json
{ "status": "degraded", "db": "ok", "stale_tables": ["fixtures"] }
```

The frontend polls `/health` every 60s and shows a "data may be delayed" banner if status is `degraded`.

### 6.6 Human ground-truth spot-checks

During active tournament days, manually verify at least 3 finished match scores per day against:
- ESPN.com match page (the human-readable one, not the API)
- FIFA.com official results page

Log the verification in `docs/spot-checks.md`:
```
2026-06-14: Verified BRA 2-0 ARG, ESP 1-1 GER, FRA 3-1 POL against ESPN.com + FIFA.com ✓
```

This takes 2 minutes and is the final line of defence against a systematic data error.

---

## 7. What Each Source Covers (Capability Matrix)

| Data point | ESPN | football-data.org (free) | openfootball |
|---|---|---|---|
| Fixture schedule (all 104) | ✅ | ✅ | ✅ seed only |
| Live scores | ✅ real-time | ❌ delayed | ❌ |
| Final scores | ✅ | ✅ | ✅ hand-updated |
| Match status | ✅ | ✅ | ❌ |
| Venue | ✅ | ❌ | ✅ seed only |
| Goal timeline | ✅ | ❌ free | ❌ |
| Lineups | ✅ (when available) | ❌ free | ❌ |
| Possession / shots / corners | ✅ | ❌ free | ❌ |
| Yellow / red cards | ✅ | ❌ free | ❌ |
| Group standings | ✅ | ✅ | ❌ |
| Top scorers | ❌ | ✅ | ❌ |
| Assists | ✅ (keyEvents prose) | ⚠️ sparse/null free tier | ❌ |
| Team flags / logos | ✅ | ❌ | ❌ |
| Player names | ✅ (in lineups) | ✅ (in scorers) | ❌ |

**Gaps and how they are handled:**
- **Assists:** football-data.org's free-tier `/scorers` returns `assists: null` for most goals (delayed / not entered), so it is NOT a reliable assist source. ESPN does expose assists — not in structured fields, but in the goal `keyEvents` text ("…Assisted by <Name>"). The pipeline parses that text (normalizer `parse_assister`), stores it on `goals.assist_player_name`, and the aggregator derives every player's assists from it (verified live 2026-06-13). football-data remains the source for the scorer LIST and matches_played.
- **Top scorers from ESPN:** not available. Use football-data.org as the sole scorer source.
- **Lineups:** ESPN only, and not guaranteed. If absent, hide the lineup section — do not error.
- **Detailed stats (possession etc.) from football-data.org:** not available on free tier. ESPN is the sole source. If ESPN is down, these stats show `—` rather than crashing.

---

## 8. Ingestion Call Budget Per Run

The ingestion job makes the following external calls per run. This is the maximum — do not add calls without updating this table.

| Source | Endpoint | Calls per run | Notes |
|---|---|---|---|
| ESPN | `/scoreboard` | 1 | All fixtures in one call |
| ESPN | `/summary?event={id}` | 0–5 | Only for live or recently-finished matches |
| ESPN | `/standings` | 1 | Once per run |
| football-data.org | `/competitions/WC/matches?status=FINISHED` | 1 | Cross-check only |
| football-data.org | `/competitions/WC/standings` | 1 | Cross-check only |
| football-data.org | `/competitions/WC/scorers` | 1 | Primary scorer source |
| openfootball | Raw JSON | 0 | Seed only — not called on every run |

**Total calls per run: 6–11**. Well within ESPN's informal limit and football-data.org's 10 req/min (6 calls with 7s spacing = ~42 seconds, safely under the limit).

---

## 9. Failover Procedures

### If ESPN returns 4xx or 5xx for 3 consecutive runs
1. Log CRITICAL: `espn_api_unavailable, consecutive_failures=3`
2. Continue serving the last cached data from PostgreSQL
3. Suspend ESPN calls for 5 minutes, then retry
4. If down for >30 minutes: surface the "data may be delayed" banner in the UI

### If football-data.org returns 429 (rate limit)
1. Back off for 60 seconds
2. Retry once
3. If still 429: skip the cross-check for this run, log WARNING, continue
4. Do not block the ingestion run on a cross-check failure

### If both sources are down simultaneously
1. Log CRITICAL: `all_sources_unavailable`
2. Serve last cached data
3. Show "data may be delayed" banner
4. Do not attempt to show "live" status on any fixture

### If a score mismatch persists for >3 runs
1. The fixture remains `verified = false`
2. Send a structured CRITICAL log: `persistent_score_mismatch, fixture_id=X, espn=A, football_data=B`
3. Manually check FIFA.com and update the correct score via `scripts/manual_correction.py` if needed

---

## 10. Environment Variables (this file's scope)

These are the variables directly related to API sources. The full list is in `.env.example`.

```bash
# ESPN (no key required — these are just URL configuration)
ESPN_API_BASE_URL=https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world
ESPN_STANDINGS_URL=https://site.api.espn.com/apis/v2/sports/soccer/fifa.world
ESPN_TIMEOUT_SECONDS=10
ESPN_MAX_RETRIES=2

# football-data.org
FOOTBALL_DATA_API_KEY=your_key_here        # register free at football-data.org
FOOTBALL_DATA_BASE_URL=https://api.football-data.org/v4
FOOTBALL_DATA_TIMEOUT_SECONDS=10
FOOTBALL_DATA_MAX_RETRIES=1               # lower than ESPN — we can tolerate a miss

# Reconciliation
RECONCILIATION_SCORE_MISMATCH_ALERT_AFTER=3   # runs before CRITICAL log
FRESHNESS_THRESHOLD_MINUTES=5                  # for live windows
```

---

## 11. ADR Reference

The following Architecture Decision Records document the non-obvious choices made here:

| ADR | Decision | Location |
|---|---|---|
| ADR-001 | ESPN as primary, not API-Football | `docs/adr/ADR-001-api-sources.md` |
| ADR-002 | Cache-first architecture | `docs/adr/ADR-002-cache-architecture.md` |
| ADR-003 | Self-computed standings, not provider standings | `docs/adr/ADR-003-standings-computation.md` |
| ADR-004 | Constrained NL query (no raw SQL generation) | `docs/adr/ADR-004-nl-query-design.md` |

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-06-12 | Initial version — ESPN primary, football-data.org secondary, openfootball seed, full reconciliation strategy |
| 1.1 | 2026-06-12 | Live-verification corrections (backend build): **(a)** ESPN reports finished matches as `status.type.id "28"` / `STATUS_FULL_TIME`, not the documented `"3"` / `STATUS_FINAL` — the normalizer now maps on `status.type.state` (`pre`\|`in`\|`post`) first, documented ids as fallback, unknown → WARNING + `scheduled` unchanged. **(b)** The 2026 openfootball edition has top level `{name, matches}` (no `rounds`), `team1`/`team2` are plain NAME STRINGS (no 3-letter codes — codes come from ESPN `abbreviation` instead), knockouts use tokens (`W101`, `1A`, `3A/B/C/D/F`), `time` is local with UTC offset (`"13:00 UTC-6"`). **(c)** One ESPN scoreboard call with `?dates=YYYYMMDD-YYYYMMDD&limit=200` returns all 104 events — call budget unchanged. **(d)** ESPN models bracket placeholders as teams (`"Group A Winner"`, abbr `1A`), used by the seed for knockout fixture matching. |