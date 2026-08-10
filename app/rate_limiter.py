"""CP3 — Rate limiting bằng thuật toán token bucket.

Hình dung mỗi client có một cái xô đựng token:

    - Xô chứa tối đa ``capacity`` token, ban đầu đầy.
    - Token tự nhỏ vào xô đều đặn với tốc độ ``refill_per_minute`` mỗi phút.
    - Mỗi request lấy ra 1 token. Xô cạn → 429.

Vì sao không đơn giản là "tối đa N request mỗi phút"? Vì người dùng thật
không gửi request đều tăm tắp. Họ im lặng 5 phút rồi bấm 8 lần liên tiếp.
Token bucket cho phép đúng kiểu dùng đó — im lặng thì tích token, cần thì
tiêu một lúc — mà vẫn chặn được kẻ gọi liên tục không nghỉ. Đây là lý do nó
là thuật toán mặc định ở hầu hết API gateway (Stripe, AWS, Kong).

Cấu trúc dữ liệu: một Redis HASH cho mỗi client, gồm 2 trường:
``tokens`` (số token còn lại) và ``ts`` (lần cập nhật gần nhất).
"""

from __future__ import annotations

import time

from fastapi import HTTPException, status

# Xô không dùng tới thì bỏ đi cho sạch Redis
BUCKET_TTL_SECONDS = 3600


class TokenBucket:
    def __init__(self, client, capacity: int, refill_per_minute: int) -> None:
        self.client = client
        self.capacity = capacity
        self.refill_per_minute = refill_per_minute

    @staticmethod
    def _key(client_id: str) -> str:
        """CHO SẴN — mỗi client một cái xô riêng."""
        return f"bucket:{client_id}"

    @property
    def refill_per_second(self) -> float:
        """CHO SẴN — tốc độ nạp lại, đổi sang đơn vị giây."""
        return self.refill_per_minute / 60.0

    def available(self, client_id: str, now: float | None = None) -> float:
        now = now if now is not None else time.time()

        state = self.client.hgetall(self._key(client_id))

        # Client mới -> xô đầy
        if not state:
            return float(self.capacity)

        tokens = float(state["tokens"])
        last = float(state["ts"])

        # Nạp thêm token theo thời gian
        tokens += (now - last) * self.refill_per_second

        # Không bao giờ vượt capacity
        return min(float(self.capacity), tokens)

    def consume(self, client_id: str, now: float | None = None) -> None:
        now = now if now is not None else time.time()

        tokens = self.available(client_id, now)

        # Không còn đủ 1 token
        if tokens < 1:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
                headers={"Retry-After": str(self.retry_after(tokens))},
            )

        key = self._key(client_id)

        # Tiêu 1 token và lưu lại timestamp mới
        self.client.hset(
            key,
            mapping={
                "tokens": tokens - 1,
                "ts": now,
            },
        )

        # Xô không dùng lâu thì Redis tự xóa
        self.client.expire(key, BUCKET_TTL_SECONDS)

    def retry_after(self, tokens: float) -> int:
        """CHO SẴN — còn bao nhiêu giây nữa thì có token tiếp theo."""
        if self.refill_per_second <= 0:
            return BUCKET_TTL_SECONDS
        return max(1, int((1 - tokens) / self.refill_per_second) + 1)
