from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.knowledge_runtime_service import normalize_runtime_profile


router = APIRouter(tags=["knowledge-runtime"])


def _get_mongo_conn():
    from app.database.mongodb import mongodb_conn

    return mongodb_conn


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


def _ensure_bootstrap_runtime_for_kg(kg_name: str, *, runtime_profile: str | None = None) -> None:
    if kg_name != "news_kg":
        return
    normalized_profile = normalize_runtime_profile(runtime_profile) if runtime_profile else None
    if normalized_profile and normalized_profile != "openks_direct":
        return

    mongo = _get_mongo_conn()
    existing_runs = _list_documents("knowledge_runs", query={"kg_name": kg_name}, limit=1)
    if existing_runs:
        return

    legacy_runs = _list_documents("kg_build_runs", query={"kg_name": kg_name}, limit=1)
    if not legacy_runs:
        return

    legacy = legacy_runs[0]
    legacy_source_run_id = str(legacy.get("run_id") or "").strip()
    started_at = str(legacy.get("started_at") or legacy.get("created_at") or datetime.utcnow().isoformat())
    finished_at = str(legacy.get("finished_at") or legacy.get("updated_at") or started_at)
    run_id = f"KRUN_BOOTSTRAP_{legacy_source_run_id or 'news_kg'}"
    artifact_version = f"{kg_name}:bootstrap:{finished_at.replace(':', '').replace('-', '').replace('T', '_')}"
    artifact_id = f"KART_BOOTSTRAP_{legacy_source_run_id or 'news_kg'}"
    release_id = f"KREL_BOOTSTRAP_{legacy_source_run_id or 'news_kg'}"

    mongo.update_one(
        "knowledge_runs",
        {"run_id": run_id},
        {"$set": {
            "run_id": run_id,
            "kg_name": kg_name,
            "status": "completed",
            "runtime_profile": "openks_direct",
            "artifact_ref": artifact_id,
            "legacy_build_run_id": legacy_source_run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "created_at": finished_at,
        }},
        upsert=True,
    )
    mongo.update_one(
        "knowledge_artifacts",
        {"artifact_id": artifact_id},
        {"$set": {
            "artifact_id": artifact_id,
            "kg_name": kg_name,
            "run_id": run_id,
            "version": artifact_version,
            "status": "ready",
            "entity_count": int(legacy.get("entities_written") or 0),
            "statement_count": int(legacy.get("statements_written") or 0),
            "context_count": int(legacy.get("contexts_written") or 0),
            "graph_relation_count": int(legacy.get("graph_relations_written") or 0),
            "legacy_build_run_id": legacy_source_run_id,
            "created_at": finished_at,
        }},
        upsert=True,
    )
    mongo.update_one(
        "service_releases",
        {"release_id": release_id},
        {"$set": {
            "release_id": release_id,
            "artifact_id": artifact_id,
            "kg_name": kg_name,
            "artifact_version": artifact_version,
            "version": "bootstrap-active",
            "status": "active",
            "released_at": finished_at,
            "state_history": [
                {"action": "bootstrap", "to_status": "active", "changed_at": finished_at},
            ],
            "created_at": finished_at,
        }},
        upsert=True,
    )

    if hasattr(mongo, "get_collection"):
        for collection_name in ("entity_instances", "inc_statement", "inc_context"):
            collection = mongo.get_collection(collection_name)
            if hasattr(collection, "update_many"):
                collection.update_many(
                    {"source_kg": kg_name},
                    {"$set": {"run_id": run_id, "artifact_id": artifact_id}},
                )


def _append_state_history(
    document: Dict[str, Any],
    *,
    to_status: str,
    action: str,
    operator: str | None = None,
    comment: str | None = None,
) -> Dict[str, Any]:
    history = list(document.get("state_history") or [])
    entry = {
        "action": action,
        "to_status": to_status,
        "changed_at": datetime.utcnow().isoformat(),
    }
    if str(operator or "").strip():
        entry["operator"] = str(operator).strip()
    if str(comment or "").strip():
        entry["comment"] = str(comment).strip()
    history.append(entry)
    return {**document, "status": to_status, "state_history": history}


def _update_release_document(release_id: str, mutate_fn):
    mongo = _get_mongo_conn()
    existing = _normalize_document(mongo.find_one("service_releases", {"release_id": release_id}))
    if existing is None:
        raise HTTPException(status_code=404, detail=f"release {release_id} 不存在")
    updated = mutate_fn(existing)
    mongo.update_one(
        "service_releases",
        {"release_id": release_id},
        {"$set": updated},
        upsert=False,
    )
    return _normalize_document(mongo.find_one("service_releases", {"release_id": release_id})) or updated


class CreateReleaseRequest(BaseModel):
    artifact_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    status: str = Field(default="released", min_length=1)


class ReleaseActionRequest(BaseModel):
    operator: str | None = None
    comment: str | None = None


class RollbackReleaseRequest(ReleaseActionRequest):
    target_release_id: str = Field(..., min_length=1)


@router.get("/runs")
def list_runs(
    kg_name: str | None = Query(default=None),
    runtime_profile: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
):
    if kg_name:
        _ensure_bootstrap_runtime_for_kg(kg_name, runtime_profile=runtime_profile)
    query = {"kg_name": kg_name} if kg_name else {}
    if runtime_profile:
        query["runtime_profile"] = normalize_runtime_profile(runtime_profile)
    items = _list_documents("knowledge_runs", query=query, limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    mongo = _get_mongo_conn()
    item = _normalize_document(mongo.find_one("knowledge_runs", {"run_id": run_id}))
    if item is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} 不存在")
    artifact = _normalize_document(mongo.find_one("knowledge_artifacts", {"artifact_id": item.get("artifact_ref")}))
    releases = _list_documents("service_releases", query={"artifact_id": item.get("artifact_ref")}, limit=20)
    return {
        **item,
        "artifact": artifact,
        "releases": releases,
    }


@router.get("/artifacts")
def list_artifacts(
    kg_name: str | None = Query(default=None),
    runtime_profile: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
):
    if kg_name:
        _ensure_bootstrap_runtime_for_kg(kg_name, runtime_profile=runtime_profile)
    query = {"kg_name": kg_name} if kg_name else {}
    if runtime_profile:
        query["runtime_profile"] = normalize_runtime_profile(runtime_profile)
    items = _list_documents("knowledge_artifacts", query=query, limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str):
    mongo = _get_mongo_conn()
    item = _normalize_document(mongo.find_one("knowledge_artifacts", {"artifact_id": artifact_id}))
    if item is None:
        raise HTTPException(status_code=404, detail=f"artifact {artifact_id} 不存在")
    run = _normalize_document(mongo.find_one("knowledge_runs", {"run_id": item.get("run_id")}))
    releases = _list_documents("service_releases", query={"artifact_id": artifact_id}, limit=20)
    active_release = next((release for release in releases if str(release.get("status") or "").lower() == "active"), None)
    return {
        **item,
        "run": run,
        "releases": releases,
        "active_release": active_release,
    }


@router.get("/releases")
def list_releases(
    kg_name: str | None = Query(default=None),
    runtime_profile: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
):
    if kg_name:
        _ensure_bootstrap_runtime_for_kg(kg_name, runtime_profile=runtime_profile)
    query = {"kg_name": kg_name} if kg_name else {}
    if runtime_profile:
        query["runtime_profile"] = normalize_runtime_profile(runtime_profile)
    items = _list_documents("service_releases", query=query, limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/releases/{release_id}")
def get_release(release_id: str):
    mongo = _get_mongo_conn()
    item = _normalize_document(mongo.find_one("service_releases", {"release_id": release_id}))
    if item is None:
        raise HTTPException(status_code=404, detail=f"release {release_id} 不存在")
    artifact = _normalize_document(mongo.find_one("knowledge_artifacts", {"artifact_id": item.get("artifact_id")}))
    run = _normalize_document(mongo.find_one("knowledge_runs", {"run_id": (artifact or {}).get("run_id")}))
    return {
        **item,
        "artifact": artifact,
        "run": run,
    }


@router.post("/releases")
def create_release(payload: CreateReleaseRequest):
    mongo = _get_mongo_conn()
    artifact = _normalize_document(mongo.find_one("knowledge_artifacts", {"artifact_id": payload.artifact_id}))
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"artifact {payload.artifact_id} 不存在")

    released_at = datetime.utcnow().isoformat()
    release_id = f"KREL_{payload.artifact_id}_{payload.version}"
    document = {
        "release_id": release_id,
        "artifact_id": payload.artifact_id,
        "kg_name": artifact.get("kg_name"),
        "runtime_profile": artifact.get("runtime_profile"),
        "artifact_version": artifact.get("version"),
        "version": payload.version,
        "status": payload.status,
        "released_at": released_at,
        "state_history": [
            {
                "action": "create",
                "to_status": payload.status,
                "changed_at": released_at,
            }
        ],
    }
    mongo.update_one(
        "service_releases",
        {"release_id": release_id},
        {"$set": document},
        upsert=True,
    )
    return document


def _activate_release(release_id: str, payload: ReleaseActionRequest):
    mongo = _get_mongo_conn()
    release = _normalize_document(mongo.find_one("service_releases", {"release_id": release_id}))
    if release is None:
        raise HTTPException(status_code=404, detail=f"release {release_id} 不存在")

    kg_name = str(release.get("kg_name") or "").strip()
    if kg_name:
        for item in _list_documents("service_releases", query={"kg_name": kg_name}, limit=200):
            if item.get("release_id") != release_id and str(item.get("status") or "").strip().lower() == "active":
                superseded = _append_state_history(
                    item,
                    to_status="superseded",
                    action="supersede",
                    operator=payload.operator,
                    comment=payload.comment,
                )
                mongo.update_one("service_releases", {"release_id": item["release_id"]}, {"$set": superseded}, upsert=False)

    activated = _update_release_document(
        release_id,
        lambda current: _append_state_history(
            current,
            to_status="active",
            action="activate",
            operator=payload.operator,
            comment=payload.comment,
        ),
    )
    return activated or {"release_id": release_id, "status": "active"}


@router.post("/releases/{release_id}/activate")
def activate_release(release_id: str, payload: ReleaseActionRequest):
    return _activate_release(release_id, payload)


@router.post("/releases/{release_id}/submit-review")
def submit_release_review(release_id: str, payload: ReleaseActionRequest):
    updated = _update_release_document(
        release_id,
        lambda current: _append_state_history(
            current,
            to_status="review_pending",
            action="submit_review",
            operator=payload.operator,
            comment=payload.comment,
        ),
    )
    return updated


@router.post("/releases/{release_id}/approve")
def approve_release(release_id: str, payload: ReleaseActionRequest):
    updated = _update_release_document(
        release_id,
        lambda current: _append_state_history(
            current,
            to_status="released",
            action="approve",
            operator=payload.operator,
            comment=payload.comment,
        ),
    )
    return updated


@router.post("/releases/{release_id}/rollback")
def rollback_release(release_id: str, payload: RollbackReleaseRequest):
    current = _update_release_document(
        release_id,
        lambda current: _append_state_history(
            current,
            to_status="rolled_back",
            action="rollback",
            operator=payload.operator,
            comment=payload.comment,
        ),
    )
    target = _activate_release(
        payload.target_release_id,
        ReleaseActionRequest(operator=payload.operator, comment=payload.comment),
    )
    return {
        "rolled_back": current,
        "current": target,
    }
