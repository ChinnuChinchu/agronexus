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
    
# def test_postgres_scheme_is_normalised():
#     settings = make(DATABASE_URL="postgres://user:pass@host/db")
#     assert settings.DATABASE_URL == "postgresql://user:pass@host/db"

@pytest.mark.parametrize(
    "url", ["postgres://user:pass@host/db", "postgresql://user:pass@host/db"]
)
def test_plain_postgres_urls_use_the_psycopg2_driver(url):
    assert make(DATABASE_URL=url).DATABASE_URL == "postgresql+psycopg2://user:pass@host/db"

def test_other_database_urls_are_left_alone():
    url = "postgresql+psycopg2://user:pass@host/db"
    assert make(DATABASE_URL=url).DATABASE_URL == url