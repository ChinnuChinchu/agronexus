from datetime import timedelta

import pytest

from tests.conftest import API
from tests.test_market_service import AS_OF, add_price


@pytest.fixture()
def coconut_prices(db_session, crop_types):
    add_price(db_session, AS_OF, market="Koduvayoor", district="Palakkad", modal=7400)
    add_price(db_session, AS_OF, market="Munnar", district="Idukki", modal=6500, variety="Other")
    add_price(
        db_session,
        AS_OF,
        market="Pollachi",
        district="Coimbatore",
        state="Tamil Nadu",
        modal=9999,
    )
    db_session.commit()
    return crop_types


def set_profile(client, headers, **fields):
    response = client.put(f"{API}/users/me", json=fields, headers=headers)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/market/crops", "/market/prices?crop_type_id=1", "/market/trend?crop_type_id=1"],
)
def test_market_endpoints_require_auth(client, path):
    assert client.get(f"{API}{path}").status_code == 401


# ---------- crops with price data ----------
def test_available_crops_for_my_state(client, auth_headers, coconut_prices):
    set_profile(client, auth_headers, state="Kerala")
    body = client.get(f"{API}/market/crops", headers=auth_headers).json()

    assert [c["name"] for c in body] == ["Coconut"]
    assert body[0]["latest_date"] == "2025-10-30"
    assert body[0]["stale"] is True


def test_available_crops_empty_for_state_without_data(client, auth_headers, coconut_prices):
    set_profile(client, auth_headers, state="Maharashtra")
    assert client.get(f"{API}/market/crops", headers=auth_headers).json() == []


def test_state_defaults_to_kerala_when_profile_has_none(client, auth_headers, coconut_prices):
    body = client.get(f"{API}/market/crops", headers=auth_headers).json()
    assert [c["name"] for c in body] == ["Coconut"]


# ---------- price board ----------
def test_price_board(client, auth_headers, coconut_prices):
    set_profile(client, auth_headers, state="Kerala", district="Palakkad")
    response = client.get(
        f"{API}/market/prices",
        params={"crop_type_id": coconut_prices["Coconut"]},
        headers=auth_headers,
    )
    assert response.status_code == 200

    body = response.json()
    assert body["has_data"] is True
    assert body["as_of"] == "2025-10-30"
    assert body["stale"] is True
    assert body["days_old"] > 14
    assert [m["market"] for m in body["markets"]] == ["Koduvayoor", "Munnar"]
    assert body["markets"][0]["in_my_district"] is True
    assert body["summary"]["highest_modal"] == 7400
    assert body["varieties"] == ["Big", "Other"]
    assert body["unit"] == "Rs per quintal"
    assert "CEDA" in body["source"]


def test_price_board_variety_filter(client, auth_headers, coconut_prices):
    response = client.get(
        f"{API}/market/prices",
        params={"crop_type_id": coconut_prices["Coconut"], "variety": "other"},
        headers=auth_headers,
    )
    body = response.json()
    assert [m["market"] for m in body["markets"]] == ["Munnar"]
    assert body["varieties"] == ["Big", "Other"]


def test_unknown_crop_type_is_404(client, auth_headers, coconut_prices):
    response = client.get(
        f"{API}/market/prices", params={"crop_type_id": 999999}, headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Crop type not found"


def test_missing_crop_type_id_is_422(client, auth_headers):
    assert client.get(f"{API}/market/prices", headers=auth_headers).status_code == 422


def test_crop_without_price_data(client, auth_headers, coconut_prices):
    response = client.get(
        f"{API}/market/prices",
        params={"crop_type_id": coconut_prices["Black Pepper"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_data"] is False
    assert body["markets"] == []
    assert body["as_of"] is None


# ---------- trend ----------
def test_trend(client, auth_headers, db_session, crop_types):
    for i in range(40):
        add_price(db_session, AS_OF - timedelta(days=39 - i), modal=7000 + 10 * i)
    db_session.commit()

    response = client.get(
        f"{API}/market/trend",
        params={"crop_type_id": crop_types["Coconut"], "days": 30},
        headers=auth_headers,
    )
    assert response.status_code == 200

    body = response.json()
    assert body["has_data"] is True
    assert len(body["points"]) == 30
    assert body["points"][-1]["date"] == "2025-10-30"
    assert body["latest_modal"] == 7390
    assert body["signal"]["label"] == "stable"
    assert "CEDA" in body["source"]


def test_trend_days_limits(client, auth_headers, crop_types):
    coconut = crop_types["Coconut"]
    for days in (3, 400):
        response = client.get(
            f"{API}/market/trend",
            params={"crop_type_id": coconut, "days": days},
            headers=auth_headers,
        )
        assert response.status_code == 422