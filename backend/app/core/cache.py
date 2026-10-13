import threading
import time
from typing import Any


class TTLCache:
    """A small thread-safe in-memory cache where each entry expires after a TTL."""

    def __init__(self, max_items: int = 512) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._max_items = max_items

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            if key not in self._data and len(self._data) >= self._max_items:
                self._evict()
            self._data[key] = (time.monotonic() + ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def _evict(self) -> None:
        now = time.monotonic()
        for key in [k for k, (expires_at, _) in self._data.items() if expires_at <= now]:
            del self._data[key]
        if len(self._data) >= self._max_items:
            oldest = min(self._data, key=lambda k: self._data[k][0])
            del self._data[oldest]