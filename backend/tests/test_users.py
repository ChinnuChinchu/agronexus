from tests.conftest import API


def test_me_requires_token(client):
    response = client.get(f"{API}/users/me")
    assert response.status_code == 401


def test_me_with_invalid_token(client):
    response = client.get(
        f"{API}/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_me_returns_profile(client, auth_headers):
    response = client.get(f"{API}/users/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "chinchu"
    assert "hashed_password" not in body


def test_update_profile(client, auth_headers):
    payload = {
        "village": "Kollengode",
        "district": "Palakkad",
        "state": "Kerala",
        "farm_size_acres": 2.5,
    }
    response = client.put(f"{API}/users/me", json=payload, headers=auth_headers)
    assert response.status_code == 200

    profile = client.get(f"{API}/users/me", headers=auth_headers).json()
    assert profile["village"] == "Kollengode"
    assert profile["district"] == "Palakkad"
    assert profile["farm_size_acres"] == 2.5


def test_update_keeps_unsent_fields(client, auth_headers):
    client.put(f"{API}/users/me", json={"village": "Kollengode"}, headers=auth_headers)
    client.put(f"{API}/users/me", json={"state": "Kerala"}, headers=auth_headers)

    profile = client.get(f"{API}/users/me", headers=auth_headers).json()
    assert profile["village"] == "Kollengode"
    assert profile["state"] == "Kerala"


def test_update_invalid_farm_size(client, auth_headers):
    response = client.put(
        f"{API}/users/me", json={"farm_size_acres": -1}, headers=auth_headers
    )
    assert response.status_code == 422


def test_update_email_already_taken(client, auth_headers):
    client.post(
        f"{API}/auth/register",
        json={
            "username": "other",
            "password": "farm12345",
            "email": "other@example.com",
        },
    )
    response = client.put(
        f"{API}/users/me", json={"email": "other@example.com"}, headers=auth_headers
    )
    assert response.status_code == 409