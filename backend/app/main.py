"""FastAPI application: router registration, CORS, rate limiting, scheduler
lifecycle (CLAUDE.md §3, §11).

Architecture (ADR-002): GET endpoints read PostgreSQL only. All third-party
calls (ESPN, football-data.org, LLM) happen in the APScheduler ingestion job —
never on the request path.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import get_settings
from app.ingestion.scheduler import start_scheduler, stop_scheduler
from app.routers import fixtures, health, ingest, query, scorers, standings, teams

settings = get_settings()

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
# httpx logs the full request URL (incl. any query params) at INFO. Keep it at
# WARNING so a URL can never carry a secret into the logs (defense in depth —
# all provider keys are sent as headers, never query params).
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SCHEDULER_ENABLED:
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="FIFA World Cup Intelligence Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting: 60 req/min per IP on all routes (CLAUDE.md §11).
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS: explicit origins only; cors_origins_list rejects "*" in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Ingest-Secret"],
)

app.include_router(health.router)
app.include_router(fixtures.router)
app.include_router(standings.router)
app.include_router(scorers.router)
app.include_router(teams.router)
app.include_router(query.router)
app.include_router(ingest.router)
