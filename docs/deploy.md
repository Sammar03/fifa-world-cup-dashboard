# Deployment Runbook

Free-tier, no-credit-card stack:

| Layer | Host | Why |
|---|---|---|
| Database | **Neon** (serverless Postgres) | Free 0.5 GB, no card, asyncpg-compatible |
| Backend API | **Render** (Docker, free web service) | No card; deploys our GitHub repo + root `Dockerfile`. Sleeps on idle → kept awake by a free uptime pinger |
| Keep-alive | **UptimeRobot** or **cron-job.org** | No card; pings `/health` every ~10 min so Render never sleeps and the in-process scheduler keeps running |
| Frontend | **Vercel** | Free, native Next.js 15 |

> Koyeb was the original pick but now requires a card at org creation, so we moved
> to Render. Render's free Postgres expires in 90 days — irrelevant to us because
> the database is Neon, not Render.

Deploy order (URL dependencies):
**Neon → push to GitHub → Render (get backend URL) → keep-alive pinger → Vercel (get frontend URL) → set Render `CORS_ORIGINS` to the Vercel URL.**

---

## 1. Neon — Postgres (do this first)

1. Sign up at <https://neon.tech> (GitHub login, **no card**).
2. **Create project** → pick a region close to the Render region you'll choose in §3
   (e.g. AWS `us-east` ↔ Render `virginia`). Postgres 16.
3. Open **Connection string**:
   - **Turn OFF "Connection pooling"** → use the **direct** host (no `-pooler` in the
     hostname). Avoids PgBouncer prepared-statement issues with asyncpg.
   - Copy the `postgresql://…?sslmode=require` string.
4. That whole string is `DATABASE_URL`. The app rewrites it to `postgresql+asyncpg://…`
   and applies TLS automatically (`backend/app/db_url.py`) — **paste it verbatim**.

> Migrations + a one-time idempotent seed run automatically on every backend boot
> (`scripts/start.sh`), so you never run Alembic by hand against Neon.

---

## 2. Push to GitHub  ✅ done

Repo: <https://github.com/Sammar03/fifa-world-cup-dashboard> (branch `main`).
`.env` is gitignored and was never pushed.

---

## 3. Render — Backend API

**Blueprint flow (recommended — reads `render.yaml`):**

1. Sign up at <https://render.com> (GitHub login, **no card**).
2. **New → Blueprint** → connect `Sammar03/fifa-world-cup-dashboard` (branch `main`).
   Render detects `render.yaml` and shows the `fifa-world-cup-api` Docker web service.
3. It will prompt for the `sync: false` values — fill them in:
   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Neon **direct** string (`postgresql://…?sslmode=require`) |
   | `INGEST_SECRET` | copy from your local `.env` |
   | `AI_API_KEY` | your Groq key (from `.env`) |
   | `FOOTBALL_DATA_API_KEY` | from `.env` |
   | `CORS_ORIGINS` | `https://temp.placeholder.app` (temporary — real Vercel URL set in §6) |
   (`AI_PROVIDER`, `AI_MODEL`, `ENVIRONMENT=production`, `LOG_LEVEL` are baked into the blueprint.)
4. **Region:** if you want a different region than the blueprint's `virginia`, edit it
   in `render.yaml` (or in the dashboard) to sit near your Neon region.
5. **Apply / Create.** Watch the logs for:
   `alembic upgrade head` → `seed ok` (or "seed skipped") → `Scheduler started` → `Uvicorn running`.
6. Copy the public URL, e.g. `https://fifa-world-cup-api.onrender.com`. Verify:
   `GET …/health` → `200`, `"db":"ok"`.

**Manual flow (if you skip the blueprint):** New → **Web Service** → connect the repo →
Runtime **Docker**, Dockerfile path `./Dockerfile`, **Plan: Free**, Health check path
`/health`, then add the env vars from §5.

> Render injects `$PORT` (≈10000); `start.sh` binds to it (`--host 0.0.0.0`). Nothing to configure.

---

## 4. Keep-alive (so Render doesn't sleep)

Render free web services sleep after 15 min idle (30–60 s cold start), which would
pause the in-process ingestion scheduler. Keep it awake with a free, no-card pinger:

- **UptimeRobot** (<https://uptimerobot.com>, no card): New monitor → **HTTP(s)** →
  URL `https://<service>.onrender.com/health` → interval **5–10 min**.
- *or* **cron-job.org** (no card): new cronjob → same URL → every 10 min.

One always-awake free service uses ≈720 h/month, within Render's 750 h free allowance.

---

## 5. Vercel — Frontend

1. Sign up at <https://vercel.com> (GitHub login, **no card**).
2. **Add New → Project** → import `Sammar03/fifa-world-cup-dashboard`.
3. **Root Directory: `frontend`** (critical — the Next.js app is a subfolder).
4. **Environment Variables:**
   - `NEXT_PUBLIC_USE_MOCKS` = `false`  ← without this the site serves mock data
   - `NEXT_PUBLIC_API_BASE_URL` = `https://<service>.onrender.com` (no trailing slash)
5. **Deploy.** Copy the production URL, e.g. `https://fifa-world-cup-dashboard.vercel.app`.

---

## 6. Close the CORS loop

1. Render → service → **Environment** → set `CORS_ORIGINS` = the exact Vercel URL
   (no trailing slash, never `*`). Save → Render redeploys.
2. Open the Vercel site → live fixtures/standings/scorers should load from Render.
   Browser console should show no CORS errors.

---

## 7. Env vars reference

### Render (backend)
| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon direct string (`postgresql://…?sslmode=require`) |
| `INGEST_SECRET` | long random string (`POST /ingest` header) |
| `AI_PROVIDER` | `groq` |
| `AI_MODEL` | `llama-3.3-70b-versatile` |
| `AI_API_KEY` | your Groq key |
| `FOOTBALL_DATA_API_KEY` | your football-data.org key |
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |
| `CORS_ORIGINS` | the Vercel URL only; never `*` |

### Vercel (frontend)
| Variable | Value |
|---|---|
| `NEXT_PUBLIC_USE_MOCKS` | `false` |
| `NEXT_PUBLIC_API_BASE_URL` | `https://<service>.onrender.com` |

---

## 8. Post-deploy checklist (CLAUDE.md §14)

- [ ] `GET /health` → `200`, `"db":"ok"`
- [ ] Render logs show `Scheduler started` and at least one `ingestion_run_complete`
- [ ] Keep-alive monitor is green (no sleeps)
- [ ] `POST /ingest` with no header → `401`
- [ ] All 5 Vercel routes load real data (`/`, `/standings`, `/scorers`, `/match/[id]`, `/team/[id]`)
- [ ] No secrets in any response (`BASE_URL=https://<service>.onrender.com python scripts/security_probe.py`)
- [ ] `CORS_ORIGINS` is the Vercel URL only

---

## Notes / known follow-ups

- **First request after a deploy** (or any lapse in the pinger) is a 30–60 s cold
  start while Render wakes the service; steady-state is fast once the pinger holds it open.
- **Rate limiting behind a proxy** (DEBT-009): slowapi keys on the client IP via
  `get_remote_address`, which behind Render's proxy may see the proxy IP, so the
  60/min limit can be shared across clients. Fine for a portfolio demo; key on
  `X-Forwarded-For` if it ever bites.
- **Seed is non-fatal at boot:** if ESPN/openfootball are briefly down during a
  deploy, the seed is skipped and the scheduler backfills within seconds; openfootball
  group labels arrive on the next successful seed/redeploy.
- **Local dev is unchanged:** `docker-compose.yml` still uses `backend/Dockerfile`
  (port 8000). The root `Dockerfile` + `render.yaml` are deploy-only.
