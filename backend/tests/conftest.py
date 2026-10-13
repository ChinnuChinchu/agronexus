import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.seed import CATALOG
from app.db.session import get_db
from app.main import app
from app.models.crop_type import CropType
from app.services import openweather as ow
from app.core.rate_limit import reset_all_limiters

API = settings.API_V1_PREFIX

base_url = make_url(settings.DATABASE_URL)
TEST_DB_NAME = f"{base_url.database}_test"
test_url = base_url.set(database=TEST_DB_NAME)


def _create_test_database() -> None:
    admin_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _create_test_database()
    test_engine = create_engine(test_url, pool_pre_ping=True)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture()
def client(engine):
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture()
def user_payload():
    return {
        "username": "chinchu",
        "password": "farm12345",
        "email": "chinchu@example.com",
        "full_name": "Chinchu P",
    }


@pytest.fixture()
def auth_headers(client, user_payload):
    client.post(f"{API}/auth/register", json=user_payload)
    response = client.post(
        f"{API}/auth/login",
        data={
            "username": user_payload["username"],
            "password": user_payload["password"],
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def other_headers(client):
    """A second, unrelated user (used for ownership tests)."""
    client.post(
        f"{API}/auth/register",
        json={"username": "otherfarmer", "password": "farm12345"},
    )
    response = client.post(
        f"{API}/auth/login",
        data={"username": "otherfarmer", "password": "farm12345"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def crop_types(client, engine):
    """Insert the crop catalog into the test database. Returns {name: id}."""
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = TestingSessionLocal()
    try:
        for item in CATALOG:
            db.add(CropType(**item))
        db.commit()
        return {row.name: row.id for row in db.scalars(select(CropType))}
    finally:
        db.close()
        
@pytest.fixture(autouse=True)
def clear_weather_cache():
    """The weather cache is in-memory, so isolate it between tests."""
    ow._cache.clear()
    yield
    ow._cache.clear()
    
    
@pytest.fixture()
def db_session(engine):
    """A plain database session for service-level tests. Cleans every table afterwards."""
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
                

@pytest.fixture(autouse=True)
def clear_rate_limits():
    """Rate limits are in memory, so isolate them between tests."""
    reset_all_limiters()
    yield
    reset_all_limiters()