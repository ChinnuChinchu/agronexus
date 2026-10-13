from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.crop import Crop
from app.models.user import User
from app.schemas.crop import CropCreate, CropRead, CropStatus, CropUpdate, HarvestRequest
from app.services import crop_service
from app.services.crop_service import CropValidationError

router = APIRouter(prefix="/crops", tags=["Crops"])


def _owned_crop_or_404(db: Session, user: User, crop_id: int) -> Crop:
    crop = crop_service.get_crop(db, user.id, crop_id)
    if crop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Crop not found")
    return crop


# def _unprocessable(exc: CropValidationError) -> HTTPException:
#     return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

def _unprocessable(exc: CropValidationError) -> HTTPException:
    return HTTPException(422, str(exc))

@router.get("", response_model=list[CropRead])
def list_my_crops(
    status_filter: CropStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crops = crop_service.list_crops(db, current_user.id, status_filter, limit, offset)
    return [crop_service.to_crop_read(c) for c in crops]


@router.post("", response_model=CropRead, status_code=status.HTTP_201_CREATED)
def create_crop(
    data: CropCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        crop = crop_service.create_crop(db, current_user, data)
    except CropValidationError as exc:
        raise _unprocessable(exc)
    return crop_service.to_crop_read(crop)


@router.get("/{crop_id}", response_model=CropRead)
def get_crop(
    crop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crop_service.to_crop_read(_owned_crop_or_404(db, current_user, crop_id))


@router.put("/{crop_id}", response_model=CropRead)
def update_crop(
    crop_id: int,
    data: CropUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crop = _owned_crop_or_404(db, current_user, crop_id)
    try:
        crop = crop_service.update_crop(db, crop, data)
    except CropValidationError as exc:
        raise _unprocessable(exc)
    return crop_service.to_crop_read(crop)


@router.post("/{crop_id}/harvest", response_model=CropRead)
def harvest_crop(
    crop_id: int,
    data: HarvestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crop = _owned_crop_or_404(db, current_user, crop_id)
    try:
        crop = crop_service.harvest_crop(db, crop, data)
    except CropValidationError as exc:
        raise _unprocessable(exc)
    return crop_service.to_crop_read(crop)


@router.delete("/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crop(
    crop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crop = _owned_crop_or_404(db, current_user, crop_id)
    crop_service.delete_crop(db, crop)