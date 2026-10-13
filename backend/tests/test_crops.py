from datetime import timedelta

from app.services.growth import today_local
from tests.conftest import API


def iso(offset_days: int) -> str:
    return (today_local() + timedelta(days=offset_days)).isoformat()


def crop_payload(types, **overrides):
    payload = {
        "name": "Paddy field 1",
        "crop_type_id": types["Rice (Paddy)"],
        "variety": "Jyothi",
        "area_acres": 1.5,
        "planting_date": iso(-40),
        "expected_harvest_date": iso(80),
    }
    payload.update(overrides)
    return payload


def create_crop(client, headers, types, **overrides):
    response = client.post(
        f"{API}/crops", json=crop_payload(types, **overrides), headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------- crop types ----------
def test_crop_types_require_auth(client):
    assert client.get(f"{API}/crop-types").status_code == 401


def test_list_crop_types(client, auth_headers, crop_types):
    response = client.get(f"{API}/crop-types", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(crop_types)
    names = {item["name"] for item in body}
    assert {"Rice (Paddy)", "Coconut"} <= names


# ---------- create ----------
def test_create_requires_auth(client):
    response = client.post(
        f"{API}/crops",
        json={"name": "x", "crop_type_id": 1, "planting_date": iso(0)},
    )
    assert response.status_code == 401


def test_create_seasonal_crop(client, auth_headers, crop_types):
    body = create_crop(client, auth_headers, crop_types)
    assert body["name"] == "Paddy field 1"
    assert body["status"] == "growing"
    assert body["crop_type"]["name"] == "Rice (Paddy)"
    growth = body["growth"]
    assert growth["stage"] == "Tillering"
    assert growth["progress_pct"] == 33.3
    assert growth["days_to_harvest"] == 80
    assert growth["is_overdue"] is False
    assert len(growth["stages"]) == 5


def test_create_perennial_without_harvest_date(client, auth_headers, crop_types):
    body = create_crop(
        client,
        auth_headers,
        crop_types,
        name="Coconut grove",
        crop_type_id=crop_types["Coconut"],
        planting_date=iso(-1095),
        expected_harvest_date=None,
    )
    assert body["expected_harvest_date"] is None
    assert body["growth"]["stage"] == "Juvenile growth"
    assert body["growth"]["days_to_harvest"] is None


def test_create_seasonal_requires_harvest_date(client, auth_headers, crop_types):
    response = client.post(
        f"{API}/crops",
        json=crop_payload(crop_types, expected_harvest_date=None),
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "required" in response.json()["detail"]


def test_create_harvest_before_planting(client, auth_headers, crop_types):
    response = client.post(
        f"{API}/crops",
        json=crop_payload(crop_types, planting_date=iso(-10), expected_harvest_date=iso(-20)),
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_unknown_crop_type(client, auth_headers, crop_types):
    response = client.post(
        f"{API}/crops",
        json=crop_payload(crop_types, crop_type_id=999999),
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown crop type"


def test_create_invalid_area(client, auth_headers, crop_types):
    response = client.post(
        f"{API}/crops",
        json=crop_payload(crop_types, area_acres=-1),
        headers=auth_headers,
    )
    assert response.status_code == 422


# ---------- list ----------
def test_list_returns_only_own_crops(client, auth_headers, other_headers, crop_types):
    create_crop(client, auth_headers, crop_types)

    mine = client.get(f"{API}/crops", headers=auth_headers).json()
    theirs = client.get(f"{API}/crops", headers=other_headers).json()
    assert len(mine) == 1
    assert theirs == []


def test_list_status_filter(client, auth_headers, crop_types):
    first = create_crop(client, auth_headers, crop_types, name="First")
    create_crop(client, auth_headers, crop_types, name="Second")
    client.post(f"{API}/crops/{first['id']}/harvest", json={}, headers=auth_headers)

    growing = client.get(f"{API}/crops?status=growing", headers=auth_headers).json()
    harvested = client.get(f"{API}/crops?status=harvested", headers=auth_headers).json()
    assert [c["name"] for c in growing] == ["Second"]
    assert [c["name"] for c in harvested] == ["First"]


def test_list_pagination(client, auth_headers, crop_types):
    create_crop(client, auth_headers, crop_types, name="A", planting_date=iso(-30))
    create_crop(client, auth_headers, crop_types, name="B", planting_date=iso(-20))
    create_crop(client, auth_headers, crop_types, name="C", planting_date=iso(-10))

    page1 = client.get(f"{API}/crops?limit=2", headers=auth_headers).json()
    page2 = client.get(f"{API}/crops?limit=2&offset=2", headers=auth_headers).json()
    assert [c["name"] for c in page1] == ["C", "B"]
    assert [c["name"] for c in page2] == ["A"]


def test_list_invalid_status_filter(client, auth_headers):
    response = client.get(f"{API}/crops?status=banana", headers=auth_headers)
    assert response.status_code == 422


# ---------- read / ownership ----------
def test_get_crop(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    response = client.get(f"{API}/crops/{crop['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Paddy field 1"


def test_other_user_cannot_access_crop(client, auth_headers, other_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    url = f"{API}/crops/{crop['id']}"

    assert client.get(url, headers=other_headers).status_code == 404
    assert client.put(url, json={"notes": "hacked"}, headers=other_headers).status_code == 404
    assert client.post(f"{url}/harvest", json={}, headers=other_headers).status_code == 404
    assert client.delete(url, headers=other_headers).status_code == 404

    still_there = client.get(url, headers=auth_headers)
    assert still_there.status_code == 200
    assert still_there.json()["notes"] is None
    assert still_there.json()["status"] == "growing"


# ---------- update ----------
def test_update_partial_keeps_other_fields(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    response = client.put(
        f"{API}/crops/{crop['id']}",
        json={"notes": "Irrigated twice"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["notes"] == "Irrigated twice"
    assert body["name"] == "Paddy field 1"
    assert body["variety"] == "Jyothi"
    assert body["area_acres"] == 1.5
    assert body["expected_harvest_date"] == iso(80)


def test_update_rejects_harvest_before_planting(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    response = client.put(
        f"{API}/crops/{crop['id']}",
        json={"expected_harvest_date": iso(-50)},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "cannot be before" in response.json()["detail"]


def test_mark_crop_failed(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    response = client.put(
        f"{API}/crops/{crop['id']}", json={"status": "failed"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["growth"]["stage"] == "Failed"


# ---------- harvest ----------
def test_harvest_crop(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    response = client.post(
        f"{API}/crops/{crop['id']}/harvest",
        json={"yield_quantity": 2500, "yield_unit": "kg"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "harvested"
    assert body["actual_harvest_date"] == iso(0)
    assert body["yield_quantity"] == 2500
    assert body["yield_unit"] == "kg"
    assert body["growth"]["stage"] == "Harvested"
    assert body["growth"]["progress_pct"] == 100.0


def test_harvest_twice_rejected(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    url = f"{API}/crops/{crop['id']}/harvest"
    assert client.post(url, json={}, headers=auth_headers).status_code == 200

    response = client.post(url, json={}, headers=auth_headers)
    assert response.status_code == 422
    assert "currently growing" in response.json()["detail"]


def test_harvest_quantity_requires_unit(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    response = client.post(
        f"{API}/crops/{crop['id']}/harvest",
        json={"yield_quantity": 100},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_harvest_future_date_rejected(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    response = client.post(
        f"{API}/crops/{crop['id']}/harvest",
        json={"actual_harvest_date": iso(1)},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "future" in response.json()["detail"]


def test_reopen_harvested_crop_clears_harvest_data(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    client.post(
        f"{API}/crops/{crop['id']}/harvest",
        json={"yield_quantity": 100, "yield_unit": "kg"},
        headers=auth_headers,
    )
    response = client.put(
        f"{API}/crops/{crop['id']}", json={"status": "growing"}, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "growing"
    assert body["actual_harvest_date"] is None
    assert body["yield_quantity"] is None
    assert body["yield_unit"] is None


# ---------- delete ----------
def test_delete_crop(client, auth_headers, crop_types):
    crop = create_crop(client, auth_headers, crop_types)
    url = f"{API}/crops/{crop['id']}"

    assert client.delete(url, headers=auth_headers).status_code == 204
    assert client.get(url, headers=auth_headers).status_code == 404
    assert client.get(f"{API}/crops", headers=auth_headers).json() == []