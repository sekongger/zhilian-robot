from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_client():
    from app.api.resource_hub_routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_resource_hub_summary_endpoint_returns_overview(monkeypatch):
    from app.api import resource_hub_routes

    monkeypatch.setattr(
        resource_hub_routes,
        "_build_resource_hub_summary",
        lambda: {"resources": 2, "raw_documents": 100, "queue_pending": 7},
        raising=False,
    )

    client = _build_client()
    response = client.get("/api/v1/resource-hub/summary")

    assert response.status_code == 200
    assert response.json()["queue_pending"] == 7


def test_resource_hub_resources_endpoint_returns_resource_cards(monkeypatch):
    from app.api import resource_hub_routes

    monkeypatch.setattr(
        resource_hub_routes,
        "_build_resource_cards",
        lambda: [{"resource_key": "news", "label": "资讯"}, {"resource_key": "report", "label": "研报"}],
        raising=False,
    )

    client = _build_client()
    response = client.get("/api/v1/resource-hub/resources")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["resource_key"] == "news"


def test_resource_hub_resource_detail_endpoint_returns_tabs(monkeypatch):
    from app.api import resource_hub_routes

    monkeypatch.setattr(
        resource_hub_routes,
        "_build_resource_detail",
        lambda resource_key: {
            "resource_key": resource_key,
            "tabs": {
                "数据源": [{"name": "RSS"}],
                "数据库表设计": [{"name": "raw_documents"}],
                "数据接入和治理任务": [{"name": "fetch_rss_updates"}],
                "数据质量": {"duplicate_rate": 0.1},
            },
        },
        raising=False,
    )

    client = _build_client()
    response = client.get("/api/v1/resource-hub/resources/news")

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource_key"] == "news"
    assert "数据源" in payload["tabs"]


def test_resource_hub_metric_records_endpoint_maps_news_metrics(monkeypatch):
    from app.api import resource_hub_routes

    async def fake_records(*, layer="", limit=20, offset=0, doc_type=None):
        return {
            "layer": layer,
            "fields": ["doc_id", "title"],
            "data": [{"doc_id": "DOC_1", "title": "测试资讯"}],
            "total": 1,
        }

    monkeypatch.setattr(resource_hub_routes, "_metric_layer_config", lambda resource_key, metric_key: {
        "layer": "knowledge.statements",
        "doc_type": "news",
        "title": "资讯陈述明细",
    })
    monkeypatch.setattr(resource_hub_routes, "_document_records_loader", fake_records, raising=False)

    client = _build_client()
    response = client.get("/api/v1/resource-hub/resources/news/metrics/statements/records", params={"page": 2, "page_size": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource_key"] == "news"
    assert payload["metric_key"] == "statements"
    assert payload["title"] == "资讯陈述明细"
    assert payload["layer"] == "knowledge.statements"
    assert payload["page"] == 2
    assert payload["page_size"] == 5
    assert payload["data"][0]["doc_id"] == "DOC_1"


def test_resource_hub_metric_records_endpoint_rejects_report_until_connected():
    client = _build_client()

    response = client.get("/api/v1/resource-hub/resources/report/metrics/raw_documents/records")

    assert response.status_code == 409
    assert "暂未接入" in response.json()["detail"]
