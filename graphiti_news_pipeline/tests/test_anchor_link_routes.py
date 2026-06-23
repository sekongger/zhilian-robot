from __future__ import annotations

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import graph_routes


class FakeGraphitiService:
    def __init__(self):
        self.synced = []
        self.links = []

    async def sync_common_sense_anchors(self, anchors):
        self.synced.extend(anchors)
        return {"synced": len(anchors), "skipped": 0}

    async def link_news_entities_to_anchors(self, decisions):
        self.links.extend(decisions)
        return {"refersTo": 1, "candidateRefersTo": 0, "unresolved": 0}

    async def get_anchor_link_stats(self, group_id):
        return {"group_id": group_id, "refersTo": 1, "candidateRefersTo": 0, "unresolved": 0}


def test_sync_common_sense_anchors_route_delegates_to_graphiti_service(monkeypatch):
    fake_service = FakeGraphitiService()
    monkeypatch.setattr(graph_routes, "graphiti_service", fake_service)

    request = graph_routes.SyncAnchorsRequest(
        anchors=[
            {
                "anchor_id": "Enterprise:wiki:Q20716",
                "type_name": "Enterprise",
                "name": "三星",
                "aliases": ["Samsung"],
                "description": "韩国综合性企业集团。",
                "source_graph": "incore_common_neo4j",
                "source_version": "wikidata_v2_202606",
                "properties": {"country": "韩国"},
            }
        ]
    )

    response = asyncio.run(graph_routes.sync_common_sense_anchors(request))

    assert response["status"] == "success"
    assert response["result"] == {"synced": 1, "skipped": 0}
    assert fake_service.synced[0]["anchor_id"] == "Enterprise:wiki:Q20716"


def test_link_news_entities_route_delegates_to_graphiti_service(monkeypatch):
    fake_service = FakeGraphitiService()
    monkeypatch.setattr(graph_routes, "graphiti_service", fake_service)

    request = graph_routes.LinkEntitiesRequest(
        decisions=[
            {
                "news_entity_id": "entity-1",
                "news_entity_name": "三星",
                "candidate_anchor_id": "Enterprise:wiki:Q20716",
                "match_score": 1.0,
                "match_method": "exact_name",
                "decision": "refersTo",
                "reason": "exact_name score 1.000",
                "group_id": "crawl_1",
            }
        ]
    )

    response = asyncio.run(graph_routes.link_news_entities_to_anchors(request))

    assert response["status"] == "success"
    assert response["result"]["refersTo"] == 1
    assert fake_service.links[0]["decision"] == "refersTo"


def test_anchor_link_stats_route_returns_group_scoped_stats(monkeypatch):
    fake_service = FakeGraphitiService()
    monkeypatch.setattr(graph_routes, "graphiti_service", fake_service)

    response = asyncio.run(graph_routes.anchor_link_stats(group_id="crawl_1"))

    assert response["status"] == "success"
    assert response["stats"]["group_id"] == "crawl_1"

