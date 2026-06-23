from __future__ import annotations

from crawler.domain.enums import ArticleStatus
from crawler.pipeline.context import PipelineContext
from crawler.services.canonical_url_service import is_traceable_source_url


def run_ingest(
    context: PipelineContext,
    *,
    limit: int,
    statuses: list[str] | None = None,
    group_id: str | None = None,
) -> dict[str, int]:
    query_statuses = statuses or [ArticleStatus.COMPRESSED.value]
    records = context.repository.list_by_status(query_statuses, limit=limit)
    ingested = 0
    failed = 0

    for record in records:
        article_id = record["article_id"]
        context.repository.increment_attempt(article_id)
        canonical_url = str(record.get("canonical_url") or "").strip()
        if not is_traceable_source_url(canonical_url):
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.INGEST_FAILED.value,
                    "ingest_error": "missing traceable original source url",
                },
            )
            failed += 1
            continue
        payload = {
            "title": record.get("title"),
            "name": record.get("title"),
            "text": record.get("compressed_text"),
            "publish_time": (
                record.get("publish_time_utc").isoformat()
                if record.get("publish_time_utc")
                else None
            ),
            "source": record.get("source_name"),
            "url": canonical_url,
            "raw_text": record.get("content_raw"),
            "structured_facts": record.get("compressed_structured"),
        }
        if group_id:
            payload["group_id"] = group_id
            payload["fusion_batch_id"] = group_id
        try:
            response = context.ingest_client.ingest(payload)
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.INGESTED.value,
                    "ingest_error": None,
                    "graphiti_episode_uuid": response.get("episode_uuid"),
                },
            )
            ingested += 1
        except Exception as exc:
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.INGEST_FAILED.value,
                    "ingest_error": str(exc),
                },
            )
            failed += 1

    return {"ingested": ingested, "failed": failed, "total": len(records)}
