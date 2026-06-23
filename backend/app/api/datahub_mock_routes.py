from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.datahub_mock_service import (
    create_headlines_batch,
    enterprise_placeholder,
    get_batch,
    get_headlines_contract,
    list_mock_headlines,
)


router = APIRouter(prefix="/datahub/mock", tags=["datahub-mock"])


class HeadlinesBatchRequest(BaseModel):
    source: str = Field(default="rsshub", min_length=1)
    limit: int = Field(default=20, ge=1, le=200)


@router.get("/headlines")
def get_mock_headlines(limit: int = Query(default=20, ge=1, le=200)):
    return {
        "source": "rsshub",
        **get_headlines_contract(),
        "items": list_mock_headlines(limit=limit),
    }


@router.get("/enterprise")
def get_mock_enterprise():
    return enterprise_placeholder()


@router.post("/batches")
def create_mock_batch(request: HeadlinesBatchRequest):
    return create_headlines_batch(source=request.source, limit=request.limit)


@router.get("/batches/{batch_id}")
def get_mock_batch(batch_id: str):
    payload = get_batch(batch_id)
    return payload or {"batch_id": batch_id, "status": "missing"}
