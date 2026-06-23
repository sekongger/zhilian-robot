from __future__ import annotations

from datetime import datetime, timezone
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import graph_routes


class FakeGraphitiService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def add_text_episode(
        self,
        text: str,
        *,
        name: str,
        reference_time: datetime | None,
        episode_metadata: dict,
        group_id: str | None = None,
    ):
        self.calls.append(
            {
                "text": text,
                "name": name,
                "reference_time": reference_time,
                "episode_metadata": episode_metadata,
                "group_id": group_id,
            }
        )
        return (
            SimpleNamespace(
                episode=SimpleNamespace(
                    uuid="episode-001",
                    valid_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
                    created_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
                ),
                nodes=[],
            ),
            False,
        )


def test_add_text_passes_group_id_and_fusion_batch_id_to_graphiti_service(monkeypatch):
    fake_service = FakeGraphitiService()
    monkeypatch.setattr(graph_routes, "graphiti_service", fake_service)

    request = graph_routes.AddTextRequest(
        text="三星集团存储芯片相关资讯。",
        title="三星存储资讯",
        source="rss_36kr_newsflash",
        url="https://36kr.com/p/3822747968196993?f=rss",
        group_id="crawl_202605240001",
        fusion_batch_id="crawl_202605240001",
    )

    response = asyncio.run(graph_routes.add_text(request, BackgroundTasks()))

    assert response["status"] == "success"
    assert fake_service.calls[0]["group_id"] == "crawl_202605240001"
    assert fake_service.calls[0]["episode_metadata"]["group_id"] == "crawl_202605240001"
    assert fake_service.calls[0]["episode_metadata"]["fusion_batch_id"] == "crawl_202605240001"
