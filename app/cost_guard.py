from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

KEY_TTL_SECONDS = 62 * 24 * 3600


class CostGuard:
    def __init__(self, client, daily_budget_usd: float = 1.0) -> None:
        self.client = client
        self.budget = daily_budget_usd

    @staticmethod
    def current_day() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @classmethod
    def _key(cls, user_id: str, day: str | None = None) -> str:
        return f"cost:{user_id}:{day or cls.current_day()}"

    def spent(self, user_id: str, day: str | None = None) -> float:
        value = self.client.get(self._key(user_id, day))
        if value is None:
            return 0.0
        return float(value)

    def check(self, user_id: str, estimated_cost: float = 0.0, day: str | None = None) -> None:
        if self.spent(user_id, day) + estimated_cost > self.budget:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="daily budget exceeded",
            )

    def record(self, user_id: str, cost_usd: float, day: str | None = None) -> float:
        key = self._key(user_id, day)
        total = self.client.incrbyfloat(key, cost_usd)
        self.client.expire(key, KEY_TTL_SECONDS)
        return float(total)

    def remaining(self, user_id: str, day: str | None = None) -> float:
        return max(0.0, self.budget - self.spent(user_id, day))