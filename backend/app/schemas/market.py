import datetime as dt
from typing import Literal

from pydantic import BaseModel

SignalLabel = Literal["above_average", "below_average", "stable", "insufficient_data"]

SOURCE_ATTRIBUTION = (
    "Agmarknet (Ministry of Agriculture & Farmers Welfare), via CEDA, Ashoka University"
)


class MarketPriceRow(BaseModel):
    market: str
    district: str
    variety: str
    date: dt.date
    min_price: int
    max_price: int
    modal_price: int
    in_my_district: bool


class PriceSummary(BaseModel):
    average_modal: int
    highest_modal: int
    lowest_modal: int
    markets: int


class PriceBoard(BaseModel):
    crop_type_id: int
    crop_name: str
    state: str
    commodity_names: list[str]
    has_data: bool
    as_of: dt.date | None = None
    days_old: int | None = None
    stale: bool = False
    variety: str | None = None
    varieties: list[str] = []
    summary: PriceSummary | None = None
    markets: list[MarketPriceRow] = []
    unit: str = "Rs per quintal"
    source: str = SOURCE_ATTRIBUTION


class TrendPoint(BaseModel):
    date: dt.date
    median_modal: int
    markets: int


class Signal(BaseModel):
    label: SignalLabel
    pct_vs_average: float | None
    average_modal: int | None
    message: str


class PriceTrend(BaseModel):
    crop_type_id: int
    crop_name: str
    state: str
    has_data: bool
    as_of: dt.date | None = None
    days_old: int | None = None
    stale: bool = False
    days: int
    variety: str | None = None
    points: list[TrendPoint] = []
    latest_modal: int | None = None
    change_7d_pct: float | None = None
    change_30d_pct: float | None = None
    signal: Signal | None = None
    unit: str = "Rs per quintal"
    source: str = SOURCE_ATTRIBUTION


class AvailableCrop(BaseModel):
    crop_type_id: int
    name: str
    category: str
    latest_date: dt.date
    days_old: int
    stale: bool