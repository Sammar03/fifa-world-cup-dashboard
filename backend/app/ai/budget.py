"""AI_DAILY_BUDGET_USD circuit breaker (CLAUDE.md §10).

In-process daily spend estimate. Exact per-model pricing varies by provider, so
a deliberately conservative flat rate is used — overestimating spend on cheap /
free-tier models only makes the breaker trip earlier, never later. Resets at
UTC midnight. Single-process deployment (one scheduler), so process-local state
is sufficient for MVP.
"""

import logging
from datetime import UTC, datetime

from app.config import get_settings

logger = logging.getLogger(__name__)

# Conservative flat estimate, USD per 1M tokens.
_INPUT_USD_PER_MTOK = 1.00
_OUTPUT_USD_PER_MTOK = 4.00


class DailyBudget:
    def __init__(self) -> None:
        self._day: str = ""
        self._spent_usd: float = 0.0

    def _roll(self) -> None:
        today = datetime.now(UTC).date().isoformat()
        if today != self._day:
            self._day = today
            self._spent_usd = 0.0

    def allow(self) -> bool:
        self._roll()
        budget = get_settings().AI_DAILY_BUDGET_USD
        if self._spent_usd >= budget:
            logger.warning(
                "ai_budget_exhausted spent_usd=%.4f budget_usd=%.2f — skipping AI calls until UTC midnight",
                self._spent_usd,
                budget,
            )
            return False
        return True

    def record(self, input_tokens: int | None, output_tokens: int | None) -> None:
        self._roll()
        cost = ((input_tokens or 0) * _INPUT_USD_PER_MTOK + (output_tokens or 0) * _OUTPUT_USD_PER_MTOK) / 1_000_000
        self._spent_usd += cost

    @property
    def spent_usd(self) -> float:
        self._roll()
        return self._spent_usd


budget = DailyBudget()
