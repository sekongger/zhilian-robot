from __future__ import annotations

from datetime import datetime
import asyncio

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/resource-hub", tags=["resource-hub"])


RESOURCE_META = {
    "news": {
        "label": "资讯",
        "doc_type": "news",
        "data_sources": [
            {"name": "RSS 订阅", "mode": "拉取", "frequency": "每 6 小时", "entry": "/api/v1/data/rss/update"},
            {"name": "新闻爬虫", "mode": "抓取", "frequency": "按任务触发 / 每日批量", "entry": "/api/v1/data/crawl"},
            {"name": "手工导入", "mode": "导入", "frequency": "按需", "entry": "/api/v1/data/process/*"},
        ],
        "tables": [
            {"name": "crawled_articles", "role": "爬取原文缓存", "primary_key": "_id", "key_fields": ["title", "content", "url", "source_news_id"]},
            {"name": "raw_documents", "role": "原始文档保真层", "primary_key": "doc_id", "key_fields": ["doc_hash", "source_url", "publish_time"]},
            {"name": "news_pipeline_source_news", "role": "资讯标准入口", "primary_key": "_id", "key_fields": ["doc_id", "process_status", "source_url"]},
            {"name": "kg_input_queue", "role": "知识计算输入队列", "primary_key": "queue_id", "key_fields": ["kg_name", "status", "doc_id"]},
            {"name": "inc_statement", "role": "结构化陈述", "primary_key": "statement_id", "key_fields": ["subject_id", "predicate_id", "doc_id"]},
        ],
        "task_names": ["crawl_all_news", "fetch_rss_updates", "crawl_single_keyword", "build_news_kg_queue"],
    },
    "report": {
        "label": "研报",
        "doc_type": "report",
        "data_sources": [
            {"name": "文件上传", "mode": "上传", "frequency": "按需", "entry": "/api/v1/ingestion/upload"},
            {"name": "批量导入", "mode": "导入", "frequency": "按需", "entry": "/api/v1/ingestion/upload/batch"},
            {"name": "对象存储", "mode": "存储", "frequency": "实时", "entry": "minio://minio_file_index"},
        ],
        "tables": [
            {"name": "raw_data", "role": "上传原始记录", "primary_key": "_id", "key_fields": ["source_name", "is_processed"]},
            {"name": "minio_file_index", "role": "原始文件索引", "primary_key": "_id", "key_fields": ["object_name", "bucket_name"]},
            {"name": "report_pipeline_reports", "role": "研报处理入口", "primary_key": "_id", "key_fields": ["title", "status"]},
            {"name": "inc_document", "role": "标准化文档", "primary_key": "doc_id", "key_fields": ["resource_type", "title_raw"]},
            {"name": "inc_context", "role": "上下文知识", "primary_key": "context_id", "key_fields": ["doc_id", "context_scenario"]},
        ],
        "task_names": ["upload_file", "upload_batch_files", "process_report", "batch_process_reports"],
    },
}


def _get_mongo_conn():
    from app.database.mongodb import mongodb_conn

    return mongodb_conn


def _stats_route(*, doc_type=None, knowledge_scope=None):
    from app.api.document_pipeline_routes import stats

    return asyncio.run(stats(doc_type=doc_type, knowledge_scope=knowledge_scope))


async def _document_records_loader(*, layer: str, limit: int, offset: int, doc_type: str | None):
    from app.api.document_pipeline_routes import records

    return await records(layer=layer, limit=limit, offset=offset, doc_type=doc_type)


def _safe_count(collection_name: str, query: dict | None = None) -> int:
    mongo = _get_mongo_conn()
    try:
        return mongo.get_collection(collection_name).count_documents(query or {})
    except Exception:
        return 0


def _safe_latest(collection_name: str, sort_field: str) -> str | None:
    mongo = _get_mongo_conn()
    try:
        rows = mongo.find_many(collection_name, query={}, limit=1, sort=[(sort_field, -1)])
    except Exception:
        rows = []
    if not rows:
        return None
    value = rows[0].get(sort_field)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else None


def _task_rows(task_names: list[str]) -> list[dict]:
    mongo = _get_mongo_conn()
    rows = []
    for task_name in task_names:
        latest = None
        try:
            items = mongo.find_many("task_history", query={"task": task_name}, limit=1, sort=[("completed_at", -1)])
            latest = items[0] if items else None
        except Exception:
            latest = None
        rows.append(
            {
                "name": task_name,
                "status": str((latest or {}).get("status") or "unknown"),
                "latest_run": (
                    latest.get("completed_at").isoformat()
                    if isinstance((latest or {}).get("completed_at"), datetime)
                    else str((latest or {}).get("completed_at") or "")
                ),
                "processed": int((latest or {}).get("articles_processed") or 0),
            }
        )
    return rows


def _resource_metrics(resource_key: str) -> dict:
    meta = RESOURCE_META[resource_key]
    stats = _stats_route(doc_type=meta["doc_type"], knowledge_scope=None)
    queue_query = {"kg_name": "news_kg"} if resource_key == "news" else {}
    queue_pending = _safe_count("kg_input_queue", {**queue_query, "status": "pending"}) if resource_key == "news" else 0
    queue_failed = _safe_count("kg_input_queue", {**queue_query, "status": "failed"}) if resource_key == "news" else 0
    return {
        "raw_documents": int(((stats.get("raw_layer") or {}).get("raw_documents") or 0)),
        "resource_documents": int(((stats.get("resource_layer") or {}).get("inc_document") or 0)),
        "entities": int(((stats.get("knowledge_layer") or {}).get("entities") or 0)),
        "statements": int(((stats.get("knowledge_layer") or {}).get("statements") or 0)),
        "pending_tasks": int(((stats.get("resource_layer") or {}).get("pending_records") or 0)),
        "queue_pending": queue_pending,
        "queue_failed": queue_failed,
    }


def _resource_quality(resource_key: str, metrics: dict) -> dict:
    if resource_key == "news":
        raw_documents = max(int(metrics.get("raw_documents") or 0), 1)
        queue_pending = int(metrics.get("queue_pending") or 0)
        return {
            "duplicate_rate": round(max(raw_documents - int(metrics.get("resource_documents") or 0), 0) / raw_documents, 4),
            "build_backlog_rate": round(queue_pending / raw_documents, 4),
            "failed_queue_count": int(metrics.get("queue_failed") or 0),
        }
    resource_documents = max(int(metrics.get("resource_documents") or 0), 1)
    return {
        "parse_completion_rate": round(int(metrics.get("entities") or 0) / resource_documents, 4),
        "statement_coverage_rate": round(int(metrics.get("statements") or 0) / resource_documents, 4),
        "pending_task_count": int(metrics.get("pending_tasks") or 0),
    }


def _build_resource_hub_summary() -> dict:
    news_metrics = _resource_metrics("news")
    report_metrics = _resource_metrics("report")
    return {
        "resources": len(RESOURCE_META),
        "raw_documents": news_metrics["raw_documents"] + report_metrics["raw_documents"],
        "resource_documents": news_metrics["resource_documents"] + report_metrics["resource_documents"],
        "entities": news_metrics["entities"] + report_metrics["entities"],
        "statements": news_metrics["statements"] + report_metrics["statements"],
        "queue_pending": news_metrics["queue_pending"],
        "pending_tasks": news_metrics["pending_tasks"] + report_metrics["pending_tasks"],
    }


def _build_resource_cards() -> list[dict]:
    items = []
    for resource_key, meta in RESOURCE_META.items():
        metrics = _resource_metrics(resource_key)
        status = "connected" if resource_key == "news" else "pending"
        items.append(
            {
                "resource_key": resource_key,
                "label": meta["label"],
                "metrics": metrics,
                "status": status,
                "updated_at": _safe_latest("kg_build_runs" if resource_key == "news" else "report_pipeline_reports", "updated_at") or _safe_latest("task_history", "completed_at"),
                "quality": _resource_quality(resource_key, metrics),
            }
        )
    return items


def _build_resource_detail(resource_key: str) -> dict:
    if resource_key not in RESOURCE_META:
        raise HTTPException(status_code=404, detail=f"资源 {resource_key} 不存在")
    meta = RESOURCE_META[resource_key]
    metrics = _resource_metrics(resource_key)
    return {
        "resource_key": resource_key,
        "label": meta["label"],
        "status": "connected" if resource_key == "news" else "pending",
        "metrics": metrics,
        "tabs": {
            "数据源": meta["data_sources"],
            "数据库表设计": meta["tables"],
            "数据接入和治理任务": _task_rows(meta["task_names"]),
            "数据质量": _resource_quality(resource_key, metrics),
        },
    }


def _metric_layer_config(resource_key: str, metric_key: str) -> dict:
    if resource_key == "report":
        raise HTTPException(status_code=409, detail="研报数据源暂未接入，暂不支持明细下钻")

    metric_map = {
        "raw_documents": {"layer": "raw.raw_documents", "doc_type": "news", "title": "资讯原始文档明细"},
        "resource_documents": {"layer": "resource.inc_document", "doc_type": "news", "title": "资讯标准文档明细"},
        "entities": {"layer": "knowledge.entities", "doc_type": "news", "title": "资讯实体明细"},
        "statements": {"layer": "knowledge.statements", "doc_type": "news", "title": "资讯陈述明细"},
    }
    config = metric_map.get(metric_key)
    if not config:
        raise HTTPException(status_code=404, detail=f"指标 {metric_key} 不存在")
    return config


@router.get("/summary")
def get_resource_hub_summary():
    return _build_resource_hub_summary()


@router.get("/resources")
def list_resource_cards():
    items = _build_resource_cards()
    return {"items": items, "total": len(items)}


@router.get("/resources/{resource_key}")
def get_resource_detail(resource_key: str):
    return _build_resource_detail(resource_key)


@router.get("/resources/{resource_key}/metrics/{metric_key}/records")
def get_resource_metric_records(
    resource_key: str,
    metric_key: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    config = _metric_layer_config(resource_key, metric_key)
    offset = (page - 1) * page_size
    payload = asyncio.run(
        _document_records_loader(
            layer=config["layer"],
            limit=page_size,
            offset=offset,
            doc_type=config.get("doc_type"),
        )
    )
    return {
        "resource_key": resource_key,
        "metric_key": metric_key,
        "title": config["title"],
        "page": page,
        "page_size": page_size,
        **(payload or {}),
    }
