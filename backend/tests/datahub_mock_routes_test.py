from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_module():
    route_path = Path(__file__).resolve().parents[1] / "app" / "api" / "datahub_mock_routes.py"
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    spec = spec_from_file_location("datahub_mock_routes_under_test", route_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _build_client():
    module = _load_module()

    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1")
    return TestClient(app), module


def test_datahub_mock_headlines_endpoint_returns_items(monkeypatch):
    client, datahub_mock_routes = _build_client()

    monkeypatch.setattr(
        datahub_mock_routes,
        "list_mock_headlines",
        lambda limit=20: [
            {
                "doc_id": "DOC_1",
                "title": "测试头条",
                "summary": "摘要",
                "content": "正文",
                "source_name": "RSSHub",
                "source_url": "https://example.com/1",
                "publish_time": "2026-03-21T10:00:00+08:00",
            }
        ],
        raising=False,
    )

    response = client.get("/api/v1/datahub/mock/headlines")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "rsshub"
    assert payload["contract_version"] == "2026-03-24"
    assert payload["request_spec"]["method"] == "GET"
    assert payload["request_spec"]["path"] == "/api/v1/datahub/mock/headlines"
    assert "doc_id" in payload["response_fields"]
    assert payload["openks_submit_hint"]["path"] == "/api/v1/openks/build-jobs"
    assert payload["items"][0]["doc_id"] == "DOC_1"


def test_datahub_mock_enterprise_endpoint_returns_placeholder():
    client, _ = _build_client()
    response = client.get("/api/v1/datahub/mock/enterprise")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["contract_status"] == "defined_not_connected"
    assert "后续接入" in payload["message"]


def test_datahub_mock_batch_endpoint_returns_ready_batch(monkeypatch):
    client, datahub_mock_routes = _build_client()

    monkeypatch.setattr(
        datahub_mock_routes,
        "create_headlines_batch",
        lambda source="rsshub", limit=20: {
            "batch_id": "BATCH_001",
            "source": source,
            "raw_count": 2,
            "normalized_count": 2,
            "manifest_uri": "file:///tmp/BATCH_001.jsonl",
            "status": "ready",
        },
        raising=False,
    )

    response = client.post("/api/v1/datahub/mock/batches", json={"source": "rsshub", "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload["batch_id"] == "BATCH_001"
    assert payload["status"] == "ready"
