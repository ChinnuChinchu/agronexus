import datetime as dt
from typing import Literal

from pydantic import BaseModel

from app.schemas.weather import LocationInfo

IrrigationStatus = Literal[
    "irrigate_soon", "plan_irrigation", "not_needed", "flooded", "not_planted", "no_guidance"
]
FertilizerWeather = Literal["ok", "caution", "hold"]


class WaterDay(BaseModel):
    date: dt.date
    et0_mm: float
    kc: float
    crop_need_mm: float
    rain_mm: float
    effective_rain_mm: float
    soil_water_mm: float


class IrrigationAdvice(BaseModel):
    status: IrrigationStatus
    headline: str
    detail: str
    irrigate_by: dt.date | None = None
    days: list[WaterDay] = []
    total_need_mm: float = 0.0
    total_effective_rain_mm: float = 0.0
    suggested_depth_mm: float | None = None
    litres_per_acre: int | None = None
    total_litres: int | None = None
    approximate: bool = False


class FertilizerStepInfo(BaseModel):
    title: str
    nutrients: str
    note: str


class FertilizerAdvice(BaseModel):
    summary: str
    current: FertilizerStepInfo | None = None
    upcoming: FertilizerStepInfo | None = None
    days_until_upcoming: int | None = None
    weather: FertilizerWeather = "ok"
    weather_message: str | None = None
    approximate_timing: bool = False
    disclaimer: str
    
class Action(BaseModel):
    crop_id: int
    crop_name: str
    kind: Literal["irrigation", "fertilizer"]
    priority: Literal["high", "medium"]
    text: str


class CropPlan(BaseModel):
    crop_id: int
    crop_name: str
    crop_type: str
    stage: str
    progress_pct: float
    area_acres: float | None
    irrigation: IrrigationAdvice
    fertilizer: FertilizerAdvice | None


class PlanSummary(BaseModel):
    crops: int
    need_water_soon: int
    fertilizer_due: int
    fertilizer_on_hold: int
    litres_needed: int
    litres_crops_counted: int


class ResourcePlan(BaseModel):
    location: LocationInfo | None
    as_of: dt.date | None
    summary: PlanSummary
    actions: list[Action]
    crops: list[CropPlan]
    note: str