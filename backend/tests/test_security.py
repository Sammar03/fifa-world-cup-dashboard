"""API security tests (CLAUDE.md §11) — no secret leakage, auth enforced,
input validated, errors don't expose internals.

The conftest configures sentinel secrets (INGEST_SECRET="test-secret",
DATABASE_URL with "sqlite"); these tests assert those values never appear in
any response. The live counterpart (scripts/security_probe.py) repeats the leak
scan against a running server using the REAL .env secret values.
"""

import pytest

# Public, unauthenticated read endpoints — none should ever expose a secret.
READ_ENDPOINTS = [
    "/health",
    "/fixtures",
    "/fixtures?status=live",
    "/standings",
    "/standings?group=A",
    "/scorers?sort=goals&limit=50",
]

# Substrings that must never appear in a response body or headers.
LEAK_MARKERS = ["test-secret", "sqlite", "password", "DATABASE_URL", "INGEST_SECRET"]


@pytest.mark.parametrize("path", READ_ENDPOINTS)
async def test_read_endpoints_do_not_leak_secrets(client, path):
    res = await client.get(path)
    assert res.status_code == 200
    blob = res.text + " " + " ".join(f"{k}:{v}" for k, v in res.headers.items())
    for marker in LEAK_MARKERS:
        assert marker not in blob, f"{marker!r} leaked in response from {path}"


async def test_health_does_not_expose_db_url_or_secrets(client):
    res = await client.get("/health")
    body = res.json()
    # Only the documented, non-sensitive fields are present.
    assert set(body).issubset(
        {"status", "db", "stale_tables", "ingestion_last_run", "version"}
    )
    assert "://" not in res.text  # no connection string of any kind


async def test_ingest_requires_secret_and_never_echoes_it(client):
    # Absent header → 401
    res = await client.post("/ingest")
    assert res.status_code == 401
    assert "test-secret" not in res.text

    # Wrong header → 401, and the expected secret is not revealed
    res = await client.post("/ingest", headers={"X-Ingest-Secret": "definitely-wrong"})
    assert res.status_code == 401
    assert "test-secret" not in res.text
    assert res.json()["detail"] == "Unauthorized"


async def test_query_rejects_oversized_input(client):
    res = await client.post("/query", json={"question": "x" * 501})
    assert res.status_code == 422
    assert "Traceback" not in res.text


async def test_query_rejects_html(client):
    res = await client.post("/query", json={"question": "<script>alert(1)</script>"})
    assert res.status_code == 422


async def test_query_valid_input_is_stub_not_error(client):
    res = await client.post("/query", json={"question": "Who is the top scorer?"})
    assert res.status_code == 501  # honest stub, not a 500


async def test_errors_do_not_leak_tracebacks(client):
    # 404 (unknown fixture) and 422 (bad path type) must return clean JSON.
    for path in ["/fixtures/999999", "/fixtures/not-an-int", "/teams/999999"]:
        res = await client.get(path)
        assert res.status_code in (404, 422)
        for marker in ("Traceback", 'File "', "sqlalchemy", "asyncpg", "/app/"):
            assert marker not in res.text, f"{marker!r} leaked from {path}"


async def test_unknown_route_is_404_without_internals(client):
    res = await client.get("/admin/secrets")
    assert res.status_code == 404
    assert "Traceback" not in res.text
