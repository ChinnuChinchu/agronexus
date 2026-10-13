from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.services import openweather as ow
from app.services.growth import today_local
from tests.conftest import API
from tests.weather_fakes import default_forecast, raw_current

LOCATION = {"village": "Kollengode", "district": "Palakkad", "state": "Kerala"}


@pytest.fixture()
def fake_weather(monkeypatch):
    """Replaces the HTTP layer. `state.missing` lists place names that cannot be found."""
    state = SimpleNamespace(calls=[], missing=set(), fail=None)
    base = today_local()

    def fake_request(path, params):
        state.calls.append(path)
        if state.fail:
            raise state.fail
        if path == "/geo/1.0/direct":
            name = params["q"].split(",")[0]
            if name.lower() in state.missing:
                return []
            return [
                {"name": name, "state": "Kerala", "country": "IN", "lat": 10.77, "lon": 76.65}
            ]
        if path == "/data/2.5/weather":
            return raw_current(base)
        if path == "/data/2.5/forecast":
            return default_forecast(base, wet_day_offset=1)
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(ow, "_request", fake_request)
    return state


def set_location(client, headers, **fields):
    response = client.put(f"{API}/users/me", json=fields, headers=headers)
    assert response.status_code == 200


def test_weather_requires_auth(client):
    assert client.get(f"{API}/weather").status_code == 401


def test_weather_needs_a_location(client, auth_headers, fake_weather):
    response = client.get(f"{API}/weather", headers=auth_headers)
    assert response.status_code == 400
    assert "village or district" in response.json()["detail"]
    assert fake_weather.calls == []


def test_weather_report(client, auth_headers, fake_weather):
    set_location(client, auth_headers, **LOCATION)
    response = client.get(f"{API}/weather", headers=auth_headers)
    assert response.status_code == 200

    body = response.json()
    assert body["location"]["name"] == "Kollengode"
    assert body["current"]["temp_c"] == 30.0
    assert body["current"]["condition"]["icon"] == "partly_cloudy"
    assert len(body["hourly"]) == 8
    assert len(body["daily"]) == 5
    assert body["daily"][1]["rain_mm"] == 17.6
    assert isinstance(body["advisories"], list)


def test_weather_falls_back_to_district(client, auth_headers, fake_weather):
    set_location(client, auth_headers, **LOCATION)
    fake_weather.missing = {"kollengode"}
    response = client.get(f"{API}/weather", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["location"]["name"] == "Palakkad"


def test_weather_location_not_found(client, auth_headers, fake_weather):
    set_location(client, auth_headers, **LOCATION)
    fake_weather.missing = {"kollengode", "palakkad"}
    response = client.get(f"{API}/weather", headers=auth_headers)
    assert response.status_code == 404
    assert "Could not find your location" in response.json()["detail"]


def test_weather_service_unavailable(client, auth_headers, fake_weather):
    set_location(client, auth_headers, **LOCATION)
    fake_weather.fail = ow.WeatherUnavailable("The weather service is not responding.")
    response = client.get(f"{API}/weather", headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["detail"] == "The weather service is not responding."


def test_weather_service_not_configured(client, auth_headers, fake_weather):
    set_location(client, auth_headers, **LOCATION)
    fake_weather.fail = ow.WeatherNotConfigured("The weather service is not configured yet")
    response = client.get(f"{API}/weather", headers=auth_headers)
    assert response.status_code == 503


def test_weather_responses_are_cached(client, auth_headers, fake_weather):
    set_location(client, auth_headers, **LOCATION)
    client.get(f"{API}/weather", headers=auth_headers)
    client.get(f"{API}/weather", headers=auth_headers)
    # geocode + current + forecast, fetched only once
    assert len(fake_weather.calls) == 3


def create_rice_crop_due_in(client, headers, crop_types, days):
    today = today_local()
    response = client.post(
        f"{API}/crops",
        json={
            "name": "Paddy field 1",
            "crop_type_id": crop_types["Rice (Paddy)"],
            "planting_date": (today - timedelta(days=40)).isoformat(),
            "expected_harvest_date": (today + timedelta(days=days)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_weather_includes_harvest_advisory_for_my_crop(
    client, auth_headers, fake_weather, crop_types
):
    set_location(client, auth_headers, **LOCATION)
    crop_id = create_rice_crop_due_in(client, auth_headers, crop_types, days=2)

    body = client.get(f"{API}/weather", headers=auth_headers).json()
    advisory = next(a for a in body["advisories"] if a["code"] == f"harvest_rain_{crop_id}")
    assert advisory["severity"] == "warning"


def test_other_users_crops_do_not_leak_into_advisories(
    client, auth_headers, other_headers, fake_weather, crop_types
):
    create_rice_crop_due_in(client, other_headers, crop_types, days=2)
    set_location(client, auth_headers, **LOCATION)

    body = client.get(f"{API}/weather", headers=auth_headers).json()
    assert not [a for a in body["advisories"] if a["code"].startswith("harvest_rain_")]