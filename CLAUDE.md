# CLAUDE.md
## FIFA World Cup Intelligence Dashboard — Claude Code Operating Instructions

> **This file is your first and most important read. Do not write a single line of code, create a single file, or run a single command until you have read and understood every section of this document.**

---

## SECTION 0 — Mandatory Pre-Flight: Read Everything First

When you open this project, you must complete the following reading in order before taking any action whatsoever.

### Step 1 — Read the governing documents

Read each of these files completely, in this order:

```
Templates/master-project-prompt.md       ← global workspace standards (parent folder)
Amout-me/about-me.md       ← global 
Templates/anti-ai-style.md       ← global 
docs/PRD.md                       ← product requirements for this project
docs/api-research.md              ← approved API sources and correctness strategy
docs/dashboard.md
docs/adr/                         ← all Architecture Decision Records (read every one)
BACKLOG.md                        ← known limitations and deferred features
.env.example                      ← every environment variable this project needs
```

If any of these files does not exist yet, **stop and say so** before proceeding. Do not invent what they might contain.

### Step 2 — Confirm your understanding

After reading, write a short summary (in your response, not in a file) covering:
- What this project does and who it is for
- The four engineering competencies it must visibly demonstrate
- The current state of the codebase (what exists, what is incomplete, what is broken)
- What you are being asked to do in this session
- Any ambiguities or missing information that would block you

Do not proceed past Step 2 until that summary is written and confirmed.

### Step 3 — Ask before assuming

If anything in the governing documents is unclear, contradictory, or insufficient to make a decision without guessing: **ask**. One clear question at a time. Never guess and proceed — the cost of a wrong assumption compounds across every file it touches.

---

## SECTION 1 — Project Identity

| Field | Value |
|---|---|
| **Project name** | FIFA World Cup Intelligence Dashboard |
| **Type** | Portfolio project |
| **Target build time** | 1 day (deployable MVP) |
| **Status** | See `docs/PRD.md` §1 |
| **PRD version** | 1.0 |
| **Governing standard** | `../master-project-prompt.md` |

### What this project must demonstrate to a portfolio reviewer
A reviewer skimming this repo and live demo must be able to immediately trace:
1. **AI engineering** — where the LLM prompt lives, how it is versioned, how output is cached, where the constrained query logic is
2. **API integration** — where the third-party football API is called, how the response is normalized, how rate limits are respected
3. **Data processing** — the ETL pipeline: fetch → normalize → upsert → aggregate → serve
4. **Dashboard development** — a fast, responsive, polished Next.js 15 UI that works on mobile

If any of these four is not obviously visible in the repo structure, that is a failure condition — not a cosmetic issue.

---

## SECTION 2 — Tech Stack (Locked)

Do not deviate from this stack without an explicit instruction from the project owner. If you believe a deviation is warranted, surface it as a trade-off decision (see `../master-project-prompt.md` §10.4) and wait for approval.

| Layer | Technology | Version / Notes |
|---|---|---|
| Frontend framework | Next.js | 15, App Router only |
| Frontend language | TypeScript | strict mode, `"strict": true` in tsconfig |
| Styling | Tailwind CSS | utility-first, no inline styles |
| UI components | shadcn/ui | do not roll custom primitives that shadcn already provides |
| Backend framework | FastAPI | Python 3.11+ |
| Backend language | Python | type hints everywhere, Pydantic v2 for all models |
| Database | PostgreSQL | 15+; managed instance in production |
| ORM / query | SQLAlchemy 2.x | async engine; Alembic for migrations |
| Scheduler | APScheduler | in-process; `AsyncIOScheduler` |
| AI provider | Configurable via env | see `AI_MODEL` and `AI_PROVIDER` in `.env.example` |
| Linting (TS) | ESLint + Prettier | config files committed |
| Linting (Python) | Ruff | `ruff.toml` committed |
| Testing (TS) | Vitest | |
| Testing (Python) | pytest + pytest-asyncio | |
| Deploy: frontend | Vercel | `vercel.json` in `/frontend` |
| Deploy: backend + DB | Railway / Render / Fly | platform config file committed |
| Containerisation | docker-compose.yml | for local development |

---

## SECTION 3 — Repository Structure (Canonical)

This is the required folder structure. Create it exactly as shown on day one. Do not invent new top-level folders without approval.

```
/                                  ← project root
├── CLAUDE.md                      ← this file
├── README.md                      ← setup + architecture + deploy (always up to date)
├── BACKLOG.md                     ← deferred features and known limits
├── .env.example                   ← every env var, described, no real values
├── .gitignore                     ← comprehensive; .env always listed
├── docker-compose.yml             ← postgres + backend for local dev
│
├── docs/
│   ├── PRD.md                     ← product requirements (source of truth for features)
│   ├── api-research.md            ← approved API sources and data correctness strategy
│   └── adr/
│       ├── ADR-001-api-sources.md
│       ├── ADR-002-cache-architecture.md
│       └── ...                    ← one ADR per non-obvious decision
│
├── frontend/                      ← Next.js 15 app
│   ├── vercel.json
│   ├── package.json
│   ├── tsconfig.json              ← strict: true
│   ├── .eslintrc.json
│   ├── prettier.config.js
│   ├── tailwind.config.ts
│   ├── components.json            ← shadcn/ui config
│   └── src/
│       ├── app/                   ← App Router pages
│       │   ├── page.tsx           ← home: live fixtures
│       │   ├── standings/
│       │   ├── scorers/
│       │   ├── match/[id]/
│       │   └── team/[id]/
│       ├── components/            ← shared UI components
│       ├── lib/                   ← api client, utils, types
│       └── types/                 ← shared TypeScript types
│
├── backend/                       ← FastAPI app
│   ├── requirements.txt           ← pinned
│   ├── ruff.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/              ← migration files
│   └── app/
│       ├── main.py                ← FastAPI app + router registration
│       ├── config.py              ← settings via pydantic-settings
│       ├── database.py            ← async engine + session factory
│       ├── models/                ← SQLAlchemy ORM models
│       ├── schemas/               ← Pydantic request/response schemas
│       ├── routers/               ← one file per route group
│       │   ├── fixtures.py
│       │   ├── standings.py
│       │   ├── scorers.py
│       │   ├── teams.py
│       │   └── query.py
│       ├── ingestion/             ← ETL pipeline
│       │   ├── scheduler.py       ← APScheduler setup
│       │   ├── fetcher.py         ← HTTP calls to football API
│       │   ├── normalizer.py      ← maps API shapes to internal schema
│       │   ├── upsert.py          ← DB write operations
│       │   └── aggregator.py      ← standings / scorers / team stats
│       ├── ai/                    ← AI features
│       │   ├── prompts/           ← versioned prompt files (not inline strings)
│       │   │   ├── match_insight_v1.txt
│       │   │   └── nl_query_v1.txt
│       │   ├── insights.py        ← insight generation + caching
│       │   └── nl_query.py        ← constrained natural-language query
│       └── reconciliation/        ← data correctness checks
│           └── checker.py
│
└── scripts/
    ├── seed.py                    ← seed DB from openfootball/worldcup.json
    ├── smoke_test.sh              ← hit every endpoint, check 200s
    └── validate_data.py           ← run reconciliation checks manually
```

---

## SECTION 4 — Features and Acceptance Criteria

These are the exact requirements. Implement them literally. If a requirement is ambiguous, ask — do not interpret and proceed.

### 4.1 Live Fixtures (PRD §5.1) — MUST HAVE
- Home page (`/`) lists fixtures grouped by day
- Live matches appear at the top with a `LIVE` badge and current score
- Finished matches show final score; upcoming show kickoff in the user's local timezone (use `Intl.DateTimeFormat`)
- Load time: fixtures served from DB, not from a live API call — must be < 1.5 s
- Client polls for updates every 30 s on live matches only (not on every page)
- Each fixture card navigates to `/match/[id]`
- Empty days render a friendly empty state, never a blank screen or error

### 4.2 Group Standings (PRD §5.2) — MUST HAVE
- `/standings` page with all 12 groups, selectable by tab or dropdown
- Columns: P, W, D, L, GF, GA, GD, Pts
- Sorted by: Points → Goal Difference → Goals For → Alphabetical (official FIFA 2026 tiebreaker)
- Standings are **recomputed** from match results in the ingestion job — never hand-entered
- Each team row links to `/team/[id]`

### 4.3 Top Scorers (PRD §5.3) — MUST HAVE
- `/scorers` page showing player, team, goals, assists, matches played
- Default sort: goals descending; ties broken by fewer matches played, then assists
- Client-side sort toggle between goals and assists (instant, no network call)

### 4.4 Team Statistics (PRD §5.4) — MUST HAVE
- `/team/[id]` page: matches played, goals for/against, possession avg, shots, cards, clean sheets
- Recent form: last 5 results as W/D/L chips, colour-coded
- Stats aggregated server-side in the ingestion pipeline, not computed on page load
- Missing fields degrade to `—`, never crash or throw

### 4.5 Match Details (PRD §5.5) — MUST HAVE
- `/match/[id]` page: teams, score, status, venue, goal timeline, basic stats
- Stats: possession, shots, corners, cards; lineups if the API provides them
- Renders correctly for all three states: `scheduled` (preview), `live`, `finished`
- URL is deep-linkable and shareable
- AI insight block rendered below stats (see 4.6)

### 4.6 AI Match Insights (PRD §5.6) — MUST HAVE
- Every match in `scheduled` or `finished` state has a cached insight in `ai_insights`
- Pre-match: 2–4 sentence form-based preview built from DB stats
- Post-match: 2–4 sentence result summary highlighting the decisive stat
- Generated in the ingestion job, **not** on the request path
- If no insight is cached yet, the block is hidden — it never blocks page render
- Prompt lives in `backend/app/ai/prompts/match_insight_v1.txt` — not inline
- `AI_MODEL` and `AI_PROVIDER` configured via environment variables
- Every AI call logs: model, input tokens, output tokens, latency, cache hit/miss

### 4.7 AI Natural-Language Query (PRD §5.7) — SHIP IF TIME ALLOWS, else "coming soon" UI stub
- Search box, likely on the home page or a dedicated `/ask` route
- `POST /query` endpoint; LLM selects from a **whitelist of ~10 pre-defined query patterns** (constrained tool-select) — no raw SQL generation
- Response includes the answer sentence **and** the numeric evidence
- Out-of-scope questions get an honest `"I can't answer that yet"` — never a hallucinated stat
- Prompt lives in `backend/app/ai/prompts/nl_query_v1.txt`

---

## SECTION 5 — Data Architecture (Non-Negotiable)

### 5.1 The golden rule
**The frontend never calls the football API. The frontend never calls the LLM. Ever.**

All third-party calls happen in the ingestion job. The frontend talks only to the FastAPI backend. The FastAPI GET endpoints read only from PostgreSQL. This is the architecture that makes the app fast, rate-limit-safe, cost-controlled, and demo-stable.

If you find yourself writing a server action or API route that calls a third-party API, stop — that is an architecture violation.

### 5.2 Database schema
Implement exactly this schema. Do not add, rename, or remove columns without a corresponding Alembic migration and an update to this file.

```sql
-- Raw / source tables
teams (
  id              SERIAL PRIMARY KEY,
  external_id     TEXT UNIQUE NOT NULL,   -- ID from the football API
  name            TEXT NOT NULL,
  code            TEXT,                   -- e.g. "BRA", "ENG"
  group_label     TEXT,                   -- e.g. "A", "B" ... "L"
  flag_url        TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
)

players (
  id              SERIAL PRIMARY KEY,
  external_id     TEXT UNIQUE NOT NULL,
  name            TEXT NOT NULL,
  team_id         INTEGER REFERENCES teams(id),
  position        TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
)

fixtures (
  id              SERIAL PRIMARY KEY,
  external_id     TEXT UNIQUE NOT NULL,
  home_team_id    INTEGER REFERENCES teams(id),
  away_team_id    INTEGER REFERENCES teams(id),
  kickoff_at      TIMESTAMPTZ,
  venue           TEXT,
  status          TEXT NOT NULL,          -- scheduled | live | finished
  home_score      INTEGER,
  away_score      INTEGER,
  group_label     TEXT,
  round           TEXT,
  minute          INTEGER,                -- live display clock; null unless live (frontend Fixture.minute)
  verified        BOOLEAN DEFAULT FALSE,  -- two-source reconciliation (api-research §6.2)
  verified_at     TIMESTAMPTZ,
  mismatch_count  INTEGER DEFAULT 0,      -- consecutive mismatch runs; CRITICAL at threshold (api-research §9)
  summary_synced_at TIMESTAMPTZ,         -- when ESPN /summary (stats, lineups, assists) last applied; NULL on status change so each state syncs once
  last_updated_at TIMESTAMPTZ DEFAULT NOW()
)

match_stats (
  id              SERIAL PRIMARY KEY,
  fixture_id      INTEGER REFERENCES fixtures(id),
  team_id         INTEGER REFERENCES teams(id),
  possession      NUMERIC(5,2),           -- percentage
  shots           INTEGER,
  shots_on_target INTEGER,
  corners         INTEGER,
  fouls           INTEGER,
  yellow_cards    INTEGER,
  red_cards       INTEGER,
  UNIQUE (fixture_id, team_id)
)

goals (
  id              SERIAL PRIMARY KEY,
  fixture_id      INTEGER REFERENCES fixtures(id),
  player_id       INTEGER REFERENCES players(id),
  player_name     TEXT,                   -- denormalized: ESPN timeline gives display names (frontend Goal.player_name)
  assist_player_name TEXT,                -- assist provider, parsed from ESPN keyEvents prose ("Assisted by …"); the only assist source
  team_id         INTEGER REFERENCES teams(id),
  minute          INTEGER,
  type            TEXT,                   -- regular | own_goal | penalty
  UNIQUE (fixture_id, player_name, minute, type)  -- dedup guard (DEBT-003)
)

-- Lineups from ESPN summaries (frontend FixtureDetailResponse.lineups; source
-- for scorer position + GK clean sheets — owner decision 2026-06-12)
lineups (
  id              SERIAL PRIMARY KEY,
  fixture_id      INTEGER NOT NULL REFERENCES fixtures(id),
  team_id         INTEGER NOT NULL REFERENCES teams(id),
  player_name     TEXT NOT NULL,
  number          INTEGER,
  position        TEXT,                   -- normalized GK | DF | MF | FW
  is_starter      BOOLEAN NOT NULL DEFAULT TRUE,
  formation       TEXT,                   -- per team, repeated per row (MVP)
  UNIQUE (fixture_id, team_id, player_name)
)

-- Cross-source id reconciliation (api-research §5)
external_id_map (
  id              SERIAL PRIMARY KEY,
  internal_id     INTEGER NOT NULL,
  entity_type     TEXT NOT NULL,          -- 'team' | 'fixture'
  source          TEXT NOT NULL,          -- 'espn' | 'football_data' | 'openfootball'
  external_id     TEXT NOT NULL,
  UNIQUE (entity_type, source, external_id)
)

-- Observability: one row per ingestion run (feeds /health and POST /ingest)
ingestion_runs (
  id              SERIAL PRIMARY KEY,
  started_at      TIMESTAMPTZ DEFAULT NOW(),
  finished_at     TIMESTAMPTZ,
  status          TEXT NOT NULL DEFAULT 'running',  -- running | ok | error
  fixtures_updated      INTEGER DEFAULT 0,
  insights_generated    INTEGER DEFAULT 0,
  reconciliation_flags  INTEGER DEFAULT 0,
  error           TEXT
)

-- Derived tables (recomputed each ingestion run)
standings (
  id              SERIAL PRIMARY KEY,
  team_id         INTEGER REFERENCES teams(id) UNIQUE,
  group_label     TEXT NOT NULL,
  played          INTEGER DEFAULT 0,
  won             INTEGER DEFAULT 0,
  drawn           INTEGER DEFAULT 0,
  lost            INTEGER DEFAULT 0,
  goals_for       INTEGER DEFAULT 0,
  goals_against   INTEGER DEFAULT 0,
  goal_diff       INTEGER GENERATED ALWAYS AS (goals_for - goals_against) STORED,
  points          INTEGER DEFAULT 0,
  updated_at      TIMESTAMPTZ DEFAULT NOW()
)

scorer_stats (
  id              SERIAL PRIMARY KEY,
  player_id       INTEGER REFERENCES players(id) UNIQUE,
  goals           INTEGER DEFAULT 0,
  assists         INTEGER DEFAULT 0,
  matches_played  INTEGER DEFAULT 0,
  position        TEXT,                   -- derived from ESPN lineups; null → UI "—"
  clean_sheets    INTEGER,                -- goalkeepers only; null for outfield
  updated_at      TIMESTAMPTZ DEFAULT NOW()
)

-- AI cache
ai_insights (
  id              SERIAL PRIMARY KEY,
  fixture_id      INTEGER REFERENCES fixtures(id),
  state           TEXT NOT NULL,          -- scheduled | finished
  content         TEXT NOT NULL,
  model           TEXT NOT NULL,
  prompt_version  TEXT NOT NULL,
  input_tokens    INTEGER,
  output_tokens   INTEGER,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (fixture_id, state)
)
```

Every migration must be created with Alembic. Never edit the DB schema directly in production.

### 5.3 Ingestion pipeline sequence
The ingestion job must run these steps in order. Never skip a step, never reorder them.

```
1. fetch()       → call football API, get raw JSON
2. validate()    → Pydantic schema validation; reject/log invalid records
3. normalize()   → map API fields to internal schema
4. upsert()      → write to teams, players, fixtures, match_stats, goals
5. aggregate()   → recompute standings, scorer_stats from raw tables
6. reconcile()   → cross-check scores between primary and secondary source
7. enrich()      → generate AI insights for fixtures whose state changed
```

### 5.4 Data correctness — two-source reconciliation
Per `docs/api-research.md`, two data sources are used:
- **Primary:** ESPN public JSON API (live scores, match stats, lineups)
- **Secondary:** football-data.org (standings cross-check, scorer leaderboard)
- **Canonical fixture seed:** openfootball/worldcup.json (groups, teams, venues)

For every finished fixture, compare home/away score from both sources. If they match → mark `verified = true`. If they disagree → mark `verified = false`, log both values, alert in structured logs, serve the last verified value. The UI must show a small "data verified" / "data unverified" indicator where relevant.

---

## SECTION 6 — API Contracts (FastAPI)

Every endpoint listed here must exist and return exactly the documented shape. Do not add undocumented fields to responses without updating this file. Do not remove documented fields without a BACKLOG entry explaining why.

```
GET  /health
     → { status: "ok", db: "ok"|"error", ingestion_last_run: ISO8601, version: string }

GET  /fixtures?date=YYYY-MM-DD&status=scheduled|live|finished
     → { fixtures: Fixture[], generated_at: ISO8601 }

GET  /fixtures/{id}
     → { fixture: Fixture, stats: MatchStats[], goals: Goal[],
         lineups?: Lineup[], insight?: AIInsight }

GET  /standings?group=A|B|...|L
     → { standings: Standing[], group: string, updated_at: ISO8601 }

GET  /scorers?sort=goals|assists&limit=50
     → { scorers: ScorerStat[], updated_at: ISO8601 }

GET  /teams/{id}
     → { team: Team, stats: TeamAggregate, form: FormResult[] }

POST /query
     Body: { question: string }
     → { answer: string, evidence: { metric: string, value: number|string,
         team?: string, player?: string }, supported: boolean }

POST /ingest   (internal — require INGEST_SECRET header)
     → { status: "ok", fixtures_updated: int, insights_generated: int,
         reconciliation_flags: int }
```

All Pydantic response schemas live in `backend/app/schemas/`. All are fully typed — no `dict`, no `Any`.

---

## SECTION 7 — Frontend Routing and Components

### 7.1 Routes (App Router)
```
/                     → home: live + upcoming fixtures grouped by day
/standings            → group standings (all groups, tabbed)
/scorers              → top scorers leaderboard
/match/[id]           → match detail + AI insight
/team/[id]            → team stats + form
```

No other routes in MVP. If a route is needed that is not listed, ask first.

### 7.2 Component rules
- **Server Components** for all data fetching from the FastAPI backend. No `useEffect` for initial data load.
- **Client Components** (`"use client"`) only for: live polling logic, client-side sort, interactive tabs, the NL query input.
- **No business logic in components.** Data transformation belongs in `src/lib/`.
- **No direct fetch to the football API or LLM from any frontend file** — ever.
- All API calls from the frontend go through `src/lib/api.ts` — a single typed client. No ad-hoc `fetch` calls scattered across components.

### 7.3 Polling
Live match polling uses `setInterval` inside a `useEffect` in a dedicated `useLiveFixtures` hook. The interval is 30 000 ms. The interval is cleared in the cleanup function. The hook only polls when at least one fixture has `status === "live"`.

### 7.4 Responsive design
All pages must work correctly at these breakpoints: 375 px (mobile), 768 px (tablet), 1280 px (desktop). Test at all three before marking a UI task done. Use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`). No fixed pixel widths on layout containers.

---

## SECTION 8 — AI Feature Rules

These rules are specific to this project and extend `../master-project-prompt.md §7`.

### 8.1 Prompts are files, not strings
Both prompts live in `backend/app/ai/prompts/`:
- `match_insight_v1.txt` — for pre/post-match insights
- `nl_query_v1.txt` — for constrained natural-language queries

The version number is in the filename. When a prompt changes, create a new versioned file — never edit the existing one. The `ai_insights` table stores `prompt_version` so you can trace which prompt generated which insight.

### 8.2 Match insight prompt contract
The prompt receives a structured context object (not free text). The context must include:
- `match_type`: `"pre_match"` | `"post_match"`
- `home_team`, `away_team`: name, group, form (last 5 W/D/L), goals_for, goals_against
- `score` (post-match only): home score, away score
- `decisive_stat` (post-match only): the single most significant stat difference

The prompt instructs the model to return **exactly** this JSON:
```json
{ "insight": "<2-4 sentence string>" }
```
Parse this with Pydantic. If parsing fails, log the raw response and skip caching — do not crash the ingestion job.

### 8.3 NL query whitelist
The constrained query system supports exactly these 10 patterns. Do not add patterns without updating this list.

| # | Question pattern | Underlying query |
|---|---|---|
| 1 | Top scorer in the tournament | MAX goals from scorer_stats |
| 2 | Most goals by a team | SUM goals_for from standings |
| 3 | Best defensive team (fewest goals conceded) | MIN goals_against from standings |
| 4 | Team with the most wins | MAX won from standings |
| 5 | Current leader of group [X] | standings WHERE group_label=X ORDER BY points DESC LIMIT 1 |
| 6 | Teams with a clean sheet | COUNT fixtures where team had 0 goals against |
| 7 | Player with the most assists | MAX assists from scorer_stats |
| 8 | Highest scoring match | MAX (home_score + away_score) from fixtures |
| 9 | Team with most yellow cards | SUM yellow_cards from match_stats |
| 10 | How many matches have been played | COUNT finished fixtures |

For any other question, return `{ answer: "I can't answer that yet — I only know about goals, standings, scorers, and cards.", supported: false, evidence: null }`.

---

## SECTION 9 — Performance Requirements

These are acceptance criteria, not aspirations. A feature is not done until it meets them.

| Metric | Target | How to verify |
|---|---|---|
| Home page LCP | < 1.5 s | Lighthouse on a throttled mobile simulation |
| Backend GET endpoints | < 200 ms p95 | Logs + `/health` response time |
| Live match poll | ≤ 30 s between updates | Check `last_updated_at` on fixture |
| Ingestion job (normal run) | < 60 s end-to-end | APScheduler job duration log |
| AI insight generation | Cached; 0 ms on read | Confirm `ai_insights` row exists before serving |
| DB query hot paths | < 10 ms | Check `EXPLAIN ANALYZE` on all routes |

Required indexes (create in the initial migration, not later):
```sql
CREATE INDEX idx_fixtures_status       ON fixtures(status);
CREATE INDEX idx_fixtures_kickoff      ON fixtures(kickoff_at);
CREATE INDEX idx_fixtures_home_team    ON fixtures(home_team_id);
CREATE INDEX idx_fixtures_away_team    ON fixtures(away_team_id);
CREATE INDEX idx_standings_group       ON standings(group_label);
CREATE INDEX idx_scorer_stats_goals    ON scorer_stats(goals DESC);
CREATE INDEX idx_match_stats_fixture   ON match_stats(fixture_id);
CREATE INDEX idx_ai_insights_fixture   ON ai_insights(fixture_id, state);
```

---

## SECTION 10 — Environment Variables

Every variable in `.env.example` must be present before the app will start. The backend uses `pydantic-settings` to validate on startup — missing required variables must cause an immediate, clear startup error, not a runtime KeyError later.

```bash
# --- Database ---
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/worldcup

# --- Football API (Primary: ESPN public — no key needed) ---
ESPN_API_BASE_URL=https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world
ESPN_STANDINGS_URL=https://site.api.espn.com/apis/v2/sports/soccer/fifa.world

# --- Football API (Secondary: football-data.org) ---
FOOTBALL_DATA_API_KEY=your_key_here
FOOTBALL_DATA_BASE_URL=https://api.football-data.org/v4

# --- AI (multi-provider — owner decision 2026-06-12: free tiers first) ---
AI_PROVIDER=groq                       # groq | gemini | openrouter | anthropic | openai
AI_MODEL=llama-3.3-70b-versatile       # model id at the chosen provider
AI_API_KEY=your_key_here               # key for the ACTIVE provider
AI_MAX_TOKENS=300
AI_DAILY_BUDGET_USD=2.00               # circuit breaker threshold

# --- Ingestion ---
INGEST_SECRET=a_long_random_string     # required header for POST /ingest
SCHEDULER_ENABLED=true                 # false in tests/scripts
INGEST_INTERVAL_SECONDS=60             # how often the scheduler runs
LIVE_POLL_INTERVAL_SECONDS=30          # faster polling during live matches

# --- App ---
ENVIRONMENT=development                # development | production
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000     # comma-separated in production
```

---

## SECTION 11 — Security Baseline

- `INGEST_SECRET` header required on `POST /ingest`. Return 401 if absent or wrong.
- CORS: in production, `CORS_ORIGINS` lists only the Vercel frontend domain. Never `*` in production.
- Rate limiting: `slowapi` on all public endpoints. Default: 60 requests/minute per IP.
- All user input to `POST /query` is validated by Pydantic (max 500 chars, stripped, no HTML).
- `AI_API_KEY`, `FOOTBALL_DATA_API_KEY`, `DATABASE_URL`, `INGEST_SECRET` never logged, never returned in any response.
- `npm audit` / `pip-audit` run before first deploy. No critical vulnerabilities shipped.

---

## SECTION 12 — Error Handling Standards

### Backend
- Every route handler is wrapped in try/except. Unexpected exceptions return `500` with a generic message — never a raw stack trace.
- External API calls (football API, LLM) have a timeout (10 s default), retry (2 retries with exponential backoff), and a fallback (serve last cached data, log the failure).
- Ingestion errors do not crash the app. The scheduler catches, logs, and continues. A `consecutive_failures` counter is incremented; if it reaches 5, a structured CRITICAL log is emitted.
- Validation failures on ingest are logged at WARNING level with the raw payload — they do not stop the run.

### Frontend
- Every page has an `error.tsx` boundary that renders a friendly message, not a stack trace.
- Every page has a `loading.tsx` skeleton that matches the page's layout.
- If the API is unreachable, show the last successfully rendered data (via Next.js stale-while-revalidate) with a "data may be outdated" banner.
- The AI insight block is `{insight && <InsightBlock insight={insight} />}` — a missing insight is simply not rendered, never an error.

---

## SECTION 13 — Testing Requirements

Tests are not optional. The following must exist before a feature is marked done.

### Backend tests (`pytest`)
| Test | Type | Location |
|---|---|---|
| `test_health_endpoint` | integration | `tests/test_routes.py` |
| `test_fixtures_endpoint` | integration | `tests/test_routes.py` |
| `test_standings_computed_correctly` | unit | `tests/test_aggregator.py` |
| `test_fifa_tiebreaker_ordering` | unit | `tests/test_aggregator.py` |
| `test_ingest_normalizes_espn_response` | unit | `tests/test_normalizer.py` |
| `test_ingest_handles_missing_fields` | unit | `tests/test_normalizer.py` |
| `test_ai_insight_cached_not_regenerated` | unit | `tests/test_insights.py` |
| `test_nl_query_returns_evidence` | unit | `tests/test_nl_query.py` |
| `test_nl_query_unknown_question_refuses` | unit | `tests/test_nl_query.py` |
| `test_reconciliation_flags_mismatch` | unit | `tests/test_reconciliation.py` |

### Frontend tests (`vitest`)
| Test | Type |
|---|---|
| `FixtureCard` renders LIVE badge when status is live | component |
| `StandingsTable` sorts by FIFA tiebreaker rules | component |
| `ScorerTable` client-side sort works correctly | component |
| `useLiveFixtures` cleans up interval on unmount | hook |
| `api.ts` getFixtures correctly calls the backend URL | unit |

### Smoke test
`scripts/smoke_test.sh` hits every endpoint, checks for HTTP 200, and prints a pass/fail summary. Run it before every deploy.

---

## SECTION 14 — Deployment Checklist

Run through this list before calling any deploy done. Every item must be ✅ before the project is shipped.

```
ENVIRONMENT
[ ] .env.example is complete and matches the actual .env used in production
[ ] No real secrets committed to git (run: git log --all -p | grep -i "api_key\|secret\|password")
[ ] ENVIRONMENT=production set in the deployed backend
[ ] CORS_ORIGINS set to the production Vercel URL only

DATABASE
[ ] All Alembic migrations applied (alembic upgrade head)
[ ] Required indexes created (verify with \d+ table_name in psql)
[ ] Seed data loaded (python scripts/seed.py)
[ ] At least one ingestion run completed successfully

BACKEND
[ ] GET /health returns 200 with db: "ok"
[ ] All endpoints return 200 with real data
[ ] APScheduler is running (check logs for "Scheduler started")
[ ] Rate limiting active (test with a burst of requests)
[ ] INGEST_SECRET tested

FRONTEND
[ ] Deployed to Vercel, custom domain (if any) configured
[ ] All 5 routes load without errors (/, /standings, /scorers, /match/[id], /team/[id])
[ ] Mobile layout verified at 375px
[ ] Live fixture polling fires and updates the UI
[ ] AI insight appears on at least one finished match

AI
[ ] At least one ai_insights row exists in the DB
[ ] Insight appears correctly on a match detail page
[ ] AI_DAILY_BUDGET_USD circuit breaker configured

QUALITY
[ ] Lighthouse score ≥ 80 on Performance, Accessibility, Best Practices
[ ] npm audit — no critical vulnerabilities
[ ] pip-audit — no critical vulnerabilities
[ ] All tests pass (pytest + vitest)
[ ] smoke_test.sh passes

DOCUMENTATION
[ ] README.md has working local setup instructions (tested on a clean checkout)
[ ] README.md lists all four portfolio competencies with links to where they're demonstrated
[ ] All ADRs written for non-obvious decisions
[ ] BACKLOG.md lists any MVP cuts and why
```

---

## SECTION 15 — The Cut List (If Time Runs Out)

Cut in this order. **Never cut items marked MUST HAVE.**

| Priority | Feature | Action if cut |
|---|---|---|
| Cut first | NL Query (§4.7) | Render a "coming soon" UI stub; leave the POST /query endpoint stubbed with a 501 |
| Cut second | Match lineups | Hide the lineups section; do not error if `lineups` is null |
| Cut third | Team stat depth (possession, shots) | Show only W/D/L/GD; hide missing stat rows |
| Cut fourth | Data verified badge | Remove badge; keep the reconciliation logic in the pipeline |
| MUST HAVE | Live fixtures | Never cut |
| MUST HAVE | Group standings | Never cut |
| MUST HAVE | Top scorers | Never cut |
| MUST HAVE | AI match insights | Never cut — it is the core AI engineering showcase |
| MUST HAVE | /health endpoint | Never cut |
| MUST HAVE | Working deploy | Never cut |

---

## SECTION 16 — What to Do When You Are Unsure

This section is the most important one for preventing wasted work.

**Stop and ask if you are unsure about:**
- Which API endpoint to call and what its response shape is
- Whether a column belongs in a raw table or a derived table
- Whether a component should be a Server Component or a Client Component
- Which prompt template to use or how to structure the context object
- Whether a feature is in MVP scope or deferred to BACKLOG
- Whether a library version is compatible with the installed version
- How to handle a real API response that doesn't match the documented schema

**Frame your question like this:**
> "I need to [do X]. My current understanding is [Y]. I'm unsure about [Z specifically]. If I assume [Z=A] and proceed, the consequence is [C]. Do you want me to proceed with that assumption, or can you confirm?"

**Do not:**
- Write code that has a `TODO: figure out the right approach` comment
- Use `any` in TypeScript or `dict` in Python because the shape is unclear
- Call a third-party API endpoint speculatively to see what it returns — check the docs or ask first
- Commit code that you know is wrong because "it'll do for now"
- Make a architectural decision that affects multiple files without first confirming it

---

## SECTION 17 — Session Close Protocol

At the end of every session, before stopping, you must:

1. **State what was completed** — list the files created/modified, the features implemented, and the tests written
2. **Run the checklist** — run the relevant subset of the Section 14 checklist and report the results
3. **State what is broken or incomplete** — be specific; "the ingestion job runs but the AI enrichment step is not yet connected" is acceptable; leaving a silent bug is not
4. **State the next session's starting point** — the exact first task the next session should pick up
5. **Propose a skill** — if any pattern in this session (an integration approach, a data transformation, a test pattern) repeated or would benefit future sessions, propose creating a skill for it

---

*This file is a living document. If a requirement in this file conflicts with `docs/PRD.md`, the PRD wins. If a requirement in this file conflicts with `../master-project-prompt.md`, this file wins (project-specific overrides global). Update this file when requirements change — do not work around it.*

**Last updated:** 2026-06-12 (backend shipped: schema extensions §5.2, multi-provider AI §10) **|** **PRD version aligned:** 1.0