import httpx
import pytest

from app.core.config import settings
from app.services import openweather as ow


@pytest.fixture()
def api_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "test-key")


def use_handler(monkeypatch, handler):
    """Route the client's HTTP calls to `handler`. Returns the list of requests seen."""
    calls = []

    def wrapped(request):
        calls.append(request)
        return handler(request)

    def make_client():
        return httpx.Client(
            base_url="https://owm.test", transport=httpx.MockTransport(wrapped)
        )

    monkeypatch.setattr(ow, "_make_client", make_client)
    return calls


def json_handler(payload):
    return lambda request: httpx.Response(200, json=payload)


def place(name, state, lat, lon):
    return {"name": name, "state": state, "country": "IN", "lat": lat, "lon": lon}


# ---------- _request ----------
def test_request_sends_api_key(monkeypatch, api_key):
    calls = use_handler(monkeypatch, json_handler({"ok": True}))
    assert ow._request("/data/2.5/weather", {"lat": 1}) == {"ok": True}
    assert calls[0].url.params["appid"] == "test-key"
    assert calls[0].url.path == "/data/2.5/weather"


def test_request_without_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "")
    with pytest.raises(ow.WeatherNotConfigured):
        ow._request("/data/2.5/weather", {})


@pytest.mark.parametrize(
    "status_code, expected",
    [
        (401, ow.WeatherNotConfigured),
        (429, ow.WeatherUnavailable),
        (500, ow.WeatherUnavailable),
        (404, ow.WeatherUnavailable),
    ],
)
def test_request_maps_http_errors(monkeypatch, api_key, status_code, expected):
    use_handler(monkeypatch, lambda request: httpx.Response(status_code))
    with pytest.raises(expected):
        ow._request("/data/2.5/weather", {})


def test_request_network_error_hides_key(monkeypatch, api_key):
    def boom(request):
        raise httpx.ConnectError("connection failed")

    use_handler(monkeypatch, boom)
    with pytest.raises(ow.WeatherUnavailable) as exc_info:
        ow._request("/data/2.5/weather", {})
    assert "test-key" not in str(exc_info.value)


def test_request_non_json_response(monkeypatch, api_key):
    use_handler(monkeypatch, lambda request: httpx.Response(200, content=b"<html>oops</html>"))
    with pytest.raises(ow.WeatherUnavailable):
        ow._request("/data/2.5/weather", {})


# ---------- geocode ----------
def test_geocode_prefers_expected_state(monkeypatch, api_key):
    results = [
        place("Palakkad", "Tamil Nadu", 1.0, 2.0),
        place("Palakkad", "Kerala", 10.77, 76.65),
    ]
    use_handler(monkeypatch, json_handler(results))
    found = ow.geocode("Palakkad,IN", expected_state="Kerala")
    assert found.state == "Kerala"
    assert found.lat == 10.77


def test_geocode_state_match_ignores_case_and_spaces(monkeypatch, api_key):
    use_handler(monkeypatch, json_handler([place("Palakkad", "Kerala", 10.77, 76.65)]))
    assert ow.geocode("Palakkad,IN", expected_state=" kerala ").name == "Palakkad"


def test_geocode_without_state_takes_first(monkeypatch, api_key):
    results = [place("Palakkad", "Tamil Nadu", 1.0, 2.0), place("Palakkad", "Kerala", 3.0, 4.0)]
    use_handler(monkeypatch, json_handler(results))
    assert ow.geocode("Palakkad,IN").state == "Tamil Nadu"


def test_geocode_empty_result(monkeypatch, api_key):
    use_handler(monkeypatch, json_handler([]))
    with pytest.raises(ow.LocationNotFound):
        ow.geocode("Nowhere,IN")


def test_geocode_no_match_in_expected_state(monkeypatch, api_key):
    use_handler(monkeypatch, json_handler([place("Palakkad", "Tamil Nadu", 1.0, 2.0)]))
    with pytest.raises(ow.LocationNotFound):
        ow.geocode("Palakkad,IN", expected_state="Kerala")


def test_geocode_is_cached(monkeypatch, api_key):
    calls = use_handler(monkeypatch, json_handler([place("Palakkad", "Kerala", 10.77, 76.65)]))
    ow.geocode("Palakkad,IN")
    ow.geocode("PALAKKAD,IN")
    assert len(calls) == 1


# ---------- current / forecast ----------
def test_current_is_cached_for_nearby_coordinates(monkeypatch, api_key):
    calls = use_handler(monkeypatch, json_handler({"main": {"temp": 30}}))
    ow.get_current(10.7681, 76.6521)
    ow.get_current(10.7699, 76.6529)  # same ~1 km cell
    assert len(calls) == 1


def test_forecast_is_cached(monkeypatch, api_key):
    calls = use_handler(monkeypatch, json_handler({"list": []}))
    ow.get_forecast(10.77, 76.65)
    ow.get_forecast(10.77, 76.65)
    assert len(calls) == 1