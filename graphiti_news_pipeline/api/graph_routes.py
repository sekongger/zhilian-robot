import logging
import re
import asyncio
import copy
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.graphiti_service import graphiti_service
from services import calculation_service
from services.calculation_service import UUID_REGEX
from services.entity_heat_service import EntityHeatRankingService
from services.es_service import es_service, GRAPH_NODES_INDEX
from services.news_graph_projection_service import NewsGraphProjectionService
from services.storyline_service import storyline_service
from services.wikidata_mapping_service import wikidata_mapping_service


router = APIRouter()
GRAPH_EDGES_INDEX = "graph_edges"
MAX_ITEMS_PER_SOURCE_LIMIT = 1000

# --- Pydantic Models for Request/Response ---

class AddTextRequest(BaseModel):
    text: str
    title: Optional[str] = None
    name: Optional[str] = None
    publish_time: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    group_id: Optional[str] = None
    fusion_batch_id: Optional[str] = None
    raw_text: Optional[str] = None
    structured_facts: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    center_node_uuid: Optional[str] = None


class CrawlerRunRequest(BaseModel):
    max_items_per_source: int = 5
    since_hours: int = 24
    process_limit: int = 200
    source: Optional[str] = None
    ingest: bool = True
    force_ingest: bool = True


class CrawlerOctopusFullRunRequest(BaseModel):
    max_items_per_source: int = 20
    since_hours: int = 24
    process_limit: int = 300
    ingest_retry_limit: int = 5
    force_ingest: bool = True
    rebuild_storylines: bool = True
    storyline_since_days: int = 30


class WikidataMapRequest(BaseModel):
    names: List[str]


class SyncAnchorsRequest(BaseModel):
    anchors: List[Dict[str, Any]]


class LinkEntitiesRequest(BaseModel):
    decisions: List[Dict[str, Any]]


class EntityHeatRankingRequest(BaseModel):
    period_type: str = "daily"
    as_of: Optional[str] = None
    entity_type: Optional[str] = None
    limit_per_type: int = 50


class NewsGraphProjectionRequest(BaseModel):
    group_id: Optional[str] = None
    limit: int = 5000
    clear_existing: bool = False


_OCTOPUS_FULL_RUNS: dict[str, dict[str, Any]] = {}
_OCTOPUS_FULL_RUN_STATE_LOCK = asyncio.Lock()
_OCTOPUS_FULL_RUN_EXECUTION_LOCK = asyncio.Lock()
_OCTOPUS_FULL_RUN_HISTORY_LIMIT = 50


def _resolve_entity_label(label: Optional[str]) -> Optional[str]:
    if label is None:
        return None

    normalized = label.strip().lower()
    if not normalized:
        return None

    mapping = {
        "company": "Enterprise",
        "enterprise": "Enterprise",
        "product": "Product",
        "productobject": "Product",
        "product_model": "ProductModel",
        "productmodel": "ProductModel",
        "technology": "Technology",
        "tech": "Technology",
    }
    return mapping.get(normalized)


def _serialize_neo4j_properties(data: dict) -> dict:
    """Convert Neo4j temporal values to ISO strings for JSON responses."""

    def _serialize_value(value):
        if isinstance(value, dict):
            return {k: _serialize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_serialize_value(item) for item in value]
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    return {key: _serialize_value(value) for key, value in dict(data).items()}


def _derive_episode_name(text: str, max_len: int = 36) -> str:
    """
    Build a readable episode name from text when caller does not provide one.
    """
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return "Untitled Episode"

    # Prefer the first sentence-like fragment
    first_fragment = re.split(r"[。！？!?;；\n]", normalized)[0].strip()
    candidate = first_fragment if first_fragment else normalized
    if len(candidate) <= max_len:
        return candidate
    return candidate[:max_len].rstrip() + "..."


def _crawler_root() -> Path:
    return Path(__file__).resolve().parents[1] / "crawler"


def _list_crawler_sources() -> list[dict]:
    from crawler.connectors.source_registry import load_sources

    root = _crawler_root()
    sources = load_sources(root / "config" / "sources.yaml")
    return [
        {
            "source_id": source.source_id,
            "name": source.name,
            "type": source.source_type,
            "enabled": source.enabled,
            "priority": source.priority,
            "url": source.url,
            "tags": source.tags,
        }
        for source in sources
    ]


def _run_crawler_once_sync(request: CrawlerRunRequest) -> dict:
    from crawler.connectors.source_registry import load_pipeline_config, load_sources
    from crawler.pipeline.context import PipelineContext
    from crawler.pipeline.orchestrator import CrawlerOrchestrator
    from crawler.services.compression_service import LLMCompressor
    from crawler.services.ingest_service import GraphitiIngestClient
    from crawler.storage.mongo_store import MongoStore
    from crawler.storage.repositories import ArticleRepository

    root = _crawler_root()
    sources = load_sources(root / "config" / "sources.yaml")
    config = load_pipeline_config(root / "config" / "pipeline.yaml")
    store = MongoStore()
    repository = ArticleRepository(store)
    context = PipelineContext(
        config=config,
        sources=sources,
        repository=repository,
        compressor=LLMCompressor(),
        ingest_client=GraphitiIngestClient(),
    )
    orchestrator = CrawlerOrchestrator(context)

    old_gray_mode = context.config.gray_mode
    try:
        if request.ingest and request.force_ingest:
            context.config.gray_mode = False
        return orchestrator.run_once(
            since_hours=request.since_hours,
            source_filter=request.source,
            max_items_per_source=request.max_items_per_source,
            process_limit=request.process_limit,
            enable_ingest=request.ingest,
        )
    finally:
        context.config.gray_mode = old_gray_mode
        store.close()


def _run_crawler_retry_ingest_failed_sync(
    *,
    process_limit: int,
    force_ingest: bool,
) -> dict:
    from crawler.connectors.source_registry import load_pipeline_config, load_sources
    from crawler.pipeline.context import PipelineContext
    from crawler.pipeline.orchestrator import CrawlerOrchestrator
    from crawler.services.compression_service import LLMCompressor
    from crawler.services.ingest_service import GraphitiIngestClient
    from crawler.storage.mongo_store import MongoStore
    from crawler.storage.repositories import ArticleRepository

    root = _crawler_root()
    sources = load_sources(root / "config" / "sources.yaml")
    config = load_pipeline_config(root / "config" / "pipeline.yaml")
    store = MongoStore()
    repository = ArticleRepository(store)
    context = PipelineContext(
        config=config,
        sources=sources,
        repository=repository,
        compressor=LLMCompressor(),
        ingest_client=GraphitiIngestClient(),
    )
    orchestrator = CrawlerOrchestrator(context)

    old_gray_mode = context.config.gray_mode
    try:
        if force_ingest:
            context.config.gray_mode = False
        return orchestrator.run_retry(
            retry_status="INGEST_FAILED",
            process_limit=process_limit,
            enable_ingest=True,
        )
    finally:
        context.config.gray_mode = old_gray_mode
        store.close()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _new_stage_state() -> dict[str, Any]:
    return {
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "details": {},
        "error": None,
    }


def _new_full_run_state(run_id: str, request: CrawlerOctopusFullRunRequest) -> dict[str, Any]:
    now = _now_utc()
    return {
        "run_id": run_id,
        "status": "running",
        "source": "octopus_news",
        "started_at": _iso_utc(now),
        "finished_at": None,
        "duration_ms": None,
        "updated_at": _iso_utc(now),
        "request": request.model_dump(),
        "result": None,
        "error": None,
        "stages": {
            "fetch": _new_stage_state(),
            "compress": _new_stage_state(),
            "ingest": _new_stage_state(),
            "calculation": _new_stage_state(),
            "storyline": _new_stage_state(),
        },
    }


async def _save_full_run_state(state: dict[str, Any]) -> None:
    run_id = str(state.get("run_id") or "").strip()
    if not run_id:
        return
    async with _OCTOPUS_FULL_RUN_STATE_LOCK:
        state["updated_at"] = _iso_utc(_now_utc())
        _OCTOPUS_FULL_RUNS[run_id] = copy.deepcopy(state)
        if len(_OCTOPUS_FULL_RUNS) > _OCTOPUS_FULL_RUN_HISTORY_LIMIT:
            ordered = sorted(
                _OCTOPUS_FULL_RUNS.items(),
                key=lambda item: str((item[1] or {}).get("started_at") or ""),
            )
            remove_count = max(0, len(_OCTOPUS_FULL_RUNS) - _OCTOPUS_FULL_RUN_HISTORY_LIMIT)
            for old_run_id, _ in ordered[:remove_count]:
                _OCTOPUS_FULL_RUNS.pop(old_run_id, None)


async def _load_full_run_state(run_id: str) -> dict[str, Any] | None:
    async with _OCTOPUS_FULL_RUN_STATE_LOCK:
        state = _OCTOPUS_FULL_RUNS.get(run_id)
        if state is None:
            return None
        return copy.deepcopy(state)


def _mark_stage_running(state: dict[str, Any], stage_name: str) -> None:
    stage = (state.get("stages") or {}).get(stage_name)
    if not isinstance(stage, dict):
        return
    now = _iso_utc(_now_utc())
    stage["status"] = "running"
    stage["started_at"] = stage.get("started_at") or now
    stage["finished_at"] = None
    stage["error"] = None


def _mark_stage_done(
    state: dict[str, Any],
    stage_name: str,
    *,
    status: str,
    details: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    stage = (state.get("stages") or {}).get(stage_name)
    if not isinstance(stage, dict):
        return
    now = _iso_utc(_now_utc())
    stage["status"] = status
    stage["started_at"] = stage.get("started_at") or now
    stage["finished_at"] = now
    stage["details"] = details or {}
    stage["error"] = error


def _parse_publish_time(value: Optional[str]) -> Optional[datetime]:
    """Parse user-provided publish time to timezone-aware UTC datetime."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None

    # ISO-8601 support (including trailing Z)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        parsed = None

    # Common date-time formats
    if parsed is None:
        fmts = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]
        for fmt in fmts:
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        raise ValueError(
            "Invalid publish_time format. Use ISO-8601 or 'YYYY-MM-DD HH:MM:SS'."
        )

    # Default naive datetime to UTC+8 for CN data, then normalize to UTC
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=8))).astimezone(timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        parsed = float(value)
        if math.isfinite(parsed):
            return parsed
        return None
    except (TypeError, ValueError):
        return None


def _normalize_labels(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value is None:
        return []
    return [str(value)]


def _parse_datetime_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    raw = str(value).strip()
    if not raw:
        return None

    for candidate in (raw.replace("Z", "+00:00"), raw):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _compute_decayed_momentum(momentum_score: float, momentum_updated_at: Any, gravity: float) -> float:
    updated_at = _parse_datetime_utc(momentum_updated_at)
    age_hours = 0.0
    if updated_at is not None:
        age_hours = (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600.0
        if age_hours < 0:
            age_hours = 0.0
    return momentum_score / ((age_hours + 2.0) ** gravity)


def _clip_text(value: Any, max_len: int) -> str:
    raw = str(value or "").strip()
    if len(raw) <= max_len:
        return raw
    return raw[:max_len].rstrip() + "..."


def _extract_entity_uuids_from_embedded_edges(entity_edges: Any) -> List[str]:
    if not isinstance(entity_edges, list):
        return []

    candidate_keys = (
        "target_node_uuid",
        "target_uuid",
        "entity_uuid",
        "node_uuid",
        "uuid",
    )
    result: List[str] = []
    seen: set[str] = set()

    for edge in entity_edges:
        candidate = None
        if isinstance(edge, dict):
            for key in candidate_keys:
                value = edge.get(key)
                if isinstance(value, str) and value.strip():
                    candidate = value.strip()
                    break
        elif isinstance(edge, str) and edge.strip():
            candidate = edge.strip()

        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result


def _fetch_nodes_by_uuids_from_es(node_uuids: List[str]) -> List[dict]:
    if not node_uuids:
        return []

    es_client = es_service.get_client()
    if not es_client:
        return []

    query_body = {
        "query": {
            "bool": {
                "filter": [
                    {"terms": {"uuid": node_uuids}},
                ]
            }
        },
        "_source": [
            "uuid",
            "name",
            "labels",
            "summary",
            "description",
            "momentum_score",
            "momentum_updated_at",
            "pageRank",
            "communityId",
        ],
        "size": min(len(node_uuids), 1000),
    }
    response = es_client.search(index=GRAPH_NODES_INDEX, body=query_body)
    return [hit.get("_source", {}) for hit in response.get("hits", {}).get("hits", [])]


def _query_episode_entities_from_es(episode_uuid: str, limit: int) -> Optional[List[dict]]:
    es_client = es_service.get_client()
    if not es_client:
        return None

    try:
        search_size = min(max(limit * 10, 200), 2000)
        edge_fields = ["source_node_uuid", "target_node_uuid", "relationship_type", "name"]
        edge_sources: List[dict] = []

        forward_body = {
            "query": {
                "bool": {
                    "filter": [{"term": {"source_node_uuid": episode_uuid}}],
                }
            },
            "_source": edge_fields,
            "size": search_size,
        }
        forward_resp = es_client.search(index=GRAPH_EDGES_INDEX, body=forward_body)
        edge_sources.extend(
            [hit.get("_source", {}) for hit in forward_resp.get("hits", {}).get("hits", [])]
        )

        reverse_body = {
            "query": {
                "bool": {
                    "filter": [{"term": {"target_node_uuid": episode_uuid}}],
                }
            },
            "_source": edge_fields,
            "size": search_size,
        }
        reverse_resp = es_client.search(index=GRAPH_EDGES_INDEX, body=reverse_body)
        edge_sources.extend(
            [hit.get("_source", {}) for hit in reverse_resp.get("hits", {}).get("hits", [])]
        )

        entity_uuids: List[str] = []
        seen: set[str] = set()
        for edge in edge_sources:
            rel_type = str(edge.get("relationship_type") or edge.get("name") or "").upper()
            if rel_type and rel_type not in {"MENTIONS", "RELATES", "RELATES_TO", "HAS_ENTITY", "ABOUT"}:
                continue

            source_uuid = edge.get("source_node_uuid")
            target_uuid = edge.get("target_node_uuid")
            candidates = [target_uuid, source_uuid]
            for candidate in candidates:
                if not isinstance(candidate, str):
                    continue
                normalized = candidate.strip()
                if not normalized or normalized == episode_uuid or normalized in seen:
                    continue
                seen.add(normalized)
                entity_uuids.append(normalized)

        if not entity_uuids:
            episode_query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"uuid": episode_uuid}},
                            {"term": {"labels": "Episodic"}},
                        ]
                    }
                },
                "_source": ["entity_edges"],
                "size": 1,
            }
            episode_resp = es_client.search(index=GRAPH_NODES_INDEX, body=episode_query)
            hits = episode_resp.get("hits", {}).get("hits", [])
            if hits:
                embedded = hits[0].get("_source", {}).get("entity_edges")
                entity_uuids.extend(_extract_entity_uuids_from_embedded_edges(embedded))

        if not entity_uuids:
            return []

        nodes = _fetch_nodes_by_uuids_from_es(entity_uuids)
        results: List[dict] = []
        for src in nodes:
            labels = _normalize_labels(src.get("labels"))
            if "Episodic" in labels:
                continue
            item = {
                "uuid": src.get("uuid"),
                "name": src.get("name"),
                "labels": labels,
                "summary": src.get("summary"),
                "description": src.get("description"),
                "momentum_score": _to_float(src.get("momentum_score")),
                "momentum_updated_at": src.get("momentum_updated_at"),
                "pageRank": _to_float(src.get("pageRank")),
                "communityId": src.get("communityId"),
            }
            results.append(item)

        results.sort(key=lambda x: ((x.get("momentum_score") or 0.0), x.get("name") or ""), reverse=True)
        return results[:limit]
    except Exception as e:
        logging.error("Error querying Elasticsearch for episode entities: %s", e, exc_info=True)
        return None


def _query_hot_entities_from_es(limit: int, gravity: float) -> Optional[List[dict]]:
    es_client = es_service.get_client()
    if not es_client:
        return None

    try:
        query_body = {
            "query": {
                "bool": {
                    "filter": [
                        {"exists": {"field": "momentum_score"}},
                    ]
                }
            },
            "_source": ["uuid", "name", "labels", "momentum_score", "momentum_updated_at"],
            "sort": [{"momentum_score": {"order": "desc"}}],
            "size": min(max(limit * 10, 200), 5000),
        }
        response = es_client.search(index=GRAPH_NODES_INDEX, body=query_body)

        results: List[dict] = []
        for hit in response.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            labels = _normalize_labels(src.get("labels"))
            if "Episodic" in labels:
                continue
            momentum_score = _to_float(src.get("momentum_score"))
            if momentum_score is None:
                continue

            decayed_momentum = _compute_decayed_momentum(
                momentum_score=momentum_score,
                momentum_updated_at=src.get("momentum_updated_at"),
                gravity=gravity,
            )
            results.append(
                {
                    "uuid": src.get("uuid"),
                    "name": src.get("name"),
                    "labels": labels,
                    "decayed_momentum": decayed_momentum,
                    "original_momentum": momentum_score,
                }
            )

        results.sort(key=lambda x: x["decayed_momentum"], reverse=True)
        return results[:limit]
    except Exception as e:
        logging.error("Error querying Elasticsearch for hot entities: %s", e, exc_info=True)
        return None


def _build_episode_storyline_from_es(episode_uuid: str) -> Optional[dict]:
    es_client = es_service.get_client()
    if not es_client:
        return None

    try:
        episode_query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"uuid": episode_uuid}},
                        {"term": {"labels": "Episodic"}},
                    ]
                }
            },
            "size": 1,
        }
        response = es_client.search(index=GRAPH_NODES_INDEX, body=episode_query)
        hits = response.get("hits", {}).get("hits", [])
        if not hits:
            return {
                "status": "not_found",
                "message": "No episodic document found in Elasticsearch for this episode.",
                "episode_uuid": episode_uuid,
            }

        episode = hits[0].get("_source", {})
        episode_title = (
            episode.get("title")
            or episode.get("name")
            or _clip_text(episode.get("content") or "未命名资讯", 36)
        )
        publish_at = (
            episode.get("publish_time")
            or episode.get("created_at")
            or episode.get("valid_at")
        )
        source = episode.get("news_source") or episode.get("source") or "未知来源"
        hotness = _to_float(episode.get("news_hotness_score"))

        seed_entities = _query_episode_entities_from_es(episode_uuid, limit=12) or []
        key_entities = [
            {
                "uuid": item.get("uuid"),
                "name": item.get("name"),
                "labels": item.get("labels") or [],
            }
            for item in seed_entities[:8]
        ]
        key_names = [item.get("name") for item in key_entities if item.get("name")]

        return {
            "status": "success",
            "source": "elasticsearch_fallback",
            "episode_uuid": episode_uuid,
            "title": " / ".join(key_names[:2]) if key_names else f"资讯脉络：{episode_title}",
            "summary": (
                f"该脉络由 ES 回退生成，当前包含 1 条资讯。{_clip_text(episode.get('content') or '', 90)}"
            ),
            "thread_hotness": hotness,
            "episode_count": 1,
            "first_seen_at": publish_at,
            "last_seen_at": publish_at,
            "key_entities": key_entities,
            "timeline": [
                {
                    "uuid": episode_uuid,
                    "title": episode_title,
                    "content": episode.get("content"),
                    "publish_at": publish_at,
                    "source": source,
                    "news_hotness_score": hotness,
                    "rank": 1,
                }
            ],
        }
    except Exception as e:
        logging.error("Error building ES fallback storyline: %s", e, exc_info=True)
        return None

# --- API Endpoints ---

@router.post("/initialize-database", status_code=200)
async def initialize_database():
    """
    Endpoint to initialize the database indices and constraints.
    This is a one-time setup operation.
    """
    try:
        result = await graphiti_service.initialize_database()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-text", status_code=201)
async def add_text(request: AddTextRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to add a piece of unstructured text to the knowledge graph.
    Graphiti will process it to extract entities and relationships.
    Automatically triggers the full calculation pipeline in sequence.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text content cannot be empty.")
    try:
        title = request.title.strip() if request.title and request.title.strip() else None
        fallback_name = request.name.strip() if request.name and request.name.strip() else None
        episode_name = title or fallback_name or _derive_episode_name(request.text)

        publish_time = _parse_publish_time(request.publish_time)
        group_id = (request.group_id or request.fusion_batch_id or "").strip() or None
        fusion_batch_id = (request.fusion_batch_id or group_id or "").strip() or None
        episode_metadata = {
            "title": title or episode_name,
            "publish_time": publish_time,
            "news_source": request.source.strip() if request.source and request.source.strip() else None,
            "news_url": request.url.strip() if request.url and request.url.strip() else None,
            "group_id": group_id,
            "fusion_batch_id": fusion_batch_id,
            "raw_text": request.raw_text.strip() if request.raw_text and request.raw_text.strip() else None,
            "structured_facts_json": (
                json.dumps(request.structured_facts, ensure_ascii=False)
                if request.structured_facts is not None
                else None
            ),
        }

        results, deduplicated = await graphiti_service.add_text_episode(
            request.text,
            name=episode_name,
            reference_time=publish_time,
            episode_metadata=episode_metadata,
            group_id=group_id,
        )

        if deduplicated:
            return {
                "status": "success",
                "deduplicated": True,
                "episode_uuid": results.episode.uuid,
                "episode_name": episode_name,
                "reference_time": results.episode.valid_at.isoformat() if results.episode.valid_at else None,
                "ingested_at": results.episode.created_at.isoformat() if results.episode.created_at else None,
                "queued_entity_count": 0,
                "message": "Episode already exists. Reused existing node by idempotent dedup check.",
            }

        # Trigger the full post-ingest calculation pipeline serially in background.
        entity_uuids = [node.uuid for node in results.nodes if getattr(node, "uuid", None)]
        background_tasks.add_task(
            calculation_service.calculate_all_after_ingest,
            entity_uuids,
            results.episode.uuid,
        )

        return {
            "status": "success",
            "deduplicated": False,
            "episode_uuid": results.episode.uuid,
            "episode_name": episode_name,
            "reference_time": results.episode.valid_at.isoformat() if results.episode.valid_at else None,
            "ingested_at": results.episode.created_at.isoformat() if results.episode.created_at else None,
            "queued_entity_count": len(entity_uuids),
            "message": (
                "Episode added for processing. Full calculation pipeline "
                "(momentum -> pagerank -> communities -> news hotness) queued."
            ),
        }
    except Exception as e:
        logging.exception("Error processing /add-text request:")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anchors/sync", status_code=200)
async def sync_common_sense_anchors(request: SyncAnchorsRequest):
    """Sync common-sense anchor nodes into the Graphiti news graph."""

    try:
        result = await graphiti_service.sync_common_sense_anchors(request.anchors)
        return {"status": "success", "result": result}
    except Exception as e:
        logging.exception("Error syncing common-sense anchors:")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anchors/link-entities", status_code=200)
async def link_news_entities_to_anchors(request: LinkEntitiesRequest):
    """Write entity-to-anchor link decisions into the Graphiti news graph."""

    try:
        result = await graphiti_service.link_news_entities_to_anchors(request.decisions)
        return {"status": "success", "result": result}
    except Exception as e:
        logging.exception("Error linking news entities to anchors:")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anchors/link-stats", status_code=200)
async def anchor_link_stats(group_id: str = Query(...)):
    """Return group-scoped anchor link statistics."""

    try:
        stats = await graphiti_service.get_anchor_link_stats(group_id)
        return {"status": "success", "stats": stats}
    except Exception as e:
        logging.exception("Error loading anchor link stats:")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crawler/sources", status_code=200)
async def crawler_sources():
    """
    Returns configured crawler sources for frontend selection.
    """
    try:
        return {"status": "success", "sources": _list_crawler_sources()}
    except Exception as e:
        logging.exception("Error loading crawler sources:")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawler/run-once", status_code=200)
async def crawler_run_once(request: CrawlerRunRequest):
    """
    Trigger one crawler run (fetch -> normalize -> relevance -> dedup -> compress -> ingest).
    """
    if request.max_items_per_source < 1 or request.max_items_per_source > MAX_ITEMS_PER_SOURCE_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"max_items_per_source must be in [1, {MAX_ITEMS_PER_SOURCE_LIMIT}].",
        )
    if request.since_hours < 1 or request.since_hours > 24 * 30:
        raise HTTPException(status_code=400, detail="since_hours must be in [1, 720].")
    if request.process_limit < 1 or request.process_limit > 2000:
        raise HTTPException(status_code=400, detail="process_limit must be in [1, 2000].")

    try:
        result = await asyncio.to_thread(_run_crawler_once_sync, request)
        return {"status": "success", "result": result}
    except Exception as e:
        logging.exception("Error running crawler run-once:")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawler/run-octopus-full", status_code=200)
async def crawler_run_octopus_full(request: CrawlerOctopusFullRunRequest):
    """
    Trigger one full octopus flow:
    octopus fetch -> compress/ingest -> background calculations -> storyline rebuild.
    """
    if request.max_items_per_source < 1 or request.max_items_per_source > MAX_ITEMS_PER_SOURCE_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"max_items_per_source must be in [1, {MAX_ITEMS_PER_SOURCE_LIMIT}].",
        )
    if request.since_hours < 1 or request.since_hours > 24 * 30:
        raise HTTPException(status_code=400, detail="since_hours must be in [1, 720].")
    if request.process_limit < 1 or request.process_limit > 2000:
        raise HTTPException(status_code=400, detail="process_limit must be in [1, 2000].")
    if request.ingest_retry_limit < 0 or request.ingest_retry_limit > 500:
        raise HTTPException(status_code=400, detail="ingest_retry_limit must be in [0, 500].")
    if request.storyline_since_days < 1 or request.storyline_since_days > 365:
        raise HTTPException(status_code=400, detail="storyline_since_days must be in [1, 365].")

    run_id = f"octopus_full_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    state = _new_full_run_state(run_id, request)
    await _save_full_run_state(state)
    asyncio.create_task(_execute_octopus_full_run(run_id, request))
    return {
        "status": "accepted",
        "run_id": run_id,
        "message": "Octopus full-run queued. Poll /api/crawler/full-run/{run_id} for progress.",
    }


@router.get("/crawler/full-run/{run_id}", status_code=200)
async def crawler_get_full_run(run_id: str):
    state = await _load_full_run_state(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run_id not found.")
    return {"status": "success", "result": state}


async def _execute_octopus_full_run(run_id: str, request: CrawlerOctopusFullRunRequest) -> None:
    state = await _load_full_run_state(run_id)
    if state is None:
        return

    if _OCTOPUS_FULL_RUN_EXECUTION_LOCK.locked():
        state["status"] = "failed"
        state["error"] = "Another octopus full-run is in progress."
        state["finished_at"] = _iso_utc(_now_utc())
        state["duration_ms"] = 0
        await _save_full_run_state(state)
        return

    async with _OCTOPUS_FULL_RUN_EXECUTION_LOCK:
        started_at = _now_utc()
        try:
            _mark_stage_running(state, "fetch")
            _mark_stage_running(state, "compress")
            _mark_stage_running(state, "ingest")
            await _save_full_run_state(state)

            run_request = CrawlerRunRequest(
                max_items_per_source=request.max_items_per_source,
                since_hours=request.since_hours,
                process_limit=request.process_limit,
                source="octopus_news",
                ingest=True,
                force_ingest=request.force_ingest,
            )
            crawler_result = await asyncio.to_thread(_run_crawler_once_sync, run_request)
            retry_limit = max(0, min(request.ingest_retry_limit, request.process_limit))
            if retry_limit > 0:
                retry_result = await asyncio.to_thread(
                    _run_crawler_retry_ingest_failed_sync,
                    process_limit=retry_limit,
                    force_ingest=request.force_ingest,
                )
            else:
                retry_result = {
                    "mode": "retry",
                    "ingest_retry": {
                        "ingested": 0,
                        "failed": 0,
                        "total": 0,
                        "skipped": True,
                        "reason": "ingest_retry_limit_zero",
                    },
                }

            fetch_details = crawler_result.get("fetch", {}) if isinstance(crawler_result, dict) else {}
            compress_details = crawler_result.get("compress", {}) if isinstance(crawler_result, dict) else {}
            ingest_details = crawler_result.get("ingest", {}) if isinstance(crawler_result, dict) else {}
            ingest_retry_details = (
                retry_result.get("ingest_retry", {}) if isinstance(retry_result, dict) else {}
            )
            merged_ingest_details = {
                "primary": ingest_details,
                "retry_ingest_failed": ingest_retry_details,
                "retry_limit": retry_limit,
                "ingested": int((ingest_details or {}).get("ingested", 0))
                + int((ingest_retry_details or {}).get("ingested", 0)),
                "failed": int((ingest_details or {}).get("failed", 0))
                + int((ingest_retry_details or {}).get("failed", 0)),
                "total": int((ingest_details or {}).get("total", 0))
                + int((ingest_retry_details or {}).get("total", 0)),
            }
            _mark_stage_done(state, "fetch", status="success", details=fetch_details)
            _mark_stage_done(state, "compress", status="success", details=compress_details)
            ingest_failed = int((merged_ingest_details or {}).get("failed", 0))
            ingest_ingested = int((merged_ingest_details or {}).get("ingested", 0))
            if ingest_failed > 0 and ingest_ingested == 0:
                ingest_stage_status = "failed"
            elif ingest_failed > 0:
                ingest_stage_status = "partial_success"
            else:
                ingest_stage_status = "success"
            _mark_stage_done(
                state,
                "ingest",
                status=ingest_stage_status,
                details=merged_ingest_details,
            )

            # Calculations are queued by /api/add-text background task.
            _mark_stage_done(
                state,
                "calculation",
                status="queued",
                details={"mode": "triggered_by_add_text_background_tasks"},
            )
            await _save_full_run_state(state)

            storyline_result: dict[str, Any] = {"skipped": True, "reason": "rebuild_not_requested"}
            if request.rebuild_storylines:
                _mark_stage_running(state, "storyline")
                await _save_full_run_state(state)
                storyline_result = await storyline_service.rebuild_storylines(request.storyline_since_days)
                _mark_stage_done(state, "storyline", status="success", details=storyline_result)
            else:
                _mark_stage_done(state, "storyline", status="skipped", details=storyline_result)

            finished_at = _now_utc()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            state["status"] = "success"
            state["finished_at"] = _iso_utc(finished_at)
            state["duration_ms"] = duration_ms
            state["result"] = {
                "crawler": crawler_result,
                "ingest_retry": retry_result,
                "storyline": storyline_result,
            }
            await _save_full_run_state(state)
        except Exception as exc:
            finished_at = _now_utc()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            state["status"] = "failed"
            state["finished_at"] = _iso_utc(finished_at)
            state["duration_ms"] = duration_ms
            state["error"] = str(exc)
            for stage_name, stage in (state.get("stages") or {}).items():
                if isinstance(stage, dict) and stage.get("status") == "running":
                    _mark_stage_done(state, stage_name, status="failed", error=str(exc))
            await _save_full_run_state(state)
            logging.exception("Error running crawler octopus full-run:")

@router.post("/search")
async def search(request: SearchRequest):
    """
    Endpoint to search the knowledge graph using a natural language query.
    Optionally, a center_node_uuid can be provided for contextual search.
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        results = await graphiti_service.search_graph(request.query, request.center_node_uuid)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/lookup")
async def lookup_entities(
    name: str = Query(..., min_length=1, max_length=120, description="Entity name keyword."),
    label: Optional[str] = Query(
        None,
        description="Optional type filter: company/enterprise, product/product_model, technology.",
    ),
    limit: int = Query(10, gt=0, le=100),
):
    """
    Lookup candidate entities by name keyword with optional type filtering.
    """
    resolved_label = _resolve_entity_label(label)
    if label is not None and resolved_label is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid label. Use company/enterprise, product/product_model, or technology.",
        )

    try:
        driver = graphiti_service.graphiti.driver
        query = """
        MATCH (e:Entity)
        WHERE toLower(coalesce(e.name, '')) CONTAINS toLower($name)
          AND ($label IS NULL OR $label IN labels(e))
        RETURN
            e.uuid AS uuid,
            e.name AS name,
            labels(e) AS labels,
            coalesce(e.summary, '') AS summary,
            coalesce(e.description, '') AS description,
            coalesce(e.momentum_score, 0.0) AS momentum_score,
            coalesce(e.pageRank, 0.0) AS pageRank,
            coalesce(e.communityId, -1) AS communityId
        ORDER BY momentum_score DESC, pageRank DESC, name ASC
        LIMIT $limit
        """
        records, _, _ = await driver.execute_query(
            query,
            name=name.strip(),
            label=resolved_label,
            limit=limit,
        )

        entities: list[dict] = []
        for record in records:
            entities.append(
                _serialize_neo4j_properties(
                    {
                        "uuid": record.get("uuid"),
                        "name": record.get("name"),
                        "labels": record.get("labels") or [],
                        "summary": record.get("summary"),
                        "description": record.get("description"),
                        "momentum_score": record.get("momentum_score"),
                        "pageRank": record.get("pageRank"),
                        "communityId": record.get("communityId"),
                    }
                )
            )

        return {
            "status": "success",
            "name": name.strip(),
            "label": resolved_label,
            "count": len(entities),
            "entities": entities,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Knowledge Calculation Endpoints ---

@router.post("/calculate-momentum/{entity_uuid}", status_code=202)
async def trigger_momentum_calculation(entity_uuid: str, background_tasks: BackgroundTasks):
    """
    Asynchronously triggers the momentum calculation for a specific entity.
    The API returns immediately, and the calculation is performed in the background.
    """
    if not UUID_REGEX.match(entity_uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format.")

    background_tasks.add_task(calculation_service.calculate_and_store_momentum, entity_uuid)
    return {
        "status": "accepted",
        "message": f"Momentum calculation for entity {entity_uuid} has been queued."
    }

@router.post("/calculate/all-pagerank", status_code=202)
async def trigger_pagerank_calculation(background_tasks: BackgroundTasks):
    """
    Asynchronously triggers the PageRank calculation for all entities in the graph.
    The API returns immediately, and the calculation is performed in the background.
    """
    background_tasks.add_task(calculation_service.calculate_and_store_pagerank)
    return {
        "status": "accepted",
        "message": "PageRank calculation for the entire graph has been queued."
    }

@router.post("/calculate/all-communities", status_code=202)
async def trigger_community_calculation(background_tasks: BackgroundTasks):
    """
    Asynchronously triggers community detection for all entities in the graph.
    The API returns immediately, and the calculation is performed in the background.
    """
    background_tasks.add_task(calculation_service.calculate_and_store_communities)
    return {
        "status": "accepted",
        "message": "Community detection for the entire graph has been queued."
    }

@router.post("/calculate/all-news-hotness", status_code=202)
async def trigger_news_hotness_calculation(
    background_tasks: BackgroundTasks,
    episode_uuid: Optional[str] = Query(None, description="Optional specific episodic uuid to recalculate."),
    since_days: Optional[int] = Query(
        None,
        gt=0,
        le=3650,
        description="Optional rolling window in days. Recalculates news within the window.",
    ),
):
    """
    Asynchronously triggers the hotness score calculation for all news ('Episodic') nodes.
    The API returns immediately, and the calculation is performed in the background.
    """
    if episode_uuid and not UUID_REGEX.match(episode_uuid):
        raise HTTPException(status_code=400, detail="Invalid episode UUID format.")

    background_tasks.add_task(
        calculation_service.calculate_and_store_news_hotness,
        episode_uuid,
        since_days,
    )

    scope_desc = "all episodic nodes"
    if episode_uuid:
        scope_desc = f"episode {episode_uuid}"
    elif since_days:
        scope_desc = f"episodes in last {since_days} day(s)"

    return {
        "status": "accepted",
        "message": f"News hotness calculation for {scope_desc} has been queued."
    }


@router.post("/calculate/entity-heat-rankings", status_code=200)
async def trigger_entity_heat_rankings(request: EntityHeatRankingRequest):
    """
    Generate entity heat ranking snapshots and return the generated ranking payload.
    """
    if request.limit_per_type < 1 or request.limit_per_type > 500:
        raise HTTPException(status_code=400, detail="limit_per_type must be between 1 and 500.")
    service = EntityHeatRankingService(graphiti_service.graphiti.driver)
    try:
        result = await service.generate_and_store_rankings(
            period_type=request.period_type,
            as_of=request.as_of,
            entity_type=request.entity_type,
            limit_per_type=request.limit_per_type,
        )
        return {"status": "success", "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error("Entity heat ranking calculation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/entity-heat-rankings", status_code=200)
async def get_entity_heat_rankings(
    period_type: str = Query("daily", description="daily or weekly"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD or ISO datetime"),
    entity_type: str = Query("Enterprise", description="Enterprise/Product/Person/Technology/Region"),
    limit: int = Query(50, gt=0, le=500),
):
    """
    Query precomputed entity heat ranking snapshots for frontend and downstream agents.
    """
    service = EntityHeatRankingService(graphiti_service.graphiti.driver)
    try:
        return await service.query_rankings(
            period_type=period_type,
            date=date,
            entity_type=entity_type,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error("Entity heat ranking query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/calculate/news-graph-projection", status_code=200)
async def materialize_news_graph_projection(request: NewsGraphProjectionRequest):
    """
    Materialize a browser-friendly projection inside the Graphiti news graph.
    """
    if request.limit < 1 or request.limit > 20000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 20000.")
    service = NewsGraphProjectionService(graphiti_service.graphiti.driver)
    try:
        result = await service.materialize_projection(
            group_id=request.group_id,
            limit=request.limit,
            clear_existing=request.clear_existing,
        )
        return {"status": "success", "result": result}
    except Exception as exc:
        logging.error("News graph projection materialization failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/news-graph-projection/stats", status_code=200)
async def get_news_graph_projection_stats(
    group_id: Optional[str] = Query(None, description="Optional Graphiti group_id scope."),
):
    """
    Return current news projection statistics.
    """
    service = NewsGraphProjectionService(graphiti_service.graphiti.driver)
    try:
        return {"status": "success", "stats": await service.projection_stats(group_id=group_id)}
    except Exception as exc:
        logging.error("News graph projection stats query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/calculate/rebuild-storylines", status_code=202)
async def trigger_storyline_rebuild(
    background_tasks: BackgroundTasks,
    since_days: int = Query(30, gt=0, le=365),
):
    """
    Manually trigger storyline rebuild in the given time window.
    """
    background_tasks.add_task(storyline_service.rebuild_storylines, since_days)
    return {
        "status": "accepted",
        "message": f"Storyline rebuild for the last {since_days} day(s) has been queued.",
    }


@router.get("/storylines", response_model=List[dict])
async def list_storylines(
    limit: int = Query(20, gt=0, le=100),
    min_episode_count: int = Query(2, gt=0, le=200),
    thread_type: Optional[str] = Query(
        None,
        pattern="^(company|product)$",
        description="Optional thread type filter: company or product.",
    ),
):
    """
    Returns storyline list ordered by storyline hotness.
    """
    try:
        storylines = await storyline_service.list_storylines(
            limit=limit,
            min_episode_count=min_episode_count,
            thread_type=thread_type,
        )
        return [_serialize_neo4j_properties(item) for item in storylines]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storylines/by-anchor")
async def list_storylines_by_anchor(
    anchor_entity_uuid: str = Query(..., description="Anchor entity UUID."),
    limit: int = Query(20, gt=0, le=100),
    min_episode_count: int = Query(1, gt=0, le=200),
    thread_type: Optional[str] = Query(
        None,
        pattern="^(company|product)$",
        description="Optional thread type filter: company or product.",
    ),
):
    """
    Returns storyline list for one anchor entity.
    """
    if not UUID_REGEX.match(anchor_entity_uuid):
        raise HTTPException(status_code=400, detail="Invalid anchor_entity_uuid format.")

    try:
        storylines = await storyline_service.list_storylines_by_anchor(
            anchor_entity_uuid=anchor_entity_uuid,
            limit=limit,
            min_episode_count=min_episode_count,
            thread_type=thread_type,
        )
        return {
            "status": "success",
            "anchor_entity_uuid": anchor_entity_uuid,
            "count": len(storylines),
            "storylines": [_serialize_neo4j_properties(item) for item in storylines],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_uuid}")
async def get_entity_details(entity_uuid: str):
    """
    Retrieves the detailed information for a specific entity, including all its properties.
    This can be used to verify the results of background tasks like momentum calculation.
    """
    if not UUID_REGEX.match(entity_uuid):
        raise HTTPException(status_code=400, detail=f"Invalid UUID format.")

    try:
        driver = graphiti_service.graphiti.driver
        query = """
        MATCH (n {uuid: $entity_uuid})
        RETURN properties(n) AS details
        """
        records, _, _ = await driver.execute_query(query, entity_uuid=entity_uuid)

        if not records:
            raise HTTPException(status_code=404, detail="Entity not found.")

        details = dict(records[0]["details"])

        # Convert non-serializable types (like Arrow datetime) to strings for JSON response
        for key, value in details.items():
            if hasattr(value, 'isoformat'): # Handles datetime objects
                details[key] = value.isoformat()

        return details

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_uuid}")
async def get_episode_details(episode_uuid: str):
    """
    Retrieves detailed properties for a specific episodic node.
    """
    if not UUID_REGEX.match(episode_uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format.")

    try:
        driver = graphiti_service.graphiti.driver
        query = """
        MATCH (ep:Episodic {uuid: $episode_uuid})
        RETURN properties(ep) AS details
        """
        records, _, _ = await driver.execute_query(query, episode_uuid=episode_uuid)

        if not records:
            raise HTTPException(status_code=404, detail="Episode not found.")

        details = dict(records[0]["details"])
        return _serialize_neo4j_properties(details)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_uuid}/storyline")
async def get_episode_storyline(
    episode_uuid: str,
    limit: int = Query(30, gt=1, le=200),
    debug: bool = Query(False, description="Whether to include clustering explain fields."),
):
    """
    Returns the storyline that the target episode belongs to, including timeline.
    """
    if not UUID_REGEX.match(episode_uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format.")

    storyline_from_es = _build_episode_storyline_from_es(episode_uuid)
    if storyline_from_es:
        return storyline_from_es

    try:
        storyline = await storyline_service.get_storyline_for_episode(
            episode_uuid=episode_uuid,
            limit=limit,
            debug=debug,
        )
        if not storyline:
            return {
                "status": "not_found",
                "message": "No storyline found for this episode. Run /api/calculate/rebuild-storylines first.",
                "episode_uuid": episode_uuid,
            }
        serialized = _serialize_neo4j_properties(storyline)
        serialized["deprecated"] = True
        serialized["message"] = "Use /api/episode/{episode_uuid}/storylines for all memberships."
        return serialized
    except Exception as e:
        logging.error("Neo4j storyline query failed: %s", e, exc_info=True)
        return {
            "status": "not_found",
            "message": "Failed to load storyline from Neo4j and Elasticsearch fallback is unavailable.",
            "episode_uuid": episode_uuid,
        }


@router.get("/episode/{episode_uuid}/storylines")
async def get_episode_storylines(
    episode_uuid: str,
    limit: int = Query(30, gt=1, le=200),
    debug: bool = Query(False, description="Whether to include explain fields."),
):
    """
    Returns all storylines that the target episode belongs to.
    """
    if not UUID_REGEX.match(episode_uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format.")
    try:
        storylines = await storyline_service.get_storylines_for_episode(
            episode_uuid=episode_uuid,
            limit=limit,
            debug=debug,
        )
        if not storylines:
            return {
                "status": "not_found",
                "message": "No storylines found for this episode. Run /api/calculate/rebuild-storylines first.",
                "episode_uuid": episode_uuid,
                "count": 0,
                "storylines": [],
            }
        return {
            "status": "success",
            "episode_uuid": episode_uuid,
            "count": len(storylines),
            "storylines": [_serialize_neo4j_properties(item) for item in storylines],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_uuid}/entities", response_model=List[dict])
async def get_episode_entities(
    episode_uuid: str,
    limit: int = Query(30, gt=0, le=200),
):
    """
    Retrieves entities mentioned by a specific episodic node.
    This endpoint is designed for frontend expansion panels on hot-news cards.
    """
    if not UUID_REGEX.match(episode_uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format.")

    entities_from_es = _query_episode_entities_from_es(episode_uuid, limit=limit)
    if entities_from_es is not None:
        return [_serialize_neo4j_properties(item) for item in entities_from_es]

    try:
        driver = graphiti_service.graphiti.driver
        query = """
        MATCH (ep:Episodic {uuid: $episode_uuid})-[:MENTIONS]->(n:Entity)
        RETURN
            n.uuid AS uuid,
            n.name AS name,
            labels(n) AS labels,
            n.summary AS summary,
            n.description AS description,
            n.momentum_score AS momentum_score,
            n.momentum_updated_at AS momentum_updated_at,
            n.pageRank AS pageRank,
            n.communityId AS communityId
        ORDER BY coalesce(n.momentum_score, 0.0) DESC, n.name ASC
        LIMIT $limit
        """
        records, _, _ = await driver.execute_query(query, episode_uuid=episode_uuid, limit=limit)

        results = []
        for record in records:
            item = {
                "uuid": record["uuid"],
                "name": record["name"],
                "labels": record["labels"] if record["labels"] else [],
                "summary": record["summary"],
                "description": record["description"],
                "momentum_score": record["momentum_score"],
                "momentum_updated_at": record["momentum_updated_at"],
                "pageRank": record["pageRank"],
                "communityId": record["communityId"],
            }
            results.append(_serialize_neo4j_properties(item))

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-entities")
async def get_hot_entities(
    limit: int = 10,
    gravity: float = Query(
        1.8,
        gt=0,
        le=5,
        description="Gravity factor for time-decay. Higher values mean faster decay.",
    )
):
    """
    Retrieves a ranking of entities by a time-decayed momentum score.
    The score is calculated using a gravity formula, penalizing older scores.
    """
    es_results = _query_hot_entities_from_es(limit=limit, gravity=gravity)
    if es_results is not None:
        return es_results

    try:
        driver = graphiti_service.graphiti.driver
        query = """
        MATCH (n:Entity)
        WHERE n.momentum_score IS NOT NULL AND n.momentum_updated_at IS NOT NULL

        // 1. Calculate age of momentum score in hours
        WITH n, toFloat(datetime().epochSeconds - n.momentum_updated_at.epochSeconds) / 3600.0 AS age_in_hours_raw
        WITH n, CASE WHEN age_in_hours_raw < 0 THEN 0.0 ELSE age_in_hours_raw END AS age_in_hours

        // 2. Calculate the time-decayed momentum score
        WITH n, (n.momentum_score / (age_in_hours + 2)^$gravity) AS decayed_momentum

        // 3. Return the top N results, ordered by the new decayed score
        RETURN
            n.uuid AS uuid,
            n.name AS name,
            [label IN labels(n) WHERE label <> 'Entity'] AS labels,
            decayed_momentum,
            n.momentum_score AS original_momentum
        ORDER BY decayed_momentum DESC
        LIMIT $limit
        """
        records, _, _ = await driver.execute_query(query, limit=limit, gravity=gravity)

        results = []
        for record in records:
            results.append({
                "uuid": record["uuid"],
                "name": record["name"],
                "labels": record["labels"] if record["labels"] else [],
                "decayed_momentum": record["decayed_momentum"],
                "original_momentum": record["original_momentum"],
            })
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _query_hot_news_from_neo4j(limit: int) -> List[dict]:
    """Fallback query when ES is unavailable or not yet synchronized."""
    driver = graphiti_service.graphiti.driver
    query = """
    MATCH (ep:Episodic)
    WHERE ep.news_hotness_score IS NOT NULL
    RETURN properties(ep) AS news
    ORDER BY ep.news_hotness_score DESC
    LIMIT $limit
    """
    records, _, _ = await driver.execute_query(query, limit=limit)
    return [_serialize_neo4j_properties(dict(record["news"])) for record in records]


@router.get("/hot-news", response_model=List[dict])
async def get_hot_news(limit: int = Query(20, gt=0, le=100)):
    """
    Retrieves a ranked list of hot news ('Episodic' nodes) from Elasticsearch.
    The ranking is based on the pre-calculated 'news_hotness_score'.
    """
    query_body = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"labels": "Episodic"}},
                    {"exists": {"field": "news_hotness_score"}}
                ]
            }
        },
        "sort": [
            {"news_hotness_score": {"order": "desc"}}
        ],
        "size": limit
    }

    es_client = es_service.get_client()
    if es_client:
        try:
            response = es_client.search(
                index=GRAPH_NODES_INDEX,
                body=query_body
            )
            # Extract the source document from each hit
            results = [hit['_source'] for hit in response['hits']['hits']]
            if results:
                return results
            logging.warning("ES hot-news query returned no results. Falling back to Neo4j.")
        except Exception as e:
            logging.error(f"Error querying Elasticsearch for hot news: {e}", exc_info=True)
            logging.warning("Falling back to Neo4j for /hot-news.")
    else:
        logging.warning("Elasticsearch is not available. Falling back to Neo4j for /hot-news.")

    try:
        return await _query_hot_news_from_neo4j(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query hot news from both Elasticsearch and Neo4j: {e}")


@router.get("/wikidata/map")
async def wikidata_map_single(
    name: str = Query(..., min_length=1, max_length=200, description="Product/entity name to map."),
):
    """
    Real Wikidata mapping API (standalone, not wired into crawler flow yet).
    """
    try:
        return {
            "status": "success",
            "mapping": wikidata_mapping_service.map_product(name),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wikidata/map/batch")
async def wikidata_map_batch(request: WikidataMapRequest):
    """
    Batch Wikidata mapping + pairwise relation hints.
    """
    if not request.names:
        raise HTTPException(status_code=400, detail="names cannot be empty.")
    if len(request.names) > 200:
        raise HTTPException(status_code=400, detail="names size must be <= 200.")

    try:
        mapped = wikidata_mapping_service.map_products(request.names)
        return {
            "status": "success",
            **mapped,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
