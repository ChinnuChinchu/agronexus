import time

from app.core.cache import TTLCache


def test_set_and_get():
    cache = TTLCache()
    cache.set("a", 1, ttl_seconds=10)
    assert cache.get("a") == 1
    assert cache.get("missing") is None


def test_entry_expires():
    cache = TTLCache()
    cache.set("a", 1, ttl_seconds=0.01)
    time.sleep(0.05)
    assert cache.get("a") is None


def test_evicts_oldest_when_full():
    cache = TTLCache(max_items=2)
    cache.set("a", 1, ttl_seconds=10)
    cache.set("b", 2, ttl_seconds=20)
    cache.set("c", 3, ttl_seconds=30)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_clear():
    cache = TTLCache()
    cache.set("a", 1, ttl_seconds=10)
    cache.clear()
    assert cache.get("a") is None