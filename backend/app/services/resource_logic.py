import math
from collections.abc import Sequence
from datetime import date

from app.schemas.resources import (
    Action,
    CropPlan,
    FertilizerAdvice,
    FertilizerStepInfo,
    IrrigationAdvice,
    PlanSummary,
    WaterDay,
)

from app.schemas.weather import DailyForecast
from app.services.agronomy_data import (
    CROP_WATER,
    FERTILIZER,
    PADDY_DEFAULT_GUIDANCE,
    PADDY_GUIDANCE,
    CropWater,
    FertStep,
)

# ---------- constants (assumptions are named here so they are easy to change) ----------
SOLAR_CONSTANT = 0.0820           # MJ m-2 min-1
LATENT_HEAT = 2.45                # MJ kg-1
MIN_TEMP_RANGE = 1.0              # 3-hourly forecasts underestimate the daily range
MIN_EFFECTIVE_RAIN_MM = 2.0       # lighter rain does not reach the roots
RAIN_EFFICIENCY = 0.8
SOIL_BUFFER_CAPACITY_MM = 25.0    # assumed readily available water in the root zone
SOIL_BUFFER_START_MM = 12.0       # assumed starting moisture, because it is unknown
IRRIGATION_DEPTH_MM = 25.0        # suggested depth of one irrigation
LITRES_PER_MM_PER_ACRE = 4047     # 1 mm of water over 1 acre
FORECAST_DAYS = 5
RAIN_NOTE_MM = 5.0
PADDY_HEAVY_RAIN_MM = 60.0
PADDY_LOW_RAIN_MM = 5.0
PADDY_DRAINAGE_RAIN_MM = 20.0
FERT_HOLD_RAIN_MM = 25.0
FERT_CAUTION_RAIN_MM = 10.0

DISCLAIMER = (
    "General timing guidance only. Doses depend on your soil test, variety and local "
    "conditions. Confirm with a soil test, the KAU Package of Practices or your local "
    "Krishi Bhavan."
)


# ---------- evapotranspiration ----------
def extraterrestrial_radiation_mm(latitude_deg: float, day_of_year: int) -> float:
    """Extraterrestrial radiation for a day, as mm of evaporation (FAO-56 eq. 21)."""
    phi = math.radians(latitude_deg)
    angle = 2 * math.pi * day_of_year / 365
    dr = 1 + 0.033 * math.cos(angle)
    delta = 0.409 * math.sin(angle - 1.39)
    x = max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta)))
    sunset = math.acos(x)
    ra = (
        (24 * 60 / math.pi)
        * SOLAR_CONSTANT
        * dr
        * (
            sunset * math.sin(phi) * math.sin(delta)
            + math.cos(phi) * math.cos(delta) * math.sin(sunset)
        )
    )
    return ra / LATENT_HEAT


def hargreaves_et0(tmin: float, tmax: float, ra_mm: float) -> float:
    """Reference evapotranspiration in mm/day (Hargreaves-Samani)."""
    tmean = (tmax + tmin) / 2
    spread = max(tmax - tmin, MIN_TEMP_RANGE)
    return max(0.0023 * (tmean + 17.8) * math.sqrt(spread) * ra_mm, 0.0)


def effective_rain(rain_mm: float) -> float:
    if rain_mm < MIN_EFFECTIVE_RAIN_MM:
        return 0.0
    return round(rain_mm * RAIN_EFFICIENCY, 1)


def crop_kc(crop_name: str, stage_index: int | None) -> float | None:
    info = CROP_WATER.get(crop_name)
    if info is None or info.kind != "upland" or stage_index is None:
        return None
    return info.kc[min(max(stage_index, 0), len(info.kc) - 1)]


# ---------- irrigation ----------
def _day_phrase(index: int, day: date) -> str:
    if index <= 0:
        return "today"
    if index == 1:
        return "tomorrow"
    return f"on {day.strftime('%A')}"


def _rain_note(days: Sequence[DailyForecast]) -> str:
    for index, day in enumerate(days):
        if day.rain_mm >= RAIN_NOTE_MM:
            return f" Rain of about {day.rain_mm:g} mm is forecast {_day_phrase(index, day.date)}."
    return ""


def _flooded_advice(stage_name: str, days: Sequence[DailyForecast]) -> IrrigationAdvice:
    headline, detail = PADDY_GUIDANCE.get(stage_name, PADDY_DEFAULT_GUIDANCE)
    total_rain = sum(d.rain_mm for d in days)
    late_stage = stage_name in ("Grain filling", "Harvest-ready")

    if total_rain >= PADDY_HEAVY_RAIN_MM:
        detail += (
            f" About {total_rain:.0f} mm of rain is forecast over the next {len(days)} days. "
            "Check the bunds and keep drainage outlets clear."
        )
    elif late_stage and total_rain >= PADDY_DRAINAGE_RAIN_MM:
        detail += " Rain is forecast, so keep drainage outlets open to avoid water standing."
    elif not late_stage and total_rain < PADDY_LOW_RAIN_MM:
        detail += " Little rain is forecast, so plan to top up the standing water."

    return IrrigationAdvice(
        status="flooded",
        headline=headline,
        detail=detail,
        total_effective_rain_mm=round(sum(effective_rain(d.rain_mm) for d in days), 1),
    )


def _upland_advice(
    info: CropWater,
    stage_index: int,
    days: Sequence[DailyForecast],
    latitude: float,
    area_acres: float | None,
    soil_water_start_mm: float,
) -> IrrigationAdvice:
    kc = info.kc[min(max(stage_index, 0), len(info.kc) - 1)]
    store = soil_water_start_mm
    first_dry: int | None = None
    water_days: list[WaterDay] = []
    total_need = 0.0
    total_effective = 0.0

    for index, day in enumerate(days):
        ra = extraterrestrial_radiation_mm(latitude, day.date.timetuple().tm_yday)
        et0 = hargreaves_et0(day.temp_min_c, day.temp_max_c, ra)
        need = et0 * kc
        useful_rain = effective_rain(day.rain_mm)

        store = min(store + useful_rain - need, SOIL_BUFFER_CAPACITY_MM)
        if store < 0:
            if first_dry is None:
                first_dry = index
            store = 0.0

        total_need += need
        total_effective += useful_rain
        water_days.append(
            WaterDay(
                date=day.date,
                et0_mm=round(et0, 1),
                kc=kc,
                crop_need_mm=round(need, 1),
                rain_mm=day.rain_mm,
                effective_rain_mm=useful_rain,
                soil_water_mm=round(store, 1),
            )
        )

    count = len(days)
    base = (
        f"Estimated crop water use is about {total_need:.0f} mm over the next {count} days, "
        f"against about {total_effective:.0f} mm of useful rain."
    ) + _rain_note(days)

    if first_dry is None:
        status = "not_needed"
        headline = "No irrigation needed for now"
        detail = base + " Stored soil moisture and rain should cover the crop."
    else:
        if first_dry <= 1:
            status = "irrigate_soon"
            headline = "Irrigate today" if first_dry == 0 else "Irrigate by tomorrow"
        else:
            status = "plan_irrigation"
            headline = f"Plan to irrigate {_day_phrase(first_dry, days[first_dry].date)}"
        detail = base + f" Apply about {IRRIGATION_DEPTH_MM:g} mm in one irrigation."

    depth = IRRIGATION_DEPTH_MM if first_dry is not None else None
    litres_per_acre = round(depth * LITRES_PER_MM_PER_ACRE) if depth else None
    total_litres = round(litres_per_acre * area_acres) if litres_per_acre and area_acres else None

    return IrrigationAdvice(
        status=status,
        headline=headline,
        detail=detail,
        irrigate_by=days[first_dry].date if first_dry is not None else None,
        days=water_days,
        total_need_mm=round(total_need, 1),
        total_effective_rain_mm=round(total_effective, 1),
        suggested_depth_mm=depth,
        litres_per_acre=litres_per_acre,
        total_litres=total_litres,
        approximate=info.approximate,
    )


def irrigation_advice(
    crop_name: str,
    stage_name: str,
    stage_index: int | None,
    daily: Sequence[DailyForecast],
    latitude: float,
    area_acres: float | None = None,
    soil_water_start_mm: float = SOIL_BUFFER_START_MM,
) -> IrrigationAdvice:
    info = CROP_WATER.get(crop_name)
    days = list(daily[:FORECAST_DAYS])

    if info is None:
        return IrrigationAdvice(
            status="no_guidance",
            headline="No irrigation guidance for this crop yet",
            detail="We do not have water-use data for this crop.",
        )
    if stage_index is None:
        return IrrigationAdvice(
            status="not_planted",
            headline="Not planted yet",
            detail="Irrigation advice starts once the crop is planted.",
        )
    if not days:
        return IrrigationAdvice(
            status="no_guidance",
            headline="No forecast available",
            detail="Irrigation advice needs the weather forecast, which is not available now.",
        )
    if info.kind == "flooded":
        return _flooded_advice(stage_name, days)
    return _upland_advice(info, stage_index, days, latitude, area_acres, soil_water_start_mm)


# ---------- fertilizer ----------
def _months_until(today_month: int, months: tuple[int, ...]) -> int:
    return min((m - today_month) % 12 for m in months)


def _step_info(step: FertStep) -> FertilizerStepInfo:
    return FertilizerStepInfo(title=step.title, nutrients=step.nutrients, note=step.note)


def _fertilizer_weather(daily: Sequence[DailyForecast]) -> tuple[str, str | None]:
    window = list(daily[:2])
    if not window:
        return "ok", None

    index = max(range(len(window)), key=lambda i: window[i].rain_mm)
    heaviest = window[index]
    when = _day_phrase(index, heaviest.date)

    if heaviest.rain_mm >= FERT_HOLD_RAIN_MM:
        return "hold", (
            f"Heavy rain (about {heaviest.rain_mm:g} mm) is forecast {when}. Delay fertilizer "
            "application until it has passed, so the fertilizer is not washed away."
        )
    if heaviest.rain_mm >= FERT_CAUTION_RAIN_MM:
        return "caution", (
            f"Rain (about {heaviest.rain_mm:g} mm) is forecast {when}. Apply once the rain "
            "has eased."
        )
    return "ok", None


def fertilizer_advice(
    crop_name: str,
    stage_index: int | None,
    age_days: int,
    stage_start_days: Sequence[int] | None,
    today_month: int,
    daily: Sequence[DailyForecast],
) -> FertilizerAdvice | None:
    schedule = FERTILIZER.get(crop_name)
    if schedule is None or stage_index is None or not schedule.steps:
        return None

    weather, weather_message = _fertilizer_weather(daily)
    current: FertStep | None = None
    upcoming: FertStep | None = None
    days_until: int | None = None

    if schedule.steps[0].months:  # perennial: steps follow the calendar
        distances = [(_months_until(today_month, s.months), s) for s in schedule.steps]
        current = next((s for d, s in distances if d == 0), None)
        later = [(d, s) for d, s in distances if d > 0]
        if later:
            months_away, upcoming = min(later, key=lambda item: item[0])
            days_until = months_away * 30

        if current is not None:
            summary = f"{current.title} is due this month."
        elif upcoming is not None and days_until is not None:
            months = days_until // 30
            summary = (
                f"No dose is due this month. Next: {upcoming.title} in about {months} "
                f"month{'s' if months != 1 else ''}."
            )
        else:
            summary = "No dose is scheduled."
    else:  # seasonal: steps follow the growth stage
        current = next((s for s in schedule.steps if s.stage_index == stage_index), None)
        later_steps = [
            s for s in schedule.steps if s.stage_index is not None and s.stage_index > stage_index
        ]
        upcoming = min(later_steps, key=lambda s: s.stage_index or 0) if later_steps else None

        if (
            upcoming is not None
            and stage_start_days is not None
            and upcoming.stage_index is not None
            and upcoming.stage_index < len(stage_start_days)
        ):
            days_until = max(stage_start_days[upcoming.stage_index] - age_days, 0)

        if current is not None:
            summary = f"{current.title} applies at this stage."
        elif upcoming is not None:
            if days_until:
                summary = f"Next: {upcoming.title} in about {days_until} days."
            else:
                summary = f"Next: {upcoming.title}, very soon."
        else:
            summary = "No further fertilizer is needed this season."

    return FertilizerAdvice(
        summary=summary,
        current=_step_info(current) if current else None,
        upcoming=_step_info(upcoming) if upcoming else None,
        days_until_upcoming=days_until,
        weather=weather,
        weather_message=weather_message,
        approximate_timing=schedule.approximate,
        disclaimer=DISCLAIMER,
    )
    
# ---------- plan summary and actions ----------
PRIORITY_RANK = {"high": 0, "medium": 1}
WATERING_STATUSES = ("irrigate_soon", "plan_irrigation")


def summarise(plans: Sequence[CropPlan]) -> PlanSummary:
    watering = [p for p in plans if p.irrigation.status in WATERING_STATUSES]
    counted = [p for p in watering if p.irrigation.total_litres]
    due = [p for p in plans if p.fertilizer is not None and p.fertilizer.current is not None]
    return PlanSummary(
        crops=len(plans),
        need_water_soon=len(watering),
        fertilizer_due=len(due),
        fertilizer_on_hold=sum(1 for p in due if p.fertilizer.weather == "hold"),
        litres_needed=sum(p.irrigation.total_litres for p in counted),
        litres_crops_counted=len(counted),
    )


def build_actions(plans: Sequence[CropPlan]) -> list[Action]:
    """The things to do, with the most urgent first."""
    actions: list[Action] = []
    for plan in plans:
        irrigation = plan.irrigation
        if irrigation.status in WATERING_STATUSES:
            actions.append(
                Action(
                    crop_id=plan.crop_id,
                    crop_name=plan.crop_name,
                    kind="irrigation",
                    priority="high" if irrigation.status == "irrigate_soon" else "medium",
                    text=f"{plan.crop_name}: {irrigation.headline}",
                )
            )

        fertilizer = plan.fertilizer
        if fertilizer is not None and fertilizer.current is not None:
            if fertilizer.weather == "hold":
                text = (
                    f"{plan.crop_name}: delay {fertilizer.current.title.lower()}, "
                    "heavy rain is forecast"
                )
            else:
                text = f"{plan.crop_name}: {fertilizer.summary}"
            actions.append(
                Action(
                    crop_id=plan.crop_id,
                    crop_name=plan.crop_name,
                    kind="fertilizer",
                    priority="medium",
                    text=text,
                )
            )

    actions.sort(key=lambda a: (PRIORITY_RANK[a.priority], a.crop_name, a.kind))
    return actions