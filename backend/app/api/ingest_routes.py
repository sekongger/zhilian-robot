from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List

router = APIRouter(prefix="/ingest", tags=["统一接入"])


class IngestRequest(BaseModel):
    resource_type: str
    source_id: str
    content: Dict
    metadata: Dict = {}
    options: Dict = {}


class BatchIngestRequest(BaseModel):
    documents: List[IngestRequest] = []
    batch_options: Dict = {}


@router.post("/document")
async def ingest_document(req: IngestRequest):
    return {
        "code": 200,
        "message": "accepted",
        "data": {
            "doc_id": "DOC_PLACEHOLDER",
            "resource_doc_id": "DOC_PLACEHOLDER",
            "status": "pending",
        },
    }


@router.post("/batch")
async def ingest_batch(req: BatchIngestRequest):
    return {
        "code": 200,
        "message": "accepted",
        "data": {
            "batch_id": "BATCH_PLACEHOLDER",
            "total_count": len(req.documents),
            "accepted_count": len(req.documents),
            "rejected_count": 0,
            "rejected_details": [],
        },
    }
