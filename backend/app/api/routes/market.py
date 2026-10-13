from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.crop_type import CropType
from app.models.user import User
from app.schemas.market import AvailableCrop, PriceBoard, PriceTrend
from app.services import market_service

router = APIRouter(prefix="/market", tags=["Market"])


def _crop_type_or_404(db: Session, crop_type_id: int) -> CropType:
    crop_type = db.get(CropType, crop_type_id)
    if crop_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Crop type not found")
    return crop_type


@router.get("/crops", response_model=list[AvailableCrop])
def available_crops(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return market_service.list_available_crops(db, current_user.state)


@router.get("/prices", response_model=PriceBoard)
def price_board(
    crop_type_id: int = Query(..., ge=1),
    variety: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crop_type = _crop_type_or_404(db, crop_type_id)
    return market_service.get_price_board(
        db, crop_type, current_user.state, current_user.district, variety
    )


@router.get("/trend", response_model=PriceTrend)
def price_trend(
    crop_type_id: int = Query(..., ge=1),
    days: int = Query(default=90, ge=7, le=365),
    variety: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crop_type = _crop_type_or_404(db, crop_type_id)
    return market_service.get_price_trend(db, crop_type, current_user.state, days, variety)