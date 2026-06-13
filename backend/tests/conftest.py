"""Test environment: file-backed SQLite (async), scheduler disabled, no API
keys — importing the app can never fire an HTTP call. Env vars are set BEFORE
any app import so pydantic-settings picks them up over .env files."""

import os

os.environ.update(
    {
        "DATABASE_URL": "sqlite+aiosqlite:///./test_app.db",
        "INGEST_SECRET": "test-secret",
        "SCHEDULER_ENABLED": "false",
        "AI_API_KEY": "",
        "FOOTBALL_DATA_API_KEY": "",
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "WARNING",
    }
)

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app import models  # noqa: E402, F401 — register tables on Base.metadata
from app.database import Base, SessionLocal, engine  # noqa: E402


@pytest_asyncio.fixture()
async def db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db):
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
