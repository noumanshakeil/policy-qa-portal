from fastapi import APIRouter
from backend.api import health, policies, ui
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(policies.router, prefix="/api", tags=["policies"])
api_router.include_router(ui.router, tags=["ui"])
