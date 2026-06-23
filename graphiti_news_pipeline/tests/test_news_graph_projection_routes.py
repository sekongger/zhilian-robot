from __future__ import annotations

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import graph_routes


class FakeProjectionService:
    def __init__(self, driver):
        self.driver = driver

    async def materialize_projection(self, *, group_id=None, limit=5000, clear_existing=False):
        return {
            "projection_version": "news_projection_v1",
            "group_id": group_id,
            "projected_entities": 2,
            "projected_relationships": 1,
            "entity_type_counts": {"Enterprise": 1, "Product": 1},
            "relationship_type_counts": {"RELEASES": 1},
            "limit": limit,
            "clear_existing": clear_existing,
        }

    async def projection_stats(self, *, group_id=None):
        return {
            "projection_version": "news_projection_v1",
            "group_id": group_id,
            "projected_entities": 2,
            "projected_relationships": 1,
        }


class FakeGraphitiService:
    def __init__(self):
        self.graphiti = type("Graphiti", (), {"driver": object()})()


def test_materialize_news_graph_projection_route_delegates_to_service(monkeypatch):
    monkeypatch.setattr(graph_routes, "graphiti_service", FakeGraphitiService())
    monkeypatch.setattr(graph_routes, "NewsGraphProjectionService", FakeProjectionService)

    request = graph_routes.NewsGraphProjectionRequest(
        group_id="crawl_1",
        limit=100,
        clear_existing=True,
    )

    response = asyncio.run(graph_routes.materialize_news_graph_projection(request))

    assert response["status"] == "success"
    assert response["result"]["group_id"] == "crawl_1"
    assert response["result"]["projected_relationships"] == 1
    assert response["result"]["clear_existing"] is True


def test_news_graph_projection_stats_route_delegates_to_service(monkeypatch):
    monkeypatch.setattr(graph_routes, "graphiti_service", FakeGraphitiService())
    monkeypatch.setattr(graph_routes, "NewsGraphProjectionService", FakeProjectionService)

    response = asyncio.run(graph_routes.get_news_graph_projection_stats(group_id="crawl_1"))

    assert response["status"] == "success"
    assert response["stats"]["group_id"] == "crawl_1"
    assert response["stats"]["projected_entities"] == 2
