# BACKLOG.md
## FIFA World Cup Intelligence Dashboard

**Purpose:** Every feature that is not in the MVP, every known limitation, every conscious cut, and every piece of technical debt lives here. Nothing stays as a `TODO` comment in code — it comes here instead.

**Rules:**
- Add an entry the moment a decision is made to defer something
- Never delete entries — mark them `[DONE]` or `[CANCELLED]` with a reason
- If an item is picked up, link to the PR or commit that closes it
- Priority: `P1` = next logical thing to build | `P2` = would add real value | `P3` = nice to have | `DEBT` = technical improvement with no user-visible change

---

## Section 1 — MVP Cuts (Deferred at Day-1 Build)

These were explicitly cut from the MVP to hit the 1-day build target. They are candidates for v1.1 once the MVP is stable and deployed.

---

### [BACKLOG-001] AI Natural-Language Query — Full Implementation
**Priority:** P1  
**Cut from:** PRD §5.7, CLAUDE.md §4.7  
**Cut reason:** Time — the constrained query endpoint is the last feature in the build plan and is cut first if behind schedule  
**Current state:** A "coming soon" UI stub on the home page and a `POST /query` endpoint that returns `HTTP 501 Not Implemented`  
**What "done" looks like:**
- `POST /query` implemented with the 10 whitelisted question patterns (CLAUDE.md §8.3)
- LLM selects from the whitelist using constrained tool-select (no raw SQL)
- Response includes `{ answer, evidence: { metric, value, team?, player? }, supported }`
- Out-of-scope questions return `supported: false` with an honest refusal message
- Prompt lives in `backend/app/ai/prompts/nl_query_v1.txt`
- Frontend search box replaced with a functional input that calls the endpoint
- 2 tests added: `test_nl_query_returns_evidence`, `test_nl_query_unknown_question_refuses`

---

### [BACKLOG-002] Match Lineups Display
**Priority:** P1  
**Cut from:** PRD §5.5, CLAUDE.md §4.5  
**Cut reason:** ESPN lineup data is not guaranteed to be present and requires per-match `/summary` calls; deprioritised to avoid over-spending API budget at build time  
**Current state:** The `lineups` field is fetched and stored in the DB when available, but the UI hides the lineup section entirely if `lineups` is null  
**What "done" looks like:**
- UI shows a starting XI formation or a simple list for both teams when `lineups` is present
- Gracefully hidden (not an error) when absent
- Substitutes shown in a separate row if available

---

### [BACKLOG-003] Team Statistics — Full Depth (Possession, Shots, Corners) `[DONE]`
**Priority:** P1  
**Cut from:** PRD §5.4  
**Done:** 2026-06-12 (backend build session). `GET /teams/{id}` serves the full
`TeamAggregate` — possession_avg (mean across that team's match_stats rows),
shots, shots on target, corners, cards (sums), clean sheets — computed from the
match_stats rows the ingestion pipeline writes from ESPN `/summary`. Missing
fields serve `null` → UI renders `—`. Verified live against Mexico's opener
(possession_avg 60.5, shots 16).

---

### [BACKLOG-004] Data Verified Badge (UI)
**Priority:** P2  
**Cut from:** CLAUDE.md §5.4, api-research.md §6.1  
**Cut reason:** The reconciliation logic runs in the pipeline and the `verified` column is written correctly. The UI indicator was cut to save frontend time  
**Current state:** `fixtures.verified` column is populated correctly. The UI does not surface it  
**What "done" looks like:**
- Finished match cards and match detail pages show a small `✓ verified` chip when `verified = true`
- Show `⚠ unverified` when `verified = false`
- Tooltip explains what "verified" means when hovered

---

## Section 2 — Post-MVP Features (v2 Candidates)

These were never in MVP scope (PRD §4, "Out of scope"). They are candidates for a v2 if the project is continued.

---

### [BACKLOG-005] Knockout Bracket Visualizer
**Priority:** P1 (post-MVP)  
**PRD reference:** PRD §16  
**Description:** Visual bracket showing the round of 32 → final progression as knockout matches are played. Teams advance automatically from computed standings.  
**Dependencies:** Standings must be finalised after group stage (day 3 of tournament). Bracket data structure needs to be added to the DB schema.

---

### [BACKLOG-006] WebSocket Live Updates
**Priority:** P2 (post-MVP)  
**PRD reference:** PRD §16, PRD §6 (non-goals)  
**Description:** Replace the 30-second client polling with a WebSocket connection so live score updates push to the client instantly  
**Current approach:** `setInterval` polling every 30s — sufficient for MVP, noticeably laggy in UX  
**Dependencies:** Backend needs a WebSocket endpoint (FastAPI supports this natively). Frontend needs to replace the `useLiveFixtures` polling hook with a `useLiveFixturesWS` WebSocket hook.  
**Note:** Do not implement until polling is confirmed as a UX problem — do not add complexity for a theoretical improvement.

---

### [BACKLOG-007] Player Profile Pages
**Priority:** P2 (post-MVP)  
**PRD reference:** PRD §16  
**Description:** Deep-linked `/player/[id]` page showing: career stats for this tournament, goals scored (with minute and match), assists, cards, and which team they play for  
**Dependencies:** Player data is already in the DB (`players` table, `goals` table). Needs a new `/players/{id}` FastAPI endpoint and a new frontend route.

---

### [BACKLOG-008] Head-to-Head Team Comparison
**Priority:** P2 (post-MVP)  
**Description:** `/compare?teams=BRA,ARG` page showing side-by-side stat comparison for two teams: goals, clean sheets, form, possession avg, discipline  
**Dependencies:** Team stats aggregation (BACKLOG-003) must be complete first.

---

### [BACKLOG-009] Historical Tournaments
**Priority:** P3 (post-MVP)  
**PRD reference:** PRD §16  
**Description:** Extend the dashboard to show previous World Cups (2022 Qatar, 2018 Russia, 2014 Brazil). Uses openfootball historical JSON data.  
**Dependencies:** DB schema needs a `tournament_year` column on fixtures/standings. UI needs a tournament selector.

---

### [BACKLOG-010] User Favorites and Match Notifications
**Priority:** P3 (post-MVP)  
**PRD reference:** PRD §16 — explicitly out of scope for MVP  
**Description:** Users can star teams to follow; receive browser push notifications when a match goes live or ends  
**Dependencies:** Requires authentication (NextAuth or similar), user table in DB, push notification service (e.g. web-push). This is a significant scope increase — not suitable for a 1-day extension.

---

### [BACKLOG-011] Dark / Light Theme Toggle
**Priority:** P3 (post-MVP)  
**PRD reference:** PRD §4 ("ship one theme")  
**Description:** shadcn/ui and Tailwind support dark mode natively via `class` strategy. Add a theme toggle button and persist preference in localStorage.  
**Current state:** Ships in dark mode only (or whichever single theme is chosen on day 1).  
**Effort:** Low — 2–3 hours.

---

### [BACKLOG-012] Richer NL Query with Chart Output
**Priority:** P3 (post-MVP)  
**PRD reference:** PRD §16  
**Description:** Extend the NL query feature so answers that involve a ranked list (e.g. "top 5 scorers") render as a small inline chart rather than just text  
**Dependencies:** BACKLOG-001 (NL query) must be complete and stable first.

---

### [BACKLOG-013] Privacy-Light Analytics
**Priority:** P3 (post-MVP)  
**PRD reference:** PRD §15 (optional note)  
**Description:** Add Plausible or similar privacy-first analytics to track: page views, most-viewed matches, most-searched NL queries  
**Note:** No cookies, no personal data, compliant with GDPR without a consent banner.

---

## Section 3 — Technical Debt

These are not features — they are improvements to the implementation that would reduce risk, improve maintainability, or improve performance. None of them change user-visible behaviour.

---

### [DEBT-001] ESPN API URL Monitoring
**Priority:** DEBT  
**Description:** ESPN has changed base URLs before (fantasy API, ~April 2024). Add an automated check that fires a CRITICAL log if any ESPN endpoint returns a non-200 for 3 consecutive runs, with the URL logged so it can be investigated  
**Current state:** Failures are logged but the alert threshold is a simple counter — not tied to a specific URL pattern check

---

### [DEBT-002] Alembic Migration Tests
**Priority:** DEBT  
**Description:** Add a pytest fixture that spins up a fresh test database, runs `alembic upgrade head`, and verifies all tables and indexes exist as expected. Prevents silent migration failures  
**Effort:** ~2 hours

---

### [DEBT-003] Ingestion Job — Idempotency Guarantee `[DONE]`
**Priority:** DEBT  
**Done:** 2026-06-12. Goals are wholesale-replaced per fixture on every run
(ESPN is the sole goal source), and the initial migration adds
`UNIQUE (fixture_id, player_name, minute, type)` as a second guard.
(`player_name` rather than `player_id` because ESPN timeline events carry
display names; player_id can be null.) Duplicate runs cannot double-count.

---

### [DEBT-004] Frontend API Client Error States
**Priority:** DEBT  
**Description:** `src/lib/api.ts` currently throws on non-200 responses. Add typed error classes (`APIError`, `NetworkError`, `StaleDataError`) so error boundaries can render context-specific messages rather than a generic fallback  
**Effort:** ~1 hour

---

### [DEBT-005] Python Dependency Pinning Audit `[DONE]`
**Priority:** DEBT  
**Done:** 2026-06-13. `pip-audit -r requirements.txt` reports **no known
vulnerabilities** after bumping fastapi 0.115.8 → 0.136.3 (pulls starlette 1.3.1,
clearing CVE-2025-54121 / CVE-2025-62727 / PYSEC-2026-161), pytest → 9.0.3,
pytest-asyncio → 1.4.0, and pinning starlette explicitly. Full transitive
freeze-pinning not done (top-level pins retained for readability).

---

### [DEBT-006] ESPN Response Caching Layer
**Priority:** DEBT  
**Description:** Currently, if the ingestion job runs twice within 30 seconds (e.g. during a live window), it makes duplicate ESPN calls. Add an in-memory or Redis TTL cache (even `functools.lru_cache` with a TTL wrapper) on the fetcher to deduplicate calls within the same window  
**Effort:** ~1 hour

---

### [DEBT-007] Structured Logging Format
**Priority:** DEBT  
**Description:** The ingestion job currently logs with Python's standard `logging`. Replace with `structlog` to emit JSON-structured logs (timestamp, level, event, key-value pairs). Makes log querying in Railway/Render/Fly log dashboards significantly easier  
**Effort:** ~2 hours

---

### [DEBT-008] ID Mapping Table — Initial Population Script
**Priority:** DEBT  
**Description:** The `external_id_map` table is built automatically during ingestion, but the first run requires both ESPN and football-data.org to return the same teams. If either source is down on first run, the map is incomplete. Add a `scripts/build_id_map.py` that can be run manually to populate it from both sources independently  
**Effort:** ~1 hour

---

### [DEBT-009] Rate Limiting Behind a Reverse Proxy
**Priority:** DEBT  
**Description:** slowapi keys on the client IP via `get_remote_address`. Behind Koyeb's edge proxy this can resolve to the proxy IP, so the 60/min limit may be shared across all users (and platform health checks) instead of being per-client. Acceptable for the portfolio demo. Fix by trusting `X-Forwarded-For` (e.g. a key func that reads the first hop) once real traffic warrants it. Surfaced during the 2026-06-13 Koyeb deploy prep (see `docs/deploy.md`)  
**Effort:** ~30 min

---

## Section 4 — Known Limitations (Accepted for MVP)

These are limitations that are known, accepted, and will not be fixed unless explicitly deprioritised out of this section. They are documented here so a reviewer or future developer is not surprised.

| # | Limitation | Accepted reason | Would fix in |
|---|---|---|---|
| KL-001 | Lineups may be absent for some matches | ESPN does not guarantee lineups for all fixtures | BACKLOG-002 |
| KL-002 | Assists come from ESPN keyEvents prose, applied when a match's summary is synced (live polls + one final post-match pass) | football-data free tier returns null assists; ESPN text is the complete source | Resolved 2026-06-13 |
| KL-003 | NL query returns "coming soon" stub | Time cut | BACKLOG-001 |
| KL-004 | No possession/shots on team page | ESPN summary calls add API budget | BACKLOG-003 |
| KL-005 | Single theme (no dark/light toggle) | PRD explicitly defers this | BACKLOG-011 |
| KL-006 | ESPN API is unofficial — may break | No free real-time alternative exists | Have football-data.org as fallback |
| KL-007 | No knockout bracket | PRD §4 out of scope | BACKLOG-005 |
| KL-008 | 30-second poll latency on live scores | Polling is sufficient for MVP; WebSockets deferred | BACKLOG-006 |
| KL-009 | No user accounts or personalisation | PRD §2 non-goal | BACKLOG-010 |
| KL-010 | Keyless mode: scorer board derives from local goals + lineups — assists show 0, MP = lineup appearances | No FOOTBALL_DATA_API_KEY configured yet (owner decision 2026-06-12); switches to football-data automatically once the key is set | Add free key |
| KL-011 | Keyless mode: all finished fixtures stay `verified: false` | Reconciliation needs football-data.org; skips with WARNING | Add free key |
| KL-012 | Keyless mode: no AI insights generated | No AI_API_KEY yet; enrichment skips with WARNING, UI hides the block | Add Groq key |
| KL-013 | AI budget breaker uses a flat conservative price estimate, not per-model pricing | Overestimates only — trips early, never late | Per-model price table if needed |
| KL-015 | `npm audit` reports 6 high (esbuild/vite/vitest) + 2 moderate (postcss CSS-stringify XSS) | All in **devDependencies** (test toolchain) — not in the production bundle; esbuild advisories are dev-server/Deno-specific; postcss XSS needs untrusted CSS (we author all CSS) and has no upstream fix across Next versions yet | Bump vitest/@vitejs/plugin-react when peer-deps align |
| KL-014 | A few scorers show position `—` / no clean-sheet enrichment when football-data and ESPN transliterate a name differently beyond word order (e.g. football-data "Hyun-Gyu Oh" vs ESPN "Oh Hyeon-Gyu") | Word-order mismatches are resolved by a sorted-token name key; true transliteration differences are not, and fuzzy matching would risk false positives | Add a curated alias map or fuzzy threshold if it becomes material |

---

## Section 5 — Completed Items

Items moved here when they are implemented and merged.

- **2026-06-12 — Backend MVP shipped** (full session): schema + Alembic initial
  migration, openfootball+ESPN merge seed (104/104 fixtures matched), 7-step
  ingestion pipeline with self-computed standings + two-source reconciliation,
  multi-provider AI insight generation (groq default) with budget breaker,
  all REST endpoints matching `frontend/src/types/index.ts`, 23 pytest tests,
  smoke test 11/11, frontend flipped off mocks and verified on live data.
  BACKLOG-003 and DEBT-003 closed in the same session.
- **2026-06-13 — Pre-deploy API security pass**: added `tests/test_security.py`
  (13 tests: secret-leak, auth, input validation, error-handling) and
  `scripts/security_probe.py` (live: 22/22 — no secret leaks in any response,
  401/422/501 enforced, CORS never `*`, rate limiting active). Fixed a latent
  leak: Gemini provider now sends its key via `x-goog-api-key` header (was a
  `?key=` query param that httpx logs); httpx logger quieted to WARNING.
  Dependency audit: backend pip-audit CLEAN (fastapi/starlette/pytest bumps);
  Next.js → 15.5.19 clears the critical + production-high advisories (remaining
  npm items are dev-only, KL-015). 39 backend + 10 frontend tests pass.
- **2026-06-13 — Frontend polish + assist fix**: FIFA WC26 logo + wordmark in
  the app bar; removed eyebrow/description sub-text from list-page headers;
  Fixtures board rebuilt as Live (pinned) + Upcoming/Results tabs revealing one
  matchday at a time via Show more (first screen 3 cards vs ~104). Assists now
  parsed from ESPN keyEvents prose (goals.assist_player_name + fixtures.summary
  _synced_at, two migrations), making the Assists board complete incl. assisters
  who didn't score, with positions/teams from lineups. 26 backend + 10 frontend
  tests pass.
- **2026-06-12 — API keys activated** (follow-up session): football-data.org +
  Groq keys added. Confirmed `X-Auth-Token` header. Added `scripts/check_keys.py`
  (loud key + live-shape validation). Keyed ingestion run: scorers now carry
  football-data assists, both finished fixtures reconcile to `verified: true`,
  64 AI insights cached and growing. Added sorted-token name matching so
  football-data ↔ ESPN name-order differences resolve for scorer position /
  GK clean sheets (KL-014 covers the residual transliteration cases). 24 tests.

---

**Last updated:** 2026-06-12  
**Next review:** After MVP is deployed — review Section 1 cuts and Section 3 debt items for v1.1 prioritisation