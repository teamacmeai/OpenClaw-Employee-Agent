from fastapi import APIRouter

from app.api.routes import device, health, ingest

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(device.router)
api_router.include_router(ingest.router)
