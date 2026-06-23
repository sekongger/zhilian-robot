from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import ArticleStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class SourceConfig:
    source_id: str
    source_type: str
    name: str
    url: str
    enabled: bool = True
    priority: int = 100
    quality_score: float = 0.5
    rate_limit_per_min: int = 20
    tags: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineConfig:
    max_content_length: int = 5000
    min_content_length: int = 80
    dedup_similarity_threshold: float = 0.9
    compress_max_chars: int = 200
    ingest_retry_times: int = 2
    relevance_mode: str = "high_recall"
    gray_mode: bool = True
    schedule_hours: int = 4


@dataclass(slots=True)
class ArticleRecord:
    article_id: str
    source_id: str
    source_name: str
    source_url: str
    title: str
    content_raw: str
    publish_time_utc: datetime | None
    canonical_url: str
    crawled_at_utc: datetime = field(default_factory=utcnow)
    status: ArticleStatus = ArticleStatus.FETCHED
    content_clean: str | None = None
    relevance_score: float | None = None
    matched_keywords: list[str] = field(default_factory=list)
    dedup_key: str | None = None
    compressed_text: str | None = None
    compressed_structured: dict[str, Any] | None = None
    compress_error: str | None = None
    ingest_error: str | None = None
    graphiti_episode_uuid: str | None = None
    attempt_count: int = 0
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def to_document(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "title": self.title,
            "content_raw": self.content_raw,
            "publish_time_utc": self.publish_time_utc,
            "canonical_url": self.canonical_url,
            "crawled_at_utc": self.crawled_at_utc,
            "status": self.status.value,
            "content_clean": self.content_clean,
            "relevance_score": self.relevance_score,
            "matched_keywords": self.matched_keywords,
            "dedup_key": self.dedup_key,
            "compressed_text": self.compressed_text,
            "compressed_structured": self.compressed_structured,
            "compress_error": self.compress_error,
            "ingest_error": self.ingest_error,
            "graphiti_episode_uuid": self.graphiti_episode_uuid,
            "attempt_count": self.attempt_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
