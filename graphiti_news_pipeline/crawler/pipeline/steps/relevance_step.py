from __future__ import annotations

from crawler.domain.enums import ArticleStatus
from crawler.pipeline.context import PipelineContext
from crawler.services.relevance_service import evaluate_relevance


def run_relevance(context: PipelineContext, *, limit: int) -> dict[str, int]:
    records = context.repository.list_by_status([ArticleStatus.NORMALIZED.value], limit=limit)
    passed = 0
    rejected = 0

    for record in records:
        article_id = record["article_id"]
        result = evaluate_relevance(
            record.get("title", ""),
            record.get("content_clean", "") or "",
            mode=context.config.relevance_mode,
        )
        if result.passed:
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.RELEVANCE_PASSED.value,
                    "relevance_score": result.score,
                    "matched_keywords": result.matched_keywords,
                },
            )
            passed += 1
        else:
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.RELEVANCE_REJECTED.value,
                    "relevance_score": result.score,
                    "matched_keywords": result.matched_keywords,
                },
            )
            rejected += 1

    return {"passed": passed, "rejected": rejected, "total": len(records)}

