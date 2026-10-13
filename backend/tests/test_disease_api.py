from io import BytesIO

import pytest
from PIL import Image

from app.api.routes import disease as disease_routes
from app.api.routes.disease import classifier_dependency
from app.main import app
from app.services import disease_classifier as dc
from tests.conftest import API
from tests.disease_fakes import FakeClassifier


@pytest.fixture()
def fake_classifier(client):
    fake = FakeClassifier()
    app.dependency_overrides[classifier_dependency] = lambda: fake
    return fake  # the client fixture clears all overrides afterwards


def photo(fmt="JPEG"):
    buffer = BytesIO()
    Image.new("RGB", (320, 240), (40, 130, 50)).save(buffer, fmt)
    return buffer.getvalue()


def upload(client, headers, crop_type_id, data=None):
    files = {"image": ("leaf.jpg", photo() if data is None else data, "image/jpeg")}
    return client.post(
        f"{API}/disease/predict",
        data={"crop_type_id": str(crop_type_id)},
        files=files,
        headers=headers,
    )


# ---------- access ----------
@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/disease/crops"),
        ("post", "/disease/predict"),
        ("get", "/disease/history"),
        ("delete", "/disease/history/1"),
    ],
)
def test_endpoints_require_auth(client, fake_classifier, method, path):
    assert getattr(client, method)(f"{API}{path}").status_code == 401


def test_supported_crops(client, auth_headers, fake_classifier, crop_types):
    response = client.get(f"{API}/disease/crops", headers=auth_headers)

    assert response.status_code == 200
    assert {c["name"]: c["crop_type_id"] for c in response.json()} == {
        "Maize": crop_types["Maize"],
        "Tomato": crop_types["Tomato"],
    }


# ---------- outcomes ----------
def test_strong_match(client, auth_headers, fake_classifier, crop_types):
    fake_classifier.scores = {
        ("Tomato", "late_blight"): 0.97,
        ("Tomato", "early_blight"): 0.02,
        ("Tomato", "healthy"): 0.01,
    }
    response = upload(client, auth_headers, crop_types["Tomato"])

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["level"]) == ("ok", "strong")
    assert body["headline"] == "Strong match: Late blight"
    assert body["top"]["key"] == "late_blight"
    assert body["top"]["confidence_pct"] == 97.0
    assert [a["key"] for a in body["alternatives"]] == ["early_blight", "healthy"]
    assert body["guide"]["name"] == "Late blight"
    assert body["guide"]["urgent"] is True
    assert body["guide"]["actions"]
    assert body["tips"] == []
    assert "not a diagnosis" in body["disclaimer"]
    assert isinstance(body["scan_id"], int)
    assert fake_classifier.last_shape == (1, 224, 224, 3)


def test_possible_match(client, auth_headers, fake_classifier, crop_types):
    fake_classifier.scores = {
        ("Tomato", "late_blight"): 0.88,
        ("Tomato", "early_blight"): 0.08,
        ("Tomato", "healthy"): 0.04,
    }
    body = upload(client, auth_headers, crop_types["Tomato"]).json()

    assert (body["status"], body["level"]) == ("ok", "possible")
    assert body["headline"] == "Possible match: Late blight"
    assert body["guide"] is not None
    assert body["tips"]


def test_uncertain_gives_candidates_but_no_guide(client, auth_headers, fake_classifier, crop_types):
    fake_classifier.scores = {
        ("Tomato", "late_blight"): 0.5,
        ("Tomato", "early_blight"): 0.3,
        ("Tomato", "healthy"): 0.2,
    }
    body = upload(client, auth_headers, crop_types["Tomato"]).json()

    assert (body["status"], body["level"]) == ("uncertain", "uncertain")
    assert body["headline"] == "We're not sure"
    assert body["top"]["key"] == "late_blight"
    assert len(body["alternatives"]) == 2
    assert body["guide"] is None
    assert body["tips"]


def test_crop_mismatch(client, auth_headers, fake_classifier, crop_types):
    fake_classifier.scores = {("Maize", "common_rust"): 0.9, ("Tomato", "late_blight"): 0.1}
    body = upload(client, auth_headers, crop_types["Tomato"]).json()

    assert body["status"] == "crop_mismatch"
    assert body["top"] is None
    assert "Tomato" in body["headline"]
    assert body["guide"] is None


def test_healthy_leaf(client, auth_headers, fake_classifier, crop_types):
    fake_classifier.scores = {("Tomato", "healthy"): 0.98, ("Tomato", "early_blight"): 0.02}
    body = upload(client, auth_headers, crop_types["Tomato"]).json()

    assert body["headline"] == "Looks healthy"
    assert body["top"]["healthy"] is True
    assert body["guide"]["healthy"] is True


def test_maize_prediction(client, auth_headers, fake_classifier, crop_types):
    fake_classifier.scores = {("Maize", "common_rust"): 0.97, ("Maize", "healthy"): 0.03}
    body = upload(client, auth_headers, crop_types["Maize"]).json()

    assert body["crop"] == "Maize"
    assert body["guide"]["name"] == "Common rust"


# ---------- bad requests ----------
def test_unsupported_crop(client, auth_headers, fake_classifier, crop_types):
    response = upload(client, auth_headers, crop_types["Banana"])
    assert response.status_code == 422
    assert "does not support Banana" in response.json()["detail"]


def test_unknown_crop_type(client, auth_headers, fake_classifier, crop_types):
    assert upload(client, auth_headers, 999999).status_code == 404


def test_not_an_image(client, auth_headers, fake_classifier, crop_types):
    response = upload(client, auth_headers, crop_types["Tomato"], data=b"this is not a photo")
    assert response.status_code == 422
    assert "could not be read" in response.json()["detail"]
    assert fake_classifier.calls == 0


def test_photo_too_large(client, auth_headers, fake_classifier, crop_types, monkeypatch):
    monkeypatch.setattr(disease_routes, "MAX_UPLOAD_BYTES", 100)
    response = upload(client, auth_headers, crop_types["Tomato"])
    assert response.status_code == 413
    assert fake_classifier.calls == 0


def test_missing_photo(client, auth_headers, fake_classifier, crop_types):
    response = client.post(
        f"{API}/disease/predict",
        data={"crop_type_id": str(crop_types["Tomato"])},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_model_not_installed_is_503(client, auth_headers, crop_types, monkeypatch, tmp_path):
    monkeypatch.setattr(dc, "ML_DIR", tmp_path)
    dc.reset_classifier()
    try:
        response = upload(client, auth_headers, crop_types["Tomato"])
    finally:
        dc.reset_classifier()

    assert response.status_code == 503
    assert "not installed" in response.json()["detail"]


# ---------- history ----------
def test_history_lists_my_scans_newest_first(
    client, auth_headers, other_headers, fake_classifier, crop_types
):
    tomato = crop_types["Tomato"]
    fake_classifier.scores = {("Tomato", "late_blight"): 0.97, ("Tomato", "early_blight"): 0.03}
    assert upload(client, auth_headers, tomato).status_code == 200
    fake_classifier.scores = {("Maize", "common_rust"): 0.9, ("Tomato", "late_blight"): 0.1}
    assert upload(client, auth_headers, tomato).status_code == 200

    body = client.get(f"{API}/disease/history", headers=auth_headers).json()

    assert [s["status"] for s in body] == ["crop_mismatch", "ok"]
    assert body[0]["result_key"] is None
    older = body[1]
    assert older["crop_name"] == "Tomato"
    assert older["level"] == "strong"
    assert older["result_key"] == "late_blight"
    assert older["result_name"] == "Late blight"
    assert older["confidence_pct"] == 97.0
    assert older["healthy"] is False

    page = client.get(f"{API}/disease/history?limit=1&offset=1", headers=auth_headers).json()
    assert [s["status"] for s in page] == ["ok"]
    assert client.get(f"{API}/disease/history", headers=other_headers).json() == []


def test_delete_scan(client, auth_headers, other_headers, fake_classifier, crop_types):
    fake_classifier.scores = {("Tomato", "late_blight"): 0.97}
    scan_id = upload(client, auth_headers, crop_types["Tomato"]).json()["scan_id"]
    url = f"{API}/disease/history/{scan_id}"

    assert client.delete(url, headers=other_headers).status_code == 404
    assert client.delete(url, headers=auth_headers).status_code == 204
    assert client.get(f"{API}/disease/history", headers=auth_headers).json() == []
    assert client.delete(url, headers=auth_headers).status_code == 404