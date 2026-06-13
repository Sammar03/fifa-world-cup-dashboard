"""Normalize a libpq-style DATABASE_URL into an asyncpg-compatible (url, connect_args).

Managed Postgres providers (Neon, Supabase, Railway) emit URLs like
    postgresql://user:pass@host/db?sslmode=require&channel_binding=require
The asyncpg driver SQLAlchemy uses cannot parse the libpq-only query params
(sslmode, channel_binding) and needs the +asyncpg marker plus SSL supplied via
connect_args. This helper centralizes that translation so the app engine
(database.py) and Alembic (alembic/env.py) stay in lockstep — one source of truth.

Local docker-compose URLs (no sslmode) pass through unchanged with empty
connect_args.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def prepare_database_url(raw: str) -> tuple[str, dict]:
    parts = urlsplit(raw)

    # Only Postgres URLs need rewriting. Anything else (e.g. the test sqlite URL)
    # is returned byte-for-byte — reconstructing a netloc-less URL via urlunsplit
    # silently drops the `///`, so we never touch non-Postgres schemes.
    if parts.scheme not in ("postgres", "postgresql", "postgresql+asyncpg"):
        return raw, {}

    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)  # libpq-only; asyncpg errors on it

    connect_args: dict = {}
    if sslmode and sslmode != "disable":
        # asyncpg takes TLS via connect_args, not the URL. "require" encrypts
        # without local CA verification — correct for Neon/Supabase managed certs.
        connect_args["ssl"] = "require"

    cleaned = urlunsplit(
        ("postgresql+asyncpg", parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    return cleaned, connect_args
