# Deployment Runbook

Free-tier, no-credit-card stack:

| Layer | Host | Why |
|---|---|---|
| Database | **Neon** (serverless Postgres) | Free 0.5 GB, no card, asyncpg-compatible |
| Backend API | **Koyeb** (Docker, git deploy) | Free, **always-on** (the in-process APScheduler ingestion would die on a sleeping host) |
| Frontend | **Vercel** | Free, native Next.js 15 |

Deploy order matters because of the URL dependencies:
**Neon → push to GitHub → Koyeb (get backend URL) → Vercel (get frontend URL) → set Koyeb `CORS_ORIGINS` to the Vercel URL.**

---

## 1. Neon — Postgres (do this first)

1. Sign up at <https://neon.tech> (GitHub login, **no card**).
2. **Create project** → pick the region closest to your Koyeb region (e.g. AWS `us-east-2` / EU `eu-central-1`). Postgres 16.
3. On the project dashboard, open **Connection string**:
   - **Turn OFF "Connection pooling"** so you get the **direct** host (the one *without* `-pooler` in the hostname). The direct endpoint avoids PgBouncer prepared-statement issues with asyncpg; one Koyeb instance with a small pool is well within its limits.
   - Copy the `postgresql://…?sslmode=require` string.
4. That whole string is your `DATABASE_URL`. The app rewrites it to `postgresql+asyncpg://…` and applies TLS automatically (`app/db_url.py`) — **paste it verbatim**, do not hand-edit the scheme.

> Migrations and a one-time idempotent seed run automatically on every backend boot (`scripts/start.sh`), so you do **not** run Alembic by hand against Neon.

---

## 2. Push to GitHub

From the repo root (`fifa-world-cup-dashboard/`):

```bash
git add -A
git commit -m "Add deploy config (Koyeb/Neon/Vercel)"
# Create an EMPTY repo at github.com/Sammar03 (no README), then:
git remote add origin https://github.com/Sammar03/fifa-world-cup-dashboard.git
git branch -M main
git push -u origin main
```

`.env` is gitignored — confirm it is **not** in the push (`git status` should never list it).

---

## 3. Koyeb — Backend API

1. Sign up at <https://app.koyeb.com> (GitHub login, **no card** on the free Starter plan).
2. **Create Web Service → GitHub** → authorize and pick `Sammar03/fifa-world-cup-dashboard`, branch `main`.
3. **Builder: Dockerfile.**
   - Dockerfile location: `Dockerfile` (the repo-root one — **not** `backend/Dockerfile`).
   - Work directory / build context: leave as repo root (default).
4. **Instance:** Free (`nano`). **Region:** same as Neon. **Min/Max scale:** 1 (keep it always-on for the scheduler).
5. **Port:** `8000` (Koyeb injects `$PORT`; `start.sh` honors it).
6. **Health check:** HTTP, path `/health`.
7. **Environment variables** (set these — see the table in §5):
   `DATABASE_URL`, `INGEST_SECRET`, `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`,
   `FOOTBALL_DATA_API_KEY`, `ENVIRONMENT=production`, `LOG_LEVEL=INFO`,
   `CORS_ORIGINS` (temporary placeholder for now — updated in §6).
8. **Deploy.** Watch the build logs for `alembic upgrade head` → `seed ok` → `Scheduler started` → `Uvicorn running`.
9. Copy the public app URL, e.g. `https://fifa-...koyeb.app`. Verify:
   `GET https://<app>.koyeb.app/health` → `200` with `"db":"ok"`.

---

## 4. Vercel — Frontend

1. Sign up at <https://vercel.com> (GitHub login, **no card**).
2. **Add New → Project →** import `Sammar03/fifa-world-cup-dashboard`.
3. **Root Directory: `frontend`** (critical — the Next.js app is a subfolder). Framework auto-detects as Next.js.
4. **Environment Variables:**
   - `NEXT_PUBLIC_USE_MOCKS` = `false`  ← without this the site serves mock data
   - `NEXT_PUBLIC_API_BASE_URL` = `https://<app>.koyeb.app`  (no trailing slash)
5. **Deploy.** Copy the production URL, e.g. `https://fifa-world-cup-dashboard.vercel.app`.

---

## 5. Environment variables reference

### Koyeb (backend)
| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon direct connection string (`postgresql://…?sslmode=require`) |
| `INGEST_SECRET` | a long random string (header for `POST /ingest`) |
| `AI_PROVIDER` | `groq` |
| `AI_MODEL` | `llama-3.3-70b-versatile` |
| `AI_API_KEY` | your Groq key |
| `FOOTBALL_DATA_API_KEY` | your football-data.org key |
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |
| `CORS_ORIGINS` | the Vercel URL **only** (set in §6); never `*` |

### Vercel (frontend)
| Variable | Value |
|---|---|
| `NEXT_PUBLIC_USE_MOCKS` | `false` |
| `NEXT_PUBLIC_API_BASE_URL` | `https://<app>.koyeb.app` |

---

## 6. Close the CORS loop

1. In Koyeb → service → **Environment**, set `CORS_ORIGINS` = the exact Vercel URL
   (e.g. `https://fifa-world-cup-dashboard.vercel.app`), no trailing slash.
2. Redeploy (env change triggers a fast redeploy).
3. Open the Vercel site → it should load live fixtures/standings/scorers from the
   Koyeb backend. Check the browser console for CORS errors (there should be none).

---

## 7. Post-deploy checklist (CLAUDE.md §14)

- [ ] `GET /health` → `200`, `"db":"ok"`
- [ ] Koyeb logs show `Scheduler started` and at least one `ingestion_run_complete`
- [ ] `POST /ingest` with no header → `401`
- [ ] All 5 Vercel routes load real data (`/`, `/standings`, `/scorers`, `/match/[id]`, `/team/[id]`)
- [ ] No secrets in any response (`BASE_URL=https://<app>.koyeb.app python scripts/security_probe.py`)
- [ ] `CORS_ORIGINS` is the Vercel URL only

---

## Notes / known follow-ups

- **Rate limiting behind a proxy:** slowapi keys on the client IP via
  `get_remote_address`, which behind Koyeb's edge may see the proxy IP, so the
  60/min limit can be shared across users. Fine for a portfolio demo; if it ever
  bites, key on `X-Forwarded-For`. (Tracked in BACKLOG.)
- **Seed is non-fatal at boot:** if ESPN/openfootball are briefly down during a
  deploy, the seed is skipped and the scheduler backfills fixtures within seconds;
  openfootball group labels arrive on the next successful seed/redeploy.
- **Local dev is unchanged:** `docker-compose.yml` still uses `backend/Dockerfile`
  (port 8000, context `./backend`). The root `Dockerfile` is deploy-only.
