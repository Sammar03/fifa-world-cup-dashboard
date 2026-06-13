# Production image for Koyeb. Build context = repo ROOT (it needs both backend/
# and the root-level scripts/ for migrations + seeding).
#
# Local development uses backend/Dockerfile via docker-compose instead — that one
# has a narrower context (./backend) and a fixed port; do not point Koyeb at it.
FROM python:3.13-slim

WORKDIR /app

# Install deps first so the layer caches across code-only changes.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# App + migrations, and the root-level seed/start scripts.
COPY backend/ ./backend/
COPY scripts/ ./scripts/

RUN chmod +x /app/scripts/start.sh

# start.sh: alembic upgrade head -> seed (non-fatal) -> uvicorn on $PORT.
CMD ["/app/scripts/start.sh"]
