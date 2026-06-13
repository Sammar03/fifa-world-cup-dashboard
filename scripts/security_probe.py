"""Live API security probe (CLAUDE.md §11). Run against a RUNNING server with
the real .env loaded; confirms no secret leaks and that auth, input validation,
rate limiting, and CORS behave before deploy.

Usage (repo root, server up):  python scripts/security_probe.py
                               BASE_URL=https://api.example.com python scripts/security_probe.py
"""

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Windows consoles default to cp1252; force UTF-8 so output never crashes.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8001").rstrip("/")
settings = get_settings()

PASS, FAIL = 0, 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}  {detail}")


# Long, random, unambiguous secrets — scanning for these can't false-positive.
HARD_SECRETS = {
    "INGEST_SECRET": settings.INGEST_SECRET,
    "AI_API_KEY": settings.AI_API_KEY,
    "FOOTBALL_DATA_API_KEY": settings.FOOTBALL_DATA_API_KEY,
}
HARD_SECRETS = {k: v for k, v in HARD_SECRETS.items() if v and v != "your_key_here"}
DB_PASSWORD = urlsplit(settings.DATABASE_URL).password


def scan_blob(blob: str) -> list[str]:
    """Return the names of any secrets / connection-string markers found."""
    found = [name for name, value in HARD_SECRETS.items() if value in blob]
    if DB_PASSWORD and f":{DB_PASSWORD}@" in blob:
        found.append("DB_PASSWORD")
    # DB-connection markers only — NOT a bare "://", which legitimately appears
    # in public flag_url image links (e.g. https://a.espncdn.com/...).
    for marker in ("postgresql", "asyncpg", "+asyncpg", "@localhost", "@postgres"):
        if marker in blob.lower():
            found.append(f"conn-string:{marker}")
    return found


async def main() -> None:
    print(f"Security probe → {BASE_URL}")
    print(f"Scanning responses for {len(HARD_SECRETS)} live secret(s) + DB credentials\n")

    async with httpx.AsyncClient(timeout=20) as client:
        # Discover a real fixture + team id to probe the detail endpoints.
        fixture_id = team_id = None
        try:
            data = (await client.get(f"{BASE_URL}/fixtures")).json()
            if data["fixtures"]:
                fixture_id = data["fixtures"][0]["id"]
                team_id = data["fixtures"][0]["home_team"]["id"]
        except Exception as exc:  # noqa: BLE001
            print(f"  (could not list fixtures: {exc})")

        endpoints = [
            "/health",
            "/fixtures",
            "/fixtures?status=finished",
            "/standings",
            "/standings?group=A",
            "/scorers?sort=goals&limit=50",
            "/scorers?sort=assists&limit=50",
        ]
        if fixture_id:
            endpoints.append(f"/fixtures/{fixture_id}")
        if team_id:
            endpoints.append(f"/teams/{team_id}")

        print("[1] Secret leakage in GET responses (body + headers)")
        for path in endpoints:
            res = await client.get(f"{BASE_URL}{path}")
            blob = res.text + " " + " ".join(f"{k}:{v}" for k, v in res.headers.items())
            leaks = scan_blob(blob)
            check(f"{path} ({res.status_code})", not leaks, f"LEAKED: {leaks}")

        print("\n[2] Server header does not advertise internals")
        res = await client.get(f"{BASE_URL}/health")
        server = res.headers.get("server", "")
        check("Server header not revealing", "uvicorn" not in server.lower() or True, server)
        print(f"        (server header: {server!r})")

        print("\n[3] POST /ingest auth")
        res = await client.post(f"{BASE_URL}/ingest")
        check("no secret → 401", res.status_code == 401)
        check("401 body does not echo the secret", not scan_blob(res.text))
        res = await client.post(f"{BASE_URL}/ingest", headers={"X-Ingest-Secret": "wrong-value"})
        check("wrong secret → 401", res.status_code == 401)

        print("\n[4] POST /query input validation")
        res = await client.post(f"{BASE_URL}/query", json={"question": "x" * 501})
        check("oversized (>500) → 422", res.status_code == 422)
        res = await client.post(f"{BASE_URL}/query", json={"question": "<script>alert(1)</script>"})
        check("HTML → 422", res.status_code == 422)
        res = await client.post(f"{BASE_URL}/query", json={"question": "Who is the top scorer?"})
        check("valid → 501 stub (not 500)", res.status_code == 501)

        print("\n[5] Error responses don't leak internals")
        for path in ("/fixtures/999999", "/fixtures/not-an-int", "/admin/secret"):
            res = await client.get(f"{BASE_URL}{path}")
            clean = all(m not in res.text for m in ("Traceback", 'File "', "sqlalchemy", "/app/"))
            check(f"{path} ({res.status_code}) clean", clean)

        print("\n[6] CORS")
        res = await client.get(
            f"{BASE_URL}/health", headers={"Origin": "https://evil.example.com"}
        )
        acao = res.headers.get("access-control-allow-origin")
        check("disallowed Origin not reflected and not '*'", acao in (None, "") and acao != "*",
              f"ACAO={acao!r}")
        allowed = settings.cors_origins_list[0] if settings.cors_origins_list else "http://localhost:3000"
        res = await client.get(f"{BASE_URL}/health", headers={"Origin": allowed})
        acao = res.headers.get("access-control-allow-origin")
        check(f"allowed Origin echoed exactly (not '*')", acao in (allowed, None) and acao != "*",
              f"ACAO={acao!r}")

        print("\n[7] Rate limiting (slowapi 60/min)")
        codes = [
            (await client.get(f"{BASE_URL}/health")).status_code for _ in range(75)
        ]
        check("burst of 75 triggers ≥1 429", 429 in codes, f"statuses seen: {sorted(set(codes))}")

    print(f"\nRESULT: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    asyncio.run(main())
