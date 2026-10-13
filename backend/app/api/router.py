from fastapi import APIRouter

from app.api.routes import auth, crop_types, crops, disease, market, resources, users, weather

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(crop_types.router)
api_router.include_router(crops.router)
api_router.include_router(weather.router)
api_router.include_router(market.router)
api_router.include_router(resources.router)
api_router.include_router(disease.router)