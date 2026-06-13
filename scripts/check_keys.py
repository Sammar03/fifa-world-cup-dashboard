"""Validate the configured API keys and confirm live response shapes.

Unlike the ingestion pipeline (which degrades silently on a bad key — a WARNING
that looks just like keyless mode), this script reports auth failures loudly and
prints status codes + parsed shapes so a wrong key or an empty competition is
obvious. Secrets are never printed.

Usage (repo root):  python scripts/check_keys.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.ingestion.schemas.football_data import (  # noqa: E402
    FDMatchesResponse,
    FDScorersResponse,
    FDStandingsResponse,
)

USER_AGENT = "WorldCupDashboard/1.0 (portfolio project)"


def _ok(label: str, msg: str) -> None:
    print(f"  OK    {label}: {msg}")


def _fail(label: str, msg: str) -> None:
    print(f"  FAIL  {label}: {msg}")


async def check_football_data() -> bool:
    settings = get_settings()
    key = settings.FOOTBALL_DATA_API_KEY
    print("football-data.org (X-Auth-Token header):")
    if not key or key == "your_key_here":
        _fail("key", "FOOTBALL_DATA_API_KEY not set")
        return False

    headers = {"X-Auth-Token": key, "User-Agent": USER_AGENT}
    base = settings.FOOTBALL_DATA_BASE_URL
    ok = True
    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        # matches
        try:
            r = await client.get(f"{base}/competitions/WC/matches", params={"status": "FINISHED"})
            if r.status_code == 403:
                _fail("matches", "403 — key rejected or WC not on this plan")
                return False
            r.raise_for_status()
            parsed = FDMatchesResponse.model_validate(r.json())
            _ok("matches", f"{r.status_code}, FINISHED matches={len(parsed.matches)} (boundary schema OK)")
        except (httpx.HTTPError, ValueError) as exc:
            _fail("matches", str(exc))
            ok = False

        await asyncio.sleep(7)  # 10 req/min limit
        try:
            r = await client.get(f"{base}/competitions/WC/standings")
            r.raise_for_status()
            parsed = FDStandingsResponse.model_validate(r.json())
            groups = len(parsed.standings)
            sample = parsed.standings[0].table[0] if groups and parsed.standings[0].table else None
            detail = f"first row tla={sample.team.tla} pts={sample.points}" if sample else "no rows yet"
            _ok("standings", f"{r.status_code}, groups={groups}, {detail}")
        except (httpx.HTTPError, ValueError) as exc:
            _fail("standings", str(exc))
            ok = False

        await asyncio.sleep(7)
        try:
            r = await client.get(f"{base}/competitions/WC/scorers", params={"limit": "5"})
            r.raise_for_status()
            parsed = FDScorersResponse.model_validate(r.json())
            top = parsed.scorers[0] if parsed.scorers else None
            detail = (
                f"top={top.player.name} goals={top.goals} assists={top.assists} "
                f"playedMatches={top.playedMatches} position={top.player.position}"
                if top
                else "no scorers yet"
            )
            _ok("scorers", f"{r.status_code}, count={len(parsed.scorers)}, {detail}")
        except (httpx.HTTPError, ValueError) as exc:
            _fail("scorers", str(exc))
            ok = False
    return ok


async def check_ai() -> bool:
    from app.ai import providers

    settings = get_settings()
    print(f"AI provider ({settings.AI_PROVIDER}, model={settings.AI_MODEL}):")
    if not providers.ai_available():
        _fail("key", "AI_API_KEY not set")
        return False
    try:
        result = await providers.complete(
            'Reply with exactly this JSON and nothing else: {"insight": "connection ok"}'
        )
        _ok(
            "completion",
            f"model={result.model} latency_ms={result.latency_ms} "
            f"in_tok={result.input_tokens} out_tok={result.output_tokens} "
            f"text={result.text.strip()[:80]!r}",
        )
        return True
    except providers.AIProviderError as exc:
        _fail("completion", str(exc))
        return False


async def main() -> None:
    fd_ok = await check_football_data()
    print()
    ai_ok = await check_ai()
    print()
    print(f"RESULT: football-data={'OK' if fd_ok else 'FAIL'}  AI={'OK' if ai_ok else 'FAIL'}")
    sys.exit(0 if (fd_ok and ai_ok) else 1)


if __name__ == "__main__":
    asyncio.run(main())
