from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.news_pipeline.constants import (
    ENTITY_CATEGORY_MAP,
    ENTITY_CLASS_MAP,
    ENTITY_TYPE_MAP,
    PREDICATE_MAP,
)


def _hash(value: str, length: int = 16) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:length]


def make_entity_id(class_id: str, name: str) -> str:
    key = f"{class_id}:{name}".lower().strip()
    return f"EN{_hash(key, 16)}"


def make_statement_id(doc_id: str, subject_id: str, predicate_id: str, object_value: str) -> str:
    key = f"{doc_id}|{subject_id}|{predicate_id}|{object_value}"
    return f"ST{_hash(key, 16)}"


def make_context_id(doc_id: str, statement_id: str) -> str:
    key = f"{doc_id}|{statement_id}"
    return f"KC{_hash(key, 16)}"


def _normalize_predicate(predicate_raw: Optional[str]) -> Tuple[str, Optional[str]]:
    if not predicate_raw:
        return "rel:related_to", None
    if predicate_raw in PREDICATE_MAP:
        return PREDICATE_MAP[predicate_raw], predicate_raw
    if predicate_raw.startswith(("rel:", "prop:")):
        return predicate_raw, None
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", str(predicate_raw)).strip("_").lower()
    if not slug:
        slug = f"rel_{_hash(str(predicate_raw), 8)}"
    return f"rel:{slug}", predicate_raw


def build_entity_docs(entities: Dict[str, List[str]]) -> List[Dict]:
    docs: List[Dict] = []
    seen = set()
    for category, items in (entities or {}).items():
        entity_category = ENTITY_CATEGORY_MAP.get(category)
        class_id = ENTITY_CLASS_MAP.get(category) or "ont:Entity"
        if not entity_category:
            continue
        for name in items or []:
            cleaned = (name or "").strip()
            if not cleaned:
                continue
            key = (category, cleaned)
            if key in seen:
                continue
            seen.add(key)
            docs.append({
                "entity_id": make_entity_id(class_id, cleaned),
                "class_id": class_id,
                "entity_category": entity_category,
                "entity_type": ENTITY_TYPE_MAP.get(category) or category,
                "name": cleaned,
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
    return docs


def build_statement_docs(
    doc_id: str,
    relations: List[Dict],
    entity_map: Dict[str, str],
    doc_type: str,
    data_source: Optional[str] = None,
    publish_time: Optional[str] = None,
    extraction_model: Optional[str] = None,
) -> List[Dict]:
    docs: List[Dict] = []
    for relation in relations or []:
        subject_name = relation.get("subject")
        object_name = relation.get("object")
        if not subject_name or not object_name:
            continue
        subject_id = entity_map.get(subject_name)
        object_id = entity_map.get(object_name)
        if not subject_id or not object_id:
            continue
        predicate_raw = relation.get("relation") or relation.get("predicate")
        predicate_id, predicate_label = _normalize_predicate(predicate_raw)
        statement_id = make_statement_id(doc_id, subject_id, predicate_id, object_id)
        docs.append({
            "statement_id": statement_id,
            "statement_type": "relation",
            "subject_id": subject_id,
            "predicate_id": predicate_id,
            "predicate_label": predicate_label,
            "object_type": "entity_ref",
            "object_entity_id": object_id,
            "doc_id": doc_id,
            "context_id": make_context_id(doc_id, statement_id),
            "confidence": relation.get("confidence", 0.8),
            "extraction_model": extraction_model,
            "context_source_id": data_source,
            "context_scenario": doc_type,
            "context_time_value": publish_time,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
    return docs


def build_context_docs(
    doc_id: str,
    statements: List[Dict],
    doc_type: str,
    data_source: Optional[str],
    publish_time: Optional[str],
) -> List[Dict]:
    docs: List[Dict] = []
    for stmt in statements or []:
        statement_id = stmt.get("statement_id")
        if not statement_id:
            continue
        docs.append({
            "context_id": make_context_id(doc_id, statement_id),
            "context_type": "document",
            "begin_time": publish_time,
            "end_time": None,
            "doc_id": doc_id,
            "context_source_id": data_source,
            "context_scenario": doc_type,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
    return docs
