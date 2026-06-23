import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from crawler.connectors.octopus_connector import OctopusConnector
from crawler.domain.models import SourceConfig


class _StubCleaner:
    def clean(self, *, title: str, raw_text: str):  # type: ignore[no-untyped-def]
        return f"clean::{title}::{raw_text[:20]}", True


class OctopusConnectorTests(unittest.TestCase):
    def test_map_item_builds_dedup_passed_record(self) -> None:
        connector = OctopusConnector()
        connector.cleaner = _StubCleaner()
        source = SourceConfig(
            source_id="octopus_news",
            source_type="octopus",
            name="Octopus",
            url="https://openapi.bazhuayu.com",
            enabled=True,
            priority=1,
            tags=["robotics"],
            options={},
        )
        item = {
            "title": "某公司发布机器人新品",
            "url": "https://example.com/news?id=1&utm_source=x",
            "publish_time": (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "content": "这是正文内容",
            "abstract": "这是摘要",
        }

        record = connector._map_item(  # noqa: SLF001
            source=source,
            task_id="task-1",
            item=item,
            since_hours=48,
        )

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.status.value, "DEDUP_PASSED")
        self.assertTrue(record.content_clean.startswith("clean::"))
        self.assertEqual(record.relevance_score, 1.0)
        self.assertIn("octopus", record.matched_keywords)
        self.assertIn("robotics", record.matched_keywords)
        self.assertIsNotNone(record.publish_time_utc)
        assert record.publish_time_utc is not None
        age_hours = (datetime.now(timezone.utc) - record.publish_time_utc).total_seconds() / 3600
        self.assertGreaterEqual(age_hours, 0)
        self.assertLess(age_hours, 8)
        self.assertTrue(record.canonical_url.startswith("https://example.com/news"))

    def test_map_item_filters_old_publish_time(self) -> None:
        connector = OctopusConnector()
        connector.cleaner = _StubCleaner()
        source = SourceConfig(
            source_id="octopus_news",
            source_type="octopus",
            name="Octopus",
            url="https://openapi.bazhuayu.com",
            options={},
        )
        item = {
            "title": "旧新闻",
            "url": "https://example.com/old",
            "publish_time": "2024-01-01 10:00:00",
            "content": "正文",
        }
        record = connector._map_item(  # noqa: SLF001
            source=source,
            task_id="task-1",
            item=item,
            since_hours=24,
        )
        self.assertIsNone(record)

    def test_fetch_task_records_all_uses_offset_pagination(self) -> None:
        connector = OctopusConnector()
        connector.cleaner = _StubCleaner()
        source = SourceConfig(
            source_id="octopus_news",
            source_type="octopus",
            name="Octopus",
            url="https://openapi.bazhuayu.com",
            options={},
        )

        class _Resp:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):  # type: ignore[no-untyped-def]
                return None

            def json(self):  # type: ignore[no-untyped-def]
                return self._payload

        calls: list[dict] = []

        def _fake_get(url, headers=None, params=None, timeout=None):  # type: ignore[no-untyped-def]
            calls.append(dict(params or {}))
            if len(calls) == 1:
                return _Resp(
                    {
                        "data": {
                            "total": 200,
                            "offset": 2,
                            "data": [
                                {
                                    "title": "A",
                                    "url": "https://example.com/a",
                                    "publish_time": (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                                    "content": "body-a",
                                }
                            ],
                        }
                    }
                )
            return _Resp(
                {
                    "data": {
                        "total": 200,
                        "offset": None,
                        "data": [
                            {
                                "title": "B",
                                "url": "https://example.com/b",
                                "publish_time": (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                                "content": "body-b",
                            }
                        ],
                    }
                }
            )

        with patch("crawler.connectors.octopus_connector.requests.get", side_effect=_fake_get):
            records = connector._fetch_task_records_all(  # noqa: SLF001
                token="Bearer t",
                source=source,
                task_id="task-x",
                since_hours=24,
                max_items=10,
                should_keep=None,
            )

        self.assertEqual(len(records), 2)
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(calls[0].get("offset"), 1)
        self.assertEqual(calls[1].get("offset"), 2)

    def test_fetch_task_records_all_fallbacks_to_notexported_when_data_all_empty(self) -> None:
        connector = OctopusConnector()
        connector.cleaner = _StubCleaner()
        source = SourceConfig(
            source_id="octopus_news",
            source_type="octopus",
            name="Octopus",
            url="https://openapi.bazhuayu.com",
            options={},
        )

        class _Resp:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):  # type: ignore[no-untyped-def]
                return None

            def json(self):  # type: ignore[no-untyped-def]
                return self._payload

        calls: list[str] = []

        def _fake_get(url, headers=None, params=None, timeout=None):  # type: ignore[no-untyped-def]
            calls.append(str(url))
            if str(url).endswith("/data/all"):
                return _Resp({"data": {"total": 0, "data": []}})
            return _Resp(
                {
                    "data": {
                        "total": 1,
                        "offset": None,
                        "data": [
                            {
                                "title": "C",
                                "url": "https://example.com/c",
                                "publish_time": (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                                "content": "body-c",
                            }
                        ],
                    }
                }
            )

        with patch("crawler.connectors.octopus_connector.requests.get", side_effect=_fake_get):
            records = connector._fetch_task_records_all(  # noqa: SLF001
                token="Bearer t",
                source=source,
                task_id="task-fallback",
                since_hours=24,
                max_items=10,
                should_keep=None,
            )

        self.assertEqual(len(records), 1)
        self.assertTrue(any(url.endswith("/data/all") for url in calls))
        self.assertTrue(any(url.endswith("/data/notexported") for url in calls))


if __name__ == "__main__":
    unittest.main()
