from app.services import openweather as ow
from tests.conftest import API
from tests.test_crops import create_crop, iso
from tests.test_weather_api import LOCATION, fake_weather, set_location  # noqa: F401


def test_plan_requires_auth(client):
    assert client.get(f"{API}/resources/plan").status_code == 401


def test_empty_plan_needs_no_location_or_weather(client, auth_headers, fake_weather):
    response = client.get(f"{API}/resources/plan", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["crops"] == []
    assert body["actions"] == []
    assert body["location"] is None
    assert body["as_of"] is None
    assert body["summary"]["crops"] == 0
    assert body["note"]
    assert fake_weather.calls == []


def test_plan_without_a_location_is_400(client, auth_headers, fake_weather, crop_types):
    create_crop(client, auth_headers, crop_types)

    response = client.get(f"{API}/resources/plan", headers=auth_headers)

    assert response.status_code == 400
    assert "village or district" in response.json()["detail"]


def test_plan_for_two_crops(client, auth_headers, fake_weather, crop_types):
    set_location(client, auth_headers, **LOCATION)
    create_crop(client, auth_headers, crop_types)  # paddy, about 33% grown
    create_crop(
        client,
        auth_headers,
        crop_types,
        name="Tomato bed",
        crop_type_id=crop_types["Tomato"],
        planting_date=iso(-30),
        expected_harvest_date=iso(80),
    )

    response = client.get(f"{API}/resources/plan", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["location"]["name"] == "Kollengode"
    assert body["as_of"] == iso(0)
    plans = {c["crop_name"]: c for c in body["crops"]}
    assert set(plans) == {"Paddy field 1", "Tomato bed"}

    paddy = plans["Paddy field 1"]
    assert paddy["stage"] == "Tillering"
    assert paddy["irrigation"]["status"] == "flooded"
    assert paddy["fertilizer"]["current"]["title"] == "First top dressing"
    assert paddy["fertilizer"]["weather"] == "caution"  # 17.6 mm of rain tomorrow
    assert paddy["fertilizer"]["disclaimer"]

    tomato = plans["Tomato bed"]
    assert tomato["stage"] == "Vegetative growth"
    assert tomato["irrigation"]["status"] == "not_needed"
    assert len(tomato["irrigation"]["days"]) == 5
    assert tomato["fertilizer"]["current"]["title"] == "First top dressing"

    summary = body["summary"]
    assert summary["crops"] == 2
    assert summary["need_water_soon"] == 0
    assert summary["fertilizer_due"] == 2
    assert {(a["crop_name"], a["kind"]) for a in body["actions"]} == {
        ("Paddy field 1", "fertilizer"),
        ("Tomato bed", "fertilizer"),
    }


def test_crop_not_planted_yet(client, auth_headers, fake_weather, crop_types):
    set_location(client, auth_headers, **LOCATION)
    create_crop(
        client, auth_headers, crop_types, planting_date=iso(10), expected_harvest_date=iso(130)
    )

    body = client.get(f"{API}/resources/plan", headers=auth_headers).json()

    plan = body["crops"][0]
    assert plan["stage"] == "Planned"
    assert plan["irrigation"]["status"] == "not_planted"
    assert plan["fertilizer"] is None
    assert body["actions"] == []


def test_perennial_crop_plan(client, auth_headers, fake_weather, crop_types):
    set_location(client, auth_headers, **LOCATION)
    create_crop(
        client,
        auth_headers,
        crop_types,
        name="Coconut grove",
        crop_type_id=crop_types["Coconut"],
        planting_date=iso(-1095),
        expected_harvest_date=None,
    )

    body = client.get(f"{API}/resources/plan", headers=auth_headers).json()

    plan = body["crops"][0]
    assert plan["stage"] == "Juvenile growth"
    assert plan["irrigation"]["status"] == "not_needed"
    assert plan["fertilizer"] is not None
    assert plan["fertilizer"]["approximate_timing"] is False


def test_plan_only_includes_my_crops(
    client, auth_headers, other_headers, fake_weather, crop_types
):
    create_crop(client, other_headers, crop_types)

    body = client.get(f"{API}/resources/plan", headers=auth_headers).json()

    assert body["crops"] == []
    assert fake_weather.calls == []


def test_plan_when_weather_service_is_unavailable(
    client, auth_headers, fake_weather, crop_types
):
    set_location(client, auth_headers, **LOCATION)
    create_crop(client, auth_headers, crop_types)
    fake_weather.fail = ow.WeatherUnavailable("The weather service is not responding.")

    response = client.get(f"{API}/resources/plan", headers=auth_headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "The weather service is not responding."