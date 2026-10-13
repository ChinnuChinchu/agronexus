import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict

ScanStatus = Literal["ok", "uncertain", "crop_mismatch"]
ScanLevel = Literal["strong", "possible", "uncertain"]


class SupportedCrop(BaseModel):
    crop_type_id: int
    name: str


class Candidate(BaseModel):
    key: str
    name: str
    healthy: bool
    confidence_pct: float


class SimilarCondition(BaseModel):
    key: str
    name: str


class DiseaseGuide(BaseModel):
    key: str
    name: str
    healthy: bool
    urgent: bool
    summary: str
    symptoms: list[str]
    actions: list[str]
    prevention: list[str]
    similar: list[SimilarCondition]


class PredictionResult(BaseModel):
    scan_id: int
    crop: str
    status: ScanStatus
    level: ScanLevel
    headline: str
    message: str
    top: Candidate | None
    alternatives: list[Candidate]
    guide: DiseaseGuide | None
    tips: list[str]
    disclaimer: str


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crop_name: str
    status: ScanStatus
    level: ScanLevel
    result_key: str | None
    result_name: str | None
    confidence_pct: float | None
    healthy: bool
    created_at: dt.datetime