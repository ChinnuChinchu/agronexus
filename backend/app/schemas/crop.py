from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CropStatus = Literal["growing", "harvested", "failed"]


def _clean_name(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Name cannot be empty")
    return value


class CropTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    cycle: str
    duration_days: int | None
    bearing_age_months: int | None


class GrowthInfo(BaseModel):
    stage: str
    stage_index: int | None
    stages: list[str]
    progress_pct: float
    age_days: int
    days_to_harvest: int | None
    is_overdue: bool


class CropCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    crop_type_id: int
    variety: str | None = Field(default=None, max_length=100)
    area_acres: float | None = Field(default=None, gt=0)
    planting_date: date
    expected_harvest_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return _clean_name(value)  # type: ignore[return-value]

    @model_validator(mode="after")
    def check_dates(self):
        if self.expected_harvest_date and self.expected_harvest_date < self.planting_date:
            raise ValueError("Expected harvest date cannot be before the planting date")
        return self


class CropUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    crop_type_id: int | None = None
    variety: str | None = Field(default=None, max_length=100)
    area_acres: float | None = Field(default=None, gt=0)
    planting_date: date | None = None
    expected_harvest_date: date | None = None
    status: Literal["growing", "failed"] | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return _clean_name(value)


class HarvestRequest(BaseModel):
    actual_harvest_date: date | None = None
    yield_quantity: float | None = Field(default=None, gt=0)
    yield_unit: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def check_yield(self):
        if self.yield_quantity is not None and not (self.yield_unit or "").strip():
            raise ValueError("Yield unit is required when a yield quantity is given")
        return self


class CropCore(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    crop_type: CropTypeRead
    variety: str | None
    area_acres: float | None
    planting_date: date
    expected_harvest_date: date | None
    status: CropStatus
    actual_harvest_date: date | None
    yield_quantity: float | None
    yield_unit: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CropRead(CropCore):
    growth: GrowthInfo