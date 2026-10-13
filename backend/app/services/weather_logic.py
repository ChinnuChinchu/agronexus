from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Sequence

from app.schemas.weather import (
    Advisory,
    Condition,
    CurrentWeather,
    DailyForecast,
    HourlySlot,
)

# ---------- advisory thresholds (rules of thumb, tune as needed) ----------
HEAVY_RAIN_MM = 30.0          # total rain in a day
RAIN_LIKELY_PCT = 60          # chance of rain
RAIN_LIKELY_MM = 2.0
HIGH_WIND_KMH = 25
HEAT_C = 35.0
SPRAY_MAX_WIND_KMH = 15
SPRAY_MAX_RAIN_CHANCE = 30
SPRAY_MAX_RAIN_MM = 1.0
DRY_SPELL_MAX_MM = 1.0
DRY_SPELL_MAX_CHANCE = 30
HARVEST_WINDOW_DAYS = 5       # crops due within this many days are checked
HARVEST_RAIN_MM = 10.0
MAX_CROP_ADVISORIES = 3
MAX_ADVISORIES = 6
HOURLY_SLOTS = 8              # next 24 hours
FORECAST_DAYS = 5

PRECIP_ICONS = {"thunderstorm", "rain", "drizzle", "snow"}
ICON_RANK = {
    "clear": 0,
    "partly_cloudy": 1,
    "cloudy": 2,
    "fog": 3,
    "drizzle": 4,
    "snow": 5,
    "rain": 6,
    "thunderstorm": 7,
}
SEVERITY_ORDER = {"warning": 0, "caution": 1, "info": 2}


# ---------- small helpers ----------
def icon_for(condition_id: int) -> str:
    if 200 <= condition_id < 300:
        return "thunderstorm"
    if 300 <= condition_id < 400:
        return "drizzle"
    if 500 <= condition_id < 600:
        return "rain"
    if 600 <= condition_id < 700:
        return "snow"
    if 700 <= condition_id < 800:
        return "fog"
    if condition_id == 800:
        return "clear"
    if condition_id in (801, 802):
        return "partly_cloudy"
    return "cloudy"


def _condition(weather: list[dict]) -> Condition:
    first = weather[0] if weather else {}
    label = str(first.get("description") or first.get("main") or "Unknown").strip().capitalize()
    return Condition(label=label, icon=icon_for(int(first.get("id", 800))))


def _kmh(metres_per_second: Any) -> int:
    return round(float(metres_per_second or 0) * 3.6)


def _tz(offset_seconds: Any) -> timezone:
    return timezone(timedelta(seconds=int(offset_seconds or 0)))


# ---------- parsing OpenWeatherMap responses ----------
# These raise KeyError / TypeError / ValueError on malformed data.
# The service layer turns those into a "weather unavailable" error.
def parse_current(raw: dict) -> CurrentWeather:
    tz = _tz(raw.get("timezone"))
    main = raw["main"]
    return CurrentWeather(
        temp_c=round(float(main["temp"]), 1),
        feels_like_c=round(float(main.get("feels_like", main["temp"])), 1),
        humidity_pct=int(main.get("humidity", 0)),
        wind_kmh=_kmh((raw.get("wind") or {}).get("speed")),
        rain_mm=round(float((raw.get("rain") or {}).get("1h", 0.0)), 1),
        condition=_condition(raw.get("weather", [])),
        observed_at=datetime.fromtimestamp(int(raw["dt"]), tz),
    )


def _slots(raw: dict) -> list[HourlySlot]:
    tz = _tz((raw.get("city") or {}).get("timezone"))
    slots = []
    for item in raw.get("list", []):
        main = item["main"]
        slots.append(
            HourlySlot(
                time=datetime.fromtimestamp(int(item["dt"]), tz),
                temp_c=round(float(main["temp"]), 1),
                humidity_pct=int(main.get("humidity", 0)),
                rain_chance_pct=round(float(item.get("pop", 0)) * 100),
                rain_mm=round(float((item.get("rain") or {}).get("3h", 0.0)), 1),
                wind_kmh=_kmh((item.get("wind") or {}).get("speed")),
                condition=_condition(item.get("weather", [])),
            )
        )
    slots.sort(key=lambda s: s.time)
    return slots


def _day_condition(group: list[HourlySlot]) -> Condition:
    precip = [s for s in group if s.condition.icon in PRECIP_ICONS]
    total_rain = sum(s.rain_mm for s in group)
    if precip and (total_rain >= 2.0 or len(precip) >= 2):
        worst = max(precip, key=lambda s: (ICON_RANK[s.condition.icon], s.rain_mm))
        return worst.condition

    counts = Counter(s.condition.icon for s in group)
    top = max(counts, key=lambda icon: (counts[icon], ICON_RANK[icon]))
    return next(s.condition for s in group if s.condition.icon == top)


def _daily(slots: list[HourlySlot]) -> list[DailyForecast]:
    by_day: dict[date, list[HourlySlot]] = defaultdict(list)
    for slot in slots:
        by_day[slot.time.date()].append(slot)  # local date, because slot.time is localised

    days = []
    for day in sorted(by_day):
        group = by_day[day]
        days.append(
            DailyForecast(
                date=day,
                temp_min_c=min(s.temp_c for s in group),
                temp_max_c=max(s.temp_c for s in group),
                rain_chance_pct=max(s.rain_chance_pct for s in group),
                rain_mm=round(sum(s.rain_mm for s in group), 1),
                wind_max_kmh=max(s.wind_kmh for s in group),
                humidity_pct=round(sum(s.humidity_pct for s in group) / len(group)),
                condition=_day_condition(group),
            )
        )
    return days[:FORECAST_DAYS]


def parse_forecast(raw: dict) -> tuple[list[HourlySlot], list[DailyForecast]]:
    slots = _slots(raw)
    return slots[:HOURLY_SLOTS], _daily(slots)


# ---------- location ----------
def location_candidates(
    village: str | None, district: str | None, state: str | None
) -> list[tuple[str, str | None]]:
    """(query, expected_state) pairs to try in order."""
    village = (village or "").strip()
    district = (district or "").strip()
    state_filter = (state or "").strip() or None

    candidates: list[tuple[str, str | None]] = []
    if village:
        candidates.append((f"{village},IN", state_filter))
    if district:
        candidates.append((f"{district},IN", state_filter))
        if state_filter:
            candidates.append((f"{district},IN", None))

    unique: list[tuple[str, str | None]] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


# ---------- advisories ----------
def _when(day: date, today: date) -> str:
    delta = (day - today).days
    if delta <= 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    return f"on {day.strftime('%A')}"


def _also(extra_days: int) -> str:
    if extra_days <= 0:
        return ""
    return f" (and {extra_days} more day{'s' if extra_days > 1 else ''})"


def _in_days(n: int) -> str:
    if n <= 0:
        return "today"
    if n == 1:
        return "tomorrow"
    return f"in {n} days"


def _harvest_advisories(
    daily: list[DailyForecast], today: date, crops: Sequence[Any]
) -> list[Advisory]:
    wet = [d for d in daily if d.rain_mm >= HARVEST_RAIN_MM]
    if not wet:
        return []
    first_wet = wet[0]
    rain_in_days = (first_wet.date - today).days
    rain_when = _when(first_wet.date, today)

    result: list[Advisory] = []
    for crop in crops:
        if getattr(crop, "status", None) != "growing":
            continue
        growth = crop.growth
        if growth.days_to_harvest is None or growth.days_to_harvest > HARVEST_WINDOW_DAYS:
            continue
        if not growth.is_overdue and rain_in_days > growth.days_to_harvest + 2:
            continue

        if growth.is_overdue:
            status_text = "is past its expected harvest date"
        else:
            status_text = f"is due for harvest {_in_days(growth.days_to_harvest)}"

        result.append(
            Advisory(
                code=f"harvest_rain_{crop.id}",
                severity="warning" if rain_in_days <= 1 else "caution",
                title=f"Harvest before rain: {crop.name}",
                message=(
                    f"{crop.name} {status_text}, and about {first_wet.rain_mm:g} mm of rain "
                    f"is forecast {rain_when}. If the crop is mature, consider harvesting "
                    "before the rain."
                ),
                date=first_wet.date,
            )
        )
        if len(result) >= MAX_CROP_ADVISORIES:
            break
    return result


def generate_advisories(
    daily: list[DailyForecast], today: date, crops: Sequence[Any] = ()
) -> list[Advisory]:
    advisories: list[Advisory] = []
    if not daily:
        return advisories

    heavy = [d for d in daily if d.rain_mm >= HEAVY_RAIN_MM]
    if heavy:
        first = heavy[0]
        advisories.append(
            Advisory(
                code="heavy_rain",
                severity="warning",
                title="Heavy rain expected",
                message=(
                    f"About {first.rain_mm:g} mm of rain is forecast "
                    f"{_when(first.date, today)}{_also(len(heavy) - 1)}. Avoid spraying and "
                    "fertilizer application, and make sure field drainage is clear."
                ),
                date=first.date,
            )
        )
    else:
        likely = [
            d
            for d in daily[:3]
            if d.rain_chance_pct >= RAIN_LIKELY_PCT and d.rain_mm >= RAIN_LIKELY_MM
        ]
        if likely:
            first = likely[0]
            advisories.append(
                Advisory(
                    code="rain_likely",
                    severity="caution",
                    title="Rain likely",
                    message=(
                        f"Rain is likely {_when(first.date, today)} "
                        f"({first.rain_chance_pct}% chance, about {first.rain_mm:g} mm). "
                        "Plan field work and harvest drying around it."
                    ),
                    date=first.date,
                )
            )

    hot = [d for d in daily if d.temp_max_c >= HEAT_C]
    if hot:
        first = hot[0]
        advisories.append(
            Advisory(
                code="heat",
                severity="caution",
                title="Hot weather",
                message=(
                    f"Temperatures up to {first.temp_max_c:g}°C are forecast "
                    f"{_when(first.date, today)}{_also(len(hot) - 1)}. Irrigate in the early "
                    "morning or evening and avoid heavy field work at midday."
                ),
                date=first.date,
            )
        )

    windy = [d for d in daily if d.wind_max_kmh >= HIGH_WIND_KMH]
    if windy:
        first = windy[0]
        advisories.append(
            Advisory(
                code="wind",
                severity="caution",
                title="Strong winds",
                message=(
                    f"Winds up to {first.wind_max_kmh} km/h are forecast "
                    f"{_when(first.date, today)}{_also(len(windy) - 1)}. Avoid spraying "
                    "pesticides, and support young plants and banana."
                ),
                date=first.date,
            )
        )

    if len(daily) >= 4 and all(
        d.rain_mm < DRY_SPELL_MAX_MM and d.rain_chance_pct < DRY_SPELL_MAX_CHANCE
        for d in daily
    ):
        advisories.append(
            Advisory(
                code="dry_spell",
                severity="info",
                title="Dry spell ahead",
                message=(
                    f"No significant rain is forecast for the next {len(daily)} days. "
                    "Plan irrigation for your crops."
                ),
            )
        )

    for d in daily[:3]:
        if (
            d.wind_max_kmh <= SPRAY_MAX_WIND_KMH
            and d.rain_mm < SPRAY_MAX_RAIN_MM
            and d.rain_chance_pct < SPRAY_MAX_RAIN_CHANCE
        ):
            advisories.append(
                Advisory(
                    code="spray_window",
                    severity="info",
                    title="Good spraying window",
                    message=(
                        f"{_when(d.date, today).capitalize()} looks calm and dry (wind up to "
                        f"{d.wind_max_kmh} km/h), a good time for spraying."
                    ),
                    date=d.date,
                )
            )
            break

    advisories.extend(_harvest_advisories(daily, today, crops))

    advisories.sort(key=lambda a: (SEVERITY_ORDER[a.severity], a.date or date.max))
    return advisories[:MAX_ADVISORIES]