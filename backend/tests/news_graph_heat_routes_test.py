from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = "fake error"

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError("fake error", response=self)

    def json(self):
        return self._payload


def _build_client(monkeypatch, payload=None, status_code=200):
    from app.api import news_graph_routes

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return _FakeResponse(payload or {"items": [], "formula_version": "entity_heat_v1"}, status_code=status_code)

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse(payload or {"status": "success", "result": {"items": []}}, status_code=status_code)

    monkeypatch.setattr(news_graph_routes.requests, "get", fake_get)
    monkeypatch.setattr(news_graph_routes.requests, "post", fake_post)
    monkeypatch.setattr(news_graph_routes.settings, "GRAPHITI_BASE_URL", "http://graphiti:8000")

    app = FastAPI()
    app.include_router(news_graph_routes.router, prefix="/api/v1")
    return TestClient(app), calls


def test_news_graph_heat_rankings_facade_forwards_query_to_graphiti(monkeypatch):
    payload = {
        "period_type": "daily",
        "entity_type": "Enterprise",
        "formula_version": "entity_heat_v1",
        "formula": {"mention_weight": 0.45},
        "items": [{"rank": 1, "entity_name": "腾讯", "heat_score": 98.0}],
    }
    client, calls = _build_client(monkeypatch, payload=payload)

    response = client.get(
        "/api/v1/news-graph/heat-rankings",
        params={"period_type": "daily", "date": "2026-06-22", "entity_type": "Enterprise", "limit": 20},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["entity_name"] == "腾讯"
    assert calls[0]["url"] == "http://graphiti:8000/api/entity-heat-rankings"
    assert calls[0]["params"]["period_type"] == "daily"
    assert calls[0]["params"]["date"] == "2026-06-22"
    assert calls[0]["params"]["entity_type"] == "Enterprise"


def test_news_graph_heat_rankings_facade_reports_graphiti_errors(monkeypatch):
    client, _ = _build_client(monkeypatch, status_code=502)

    response = client.get("/api/v1/news-graph/heat-rankings")

    assert response.status_code == 502
    assert "Graphiti heat rankings query failed" in response.json()["detail"]


def test_news_graph_heat_rankings_calculate_facade_forwards_payload(monkeypatch):
    payload = {"status": "success", "result": {"period_type": "daily", "items": []}}
    client, calls = _build_client(monkeypatch, payload=payload)

    response = client.post(
        "/api/v1/news-graph/heat-rankings/calculate",
        json={
            "period_type": "daily",
            "as_of": "2026-06-22",
            "entity_type": "Enterprise",
            "limit_per_type": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert calls[0]["url"] == "http://graphiti:8000/api/calculate/entity-heat-rankings"
    assert calls[0]["json"]["period_type"] == "daily"
    assert calls[0]["json"]["limit_per_type"] == 20
