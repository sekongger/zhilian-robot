from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import json


HEADLINES_CONTRACT_VERSION = "2026-03-24"
HEADLINES_RESPONSE_FIELDS = [
    "doc_id",
    "title",
    "summary",
    "content",
    "source_name",
    "source_url",
    "publish_time",
]
ENTERPRISE_SAMPLE_FIELDS = [
    "name",
    "official_name",
    "code",
    "industry",
    "region",
    "website",
    "status",
    "description",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _batches_dir() -> Path:
    target = _repo_root() / "backend" / "data" / "datahub_mock_batches"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _get_mongo_conn():
    from app.database.mongodb import mongodb_conn

    return mongodb_conn


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _normalize_doc(document: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not isinstance(document, dict):
        return None
    payload = dict(document)
    if "_id" in payload:
        payload["_id"] = str(payload["_id"])
    return payload


def _fallback_headlines() -> List[Dict[str, Any]]:
    return [
        {
            "doc_id": "DOC_NEWS_FALLBACK_001",
            "title": "华为与具身智能企业推进产业合作",
            "summary": "双方围绕具身智能与自动化产线开展合作。",
            "content": "华为与某具身智能企业围绕自动化产线、机器视觉和工业机器人展开合作。",
            "source_name": "RSSHub",
            "source_url": "https://example.com/fallback/huawei-1",
            "publish_time": "2026-03-21T09:30:00+08:00",
        },
        {
            "doc_id": "DOC_NEWS_FALLBACK_002",
            "title": "机器人企业完成新一轮融资",
            "summary": "机器人企业获得机构投资，继续布局产业链协同。",
            "content": "某机器人企业宣布完成新一轮融资，将继续加大在机器人控制器和具身智能方向的投入。",
            "source_name": "RSSHub",
            "source_url": "https://example.com/fallback/robot-2",
            "publish_time": "2026-03-21T11:00:00+08:00",
        },
    ]


def get_headlines_contract() -> Dict[str, Any]:
    return {
        "contract_version": HEADLINES_CONTRACT_VERSION,
        "integration_mode": "mock_headlines",
        "status": "mock_ready",
        "request_spec": {
            "method": "GET",
            "path": "/api/v1/datahub/mock/headlines",
            "query": {
                "limit": "int, 1-200, 默认 20",
            },
        },
        "response_fields": list(HEADLINES_RESPONSE_FIELDS),
        "required_fields": list(HEADLINES_RESPONSE_FIELDS),
        "openks_submit_hint": {
            "method": "POST",
            "path": "/api/v1/openks/build-jobs",
            "module_names": ["news_kg", "event_kg", "industry_network"],
            "runtime_profile": "kag_openspg",
        },
        "notes": [
            "当前接口以 RSSHub/资源层资讯模拟 DataHub 头条输出。",
            "接口字段以 OpenKS headlines 批次标准化输入为准。",
            "真实 DataHub 接入完成后保留字段口径，不直接透出 OpenSPG 顶点边格式。",
        ],
    }


def list_mock_headlines(*, limit: int = 20) -> List[Dict[str, Any]]:
    mongo = _get_mongo_conn()
    rows = []
    try:
      rows = mongo.find_many("raw_documents", query={"doc_type": "news"}, limit=max(int(limit or 20), 1), sort=[("publish_time", -1)])
    except Exception:
      rows = []

    normalized = []
    for item in rows:
        payload = _normalize_doc(item) or {}
        normalized.append(
            {
                "doc_id": str(payload.get("doc_id") or payload.get("_id") or ""),
                "title": str(payload.get("title") or "未命名资讯"),
                "summary": str(payload.get("summary") or payload.get("content") or "")[:200],
                "content": str(payload.get("content") or payload.get("summary") or ""),
                "source_name": str(payload.get("source_name") or "RSSHub"),
                "source_url": str(payload.get("source_url") or payload.get("url") or ""),
                "publish_time": str(payload.get("publish_time") or payload.get("crawl_time") or ""),
            }
        )

    if normalized:
        return normalized[: max(int(limit or 20), 1)]
    return _fallback_headlines()[: max(int(limit or 20), 1)]


def enterprise_placeholder() -> Dict[str, Any]:
    return {
        "source": "enterprise_api",
        "enabled": False,
        "contract_status": "defined_not_connected",
        "message": "后续接入",
        "request_spec": {
            "method": "GET",
            "path": "/api/v1/datahub/mock/enterprise",
            "query": {
                "name": "string, 企业名称或简称",
            },
        },
        "sample_fields": list(ENTERPRISE_SAMPLE_FIELDS),
        "response_fields": list(ENTERPRISE_SAMPLE_FIELDS),
    }


def create_headlines_batch(*, source: str = "rsshub", limit: int = 20) -> Dict[str, Any]:
    items = list_mock_headlines(limit=limit)
    batch_id = f"BATCH_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    batch_file = _batches_dir() / f"{batch_id}.jsonl"
    lines = [json.dumps(item, ensure_ascii=False) for item in items]
    batch_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    payload = {
        "batch_id": batch_id,
        "source": source,
        "raw_count": len(items),
        "normalized_count": len(items),
        "manifest_uri": batch_file.resolve().as_uri(),
        "status": "ready",
        "created_at": _utc_now_iso(),
        "items_preview": items[:5],
    }
    try:
        _get_mongo_conn().update_one(
            "datahub_mock_batches",
            {"batch_id": batch_id},
            {"$set": payload},
            upsert=True,
        )
    except Exception:
        pass
    return payload


def get_batch(batch_id: str) -> Dict[str, Any] | None:
    try:
        payload = _get_mongo_conn().find_one("datahub_mock_batches", {"batch_id": batch_id})
    except Exception:
        payload = None
    return _normalize_doc(payload)
