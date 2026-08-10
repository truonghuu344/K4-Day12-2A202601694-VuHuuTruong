import math
import time
import uuid

from fastapi import HTTPException, status

WINDOW_SECONDS = 60
RATE_LIMIT_KEY_TTL = 3600


class TokenBucket:
    def __init__(self, client, capacity: int = 10, refill_per_minute: int = 10) -> None:
        self.client = client
        self.capacity = capacity
        self.refill_per_minute = refill_per_minute

    @staticmethod
    def _key(client_id: str) -> str:
        return f"rate_limit:{client_id}"

    def available(self, client_id: str, now: float | None = None) -> float:
        now = now if now is not None else time.time()
        key = self._key(client_id)

        data = self.client.hgetall(key)
        if not data:
            return float(self.capacity)

        tokens_val = data.get("tokens") or data.get(b"tokens")
        ts_val = data.get("ts") or data.get(b"ts")

        if tokens_val is None or ts_val is None:
            return float(self.capacity)

        tokens = float(tokens_val)
        ts = float(ts_val)

        refill_rate = self.refill_per_minute / 60.0
        elapsed = max(0.0, now - ts)
        refilled_tokens = tokens + elapsed * refill_rate

        return min(float(self.capacity), refilled_tokens)

    def consume(self, client_id: str, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        key = self._key(client_id)

        avail = self.available(client_id, now)

        if avail < 1.0:
            needed = 1.0 - avail
            refill_rate = self.refill_per_minute / 60.0
            retry_after = math.ceil(needed / refill_rate) if refill_rate > 0 else 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
                headers={"Retry-After": str(int(retry_after))},
            )

        new_tokens = avail - 1.0
        self.client.hset(key, mapping={"tokens": new_tokens, "ts": now})
        self.client.expire(key, RATE_LIMIT_KEY_TTL)


class SlidingWindowRateLimiter:
    def __init__(self, client, rate_limit: int = 10) -> None:
        self.client = client
        self.rate_limit = rate_limit

    @staticmethod
    def _key(client_id: str) -> str:
        return f"rate_limit:{client_id}"

    def consume(self, client_id: str, now: float | None = None) -> None:
        now = now if now is not None else time.time()

        key = self._key(client_id)

        # 1. PRUNE
        window_start = now - WINDOW_SECONDS

        self.client.zremrangebyscore(
            key,
            "-inf",
            window_start,
        )

        # 2. COUNT
        current_count = self.client.zcard(key)

        # 3. CHECK
        if current_count >= self.rate_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
            )

        # 4. RECORD
        member = f"{now}:{uuid.uuid4()}"

        self.client.zadd(
            key,
            {
                member: now,
            },
        )

        # 5. EXPIRE
        self.client.expire(
            key,
            RATE_LIMIT_KEY_TTL,
        )