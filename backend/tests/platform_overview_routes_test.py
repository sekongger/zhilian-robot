from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_module():
    route_path = Path(__file__).resolve().parents[1] / "app" / "api" / "platform_overview_routes.py"
    spec = spec_from_file_location("platform_overview_routes_under_test", route_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _build_client() -> tuple[TestClient, object]:
    module = _load_module()

    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1")
    return TestClient(app), module


def test_platform_overview_summary_endpoint_returns_lightweight_payload(monkeypatch):
    client, platform_overview_routes = _build_client()

    monkeypatch.setattr(platform_overview_routes, "_build_data_elements_summary", lambda: {"types": [{"doc_type": "news", "status": "connected"}]})
    monkeypatch.setattr(platform_overview_routes, "_build_knowledge_computing_summary", lambda: {"workflow": {"run_id": "wf_test"}, "openks": {"module_count": 19}})
    monkeypatch.setattr(platform_overview_routes, "_build_chain_analysis_summary", lambda: {"graph": {"node_count": 1, "relation_count": 2}})
    monkeypatch.setattr(platform_overview_routes, "_build_agent_apps_summary", lambda: {"headlines": [{"event_id": "evt_1"}]})
    response = client.get("/api/v1/platform/overview")

    assert response.status_code == 200
    payload = response.json()
    assert "data_elements" in payload
    assert "knowledge_computing" in payload
    assert "chain_analysis" in payload
    assert "agent_apps" in payload


def test_platform_overview_stage_filter_returns_single_stage(monkeypatch):
    client, platform_overview_routes = _build_client()

    monkeypatch.setattr(platform_overview_routes, "_build_data_elements_summary", lambda: {"types": [{"doc_type": "news", "status": "connected"}]})
    response = client.get("/api/v1/platform/overview", params={"stage": "data-hub"})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "stage": "data-hub",
        "data_elements": {"types": [{"doc_type": "news", "status": "connected"}]},
    }


def test_data_elements_summary_passes_plain_none_for_knowledge_scope(monkeypatch):
    platform_overview_routes = _load_module()
    calls = []

    def fake_stats(*, doc_type=None, knowledge_scope=None):
        calls.append((doc_type, knowledge_scope))
        return {
            "raw_layer": {"raw_documents": 1},
            "resource_layer": {"inc_document": 2},
            "knowledge_layer": {"entities": 3, "statements": 4},
        }

    monkeypatch.setattr(platform_overview_routes, "_stats_route", fake_stats, raising=False)

    summary = platform_overview_routes._build_data_elements_summary()

    assert calls == [("news", None), ("report", None)]
    assert summary["types"][0]["resource_documents"] == 2


def test_knowledge_computing_summary_falls_back_when_workflow_unavailable(monkeypatch):
    platform_overview_routes = _load_module()

    monkeypatch.setattr(
        platform_overview_routes,
        "_workflow_summary_loader",
        lambda: (_ for _ in ()).throw(PermissionError("workflow state unavailable")),
        raising=False,
    )
    monkeypatch.setattr(
        platform_overview_routes,
        "_openks_overview_loader",
        lambda: {"module_count": 19, "modules_by_stage": {"fact": 10, "cognition": 4, "decision": 5}},
        raising=False,
    )
    monkeypatch.setattr(
        platform_overview_routes,
        "_openks_news_kg_status_loader",
        lambda: (_ for _ in ()).throw(PermissionError("news_kg status unavailable")),
        raising=False,
    )

    summary = platform_overview_routes._build_knowledge_computing_summary()

    assert summary["workflow"]["status"] == "unavailable"
    assert summary["openks"]["module_count"] == 19
    assert summary["news_kg"]["latest_run"]["status"] == "unavailable"


def test_knowledge_computing_summary_includes_news_kg_runtime_status(monkeypatch):
    platform_overview_routes = _load_module()

    monkeypatch.setattr(
        platform_overview_routes,
        "_workflow_summary_loader",
        lambda: {"run_id": "wf_1", "status": "success", "step_statuses": {}},
        raising=False,
    )
    monkeypatch.setattr(
        platform_overview_routes,
        "_openks_overview_loader",
        lambda: {"module_count": 19, "modules_by_stage": {"fact": 10, "cognition": 4, "decision": 5}},
        raising=False,
    )
    monkeypatch.setattr(
        platform_overview_routes,
        "_openks_news_kg_status_loader",
        lambda: {
            "kg_name": "news_kg",
            "queue": {"pending": 6, "running": 1, "failed": 0, "completed": 9},
            "latest_run": {"run_id": "KGRUN_1", "processed": 6, "status": "completed"},
        },
        raising=False,
    )

    summary = platform_overview_routes._build_knowledge_computing_summary()

    assert summary["news_kg"]["queue"]["pending"] == 6
    assert summary["news_kg"]["latest_run"]["run_id"] == "KGRUN_1"


def test_knowledge_computing_summary_includes_traceable_run_artifact_release(monkeypatch):
    platform_overview_routes = _load_module()

    monkeypatch.setattr(
        platform_overview_routes,
        "_workflow_summary_loader",
        lambda: {"run_id": "wf_1", "status": "success", "step_statuses": {}},
        raising=False,
    )
    monkeypatch.setattr(
        platform_overview_routes,
        "_openks_overview_loader",
        lambda: {"module_count": 19, "modules_by_stage": {"fact": 10, "cognition": 4, "decision": 5}},
        raising=False,
    )
    monkeypatch.setattr(
        platform_overview_routes,
        "_openks_news_kg_status_loader",
        lambda: {
            "kg_name": "news_kg",
            "queue": {"pending": 1, "running": 0, "failed": 0, "completed": 2},
            "latest_run": {"run_id": "KGRUN_2", "processed": 2, "status": "completed"},
        },
        raising=False,
    )
    monkeypatch.setattr(
        platform_overview_routes,
        "_knowledge_runtime_snapshot_loader",
        lambda: {
            "latest_run": {"run_id": "KRUN_1", "status": "completed"},
            "latest_artifact": {"artifact_id": "KART_1", "version": "news_kg:20260316120000"},
            "latest_release": {"release_id": "KREL_1", "version": "rel-001"},
        },
        raising=False,
    )

    summary = platform_overview_routes._build_knowledge_computing_summary()

    assert summary["traceability"]["latest_run"]["run_id"] == "KRUN_1"
    assert summary["traceability"]["latest_artifact"]["artifact_id"] == "KART_1"
    assert summary["traceability"]["latest_release"]["release_id"] == "KREL_1"


def test_chain_analysis_summary_uses_sync_wrappers(monkeypatch):
    platform_overview_routes = _load_module()

    monkeypatch.setattr(platform_overview_routes, "_graph_statistics_loader", lambda: {"node_count": 1, "relation_count": 2}, raising=False)
    monkeypatch.setattr(platform_overview_routes, "_momentum_top_loader", lambda: {"entities": [{"name": "测试实体", "current_momentum": 0.5}]}, raising=False)
    monkeypatch.setattr(platform_overview_routes, "_momentum_trend_loader", lambda start_date, end_date: {"trend": [{"date": "2026-03-11", "value": 1}]}, raising=False)

    summary = platform_overview_routes._build_chain_analysis_summary()

    assert summary["graph"]["node_count"] == 1
    assert len(summary["momentum_top"]) == 1
    assert len(summary["momentum_trend"]) == 1
