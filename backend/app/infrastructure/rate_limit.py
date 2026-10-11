import time
from collections import defaultdict, deque

from app.domain.errors import TooManyRequestsError
from app.infrastructure.config import Settings


class LoginRateLimiter:
    """Giới hạn số lần đăng nhập theo IP (sliding window, trong bộ nhớ từng tiến trình)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings  # đọc cấu hình mỗi lần gọi để bật/tắt được khi chạy test
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, ip: str) -> None:
        if not self.settings.rate_limit_enabled:
            return
        now = time.monotonic()
        hits = self._hits[ip]
        while hits and hits[0] < now - self.settings.login_rate_window_seconds:
            hits.popleft()
        if len(hits) >= self.settings.login_rate_limit:
            raise TooManyRequestsError("Đăng nhập quá nhiều lần, thử lại sau")
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()
