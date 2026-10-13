from datetime import date, timedelta
from types import SimpleNamespace

from app.db.seed import GENERAL_STAGES, perennial
from app.services.growth import calculate_growth

TODAY = date(2026, 10, 7)
STAGE_NAMES = [s["name"] for s in GENERAL_STAGES]


def days(n: int) -> date:
    return TODAY + timedelta(days=n)


def seasonal_type(duration: int = 100):
    return SimpleNamespace(
        cycle="seasonal",
        duration_days=duration,
        bearing_age_months=None,
        stages=GENERAL_STAGES,
    )


def coconut_type():
    return SimpleNamespace(**perennial("Coconut", "Plantation", 72))


def make_crop(crop_type, planting, expected=None, status="growing"):
    return SimpleNamespace(
        crop_type=crop_type,
        planting_date=planting,
        expected_harvest_date=expected,
        status=status,
    )


# ---------- seasonal crops ----------
def test_seasonal_on_planting_day():
    crop = make_crop(seasonal_type(), days(0), days(100))
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Germination"
    assert info.stage_index == 0
    assert info.progress_pct == 0.0
    assert info.days_to_harvest == 100
    assert info.is_overdue is False
    assert info.stages == STAGE_NAMES


def test_seasonal_midpoint():
    crop = make_crop(seasonal_type(), days(-50), days(50))
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Flowering"
    assert info.progress_pct == 50.0
    assert info.age_days == 50
    assert info.days_to_harvest == 50


def test_seasonal_harvest_ready():
    crop = make_crop(seasonal_type(), days(-95), days(5))
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Harvest-ready"
    assert info.progress_pct == 95.0
    assert info.is_overdue is False


def test_seasonal_overdue():
    crop = make_crop(seasonal_type(), days(-120), days(-20))
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Harvest-ready"
    assert info.progress_pct == 100.0
    assert info.days_to_harvest == -20
    assert info.is_overdue is True


def test_seasonal_without_expected_date_uses_catalog_duration():
    crop = make_crop(seasonal_type(duration=120), days(-60), None)
    info = calculate_growth(crop, TODAY)
    assert info.progress_pct == 50.0
    assert info.stage == "Flowering"
    assert info.days_to_harvest is None


def test_planting_in_the_future_is_planned():
    crop = make_crop(seasonal_type(), days(10), days(110))
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Planned"
    assert info.stage_index is None
    assert info.progress_pct == 0.0
    assert info.age_days == 0


def test_harvested_crop():
    crop = make_crop(seasonal_type(), days(-100), days(0), status="harvested")
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Harvested"
    assert info.progress_pct == 100.0
    assert info.is_overdue is False


def test_failed_crop():
    crop = make_crop(seasonal_type(), days(-30), days(70), status="failed")
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Failed"
    assert info.progress_pct == 0.0


# ---------- perennial crops ----------
def test_perennial_establishment():
    crop = make_crop(coconut_type(), days(-182))
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Establishment"
    assert info.stage_index == 0
    assert info.days_to_harvest is None


def test_perennial_juvenile_growth():
    crop = make_crop(coconut_type(), days(-1095))
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Juvenile growth"
    assert 49 <= info.progress_pct <= 51


def test_perennial_bearing():
    crop = make_crop(coconut_type(), days(-3000))
    info = calculate_growth(crop, TODAY)
    assert info.stage == "Bearing"
    assert info.stage_index == 2
    assert info.progress_pct == 100.0