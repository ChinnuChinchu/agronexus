from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.weather import WeatherReport
from app.services import openweather as ow
from app.services import weather_service
from app.services.weather_service import LocationNotSet

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("", response_model=WeatherReport)
def get_weather(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return weather_service.get_weather_report(db, current_user)
    except LocationNotSet as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except ow.LocationNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except ow.WeatherError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))