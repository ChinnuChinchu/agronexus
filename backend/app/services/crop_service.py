from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crop import Crop
from app.models.crop_type import CropType
from app.models.user import User
from app.schemas.crop import CropCore, CropCreate, CropRead, CropUpdate, HarvestRequest
from app.services.growth import calculate_growth, today_local


class CropValidationError(Exception):
    """A business rule was violated. The message is safe to show to the user."""


# ---------- crop types ----------
def list_crop_types(db: Session) -> list[CropType]:
    stmt = select(CropType).order_by(CropType.category, CropType.name)
    return list(db.scalars(stmt))


# ---------- helpers ----------
def to_crop_read(crop: Crop, today: date | None = None) -> CropRead:
    core = CropCore.model_validate(crop)
    return CropRead(**core.model_dump(), growth=calculate_growth(crop, today))


def _validate_rules(crop_type: CropType, planting: date, expected: date | None) -> None:
    if expected is not None and expected < planting:
        raise CropValidationError("Expected harvest date cannot be before the planting date")
    if crop_type.cycle == "seasonal" and expected is None:
        raise CropValidationError("Expected harvest date is required for seasonal crops")


def _get_crop_type(db: Session, crop_type_id: int) -> CropType:
    crop_type = db.get(CropType, crop_type_id)
    if crop_type is None:
        raise CropValidationError("Unknown crop type")
    return crop_type


# ---------- crops ----------
def get_crop(db: Session, user_id: int, crop_id: int) -> Crop | None:
    stmt = select(Crop).where(Crop.id == crop_id, Crop.user_id == user_id)
    return db.scalar(stmt)


def list_crops(
    db: Session,
    user_id: int,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Crop]:
    stmt = select(Crop).where(Crop.user_id == user_id)
    if status:
        stmt = stmt.where(Crop.status == status)
    stmt = stmt.order_by(Crop.planting_date.desc(), Crop.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def create_crop(db: Session, user: User, data: CropCreate) -> Crop:
    crop_type = _get_crop_type(db, data.crop_type_id)
    _validate_rules(crop_type, data.planting_date, data.expected_harvest_date)

    crop = Crop(
        user_id=user.id,
        crop_type_id=crop_type.id,
        name=data.name,
        variety=data.variety,
        area_acres=data.area_acres,
        planting_date=data.planting_date,
        expected_harvest_date=data.expected_harvest_date,
        notes=data.notes,
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


def update_crop(db: Session, crop: Crop, data: CropUpdate) -> Crop:
    changes = data.model_dump(exclude_unset=True)

    # these columns cannot be cleared, so ignore explicit nulls
    for key in ("name", "crop_type_id", "planting_date", "status"):
        if changes.get(key) is None:
            changes.pop(key, None)

    crop_type = crop.crop_type
    if "crop_type_id" in changes:
        crop_type = _get_crop_type(db, changes["crop_type_id"])

    planting = changes.get("planting_date", crop.planting_date)
    expected = changes.get("expected_harvest_date", crop.expected_harvest_date)

    _validate_rules(crop_type, planting, expected)
    if crop.actual_harvest_date and planting > crop.actual_harvest_date:
        raise CropValidationError("Planting date cannot be after the harvest date")

    for field, value in changes.items():
        setattr(crop, field, value)

    if changes.get("status") == "growing":
        crop.actual_harvest_date = None
        crop.yield_quantity = None
        crop.yield_unit = None

    db.commit()
    db.refresh(crop)
    return crop


def harvest_crop(db: Session, crop: Crop, data: HarvestRequest) -> Crop:
    if crop.status != "growing":
        raise CropValidationError("Only crops that are currently growing can be harvested")

    today = today_local()
    harvest_date = data.actual_harvest_date or today
    if harvest_date < crop.planting_date:
        raise CropValidationError("Harvest date cannot be before the planting date")
    if harvest_date > today:
        raise CropValidationError("Harvest date cannot be in the future")

    crop.status = "harvested"
    crop.actual_harvest_date = harvest_date
    crop.yield_quantity = data.yield_quantity
    crop.yield_unit = data.yield_unit.strip() if data.yield_unit else None

    db.commit()
    db.refresh(crop)
    return crop


def delete_crop(db: Session, crop: Crop) -> None:
    db.delete(crop)
    db.commit()