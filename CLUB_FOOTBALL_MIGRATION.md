# Club Football Migration — Known Hurdles

Written 2026-07-15, while the World Cup is still running (final: 2026-07-19).

**Purpose.** This project is currently a single-tournament app: every table, query,
endpoint, and page silently assumes "the 2026 World Cup" is the only competition
that exists. Moving to club football breaks that assumption in a lot of places,
some of them non-obvious. This file records every one found in a full sweep of the
codebase so the work can be picked up cold later.

Nothing here is a bug today. These are all *correct* choices for a 104-match
tournament that stop being correct for continuous multi-competition football.

Scale change to keep in mind throughout: **104 fixtures / ~112 teams / one
competition / ~5 weeks** becomes roughly **2,000+ fixtures / ~100 clubs /
many competitions / a 10-month season that never fully stops**. Most items below
are some version of "this was O(everything) and everything used to be small".

---

## 1. The root cause: there is no Competition or Season

Everything else in this document descends from this. There is no `Competition`
entity and no `Season` entity. `Fixture` has no `competition_id`
(`backend/app/models/entities.py:46-81`), so a Premier League match and an FA Cup
match are indistinguishable rows.

The migration is: add `Competition` and `Season`, hang `Fixture`, `Standing`,
`ScorerStat` off them, and backfill the World Cup as competition #1. Almost
everything below is downstream of that one change.

**Decision to make:** backfill the WC as competition #1 (keeps the finished
tournament as a live showcase, and "migrated a single-tournament schema to
multi-competition without data loss" is a good story) vs. archive it and start
clean. Recommend the former.

---

## 2. Hard schema blockers

These are `UNIQUE` constraints that make correct club data *impossible to insert*,
not merely awkward. All in `backend/app/models/entities.py`.

| Line | What | Why it breaks |
|---|---|---|
| 141 | `Standing.team_id` is `unique=True` | One standings row per team, ever. A club is in the league **and** a domestic cup **and** Europe simultaneously, and needs a row per competition per season. |
| 159 | `ScorerStat.player_id` is `unique=True` | One scorer row per player, ever. League goals and Champions League goals are different numbers and both must exist. |
| 142 | `Standing.group_label` is `nullable=False` | Clubs in a league table have no group. Needs to become nullable (cups still use groups). |
| 28 | `Team.group_label` | A World Cup concept — a nation is in exactly one group. A club has no single group; the column becomes meaningless and must move to a per-competition join. |
| 25 | `Team.external_id` unique (global) | Fine *if* one provider stays the id authority. Revisit if teams get sourced per-competition. |
| 56 | `Fixture.external_id` unique (global) | Same. ESPN event ids should stay globally unique across leagues — **verify** rather than assume. |

Also: `Fixture` has no `season_id`. Without one, the same two clubs playing the
same fixture in consecutive seasons cannot be distinguished except by kickoff date.

---

## 3. Standings are structurally World-Cup-only

`backend/app/ingestion/aggregator.py` — this is the most damaged subsystem.

- **Line 214:** `select(Team).where(Team.group_label.is_not(None))` — standings are
  computed **only for teams that have a group label**. Clubs have no group, so as
  written, club football produces *zero* standings rows. Not a degradation — a
  blank page.
- **Lines 219-231:** the finished-fixtures query has **no competition filter**. Every
  finished fixture a team has ever played is fed into one table. A club's league
  matches, cup matches, and European matches would all pile into a single standings
  row. Fundamentally wrong output, silently.
- **Line 245:** `await session.execute(delete(Standing))` — every standings row on
  the planet is deleted and rebuilt **every 60 seconds**. At 104 fixtures this is
  free. Across multiple competitions and a full season it is a pointless full
  rebuild of thousands of rows every minute.
- **Line 325:** `delete(ScorerStat)` — identical problem for scorers.
- **Lines 97-100:** `fifa_sort_key` hardcodes the FIFA 2026 tiebreaker
  (points → GD → goals for → name). **Club tiebreakers differ per competition** —
  Premier League and Bundesliga use goal difference, while La Liga and Serie A use
  head-to-head record first. This has to become per-competition, and head-to-head
  needs the fixture list, not just the totals, so `compute_standings` signature
  changes.
- **Lines 264-282:** the football-data standings cross-check assumes competition
  `WC`. Needs the competition code threaded through.

**The tiebreaker work is the genuinely hard part of this section** — head-to-head is
real domain logic, not a rename. Everything else is scoping.

---

## 4. Ingestion assumptions that die

`backend/app/ingestion/scheduler.py`

- **Lines 47-56 — `_scoreboard_window`.** Spans min-to-max kickoff across *all*
  fixtures, because (per its own comment) one ESPN call covers the whole
  tournament. Over a 10-month season that window becomes ~300 days and the trick
  collapses — `limit=200` cannot return a season.
  **The fix is a simplification:** poll *today ± 1 day* per competition, not the
  whole fixture list. Do not port the window logic forward; delete it.
- **Line 44 — `SUMMARY_CALL_CAP = 5`.** Works when one match happens at a time. A
  Saturday with ten Premier League matches kicking off simultaneously exceeds this
  immediately, and live matches are prioritised first
  (`_summary_targets`, lines 59-84), so finished matches would starve indefinitely
  behind a permanent backlog of live ones.
- **Lines 95-119 — `run_ingestion`.** Single-competition by construction: one
  scoreboard call, one football-data competition. Becomes a loop over active
  competitions, which multiplies every call budget below.
- **Lines 121-123.** Three football-data calls per run, spaced 7 s
  (`fetcher.py:30`). Per competition, that is 21 s of sleeping alone. With N
  competitions this serialises into minutes per run. Needs to move to a slower,
  separate cadence than the live scoreboard poll.

`backend/app/reconciliation/checker.py`

- **Lines 74-78:** loads **every** finished fixture and re-verifies it, every run,
  forever. At 104 fixtures, fine. Across a season this re-checks thousands of
  settled matches every 60 s to confirm what it already confirmed. Needs a
  "verify once, then leave it alone" gate (the `summary_synced_at` pattern at
  `entities.py:78` is the model to copy).
- **Lines 88-100:** joins football-data to our fixtures on the unordered pair of
  3-letter team codes (TLA) + a 24-hour window. Across many leagues, **TLA
  collisions become likely** and the 24 h window is wide enough for two legs of a
  tie to overlap. Needs to be competition-scoped at minimum, ideally id-based via
  `ExternalIdMap`.
- **Lines 102-105:** any fixture football-data doesn't cover is marked
  `verified = False`. Since the free tier only covers roughly a dozen competitions,
  **most club fixtures would have no counterpart and would sit permanently
  unverified** — turning the `verified` trust indicator red across the whole UI and
  destroying its meaning. Needs a third state: "not cross-checkable" ≠ "disputed".

---

## 5. Data sources

- **openfootball `worldcup.json` is dead for clubs.** `config.py:34` points at the
  World Cup file, and `scripts/seed.py` is written entirely around its shape
  (placeholder tokens `W101`/`1A`, group letters, the `OPENFOOTBALL_TO_ESPN_NAME`
  table at lines 46-52, the `_WINNER_ROUNDS` bracket map at lines 57-62). openfootball
  has per-league repos, but the schema differs per repo and their freshness varies.
  **Assume the entire seed is rewritten, not adapted.**
- **ESPN is the good news.** Per-league endpoints (`soccer/eng.1`, `soccer/esp.1`,
  `soccer/uefa.champions`, …) return the *same shape* as `fifa.world`, so the
  Pydantic schemas in `ingestion/schemas/espn.py` and the normalizer should survive
  intact. But `ESPN_API_BASE_URL` (`config.py:23`) is a **single scalar with
  `fifa.world` baked into it** — it must become per-competition.
  **Verify the shape on a real league endpoint before trusting this** (the
  `verify-api-shape` skill exists for exactly this, and the ESPN status-id
  deviation already documented in README.md "Operational notes" is proof this API
  does not match its docs).
- **football-data.org competition code `WC` is hardcoded in three places:**
  `fetcher.py:124`, `:138`, `:152`. Free tier is 10 req/min (`fetcher.py:30`) across
  roughly a dozen competitions — **confirm the current free-tier competition list
  before designing around it.** This is the binding constraint on how many
  competitions can be cross-checked at all.
- **No fixture-change feed.** Club football reschedules matches constantly
  (weather, cup progression, TV). Nothing currently handles a fixture whose kickoff
  moves or which is abandoned/replayed. The WC never needed it.

---

## 6. Player identity — the sleeper problem

`aggregator.py` matches players **by name string**: `_name_key` (line 353),
`_token_key` (line 357), `_lookup_by_name` (line 364), and
`_get_or_create_player` (line 571) which falls back to `external_id = name-{key}`.

This is a reasonable heuristic for ~700 World Cup players. Club football has tens
of thousands, and **name collisions stop being edge cases and become certainties**
(multiple players named "Rodrigo", "Danny Ward", "Sergio Rico"). Two different
players will silently merge into one scorer row.

Compounding it:
- `Player.team_id` (`entities.py:40`) is a single team, but **players transfer
  mid-season**. Stats need attributing per competition/season, and a transfer must
  not retroactively move a player's past goals to their new club.
- `Goal.player_name` / `Goal.assist_player_name` (`entities.py:113,116`) are
  denormalised strings, by design (ESPN gives display names, not stable ids).
  Same collision exposure.
- `Goal`'s unique constraint is `(fixture_id, player_name, minute, type)`
  (`entities.py:106`) — name-keyed, so it inherits the problem.

**This needs a real player-identity strategy** (stable provider ids + an alias
table via `ExternalIdMap`) before club scorer boards can be trusted. Probably the
second-hardest item in this document after tiebreakers.

---

## 7. API and frontend

- `routers/standings.py:20` — `GROUPS = [A..L]` hardcoded; line 32 returns
  `422 "group must be A–L"`. Needs a `competition` parameter instead of / alongside
  `group`.
- `routers/standings.py:64-73` — the FIFA tiebreaker is **duplicated here**,
  separately from `aggregator.fifa_sort_key`. Two copies of a rule that is about to
  become per-competition. Consolidate to one home during the migration.
- `routers/standings.py:41` — `all_team_forms(session)` runs on **every
  `/standings` request** and scans every finished fixture in the database
  (`aggregator.py:141-168`). At 104 fixtures this is invisible; at season scale it
  is a full table scan per request. Also mixes competitions into one form string.
- `routers/standings.py:75-78` — `updated_at` is taken from an arbitrary single
  row (`select(...).limit(1)`), which only works because all rows are rebuilt
  together. Breaks once standings are updated per competition.
- **No competition anywhere in the URL structure** — `src/app/standings/page.tsx`,
  `src/app/page.tsx`, etc. Needs competition-scoped routes.
- `src/components/team-flag.tsx` + `Team.flag_url` (`entities.py:29`) — **country
  flags, not club crests.** Rename and re-source; clubs need badges, and there is no
  keyless equivalent of a flag CDN.
- `src/components/standings-view.tsx` / `standings-table.tsx` are built around
  group tables (A–L), not a single long league ladder with promotion/relegation
  zones. Real design work, not a rename.
- Nothing in the UI expresses "which competition am I looking at" — that is a
  navigation/IA change, not just a component change.

---

## 8. Cost, infra, and operations

- **AI insight volume.** `AIInsight` is unique on `(fixture_id, state)`
  (`entities.py:172-175`), i.e. 2 per fixture. World Cup: ~208 insights, ever.
  A season across a few leagues: **4,000+**. `GENERATION_CAP_PER_RUN = 8`
  (`ai/insights.py:33`) and `AI_DAILY_BUDGET_USD = 2.00` (`config.py:43`) were sized
  for the former. Re-size both, and expect insights to become a *selective* feature
  (big matches only) rather than universal.
- **`ai/budget.py` is process-local** (see its lines 6-7) and explicitly assumes a
  single process/scheduler. Still true today. It stops being true the moment this
  runs more than one replica — which multi-competition load might force.
- **The HF free tier is a permanent tax.** Free CPU Spaces sleep on inactivity and
  get restarted by HF without notice. Every restart is a cold boot with the port
  closed. This caused the 2026-07-15 "Connection Timeout" incident. Boot is now
  lean (see `scripts/start.sh` — seeding removed, alembic retries), but if club
  football means real uptime expectations, the free tier is the wrong home.
- **Postgres scale-to-zero.** `database.py:19` notes `pool_pre_ping` exists for
  scale-to-zero wake. Fine now; a continuous ingest across many competitions may
  simply keep the DB awake permanently, which changes the free-tier maths.
- **The seed's resting place is a scheduled job, not a boot step and not a manual
  chore.** It was removed from the boot path on 2026-07-15 (`scripts/start.sh`).
  For the WC that is fine because the fixture list is static and already seeded.
  Club football has *continuously arriving* fixtures (new seasons, cup draws,
  rescheduling), so reference-data refresh must become a **low-frequency scheduled
  job** (daily-ish) alongside the existing 60 s ingestion job. The two-tier split is
  the right architecture and already half-built:
  - **slow tier (seed):** which fixtures exist, competition, round, group labels
  - **fast tier (ingestion):** scores, status, minute, stats, lineups

  The ownership rules at `ingestion/upsert.py:8-10` already encode this boundary —
  keep them.

---

## 9. Tests

`backend/tests/` (24 tests) — fixtures and assertions are built on World Cup
shapes (groups A–L, the FIFA tiebreaker, a single competition). `test_aggregator.py`
in particular tests `compute_standings` against group semantics. Expect to rewrite
rather than extend, and note `pytest.ini`/`test_app.db` run against SQLite while
production is Postgres (`upsert.py:4-5`) — the `Computed` column on
`Standing.goal_diff` (`entities.py:149`) and any new constraint work should be
checked on both.

---

## 10. Suggested sequencing

Rough order, cheapest-risk first. Not a commitment.

1. **Add `Competition` + `Season`; backfill WC as competition #1.** One migration,
   no behaviour change. Everything else depends on it.
2. **Drop the two killer unique constraints** (`Standing.team_id`,
   `ScorerStat.player_id`), replace with composite uniques including
   competition/season.
3. **Scope the aggregator** per competition; kill the global `delete()` rebuilds.
4. **Make tiebreakers per-competition** (this is where the real domain work is).
5. **Replace `_scoreboard_window`** with a today±1 per-competition poll; re-budget
   `SUMMARY_CALL_CAP`.
6. **Player identity** — stable ids + aliases before trusting any club scorer board.
7. **Reconciliation:** verify-once gate, competition scoping, third "not
   cross-checkable" state.
8. **New seed** for club reference data, as a scheduled job.
9. **Frontend:** competition routing, crests, league-ladder tables.

---

## 11. Open questions

- Which competitions, and how many at launch? (Everything above scales with N.)
- Backfill the World Cup, or archive it?
- Does the `verified` two-source promise survive club football at all, given
  football-data's free-tier coverage? If most fixtures can't be cross-checked, is
  the feature honest? Consider scoping the promise to covered competitions and
  saying so in the UI.
- Are AI insights universal or selective once there are thousands of matches?
- Does this stay on free HF + free Postgres + free football-data, and is that
  compatible with the uptime the club use case implies?
