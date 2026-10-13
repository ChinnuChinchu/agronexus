from datetime import date
from types import SimpleNamespace

from app.db.seed import GENERAL_STAGES
from app.schemas.resources import (
    CropPlan,
    FertilizerAdvice,
    FertilizerStepInfo,
    IrrigationAdvice,
)
from app.services import resource_logic as rl
from app.services.resource_service import stage_start_days


def irrigation(status, headline="headline", litres=None):
    return IrrigationAdvice(
        status=status, headline=headline, detail="detail", total_litres=litres
    )


def fert(current_title=None, weather="ok"):
    step = (
        FertilizerStepInfo(title=current_title, nutrients="N", note="note")
        if current_title
        else None
    )
    return FertilizerAdvice(
        summary="summary text", current=step, weather=weather, disclaimer="disclaimer"
    )


def plan(crop_id, name, irrigation_advice, fertilizer_advice=None):
    return CropPlan(
        crop_id=crop_id,
        crop_name=name,
        crop_type="Tomato",
        stage="Vegetative growth",
        progress_pct=30.0,
        area_acres=1.0,
        irrigation=irrigation_advice,
        fertilizer=fertilizer_advice,
    )


# ---------- actions ----------
def test_actions_are_sorted_by_priority_then_crop_name():
    plans = [
        plan(1, "C bed", irrigation("not_needed"), fert("Basal dose", weather="hold")),
        plan(
            2,
            "B bed",
            irrigation("plan_irrigation", "Plan to irrigate on Saturday"),
            fert("First top dressing"),
        ),
        plan(3, "A bed", irrigation("irrigate_soon", "Irrigate today")),
    ]
    actions = rl.build_actions(plans)

    assert [(a.crop_name, a.kind, a.priority) for a in actions] == [
        ("A bed", "irrigation", "high"),
        ("B bed", "fertilizer", "medium"),
        ("B bed", "irrigation", "medium"),
        ("C bed", "fertilizer", "medium"),
    ]
    assert actions[0].text == "A bed: Irrigate today"
    assert actions[1].text == "B bed: summary text"
    assert actions[2].text == "B bed: Plan to irrigate on Saturday"


def test_hold_replaces_the_due_text():
    plans = [plan(1, "C bed", irrigation("not_needed"), fert("Basal dose", weather="hold"))]
    actions = rl.build_actions(plans)
    assert actions[0].text == "C bed: delay basal dose, heavy rain is forecast"


def test_no_actions_when_nothing_is_needed():
    plans = [
        plan(1, "Paddy", irrigation("flooded"), fert(None)),
        plan(2, "Planned", irrigation("not_planted"), None),
        plan(3, "Tomato", irrigation("not_needed"), None),
    ]
    assert rl.build_actions(plans) == []


# ---------- summary ----------
def test_summary_counts():
    plans = [
        plan(1, "A", irrigation("irrigate_soon", litres=100000), fert("Basal dose")),
        plan(2, "B", irrigation("plan_irrigation"), fert("Top dressing", weather="hold")),
        plan(3, "C", irrigation("not_needed"), None),
    ]
    summary = rl.summarise(plans)

    assert summary.crops == 3
    assert summary.need_water_soon == 2
    assert summary.fertilizer_due == 2
    assert summary.fertilizer_on_hold == 1
    assert summary.litres_needed == 100000
    assert summary.litres_crops_counted == 1


def test_summary_litres_only_count_crops_that_need_water():
    plans = [plan(1, "A", irrigation("not_needed", litres=5000))]
    summary = rl.summarise(plans)
    assert summary.litres_needed == 0
    assert summary.litres_crops_counted == 0


# ---------- stage start days ----------
def crop(cycle="seasonal", duration=100, planting=date(2026, 9, 1), expected=date(2026, 12, 10)):
    return SimpleNamespace(
        crop_type=SimpleNamespace(cycle=cycle, duration_days=duration, stages=GENERAL_STAGES),
        planting_date=planting,
        expected_harvest_date=expected,
    )


def test_stage_start_days_seasonal_with_expected_date():
    assert stage_start_days(crop()) == [0, 10, 45, 65, 90]


def test_stage_start_days_falls_back_to_catalog_duration():
    assert stage_start_days(crop(duration=120, expected=None)) == [0, 12, 54, 78, 108]


def test_stage_start_days_perennial_or_invalid():
    assert stage_start_days(crop(cycle="perennial", expected=None)) is None
    assert stage_start_days(crop(duration=None, expected=date(2026, 9, 1))) is None