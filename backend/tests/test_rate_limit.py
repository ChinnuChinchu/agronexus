import pytest
from fastapi import HTTPException

from app.core.rate_limit import RateLimiter
from tests.conftest import API
from tests.test_disease_api import fake_classifier, upload  # noqa: F401


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_blocks_after_the_limit():
    limiter = RateLimiter(limit=2, window_seconds=10, clock=Clock())
    limiter.hit("a")
    limiter.hit("a")

    with pytest.raises(HTTPException) as exc_info:
        limiter.hit("a")

    assert exc_info.value.status_code == 429
    assert int(exc_info.value.headers["Retry-After"]) >= 1


def test_allows_again_after_the_window():
    clock = Clock()
    limiter = RateLimiter(limit=1, window_seconds=10, clock=clock)
    limiter.hit("a")
    with pytest.raises(HTTPException):
        limiter.hit("a")

    clock.now += 10
    limiter.hit("a")


def test_keys_are_independent():
    limiter = RateLimiter(limit=1, window_seconds=10, clock=Clock())
    limiter.hit("a")
    limiter.hit("b")
    with pytest.raises(HTTPException):
        limiter.hit("a")


def test_old_keys_are_pruned_when_the_table_is_full():
    clock = Clock()
    limiter = RateLimiter(limit=5, window_seconds=10, clock=clock)
    limiter.MAX_KEYS = 3
    for key in ("k1", "k2", "k3"):
        limiter.hit(key)

    clock.now += 100
    limiter.hit("k4")

    assert set(limiter._hits) == {"k4"}


def test_reset_clears_everything():
    limiter = RateLimiter(limit=1, window_seconds=10, clock=Clock())
    limiter.hit("a")
    limiter.reset()
    limiter.hit("a")


# ---------- the real endpoints ----------
def test_login_is_rate_limited(client):
    data = {"username": "nobody", "password": "wrongpass123"}
    for _ in range(20):
        assert client.post(f"{API}/auth/login", data=data).status_code == 401

    response = client.post(f"{API}/auth/login", data=data)

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_register_is_rate_limited(client):
    for i in range(5):
        response = client.post(
            f"{API}/auth/register", json={"username": f"farmer{i}", "password": "farm12345"}
        )
        assert response.status_code == 201

    response = client.post(
        f"{API}/auth/register", json={"username": "farmer5", "password": "farm12345"}
    )
    assert response.status_code == 429


def test_photo_analysis_is_rate_limited_per_user(
    client, auth_headers, fake_classifier, crop_types
):
    fake_classifier.scores = {("Tomato", "late_blight"): 0.97}
    for _ in range(10):
        assert upload(client, auth_headers, crop_types["Tomato"]).status_code == 200

    assert upload(client, auth_headers, crop_types["Tomato"]).status_code == 429