from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
import types
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fake_graphiti_service_module = types.ModuleType("services.graphiti_service")
fake_graphiti_service_module.graphiti_service = SimpleNamespace(
    graphiti=SimpleNamespace(driver=object())
)
sys.modules.setdefault("services.graphiti_service", fake_graphiti_service_module)

fake_calculation_service_module = types.ModuleType("services.calculation_service")
fake_calculation_service_module.UUID_REGEX = re.compile(r"^[0-9a-f-]{36}$", re.IGNORECASE)
sys.modules.setdefault("services.calculation_service", fake_calculation_service_module)

fake_es_service_module = types.ModuleType("services.es_service")
fake_es_service_module.es_service = SimpleNamespace(get_client=lambda: None)
fake_es_service_module.GRAPH_NODES_INDEX = "graph_nodes"
sys.modules.setdefault("services.es_service", fake_es_service_module)

fake_storyline_service_module = types.ModuleType("services.storyline_service")
fake_storyline_service_module.storyline_service = SimpleNamespace()
sys.modules.setdefault("services.storyline_service", fake_storyline_service_module)

fake_wikidata_mapping_service_module = types.ModuleType("services.wikidata_mapping_service")
fake_wikidata_mapping_service_module.wikidata_mapping_service = SimpleNamespace()
sys.modules.setdefault("services.wikidata_mapping_service", fake_wikidata_mapping_service_module)

from api import graph_routes


class FakeEntityHeatService:
    def __init__(self, driver):
        self.driver = driver

    async def generate_and_store_rankings(self, **kwargs):
        return {
            "period_type": kwargs["period_type"],
            "period_start": "2026-06-22T00:00:00+08:00",
            "period_end": "2026-06-22T23:59:59.999999+08:00",
            "entity_type": kwargs["entity_type"],
            "formula_version": "entity_heat_v1",
            "formula": {"mention_weight": 0.45},
            "items": [{"rank": 1, "entity_name": "腾讯", "heat_score": 98.0}],
        }

    async def query_rankings(self, **kwargs):
        return {
            "period_type": kwargs["period_type"],
            "period_start": "2026-06-22T00:00:00+08:00",
            "period_end": "2026-06-22T23:59:59.999999+08:00",
            "entity_type": kwargs["entity_type"],
            "formula_version": "entity_heat_v1",
            "formula": {"mention_weight": 0.45},
            "items": [{"rank": 1, "entity_name": "腾讯", "heat_score": 98.0}],
        }


def test_trigger_entity_heat_rankings_route_returns_snapshot_payload(monkeypatch):
    monkeypatch.setattr(graph_routes, "EntityHeatRankingService", FakeEntityHeatService)

    request = graph_routes.EntityHeatRankingRequest(
        period_type="daily",
        as_of="2026-06-22",
        entity_type="Enterprise",
        limit_per_type=20,
    )

    response = asyncio.run(graph_routes.trigger_entity_heat_rankings(request))

    assert response["status"] == "success"
    assert response["result"]["formula_version"] == "entity_heat_v1"
    assert response["result"]["items"][0]["entity_name"] == "腾讯"


def test_query_entity_heat_rankings_route_returns_formula_and_items(monkeypatch):
    monkeypatch.setattr(graph_routes, "EntityHeatRankingService", FakeEntityHeatService)

    response = asyncio.run(
        graph_routes.get_entity_heat_rankings(
            period_type="daily",
            date="2026-06-22",
            entity_type="Enterprise",
            limit=20,
        )
    )

    assert response["period_type"] == "daily"
    assert response["formula"]["mention_weight"] == 0.45
    assert response["items"][0]["heat_score"] == 98.0
