import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from crawler.domain.models import SourceConfig
from crawler.pipeline.steps.fetch_step import run_fetch


class _StubRecord:
    def __init__(self, article_id: str):
        self.article_id = article_id
        self.source_id = "octopus_news"
        self.source_name = "Octopus"
        self.source_url = "https://openapi.bazhuayu.com"
        self.title = "t"
        self.content_raw = "raw"
        self.publish_time_utc = datetime(2026, 4, 26, 0, 0, tzinfo=timezone.utc)
        self.canonical_url = f"https://example.com/{article_id}"
        self.crawled_at_utc = datetime(2026, 4, 26, 0, 0, tzinfo=timezone.utc)
        self.status = SimpleNamespace(value="DEDUP_PASSED")
        self.content_clean = "clean"
        self.relevance_score = 1.0
        self.matched_keywords = ["octopus"]
        self.dedup_key = None
        self.compressed_text = None
        self.compressed_structured = None
        self.compress_error = None
        self.ingest_error = None
        self.graphiti_episode_uuid = None
        self.attempt_count = 0
        self.created_at = datetime(2026, 4, 26, 0, 0, tzinfo=timezone.utc)
        self.updated_at = datetime(2026, 4, 26, 0, 0, tzinfo=timezone.utc)


class _FakeRepo:
    def __init__(self, inserted: int):
        self.inserted = inserted
        self.upsert_calls = 0

    def upsert_fetched_articles(self, records):  # type: ignore[no-untyped-def]
        self.upsert_calls += 1
        return {
            "total": len(records),
            "inserted": self.inserted,
            "touched": len(records),
        }

    def has_unprocessed_article(self, article_id: str) -> bool:
        return False

    def article_exists(self, article_id: str) -> bool:
        return False


class _FakeRssConnector:
    def fetch(self, source, since_hours: int, max_items: int):  # type: ignore[no-untyped-def]
        return []


class _FakeOctopusConnector:
    def __init__(self, records, task_ids):  # type: ignore[no-untyped-def]
        self._records = records
        self._task_ids = task_ids
        self.mark_called = 0

    def fetch_with_meta(self, source, since_hours: int, max_items: int, should_keep=None):  # type: ignore[no-untyped-def]
        records = self._records
        if should_keep is not None:
            records = [r for r in records if should_keep(r)]
        return SimpleNamespace(records=records, exported_task_ids=self._task_ids if records else [])

    def mark_exported_tasks(self, source, task_ids):  # type: ignore[no-untyped-def]
        self.mark_called += 1
        return {"total": len(task_ids), "marked": len(task_ids), "failed": 0}


class OctopusExportMarkingTests(unittest.TestCase):
    def test_mark_exported_when_consumed_even_if_not_inserted(self) -> None:
        source = SourceConfig(
            source_id="octopus_news",
            source_type="octopus",
            name="Octopus",
            url="https://openapi.bazhuayu.com",
            enabled=True,
            options={},
        )
        records = [_StubRecord("a-1")]
        context = SimpleNamespace(
            sources=[source],
            repository=_FakeRepo(inserted=0),
        )

        import crawler.pipeline.steps.fetch_step as fetch_step

        old_rss = fetch_step.RSSConnector
        old_octo = fetch_step.OctopusConnector
        fake_octo = _FakeOctopusConnector(records=records, task_ids=["task-1"])
        try:
            fetch_step.RSSConnector = lambda: _FakeRssConnector()  # type: ignore[assignment]
            fetch_step.OctopusConnector = lambda: fake_octo  # type: ignore[assignment]
            result = run_fetch(
                context,
                since_hours=24,
                max_items_per_source=10,
                source_filter="octopus_news",
            )
        finally:
            fetch_step.RSSConnector = old_rss  # type: ignore[assignment]
            fetch_step.OctopusConnector = old_octo  # type: ignore[assignment]

        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["total"], 1)
        self.assertEqual(fake_octo.mark_called, 1)
        self.assertEqual(result["octopus_mark_exported"], 1)

    def test_mark_exported_after_inserted(self) -> None:
        source = SourceConfig(
            source_id="octopus_news",
            source_type="octopus",
            name="Octopus",
            url="https://openapi.bazhuayu.com",
            enabled=True,
            options={},
        )
        records = [_StubRecord("a-2")]
        context = SimpleNamespace(
            sources=[source],
            repository=_FakeRepo(inserted=1),
        )

        import crawler.pipeline.steps.fetch_step as fetch_step

        old_rss = fetch_step.RSSConnector
        old_octo = fetch_step.OctopusConnector
        fake_octo = _FakeOctopusConnector(records=records, task_ids=["task-2"])
        try:
            fetch_step.RSSConnector = lambda: _FakeRssConnector()  # type: ignore[assignment]
            fetch_step.OctopusConnector = lambda: fake_octo  # type: ignore[assignment]
            result = run_fetch(
                context,
                since_hours=24,
                max_items_per_source=10,
                source_filter="octopus_news",
            )
        finally:
            fetch_step.RSSConnector = old_rss  # type: ignore[assignment]
            fetch_step.OctopusConnector = old_octo  # type: ignore[assignment]

        self.assertEqual(result["inserted"], 1)
        self.assertEqual(fake_octo.mark_called, 1)
        self.assertEqual(result["octopus_mark_exported"], 1)

    def test_not_mark_exported_when_no_consumed_records(self) -> None:
        source = SourceConfig(
            source_id="octopus_news",
            source_type="octopus",
            name="Octopus",
            url="https://openapi.bazhuayu.com",
            enabled=True,
            options={},
        )
        records = []
        context = SimpleNamespace(
            sources=[source],
            repository=_FakeRepo(inserted=0),
        )

        import crawler.pipeline.steps.fetch_step as fetch_step

        old_rss = fetch_step.RSSConnector
        old_octo = fetch_step.OctopusConnector
        fake_octo = _FakeOctopusConnector(records=records, task_ids=["task-3"])
        try:
            fetch_step.RSSConnector = lambda: _FakeRssConnector()  # type: ignore[assignment]
            fetch_step.OctopusConnector = lambda: fake_octo  # type: ignore[assignment]
            result = run_fetch(
                context,
                since_hours=24,
                max_items_per_source=10,
                source_filter="octopus_news",
            )
        finally:
            fetch_step.RSSConnector = old_rss  # type: ignore[assignment]
            fetch_step.OctopusConnector = old_octo  # type: ignore[assignment]

        self.assertEqual(result["total"], 0)
        self.assertEqual(fake_octo.mark_called, 0)


if __name__ == "__main__":
    unittest.main()
