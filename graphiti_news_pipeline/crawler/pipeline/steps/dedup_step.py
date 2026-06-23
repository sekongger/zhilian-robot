from __future__ import annotations

from crawler.domain.enums import ArticleStatus
from crawler.pipeline.context import PipelineContext


def run_dedup(context: PipelineContext, *, limit: int) -> dict[str, int]:
    records = context.repository.list_by_status([ArticleStatus.RELEVANCE_PASSED.value], limit=limit)
    passed = 0
    rejected = 0

    for record in records:
        article_id = record["article_id"]
        dedup_key = record.get("dedup_key", "")
        if not dedup_key:
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.DEDUP_REJECTED.value,
                    "compress_error": "missing_dedup_key",
                },
            )
            rejected += 1
            continue

        duplicate_reason = "duplicate_article"
        is_duplicate = context.repository.has_duplicate(dedup_key, article_id=article_id)
        if not is_duplicate:
            title_dedup = (record.get("title_dedup", "") or "").strip()
            publish_day = (record.get("publish_day", "") or "").strip()
            if title_dedup and publish_day:
                is_duplicate = context.repository.has_duplicate_by_title_day(
                    title_dedup,
                    publish_day,
                    article_id=article_id,
                )
                if is_duplicate:
                    duplicate_reason = "duplicate_title_day"

        if not is_duplicate:
            content_signature = (record.get("content_signature", "") or "").strip()
            publish_day = (record.get("publish_day", "") or "").strip()
            if content_signature and publish_day:
                is_duplicate = context.repository.has_duplicate_by_content_signature(
                    content_signature,
                    publish_day,
                    article_id=article_id,
                )
                if is_duplicate:
                    duplicate_reason = "duplicate_content_signature"

        if is_duplicate:
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.DEDUP_REJECTED.value,
                    "compress_error": duplicate_reason,
                },
            )
            rejected += 1
        else:
            context.repository.update_article(article_id, {"status": ArticleStatus.DEDUP_PASSED.value})
            passed += 1

    return {"passed": passed, "rejected": rejected, "total": len(records)}
