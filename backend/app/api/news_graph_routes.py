from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import requests

from config.settings import settings


router = APIRouter(prefix="/news-graph", tags=["News Graph"])


class EntityHeatRankingCalculateRequest(BaseModel):
    period_type: str = "daily"
    as_of: Optional[str] = None
    entity_type: Optional[str] = None
    limit_per_type: int = 50


@router.get("/heat-rankings")
def get_entity_heat_rankings(
    period_type: str = Query("daily", description="daily or weekly"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD or ISO datetime"),
    entity_type: str = Query("Enterprise", description="Enterprise/Product/Person/Technology/Region"),
    limit: int = Query(50, ge=1, le=500),
):
    graphiti_base = str(settings.GRAPHITI_BASE_URL).rstrip("/")
    endpoint = f"{graphiti_base}/api/entity-heat-rankings"
    params = {
        "period_type": period_type,
        "date": date,
        "entity_type": entity_type,
        "limit": limit,
    }
    try:
        response = requests.get(endpoint, params=params, timeout=settings.GRAPHITI_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Graphiti heat rankings query failed: {exc}",
        ) from exc


@router.post("/heat-rankings/calculate")
def calculate_entity_heat_rankings(request: EntityHeatRankingCalculateRequest):
    graphiti_base = str(settings.GRAPHITI_BASE_URL).rstrip("/")
    endpoint = f"{graphiti_base}/api/calculate/entity-heat-rankings"
    try:
        response = requests.post(
            endpoint,
            json=request.model_dump(),
            timeout=settings.GRAPHITI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Graphiti heat rankings calculation failed: {exc}",
        ) from exc
