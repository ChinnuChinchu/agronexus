import threading
import time
from collections import deque

from fastapi import HTTPException, Request, status

_registry: list["RateLimiter"] = []


class RateLimiter:
    """Allows `limit` calls per `window_seconds` for each key (in memory, per process)."""

    MAX_KEYS = 10_000

    def __init__(self, limit: int, window_seconds: float, clock=time.monotonic) -> None:
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        _registry.append(self)

    def hit(self, key: str) -> None:
        """Records a call, or raises 429 when the key has used up its allowance."""
        now = self._clock()
        with self._lock:
            if key not in self._hits and len(self._hits) >= self.MAX_KEYS:
                self._prune(now)

            queue = self._hits.setdefault(key, deque())
            while queue and now - queue[0] >= self.window:
                queue.popleft()

            if len(queue) >= self.limit:
                retry_after = max(1, int(self.window - (now - queue[0])) + 1)
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Too many requests. Please wait a moment and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            queue.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _prune(self, now: float) -> None:
        stale = [k for k, q in self._hits.items() if not q or now - q[-1] >= self.window]
        for key in stale:
            del self._hits[key]
        if len(self._hits) >= self.MAX_KEYS:
            self._hits.clear()


def reset_all_limiters() -> None:
    for limiter in _registry:
        limiter.reset()


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


login_limiter = RateLimiter(limit=20, window_seconds=60)
register_limiter = RateLimiter(limit=5, window_seconds=60)
predict_limiter = RateLimiter(limit=10, window_seconds=60)