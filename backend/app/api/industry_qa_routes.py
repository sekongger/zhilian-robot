"""产业问答智能体（平台内展示接口）。"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api import open_api_routes

router = APIRouter(prefix="/agent/industry-qa", tags=["Industry QA (Internal)"])

_SESSIONS: Dict[str, Dict[str, Any]] = {}
_SESSION_MESSAGES: Dict[str, List[Dict[str, Any]]] = {}
_MESSAGE_TRACE: Dict[str, str] = {}
_MESSAGE_TRACE_PAYLOAD: Dict[str, Dict[str, Any]] = {}

COLL_QA_SESSIONS = "qa_sessions"
COLL_QA_MESSAGES = "qa_messages"
COLL_QA_CITATIONS = "qa_citations"
COLL_QA_TRACES = "qa_traces"

REDIS_SESSION_CONTEXT_TTL = 24 * 3600
REDIS_TRACE_TTL = 24 * 3600


class CreateSessionRequest(BaseModel):
    doc_type: str = Field(default="news")
    title: Optional[str] = None


class IndustryQaChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    stream: bool = False
    filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=100)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def _as_plain_dict(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(document, dict):
        return None
    payload = dict(document)
    return _normalize_jsonable(payload)


def _normalize_jsonable(value: Any) -> Any:
    """递归标准化 Mongo 返回对象，避免 ObjectId 导致 JSON 序列化失败。"""
    if isinstance(value, dict):
        return {k: _normalize_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_jsonable(item) for item in value)
    if isinstance(value, datetime):
        return value.isoformat()
    if value is not None and value.__class__.__name__ == "ObjectId":
        return str(value)
    return value


def _get_mongo_conn():
    try:
        from app.database.mongodb import mongodb_conn

        return mongodb_conn
    except Exception:
        return None


def _get_redis_conn():
    try:
        from app.database.redis_db import redis_conn

        return redis_conn
    except Exception:
        return None


def _mongo_upsert_session(session: Dict[str, Any]) -> None:
    mongo = _get_mongo_conn()
    if not mongo:
        return
    try:
        mongo.update_one(
            COLL_QA_SESSIONS,
            {"session_id": session["session_id"]},
            {"$set": session},
            upsert=True,
        )
    except Exception:
        return


def _mongo_find_session(session_id: str) -> Optional[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return None
    try:
        session = mongo.find_one(COLL_QA_SESSIONS, {"session_id": session_id})
        return _as_plain_dict(session)
    except Exception:
        return None


def _mongo_list_sessions() -> List[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return []
    try:
        sessions = mongo.find_many(
            COLL_QA_SESSIONS,
            query={},
            sort=[("updated_at", -1)],
        )
        normalized = []
        for item in sessions:
            payload = _as_plain_dict(item)
            if payload:
                normalized.append(payload)
        return normalized
    except Exception:
        return []


def _mongo_insert_message(message: Dict[str, Any]) -> None:
    mongo = _get_mongo_conn()
    if not mongo:
        return
    try:
        mongo.insert_one(COLL_QA_MESSAGES, message)
    except Exception:
        return


def _mongo_insert_citations(message_id: str, citations: List[Dict[str, Any]]) -> None:
    if not citations:
        return
    mongo = _get_mongo_conn()
    if not mongo:
        return
    try:
        docs = []
        for item in citations:
            docs.append(
                {
                    "message_id": message_id,
                    "doc_id": item.get("doc_id"),
                    "title": item.get("title"),
                    "statement_id": item.get("statement_id"),
                    "context_id": item.get("context_id"),
                    "snippet": item.get("snippet"),
                    "source_name": item.get("source_name"),
                    "source_url": item.get("source_url"),
                    "publish_time": item.get("publish_time"),
                    "score": item.get("score"),
                }
            )
        if docs:
            mongo.insert_many(COLL_QA_CITATIONS, docs)
    except Exception:
        return


def _mongo_upsert_trace(trace_id: str, trace_payload: Dict[str, Any]) -> None:
    mongo = _get_mongo_conn()
    if not mongo:
        return
    try:
        mongo.update_one(
            COLL_QA_TRACES,
            {"trace_id": trace_id},
            {"$set": {"trace_id": trace_id, **trace_payload}},
            upsert=True,
        )
    except Exception:
        return


def _mongo_list_messages(session_id: str) -> List[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return []
    try:
        messages = mongo.find_many(
            COLL_QA_MESSAGES,
            query={"session_id": session_id},
            sort=[("created_at", 1)],
        )
        normalized: List[Dict[str, Any]] = []
        for item in messages:
            message = _as_plain_dict(item)
            if not message:
                continue
            message_id = str(message.get("message_id") or "")
            if message.get("role") == "assistant" and message_id:
                citations = mongo.find_many(
                    COLL_QA_CITATIONS,
                    query={"message_id": message_id},
                    sort=[("publish_time", -1)],
                )
                message["citations"] = [_as_plain_dict(citation) for citation in citations if isinstance(citation, dict)]
            normalized.append(message)
        return normalized
    except Exception:
        return []


def _mongo_get_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return None
    try:
        trace = mongo.find_one(COLL_QA_TRACES, {"trace_id": trace_id})
        return _as_plain_dict(trace)
    except Exception:
        return None


def _mongo_get_message(message_id: str) -> Optional[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo:
        return None
    try:
        payload = mongo.find_one(COLL_QA_MESSAGES, {"message_id": message_id})
        return _as_plain_dict(payload)
    except Exception:
        return None


def _mongo_delete_many(collection_name: str, query: Dict[str, Any]) -> int:
    mongo = _get_mongo_conn()
    if not mongo or not hasattr(mongo, "delete_many"):
        return 0
    try:
        result = mongo.delete_many(collection_name, query)
        if isinstance(result, dict):
            return int(result.get("deleted_count") or 0)
        deleted_count = getattr(result, "deleted_count", 0)
        return int(deleted_count or 0)
    except Exception:
        return 0


def _redis_set_session_context(session_id: str, messages: List[Dict[str, Any]]) -> None:
    redis = _get_redis_conn()
    if not redis:
        return
    try:
        context = [
            {
                "message_id": item.get("message_id"),
                "role": item.get("role"),
                "content": item.get("content"),
                "trace_id": item.get("trace_id"),
                "created_at": item.get("created_at"),
            }
            for item in messages[-20:]
        ]
        redis.set(
            f"qa:session:{session_id}:context",
            context,
            expire=REDIS_SESSION_CONTEXT_TTL,
        )
    except Exception:
        return


def _redis_set_trace(trace_id: str, trace_payload: Dict[str, Any]) -> None:
    redis = _get_redis_conn()
    if not redis:
        return
    try:
        redis.set(
            f"qa:trace:{trace_id}",
            trace_payload,
            expire=REDIS_TRACE_TTL,
        )
    except Exception:
        return


def _redis_get_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    redis = _get_redis_conn()
    if not redis:
        return None
    try:
        payload = redis.get(f"qa:trace:{trace_id}")
        if isinstance(payload, dict):
            return payload
        return None
    except Exception:
        return None


def _redis_delete(*keys: str) -> None:
    redis = _get_redis_conn()
    if not redis or not hasattr(redis, "delete"):
        return
    try:
        redis.delete(*[key for key in keys if key])
    except Exception:
        return


def _save_trace_payload(
    *,
    trace_id: str,
    trace_payload: Dict[str, Any],
    request: IndustryQaChatRequest,
    assistant_message_id: str,
) -> Dict[str, Any]:
    enriched = {
        **trace_payload,
        "industry_qa": {
            "session_id": request.session_id,
            "message_id": assistant_message_id,
            "collections_written": [
                COLL_QA_MESSAGES,
                COLL_QA_CITATIONS,
                COLL_QA_TRACES,
            ],
        },
    }
    _MESSAGE_TRACE_PAYLOAD[assistant_message_id] = enriched
    open_api_routes._cache_trace(trace_id, enriched)
    _mongo_upsert_trace(trace_id, enriched)
    _redis_set_trace(trace_id, enriched)
    return enriched


def _get_session_or_404(session_id: str) -> Dict[str, Any]:
    session = _SESSIONS.get(session_id) or _mongo_find_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session_id 不存在")
    return session


def _append_user_message(request: IndustryQaChatRequest) -> tuple[Dict[str, Any], List[Dict[str, Any]], str, str]:
    session = _get_session_or_404(request.session_id)
    user_message_id = _new_id("qa_m")
    assistant_message_id = _new_id("qa_m")
    now = _now_iso()
    messages = _SESSION_MESSAGES.setdefault(request.session_id, [])
    user_message = {
        "message_id": user_message_id,
        "session_id": request.session_id,
        "role": "user",
        "content": request.question,
        "trace_id": None,
        "created_at": now,
    }
    messages.append(user_message)
    _mongo_insert_message(user_message)
    return session, messages, user_message_id, assistant_message_id


def _persist_assistant_message(
    *,
    request: IndustryQaChatRequest,
    session: Dict[str, Any],
    messages: List[Dict[str, Any]],
    assistant_message_id: str,
    query_result: Dict[str, Any],
    started_at: float,
) -> Dict[str, Any]:
    trace_id = str(query_result.get("trace_id") or "")
    trace_payload: Optional[Dict[str, Any]] = None
    assistant_message = {
        "message_id": assistant_message_id,
        "session_id": request.session_id,
        "role": "assistant",
        "content": str(query_result.get("answer") or ""),
        "trace_id": trace_id,
        "answer_mode": str(query_result.get("answer_mode") or "classic"),
        "retrieval_compare": query_result.get("retrieval_compare") or {},
        "citations": list(query_result.get("evidences") or []),
        "created_at": _now_iso(),
    }
    messages.append(assistant_message)
    _mongo_insert_message(assistant_message)
    _mongo_insert_citations(assistant_message_id, assistant_message.get("citations") or [])
    if trace_id:
        _MESSAGE_TRACE[assistant_message_id] = trace_id
        try:
            trace_payload = open_api_routes.get_open_knowledge_trace(trace_id)
        except HTTPException:
            trace_payload = None
        if isinstance(trace_payload, dict):
            trace_payload = _save_trace_payload(
                trace_id=trace_id,
                trace_payload=trace_payload,
                request=request,
                assistant_message_id=assistant_message_id,
            )

    session["updated_at"] = _now_iso()
    _mongo_upsert_session(session)
    _redis_set_session_context(request.session_id, messages)
    latency_ms = int((time.perf_counter() - started_at) * 1000)
    workflow_reference = (trace_payload.get("workflow_reference") or {}) if isinstance(trace_payload, dict) else {}
    return {
        "answer": query_result.get("answer") or "",
        "answer_mode": query_result.get("answer_mode") or "classic",
        "retrieval_compare": query_result.get("retrieval_compare") or {},
        "citations": query_result.get("evidences") or [],
        "knowledge_objects": query_result.get("knowledge_objects") or [],
        "trace_id": trace_id,
        "run_id": workflow_reference.get("run_id") or request.filters.get("run_id"),
        "latency_ms": latency_ms,
    }


@router.post("/sessions")
def create_session(request: CreateSessionRequest):
    session_id = _new_id("qa_s")
    title = str(request.title or "").strip() or f"产业问答会话 {session_id[-4:]}"
    now = _now_iso()
    payload = {
        "session_id": session_id,
        "title": title,
        "doc_type": request.doc_type,
        "created_at": now,
        "updated_at": now,
    }
    _SESSIONS[session_id] = payload
    _SESSION_MESSAGES[session_id] = []
    _mongo_upsert_session(payload)
    _redis_set_session_context(session_id, [])
    return payload


@router.get("/sessions")
def list_sessions():
    sessions = _mongo_list_sessions()
    if not sessions:
        sessions = sorted(
            _SESSIONS.values(),
            key=lambda x: str(x.get("updated_at") or ""),
            reverse=True,
        )
    sessions = [_normalize_jsonable(item) for item in sessions]
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    session = _SESSIONS.pop(session_id, None) or _mongo_find_session(session_id)
    if not session:
        _SESSION_MESSAGES.pop(session_id, None)
        _redis_delete(f"qa:session:{session_id}:context")
        return {
            "session_id": session_id,
            "deleted": False,
            "reason": "session_id 不存在",
            "deleted_counts": {
                "sessions": 0,
                "messages": 0,
                "citations": 0,
                "traces": 0,
            },
        }

    messages = _mongo_list_messages(session_id)
    if not messages:
        messages = list(_SESSION_MESSAGES.get(session_id) or [])
    _SESSION_MESSAGES.pop(session_id, None)

    message_ids = [str(item.get("message_id") or "") for item in messages if str(item.get("message_id") or "")]
    trace_ids = [str(item.get("trace_id") or "") for item in messages if str(item.get("trace_id") or "")]

    deleted_messages = _mongo_delete_many(COLL_QA_MESSAGES, {"session_id": session_id})
    deleted_sessions = _mongo_delete_many(COLL_QA_SESSIONS, {"session_id": session_id})
    deleted_citations = 0
    deleted_traces = 0
    for message_id in message_ids:
        deleted_citations += _mongo_delete_many(COLL_QA_CITATIONS, {"message_id": message_id})
        _MESSAGE_TRACE.pop(message_id, None)
        _MESSAGE_TRACE_PAYLOAD.pop(message_id, None)
    for trace_id in trace_ids:
        deleted_traces += _mongo_delete_many(COLL_QA_TRACES, {"trace_id": trace_id})

    _redis_delete(f"qa:session:{session_id}:context", *[f"qa:trace:{trace_id}" for trace_id in trace_ids])

    return {
        "session_id": session_id,
        "deleted": True,
        "deleted_counts": {
            "sessions": deleted_sessions,
            "messages": deleted_messages,
            "citations": deleted_citations,
            "traces": deleted_traces,
        },
    }


@router.post("/chat")
def chat(request: IndustryQaChatRequest):
    started = time.perf_counter()
    session, messages, _, assistant_message_id = _append_user_message(request)
    context = open_api_routes._prepare_query_context(
        query=request.question,
        query_type="semantic",
        top_k=request.top_k,
        filters=request.filters,
        include_evidence=True,
    )
    answer = "".join(open_api_routes._stream_query_answer(context)).strip()
    if not answer:
        answer = "当前未生成可用回答，请稍后重试。"
    query_result = open_api_routes._build_query_response(context, answer)
    return _persist_assistant_message(
        request=request,
        session=session,
        messages=messages,
        assistant_message_id=assistant_message_id,
        query_result=query_result,
        started_at=started,
    )


@router.post("/chat/stream")
def chat_stream(request: IndustryQaChatRequest):
    def _event(data: Dict[str, Any]) -> str:
        return f"data: {json.dumps(_normalize_jsonable(data), ensure_ascii=False)}\n\n"

    def generate():
        started = time.perf_counter()
        session, messages, _, assistant_message_id = _append_user_message(request)
        yield _event(
            {
                "type": "meta",
                "status": "processing",
                "answer_mode": "pending",
            }
        )
        yield _event(
            {
                "type": "meta",
                "status": "retrieving",
                "message": "正在检索 workflow / 图谱数据",
            }
        )
        try:
            context = open_api_routes._prepare_query_context(
                query=request.question,
                query_type="semantic",
                top_k=request.top_k,
                filters=request.filters,
                include_evidence=True,
            )
        except HTTPException:
            raise
        except Exception as exc:
            yield _event({"type": "error", "message": str(exc)})
            return

        answer_chunks: List[str] = []
        yield _event(
            {
                "type": "meta",
                "trace_id": context.get("trace_id"),
                "run_id": ((context.get("workflow_reference") or {}).get("run_id")) or request.filters.get("run_id"),
                "answer_mode": context.get("answer_mode") or "classic",
                "status": "answering",
            }
        )
        for piece in open_api_routes._stream_query_answer(context):
            if not piece:
                continue
            answer_chunks.append(piece)
            yield _event({"type": "delta", "content": piece})
        answer = "".join(answer_chunks).strip()
        if not answer:
            answer = "当前未生成可用回答，请稍后重试。"
        payload = open_api_routes._build_query_response(context, answer)
        payload = _persist_assistant_message(
            request=request,
            session=session,
            messages=messages,
            assistant_message_id=assistant_message_id,
            query_result=payload,
            started_at=started,
        )
        yield _event(
            {
                "type": "done",
                "answer": payload.get("answer") or answer,
                "trace_id": payload.get("trace_id"),
                "run_id": payload.get("run_id"),
                "answer_mode": payload.get("answer_mode") or "classic",
                "retrieval_compare": payload.get("retrieval_compare") or {},
                "citations": payload.get("citations") or [],
                "knowledge_objects": payload.get("knowledge_objects") or [],
                "latency_ms": payload.get("latency_ms"),
            }
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    if session_id not in _SESSIONS and not _mongo_find_session(session_id):
        raise HTTPException(status_code=404, detail="session_id 不存在")
    messages = _mongo_list_messages(session_id)
    if not messages:
        messages = list(_SESSION_MESSAGES.get(session_id) or [])
    messages = [_normalize_jsonable(item) for item in messages]
    return {"messages": messages, "total": len(messages)}


@router.get("/messages/{message_id}/trace")
def get_message_trace(message_id: str):
    payload = _MESSAGE_TRACE_PAYLOAD.get(message_id)
    if isinstance(payload, dict):
        return payload
    message_doc = _mongo_get_message(message_id)
    session_id = str(message_doc.get("session_id") or "") if message_doc else ""
    trace_id = _MESSAGE_TRACE.get(message_id)
    if not trace_id:
        trace_id = str(message_doc.get("trace_id") or "") if message_doc else ""
    if not trace_id:
        raise HTTPException(status_code=404, detail="message_id 对应 trace 不存在")
    trace_payload = _redis_get_trace(trace_id) or _mongo_get_trace(trace_id)
    if isinstance(trace_payload, dict):
        trace_payload = {
            **trace_payload,
            "industry_qa": {
                "session_id": session_id,
                "message_id": message_id,
                "collections_written": [
                    COLL_QA_MESSAGES,
                    COLL_QA_CITATIONS,
                    COLL_QA_TRACES,
                ],
            },
        }
        return trace_payload
    payload = open_api_routes.get_open_knowledge_trace(trace_id)
    if isinstance(payload, dict):
        return {
            **payload,
            "industry_qa": {
                "session_id": session_id,
                "message_id": message_id,
                "collections_written": [
                    COLL_QA_MESSAGES,
                    COLL_QA_CITATIONS,
                    COLL_QA_TRACES,
                ],
            },
        }
    return payload
