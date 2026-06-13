#!/bin/sh
# Production entrypoint (Hugging Face Spaces / any Docker PaaS). Runs DB
# migrations, seeds once (idempotent), then serves the API. Binds ${PORT:-8000};
# HF sets no PORT, so it listens on 8000 (matches app_port in README.md).
#
# Seeding is deliberately NON-FATAL: scripts/seed.py raises SystemExit if ESPN /
# openfootball are momentarily unreachable, and we must never let a transient
# upstream outage block the whole backend from booting. The in-process scheduler
# re-fetches fixtures within seconds of startup regardless, so a skipped seed
# self-heals (it only adds openfootball group labels on top of ESPN data).
set -e

cd /app/backend

echo ">> alembic upgrade head"
alembic upgrade head

echo ">> seed (idempotent; non-fatal)"
if python /app/scripts/seed.py; then
  echo ">> seed ok"
else
  echo ">> seed skipped (upstream unavailable) — scheduler will populate fixtures"
fi

echo ">> starting uvicorn on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
