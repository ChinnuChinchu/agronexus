from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.crop_type import CropType
from app.models.user import User
from app.schemas.disease import PredictionResult, ScanRead, SupportedCrop
from app.services import disease_service
from app.services.disease_classifier import (
    ClassifierUnavailable,
    DiseaseClassifier,
    get_classifier,
)
from app.services.disease_image import InvalidImage
from app.core.rate_limit import predict_limiter

router = APIRouter(prefix="/disease", tags=["Disease detection"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def classifier_dependency() -> DiseaseClassifier:
    try:
        return get_classifier()
    except ClassifierUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


def _read_photo(upload: UploadFile) -> bytes:
    data = upload.file.read(MAX_UPLOAD_BYTES + 1)  # never read more than the limit
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413, "The photo is too large. Please use a photo under 5 MB"
        )
    return data


@router.get("/crops", response_model=list[SupportedCrop])
def supported_crops(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    classifier: DiseaseClassifier = Depends(classifier_dependency),
):
    crops = disease_service.list_supported_crop_types(db, classifier)
    return [SupportedCrop(crop_type_id=c.id, name=c.name) for c in crops]


@router.post("/predict", response_model=PredictionResult)
def predict(
    crop_type_id: int = Form(..., ge=1),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    classifier: DiseaseClassifier = Depends(classifier_dependency),
):
    predict_limiter.hit(f"user:{current_user.id}")

    crop_type = db.get(CropType, crop_type_id)
    if crop_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Crop type not found")
    if not disease_service.is_supported(classifier, crop_type):
        raise HTTPException(
            422, f"Disease detection does not support {crop_type.name} yet"
        )

    data = _read_photo(image)
    try:
        return disease_service.analyse_photo(db, current_user, crop_type, data, classifier)
    except InvalidImage as exc:
        raise HTTPException(422, str(exc))


@router.get("/history", response_model=list[ScanRead])
def history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return disease_service.list_scans(db, current_user.id, limit, offset)


@router.delete("/history/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_item(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = disease_service.get_scan(db, current_user.id, scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    disease_service.delete_scan(db, scan)