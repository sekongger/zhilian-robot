from __future__ import annotations

from datetime import datetime, timezone

from crawler.domain.enums import ArticleStatus
from crawler.pipeline.context import PipelineContext
from crawler.pipeline.steps.compress_step import run_compress
from crawler.pipeline.steps.dedup_step import run_dedup
from crawler.pipeline.steps.fetch_step import run_fetch
from crawler.pipeline.steps.ingest_step import run_ingest
from crawler.pipeline.steps.normalize_step import run_normalize
from crawler.pipeline.steps.relevance_step import run_relevance


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("crawl_%Y%m%d%H%M%S")


class CrawlerOrchestrator:
    def __init__(self, context: PipelineContext):
        self.context = context

    def run_once(
        self,
        *,
        since_hours: int,
        source_filter: str | None,
        max_items_per_source: int,
        process_limit: int,
        enable_ingest: bool,
    ) -> dict:
        rid = _run_id()
        summary = {
            "run_id": rid,
            "graphiti_group_id": rid,
            "mode": "run_once",
            "gray_mode": self.context.config.gray_mode,
            "since_hours": since_hours,
            "source_filter": source_filter,
            "max_items_per_source": max_items_per_source,
            "process_limit": process_limit,
            "fetch": run_fetch(
                self.context,
                since_hours=since_hours,
                max_items_per_source=max_items_per_source,
                source_filter=source_filter,
            ),
            "normalize": run_normalize(self.context, limit=process_limit),
            "relevance": run_relevance(self.context, limit=process_limit),
            "dedup": run_dedup(self.context, limit=process_limit),
            "compress": run_compress(self.context, limit=process_limit),
        }
        summary["ingest"] = self._run_ingest_if_enabled(
            process_limit=process_limit,
            enable_ingest=enable_ingest,
            statuses=None,
            group_id=rid,
        )
        return self._write_run(summary)

    def run_crawl_only(
        self,
        *,
        since_hours: int,
        source_filter: str | None,
        max_items_per_source: int,
        until_utc: datetime | None = None,
    ) -> dict:
        rid = _run_id()
        summary = {
            "run_id": rid,
            "mode": "crawl_only",
            "fetch": run_fetch(
                self.context,
                since_hours=since_hours,
                max_items_per_source=max_items_per_source,
                source_filter=source_filter,
                until_utc=until_utc,
            ),
            "since_hours": since_hours,
            "source_filter": source_filter,
            "max_items_per_source": max_items_per_source,
            "until_utc": until_utc,
        }
        return self._write_run(summary)

    def run_compress_only(self, *, process_limit: int) -> dict:
        rid = _run_id()
        summary = {
            "run_id": rid,
            "mode": "compress_only",
            "normalize": run_normalize(self.context, limit=process_limit),
            "relevance": run_relevance(self.context, limit=process_limit),
            "dedup": run_dedup(self.context, limit=process_limit),
            "compress": run_compress(self.context, limit=process_limit),
            "process_limit": process_limit,
        }
        return self._write_run(summary)

    def run_ingest_only(self, *, process_limit: int) -> dict:
        rid = _run_id()
        summary = {
            "run_id": rid,
            "graphiti_group_id": rid,
            "mode": "ingest_only",
            "gray_mode": self.context.config.gray_mode,
            "process_limit": process_limit,
            "ingest": self._run_ingest_if_enabled(
                process_limit=process_limit,
                enable_ingest=True,
                statuses=None,
                group_id=rid,
            ),
        }
        return self._write_run(summary)

    def run_retry(
        self,
        *,
        retry_status: str,
        process_limit: int,
        enable_ingest: bool,
    ) -> dict:
        rid = _run_id()
        summary: dict = {
            "run_id": rid,
            "graphiti_group_id": rid,
            "mode": "retry",
            "gray_mode": self.context.config.gray_mode,
            "retry_status": retry_status,
            "process_limit": process_limit,
        }

        retry_upper = retry_status.strip().upper()
        retry_compress = retry_upper in {"ALL", ArticleStatus.COMPRESS_FAILED.value}
        retry_ingest = retry_upper in {"ALL", ArticleStatus.INGEST_FAILED.value}

        if retry_compress:
            summary["compress_retry"] = run_compress(
                self.context,
                limit=process_limit,
                statuses=[ArticleStatus.COMPRESS_FAILED.value],
            )
        else:
            summary["compress_retry"] = {"compressed": 0, "failed": 0, "total": 0, "skipped": True}

        if retry_ingest:
            summary["ingest_retry"] = self._run_ingest_if_enabled(
                process_limit=process_limit,
                enable_ingest=enable_ingest,
                statuses=[ArticleStatus.INGEST_FAILED.value],
                group_id=rid,
            )
        else:
            summary["ingest_retry"] = {"ingested": 0, "failed": 0, "total": 0, "skipped": True}

        return self._write_run(summary)

    def run_backfill(
        self,
        *,
        from_utc: datetime,
        to_utc: datetime,
        source_filter: str | None,
        max_items_per_source: int,
        process_limit: int,
        enable_ingest: bool,
    ) -> dict:
        now_utc = datetime.now(timezone.utc)
        since_hours = max(0, int((now_utc - from_utc).total_seconds() // 3600) + 1)
        rid = _run_id()
        summary = {
            "run_id": rid,
            "graphiti_group_id": rid,
            "mode": "backfill",
            "gray_mode": self.context.config.gray_mode,
            "source_filter": source_filter,
            "max_items_per_source": max_items_per_source,
            "process_limit": process_limit,
            "from_utc": from_utc,
            "to_utc": to_utc,
            "since_hours": since_hours,
            "fetch": run_fetch(
                self.context,
                since_hours=since_hours,
                max_items_per_source=max_items_per_source,
                source_filter=source_filter,
                until_utc=to_utc,
            ),
            "normalize": run_normalize(self.context, limit=process_limit),
            "relevance": run_relevance(self.context, limit=process_limit),
            "dedup": run_dedup(self.context, limit=process_limit),
            "compress": run_compress(self.context, limit=process_limit),
        }
        summary["ingest"] = self._run_ingest_if_enabled(
            process_limit=process_limit,
            enable_ingest=enable_ingest,
            statuses=None,
            group_id=rid,
        )
        return self._write_run(summary)

    def _run_ingest_if_enabled(
        self,
        *,
        process_limit: int,
        enable_ingest: bool,
        statuses: list[str] | None,
        group_id: str | None,
    ) -> dict:
        if not enable_ingest:
            return {
                "ingested": 0,
                "failed": 0,
                "total": 0,
                "skipped": True,
                "reason": "ingest_not_requested",
            }
        if self.context.config.gray_mode:
            return {
                "ingested": 0,
                "failed": 0,
                "total": 0,
                "skipped": True,
                "reason": "gray_mode_enabled",
            }
        return run_ingest(self.context, limit=process_limit, statuses=statuses, group_id=group_id)

    def _write_run(self, summary: dict) -> dict:
        summary["created_at"] = datetime.now(timezone.utc)
        self.context.repository.write_run_log(summary)
        return summary
