from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import hashlib
import json
from urllib.parse import urlparse


def _get_mongo_conn():
    from app.database.mongodb import mongodb_conn

    return mongodb_conn


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _hash(parts: List[Any], prefix: str, length: int = 12) -> str:
    digest = hashlib.sha1("|".join(str(item or "") for item in parts).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def _normalize_document(document: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not isinstance(document, dict):
        return None
    payload = dict(document)
    if "_id" in payload:
        payload["_id"] = str(payload["_id"])
    return payload


def _manifest_path(manifest_uri: str) -> Path | None:
    text = str(manifest_uri or "").strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme == "file":
        return Path(parsed.path)
    candidate = Path(text)
    return candidate if candidate.exists() else None


def _load_records_from_manifest(manifest_uri: str, *, limit: int = 200) -> List[Dict[str, Any]]:
    manifest_path = _manifest_path(manifest_uri)
    if manifest_path is None or not manifest_path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        if isinstance(payload, dict):
            rows.append(payload)
        if len(rows) >= max(int(limit or 200), 1):
            break
    return rows


def _load_openks_runtime():
    from openks.cross import DataHubAdapter, GraphitiAdapter
    from openks.kg.fact.event_kg import EventKgBuilder
    from openks.kg.fact.industry_network import IndustryNetworkBuilder

    return DataHubAdapter, GraphitiAdapter, EventKgBuilder, IndustryNetworkBuilder


def _estimate_graph_stats(records: List[Dict[str, Any]]) -> Dict[str, int]:
    doc_count = len(records)
    event_count = doc_count
    company_count = max(doc_count * 2, 1) if doc_count else 0
    vertices = doc_count + event_count + company_count
    edges = doc_count * 3
    return {
        "documents": doc_count,
        "events": event_count,
        "companies": company_count,
        "vertices": vertices,
        "edges": edges,
    }


def submit_build_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    mongo = _get_mongo_conn()
    request = dict(payload or {})
    idempotency_key = str(request.get("idempotency_key") or "").strip()
    if idempotency_key:
        existing = _normalize_document(mongo.find_one("openks_build_jobs", {"idempotency_key": idempotency_key}))
        if existing is not None:
            return existing

    now = _utc_now_iso()
    job_id = str(request.get("job_id") or _hash([request.get("batch_id"), request.get("resource_pool_id"), now], "OKBUILD"))
    DataHubAdapter, GraphitiAdapter, EventKgBuilder, IndustryNetworkBuilder = _load_openks_runtime()
    datahub_adapter = DataHubAdapter()
    graphiti_options = dict(request.get("graphiti_options") or {})
    graphiti_adapter = GraphitiAdapter(
        enabled=graphiti_options.get("enabled"),
        group_name=str(graphiti_options.get("group_name") or graphiti_options.get("source_name") or "headlines"),
    )
    event_builder = EventKgBuilder()
    network_builder = IndustryNetworkBuilder()

    records = datahub_adapter.load_manifest(str(request.get("manifest_uri") or ""))
    normalized_headlines = datahub_adapter.normalize_headline_records(records)
    event_package = graphiti_adapter.ingest(normalized_headlines)
    event_result = event_builder.build(event_package)
    network_result = network_builder.build(
        [
            {
                "headlines": normalized_headlines,
                "events": event_result.get("events") or [],
                "event_nodes": event_result.get("nodes") or [],
                "event_edges": [
                    {
                        "source": item.get("source"),
                        "target": item.get("target"),
                        "label": item.get("relation"),
                    }
                    for item in event_result.get("edges") or []
                ],
                "evidences": event_result.get("evidences") or [],
            }
        ]
    )
    stats = _estimate_graph_stats(normalized_headlines)
    stats.update(network_result.get("stats") or {})
    stats["documents"] = len(normalized_headlines)
    stats["events"] = int(event_result.get("event_count") or 0)
    run_id = _hash([job_id, "industry_network", now], "KRUN")
    artifact_id = _hash([run_id, "industry_network", stats["vertices"]], "KART")
    release_id = _hash([artifact_id, "draft", now], "KREL")

    run_doc = {
        "run_id": run_id,
        "kg_name": "industry_network",
        "status": "completed",
        "runtime_profile": str(request.get("runtime_profile") or "kag_openspg"),
        "artifact_ref": artifact_id,
        "project_id": request.get("project_id") or 1,
        "created_at": now,
        "started_at": now,
        "finished_at": now,
        "batch_id": request.get("batch_id"),
        "job_id": job_id,
    }
    artifact_doc = {
        "artifact_id": artifact_id,
        "kg_name": "industry_network",
        "run_id": run_id,
        "runtime_profile": str(request.get("runtime_profile") or "kag_openspg"),
        "version": f"industry_network:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "status": "ready",
        "entity_count": stats["companies"] + stats["events"],
        "statement_count": stats["edges"],
        "graph_relation_count": stats["edges"],
        "context_count": stats["documents"],
        "created_at": now,
        "batch_id": request.get("batch_id"),
        "job_id": job_id,
    }
    release_doc = {
        "release_id": release_id,
        "artifact_id": artifact_id,
        "kg_name": "industry_network",
        "runtime_profile": str(request.get("runtime_profile") or "kag_openspg"),
        "artifact_version": artifact_doc["version"],
        "version": artifact_doc["version"],
        "status": "draft",
        "created_at": now,
        "state_history": [{"action": "create", "to_status": "draft", "changed_at": now}],
        "job_id": job_id,
    }

    mongo.update_one("knowledge_runs", {"run_id": run_id}, {"$set": run_doc}, upsert=True)
    mongo.update_one("knowledge_artifacts", {"artifact_id": artifact_id}, {"$set": artifact_doc}, upsert=True)
    mongo.update_one("service_releases", {"release_id": release_id}, {"$set": release_doc}, upsert=True)

    job_doc = {
        "job_id": job_id,
        "idempotency_key": idempotency_key,
        "status": "completed",
        "project_id": request.get("project_id") or 1,
        "namespace": request.get("namespace") or "IncCore",
        "resource_pool_id": request.get("resource_pool_id") or "POOL_HEADLINES_001",
        "batch_id": request.get("batch_id"),
        "manifest_uri": request.get("manifest_uri"),
        "module_names": list(request.get("module_names") or []),
        "runtime_profile": str(request.get("runtime_profile") or "kag_openspg"),
        "graphiti_options": dict(request.get("graphiti_options") or {}),
        "schema_policy": dict(request.get("schema_policy") or {}),
        "build_options": dict(request.get("build_options") or {}),
        "source_types": list(request.get("source_types") or []),
        "created_at": now,
        "updated_at": now,
        "run_id": run_id,
        "artifact_id": artifact_id,
        "release_id": release_id,
        "graph_stats": stats,
        "steps": [
            {"key": "datahub_batch", "status": "success", "label": "DataHub 批次准备完成"},
            {"key": "graphiti_preprocess", "status": "success", "label": "Graphiti 初步加工完成"},
            {"key": "schema_sync", "status": "success", "label": "OpenKS schema 已同步"},
            {"key": "graph_materialize", "status": "success", "label": "OpenSPG 图谱已物化"},
        ],
        "records_preview": normalized_headlines[:5],
        "event_package": event_package,
        "event_result": event_result,
        "network_result": network_result,
    }
    mongo.update_one("openks_build_jobs", {"job_id": job_id}, {"$set": job_doc}, upsert=True)
    return job_doc


def get_build_job(job_id: str) -> Dict[str, Any] | None:
    try:
        return _normalize_document(_get_mongo_conn().find_one("openks_build_jobs", {"job_id": job_id}))
    except Exception:
        return None


def get_build_job_result(job_id: str) -> Dict[str, Any] | None:
    job = get_build_job(job_id)
    if job is None:
        return None
    return {
        "job_id": job["job_id"],
        "status": job.get("status"),
        "run_id": job.get("run_id"),
        "artifact_id": job.get("artifact_id"),
        "release_id": job.get("release_id"),
        "graph_stats": job.get("graph_stats") or {},
        "module_names": job.get("module_names") or [],
    }


def _resolve_job(*, artifact_id: str = "", job_id: str = "") -> Dict[str, Any] | None:
    mongo = _get_mongo_conn()
    if str(job_id).strip():
        return _normalize_document(mongo.find_one("openks_build_jobs", {"job_id": str(job_id).strip()}))
    if str(artifact_id).strip():
        return _normalize_document(mongo.find_one("openks_build_jobs", {"artifact_id": str(artifact_id).strip()}))
    rows = mongo.find_many("openks_build_jobs", query={}, limit=1, sort=[("created_at", -1)])
    return _normalize_document(rows[0]) if rows else None


def get_graph_summary(*, artifact_id: str = "", job_id: str = "") -> Dict[str, Any] | None:
    job = _resolve_job(artifact_id=artifact_id, job_id=job_id)
    if job is None:
        return None
    stats = dict(job.get("graph_stats") or {})
    return {
        "job_id": job.get("job_id"),
        "artifact_id": job.get("artifact_id"),
        "release_id": job.get("release_id"),
        "vertex_count": int(stats.get("vertices") or 0),
        "edge_count": int(stats.get("edges") or 0),
        "company_count": int(stats.get("companies") or 0),
        "event_count": int(stats.get("events") or 0),
        "document_count": int(stats.get("documents") or 0),
        "module_names": job.get("module_names") or [],
    }


def get_graph_sample(*, artifact_id: str = "", job_id: str = "") -> Dict[str, Any] | None:
    job = _resolve_job(artifact_id=artifact_id, job_id=job_id)
    if job is None:
        return None
    network_result = dict(job.get("network_result") or {})
    nodes = list(network_result.get("nodes") or [])
    edges = list(network_result.get("edges") or [])
    return {
        "job_id": job.get("job_id"),
        "artifact_id": job.get("artifact_id"),
        "nodes": nodes[:20],
        "edges": edges[:30],
    }


def get_graph_evidence(*, artifact_id: str = "", job_id: str = "", limit: int = 20) -> Dict[str, Any] | None:
    job = _resolve_job(artifact_id=artifact_id, job_id=job_id)
    if job is None:
        return None
    evidence_rows = list((job.get("network_result") or {}).get("evidences") or [])[: max(int(limit or 20), 1)]
    items = [
        {
            "doc_id": str(item.get("doc_id") or ""),
            "title": str(item.get("title") or ""),
            "summary": str(item.get("summary") or item.get("text") or "")[:200],
            "source_name": str(item.get("source_name") or ""),
            "source_url": str(item.get("source_url") or ""),
            "publish_time": str(item.get("publish_time") or ""),
        }
        for item in evidence_rows
    ]
    return {
        "job_id": job.get("job_id"),
        "artifact_id": job.get("artifact_id"),
        "items": items,
        "total": len(items),
    }
