from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeMongo:
    def __init__(self):
        self.collections = {
            "entity_instances": [
                {"entity_id": "E1", "canonical_name": "智链机器人", "entity_type": "company", "artifact_id": "KART_1"},
                {"entity_id": "E2", "canonical_name": "某车企", "entity_type": "company", "artifact_id": "KART_1"},
                {"entity_id": "E3", "canonical_name": "另一家公司", "entity_type": "company", "artifact_id": "KART_2"},
            ],
            "inc_statement": [
                {
                    "statement_id": "ST_1",
                    "subject_id": "E1",
                    "object_entity_id": "E2",
                    "predicate_label": "合作",
                    "confidence": 0.9,
                    "artifact_id": "KART_1",
                },
                {
                    "statement_id": "ST_2",
                    "subject_id": "E1",
                    "object_entity_id": "E3",
                    "predicate_label": "投资",
                    "confidence": 0.8,
                    "artifact_id": "KART_2",
                },
            ],
        }

    def find_many(self, collection_name, query=None, limit=0, sort=None):
        query = query or {}
        rows = [dict(row) for row in self.collections.get(collection_name, []) if all(row.get(k) == v for k, v in query.items())]
        return rows[:limit] if limit else rows

    def find_one(self, collection_name, query):
        for row in self.collections.get(collection_name, []):
            if all(row.get(k) == v for k, v in query.items()):
                return dict(row)
        return None


def _build_client():
    from app.api import graph_routes

    app = FastAPI()
    app.include_router(graph_routes.router, prefix="/api/v1")
    return TestClient(app), graph_routes


def test_graph_company_endpoint_filters_by_artifact_id(monkeypatch):
    client, graph_routes = _build_client()
    monkeypatch.setattr(graph_routes, "_get_mongo_conn", lambda: _FakeMongo(), raising=False)

    response = client.get("/api/v1/graph/company/智链机器人", params={"artifact_id": "KART_1"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["nodes"]) == 2
    assert len(payload["edges"]) == 1
    assert payload["edges"][0]["relation"] == "合作"


def test_graph_artifact_companies_endpoint_returns_queryable_company_names(monkeypatch):
    client, graph_routes = _build_client()
    monkeypatch.setattr(graph_routes, "_get_mongo_conn", lambda: _FakeMongo(), raising=False)

    response = client.get("/api/v1/graph/artifacts/KART_1/companies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_id"] == "KART_1"
    assert payload["items"] == ["智链机器人", "某车企"]


def test_graph_artifact_companies_endpoint_filters_low_quality_company_names(monkeypatch):
    client, graph_routes = _build_client()

    class _DirtyMongo(_FakeMongo):
        def __init__(self):
            super().__init__()
            self.collections["entity_instances"] = [
                {"entity_id": "E1", "canonical_name": "目标是将高精度材料建模从实验室转移到晶圆厂", "entity_type": "company", "artifact_id": "KART_DIRTY"},
                {"entity_id": "E2", "canonical_name": "新思科技", "entity_type": "company", "artifact_id": "KART_DIRTY"},
                {"entity_id": "E3", "canonical_name": "配备了智能", "entity_type": "company", "artifact_id": "KART_DIRTY"},
            ]

    monkeypatch.setattr(graph_routes, "_get_mongo_conn", lambda: _DirtyMongo(), raising=False)

    response = client.get("/api/v1/graph/artifacts/KART_DIRTY/companies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == ["新思科技"]


def test_graph_artifact_companies_endpoint_falls_back_to_bridge_batch(monkeypatch, tmp_path):
    client, graph_routes = _build_client()

    class _FallbackMongo(_FakeMongo):
        def __init__(self):
            super().__init__()
            self.collections["entity_instances"] = []
            self.collections["inc_statement"] = []
            self.collections["knowledge_artifacts"] = [
                {"artifact_id": "KART_BATCH", "bridge_run_id": "bridge_batch_1"},
            ]

    batch_dir = tmp_path / "batches"
    batch_dir.mkdir(parents=True)
    (batch_dir / "bridge_batch_1.jsonl").write_text(
        "\n".join(
            [
                '{"doc_id":"DOC_1","title":"华为与智链机器人合作","content":"华为与智链机器人推进具身智能合作"}',
                '{"doc_id":"DOC_2","title":"特斯拉布局机器人","content":"特斯拉研究具身智能控制器"}',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(graph_routes, "_get_mongo_conn", lambda: _FallbackMongo(), raising=False)
    monkeypatch.setattr(graph_routes, "_bridge_batches_dir", lambda: batch_dir, raising=False)

    response = client.get("/api/v1/graph/artifacts/KART_BATCH/companies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == ["华为", "智链机器人", "特斯拉"]


def test_graph_company_endpoint_falls_back_to_bridge_batch_when_artifact_projection_missing(monkeypatch, tmp_path):
    client, graph_routes = _build_client()

    class _FallbackMongo(_FakeMongo):
        def __init__(self):
            super().__init__()
            self.collections["entity_instances"] = []
            self.collections["inc_statement"] = []
            self.collections["knowledge_artifacts"] = [
                {"artifact_id": "KART_BATCH", "bridge_run_id": "bridge_batch_1"},
            ]

    batch_dir = tmp_path / "batches"
    batch_dir.mkdir(parents=True)
    (batch_dir / "bridge_batch_1.jsonl").write_text(
        '{"doc_id":"DOC_1","title":"华为与智链机器人合作","content":"华为与智链机器人推进具身智能合作"}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(graph_routes, "_get_mongo_conn", lambda: _FallbackMongo(), raising=False)
    monkeypatch.setattr(graph_routes, "_bridge_batches_dir", lambda: batch_dir, raising=False)

    response = client.get("/api/v1/graph/company/华为", params={"artifact_id": "KART_BATCH"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["nodes"]) >= 2
    assert any(edge["relation"] == "同批次共现" for edge in payload["edges"])
