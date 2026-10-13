import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.cache import TTLCache
from app.core.config import settings

logger = logging.getLogger(__name__)

GEO_TTL = 24 * 60 * 60
CURRENT_TTL = 10 * 60
FORECAST_TTL = 30 * 60

_cache = TTLCache()


class WeatherError(Exception):
    """Base class. The message is safe to show to the user."""


class WeatherNotConfigured(WeatherError):
    pass


class LocationNotFound(WeatherError):
    pass


class WeatherUnavailable(WeatherError):
    pass


@dataclass(frozen=True)
class Place:
    name: str
    state: str | None
    country: str
    lat: float
    lon: float


def _make_client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.OPENWEATHER_BASE_URL,
        timeout=settings.WEATHER_TIMEOUT_SECONDS,
    )


def _request(path: str, params: dict[str, Any]) -> Any:
    if not settings.OPENWEATHER_API_KEY:
        raise WeatherNotConfigured("The weather service is not configured yet")

    query = {**params, "appid": settings.OPENWEATHER_API_KEY}
    try:
        with _make_client() as client:
            response = client.get(path, params=query)
    except httpx.HTTPError as exc:
        # log only the exception type, so the API key in the URL never reaches the logs
        logger.warning("OpenWeatherMap request failed: %s", type(exc).__name__)
        raise WeatherUnavailable(
            "The weather service is not responding. Please try again shortly."
        ) from None

    if response.status_code == 401:
        raise WeatherNotConfigured("The weather service key is invalid or not active yet")
    if response.status_code == 429:
        raise WeatherUnavailable("The weather service is busy. Please try again in a minute.")
    if response.status_code != 200:
        logger.warning("OpenWeatherMap returned HTTP %s for %s", response.status_code, path)
        raise WeatherUnavailable("The weather service returned an error. Please try again later.")

    try:
        return response.json()
    except ValueError:
        raise WeatherUnavailable("The weather service returned an unreadable response") from None


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def geocode(query: str, expected_state: str | None = None) -> Place:
    """Find a place by name, e.g. 'Palakkad,IN'.

    When expected_state is given, only a match in that state is accepted, which
    avoids picking a same-named village in another state.
    """
    key = f"geo:{_norm(query)}"
    results = _cache.get(key)
    if results is None:
        results = _request("/geo/1.0/direct", {"q": query, "limit": 5})
        if not isinstance(results, list):
            raise WeatherUnavailable("The weather service returned an unexpected response")
        _cache.set(key, results, GEO_TTL)

    wanted_state = _norm(expected_state)
    for item in results:
        if wanted_state and _norm(item.get("state")) != wanted_state:
            continue
        try:
            return Place(
                name=item["name"],
                state=item.get("state"),
                country=item.get("country", ""),
                lat=float(item["lat"]),
                lon=float(item["lon"]),
            )
        except (KeyError, TypeError, ValueError):
            continue

    raise LocationNotFound(f"Could not find the location '{query}'")


def _coord_key(prefix: str, lat: float, lon: float) -> str:
    return f"{prefix}:{lat:.2f},{lon:.2f}"


def get_current(lat: float, lon: float) -> dict:
    key = _coord_key("current", lat, lon)
    data = _cache.get(key)
    if data is None:
        data = _request("/data/2.5/weather", {"lat": lat, "lon": lon, "units": "metric"})
        _cache.set(key, data, CURRENT_TTL)
    return data


def get_forecast(lat: float, lon: float) -> dict:
    key = _coord_key("forecast", lat, lon)
    data = _cache.get(key)
    if data is None:
        data = _request("/data/2.5/forecast", {"lat": lat, "lon": lon, "units": "metric"})
        _cache.set(key, data, FORECAST_TTL)
    return data