"""Async SQLAlchemy engine + session factory (CLAUDE.md §2: SQLAlchemy 2.x async)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from app.db_url import prepare_database_url


class Base(DeclarativeBase):
    pass


# Normalize the URL so a managed-Postgres connection string (Neon: postgresql://
# …?sslmode=require) works with asyncpg, while local docker-compose URLs pass
# through unchanged. pool_pre_ping recycles connections a managed DB may have
# dropped (idle timeout / scale-to-zero wake).
_db_url, _connect_args = prepare_database_url(get_settings().DATABASE_URL)
engine = create_async_engine(_db_url, pool_pre_ping=True, connect_args=_connect_args)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
