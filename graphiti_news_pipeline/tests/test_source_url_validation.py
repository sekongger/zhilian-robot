from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawler.connectors.octopus_connector import OctopusConnector
from crawler.domain.models import SourceConfig
from crawler.services.canonical_url_service import canonicalize_url


class FakeCleaner:
    def clean(self, *, title: str, raw_text: str) -> tuple[str, bool]:
        return raw_text, False


def test_canonicalize_url_rejects_placeholder_domains():
    assert canonicalize_url("https://example.com/graphiti-news-small-20260524") == ""


def test_octopus_map_item_requires_original_article_url():
    connector = OctopusConnector()
    connector.cleaner = FakeCleaner()
    source = SourceConfig(
        source_id="octopus_news",
        source_type="octopus",
        name="Octopus News Feed",
        url="https://openapi.bazhuayu.com",
    )

    record = connector._map_item(
        source=source,
        task_id="task-001",
        item={
            "title": "三星存储芯片价格变化",
            "content": "三星存储芯片价格变化，AI服务器需求提升。",
            "publish_time": datetime.now(timezone.utc).isoformat(),
        },
        since_hours=24,
    )

    assert record is None
