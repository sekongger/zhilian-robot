from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_client() -> tuple[TestClient, object]:
    route_path = Path(__file__).resolve().parents[1] / "app" / "api" / "openks_routes.py"
    spec = spec_from_file_location("openks_routes_under_test", route_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1")
    return TestClient(app), module


def test_openks_modules_endpoint_returns_discovered_modules():
    client, _ = _build_client()

    response = client.get("/api/v1/openks/modules")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 4
    assert [item["name"] for item in payload["modules"]] == ["base_kg", "event_kg", "industry_network", "news_kg"]


def test_openks_overview_exposes_main_chain_contract_and_governance():
    client, _ = _build_client()

    response = client.get("/api/v1/openks/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["main_chain"]["runtime_profile"] == "kag_openspg"
    assert payload["main_chain"]["status"] == "production"
    assert payload["integration_boundary"]["datahub"]["status"] == "contract_only"
    assert payload["integration_boundary"]["graphiti"]["status"] == "contract_only"
    assert "upsertVertex" in payload["industry_graph_governance"]["openspg_capabilities"]
    assert payload["industry_graph_governance"]["audit_checks"]
    assert len(payload["production_steps"]) == 5
    assert payload["production_steps"][0]["key"] == "workflow"
    assert payload["production_steps"][1]["function_entry"]
    assert payload["production_steps"][2]["input_fields"]
    assert payload["production_steps"][3]["output_fields"]


def test_openks_modules_endpoint_supports_include_hidden_for_full_registry():
    client, _ = _build_client()

    response = client.get("/api/v1/openks/modules", params={"include_hidden": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 21
    assert any(item["name"] == "technology_foresight" for item in payload["modules"])
    assert any(item["name"] == "event_kg" for item in payload["modules"])
    assert any(item["name"] == "industry_network" for item in payload["modules"])


def test_openks_modules_endpoint_supports_stage_filter():
    client, _ = _build_client()

    response = client.get("/api/v1/openks/modules", params={"stage": "cognition"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["modules"] == []


def test_openks_module_detail_includes_runtime_flags():
    client, _ = _build_client()

    response = client.get("/api/v1/openks/modules/news_kg")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "news_kg"
    assert payload["has_schema"] is True
    assert payload["has_builder"] is True
    assert payload["schema_preview"]["entities"]
    assert any(item["name"] == "NewsDocument" for item in payload["schema_preview"]["entities"])
    assert any("source" in item and "target" in item for item in payload["schema_preview"]["relations"])


def test_openks_news_kg_build_endpoint_returns_build_summary(monkeypatch):
    client, openks_routes = _build_client()

    monkeypatch.setattr(
        openks_routes,
        "build_news_kg",
        lambda limit=20: {"kg_name": "news_kg", "processed": 2, "statements_written": 4},
        raising=False,
    )

    response = client.post("/api/v1/openks/news-kg/build", params={"limit": 20})

    assert response.status_code == 200
    assert response.json()["processed"] == 2


def test_openks_news_kg_status_endpoint_returns_queue_and_run_summary(monkeypatch):
    client, openks_routes = _build_client()

    monkeypatch.setattr(
        openks_routes,
        "get_news_kg_status",
        lambda: {
            "kg_name": "news_kg",
            "queue": {"pending": 3, "running": 1, "failed": 0, "completed": 5},
            "latest_run": {"run_id": "kg_run_1", "status": "completed"},
        },
        raising=False,
    )

    response = client.get("/api/v1/openks/news-kg/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["queue"]["pending"] == 3
    assert payload["latest_run"]["run_id"] == "kg_run_1"


def test_openks_news_kg_query_endpoint_delegates_to_solver(monkeypatch):
    client, openks_routes = _build_client()

    monkeypatch.setattr(
        openks_routes,
        "query_news_kg",
        lambda query: {"query": query, "results": [{"statement_id": "ST_1"}]},
        raising=False,
    )

    response = client.post("/api/v1/openks/news-kg/query", json={"keyword": "智链机器人"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["keyword"] == "智链机器人"
    assert payload["results"][0]["statement_id"] == "ST_1"


def test_openks_datahub_headlines_endpoint_returns_mock_headlines(monkeypatch):
    client, openks_routes = _build_client()

    monkeypatch.setattr(
        openks_routes,
        "get_datahub_headlines",
        lambda hours=24, limit=20: {
            "datahub": "mock",
            "data_source": "news_pipeline.source_news",
            "headlines": [{"event_id": "evt_1", "headline_title": "示例头条"}],
            "stats": {"event_count": 1},
        },
        raising=False,
    )

    response = client.get("/api/v1/openks/datahub/headlines", params={"hours": 12, "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["datahub"] == "mock"
    assert payload["headlines"][0]["event_id"] == "evt_1"


def test_openks_datahub_enterprise_endpoint_returns_placeholder(monkeypatch):
    client, openks_routes = _build_client()

    monkeypatch.setattr(
        openks_routes,
        "get_datahub_enterprise",
        lambda name="": {"datahub": "mock", "enterprise": {"enterprise_name": name or "示例企业", "status": "placeholder"}},
        raising=False,
    )

    response = client.get("/api/v1/openks/datahub/enterprise", params={"name": "智链机器人"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["enterprise"]["enterprise_name"] == "智链机器人"
    assert payload["enterprise"]["status"] == "placeholder"


def test_openks_build_jobs_submit_and_query(monkeypatch):
    client, openks_routes = _build_client()
    store = {}

    def fake_submit_build_job(payload):
        job = {
            "job_id": "KJOB_1",
            "module_name": payload.get("module_name", "news_kg"),
            "status": "queued",
            "request": dict(payload),
        }
        store[job["job_id"]] = job
        return job

    monkeypatch.setattr(openks_routes, "submit_build_job", fake_submit_build_job, raising=False)
    monkeypatch.setattr(openks_routes, "list_build_jobs", lambda status=None, limit=20: {"items": list(store.values()), "total": len(store)}, raising=False)
    monkeypatch.setattr(openks_routes, "get_build_job", lambda job_id: store.get(job_id), raising=False)
    monkeypatch.setattr(
        openks_routes,
        "get_build_job_result",
        lambda job_id: {
            "job_id": job_id,
            "status": "completed",
            "run_id": "KRUN_1",
            "artifact_id": "KART_1",
            "release_id": "KREL_1",
            "graph_stats": {"vertices": 10, "edges": 20},
        } if job_id in store else None,
        raising=False,
    )

    submit_res = client.post("/api/v1/openks/build-jobs", json={"module_name": "news_kg", "target": "openks"})
    assert submit_res.status_code == 200
    assert submit_res.json()["job_id"] == "KJOB_1"

    list_res = client.get("/api/v1/openks/build-jobs")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    get_res = client.get("/api/v1/openks/build-jobs/KJOB_1")
    assert get_res.status_code == 200
    assert get_res.json()["module_name"] == "news_kg"

    result_res = client.get("/api/v1/openks/build-jobs/KJOB_1/result")
    assert result_res.status_code == 200
    assert result_res.json()["artifact_id"] == "KART_1"


def test_openks_graph_summary_sample_and_evidence_endpoints(monkeypatch):
    client, openks_routes = _build_client()

    monkeypatch.setattr(
        openks_routes,
        "get_graph_summary",
        lambda artifact_id="", job_id="": {
            "artifact_id": artifact_id or "KART_1",
            "release_id": "KREL_1",
            "vertex_count": 12,
            "edge_count": 24,
            "company_count": 4,
            "event_count": 3,
            "document_count": 5,
        },
        raising=False,
    )
    monkeypatch.setattr(
        openks_routes,
        "get_graph_sample",
        lambda artifact_id="", job_id="": {
            "artifact_id": artifact_id or "KART_1",
            "nodes": [{"id": "company::1", "name": "华为", "type": "Company"}],
            "edges": [{"source": "company::1", "target": "event::1", "label": "involves"}],
        },
        raising=False,
    )
    monkeypatch.setattr(
        openks_routes,
        "get_graph_evidence",
        lambda artifact_id="", job_id="", limit=20: {
            "artifact_id": artifact_id or "KART_1",
            "items": [{"doc_id": "DOC_1", "title": "测试头条", "source_url": "https://example.com/1"}],
            "total": 1,
        },
        raising=False,
    )

    summary_res = client.get("/api/v1/openks/graph/summary", params={"artifact_id": "KART_1"})
    sample_res = client.get("/api/v1/openks/graph/sample", params={"artifact_id": "KART_1"})
    evidence_res = client.get("/api/v1/openks/graph/evidence", params={"artifact_id": "KART_1"})

    assert summary_res.status_code == 200
    assert summary_res.json()["vertex_count"] == 12
    assert sample_res.status_code == 200
    assert sample_res.json()["nodes"][0]["name"] == "华为"
    assert evidence_res.status_code == 200
    assert evidence_res.json()["items"][0]["doc_id"] == "DOC_1"
