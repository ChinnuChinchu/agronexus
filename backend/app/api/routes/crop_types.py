from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.crop import CropTypeRead
from app.services import crop_service

router = APIRouter(prefix="/crop-types", tags=["Crop types"])


@router.get("", response_model=list[CropTypeRead])
def list_crop_types(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return crop_service.list_crop_types(db)