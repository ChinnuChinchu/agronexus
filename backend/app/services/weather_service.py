from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.weather import LocationInfo, WeatherReport
from app.services import crop_service
from app.services import openweather as ow
from app.services import weather_logic as logic

from datetime import date
from app.schemas.weather import DailyForecast

class LocationNotSet(ow.WeatherError):
    """The user's profile has no village or district."""


def _resolve_place(user: User) -> ow.Place:
    candidates = logic.location_candidates(user.village, user.district, user.state)
    if not candidates:
        raise LocationNotSet("Add your village or district in your profile to see the weather")

    for query, state in candidates:
        try:
            return ow.geocode(query, expected_state=state)
        except ow.LocationNotFound:
            continue

    raise ow.LocationNotFound(
        "Could not find your location. Please check the village and district in your profile."
    )


def get_weather_report(db: Session, user: User) -> WeatherReport:
    place = _resolve_place(user)

    try:
        current = logic.parse_current(ow.get_current(place.lat, place.lon))
        hourly, daily = logic.parse_forecast(ow.get_forecast(place.lat, place.lon))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ow.WeatherUnavailable(
            "The weather service returned unexpected data. Please try again later."
        ) from None

    growing = crop_service.list_crops(db, user.id, "growing", 100)
    crops = [crop_service.to_crop_read(c) for c in growing]

    advisories = logic.generate_advisories(daily, current.observed_at.date(), crops)

    return WeatherReport(
        location=LocationInfo(
            name=place.name,
            state=place.state,
            country=place.country,
            lat=place.lat,
            lon=place.lon,
        ),
        current=current,
        hourly=hourly,
        daily=daily,
        advisories=advisories,
    )
    
def get_daily_forecast(user: User) -> tuple[ow.Place, list[DailyForecast], date]:
    """The user's place, its daily forecast and today's date there (for other services)."""
    place = _resolve_place(user)
    try:
        current = logic.parse_current(ow.get_current(place.lat, place.lon))
        _, daily = logic.parse_forecast(ow.get_forecast(place.lat, place.lon))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ow.WeatherUnavailable(
            "The weather service returned unexpected data. Please try again later."
        ) from None
    return place, daily, current.observed_at.date()