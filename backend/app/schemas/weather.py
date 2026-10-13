import datetime as dt
from typing import Literal

from pydantic import BaseModel

ConditionIcon = Literal[
    "clear", "partly_cloudy", "cloudy", "drizzle", "rain", "thunderstorm", "fog", "snow"
]
Severity = Literal["info", "caution", "warning"]


class Condition(BaseModel):
    label: str
    icon: ConditionIcon


class LocationInfo(BaseModel):
    name: str
    state: str | None
    country: str
    lat: float
    lon: float


class CurrentWeather(BaseModel):
    temp_c: float
    feels_like_c: float
    humidity_pct: int
    wind_kmh: int
    rain_mm: float
    condition: Condition
    observed_at: dt.datetime


class HourlySlot(BaseModel):
    time: dt.datetime
    temp_c: float
    humidity_pct: int
    rain_chance_pct: int
    rain_mm: float
    wind_kmh: int
    condition: Condition


class DailyForecast(BaseModel):
    date: dt.date
    temp_min_c: float
    temp_max_c: float
    rain_chance_pct: int
    rain_mm: float
    wind_max_kmh: int
    humidity_pct: int
    condition: Condition


class Advisory(BaseModel):
    code: str
    severity: Severity
    title: str
    message: str
    date: dt.date | None = None


class WeatherReport(BaseModel):
    location: LocationInfo
    current: CurrentWeather
    hourly: list[HourlySlot]
    daily: list[DailyForecast]
    advisories: list[Advisory]