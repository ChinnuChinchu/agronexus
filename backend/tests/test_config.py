import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make(**overrides):
    values = {
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "SECRET_KEY": "k" * 40,
        "ENVIRONMENT": "production",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_accepts_a_strong_secret():
    assert make().ENVIRONMENT == "production"


def test_production_rejects_a_short_secret():
    with pytest.raises(ValidationError, match="at least 32"):
        make(SECRET_KEY="short")


def test_production_rejects_a_placeholder_secret():
    with pytest.raises(ValidationError):
        make(SECRET_KEY="change-this-to-a-long-random-string-please")


def test_development_allows_a_weak_secret():
    assert make(ENVIRONMENT="development", SECRET_KEY="short").SECRET_KEY == "short"


def test_cors_origins_are_split_and_trimmed():
    settings = make(CORS_ORIGINS="http://localhost:4200, https://farmease.example.com ,")
    assert settings.cors_origins_list == [
        "http://localhost:4200",
        "https://farmease.example.com",
    ]