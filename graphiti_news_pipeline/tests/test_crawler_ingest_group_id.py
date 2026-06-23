from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawler.pipeline.steps.ingest_step import run_ingest


@dataclass
class FakeRepository:
    records: list[dict]
    updates: list[tuple[str, dict]]

    def list_by_status(self, statuses: list[str], limit: int) -> list[dict]:
        return self.records[:limit]

    def increment_attempt(self, article_id: str) -> int:
        return 1

    def update_article(self, article_id: str, fields: dict) -> None:
        self.updates.append((article_id, fields))


@dataclass
class FakeIngestClient:
    payloads: list[dict]

    def ingest(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return {"episode_uuid": "episode-001"}


@dataclass
class FakeContext:
    repository: FakeRepository
    ingest_client: FakeIngestClient


def test_run_ingest_passes_group_id_and_fusion_batch_id_to_graphiti_payload():
    repository = FakeRepository(
        records=[
            {
                "article_id": "article-001",
                "title": "三星存储资讯",
                "compressed_text": "三星集团存储芯片相关资讯。",
                "publish_time_utc": None,
                "source_name": "rss_36kr_newsflash",
                "canonical_url": "https://36kr.com/p/3822747968196993?f=rss",
                "content_raw": "三星集团存储芯片相关资讯原文。",
                "compressed_structured": {"entities": ["三星集团"]},
            }
        ],
        updates=[],
    )
    ingest_client = FakeIngestClient(payloads=[])
    context = FakeContext(repository=repository, ingest_client=ingest_client)

    result = run_ingest(context, limit=10, group_id="crawl_202605240001")

    assert result["ingested"] == 1
    assert ingest_client.payloads[0]["group_id"] == "crawl_202605240001"
    assert ingest_client.payloads[0]["fusion_batch_id"] == "crawl_202605240001"


def test_run_ingest_rejects_missing_traceable_original_url():
    repository = FakeRepository(
        records=[
            {
                "article_id": "article-001",
                "title": "三星存储资讯",
                "compressed_text": "三星集团存储芯片相关资讯。",
                "publish_time_utc": None,
                "source_name": "rss_36kr_newsflash",
                "canonical_url": "https://example.com/news/1",
                "content_raw": "三星集团存储芯片相关资讯原文。",
                "compressed_structured": {"entities": ["三星集团"]},
            }
        ],
        updates=[],
    )
    ingest_client = FakeIngestClient(payloads=[])
    context = FakeContext(repository=repository, ingest_client=ingest_client)

    result = run_ingest(context, limit=10, group_id="crawl_202605240001")

    assert result == {"ingested": 0, "failed": 1, "total": 1}
    assert ingest_client.payloads == []
    assert repository.updates[0][1]["status"] == "INGEST_FAILED"
    assert repository.updates[0][1]["ingest_error"] == "missing traceable original source url"
