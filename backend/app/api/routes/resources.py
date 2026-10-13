from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.resources import ResourcePlan
from app.services import openweather as ow
from app.services import resource_service
from app.services.weather_service import LocationNotSet

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("/plan", response_model=ResourcePlan)
def get_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return resource_service.get_resource_plan(db, current_user)
    except LocationNotSet as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except ow.LocationNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except ow.WeatherError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))