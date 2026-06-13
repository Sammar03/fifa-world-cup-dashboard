# Production image for Hugging Face Spaces (Docker SDK) / any Docker PaaS.
# Build context = repo ROOT (it needs both backend/ and the root-level scripts/
# for migrations + seeding).
#
# Local development uses backend/Dockerfile via docker-compose instead — that one
# has a narrower context (./backend) and a fixed port; do not point HF at it.
FROM python:3.13-slim

WORKDIR /app

# Install deps first so the layer caches across code-only changes.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# App + migrations, and the root-level seed/start scripts.
COPY backend/ ./backend/
COPY scripts/ ./scripts/

RUN chmod +x /app/scripts/start.sh

# HF Spaces routes to this port (matches app_port in README.md); start.sh binds
# ${PORT:-8000}, and HF sets no PORT, so it listens on 8000.
EXPOSE 8000

# start.sh: alembic upgrade head -> seed (non-fatal) -> uvicorn on $PORT.
CMD ["/app/scripts/start.sh"]
