"""zhilian-robot 资讯到 OpenSPG Builder 的桥接导出。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_iso_time(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return text
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _hash(*parts: str, length: int = 24) -> str:
    raw = "||".join(part for part in parts if part)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:length]


def normalize_news_record(news: Dict[str, Any]) -> Dict[str, Any]:
    title = _safe_text(news.get("title"))
    content = _safe_text(news.get("content") or news.get("summary"))
    source_name = _safe_text(news.get("source_name") or news.get("source") or "unknown")
    source_url = _safe_text(news.get("source_url") or news.get("url"))
    publish_time = _to_iso_time(news.get("publish_time") or news.get("published_at"))
    crawl_time = _to_iso_time(news.get("crawled_at") or news.get("crawl_time") or datetime.now(timezone.utc))

    doc_hash = news.get("doc_hash") or _hash(title, content, source_url, length=32)
    doc_id = news.get("doc_id") or f"DOC_{_hash(title, source_url, doc_hash, length=18)}"

    return {
        "doc_id": doc_id,
        "doc_hash": doc_hash,
        "doc_type": "news",
        "title": title or "未命名资讯",
        "content": content,
        "summary": _safe_text(news.get("summary")),
        "source_name": source_name,
        "source_url": source_url,
        "publish_time": publish_time,
        "crawl_time": crawl_time,
        "keyword": _safe_text(news.get("keyword")),
        "source_id": _safe_text(news.get("source_id") or news.get("ds_id")),
        "ingest_source": "zhilian-robot",
    }


def export_news_batch_to_jsonl_lines(rows: Iterable[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for row in rows:
        normalized = normalize_news_record(row)
        lines.append(json.dumps(normalized, ensure_ascii=False, separators=(",", ":")))
    return lines

