from datetime import date, timedelta

from app.schemas.weather import Condition, DailyForecast
from app.services import resource_logic as rl

BASE = date(2026, 10, 8)  # a Thursday
LAT = 10.77
PADDY_STARTS = [0, 18, 54, 78, 108]  # stage start days for a 120-day cycle


def day(offset, tmin=24.0, tmax=33.0, rain=0.0):
    return DailyForecast(
        date=BASE + timedelta(days=offset),
        temp_min_c=tmin,
        temp_max_c=tmax,
        rain_chance_pct=10 if rain == 0 else 80,
        rain_mm=rain,
        wind_max_kmh=10,
        humidity_pct=60,
        condition=Condition(label="Clear", icon="clear"),
    )


def week(tmin=24.0, tmax=33.0, rain_by_day=None):
    rain_by_day = rain_by_day or {}
    return [day(i, tmin, tmax, rain_by_day.get(i, 0.0)) for i in range(5)]


# ---------- evapotranspiration ----------
def test_extraterrestrial_radiation_stays_in_a_sensible_range():
    for day_of_year in (1, 80, 172, 265, 355):
        assert 11.5 < rl.extraterrestrial_radiation_mm(LAT, day_of_year) < 17.0


def test_radiation_is_higher_in_june_than_december():
    june = rl.extraterrestrial_radiation_mm(LAT, 172)
    december = rl.extraterrestrial_radiation_mm(LAT, 355)
    assert june > december


def test_hargreaves_et0_typical_day():
    ra = rl.extraterrestrial_radiation_mm(LAT, 281)
    et0 = rl.hargreaves_et0(24.0, 33.0, ra)
    assert 4.0 < et0 < 5.2


def test_et0_grows_with_temperature_range():
    ra = rl.extraterrestrial_radiation_mm(LAT, 281)
    assert rl.hargreaves_et0(22.0, 34.0, ra) > rl.hargreaves_et0(26.0, 30.0, ra)


def test_et0_handles_zero_temperature_range():
    assert rl.hargreaves_et0(30.0, 30.0, 14.0) > 0
    assert rl.hargreaves_et0(31.0, 30.0, 14.0) > 0


def test_effective_rain():
    assert rl.effective_rain(0.0) == 0.0
    assert rl.effective_rain(1.9) == 0.0
    assert rl.effective_rain(2.0) == 1.6
    assert rl.effective_rain(10.0) == 8.0
    assert rl.effective_rain(50.0) == 40.0


def test_crop_kc():
    assert rl.crop_kc("Tomato", 2) == 1.15
    assert rl.crop_kc("Tomato", 99) == 0.8
    assert rl.crop_kc("Tomato", None) is None
    assert rl.crop_kc("Rice (Paddy)", 1) is None
    assert rl.crop_kc("Dragon Fruit", 1) is None


# ---------- irrigation ----------
def test_dry_week_means_plan_irrigation():
    advice = rl.irrigation_advice("Tomato", "Flowering", 2, week(), LAT)

    assert advice.status == "plan_irrigation"
    assert advice.irrigate_by == BASE + timedelta(days=2)
    assert advice.headline == "Plan to irrigate on Saturday"
    assert len(advice.days) == 5
    assert advice.days[0].kc == 1.15
    assert 4.0 < advice.days[0].et0_mm < 5.2
    assert 20 < advice.total_need_mm < 32
    assert advice.suggested_depth_mm == 25.0
    assert advice.approximate is False


def test_hot_week_means_irrigate_by_tomorrow():
    advice = rl.irrigation_advice("Sugarcane", "Flowering", 2, week(tmin=26.0, tmax=38.0), LAT)

    assert advice.status == "irrigate_soon"
    assert advice.irrigate_by == BASE + timedelta(days=1)
    assert advice.headline == "Irrigate by tomorrow"


def test_irrigate_today_when_soil_is_nearly_dry():
    advice = rl.irrigation_advice(
        "Tomato", "Flowering", 2, week(), LAT, soil_water_start_mm=2.0
    )

    assert advice.status == "irrigate_soon"
    assert advice.irrigate_by == BASE
    assert advice.headline == "Irrigate today"


def test_rain_tomorrow_removes_the_need():
    advice = rl.irrigation_advice(
        "Tomato", "Flowering", 2, week(rain_by_day={1: 25.0}), LAT
    )

    assert advice.status == "not_needed"
    assert advice.irrigate_by is None
    assert advice.suggested_depth_mm is None
    assert advice.days[1].effective_rain_mm == 20.0
    assert advice.total_effective_rain_mm == 20.0
    assert "Rain of about 25 mm is forecast tomorrow." in advice.detail


def test_soil_storage_is_capped():
    advice = rl.irrigation_advice(
        "Tomato", "Flowering", 2, week(rain_by_day={0: 100.0}), LAT
    )

    assert advice.days[0].soil_water_mm == 25.0
    assert advice.status == "not_needed"


def test_low_demand_crop_needs_no_irrigation():
    advice = rl.irrigation_advice("Tapioca (Cassava)", "Harvest-ready", 3, week(), LAT)
    assert advice.status == "not_needed"


def test_water_volumes():
    with_area = rl.irrigation_advice("Tomato", "Flowering", 2, week(), LAT, area_acres=2.0)
    assert with_area.litres_per_acre == 101175
    assert with_area.total_litres == 202350

    without_area = rl.irrigation_advice("Tomato", "Flowering", 2, week(), LAT)
    assert without_area.litres_per_acre == 101175
    assert without_area.total_litres is None


def test_not_planted_crop():
    advice = rl.irrigation_advice("Tomato", "Planned", None, week(), LAT)
    assert advice.status == "not_planted"
    assert advice.days == []


def test_no_forecast_or_unknown_crop():
    assert rl.irrigation_advice("Tomato", "Flowering", 2, [], LAT).status == "no_guidance"
    assert rl.irrigation_advice("Dragon Fruit", "x", 1, week(), LAT).status == "no_guidance"


# ---------- paddy (flooded) ----------
def test_paddy_stage_guidance():
    flowering = rl.irrigation_advice("Rice (Paddy)", "Panicle / Flowering", 2, week(), LAT)
    assert flowering.status == "flooded"
    assert flowering.headline == "Do not let the field dry out"
    assert "most water-sensitive" in flowering.detail
    assert flowering.days == []

    harvest = rl.irrigation_advice("Rice (Paddy)", "Harvest-ready", 4, week(), LAT)
    assert harvest.headline == "Drain the field before harvest"
    assert "top up" not in harvest.detail

    unknown = rl.irrigation_advice("Rice (Paddy)", "Some new stage", 1, week(), LAT)
    assert unknown.headline == "Manage standing water"


def test_paddy_heavy_rain_warning():
    advice = rl.irrigation_advice(
        "Rice (Paddy)", "Tillering", 1, week(rain_by_day={1: 70.0}), LAT
    )
    assert "bunds" in advice.detail
    assert "drainage" in advice.detail


def test_paddy_dry_week_suggests_top_up():
    advice = rl.irrigation_advice("Rice (Paddy)", "Tillering", 1, week(), LAT)
    assert "top up the standing water" in advice.detail


# ---------- fertilizer ----------
def test_paddy_tillering_current_and_upcoming():
    advice = rl.fertilizer_advice("Rice (Paddy)", 1, 20, PADDY_STARTS, 10, week())

    assert advice.current.title == "First top dressing"
    assert advice.upcoming.title == "Second top dressing"
    assert advice.days_until_upcoming == 34
    assert advice.summary == "First top dressing applies at this stage."
    assert advice.weather == "ok"
    assert advice.disclaimer


def test_paddy_seedling_days_until_next():
    advice = rl.fertilizer_advice("Rice (Paddy)", 0, 3, PADDY_STARTS, 10, week())

    assert advice.current.title == "Basal dose"
    assert advice.upcoming.title == "First top dressing"
    assert advice.days_until_upcoming == 15


def test_no_more_fertilizer_late_in_the_season():
    advice = rl.fertilizer_advice("Rice (Paddy)", 3, 90, PADDY_STARTS, 10, week())

    assert advice.current is None
    assert advice.upcoming is None
    assert advice.days_until_upcoming is None
    assert advice.summary == "No further fertilizer is needed this season."


def test_stage_start_days_missing_gives_no_countdown():
    advice = rl.fertilizer_advice("Rice (Paddy)", 1, 20, None, 10, week())
    assert advice.upcoming.title == "Second top dressing"
    assert advice.days_until_upcoming is None


def test_perennial_dose_due_now():
    advice = rl.fertilizer_advice("Coconut", 2, 3000, None, 10, week())

    assert advice.current.title == "Second split dose"
    assert advice.upcoming.title == "First split dose"
    assert advice.days_until_upcoming == 210
    assert advice.summary == "Second split dose is due this month."


def test_perennial_between_doses():
    advice = rl.fertilizer_advice("Coconut", 2, 3000, None, 7, week())

    assert advice.current is None
    assert advice.upcoming.title == "Second split dose"
    assert advice.days_until_upcoming == 60
    assert "about 2 months" in advice.summary


def test_fertilizer_weather_gate():
    starts = [0, 11, 50, 72, 99]

    hold = rl.fertilizer_advice("Tomato", 1, 20, starts, 10, week(rain_by_day={1: 30.0}))
    assert hold.weather == "hold"
    assert "tomorrow" in hold.weather_message

    caution = rl.fertilizer_advice("Tomato", 1, 20, starts, 10, week(rain_by_day={0: 12.0}))
    assert caution.weather == "caution"
    assert "today" in caution.weather_message

    fine = rl.fertilizer_advice("Tomato", 1, 20, starts, 10, week(rain_by_day={1: 5.0}))
    assert fine.weather == "ok"
    assert fine.weather_message is None

    no_forecast = rl.fertilizer_advice("Tomato", 1, 20, starts, 10, [])
    assert no_forecast.weather == "ok"


def test_fertilizer_not_planted_or_no_schedule():
    assert rl.fertilizer_advice("Tomato", None, 0, None, 10, week()) is None
    assert rl.fertilizer_advice("Dragon Fruit", 1, 5, None, 10, week()) is None


def test_approximate_timing_flag():
    assert rl.fertilizer_advice("Cardamom", 2, 700, None, 10, week()).approximate_timing is True
    assert rl.fertilizer_advice("Coconut", 2, 3000, None, 10, week()).approximate_timing is False