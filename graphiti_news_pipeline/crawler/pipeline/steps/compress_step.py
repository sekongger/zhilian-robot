from __future__ import annotations

from crawler.domain.enums import ArticleStatus
from crawler.pipeline.context import PipelineContext


def run_compress(
    context: PipelineContext,
    *,
    limit: int,
    statuses: list[str] | None = None,
) -> dict[str, int]:
    query_statuses = statuses or [ArticleStatus.DEDUP_PASSED.value]
    records = context.repository.list_by_status(query_statuses, limit=limit)
    compressed = 0
    failed = 0

    for record in records:
        article_id = record["article_id"]
        context.repository.increment_attempt(article_id)
        try:
            output = context.compressor.compress(
                title=record.get("title", ""),
                text=record.get("content_clean", "") or "",
                max_chars=context.config.compress_max_chars,
            )
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.COMPRESSED.value,
                    "compressed_text": output.get("graphiti_text", ""),
                    "compressed_structured": output.get("structured_facts", {}),
                    "compress_error": None,
                },
            )
            compressed += 1
        except Exception as exc:
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.COMPRESS_FAILED.value,
                    "compress_error": str(exc),
                },
            )
            failed += 1

    return {"compressed": compressed, "failed": failed, "total": len(records)}
