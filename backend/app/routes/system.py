from fastapi import APIRouter

from app.schemas.api import SystemStatsResponse
from app.services.container import get_container

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/stats", response_model=SystemStatsResponse)
def system_stats() -> SystemStatsResponse:
    container = get_container()
    return SystemStatsResponse(**container["metrics"].get_system_summary())
