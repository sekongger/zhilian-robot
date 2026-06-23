from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.news_pipeline.repository import NewsPipelineRepository


DEFAULT_RUNTIME_PROFILE = "kag_openspg"
SUPPORTED_RUNTIME_PROFILES = {"kag_openspg", "openks_direct"}


def _get_mongo_conn():
    from app.database.mongodb import mongodb_conn

    return mongodb_conn


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def normalize_runtime_profile(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in SUPPORTED_RUNTIME_PROFILES:
        return text
    return DEFAULT_RUNTIME_PROFILE


def _normalize_document(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(document, dict):
        return None
    normalized = dict(document)
    if "_id" in normalized:
        normalized["_id"] = str(normalized["_id"])
    return normalized


def _list_documents(collection_name: str, *, query: Optional[Dict[str, Any]] = None, limit: int = 20):
    mongo = _get_mongo_conn()
    rows = mongo.find_many(collection_name, query=query or {}, limit=limit, sort=[("created_at", -1)])
    return [_normalize_document(row) or {} for row in rows]


def list_pending_openks_queue_preview(limit: int = 50) -> Dict[str, Any]:
    repo = NewsPipelineRepository()
    rows = repo.list_kg_input_queue(kg_name="news_kg", status="pending", limit=max(int(limit or 20), 1))
    preview_rows = [
        {
            "queue_id": str(item.get("queue_id") or ""),
            "doc_id": str(item.get("doc_id") or ""),
            "title": str(item.get("title") or ""),
            "status": str(item.get("status") or "pending"),
            "created_at": item.get("created_at"),
        }
        for item in rows
    ]
    return {
        "pending_count": len(preview_rows),
        "rows": preview_rows,
    }


def get_runtime_binding_summary(*, kg_name: str = "news_kg", runtime_profile: str = DEFAULT_RUNTIME_PROFILE) -> Dict[str, Any]:
    normalized_profile = normalize_runtime_profile(runtime_profile)
    run_query: Dict[str, Any] = {"kg_name": kg_name}
    if normalized_profile:
        run_query["runtime_profile"] = normalized_profile

    runs = _list_documents("knowledge_runs", query=run_query, limit=1)
    run = runs[0] if runs else None
    artifact = None
    release = None

    mongo = _get_mongo_conn()
    artifact_ref = str((run or {}).get("artifact_ref") or "").strip()
    if artifact_ref:
        artifact = _normalize_document(mongo.find_one("knowledge_artifacts", {"artifact_id": artifact_ref}))
        if artifact is not None:
            release_rows = _list_documents("service_releases", query={"artifact_id": artifact_ref}, limit=20)
            release = next(
                (item for item in release_rows if str(item.get("status") or "").strip().lower() == "active"),
                None,
            ) or (release_rows[0] if release_rows else None)
    return {
        "run": run,
        "artifact": artifact,
        "release": release,
    }


def register_workflow_runtime_binding(
    *,
    runtime_profile: str,
    kg_name: str = "news_kg",
    project_id: int = 1,
    workflow_run_id: str | None = None,
    bridge_run: Optional[Dict[str, Any]] = None,
    builder_submit_result: Optional[Dict[str, Any]] = None,
    graph_materialize_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_profile = normalize_runtime_profile(runtime_profile)
    if normalized_profile != "kag_openspg":
        return get_runtime_binding_summary(kg_name=kg_name, runtime_profile=normalized_profile)

    mongo = _get_mongo_conn()
    bridge = dict(bridge_run or {})
    base_id = str(workflow_run_id or bridge.get("run_id") or f"kag_{int(datetime.utcnow().timestamp())}").strip()
    now = _utc_now_iso()
    artifact_ref = f"KART_KAG_{base_id}"
    run_id = f"KRUN_KAG_{base_id}"
    artifact_version = f"{kg_name}:kag_openspg:{base_id}"
    graph_result = dict(graph_materialize_result or {})
    builder_result = dict(builder_submit_result or {})

    run_doc = {
        "run_id": run_id,
        "kg_name": kg_name,
        "status": "completed" if str(graph_result.get("status") or "").strip().lower() == "success" else "running",
        "runtime_profile": normalized_profile,
        "artifact_ref": artifact_ref,
        "project_id": project_id,
        "workflow_run_id": workflow_run_id,
        "bridge_run_id": bridge.get("run_id"),
        "started_at": str(bridge.get("run_time") or now),
        "finished_at": now,
        "created_at": now,
        "builder_job_id": builder_result.get("job_id"),
        "graph_vertices": graph_result.get("vertices"),
        "graph_edges": graph_result.get("edges"),
    }
    mongo.update_one("knowledge_runs", {"run_id": run_id}, {"$set": run_doc}, upsert=True)

    artifact_doc = {
        "artifact_id": artifact_ref,
        "kg_name": kg_name,
        "run_id": run_id,
        "runtime_profile": normalized_profile,
        "project_id": project_id,
        "version": artifact_version,
        "status": "ready" if str(graph_result.get("status") or "").strip().lower() == "success" else "building",
        "entity_count": int(graph_result.get("vertices") or 0),
        "statement_count": int(graph_result.get("edges") or 0),
        "context_count": int(bridge.get("export_count") or 0),
        "graph_relation_count": int(graph_result.get("edges") or 0),
        "workflow_run_id": workflow_run_id,
        "bridge_run_id": bridge.get("run_id"),
        "created_at": now,
    }
    mongo.update_one("knowledge_artifacts", {"artifact_id": artifact_ref}, {"$set": artifact_doc}, upsert=True)
    release_rows = _list_documents("service_releases", query={"artifact_id": artifact_ref}, limit=20)
    release = next(
        (item for item in release_rows if str(item.get("status") or "").strip().lower() == "active"),
        None,
    ) or (release_rows[0] if release_rows else None)
    if release is None:
        release_id = f"KREL_{artifact_ref}_draft"
        release_doc = {
            "release_id": release_id,
            "artifact_id": artifact_ref,
            "kg_name": kg_name,
            "runtime_profile": normalized_profile,
            "artifact_version": artifact_version,
            "version": artifact_version,
            "status": "draft",
            "created_at": now,
            "state_history": [
                {
                    "action": "create",
                    "to_status": "draft",
                    "changed_at": now,
                }
            ],
        }
        mongo.update_one("service_releases", {"release_id": release_id}, {"$set": release_doc}, upsert=True)
        release = _normalize_document(mongo.find_one("service_releases", {"release_id": release_id})) or release_doc

    return {
        "run": _normalize_document(mongo.find_one("knowledge_runs", {"run_id": run_id})) or run_doc,
        "artifact": _normalize_document(mongo.find_one("knowledge_artifacts", {"artifact_id": artifact_ref})) or artifact_doc,
        "release": release,
    }
