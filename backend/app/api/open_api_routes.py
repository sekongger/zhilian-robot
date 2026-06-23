"""对外 Open API 路由（生产智能体接入）。"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.openspg_demo import routes as demo_routes
from app.openspg_demo.openspg_client import (
    get_openspg_graph_labels,
    get_openspg_reason_schema,
    search_openspg_custom,
)

router = APIRouter(prefix="/open", tags=["Open API"])

_TRACE_STORE: Dict[str, Dict[str, Any]] = {}
_TRACE_LIMIT = 200

COLL_OPEN_API_TRACES = "open_api_traces"
REDIS_OPEN_TRACE_TTL = 24 * 3600
_QA_STRATEGIES = {"classic", "openspg", "compare"}

_TYPE_HINTS = {
    "Company": ("公司", "企业", "厂商", "合作方", "客户", "供应商", "合作", "融资", "投资", "布局"),
    "Institution": ("机构", "院", "所", "实验室", "高校", "联合实验室"),
    "Technology": ("技术", "工艺", "算法", "方案", "具身智能", "大模型"),
    "Product": ("产品", "设备", "机器人", "整机", "平台", "机械臂"),
    "Document": ("新闻", "资讯", "报道", "文档", "政策"),
    "Person": ("人物", "专家", "创始人", "高管"),
}

_NOISY_ENTITY_PATTERNS = (
    "及其全资子公司",
    "无任何关联",
    "该信息不实",
    "严正声明",
    "资讯关系抽取",
    "的手机产品与",
)

_QUERY_NOISE_TERMS = {
    "最近",
    "近期",
    "当前",
    "目前",
    "一下",
    "一下子",
    "有哪些",
    "有什么",
    "什么",
    "哪些",
    "情况",
    "进展",
    "动态",
    "相关",
    "请问",
    "帮我",
    "看下",
    "看看",
    "如何",
    "怎么",
    "是否",
    "还有",
}

_QUERY_ENTITY_PATTERNS = (
    r"[A-Za-z0-9·()（）-]{0,8}[\u4e00-\u9fa5]{2,24}(?:公司|集团|科技|智能|股份|汽车|装备|电子|机器人)",
    r"[A-Za-z0-9·()（）-]{0,8}[\u4e00-\u9fa5]{2,24}(?:机械臂|设备|平台|系统|产品)",
    r"[A-Za-z0-9·()（）-]{0,8}[\u4e00-\u9fa5]{2,24}(?:技术|算法|模型|工艺|方案)",
)

_QUERY_ENTITY_SUFFIXES = (
    "有限公司",
    "股份有限公司",
    "公司",
    "集团",
    "科技",
    "智能",
    "股份",
    "汽车",
    "装备",
    "电子",
    "机器人",
    "机械臂",
    "设备",
    "平台",
    "系统",
    "产品",
    "技术",
    "算法",
    "模型",
    "工艺",
    "方案",
)

_QUERY_RELATION_SUFFIXES = (
    "布局",
    "合作",
    "研发",
    "投资",
    "供应",
    "竞争",
    "相关",
    "进展",
    "动态",
    "情况",
    "新闻",
    "资讯",
    "报道",
    "原文",
    "证据",
)

_QUERY_RELATION_HINTS = {
    "Technology": ("技术", "算法", "方案", "工艺", "模型", "具身智能", "大模型"),
    "Product": ("产品", "设备", "平台", "系统", "机械臂", "整机"),
    "Company": ("公司", "企业", "厂商", "合作", "供应", "投资", "竞争", "伙伴", "客户", "供应商"),
    "Document": ("新闻", "资讯", "报道", "原文", "证据", "出处", "文档"),
}

_DOCUMENT_RELATION_MAP = {
    "Company": "mentionsCompany",
    "Product": "mentionsProduct",
    "Technology": "mentionsTech",
    "Person": "mentionsPerson",
}

GRAPH_PATH_STATEMENT_COLLECTIONS = ("news_pipeline_statements", "inc_statement")
GRAPH_PATH_ENTITY_COLLECTIONS = ("news_pipeline_entity_instances", "entity_instances")
GRAPH_PATH_SOURCE_COLLECTIONS = ("news_pipeline_source_news", "source_news", "raw_documents", "crawled_articles")

_LLM_TARGET_TYPE_MAP = {
    "company": "Company",
    "企业": "Company",
    "公司": "Company",
    "technology": "Technology",
    "技术": "Technology",
    "product": "Product",
    "产品": "Product",
    "document": "Document",
    "资讯": "Document",
    "新闻": "Document",
    "文档": "Document",
    "person": "Person",
    "人物": "Person",
}

_LLM_RELATION_TAG_PRIORITY = {
    "technology_layout": ["company_to_technology", "technology_to_company"],
    "technology": ["company_to_technology", "technology_to_company"],
    "product_layout": ["company_to_product", "product_to_company"],
    "product": ["company_to_product", "product_to_company"],
    "cooperation": ["company_to_company"],
    "partnership": ["company_to_company"],
    "supply": ["company_to_company"],
    "supplier": ["company_to_company"],
    "investment": ["company_to_company"],
    "competition": ["company_to_company"],
    "evidence": ["company_to_document", "technology_to_document", "product_to_document", "person_to_document"],
    "document": ["company_to_document", "technology_to_document", "product_to_document", "person_to_document"],
}


class OpenKnowledgeQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    query_type: str = Field(default="semantic")
    filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=100)
    include_evidence: bool = True


class OpenKnowledgeBatchQueryRequest(BaseModel):
    queries: List[str] = Field(default_factory=list)
    query_type: str = Field(default="semantic")
    filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=100)
    include_evidence: bool = True


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


def _get_redis_conn():
    try:
        from app.database.redis_db import redis_conn

        return redis_conn
    except Exception:
        return None


def _query_headlines(hours: int, top_n: int, allow_demo_fallback: bool) -> Dict[str, Any]:
    return demo_routes.get_headlines(
        hours=hours,
        top_n=top_n,
        allow_demo_fallback=allow_demo_fallback,
    )


def _get_event_detail(event_id: str, hours: int, allow_demo_fallback: bool) -> Optional[Dict[str, Any]]:
    try:
        return demo_routes.get_headline_detail(
            event_id=event_id,
            hours=hours,
            allow_demo_fallback=allow_demo_fallback,
        )
    except HTTPException:
        return None


def _pick_hours(filters: Dict[str, Any]) -> int:
    try:
        value = int(filters.get("hours", 24))
    except Exception:
        value = 24
    return min(max(value, 1), 168)


def _pick_project_id(filters: Dict[str, Any]) -> int:
    try:
        value = int(filters.get("project_id", 1))
    except Exception:
        value = 1
    return max(value, 1)


def _pick_qa_strategy(filters: Dict[str, Any]) -> str:
    value = str(filters.get("qa_strategy", "compare") or "compare").strip().lower()
    if value not in _QA_STRATEGIES:
        return "compare"
    return value


def _infer_tables_used(data_source: str) -> List[Dict[str, Any]]:
    text = str(data_source or "").strip().lower()
    if not text:
        return []
    if "inc_statement" in text:
        return [
            {"table": "inc_statement", "role": "structured_statement_source"},
            {"table": "entity_instances", "role": "structured_entity_source"},
            {"table": "inc_context", "role": "structured_context_source"},
        ]
    if "source_news" in text:
        return [{"table": "source_news", "role": "workflow_headline_source"}]
    if "crawled_articles" in text:
        return [{"table": "crawled_articles", "role": "workflow_headline_source"}]
    if "demo" in text:
        return [{"table": "demo_samples", "role": "workflow_headline_source"}]
    return [{"table": text, "role": "workflow_headline_source"}]


def _build_workflow_reference(event_ids: List[str]) -> Optional[Dict[str, Any]]:
    try:
        runs = demo_routes._list_workflow_runs(project_id=1, limit=20)
    except Exception:
        return None
    if not runs:
        return None
    normalized_ids = [str(item or "").strip() for item in event_ids if str(item or "").strip()]
    selected = None
    matched_event_ids: List[str] = []
    for run in runs:
        top_ids = ((run.get("headlines_snapshot") or {}).get("top_headline_ids") or []) if isinstance(run, dict) else []
        current_matches = [event_id for event_id in normalized_ids if event_id in top_ids]
        if current_matches:
            selected = run
            matched_event_ids = current_matches
            break
    if selected is None:
        selected = runs[0]
    return {
        "run_id": selected.get("run_id"),
        "status": selected.get("status"),
        "stage": "apply",
        "matched_event_ids": matched_event_ids,
        "matched_count": len(matched_event_ids),
    }


def _build_answer(headlines: List[Dict[str, Any]], query: str) -> str:
    if not headlines:
        return "当前时间窗口内暂无可回答的产业动态，请放宽筛选条件后重试。"
    top_titles = [str(item.get("headline_title") or "").strip() for item in headlines[:3]]
    top_titles = [title for title in top_titles if title]
    if not top_titles:
        return f"已检索到相关产业动态，但暂未生成标题摘要。查询：{query}"
    return "；".join(top_titles)


def _normalize_graph_node_kind(kind: str, entity_type: str) -> str:
    text = str(kind or entity_type or "").strip().lower()
    if text in {"anchor", "query_anchor"}:
        return "anchor"
    if text in {"statement"}:
        return "statement"
    if text in {"document", "evidence"}:
        return "document"
    return "entity"


def _build_statement_graph_path_view(
    *,
    query: str,
    openspg_hits: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]],
    workflow_reference: Optional[Dict[str, Any]],
    tables_used: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    doc_ids: List[str] = []
    for item in list(evidences or []) + list(openspg_hits or []):
        candidate = str(item.get("doc_id") or "").strip()
        if candidate and candidate not in doc_ids:
            doc_ids.append(candidate)
    if not openspg_hits:
        return None

    anchor_terms = [str(item or "").strip() for item in _extract_query_terms(query, seed_terms=None)[:2]]
    hit_names = {str(item.get("name") or "").strip() for item in openspg_hits if str(item.get("name") or "").strip()}

    if not doc_ids:
        doc_ids = []
    for collection in GRAPH_PATH_SOURCE_COLLECTIONS:
        for row in _safe_mongo_find_many(collection, {}, limit=200, sort=[("publish_time", -1)]):
            text = " ".join(
                [
                    str(row.get("title") or ""),
                    str(row.get("summary") or ""),
                    str(row.get("content") or ""),
                ]
            )
            if anchor_terms and not any(term and term in text for term in anchor_terms):
                continue
            if hit_names and not any(name and name in text for name in hit_names):
                continue
            candidate = str(row.get("doc_id") or "").strip()
            if candidate and candidate not in doc_ids:
                doc_ids.append(candidate)

    if not doc_ids:
        return None

    statements: List[Dict[str, Any]] = []
    for collection in GRAPH_PATH_STATEMENT_COLLECTIONS:
        for doc_id in doc_ids:
            statements.extend(_safe_mongo_find_many(collection, {"doc_id": doc_id}, limit=50))
    if not statements:
        return None

    entity_ids: List[str] = []
    for stmt in statements:
        for key in ("subject_id", "object_entity_id", "object_id", "source_document_id"):
            candidate = str(stmt.get(key) or "").strip()
            if candidate and candidate not in entity_ids:
                entity_ids.append(candidate)

    entity_lookup: Dict[str, Dict[str, Any]] = {}
    for collection in GRAPH_PATH_ENTITY_COLLECTIONS:
        for entity_id in entity_ids:
            for query_doc in ({"_id": entity_id}, {"entity_id": entity_id}):
                payload = _safe_mongo_find_one(collection, query_doc)
                if payload:
                    entity_lookup[entity_id] = payload
                    break

    matched_statements: List[Dict[str, Any]] = []
    for stmt in statements:
        subject = entity_lookup.get(str(stmt.get("subject_id") or ""))
        obj = entity_lookup.get(str(stmt.get("object_entity_id") or stmt.get("object_id") or ""))
        subject_name = str((subject or {}).get("canonical_name") or (subject or {}).get("name") or "").strip()
        object_name = str((obj or {}).get("canonical_name") or (obj or {}).get("name") or "").strip()
        if not subject_name and not object_name:
            continue
        score = 0
        if any(term and term in subject_name for term in anchor_terms):
            score += 2
        if any(term and term in object_name for term in anchor_terms):
            score += 1
        if subject_name in hit_names:
            score += 1
        if object_name in hit_names:
            score += 2
        if score <= 0:
            continue
        matched_statements.append({"score": score, "statement": stmt, "subject": subject, "object": obj})

    if not matched_statements:
        return None

    matched_statements.sort(key=lambda item: (-item["score"], str(item["statement"].get("statement_id") or "")))
    selected = matched_statements[:6]

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_nodes = set()
    seen_edges = set()

    anchor_label = str(selected[0]["subject"].get("canonical_name") or selected[0]["subject"].get("name") or anchor_terms[0] if anchor_terms else query).strip()
    anchor_node_id = f"anchor::{anchor_label}"
    nodes.append({"id": anchor_node_id, "label": anchor_label, "kind": "anchor", "type": "Company"})
    seen_nodes.add(anchor_node_id)

    evidence_lookup = {
        str(item.get("doc_id") or ""): item
        for item in evidences or []
        if str(item.get("doc_id") or "").strip()
    }

    for item in selected:
        stmt = item["statement"]
        subject = item["subject"] or {}
        obj = item["object"] or {}
        subject_label = str(subject.get("canonical_name") or subject.get("name") or stmt.get("subject_id") or "").strip()
        object_label = str(obj.get("canonical_name") or obj.get("name") or stmt.get("object_entity_id") or stmt.get("object_id") or "").strip()
        predicate_label = str(stmt.get("predicate_label") or stmt.get("predicate_id") or "关联").strip()
        statement_id = str(stmt.get("statement_id") or stmt.get("_id") or "").strip()
        doc_id = str(stmt.get("doc_id") or "").strip()
        evidence = evidence_lookup.get(doc_id) or {}
        doc_label = str(evidence.get("title") or next((hit.get("doc_title") for hit in openspg_hits if str(hit.get("doc_id") or "") == doc_id and str(hit.get("doc_title") or "").strip()), "") or doc_id or "证据文档").strip()

        subject_node_id = anchor_node_id if subject_label == anchor_label else f"entity::{stmt.get('subject_id') or subject_label}"
        object_node_id = f"entity::{stmt.get('object_entity_id') or stmt.get('object_id') or object_label}"
        statement_node_id = f"statement::{statement_id}"
        document_node_id = f"document::{doc_id or doc_label}"

        node_payloads = [
            (subject_node_id, subject_label, "anchor" if subject_node_id == anchor_node_id else "entity", str(subject.get("entity_type") or "Entity").title()),
            (statement_node_id, predicate_label, "statement", "Statement"),
            (object_node_id, object_label, "entity", str(obj.get("entity_type") or "Entity").title()),
            (document_node_id, doc_label, "document", "Document"),
        ]
        for node_id, label, kind, node_type in node_payloads:
            if not node_id or not label or node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            nodes.append({"id": node_id, "label": label, "kind": kind, "type": node_type})

        for source, target, label in (
            *(([(anchor_node_id, statement_node_id, "问题锚点")] if subject_node_id != anchor_node_id else [])),
            (statement_node_id, subject_node_id, "主体"),
            (statement_node_id, object_node_id, predicate_label),
            (statement_node_id, document_node_id, "证据文档"),
        ):
            edge_key = (source, target, label)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append({"from": source, "to": target, "label": label})

    return {
        "mode": "statement_path",
        "nodes": nodes,
        "edges": edges,
        "documents": [item for item in evidence_lookup.values()],
        "workflow": workflow_reference or {},
        "tables_used": tables_used,
    }


def _build_query_graph_path_view(
    *,
    query: str,
    openspg_hits: List[Dict[str, Any]],
    workflow_reference: Optional[Dict[str, Any]],
    tables_used: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    hits = [
        item
        for item in openspg_hits
        if str(item.get("doc_title") or "").strip() or str(item.get("doc_id") or "").strip()
    ]
    if not hits:
        return None

    anchor_label = str(hits[0].get("anchor_name") or "").strip()
    if not anchor_label:
        terms = _extract_query_terms(query, seed_terms=None)
        anchor_label = str((terms or [query])[0] or query).strip()

    nodes = [{"id": "anchor", "label": anchor_label, "kind": "anchor", "type": "Query"}]
    edges: List[Dict[str, Any]] = []
    seen_nodes = {"anchor"}

    for index, hit in enumerate(hits[:6]):
        doc_id = str(hit.get("doc_id") or "").strip()
        doc_label = str(hit.get("doc_title") or "").strip() or (f"文档 #{doc_id}" if doc_id else "")
        target_label = str(hit.get("name") or hit.get("id") or f"命中 {index + 1}").strip()
        doc_id = doc_id or doc_label or f"doc_{index}"
        target_id = f"target::{hit.get('id') or index}"
        document_id = f"document::{doc_id}"
        if document_id not in seen_nodes:
            seen_nodes.add(document_id)
            nodes.append({"id": document_id, "label": doc_label, "kind": "document", "type": "Document"})
            edges.append({"from": "anchor", "to": document_id, "label": "关联文档"})
        if target_id not in seen_nodes:
            seen_nodes.add(target_id)
            nodes.append({"id": target_id, "label": target_label, "kind": "entity", "type": str(hit.get("label") or "Entity").split(".")[-1]})
        edges.append({"from": document_id, "to": target_id, "label": str(hit.get("path_tag") or "图谱命中")})

    return {
        "mode": "query_path",
        "nodes": nodes,
        "edges": edges,
        "documents": [],
        "workflow": workflow_reference or {},
        "tables_used": tables_used,
    }


def _build_graph_path_view(
    *,
    query: str,
    openspg_hits: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]],
    workflow_reference: Optional[Dict[str, Any]],
    tables_used: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    return _build_statement_graph_path_view(
        query=query,
        openspg_hits=openspg_hits,
        evidences=evidences,
        workflow_reference=workflow_reference,
        tables_used=tables_used,
    ) or _build_query_graph_path_view(
        query=query,
        openspg_hits=openspg_hits,
        workflow_reference=workflow_reference,
        tables_used=tables_used,
    )


def _iter_text_chunks(text: str, chunk_size: int = 24):
    value = str(text or "")
    for idx in range(0, len(value), chunk_size):
        yield value[idx: idx + chunk_size]


def _build_classic_hits(headlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": str(item.get("event_id") or ""),
            "name": str(item.get("headline_title") or item.get("event_title") or ""),
            "label": str(item.get("event_type_zh") or "IndustryEvent"),
            "summary": "、".join(item.get("companies") or []) or str(item.get("headline_title") or ""),
            "score": float(item.get("headline_score") or 0.0),
            "source": "workflow_apply",
            "event_id": str(item.get("event_id") or ""),
        }
        for item in headlines
    ]


def _safe_mongo_find_many(collection_name: str, query: Dict[str, Any], *, limit: int = 0, sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo or not hasattr(mongo, "find_many"):
        return []
    try:
        rows = mongo.find_many(collection_name, query=query, limit=limit, sort=sort)
    except Exception:
        return []
    results: List[Dict[str, Any]] = []
    for row in rows or []:
        payload = _as_plain_dict(row)
        if payload:
            results.append(payload)
    return results


def _safe_mongo_find_one(collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    if not mongo or not hasattr(mongo, "find_one"):
        return None
    try:
        payload = mongo.find_one(collection_name, query)
    except Exception:
        return None
    return _as_plain_dict(payload)


def _resolve_artifact_filter(filters: Dict[str, Any]) -> str:
    artifact_id = str(filters.get("artifact_id") or "").strip()
    if artifact_id:
        return artifact_id
    release_id = str(filters.get("release_id") or "").strip()
    if not release_id:
        return ""
    release = _safe_mongo_find_one("service_releases", {"release_id": release_id})
    return str((release or {}).get("artifact_id") or "").strip()


def _get_llm_processor():
    try:
        from app.nlp.llm import llm_processor

        return llm_processor
    except Exception:
        return None


def _strip_markdown_code_fence(text: str) -> str:
    value = str(text or "").strip()
    if value.startswith("```"):
        parts = value.split("\n", 1)
        value = parts[1] if len(parts) == 2 else value[3:]
    if value.endswith("```"):
        value = value[:-3]
    return value.strip()


def _normalize_llm_target_types(values: List[Any]) -> List[str]:
    results: List[str] = []
    seen = set()
    for item in values:
        text = str(item or "").strip()
        if not text:
            continue
        normalized = _LLM_TARGET_TYPE_MAP.get(text.lower()) or _LLM_TARGET_TYPE_MAP.get(text) or text
        normalized = _normalize_openspg_label(normalized)
        if normalized in {"Company", "Technology", "Product", "Document", "Person", "Institution"} and normalized not in seen:
            seen.add(normalized)
            results.append(normalized)
    return results


def _normalize_llm_relation_intents(values: List[Any]) -> List[str]:
    results: List[str] = []
    seen = set()
    for item in values:
        text = str(item or "").strip().lower()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results


def _rewrite_query_with_llm(query: str) -> Dict[str, Any]:
    llm_processor = _get_llm_processor()
    if not llm_processor or not getattr(llm_processor, "client", None):
        return {}

    prompt = (
        "请将下面的产业问答问题改写成结构化检索意图，只返回 JSON，不要输出 Markdown。\n"
        "字段要求：\n"
        "- entities: 问题中的锚点实体列表，保留企业/技术/产品原文\n"
        "- target_types: 希望查询的目标类型，可选 Company/Technology/Product/Document/Person\n"
        "- relation_intents: 关系意图，可用 cooperation/supply/investment/competition/technology_layout/product_layout/evidence/document\n"
        "- question_focus: 一句话描述关注点\n\n"
        f"问题：{query}"
    )

    try:
        payload = llm_processor.generate_text(prompt, max_tokens=400)
        raw = _strip_markdown_code_fence(payload)
        data = json.loads(raw)
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    entities = [str(item or "").strip() for item in data.get("entities") or [] if str(item or "").strip()]
    return {
        "entities": entities[:5],
        "target_types": _normalize_llm_target_types(list(data.get("target_types") or [])),
        "relation_intents": _normalize_llm_relation_intents(list(data.get("relation_intents") or [])),
        "question_focus": str(data.get("question_focus") or "").strip(),
    }


def _generate_answer_with_llm(
    *,
    query: str,
    headlines: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]],
) -> str:
    fallback = _build_answer(headlines, query)
    if not headlines:
        return fallback
    llm_processor = _get_llm_processor()
    if not llm_processor or not getattr(llm_processor, "client", None):
        return fallback

    headline_lines = []
    for idx, item in enumerate(headlines[:5], start=1):
        headline_lines.append(
            f"{idx}. 标题：{item.get('headline_title') or item.get('event_title') or '-'}；"
            f"事件ID：{item.get('event_id') or '-'}；"
            f"公司：{','.join(item.get('companies') or []) or '-'}；"
            f"分数：{item.get('headline_score') or 0}"
        )
    evidence_lines = []
    for idx, item in enumerate(evidences[:8], start=1):
        evidence_lines.append(
            f"{idx}. 证据标题：{item.get('title') or '-'}；来源：{item.get('source_name') or '-'}；"
            f"statement_id：{item.get('statement_id') or '-'}；片段：{item.get('snippet') or '-'}"
        )

    prompt = (
        "你是产业研究助理。请基于给定的事件命中和证据，回答用户问题。\n"
        "要求：\n"
        "1. 明确给出结论，不要只罗列标题。\n"
        "2. 分成“结论 / 依据 / 风险与关注点”三段。\n"
        "3. 只使用提供的事实，不要虚构。\n"
        "4. 若证据不足要明确指出。\n\n"
        f"用户问题：{query}\n\n"
        f"命中事件：\n" + "\n".join(headline_lines) + "\n\n"
        f"证据：\n" + "\n".join(evidence_lines)
    )
    answer = llm_processor.generate_text(prompt, max_tokens=1200)
    return answer or fallback


def _build_classic_answer_prompt(
    *,
    query: str,
    headlines: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]],
) -> tuple[str, str]:
    fallback = _build_answer(headlines, query)
    headline_lines = []
    for idx, item in enumerate(headlines[:5], start=1):
        headline_lines.append(
            f"{idx}. 标题：{item.get('headline_title') or item.get('event_title') or '-'}；"
            f"事件ID：{item.get('event_id') or '-'}；"
            f"公司：{','.join(item.get('companies') or []) or '-'}；"
            f"分数：{item.get('headline_score') or 0}"
        )
    evidence_lines = []
    for idx, item in enumerate(evidences[:8], start=1):
        evidence_lines.append(
            f"{idx}. 证据标题：{item.get('title') or '-'}；来源：{item.get('source_name') or '-'}；"
            f"statement_id：{item.get('statement_id') or '-'}；片段：{item.get('snippet') or '-'}"
        )

    prompt = (
        "你是产业研究助理。请基于给定的事件命中和证据，回答用户问题。\n"
        "要求：\n"
        "1. 明确给出结论，不要只罗列标题。\n"
        "2. 分成“结论 / 依据 / 风险与关注点”三段。\n"
        "3. 只使用提供的事实，不要虚构。\n"
        "4. 若证据不足要明确指出。\n\n"
        f"用户问题：{query}\n\n"
        f"命中事件：\n" + "\n".join(headline_lines) + "\n\n"
        f"证据：\n" + "\n".join(evidence_lines)
    )
    return prompt, fallback


def _build_openspg_answer(openspg_hits: List[Dict[str, Any]], query: str) -> str:
    if not openspg_hits:
        return ""
    top_lines = []
    for item in openspg_hits[:3]:
        label = str(item.get("label") or "Node").split(".")[-1]
        name = str(item.get("name") or item.get("id") or "unknown")
        summary = str(item.get("summary") or "").strip()
        text = f"{label}：{name}"
        if summary:
            text += f"（{summary[:60]}）"
        top_lines.append(text)
    return f"OpenSPG 图谱当前命中 {len(openspg_hits)} 条结构化对象，重点包括：" + "；".join(top_lines)


def _generate_openspg_answer_with_llm(
    *,
    query: str,
    openspg_hits: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]],
) -> str:
    fallback = _build_openspg_answer(openspg_hits, query)
    if not openspg_hits:
        return fallback
    llm_processor = _get_llm_processor()
    if not llm_processor or not getattr(llm_processor, "client", None):
        return fallback

    hit_lines = []
    for idx, item in enumerate(openspg_hits[:8], start=1):
        hit_lines.append(
            f"{idx}. 类型：{item.get('label') or '-'}；"
            f"名称：{item.get('name') or '-'}；"
            f"摘要：{item.get('summary') or '-'}；"
            f"分数：{item.get('score') or 0}"
        )
    evidence_lines = []
    for idx, item in enumerate(evidences[:6], start=1):
        evidence_lines.append(
            f"{idx}. 证据标题：{item.get('title') or '-'}；来源：{item.get('source_name') or '-'}；"
            f"片段：{item.get('snippet') or '-'}"
        )
    prompt = (
        "你是 OpenSPG 图谱增强问答助手。请优先基于给定的 OpenSPG 结构化命中回答问题，"
        "必要时再参考辅助证据。\n"
        "要求：\n"
        "1. 先给结论，再给结构化依据。\n"
        "2. 如果图谱没有直接支持用户问题，也要明确指出命中不足。\n"
        "3. 不要虚构图谱中不存在的关系。\n\n"
        f"用户问题：{query}\n\n"
        "OpenSPG 结构化命中：\n" + "\n".join(hit_lines) + "\n\n"
        "辅助证据：\n" + "\n".join(evidence_lines)
    )
    answer = llm_processor.generate_text(prompt, max_tokens=1200)
    return answer or fallback


def _build_openspg_answer_prompt(
    *,
    query: str,
    openspg_hits: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]],
) -> tuple[str, str]:
    fallback = _build_openspg_answer(openspg_hits, query)
    hit_lines = []
    for idx, item in enumerate(openspg_hits[:8], start=1):
        path_tag = str(item.get("path_tag") or "").strip()
        anchor_name = str(item.get("anchor_name") or "").strip()
        hit_lines.append(
            f"{idx}. 类型：{item.get('label') or '-'}；"
            f"名称：{item.get('name') or '-'}；"
            f"摘要：{item.get('summary') or '-'}；"
            f"分数：{item.get('score') or 0}；"
            f"锚点：{anchor_name or '-'}；"
            f"路径：{path_tag or '-'}"
        )
    evidence_lines = []
    for idx, item in enumerate(evidences[:6], start=1):
        evidence_lines.append(
            f"{idx}. 证据标题：{item.get('title') or '-'}；来源：{item.get('source_name') or '-'}；"
            f"片段：{item.get('snippet') or '-'}"
        )
    prompt = (
        "你是 OpenSPG 图谱增强问答助手。请优先基于给定的 OpenSPG 结构化命中回答问题，"
        "必要时再参考辅助证据。\n"
        "要求：\n"
        "1. 先给结论，再给结构化依据。\n"
        "2. 如果图谱没有直接支持用户问题，也要明确指出命中不足。\n"
        "3. 不要虚构图谱中不存在的关系。\n\n"
        f"用户问题：{query}\n\n"
        "OpenSPG 结构化命中：\n" + "\n".join(hit_lines) + "\n\n"
        "辅助证据：\n" + "\n".join(evidence_lines)
    )
    return prompt, fallback


def _stream_answer_with_llm(prompt: str, fallback: str, *, max_tokens: int = 1200):
    llm_processor = _get_llm_processor()
    if not llm_processor or not getattr(llm_processor, "client", None):
        yield from _iter_text_chunks(fallback)
        return

    try:
        emitted = False
        for piece in llm_processor.generate_text_stream(prompt, max_tokens=max_tokens):
            if not piece:
                continue
            emitted = True
            yield piece
        if not emitted and fallback:
            yield from _iter_text_chunks(fallback)
    except Exception:
        yield from _iter_text_chunks(fallback)


def _build_knowledge_objects(headlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for item in headlines:
        subject_name = str(
            item.get("subject_name")
            or ((item.get("companies") or [None])[0])
            or item.get("event_id")
            or "unknown"
        )
        object_name = str(item.get("object_name") or item.get("headline_title") or "")
        results.append(
            {
                "statement_id": str(item.get("event_id") or ""),
                "subject": {
                    "id": str(item.get("subject_id") or f"company:{subject_name}"),
                    "type": str(item.get("subject_type_name") or "Company"),
                    "name": subject_name,
                },
                "predicate": str(item.get("predicate_label") or "industry_event"),
                "object": {
                    "id": str(item.get("object_id") or item.get("event_id") or ""),
                    "type": str(item.get("object_type_name") or "IndustryEvent"),
                    "name": object_name,
                },
                "confidence": float(item.get("headline_score") or 0.0),
                "kg_name": str(item.get("kg_name") or "").strip() or None,
            }
        )
    return results


def _build_evidences(
    headlines: List[Dict[str, Any]],
    *,
    hours: int,
    allow_demo_fallback: bool,
) -> List[Dict[str, Any]]:
    evidences: List[Dict[str, Any]] = []
    for item in headlines:
        event_id = str(item.get("event_id") or "").strip()
        if not event_id:
            continue
        detail = _get_event_detail(event_id=event_id, hours=hours, allow_demo_fallback=allow_demo_fallback)
        if not detail:
            continue
        for idx, evidence in enumerate(detail.get("evidence_news") or []):
            evidences.append(
                {
                    "doc_id": str(evidence.get("news_id") or f"{event_id}:{idx}"),
                    "title": str(evidence.get("title") or ""),
                    "snippet": str(evidence.get("snippet") or ""),
                    "source_name": str(evidence.get("source_name") or "unknown"),
                    "source_url": str(evidence.get("url") or ""),
                    "publish_time": evidence.get("publish_time"),
                    "context_id": event_id,
                    "statement_id": event_id,
                }
            )
    return evidences


def _remember_trace(trace_id: str, trace_payload: Dict[str, Any]) -> None:
    _cache_trace(trace_id, trace_payload)

    redis = _get_redis_conn()
    if redis:
        try:
            redis.set(
                f"open:trace:{trace_id}",
                trace_payload,
                expire=REDIS_OPEN_TRACE_TTL,
            )
        except Exception:
            pass

    mongo = _get_mongo_conn()
    if mongo:
        try:
            mongo.update_one(
                COLL_OPEN_API_TRACES,
                {"trace_id": trace_id},
                {"$set": {"trace_id": trace_id, **trace_payload}},
                upsert=True,
            )
        except Exception:
            pass


def _cache_trace(trace_id: str, trace_payload: Dict[str, Any]) -> None:
    _TRACE_STORE[trace_id] = trace_payload
    if len(_TRACE_STORE) <= _TRACE_LIMIT:
        return
    stale_ids = list(_TRACE_STORE.keys())[:-_TRACE_LIMIT]
    for stale_id in stale_ids:
        _TRACE_STORE.pop(stale_id, None)


def _read_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    trace = _TRACE_STORE.get(trace_id)
    if isinstance(trace, dict):
        return trace

    redis = _get_redis_conn()
    if redis:
        try:
            payload = redis.get(f"open:trace:{trace_id}")
            if isinstance(payload, dict):
                _cache_trace(trace_id, payload)
                return payload
        except Exception:
            pass

    mongo = _get_mongo_conn()
    if mongo:
        try:
            payload = mongo.find_one(COLL_OPEN_API_TRACES, {"trace_id": trace_id})
            if isinstance(payload, dict):
                normalized = dict(payload)
                if "_id" in normalized:
                    normalized["_id"] = str(normalized["_id"])
                _cache_trace(trace_id, normalized)
                return normalized
        except Exception:
            pass

    return None


def _run_classic_query(
    *,
    query: str,
    top_k: int,
    hours: int,
    allow_demo_fallback: bool,
    include_evidence: bool,
    generate_answer: bool,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    structured_result = _run_structured_query(
        query=query,
        top_k=top_k,
        include_evidence=include_evidence,
        filters=filters or {},
    )
    if structured_result:
        return {
            **structured_result,
            "answer": (
                _generate_answer_with_llm(
                    query=query,
                    headlines=structured_result.get("headlines") or [],
                    evidences=structured_result.get("evidences") or [],
                )
                if generate_answer
                else ""
            ),
        }

    headlines_payload = _query_headlines(
        hours=hours,
        top_n=top_k,
        allow_demo_fallback=allow_demo_fallback,
    )
    headlines = list(headlines_payload.get("headlines") or [])[:top_k]
    data_source = str((headlines_payload.get("meta") or {}).get("data_source") or "").strip()
    knowledge_objects = _build_knowledge_objects(headlines)
    evidences = (
        _build_evidences(
            headlines,
            hours=hours,
            allow_demo_fallback=allow_demo_fallback,
        )
        if include_evidence
        else []
    )
    entities = sorted(
        {
            str(company).strip()
            for item in headlines
            for company in (item.get("companies") or [])
            if str(company).strip()
        }
    )
    return {
        "headlines": headlines,
        "data_source": data_source,
        "knowledge_objects": knowledge_objects,
        "evidences": evidences,
        "entities": entities,
        "hits": _build_classic_hits(headlines),
        "answer": (
            _generate_answer_with_llm(
                query=query,
                headlines=headlines,
                evidences=evidences,
            )
            if generate_answer
            else ""
        ),
    }


def _load_structured_entity_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for collection_name in ("entity_instances", "news_pipeline_entity_instances"):
        for row in _safe_mongo_find_many(collection_name, {}, limit=500, sort=[("updated_at", -1)]):
            entity_id = str(row.get("entity_id") or row.get("_id") or "").strip()
            if not entity_id or entity_id in index:
                continue
            index[entity_id] = row
    return index


def _load_structured_context_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in _safe_mongo_find_many("inc_context", {}, limit=500, sort=[("updated_at", -1)]):
        statement_id = str(row.get("statement_id") or "").strip()
        if statement_id and statement_id not in index:
            index[statement_id] = row
    return index


def _load_structured_source_doc(doc_id: str) -> Optional[Dict[str, Any]]:
    value = str(doc_id or "").strip()
    if not value:
        return None
    for collection_name in GRAPH_PATH_SOURCE_COLLECTIONS:
        payload = _safe_mongo_find_one(collection_name, {"doc_id": value})
        if payload:
            return payload
    return None


def _structured_entity_name(entity_doc: Optional[Dict[str, Any]], fallback: str) -> str:
    if not isinstance(entity_doc, dict):
        return fallback
    return str(entity_doc.get("canonical_name") or entity_doc.get("name") or fallback or "").strip()


def _structured_entity_type(entity_doc: Optional[Dict[str, Any]], fallback: str = "Entity") -> str:
    if not isinstance(entity_doc, dict):
        return fallback
    raw = str(entity_doc.get("entity_type") or entity_doc.get("type") or fallback).strip()
    mapping = {
        "company": "Company",
        "technology": "Technology",
        "product": "Product",
        "person": "Person",
        "location": "Location",
        "event": "Event",
        "industry": "Industry",
    }
    return mapping.get(raw.lower(), raw or fallback)


def _score_structured_statement(
    *,
    query_terms: List[str],
    statement: Dict[str, Any],
    subject_name: str,
    object_name: str,
    source_doc: Optional[Dict[str, Any]],
) -> float:
    haystack = " ".join(
        [
            subject_name,
            object_name,
            str(statement.get("predicate_label") or statement.get("predicate_id") or ""),
            str(statement.get("evidence_text") or ""),
            str((source_doc or {}).get("title") or ""),
            str((source_doc or {}).get("content") or ""),
        ]
    ).lower()
    score = float(statement.get("confidence") or 0.0)
    matched = False
    for term in query_terms:
        normalized = str(term or "").strip().lower()
        if not normalized:
            continue
        if normalized in haystack:
            matched = True
            score += 1.2
    if not query_terms:
        matched = True
        score += 0.2
    return score if matched else 0.0


def _run_structured_query(
    *,
    query: str,
    top_k: int,
    include_evidence: bool,
    filters: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    entity_index = _load_structured_entity_index()
    if not entity_index:
        return None

    contexts_by_statement = _load_structured_context_index()
    query_terms = _extract_query_terms(query, seed_terms=None)
    artifact_id_filter = _resolve_artifact_filter(filters or {})
    statements: List[Dict[str, Any]] = []
    for collection_name in ("inc_statement", "news_pipeline_statements"):
        statements.extend(_safe_mongo_find_many(collection_name, {}, limit=300, sort=[("created_at", -1)]))

    ranked: List[Dict[str, Any]] = []
    seen_ids = set()
    for statement in statements:
        statement_id = str(statement.get("statement_id") or statement.get("_id") or "").strip()
        if not statement_id or statement_id in seen_ids:
            continue
        seen_ids.add(statement_id)
        source_kg = str(statement.get("source_kg") or "").strip().lower()
        if source_kg and source_kg not in {"news_kg", "workflow"}:
            continue
        if artifact_id_filter and str(statement.get("artifact_id") or "").strip() != artifact_id_filter:
            continue

        subject_doc = entity_index.get(str(statement.get("subject_id") or "").strip())
        object_doc = entity_index.get(str(statement.get("object_entity_id") or "").strip())
        subject_name = _structured_entity_name(subject_doc, str(statement.get("subject_id") or ""))
        object_name = _structured_entity_name(object_doc, str(statement.get("object_entity_id") or ""))
        source_doc = _load_structured_source_doc(str(statement.get("doc_id") or ""))
        score = _score_structured_statement(
            query_terms=query_terms,
            statement=statement,
            subject_name=subject_name,
            object_name=object_name,
            source_doc=source_doc,
        )
        if score <= 0:
            continue

        predicate_label = str(statement.get("predicate_label") or statement.get("predicate_id") or "相关")
        headline_title = str(
            (source_doc or {}).get("title")
            or f"{subject_name}{predicate_label}{object_name}"
        )
        companies = []
        if _structured_entity_type(subject_doc) == "Company" and subject_name:
            companies.append(subject_name)
        if _structured_entity_type(object_doc) == "Company" and object_name and object_name not in companies:
            companies.append(object_name)
        ranked.append(
            {
                "event_id": statement_id,
                "headline_title": headline_title,
                "headline_score": round(score, 4),
                "companies": companies,
                "latest_publish_time": statement.get("context_time_value") or (contexts_by_statement.get(statement_id) or {}).get("begin_time"),
                "doc_id": str(statement.get("doc_id") or ""),
                "subject_id": str(statement.get("subject_id") or ""),
                "subject_name": subject_name,
                "subject_type_name": _structured_entity_type(subject_doc),
                "predicate_id": str(statement.get("predicate_id") or ""),
                "predicate_label": predicate_label,
                "object_id": str(statement.get("object_entity_id") or ""),
                "object_name": object_name,
                "object_type_name": _structured_entity_type(object_doc),
                "kg_name": str(statement.get("source_kg") or "news_kg"),
                "source": "structured_statement",
            }
        )

    if not ranked:
        return None

    ranked.sort(key=lambda item: (-float(item.get("headline_score") or 0.0), str(item.get("latest_publish_time") or "")), reverse=False)
    headlines = ranked[:top_k]
    evidences = []
    if include_evidence:
        for item in headlines:
            statement_id = str(item.get("event_id") or "")
            context = contexts_by_statement.get(statement_id) or {}
            source_doc = _load_structured_source_doc(str(item.get("doc_id") or ""))
            evidences.append(
                {
                    "doc_id": str(item.get("doc_id") or ""),
                    "title": str((source_doc or {}).get("title") or item.get("headline_title") or ""),
                    "snippet": str(
                        (context or {}).get("evidence_text")
                        or (source_doc or {}).get("content")
                        or ""
                    )[:240],
                    "source_name": str((context or {}).get("source_name") or (source_doc or {}).get("source_name") or "unknown"),
                    "source_url": str((context or {}).get("source_url") or (source_doc or {}).get("source_url") or ""),
                    "publish_time": (context or {}).get("begin_time") or item.get("latest_publish_time"),
                    "context_id": str((context or {}).get("context_id") or statement_id),
                    "statement_id": statement_id,
                }
            )

    entities = []
    for item in headlines:
        for name in (item.get("subject_name"), item.get("object_name")):
            text = str(name or "").strip()
            if text and text not in entities:
                entities.append(text)

    return {
        "headlines": headlines,
        "data_source": "zhilian-robot-db:inc_statement",
        "kg_name": "news_kg",
        "knowledge_objects": _build_knowledge_objects(headlines),
        "evidences": evidences,
        "entities": entities,
        "hits": _build_classic_hits(headlines),
    }


def _normalize_openspg_label(label: str) -> str:
    return str(label or "").strip().split(".")[-1]


def _normalize_query_term(text: str) -> str:
    value = re.sub(r"\s+", "", str(text or "")).strip("，。！？,.?;；:：()（）[]【】")
    while True:
        updated = value
        for suffix in _QUERY_RELATION_SUFFIXES:
            if updated.endswith(suffix) and len(updated) - len(suffix) >= 2:
                updated = updated[: -len(suffix)]
        if updated == value:
            break
        value = updated
    return value


def _is_generic_query_term(text: str) -> bool:
    value = _normalize_query_term(text)
    if len(value) < 2:
        return True
    if value in _QUERY_NOISE_TERMS:
        return True
    if len(value) > 4 and any(noise in value for noise in _QUERY_NOISE_TERMS if len(noise) >= 2):
        return True
    if len(value) > 8 and not value.endswith(_QUERY_ENTITY_SUFFIXES):
        if any(hint in value for hints in _QUERY_RELATION_HINTS.values() for hint in hints):
            return True
        if any(suffix in value for suffix in _QUERY_RELATION_SUFFIXES):
            return True
    for label, hints in _QUERY_RELATION_HINTS.items():
        if value == label or value in hints:
            return True
    return False


def _append_query_term(terms: List[str], seen: set[str], text: str) -> None:
    value = _normalize_query_term(text)
    if not value or _is_generic_query_term(value):
        return
    if value not in seen:
        seen.add(value)
        terms.append(value)


def _extract_query_terms(query: str, seed_terms: Optional[List[str]] = None) -> List[str]:
    terms: List[str] = []
    seen = set()
    query_text = str(query or "")

    for pattern in _QUERY_ENTITY_PATTERNS:
        for match in re.findall(pattern, query_text):
            _append_query_term(terms, seen, match)

    normalized = re.sub(r"[，。！？,.?;；:：/]+", " ", query_text)
    normalized = re.sub(
        r"(有哪些|有什么|是什么|什么|哪些|怎么|如何|请问|帮我|看下|看一下|最近|近期|当前|目前|情况|进展|相关|一下|呢|吗|吧|呀|的|了|和|与|及)",
        " ",
        normalized,
    )
    for fragment in re.split(r"\s+", normalized):
        _append_query_term(terms, seen, fragment)

    for item in seed_terms or []:
        _append_query_term(terms, seen, item)
    compact = _normalize_query_term(query_text)
    if compact and not terms:
        _append_query_term(terms, seen, compact[:24])
    return terms[:8]


def _is_noisy_entity_name(name: str) -> bool:
    text = str(name or "").strip()
    if not text:
        return True
    if len(text) > 36:
        return True
    return any(flag in text for flag in _NOISY_ENTITY_PATTERNS)


def _extract_reason_types(reason_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    response = reason_payload.get("response")
    if isinstance(response, dict):
        raw_types = response.get("spgTypes")
    elif isinstance(response, list):
        raw_types = response
    else:
        raw_types = []
    results: List[Dict[str, Any]] = []
    for item in raw_types if isinstance(raw_types, list) else []:
        if not isinstance(item, dict):
            continue
        if str(item.get("spgTypeEnum") or "").strip().upper() not in {"ENTITY_TYPE", "CONCEPT_TYPE"}:
            continue
        basic_info = item.get("basicInfo") if isinstance(item.get("basicInfo"), dict) else {}
        name_info = basic_info.get("name") if isinstance(basic_info.get("name"), dict) else {}
        name_en = str(name_info.get("nameEn") or "").strip()
        name_zh = str(basic_info.get("nameZh") or "").strip()
        if not name_en and not name_zh:
            continue
        results.append(
            {
                "name": name_en or name_zh,
                "name_zh": name_zh,
                "label": name_en or name_zh,
            }
        )
    return results


def _match_reason_candidates(
    *,
    query: str,
    graph_labels: List[str],
    reason_payload: Dict[str, Any],
    seed_terms: List[str],
) -> List[Dict[str, Any]]:
    graph_label_map = {_normalize_openspg_label(item): item for item in graph_labels}
    if not graph_label_map:
        return []
    candidates: List[Dict[str, Any]] = []
    query_text = str(query or "")
    reason_types = _extract_reason_types(reason_payload)
    for item in reason_types:
        simple_label = _normalize_openspg_label(item.get("label") or item.get("name") or "")
        if simple_label not in graph_label_map:
            continue
        score = 0.0
        name = str(item.get("name") or "")
        name_zh = str(item.get("name_zh") or "")
        if name and name.lower() in query_text.lower():
            score += 1.2
        if name_zh and name_zh in query_text:
            score += 1.2
        for term in _TYPE_HINTS.get(simple_label, ()):
            if term in query_text:
                score += 0.6
        for term in seed_terms:
            if name and name.lower() in term.lower():
                score += 0.4
            if name_zh and name_zh in term:
                score += 0.4
        if simple_label in {"Document", "Company"}:
            score += 0.1
        if score <= 0:
            continue
        candidates.append(
            {
                "label": graph_label_map[simple_label],
                "name": name or simple_label,
                "name_zh": name_zh or simple_label,
                "score": round(score, 3),
            }
        )
    if not candidates:
        for fallback in ("Company", "Document", "Technology", "Product"):
            if fallback in graph_label_map:
                candidates.append(
                    {
                        "label": graph_label_map[fallback],
                        "name": fallback,
                        "name_zh": fallback,
                        "score": 0.1,
                    }
                )
    candidates.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    return candidates[:4]


def _escape_cypher_literal(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def _build_graph_label_map(graph_labels: List[str]) -> Dict[str, str]:
    return {
        _normalize_openspg_label(item): str(item).strip()
        for item in graph_labels
        if str(item).strip()
    }


def _infer_query_focus_labels(
    *,
    query: str,
    reason_candidates: List[Dict[str, Any]],
    graph_labels: List[str],
) -> List[str]:
    graph_label_map = _build_graph_label_map(graph_labels)
    focus = []
    query_text = str(query or "")
    for label, hints in _QUERY_RELATION_HINTS.items():
        if label in graph_label_map and any(hint in query_text for hint in hints):
            focus.append(label)
    for item in reason_candidates:
        simple_label = _normalize_openspg_label(item.get("label") or item.get("name") or "")
        if simple_label in graph_label_map and simple_label not in focus:
            focus.append(simple_label)
    if "Document" in graph_label_map and "Document" not in focus:
        focus.append("Document")
    return focus


def _build_multi_hop_query(
    *,
    anchor_label: str,
    first_edge: str,
    neighbor_label: str,
    second_edge: Optional[str],
    anchor_term: str,
    top_k: int,
    path_tag: str,
    exclude_same_name: bool = False,
) -> str:
    escaped_anchor = _escape_cypher_literal(anchor_term)
    where_clauses = [
        f'toString(anchor.name) CONTAINS "{escaped_anchor}"',
        f'toString(anchor.title) CONTAINS "{escaped_anchor}"',
        f'toString(anchor.description) CONTAINS "{escaped_anchor}"',
    ]
    where_sql = " OR ".join(where_clauses)
    if second_edge:
        same_name_clause = " AND toString(neighbor.name) <> toString(anchor.name)" if exclude_same_name else ""
        return (
            f"MATCH path = (anchor:`{anchor_label}`)<-[:{first_edge}]-(doc:`zhilian.Document`)-[:{second_edge}]->(neighbor:`{neighbor_label}`) "
            f"WHERE ({where_sql}){same_name_clause} "
            f'RETURN neighbor AS node, 2.0 AS score, doc.id AS docBizId, doc.title AS docTitle, doc.description AS docDescription, '
            f'anchor.id AS anchorBizId, anchor.name AS anchorName, "{path_tag}" AS pathTag LIMIT {top_k}'
        )
    return (
        f"MATCH path = (anchor:`{anchor_label}`)<-[:{first_edge}]-(doc:`zhilian.Document`) "
        f"WHERE ({where_sql}) "
        f'RETURN doc AS node, 1.8 AS score, doc.id AS docBizId, doc.title AS docTitle, doc.description AS docDescription, '
        f'anchor.id AS anchorBizId, anchor.name AS anchorName, "{path_tag}" AS pathTag LIMIT {top_k}'
    )


def _build_document_anchor_query(
    *,
    anchor_term: str,
    top_k: int,
    path_tag: str,
) -> str:
    escaped_anchor = _escape_cypher_literal(anchor_term)
    return (
        'MATCH path = (doc:`zhilian.Document`)-[r]->(neighbor) '
        f'WHERE toString(doc.title) CONTAINS "{escaped_anchor}" '
        f'OR toString(doc.name) CONTAINS "{escaped_anchor}" '
        f'OR toString(doc.description) CONTAINS "{escaped_anchor}" '
        f'RETURN neighbor AS node, 1.7 AS score, doc.id AS docBizId, doc.title AS docTitle, doc.description AS docDescription, type(r) AS relType, '
        f'"{path_tag}" AS pathTag LIMIT {top_k}'
    )


def _build_openspg_query_plan(
    *,
    query: str,
    top_k: int,
    graph_labels: List[str],
    reason_candidates: List[Dict[str, Any]],
    seed_terms: List[str],
) -> List[Dict[str, str]]:
    graph_label_map = _build_graph_label_map(graph_labels)
    if not graph_label_map:
        return [{"kind": "text_fallback", "tag": "text_contains", "query": item} for item in _build_openspg_search_queries(
            query=query,
            top_k=top_k,
            reason_candidates=reason_candidates,
            seed_terms=seed_terms,
        )]

    llm_rewrite = _rewrite_query_with_llm(query)
    anchor_terms: List[str] = []
    seen_anchor_terms = set()
    query_anchor_candidates = _extract_query_terms(query, seed_terms=None)

    for item in list(llm_rewrite.get("entities") or []) + query_anchor_candidates:
        value = _normalize_query_term(item)
        if not value or _is_generic_query_term(value) or value in seen_anchor_terms:
            continue
        seen_anchor_terms.add(value)
        anchor_terms.append(value)
        if len(anchor_terms) >= 2:
            break
    if not anchor_terms:
        for item in seed_terms:
            value = _normalize_query_term(item)
            if not value or _is_generic_query_term(value) or value in seen_anchor_terms:
                continue
            seen_anchor_terms.add(value)
            anchor_terms.append(value)
            if len(anchor_terms) >= 2:
                break

    focus_labels = _infer_query_focus_labels(
        query=query,
        reason_candidates=reason_candidates,
        graph_labels=graph_labels,
    )
    for item in llm_rewrite.get("target_types") or []:
        if item in graph_label_map and item not in focus_labels:
            focus_labels.insert(0, item)
    for intent in llm_rewrite.get("relation_intents") or []:
        for tag in _LLM_RELATION_TAG_PRIORITY.get(intent, []):
            if tag.endswith("_to_technology") or tag == "technology_to_company":
                if "Technology" in graph_label_map and "Technology" not in focus_labels:
                    focus_labels.insert(0, "Technology")
            elif tag.endswith("_to_product") or tag == "product_to_company":
                if "Product" in graph_label_map and "Product" not in focus_labels:
                    focus_labels.insert(0, "Product")
            elif tag == "company_to_company":
                if "Company" in graph_label_map and "Company" not in focus_labels:
                    focus_labels.insert(0, "Company")
            elif tag.endswith("_to_document"):
                if "Document" in graph_label_map and "Document" not in focus_labels:
                    focus_labels.insert(0, "Document")

    plan: List[Dict[str, str]] = []
    seen_queries = set()

    def add_query(kind: str, tag: str, query_text: str, *, target_label: str = "") -> None:
        if not query_text or query_text in seen_queries:
            return
        seen_queries.add(query_text)
        payload = {"kind": kind, "tag": tag, "query": query_text}
        if target_label:
            payload["target_label"] = target_label
        plan.append(payload)

    def full_label(simple_label: str) -> str:
        return graph_label_map.get(simple_label, f"zhilian.{simple_label}")

    if anchor_terms and "Document" in graph_label_map:
        if "Technology" in focus_labels and {"Company", "Technology", "Document"}.issubset(graph_label_map):
            for anchor_term in anchor_terms:
                add_query(
                    "graph_multi_hop",
                    "company_to_technology",
                    _build_multi_hop_query(
                        anchor_label=full_label("Company"),
                        first_edge="mentionsCompany",
                        neighbor_label=full_label("Technology"),
                        second_edge="mentionsTech",
                        anchor_term=anchor_term,
                        top_k=top_k,
                        path_tag="graph.multi_hop.company_to_technology",
                    ),
                    target_label=full_label("Technology"),
                )
                add_query(
                    "graph_multi_hop",
                    "technology_to_company",
                    _build_multi_hop_query(
                        anchor_label=full_label("Technology"),
                        first_edge="mentionsTech",
                        neighbor_label=full_label("Company"),
                        second_edge="mentionsCompany",
                        anchor_term=anchor_term,
                        top_k=top_k,
                        path_tag="graph.multi_hop.technology_to_company",
                    ),
                    target_label=full_label("Company"),
                )
        if "Product" in focus_labels and {"Company", "Product", "Document"}.issubset(graph_label_map):
            for anchor_term in anchor_terms:
                add_query(
                    "graph_multi_hop",
                    "company_to_product",
                    _build_multi_hop_query(
                        anchor_label=full_label("Company"),
                        first_edge="mentionsCompany",
                        neighbor_label=full_label("Product"),
                        second_edge="mentionsProduct",
                        anchor_term=anchor_term,
                        top_k=top_k,
                        path_tag="graph.multi_hop.company_to_product",
                    ),
                    target_label=full_label("Product"),
                )
                add_query(
                    "graph_multi_hop",
                    "product_to_company",
                    _build_multi_hop_query(
                        anchor_label=full_label("Product"),
                        first_edge="mentionsProduct",
                        neighbor_label=full_label("Company"),
                        second_edge="mentionsCompany",
                        anchor_term=anchor_term,
                        top_k=top_k,
                        path_tag="graph.multi_hop.product_to_company",
                    ),
                    target_label=full_label("Company"),
                )
        if "Company" in focus_labels and {"Company", "Document"}.issubset(graph_label_map):
            for anchor_term in anchor_terms:
                add_query(
                    "graph_multi_hop",
                    "company_to_company",
                    _build_multi_hop_query(
                        anchor_label=full_label("Company"),
                        first_edge="mentionsCompany",
                        neighbor_label=full_label("Company"),
                        second_edge="mentionsCompany",
                        anchor_term=anchor_term,
                        top_k=top_k,
                        path_tag="graph.multi_hop.company_to_company",
                        exclude_same_name=True,
                    ),
                    target_label=full_label("Company"),
                )
        if "Document" in focus_labels:
            for anchor_term in anchor_terms:
                for simple_label, relation in _DOCUMENT_RELATION_MAP.items():
                    if simple_label not in graph_label_map:
                        continue
                    add_query(
                        "graph_multi_hop",
                        f"{simple_label.lower()}_to_document",
                        _build_multi_hop_query(
                            anchor_label=full_label(simple_label),
                            first_edge=relation,
                            neighbor_label=full_label("Document"),
                            second_edge=None,
                            anchor_term=anchor_term,
                            top_k=top_k,
                            path_tag=f"graph.multi_hop.{simple_label.lower()}_to_document",
                        ),
                        target_label=full_label("Document"),
                    )

        for anchor_term in anchor_terms:
            if "Technology" in focus_labels and "Technology" in graph_label_map:
                add_query(
                    "graph_document_anchor",
                    "document_anchor_technology",
                    _build_document_anchor_query(
                        anchor_term=anchor_term,
                        top_k=top_k,
                        path_tag="graph.multi_hop.document_anchor_technology",
                    ),
                    target_label=full_label("Technology"),
                )
            if "Product" in focus_labels and "Product" in graph_label_map:
                add_query(
                    "graph_document_anchor",
                    "document_anchor_product",
                    _build_document_anchor_query(
                        anchor_term=anchor_term,
                        top_k=top_k,
                        path_tag="graph.multi_hop.document_anchor_product",
                    ),
                    target_label=full_label("Product"),
                )
            if "Company" in focus_labels and "Company" in graph_label_map:
                add_query(
                    "graph_document_anchor",
                    "document_anchor_company",
                    _build_document_anchor_query(
                        anchor_term=anchor_term,
                        top_k=top_k,
                        path_tag="graph.multi_hop.document_anchor_company",
                    ),
                    target_label=full_label("Company"),
                )

    for item in _build_openspg_search_queries(
        query=query,
        top_k=top_k,
        reason_candidates=reason_candidates,
        seed_terms=seed_terms,
    ):
        add_query("text_fallback", "text_contains", item)

    priority_tags: List[str] = []
    for intent in llm_rewrite.get("relation_intents") or []:
        for tag in _LLM_RELATION_TAG_PRIORITY.get(intent, []):
            if tag not in priority_tags:
                priority_tags.append(tag)
    if priority_tags:
        plan.sort(
            key=lambda item: (
                0 if item.get("tag") in priority_tags else 1,
                priority_tags.index(item.get("tag")) if item.get("tag") in priority_tags else 999,
                0 if item.get("kind") == "graph_multi_hop" else 1,
            )
        )

    return plan[:12]


def _build_openspg_search_queries(
    *,
    query: str,
    top_k: int,
    reason_candidates: List[Dict[str, Any]],
    seed_terms: List[str],
) -> List[str]:
    queries: List[str] = []
    seen = set()
    terms = _extract_query_terms(query, seed_terms=seed_terms)
    for term in terms[:4]:
        escaped_term = _escape_cypher_literal(term)
        for candidate in reason_candidates[:3]:
            label = str(candidate.get("label") or "").strip()
            if not label:
                continue
            custom_query = (
                f'MATCH (n:`{label}`) '
                f'WHERE toString(n.name) CONTAINS "{escaped_term}" '
                f'OR toString(n.title) CONTAINS "{escaped_term}" '
                f'OR toString(n.description) CONTAINS "{escaped_term}" '
                f'OR toString(n.content) CONTAINS "{escaped_term}" '
                f'RETURN n AS node, 1.0 AS score LIMIT {top_k}'
            )
            if custom_query not in seen:
                seen.add(custom_query)
                queries.append(custom_query)
    if not queries:
        escaped_query = _escape_cypher_literal(query)
        queries.append(
            f'MATCH (n) WHERE toString(n.name) CONTAINS "{escaped_query}" '
            f'OR toString(n.title) CONTAINS "{escaped_query}" '
            f'RETURN n AS node, 1.0 AS score LIMIT {top_k}'
        )
    return queries[:9]


def _extract_openspg_hits(
    search_result: Dict[str, Any],
    *,
    custom_query: str,
    source: str = "search/custom",
    path_tag: str = "",
    expected_target_label: str = "",
) -> List[Dict[str, Any]]:
    response = search_result.get("response")
    rows = response if isinstance(response, list) else []
    hits: List[Dict[str, Any]] = []
    expected_label_match = re.search(r"MATCH \(n:`([^`]+)`\)", custom_query)
    expected_label = expected_label_match.group(1).strip() if expected_label_match else ""
    for idx, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        fields = item.get("fields") if isinstance(item.get("fields"), dict) else {}
        node = item.get("node") if isinstance(item.get("node"), dict) else item
        labels = (
            fields.get("__labels__")
            or item.get("labels")
            or node.get("labels")
            or node.get("label")
            or node.get("@type")
            or node.get("type")
        )
        if isinstance(labels, list):
            label_text = ",".join(str(label) for label in labels if str(label).strip())
        else:
            label_text = str(labels or "").strip()
        name = str(
            fields.get("name")
            or fields.get("title")
            or node.get("name")
            or node.get("title")
            or item.get("name")
            or fields.get("id")
            or node.get("id")
            or item.get("docId")
            or f"hit_{idx}"
        ).strip()
        summary = str(
            fields.get("description")
            or fields.get("content")
            or fields.get("docTitle")
            or fields.get("docDescription")
            or fields.get("title")
            or node.get("description")
            or node.get("title")
            or node.get("content")
            or item.get("summary")
            or ""
        ).strip()
        hit_id = str(
            fields.get("id")
            or node.get("id")
            or item.get("id")
            or item.get("docId")
            or f"{label_text}:{name}:{idx}"
        )
        inferred_label = ""
        if hit_id.startswith("DOC_"):
            inferred_label = "zhilian.Document"
        elif hit_id.startswith("CHK_"):
            inferred_label = "zhilian.Chunk"
        elif hit_id.startswith("COM_"):
            inferred_label = "zhilian.Company"
        elif hit_id.startswith("PROD_"):
            inferred_label = "zhilian.Product"
        elif hit_id.startswith("TECH_"):
            inferred_label = "zhilian.Technology"
        elif hit_id.startswith("KP_"):
            inferred_label = "zhilian.KnowledgePoint"
        if not label_text or label_text == "OpenSPGNode":
            label_text = inferred_label or label_text
        elif expected_target_label and inferred_label == expected_target_label:
            label_text = inferred_label
        if expected_label and label_text not in {expected_label, "OpenSPGNode"}:
            continue
        if expected_target_label and label_text != expected_target_label:
            continue
        hits.append(
            {
                "id": hit_id,
                "name": name,
                "label": label_text or "OpenSPGNode",
                "summary": summary[:160],
                "score": float(item.get("score") or 1.0),
                "source": source,
                "custom_query": custom_query,
                "path_tag": str(fields.get("pathTag") or item.get("pathTag") or path_tag or ""),
                "anchor_name": str(fields.get("anchorName") or item.get("anchorName") or ""),
                "anchor_id": str(fields.get("anchorBizId") or item.get("anchorBizId") or fields.get("anchorId") or item.get("anchorId") or ""),
                "doc_id": str(fields.get("docBizId") or item.get("docBizId") or fields.get("docId") or item.get("docId") or ""),
                "relation_type": str(fields.get("relType") or item.get("relType") or ""),
                "doc_title": str(fields.get("docTitle") or item.get("docTitle") or ""),
                "doc_description": str(fields.get("docDescription") or item.get("docDescription") or ""),
            }
        )
    return [item for item in hits if not _is_noisy_entity_name(item.get("name") or "")]


async def _run_openspg_query_async(
    *,
    query: str,
    top_k: int,
    project_id: int,
    seed_terms: List[str],
) -> Dict[str, Any]:
    reason_result, graph_result = await asyncio.gather(
        get_openspg_reason_schema(project_id=project_id),
        get_openspg_graph_labels(project_id=project_id),
    )
    graph_labels_raw = graph_result.get("response")
    graph_labels = [str(item).strip() for item in graph_labels_raw if str(item).strip()] if isinstance(graph_labels_raw, list) else []
    reason_candidates = _match_reason_candidates(
        query=query,
        graph_labels=graph_labels,
        reason_payload=reason_result,
        seed_terms=seed_terms,
    )
    query_plan = _build_openspg_query_plan(
        query=query,
        top_k=top_k,
        graph_labels=graph_labels,
        reason_candidates=reason_candidates,
        seed_terms=seed_terms,
    )

    search_results: List[Dict[str, Any]] = []
    hits: List[Dict[str, Any]] = []
    seen_ids = set()
    graph_hit_count = 0
    for plan_item in query_plan:
        if plan_item.get("kind") == "text_fallback" and graph_hit_count > 0:
            continue
        custom_query = str(plan_item.get("query") or "")
        result = await search_openspg_custom(project_id=project_id, custom_query=custom_query)
        search_results.append(
            {
                "query": custom_query,
                "kind": plan_item.get("kind"),
                "tag": plan_item.get("tag"),
                "mode": result.get("mode"),
                "http_status": result.get("http_status"),
            }
        )
        extracted_hits = _extract_openspg_hits(
            result,
            custom_query=custom_query,
            source="graph.multi_hop" if plan_item.get("kind") in {"graph_multi_hop", "graph_document_anchor"} else "search/custom",
            path_tag=str(plan_item.get("tag") or ""),
            expected_target_label=str(plan_item.get("target_label") or ""),
        )
        if plan_item.get("kind") in {"graph_multi_hop", "graph_document_anchor"}:
            graph_hit_count += len(extracted_hits)
        for item in extracted_hits:
            dedupe_key = (item.get("id"), item.get("label"))
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            hits.append(item)
        if plan_item.get("kind") in {"graph_multi_hop", "graph_document_anchor"} and extracted_hits:
            break

    has_live_call = any(
        check.get("mode") == "live"
        for check in [reason_result, graph_result]
    ) or any(item.get("mode") == "live" for item in search_results)

    status = "live" if hits else ("empty" if has_live_call else "offline")
    return {
        "status": status,
        "mode": "openspg" if has_live_call else "offline",
        "graph_labels": graph_labels[:12],
        "reason_candidates": reason_candidates,
        "query_plan": query_plan,
        "search_queries": [str(item.get("query") or "") for item in query_plan],
        "search_checks": search_results,
        "graph_query_count": len([item for item in query_plan if item.get("kind") in {"graph_multi_hop", "graph_document_anchor"}]),
        "graph_hit_count": graph_hit_count,
        "hits": hits[:top_k],
    }


def _run_openspg_query(
    *,
    query: str,
    top_k: int,
    filters: Dict[str, Any],
    seed_terms: List[str],
) -> Dict[str, Any]:
    project_id = _pick_project_id(filters)
    try:
        return asyncio.run(
            _run_openspg_query_async(
                query=query,
                top_k=top_k,
                project_id=project_id,
                seed_terms=seed_terms,
            )
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                _run_openspg_query_async(
                    query=query,
                    top_k=top_k,
                    project_id=project_id,
                    seed_terms=seed_terms,
                )
            )
        finally:
            loop.close()
    except Exception as exc:
        return {
            "status": "offline",
            "mode": "offline",
            "graph_labels": [],
            "reason_candidates": [],
            "search_queries": [],
            "search_checks": [],
            "hits": [],
            "error": str(exc),
        }


def _prepare_query_context(
    *,
    query: str,
    query_type: str,
    top_k: int,
    filters: Dict[str, Any],
    include_evidence: bool,
) -> Dict[str, Any]:
    hours = _pick_hours(filters)
    top_n = min(max(top_k, 1), 100)
    allow_demo_fallback = bool(filters.get("allow_demo_fallback", True))
    strategy = _pick_qa_strategy(filters)
    resolved_artifact_id = _resolve_artifact_filter(filters)

    classic_result = _run_classic_query(
        query=query,
        top_k=top_n,
        hours=hours,
        allow_demo_fallback=allow_demo_fallback,
        include_evidence=include_evidence,
        generate_answer=False,
        filters=filters,
    )
    openspg_result = _run_openspg_query(
        query=query,
        top_k=top_n,
        filters=filters,
        seed_terms=classic_result.get("entities") or [],
    )

    classic_hits = list(classic_result.get("hits") or [])
    openspg_hits = list(openspg_result.get("hits") or [])
    answer_mode = "classic"
    if strategy != "classic" and openspg_hits:
        answer_mode = "openspg"
    elif strategy in {"openspg", "compare"}:
        answer_mode = "classic_fallback"

    trace_id = f"trace_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    event_ids = [
        str(item.get("event_id") or "").strip()
        for item in classic_result.get("headlines") or []
        if str(item.get("event_id") or "").strip()
    ]
    classic_data_source = str(classic_result.get("data_source") or "unknown")
    classic_stage = "structured_statement" if "inc_statement" in classic_data_source else "workflow_apply"
    classic_reasoning = ["knowledge:news_kg"] if "inc_statement" in classic_data_source else ["workflow:apply"]

    retrieval_compare = {
        "strategy": strategy,
        "answer_mode": answer_mode,
        "classic": {
            "hit_count": len(classic_hits),
            "data_source": classic_data_source,
            "kg_name": classic_result.get("kg_name"),
            "hits": classic_hits,
        },
        "openspg": {
            "status": openspg_result.get("status"),
            "mode": openspg_result.get("mode"),
            "hit_count": len(openspg_hits),
            "graph_hit_count": int(openspg_result.get("graph_hit_count") or 0),
            "graph_query_count": int(openspg_result.get("graph_query_count") or 0),
            "hits": openspg_hits,
            "graph_labels": openspg_result.get("graph_labels") or [],
            "reason_candidates": openspg_result.get("reason_candidates") or [],
            "query_plan": openspg_result.get("query_plan") or [],
            "search_queries": openspg_result.get("search_queries") or [],
            "search_checks": openspg_result.get("search_checks") or [],
            "error": openspg_result.get("error"),
        },
    }

    workflow_reference = _build_workflow_reference(event_ids)
    tables_used = _infer_tables_used(str(classic_result.get("data_source") or ""))
    graph_path_view = _build_graph_path_view(
        query=query,
        openspg_hits=openspg_hits,
        evidences=classic_result.get("evidences") or [],
        workflow_reference=workflow_reference,
        tables_used=tables_used,
    )
    trace_payload = {
        "query_plan": {
            "query": query,
            "query_type": query_type,
            "top_k": top_n,
            "hours": hours,
            "include_evidence": include_evidence,
            "qa_strategy": strategy,
            "answer_mode": answer_mode,
            "filters": {
                "artifact_id": resolved_artifact_id,
                "release_id": str(filters.get("release_id") or "").strip(),
                "release_version": str(filters.get("release_version") or "").strip(),
            },
        },
        "data_sources": [
            {
                "name": classic_data_source,
                "stage": classic_stage,
                "kg_name": classic_result.get("kg_name"),
            },
            {
                "name": "openspg",
                "stage": "graph_reason_search",
            },
        ],
        "tables_used": tables_used,
        "workflow_reference": workflow_reference,
        "retrieval_hits": classic_hits,
        "classic_retrieval_hits": classic_hits,
        "openspg_retrieval_hits": openspg_hits,
        "retrieval_compare": retrieval_compare,
        "graph_path_view": graph_path_view,
        "reasoning_path": [
            "ingestion:news",
            "extraction:kag",
            *classic_reasoning,
            "semantic:openspg.graph",
            "semantic:openspg.reason",
            *(
                ["semantic:openspg.multi_hop"]
                if int(openspg_result.get("graph_query_count") or 0) > 0
                else []
            ),
            "semantic:openspg.search",
            "gateway:open-api",
        ],
        "model_usage": {
            "mode": answer_mode,
            "provider": (
                "openspg-first"
                if answer_mode == "openspg"
                else ("news_kg-first" if "inc_statement" in classic_data_source else "workflow-headlines")
            ),
        },
        "citations_summary": {
            "count": len(classic_result.get("evidences") or []),
            "doc_ids": [str(item.get("doc_id") or "").strip() for item in classic_result.get("evidences") or []],
            "statement_ids": [str(item.get("statement_id") or "").strip() for item in classic_result.get("evidences") or []],
        },
    }
    _remember_trace(trace_id, trace_payload)
    return {
        "query": query,
        "query_type": query_type,
        "top_k": top_n,
        "filters": filters,
        "include_evidence": include_evidence,
        "trace_id": trace_id,
        "trace_payload": trace_payload,
        "workflow_reference": workflow_reference,
        "answer_mode": answer_mode,
        "retrieval_compare": retrieval_compare,
        "graph_path_view": graph_path_view,
        "classic_result": classic_result,
        "openspg_result": openspg_result,
        "knowledge_objects": classic_result.get("knowledge_objects") or [],
        "entities": classic_result.get("entities") or [],
        "evidences": classic_result.get("evidences") or [],
    }


def _stream_query_answer(context: Dict[str, Any]):
    if str(context.get("answer_mode") or "") == "openspg":
        prompt, fallback = _build_openspg_answer_prompt(
            query=str(context.get("query") or ""),
            openspg_hits=((context.get("openspg_result") or {}).get("hits") or []),
            evidences=context.get("evidences") or [],
        )
    else:
        prompt, fallback = _build_classic_answer_prompt(
            query=str(context.get("query") or ""),
            headlines=((context.get("classic_result") or {}).get("headlines") or []),
            evidences=context.get("evidences") or [],
        )
    yield from _stream_answer_with_llm(prompt, fallback, max_tokens=1200)


def _build_query_response(context: Dict[str, Any], answer: str) -> Dict[str, Any]:
    workflow_reference = context.get("workflow_reference") or {}
    return {
        "answer": answer,
        "answer_mode": context.get("answer_mode") or "classic",
        "retrieval_compare": context.get("retrieval_compare") or {},
        "graph_path_view": context.get("graph_path_view") or {},
        "knowledge_objects": context.get("knowledge_objects") or [],
        "entities": context.get("entities") or [],
        "evidences": context.get("evidences") or [],
        "trace_id": context.get("trace_id"),
        "run_id": workflow_reference.get("run_id") or ((context.get("filters") or {}).get("run_id")),
    }


def _run_query(
    *,
    query: str,
    query_type: str,
    top_k: int,
    filters: Dict[str, Any],
    include_evidence: bool,
) -> Dict[str, Any]:
    context = _prepare_query_context(
        query=query,
        query_type=query_type,
        top_k=top_k,
        filters=filters,
        include_evidence=include_evidence,
    )
    answer_chunks = list(_stream_query_answer(context))
    answer = "".join(answer_chunks).strip()
    if not answer:
        if str(context.get("answer_mode") or "") == "openspg":
            answer = _build_openspg_answer(
                ((context.get("openspg_result") or {}).get("hits") or []),
                query,
            )
        else:
            answer = _build_answer(
                ((context.get("classic_result") or {}).get("headlines") or []),
                query,
            )
    return _build_query_response(context, answer)


@router.get("/applications/headlines")
def get_open_headlines(
    hours: int = Query(24, ge=1, le=168),
    top_n: int = Query(20, ge=1, le=100),
    allow_demo_fallback: bool = Query(True),
):
    payload = _query_headlines(
        hours=hours,
        top_n=top_n,
        allow_demo_fallback=allow_demo_fallback,
    )
    meta = dict(payload.get("meta") or {})
    meta.update(
        {
            "access_scope": "open",
            "hours": hours,
            "top_n": top_n,
        }
    )
    payload["meta"] = meta
    return payload


@router.post("/knowledge/query")
def open_knowledge_query(request: OpenKnowledgeQueryRequest):
    return _run_query(
        query=request.query,
        query_type=request.query_type,
        top_k=request.top_k,
        filters=request.filters,
        include_evidence=request.include_evidence,
    )


@router.post("/knowledge/query/batch")
def open_knowledge_query_batch(request: OpenKnowledgeBatchQueryRequest):
    if not request.queries:
        raise HTTPException(status_code=400, detail="queries 不能为空")
    results = []
    for item in request.queries:
        query = str(item or "").strip()
        if not query:
            continue
        result = _run_query(
            query=query,
            query_type=request.query_type,
            top_k=request.top_k,
            filters=request.filters,
            include_evidence=request.include_evidence,
        )
        results.append({"query": query, **result})
    return {
        "count": len(results),
        "results": results,
    }


@router.get("/knowledge/trace/{trace_id}")
def get_open_knowledge_trace(trace_id: str):
    trace = _read_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="trace_id 不存在")
    return trace
