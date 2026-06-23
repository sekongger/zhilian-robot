"""DTO normalization for agent-facing news graph MCP responses."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse


PLACEHOLDER_SOURCE_DOMAINS = {"example.com", "example.org", "example.net"}


def normalize_news_record(record: Dict[str, Any], *, include_full_content: bool = False) -> Dict[str, Any]:
    """Convert a Neo4j row containing an Episodic node into MCP-safe JSON."""

    news = _as_mapping(record.get("news"))
    source_profile = _extract_source_profile(news)
    fact_payload = _as_mapping(_maybe_json(news.get("factPayload")))
    labels = [str(item) for item in record.get("labels") or []]
    entities = [item for item in (normalize_entity(raw) for raw in _as_list(record.get("entities"))) if _has_entity_signal(item)]
    events = [item for item in (normalize_event(raw) for raw in _as_list(record.get("events"))) if _has_event_signal(item)]
    relations = [item for item in (normalize_relation(raw) for raw in _as_list(record.get("relations"))) if _has_relation_signal(item)]
    publish_time = _stringify_time(
        record.get("publish_time")
        or _first(news, "publish_time", "valid_at", "created_at", "ingested_at")
        or _first(source_profile, "publish_time", "valid_at", "created_at", "ingested_at")
    )
    content = (
        _first(news, "content", "raw_text", "description", "summary")
        or _first(fact_payload, "summary", "raw_text", "description", "content")
        or _first(source_profile, "content", "raw_text", "description", "summary")
        or ""
    )
    full_content = (
        _first(news, "content", "raw_text")
        or _first(fact_payload, "raw_text", "content")
        or _first(source_profile, "content", "raw_text")
        or content
    )

    item = {
        "news_id": _first(news, "id", "graph_id", "uuid") or "",
        "title": _first(news, "title", "name", "label") or _first(source_profile, "title", "name") or _first(news, "id", "uuid") or "",
        "summary": _first(news, "summary", "description", "abstract", "content") or _first(fact_payload, "summary", "description") or _first(source_profile, "summary", "description") or "",
        "content_excerpt": _clip(str(content), 500),
        "publish_time": publish_time,
        "ingested_at": _stringify_time(_first(news, "ingested_at", "created_at") or _first(source_profile, "ingested_at", "created_at")),
        "source_name": _first(news, "source_name", "source", "sourceSystem", "data_source") or _first(source_profile, "news_source", "source", "source_name") or "",
        "source_url": _first_valid_source_url(
            _first(news, "source_url", "url", "news_url"),
            _first(source_profile, "news_url", "source_url", "url"),
        ),
        "batch_id": _first(news, "batchId", "batch_id") or _first(source_profile, "batchId", "batch_id") or "",
        "group_id": _first(news, "group_id", "fusion_batch_id") or _first(source_profile, "group_id", "fusion_batch_id") or "",
        "labels": labels,
        "entities": entities,
        "events": events,
        "relations": relations,
        "briefing_signals": build_briefing_signals(entities=entities, events=events, relations=relations),
    }
    if include_full_content:
        item["content"] = str(full_content)
    return item


def normalize_entity(raw: Any) -> Dict[str, Any]:
    data = _as_mapping(raw)
    source_profiles = _as_mapping(_maybe_json(data.get("sourceProfiles")))
    v2_profile = _as_mapping(source_profiles.get("v2"))
    entity_type = (
        data.get("type")
        or data.get("type_name")
        or data.get("sourceType")
        or v2_profile.get("sourceType")
        or data.get("canonicalType")
        or ""
    )
    return {
        "name": str(data.get("name") or data.get("title") or data.get("label") or ""),
        "type": str(entity_type),
        "profile_id": str(data.get("id") or data.get("graph_id") or data.get("uuid") or ""),
        "canonical_graph_id": str(data.get("canonicalGraphId") or v2_profile.get("canonicalGraphId") or ""),
        "match_method": str(data.get("matchMethod") or v2_profile.get("matchMethod") or ""),
        "match_score": _to_float(data.get("matchScore") or v2_profile.get("matchScore")),
        "summary": str(data.get("summary") or data.get("description") or ""),
    }


def normalize_event(raw: Any) -> Dict[str, Any]:
    data = _as_mapping(raw)
    return {
        "event_type": str(data.get("event_type") or data.get("type") or data.get("type_name") or data.get("name") or ""),
        "event_time": _stringify_time(data.get("event_time") or data.get("eventTime") or data.get("publishTime")),
        "summary": str(data.get("summary") or data.get("description") or data.get("name") or ""),
        "evidence": str(data.get("evidence") or data.get("evidence_text") or ""),
    }


def normalize_relation(raw: Any) -> Dict[str, Any]:
    data = _as_mapping(raw)
    return {
        "subject": str(data.get("subject") or data.get("source") or data.get("source_name") or ""),
        "predicate": str(data.get("predicate") or data.get("type") or ""),
        "object": str(data.get("object") or data.get("target") or data.get("target_name") or ""),
        "evidence": str(data.get("evidence") or data.get("evidence_text") or ""),
    }


def normalize_enterprise_context_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a graph row into an LLM-readable enterprise context payload."""

    enterprise = normalize_graph_node(record.get("enterprise"), record.get("enterprise_labels"))
    related_entities = [
        item
        for item in (normalize_related_entity(raw) for raw in _as_list(record.get("related_entities")))
        if item.get("name") or item.get("id")
    ]
    news_timeline = [
        item
        for raw in _as_list(record.get("news_items"))
        if _as_mapping(raw.get("news")).get("id") or _as_mapping(raw.get("news")).get("title") or _as_mapping(raw.get("news")).get("name")
        for item in [normalize_news_record(raw)]
        if is_traceable_source_url(item.get("source_url"))
    ]
    products = _unique_nodes([item for item in related_entities if item.get("role") == "product_or_technology"])
    upstream_enterprises = _unique_nodes([item for item in related_entities if item.get("role") == "upstream_enterprise"])
    downstream_enterprises = _unique_nodes([item for item in related_entities if item.get("role") == "downstream_enterprise"])

    return {
        "enterprise": enterprise,
        "related_entities": related_entities,
        "upstream_enterprises": upstream_enterprises,
        "downstream_enterprises": downstream_enterprises,
        "products": products,
        "news_timeline": news_timeline,
        "llm_context": build_enterprise_llm_context(
            enterprise=enterprise,
            products=products,
            upstream_enterprises=upstream_enterprises,
            downstream_enterprises=downstream_enterprises,
            news_timeline=news_timeline,
        ),
    }


def normalize_graph_node(raw: Any, labels: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    data = _as_mapping(raw)
    label_rows = [str(item) for item in (labels or [])]
    node_type = str(data.get("type") or data.get("type_name") or data.get("sourceType") or _first_label(label_rows) or "")
    return {
        "id": str(data.get("id") or data.get("graph_id") or data.get("uuid") or ""),
        "name": str(data.get("name") or data.get("title") or data.get("label") or ""),
        "type": node_type,
        "summary": str(data.get("summary") or data.get("description") or ""),
        "canonical_graph_id": str(data.get("canonicalGraphId") or data.get("canonical_graph_id") or ""),
        "labels": label_rows,
    }


def normalize_related_entity(raw: Any) -> Dict[str, Any]:
    data = _as_mapping(raw)
    node = normalize_graph_node(data.get("node"), data.get("labels"))
    relation = str(data.get("relation") or data.get("predicate") or "")
    direction = str(data.get("direction") or "")
    role = classify_related_entity_role(relation=relation, direction=direction, node_type=node.get("type", ""), labels=node.get("labels", []))
    return {
        **node,
        "relation": relation,
        "direction": direction,
        "role": role,
        "evidence": str(data.get("evidence") or data.get("evidence_text") or ""),
        "publish_time": _stringify_time(data.get("publish_time") or data.get("valid_at") or data.get("created_at")),
    }


def classify_related_entity_role(*, relation: str, direction: str, node_type: str, labels: Iterable[str]) -> str:
    text_type = " ".join([node_type, *[str(label) for label in labels]]).lower()
    rel = relation.lower()
    dir_text = direction.lower()
    if any(key in text_type for key in ("product", "technology", "model", "patent")):
        return "product_or_technology"

    enterprise_like = any(key in text_type for key in ("enterprise", "company", "organization", "incore.enterprise"))
    if not enterprise_like:
        return "related_entity"

    upstream_relations = {"supplies", "supplier", "provides", "manufactures", "produces", "sells_to"}
    demand_relations = {"uses", "purchases_from", "depends_on", "has_supplier", "consumes"}
    if dir_text == "incoming" and any(key in rel for key in upstream_relations):
        return "upstream_enterprise"
    if dir_text == "outgoing" and any(key in rel for key in demand_relations):
        return "upstream_enterprise"
    if dir_text == "outgoing" and any(key in rel for key in upstream_relations):
        return "downstream_enterprise"
    if dir_text == "incoming" and any(key in rel for key in demand_relations):
        return "downstream_enterprise"
    return "related_enterprise"


def build_enterprise_llm_context(
    *,
    enterprise: Dict[str, Any],
    products: List[Dict[str, Any]],
    upstream_enterprises: List[Dict[str, Any]],
    downstream_enterprises: List[Dict[str, Any]],
    news_timeline: List[Dict[str, Any]],
) -> str:
    name = enterprise.get("name") or enterprise.get("id") or "该企业"
    parts = [f"围绕{name}，当前图数据库已整理出以下可用于产业链分析的上下文。"]
    if enterprise.get("summary"):
        parts.append(f"企业基本描述：{enterprise['summary']}")
    if upstream_enterprises:
        parts.append(f"可能的上游或供给侧企业包括：{_join_names(upstream_enterprises)}。")
    if downstream_enterprises:
        parts.append(f"可能的下游、客户或应用侧企业包括：{_join_names(downstream_enterprises)}。")
    if products:
        parts.append(f"关联产品、技术或型号包括：{_join_names(products)}。")
    if news_timeline:
        latest_titles = "；".join(item.get("title", "") for item in news_timeline[:3] if item.get("title"))
        if latest_titles:
            parts.append(f"近期相关资讯包括：{latest_titles}。")
    if len(parts) == 1:
        parts.append("当前图中还没有足够的上下游、产品或资讯线索，需要继续补充抽取和融合。")
    return "\n".join(parts)


def build_briefing_signals(
    *,
    entities: Iterable[Dict[str, Any]],
    events: Iterable[Dict[str, Any]],
    relations: Iterable[Dict[str, Any]],
) -> Dict[str, str]:
    entity_rows = list(entities)
    event_rows = list(events)
    relation_rows = list(relations)
    entity_types = {str(item.get("type") or "") for item in entity_rows}
    if "Enterprise" in entity_types or "Company" in entity_types:
        section = "企业动态"
    elif {"Product", "ProductModel", "Technology"} & entity_types:
        section = "产品技术"
    elif event_rows:
        section = "事件变化"
    else:
        section = "产业动态"

    importance = "high" if event_rows or relation_rows else "medium"
    reason = "包含事件或关系线索，适合作为简报重点材料。" if importance == "high" else "包含实体动态，可作为简报补充材料。"
    return {"importance": importance, "reason": reason, "suggested_section": section}


def _as_mapping(value: Any) -> Dict[str, Any]:
    value = _maybe_json(value)
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    value = _maybe_json(value)
    return value if isinstance(value, list) else []


def _maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _first(data: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return None


def _first_label(labels: List[str]) -> str:
    for label in labels:
        if label not in {"IncoreFusionNode", "Entity"}:
            return label
    return labels[0] if labels else ""


def _clip(value: str, max_chars: int) -> str:
    return value if len(value) <= max_chars else value[:max_chars].rstrip() + "..."


def _stringify_time(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unique_nodes(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for item in items:
        key = item.get("id") or item.get("name")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _join_names(items: Iterable[Dict[str, Any]]) -> str:
    names = [str(item.get("name") or item.get("id")) for item in items if item.get("name") or item.get("id")]
    return "、".join(names[:12])


def is_traceable_source_url(value: Any) -> bool:
    url = str(value or "").strip()
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname in PLACEHOLDER_SOURCE_DOMAINS or any(hostname.endswith(f".{domain}") for domain in PLACEHOLDER_SOURCE_DOMAINS):
        return False
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return False
    return True


def _first_valid_source_url(*values: Any) -> str:
    for value in values:
        url = str(value or "").strip()
        if is_traceable_source_url(url):
            return url
    return ""


def _extract_source_profile(news: Dict[str, Any]) -> Dict[str, Any]:
    profiles = _as_mapping(news.get("sourceProfiles"))
    for key in ("graphiti_news", "v2", "octopus", "rss"):
        profile = _as_mapping(profiles.get(key))
        if profile:
            return profile
    for value in profiles.values():
        profile = _as_mapping(value)
        if profile:
            return profile
    return {}


def _has_entity_signal(item: Dict[str, Any]) -> bool:
    return any(item.get(key) for key in ("name", "type", "profile_id", "canonical_graph_id", "summary"))


def _has_event_signal(item: Dict[str, Any]) -> bool:
    return any(item.get(key) for key in ("event_type", "event_time", "summary", "evidence"))


def _has_relation_signal(item: Dict[str, Any]) -> bool:
    return any(item.get(key) for key in ("subject", "predicate", "object", "evidence"))
