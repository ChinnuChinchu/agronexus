from tests.conftest import API


def test_register_success(client, user_payload):
    response = client.post(f"{API}/auth/register", json=user_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "chinchu"
    assert body["email"] == "chinchu@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_lowercases_username(client):
    response = client.post(
        f"{API}/auth/register",
        json={"username": "Chinchu", "password": "farm12345"},
    )
    assert response.status_code == 201
    assert response.json()["username"] == "chinchu"


def test_register_duplicate_username(client, user_payload):
    client.post(f"{API}/auth/register", json=user_payload)
    response = client.post(
        f"{API}/auth/register",
        json={"username": "chinchu", "password": "another12345"},
    )
    assert response.status_code == 409


def test_register_duplicate_email(client, user_payload):
    client.post(f"{API}/auth/register", json=user_payload)
    response = client.post(
        f"{API}/auth/register",
        json={
            "username": "someone",
            "password": "farm12345",
            "email": user_payload["email"],
        },
    )
    assert response.status_code == 409


def test_register_short_password(client):
    response = client.post(
        f"{API}/auth/register",
        json={"username": "chinchu", "password": "short"},
    )
    assert response.status_code == 422


def test_register_invalid_username(client):
    response = client.post(
        f"{API}/auth/register",
        json={"username": "bad name!", "password": "farm12345"},
    )
    assert response.status_code == 422


def test_login_success(client, user_payload):
    client.post(f"{API}/auth/register", json=user_payload)
    response = client.post(
        f"{API}/auth/login",
        data={"username": "chinchu", "password": "farm12345"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client, user_payload):
    client.post(f"{API}/auth/register", json=user_payload)
    response = client.post(
        f"{API}/auth/login",
        data={"username": "chinchu", "password": "wrongpass123"},
    )
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post(
        f"{API}/auth/login",
        data={"username": "nobody", "password": "farm12345"},
    )
    assert response.status_code == 401