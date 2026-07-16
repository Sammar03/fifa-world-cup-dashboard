#!/bin/sh
# Production entrypoint (Hugging Face Spaces / any Docker PaaS). Runs DB
# migrations, then serves the API. Binds ${PORT:-8000}; HF sets no PORT, so it
# listens on 8000 (matches app_port in README.md).
#
# NOTHING SLOW OR NETWORK-DEPENDENT BELONGS BEFORE `exec uvicorn`. The port is
# closed until then, so every second spent here is a connection timeout for any
# caller or uptime monitor. That window is what an outage looks like from
# outside.
#
# ponytail: seeding used to run here and no longer does. scripts/seed.py only
# owns fixtures.group_label / fixtures.round / teams.group_label (see upsert.py
# "Ownership rules"), that data lives in Postgres and survives restarts, and the
# scheduler re-fetches everything else within 3 s of startup anyway. Re-running
# it on every boot cost ~the whole boot window to write data that was already
# there. Run it by hand after a database rebuild:
#     python scripts/seed.py     (idempotent; safe to re-run)
# When club competitions land this becomes a low-frequency scheduled job next to
# the ingestion job, NOT a boot step — see CLUB_FOOTBALL_MIGRATION.md.
set -e

cd /app/backend

log() { echo ">> $(date -u +%H:%M:%S) $*"; }

# Retry migrations: a managed Postgres (Neon/Supabase) can be seconds away from a
# scale-to-zero wake, and bare `set -e` would turn that blip into an exit — which
# HF answers by restarting the container into the same blip, i.e. a crash-loop
# that presents as "Connection Timeout" until the DB happens to answer. Five
# tries buys ~25 s of tolerance; a genuinely broken migration still fails hard,
# because serving on an unmigrated schema is worse than not serving.
log "alembic upgrade head"
attempt=1
while true; do
  if alembic upgrade head; then
    break
  fi
  if [ "$attempt" -ge 5 ]; then
    log "alembic failed after $attempt attempts — giving up"
    exit 1
  fi
  log "alembic attempt $attempt failed; retrying in 5s"
  attempt=$((attempt + 1))
  sleep 5
done

log "starting uvicorn on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
