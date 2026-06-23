from __future__ import annotations

import re

from crawler.domain.enums import ArticleStatus
from crawler.pipeline.context import PipelineContext
from crawler.utils.hash_utils import sha256_hex
from crawler.utils.text_utils import clip_text, normalize_text


TITLE_DEDUP_PATTERN = re.compile(r"[\s\W_]+", flags=re.UNICODE)


def _title_dedup_key(title: str) -> str:
    return TITLE_DEDUP_PATTERN.sub("", (title or "").lower())


def run_normalize(context: PipelineContext, *, limit: int) -> dict[str, int]:
    records = context.repository.list_by_status([ArticleStatus.FETCHED.value], limit=limit)
    normalized = 0
    rejected = 0

    for record in records:
        article_id = record["article_id"]
        content_clean = normalize_text(record.get("content_raw", ""))
        title = normalize_text(record.get("title", ""))
        if not content_clean or len(content_clean) < context.config.min_content_length:
            context.repository.update_article(
                article_id,
                {
                    "status": ArticleStatus.RELEVANCE_REJECTED.value,
                    "content_clean": content_clean,
                    "relevance_score": 0.0,
                    "matched_keywords": [],
                    "compress_error": "content_too_short_or_empty",
                },
            )
            rejected += 1
            continue

        clipped = clip_text(content_clean, context.config.max_content_length)
        publish_time = record.get("publish_time_utc")
        publish_key = publish_time.isoformat() if publish_time else ""
        publish_day = publish_key[:10]
        title_dedup = _title_dedup_key(title)
        content_signature = sha256_hex(clip_text(content_clean, 240).lower())
        dedup_key = sha256_hex(
            "|".join(
                [
                    record.get("canonical_url", "") or "",
                    title,
                    publish_day,
                ]
            )
        )
        context.repository.update_article(
            article_id,
            {
                "status": ArticleStatus.NORMALIZED.value,
                "content_clean": clipped,
                "dedup_key": dedup_key,
                "title_dedup": title_dedup,
                "publish_day": publish_day,
                "content_signature": content_signature,
            },
        )
        normalized += 1

    return {"normalized": normalized, "rejected": rejected, "total": len(records)}
