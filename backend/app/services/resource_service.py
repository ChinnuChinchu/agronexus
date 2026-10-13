from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.resources import CropPlan, ResourcePlan
from app.schemas.weather import LocationInfo
from app.services import crop_service, weather_service
from app.services import resource_logic as logic
from app.services.growth import calculate_growth

MAX_ACTIONS = 6
NOTE = (
    "Estimates based on the weather forecast and general crop data. They do not know your "
    "soil type, recent rain or irrigation method. Use them as guidance and adjust to what you "
    "see in your field."
)


def stage_start_days(crop) -> list[int] | None:
    """The day (counted from planting) on which each growth stage starts, for seasonal crops."""
    crop_type = crop.crop_type
    if crop_type.cycle != "seasonal":
        return None

    if crop.expected_harvest_date:
        cycle_days = (crop.expected_harvest_date - crop.planting_date).days
    else:
        cycle_days = crop_type.duration_days or 0
    if cycle_days <= 0:
        return None

    return [round(stage["start_pct"] / 100 * cycle_days) for stage in crop_type.stages]


def get_resource_plan(db: Session, user: User) -> ResourcePlan:
    crops = crop_service.list_crops(db, user.id, "growing", 100)
    if not crops:
        return ResourcePlan(
            location=None,
            as_of=None,
            summary=logic.summarise([]),
            actions=[],
            crops=[],
            note=NOTE,
        )

    place, daily, today = weather_service.get_daily_forecast(user)

    plans: list[CropPlan] = []
    for crop in crops:
        growth = calculate_growth(crop, today)
        name = crop.crop_type.name
        plans.append(
            CropPlan(
                crop_id=crop.id,
                crop_name=crop.name,
                crop_type=name,
                stage=growth.stage,
                progress_pct=growth.progress_pct,
                area_acres=crop.area_acres,
                irrigation=logic.irrigation_advice(
                    name, growth.stage, growth.stage_index, daily, place.lat, crop.area_acres
                ),
                fertilizer=logic.fertilizer_advice(
                    name,
                    growth.stage_index,
                    growth.age_days,
                    stage_start_days(crop),
                    today.month,
                    daily,
                ),
            )
        )

    return ResourcePlan(
        location=LocationInfo(
            name=place.name,
            state=place.state,
            country=place.country,
            lat=place.lat,
            lon=place.lon,
        ),
        as_of=today,
        summary=logic.summarise(plans),
        actions=logic.build_actions(plans)[:MAX_ACTIONS],
        crops=plans,
        note=NOTE,
    )