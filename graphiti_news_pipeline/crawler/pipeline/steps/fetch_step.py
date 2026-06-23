from __future__ import annotations

from datetime import datetime
import logging

from crawler.connectors.octopus_connector import OctopusConnector
from crawler.connectors.rss_connector import RSSConnector
from crawler.domain.models import ArticleRecord
from crawler.domain.models import SourceConfig
from crawler.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_fetch(
    context: PipelineContext,
    *,
    since_hours: int,
    max_items_per_source: int,
    source_filter: str | None = None,
    until_utc: datetime | None = None,
) -> dict[str, int]:
    rss_connector = RSSConnector()
    octopus_connector = OctopusConnector()
    target_sources: list[SourceConfig] = [
        source
        for source in context.sources
        if source.enabled and (source_filter is None or source.source_id == source_filter)
    ]

    all_records = []
    octopus_record_count = 0
    octopus_task_ids_to_mark: list[tuple[SourceConfig, str]] = []
    for source in target_sources:
        if source.source_type == "rss":
            records = rss_connector.fetch(source, since_hours=since_hours, max_items=max_items_per_source)
        elif source.source_type == "octopus":
            def _should_keep_octopus(record: ArticleRecord) -> bool:
                # Keep if it does not exist locally or it is still not fully ingested.
                return (
                    context.repository.has_unprocessed_article(record.article_id)
                    or not context.repository.article_exists(record.article_id)
                )

            octopus_result = octopus_connector.fetch_with_meta(
                source,
                since_hours=since_hours,
                max_items=max_items_per_source,
                should_keep=_should_keep_octopus,
            )
            records = octopus_result.records
            octopus_task_ids_to_mark.extend((source, task_id) for task_id in octopus_result.exported_task_ids)
            octopus_record_count += len(records)
        else:
            logger.info("Skip unsupported source type=%s source=%s", source.source_type, source.source_id)
            continue

        if until_utc is not None:
            records = [
                record
                for record in records
                if record.publish_time_utc is None or record.publish_time_utc <= until_utc
            ]
        logger.info("Fetched source=%s count=%s", source.source_id, len(records))
        all_records.extend(records)

    result = context.repository.upsert_fetched_articles(all_records)
    marked = 0
    mark_failed = 0
    # Mark exported as long as this run has consumed octopus payloads.
    # Otherwise cloud-side "notexported" can get stuck on already-upserted records
    # and block queue progression.
    if result.get("total", 0) > 0 and octopus_task_ids_to_mark:
        source_task_ids: dict[str, tuple[SourceConfig, list[str]]] = {}
        for source, task_id in octopus_task_ids_to_mark:
            bucket = source_task_ids.get(source.source_id)
            if bucket is None:
                source_task_ids[source.source_id] = (source, [task_id])
            else:
                bucket[1].append(task_id)
        for _, payload in source_task_ids.items():
            source, task_ids = payload
            mark_result = octopus_connector.mark_exported_tasks(source, task_ids)
            marked += int(mark_result.get("marked", 0))
            mark_failed += int(mark_result.get("failed", 0))

    result["sources"] = len(target_sources)
    result["octopus_prefiltered"] = octopus_record_count
    result["octopus_mark_exported"] = marked
    result["octopus_mark_exported_failed"] = mark_failed
    return result
