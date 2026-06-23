from __future__ import annotations

from typing import Any, Dict

from app.services.datahub_mock_service import create_headlines_batch, enterprise_placeholder, list_mock_headlines
from app.services.openks_build_job_service import get_build_job as _get_build_job
from app.services.openks_build_job_service import submit_build_job as _submit_build_job


def get_datahub_headlines(*, hours: int = 24, limit: int = 20) -> Dict[str, Any]:
    items = list_mock_headlines(limit=limit)
    return {
        "datahub": "mock",
        "data_source": "rsshub",
        "headlines": [
            {
                "event_id": f"evt_{index + 1}",
                "headline_title": item.get("title"),
                "summary": item.get("summary"),
                "publish_time": item.get("publish_time"),
                "source_url": item.get("source_url"),
                "companies": [],
            }
            for index, item in enumerate(items[:limit])
        ],
        "stats": {
            "event_count": min(len(items), limit),
            "hours": int(hours),
        },
    }


def get_datahub_enterprise(*, name: str = "") -> Dict[str, Any]:
    payload = enterprise_placeholder()
    payload["enterprise"] = {
        "enterprise_name": str(name or "").strip() or "示例企业",
        "status": "placeholder",
    }
    return payload


def submit_build_job(*, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    request = dict(payload or {})
    if not request.get("batch_id"):
        batch = create_headlines_batch(limit=min(max(int(request.get("top_n") or 5), 1), 20))
        request.setdefault("batch_id", batch["batch_id"])
        request.setdefault("manifest_uri", batch["manifest_uri"])
        request.setdefault("resource_pool_id", "POOL_HEADLINES_001")
        request.setdefault("module_names", ["news_kg", "event_kg", "industry_network"])
        request.setdefault("source_types", ["headlines"])
        request.setdefault("runtime_profile", "kag_openspg")
        request.setdefault("namespace", "IncCore")
    return _submit_build_job(request)


def get_build_job(job_id: str):
    return _get_build_job(job_id)


def list_build_jobs(*, status: str | None = None, limit: int = 20):
    from app.database.mongodb import mongodb_conn

    query = {}
    if str(status or "").strip():
        query["status"] = str(status).strip()
    rows = mongodb_conn.find_many("openks_build_jobs", query=query, limit=max(int(limit or 20), 1), sort=[("created_at", -1)])
    items = []
    for row in rows:
        payload = dict(row)
        if "_id" in payload:
            payload["_id"] = str(payload["_id"])
        items.append(payload)
    return {"items": items, "total": len(items)}


def reset_build_jobs() -> None:
    from app.database.mongodb import mongodb_conn

    try:
        mongodb_conn.get_collection("openks_build_jobs").delete_many({})
    except Exception:
        pass
