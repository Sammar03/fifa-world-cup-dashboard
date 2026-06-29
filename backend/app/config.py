"""Application settings, validated at startup via pydantic-settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # The canonical .env lives at the repo root; "../.env" covers processes whose
    # working directory is backend/ (alembic, uvicorn). Real env vars win over both.
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database (required) ---
    DATABASE_URL: str

    # --- ESPN (primary live feed — no key; api-research.md §2) ---
    ESPN_API_BASE_URL: str = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
    ESPN_STANDINGS_URL: str = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world"
    ESPN_TIMEOUT_SECONDS: int = 10
    ESPN_MAX_RETRIES: int = 2

    # --- football-data.org (secondary cross-check; api-research.md §3) ---
    FOOTBALL_DATA_API_KEY: str = ""
    FOOTBALL_DATA_BASE_URL: str = "https://api.football-data.org/v4"
    FOOTBALL_DATA_TIMEOUT_SECONDS: int = 10
    FOOTBALL_DATA_MAX_RETRIES: int = 1

    # --- openfootball seed (api-research.md §4) ---
    OPENFOOTBALL_WORLDCUP_URL: str = (
        "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
    )

    # --- AI ---
    AI_PROVIDER: Literal["groq", "gemini", "openrouter", "anthropic", "openai"] = "groq"
    AI_MODEL: str = "llama-3.3-70b-versatile"
    AI_API_KEY: str = ""
    AI_MAX_TOKENS: int = 300
    AI_DAILY_BUDGET_USD: float = 2.00

    # --- Ingestion (required secret) ---
    INGEST_SECRET: str
    # Off in tests / one-off scripts so importing the app never fires HTTP calls.
    SCHEDULER_ENABLED: bool = True
    INGEST_INTERVAL_SECONDS: int = 60
    LIVE_POLL_INTERVAL_SECONDS: int = 30
    RECONCILIATION_SCORE_MISMATCH_ALERT_AFTER: int = 3
    FRESHNESS_THRESHOLD_MINUTES: int = 5

    # --- App ---
    ENVIRONMENT: Literal["development", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if self.ENVIRONMENT == "production" and "*" in origins:
            raise ValueError("CORS_ORIGINS must never be '*' in production (CLAUDE.md §11)")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
