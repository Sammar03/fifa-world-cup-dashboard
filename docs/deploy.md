# Deployment Runbook

Free-tier, **no-credit-card** stack:

| Layer | Host | Why |
|---|---|---|
| Database | **Neon** (serverless Postgres) | Free 0.5 GB, no card, asyncpg-compatible |
| Backend API | **Hugging Face Spaces** (Docker SDK, CPU Basic) | No card (card is only for PRO/GPU), runs our Dockerfile, outbound HTTPS allowed |
| Keep-alive | **UptimeRobot** or **cron-job.org** | No card; pings `/health` every ~10 min so the Space stays awake and the scheduler keeps running |
| Frontend | **Vercel** | Free, no card, native Next.js 15 |

> **Why not Koyeb/Render/Fly/Railway?** All now require a credit card for identity
> verification even on their free tiers. Hugging Face's paywall is for GPUs, not for
> running a CPU Docker container — so a free CPU "Basic" Space needs no card.

Deploy order (URL dependencies):
**Neon → push to GitHub → HF Space (get backend URL) → keep-alive → Vercel (get frontend URL) → set HF `CORS_ORIGINS` to the Vercel URL.**

---

## 1. Neon — Postgres (done)

You already created the Neon project. You need the **direct** connection string
(Connection pooling **OFF** → host has no `-pooler`): `postgresql://…?sslmode=require`.
That whole string is `DATABASE_URL`; the app rewrites it to `postgresql+asyncpg://…`
with TLS automatically (`backend/app/db_url.py`) — paste it verbatim.

> Migrations + a one-time idempotent seed run automatically on every backend boot
> (`scripts/start.sh`) — you never run Alembic by hand.

---

## 2. GitHub (done)

Repo: <https://github.com/Sammar03/fifa-world-cup-dashboard> (branch `main`).
`.env` was never pushed.

---

## 3. Hugging Face Space — Backend API

### 3a. Create the Space
1. Sign up at <https://huggingface.co/join> (**no card**).
2. **New → Space**: Owner `Sammar03`, name `fifa-world-cup-api`,
   **SDK = Docker** (blank template), **Hardware = CPU basic (free)**,
   visibility Public.
3. Create it. HF makes an empty Space repo at
   `https://huggingface.co/spaces/Sammar03/fifa-world-cup-api`.

### 3b. Push our code into the Space
HF Spaces are their own git repos. Push our repo into it (run from the project root).
Authenticate with your **HF username + an access token** (create one at
<https://huggingface.co/settings/tokens> → "Write" role; use it as the git password).

```bash
git remote add hf https://huggingface.co/spaces/Sammar03/fifa-world-cup-api
git push --force hf main          # --force overwrites HF's auto-created README
```

The `README.md` YAML frontmatter (`sdk: docker`, `app_port: 8000`) tells HF to build
the root `Dockerfile` and route traffic to port 8000.

### 3c. Set the secrets (Space → Settings → Variables and secrets)
Add these as **Secrets** (not public variables):

| Secret | Value |
|---|---|
| `DATABASE_URL` | Neon direct string (`postgresql://…?sslmode=require`) |
| `INGEST_SECRET` | copy from your local `.env` |
| `AI_API_KEY` | your Groq key (from `.env`) |
| `FOOTBALL_DATA_API_KEY` | from `.env` |
| `CORS_ORIGINS` | `https://temp.placeholder.app` (temporary — real Vercel URL in §6) |

Add these as **Variables** (non-secret):

| Variable | Value |
|---|---|
| `AI_PROVIDER` | `groq` |
| `AI_MODEL` | `llama-3.3-70b-versatile` |
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |

Saving secrets restarts the Space. Watch **Logs** for:
`alembic upgrade head` → `seed ok` (or "seed skipped") → `Scheduler started` → `Uvicorn running`.

### 3d. Get the API URL
The Space's API base URL is `https://sammar03-fifa-world-cup-api.hf.space`
(shown under the Space's "Embed this Space" / app URL). Verify:
`GET https://sammar03-fifa-world-cup-api.hf.space/health` → `200`, `"db":"ok"`.

---

## 4. Keep-alive (so the Space doesn't sleep)

Free Spaces sleep after inactivity, which would pause the ingestion scheduler.
Keep it awake with a free, no-card pinger on `/health`:

- **UptimeRobot** (<https://uptimerobot.com>, no card): New monitor → HTTP(s) →
  `https://sammar03-fifa-world-cup-api.hf.space/health` → interval 5–10 min.
- *or* **cron-job.org** (no card): new cronjob, same URL, every 10 min.

---

## 5. Vercel — Frontend

1. Sign up at <https://vercel.com> (GitHub login, **no card**).
2. **Add New → Project** → import `Sammar03/fifa-world-cup-dashboard`.
3. **Root Directory: `frontend`** (critical — the Next.js app is a subfolder).
4. **Environment Variables:**
   - `NEXT_PUBLIC_USE_MOCKS` = `false`  ← without this the site serves mock data
   - `NEXT_PUBLIC_API_BASE_URL` = `https://sammar03-fifa-world-cup-api.hf.space` (no trailing slash)
5. **Deploy.** Copy the production URL, e.g. `https://fifa-world-cup-dashboard.vercel.app`.

---

## 6. Close the CORS loop

1. HF Space → Settings → edit the `CORS_ORIGINS` secret = the exact Vercel URL
   (no trailing slash, never `*`). The Space restarts.
2. Open the Vercel site → live data should load from the HF backend; no CORS errors
   in the browser console.

---

## 7. Env vars reference

### Hugging Face Space (backend)
`DATABASE_URL`, `INGEST_SECRET`, `AI_API_KEY`, `FOOTBALL_DATA_API_KEY`, `CORS_ORIGINS`
(secrets) · `AI_PROVIDER=groq`, `AI_MODEL=llama-3.3-70b-versatile`,
`ENVIRONMENT=production`, `LOG_LEVEL=INFO` (variables).

### Vercel (frontend)
`NEXT_PUBLIC_USE_MOCKS=false` · `NEXT_PUBLIC_API_BASE_URL=https://sammar03-fifa-world-cup-api.hf.space`

---

## 8. Post-deploy checklist (CLAUDE.md §14)

- [ ] `GET /health` → `200`, `"db":"ok"`
- [ ] Space logs show `Scheduler started` and at least one `ingestion_run_complete`
- [ ] Keep-alive monitor green
- [ ] `POST /ingest` with no header → `401`
- [ ] All 5 Vercel routes load real data (`/`, `/standings`, `/scorers`, `/match/[id]`, `/team/[id]`)
- [ ] No secrets in any response (`BASE_URL=https://sammar03-fifa-world-cup-api.hf.space python scripts/security_probe.py`)
- [ ] `CORS_ORIGINS` is the Vercel URL only

---

## Notes / known follow-ups

- **Keeping GitHub and HF in sync:** the backend rarely changes, so re-push manually
  (`git push hf main`) when it does. Optional: add a GitHub Action that pushes to HF on
  each commit (needs an `HF_TOKEN` repo secret).
- **First request after a sleep** is a cold start while HF wakes the Space; the
  keep-alive avoids this in steady state.
- **Rate limiting behind a proxy** (DEBT-009): slowapi keys on the client IP via
  `get_remote_address`, which behind HF's proxy may see the proxy IP. Fine for a demo;
  key on `X-Forwarded-For` if needed.
- **Seed is non-fatal at boot:** a brief ESPN/openfootball outage just skips the seed;
  the scheduler backfills within seconds and group labels arrive on the next seed.
- **Local dev is unchanged:** `docker-compose.yml` still uses `backend/Dockerfile`
  (port 8000). The root `Dockerfile` is the deploy image.
