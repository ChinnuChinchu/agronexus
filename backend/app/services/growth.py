from datetime import date, datetime, timedelta, timezone

from app.schemas.crop import GrowthInfo

IST = timezone(timedelta(hours=5, minutes=30))
DAYS_PER_MONTH = 30.4375


def today_local() -> date:
    return datetime.now(IST).date()


def _months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def _clamp_pct(value: float) -> float:
    return round(min(max(value, 0.0), 100.0), 1)


def _seasonal_stage_index(stages: list[dict], pct: float) -> int:
    for i, stage in enumerate(stages):
        if stage["start_pct"] <= pct < stage["end_pct"]:
            return i
    return len(stages) - 1


def _perennial_stage_index(stages: list[dict], age_months: int) -> int:
    for i, stage in enumerate(stages):
        end = stage["end_month"]
        if age_months >= stage["start_month"] and (end is None or age_months < end):
            return i
    return len(stages) - 1


def calculate_growth(crop, today: date | None = None) -> GrowthInfo:
    today = today or today_local()
    crop_type = crop.crop_type
    stages = crop_type.stages
    stage_names = [s["name"] for s in stages]
    age_days = max((today - crop.planting_date).days, 0)

    def info(stage, index, pct, days_to_harvest=None, overdue=False) -> GrowthInfo:
        return GrowthInfo(
            stage=stage,
            stage_index=index,
            stages=stage_names,
            progress_pct=pct,
            age_days=age_days,
            days_to_harvest=days_to_harvest,
            is_overdue=overdue,
        )

    if crop.status == "harvested":
        return info("Harvested", None, 100.0)
    if crop.status == "failed":
        return info("Failed", None, 0.0)

    days_to_harvest = (
        (crop.expected_harvest_date - today).days if crop.expected_harvest_date else None
    )

    if today < crop.planting_date:
        return info("Planned", None, 0.0, days_to_harvest)

    overdue = days_to_harvest is not None and days_to_harvest < 0

    if crop_type.cycle == "perennial":
        age_months = _months_between(crop.planting_date, today)
        index = _perennial_stage_index(stages, age_months)
        if age_months >= crop_type.bearing_age_months:
            pct = 100.0
        else:
            pct = _clamp_pct(age_days / (crop_type.bearing_age_months * DAYS_PER_MONTH) * 100)
    else:
        if crop.expected_harvest_date:
            cycle_days = (crop.expected_harvest_date - crop.planting_date).days
        else:
            cycle_days = crop_type.duration_days or 1
        cycle_days = max(cycle_days, 1)
        pct = _clamp_pct(age_days / cycle_days * 100)
        index = _seasonal_stage_index(stages, pct)

    return info(stages[index]["name"], index, pct, days_to_harvest, overdue)