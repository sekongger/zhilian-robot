"""资源与证据联查路由（internal）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.api import open_api_routes
from app.openspg_demo import routes as demo_routes

router = APIRouter(prefix="/resource", tags=["Resource (Internal)"])

COLL_QA_CITATIONS = "qa_citations"
COLL_QA_TRACES = "qa_traces"
COLL_OPEN_API_TRACES = "open_api_traces"
COLL_INC_STATEMENT = "inc_statement"
COLL_INC_CONTEXT = "inc_context"

ALLOWED_SORT_FIELDS = {
    "publish_time",
    "source_name",
    "source_collection",
    "statement_id",
    "doc_id",
}

DOC_COLLECTION_FIELDS = {
    "source_news": ["doc_id", "news_id"],
    "crawled_articles": ["doc_id", "news_id"],
    "inc_document": ["doc_id"],
    "raw_documents": ["doc_id"],
}


def _get_mongo_conn():
    try:
        from app.database.mongodb import mongodb_conn

        return mongodb_conn
    except Exception:
        return None


def _as_plain_dict(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(document, dict):
        return None
    payload = dict(document)
    if "_id" in payload:
        payload["_id"] = str(payload["_id"])
    return payload


def _load_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    try:
        payload = open_api_routes.get_open_knowledge_trace(trace_id)
        if isinstance(payload, dict):
            return payload
    except HTTPException:
        pass
    except Exception:
        pass

    mongo = _get_mongo_conn()
    if not mongo:
        return None
    for collection in (COLL_QA_TRACES, COLL_OPEN_API_TRACES):
        try:
            payload = mongo.find_one(collection, {"trace_id": trace_id})
        except Exception:
            payload = None
        normalized = _as_plain_dict(payload)
        if normalized:
            return normalized
    return None


def _extract_event_ids(trace_payload: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(trace_payload, dict):
        return []
    event_ids: List[str] = []
    for item in trace_payload.get("retrieval_hits") or []:
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or item.get("statement_id") or "").strip()
        if event_id and event_id not in event_ids:
            event_ids.append(event_id)
    return event_ids


def _build_headline_evidence_items(
    *,
    statement_id: str,
    trace_id: Optional[str],
    hours: int,
) -> List[Dict[str, Any]]:
    try:
        detail = demo_routes.get_headline_detail(
            event_id=statement_id,
            hours=hours,
            allow_demo_fallback=True,
        )
    except HTTPException:
        return []
    except Exception:
        return []

    if not isinstance(detail, dict):
        return []

    title = str(detail.get("headline_title") or "").strip()
    items: List[Dict[str, Any]] = []
    for idx, evidence in enumerate(detail.get("evidence_news") or []):
        if not isinstance(evidence, dict):
            continue
        items.append(
            {
                "trace_id": trace_id,
                "statement_id": statement_id,
                "doc_id": str(evidence.get("news_id") or f"{statement_id}:{idx}"),
                "title": str(evidence.get("title") or title),
                "snippet": str(evidence.get("snippet") or ""),
                "source_name": str(evidence.get("source_name") or "unknown"),
                "source_url": str(evidence.get("url") or ""),
                "publish_time": evidence.get("publish_time"),
                "context_id": statement_id,
                "source_collection": "headline_detail",
            }
        )
    return items


def _build_citation_items(
    *,
    statement_id: Optional[str],
    doc_id: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return []

    query: Dict[str, Any] = {}
    if statement_id:
        query["statement_id"] = statement_id
    if doc_id:
        query["doc_id"] = doc_id

    try:
        citations = mongo.find_many(
            COLL_QA_CITATIONS,
            query=query,
            limit=limit,
            sort=[("publish_time", -1)],
        )
    except Exception:
        citations = []

    items: List[Dict[str, Any]] = []
    for item in citations:
        citation = _as_plain_dict(item)
        if not citation:
            continue
        items.append(
            {
                "trace_id": None,
                "statement_id": str(citation.get("statement_id") or ""),
                "doc_id": str(citation.get("doc_id") or ""),
                "title": str(citation.get("title") or citation.get("doc_id") or ""),
                "snippet": str(citation.get("snippet") or ""),
                "source_name": str(citation.get("source_name") or ""),
                "source_url": str(citation.get("source_url") or ""),
                "publish_time": citation.get("publish_time"),
                "context_id": citation.get("context_id"),
                "source_collection": COLL_QA_CITATIONS,
            }
        )
    return items


def _matches_filters(item: Dict[str, Any], *, statement_id: Optional[str], doc_id: Optional[str]) -> bool:
    if statement_id and str(item.get("statement_id") or "") != statement_id:
        return False
    if doc_id and str(item.get("doc_id") or "") != doc_id:
        return False
    return True


def _dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique: Dict[str, Dict[str, Any]] = {}
    for item in items:
        key = "||".join(
            [
                str(item.get("trace_id") or ""),
                str(item.get("statement_id") or ""),
                str(item.get("doc_id") or ""),
                str(item.get("source_url") or ""),
                str(item.get("snippet") or ""),
            ]
        )
        if key not in unique:
            unique[key] = item
    rows = list(unique.values())
    rows.sort(key=lambda x: str(x.get("publish_time") or ""), reverse=True)
    return rows


def _sort_items(items: List[Dict[str, Any]], *, sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
    field = sort_by if sort_by in ALLOWED_SORT_FIELDS else "publish_time"
    reverse = str(sort_order or "desc").lower() != "asc"

    if field == "publish_time":
        key_func = lambda x: str(x.get("publish_time") or "")
    else:
        key_func = lambda x: str(x.get(field) or "").lower()

    return sorted(items, key=key_func, reverse=reverse)


def _lookup_statement(statement_id: str) -> Optional[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return None
    for query in ({"statement_id": statement_id}, {"_id": statement_id}):
        try:
            payload = mongo.find_one(COLL_INC_STATEMENT, query)
        except Exception:
            payload = None
        normalized = _as_plain_dict(payload)
        if normalized:
            resolved_statement_id = str(
                normalized.get("statement_id") or normalized.get("_id") or statement_id
            )
            return {
                "statement_id": resolved_statement_id,
                "subject_id": normalized.get("subject_id"),
                "predicate_id": normalized.get("predicate_id"),
                "object_id": normalized.get("object_id") or normalized.get("object_entity_id"),
                "object_type": normalized.get("object_type"),
                "confidence": normalized.get("confidence"),
                "doc_id": normalized.get("doc_id"),
                "context_id": normalized.get("context_id"),
                "context_scenario": normalized.get("context_scenario"),
                "source_collection": COLL_INC_STATEMENT,
            }
    return None


def _lookup_contexts(statement: Optional[Dict[str, Any]], statement_id: Optional[str]) -> List[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return []

    queries: List[Dict[str, Any]] = []
    if statement_id:
        queries.append({"statement_id": statement_id})
    if statement and statement.get("context_id"):
        queries.append({"context_id": statement.get("context_id")})
    if statement and statement.get("doc_id"):
        queries.append({"doc_id": statement.get("doc_id")})

    unique: Dict[str, Dict[str, Any]] = {}
    for query in queries:
        try:
            rows = mongo.find_many(COLL_INC_CONTEXT, query=query, limit=50, sort=[("begin_time", -1)])
        except Exception:
            rows = []
        for row in rows:
            payload = _as_plain_dict(row)
            if not payload:
                continue
            context_id = str(payload.get("context_id") or payload.get("_id") or "")
            key = context_id or f"ctx::{len(unique)}"
            unique[key] = {
                "context_id": context_id,
                "context_type": payload.get("context_type"),
                "doc_id": payload.get("doc_id"),
                "begin_time": payload.get("begin_time"),
                "end_time": payload.get("end_time"),
                "context_scenario": payload.get("context_scenario"),
                "source_collection": COLL_INC_CONTEXT,
            }
    return list(unique.values())


def _lookup_documents_by_doc_id(doc_id: str) -> List[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return []

    snapshots: List[Dict[str, Any]] = []
    for collection_name, fields in DOC_COLLECTION_FIELDS.items():
        for field in fields:
            try:
                found = mongo.find_one(collection_name, {field: doc_id})
            except Exception:
                found = None
            payload = _as_plain_dict(found)
            if not payload:
                continue
            snapshots.append(
                {
                    "doc_id": doc_id,
                    "title": str(payload.get("title") or payload.get("title_raw") or ""),
                    "summary": str(payload.get("summary") or ""),
                    "content": str(payload.get("content") or ""),
                    "source_name": str(payload.get("source_name") or payload.get("source") or ""),
                    "source_url": str(payload.get("source_url") or payload.get("url") or ""),
                    "publish_time": payload.get("publish_time") or payload.get("crawled_at"),
                    "source_collection": collection_name,
                }
            )
            break

    unique: Dict[str, Dict[str, Any]] = {}
    for snapshot in snapshots:
        key = f"{snapshot.get('source_collection')}::{snapshot.get('doc_id')}"
        unique[key] = snapshot
    return list(unique.values())


@router.get("/evidence/lookup")
def lookup_evidence(
    trace_id: Optional[str] = Query(None),
    statement_id: Optional[str] = Query(None),
    doc_id: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=200),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=200),
    sort_by: str = Query("publish_time"),
    sort_order: str = Query("desc"),
):
    resolved_trace_id = str(trace_id or "").strip() or None
    resolved_statement_id = str(statement_id or "").strip() or None
    resolved_doc_id = str(doc_id or "").strip() or None
    if not resolved_trace_id and not resolved_statement_id and not resolved_doc_id:
        raise HTTPException(status_code=400, detail="trace_id/statement_id/doc_id 至少传一个")

    trace_payload: Optional[Dict[str, Any]] = None
    items: List[Dict[str, Any]] = []

    if resolved_trace_id:
        trace_payload = _load_trace(resolved_trace_id)
        for event_id in _extract_event_ids(trace_payload):
            items.extend(
                _build_headline_evidence_items(
                    statement_id=event_id,
                    trace_id=resolved_trace_id,
                    hours=hours,
                )
            )

    if resolved_statement_id:
        items.extend(
            _build_headline_evidence_items(
                statement_id=resolved_statement_id,
                trace_id=resolved_trace_id,
                hours=hours,
            )
        )

    if resolved_statement_id or resolved_doc_id:
        items.extend(
            _build_citation_items(
                statement_id=resolved_statement_id,
                doc_id=resolved_doc_id,
                limit=max(limit * 3, 50),
            )
        )

    items = [row for row in items if _matches_filters(row, statement_id=resolved_statement_id, doc_id=resolved_doc_id)]
    items = _dedupe_items(items)
    items = _sort_items(items, sort_by=sort_by, sort_order=sort_order)

    resolved_statement = _lookup_statement(resolved_statement_id) if resolved_statement_id else None
    contexts = _lookup_contexts(resolved_statement, resolved_statement_id)

    document_ids: List[str] = []
    if resolved_doc_id:
        document_ids = [resolved_doc_id]
    else:
        for item in items:
            candidate = str(item.get("doc_id") or "").strip()
            if candidate and candidate not in document_ids:
                document_ids.append(candidate)
            if len(document_ids) >= 5:
                break

    documents: List[Dict[str, Any]] = []
    for candidate in document_ids:
        documents.extend(_lookup_documents_by_doc_id(candidate))

    total = len(items)
    safe_page_size = min(max(int(page_size), 1), 200)
    safe_page = max(int(page), 1)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    page_items = items[start:end]
    total_pages = (total + safe_page_size - 1) // safe_page_size if total > 0 else 0

    return {
        "query": {
            "trace_id": resolved_trace_id,
            "statement_id": resolved_statement_id,
            "doc_id": resolved_doc_id,
            "hours": hours,
            "limit": limit,
            "sort_by": sort_by if sort_by in ALLOWED_SORT_FIELDS else "publish_time",
            "sort_order": "asc" if str(sort_order).lower() == "asc" else "desc",
        },
        "trace": trace_payload,
        "statement": resolved_statement,
        "contexts": contexts,
        "total": total,
        "items": page_items,
        "pagination": {
            "page": safe_page,
            "page_size": safe_page_size,
            "total_pages": total_pages,
        },
        "documents": documents,
    }
