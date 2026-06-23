from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_module():
    route_path = Path(__file__).resolve().parents[1] / "app" / "api" / "knowledge_runtime_routes.py"
    spec = spec_from_file_location("knowledge_runtime_routes_under_test", route_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _build_client():
    module = _load_module()
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1")
    return TestClient(app), module


class _FakeMongo:
    def __init__(self):
        self.rows = {
            "knowledge_runs": [
                {
                    "_id": "KRUN001",
                    "run_id": "KRUN001",
                    "kg_name": "news_kg",
                    "status": "completed",
                    "runtime_profile": "kag_openspg",
                    "artifact_ref": "KART001",
                    "created_at": "2026-03-16T10:00:00",
                }
            ],
            "knowledge_artifacts": [
                {
                    "_id": "KART001",
                    "artifact_id": "KART001",
                    "kg_name": "news_kg",
                    "run_id": "KRUN001",
                    "runtime_profile": "kag_openspg",
                    "version": "news_kg:20260316100000",
                    "entity_count": 3,
                    "statement_count": 2,
                    "created_at": "2026-03-16T10:00:10",
                }
            ],
            "service_releases": [],
            "kg_build_runs": [],
            "entity_instances": [],
            "inc_statement": [],
            "inc_context": [],
        }

    def find_many(self, collection_name, query=None, limit=0, sort=None):
        items = list(self.rows.get(collection_name, []))
        query = query or {}
        for key, value in query.items():
            items = [item for item in items if item.get(key) == value]
        if limit:
            items = items[:limit]
        return items

    def find_one(self, collection_name, query):
        for item in self.rows.get(collection_name, []):
            if all(item.get(key) == value for key, value in query.items()):
                return item
        return None

    def update_one(self, collection_name, query, update, upsert=False):
        document = dict(update.get("$set", {}))
        existing = self.find_one(collection_name, query)
        if existing:
            existing.update(document)
            return
        if upsert:
            merged = dict(query)
            merged.update(document)
            self.rows.setdefault(collection_name, []).append(merged)

    def get_collection(self, collection_name):
        rows = self.rows.setdefault(collection_name, [])

        class _Collection:
            def __init__(self, target_rows):
                self.rows = target_rows

            def update_many(self, query, update):
                for item in self.rows:
                    if all(item.get(key) == value for key, value in query.items()):
                        item.update(dict(update.get("$set", {})))

        return _Collection(rows)


def test_runs_endpoint_returns_traceable_news_run(monkeypatch):
    client, module = _build_client()
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: _FakeMongo(), raising=False)

    response = client.get("/api/v1/runs", params={"kg_name": "news_kg"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["run_id"] == "KRUN001"


def test_runtime_endpoints_support_runtime_profile_filter(monkeypatch):
    client, module = _build_client()
    fake_mongo = _FakeMongo()
    fake_mongo.rows["knowledge_runs"].append(
        {
            "run_id": "KRUN_LEGACY",
            "kg_name": "news_kg",
            "status": "completed",
            "runtime_profile": "openks_direct",
            "artifact_ref": "KART_LEGACY",
            "created_at": "2026-03-16T09:00:00",
        }
    )
    fake_mongo.rows["knowledge_artifacts"].append(
        {
            "artifact_id": "KART_LEGACY",
            "kg_name": "news_kg",
            "run_id": "KRUN_LEGACY",
            "runtime_profile": "openks_direct",
            "version": "news_kg:legacy",
            "created_at": "2026-03-16T09:00:10",
        }
    )
    fake_mongo.rows["service_releases"] = [
        {
            "release_id": "KREL001",
            "artifact_id": "KART001",
            "kg_name": "news_kg",
            "runtime_profile": "kag_openspg",
            "version": "rel-001",
            "status": "draft",
            "created_at": "2026-03-16T10:05:00",
        },
        {
            "release_id": "KREL_LEGACY",
            "artifact_id": "KART_LEGACY",
            "kg_name": "news_kg",
            "runtime_profile": "openks_direct",
            "version": "rel-legacy",
            "status": "active",
            "created_at": "2026-03-16T09:05:00",
        },
    ]
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: fake_mongo, raising=False)

    runs_res = client.get("/api/v1/runs", params={"kg_name": "news_kg", "runtime_profile": "kag_openspg"})
    artifacts_res = client.get("/api/v1/artifacts", params={"kg_name": "news_kg", "runtime_profile": "kag_openspg"})
    releases_res = client.get("/api/v1/releases", params={"kg_name": "news_kg", "runtime_profile": "kag_openspg"})

    assert runs_res.status_code == 200
    assert artifacts_res.status_code == 200
    assert releases_res.status_code == 200
    assert runs_res.json()["total"] == 1
    assert runs_res.json()["items"][0]["runtime_profile"] == "kag_openspg"
    assert artifacts_res.json()["items"][0]["runtime_profile"] == "kag_openspg"
    assert releases_res.json()["items"][0]["runtime_profile"] == "kag_openspg"
    assert releases_res.json()["total"] == 1


def test_run_detail_includes_artifact_and_release_links(monkeypatch):
    client, module = _build_client()
    fake_mongo = _FakeMongo()
    fake_mongo.rows["service_releases"] = [
        {
            "release_id": "KREL001",
            "artifact_id": "KART001",
            "kg_name": "news_kg",
            "version": "rel-001",
            "status": "active",
        }
    ]
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: fake_mongo, raising=False)

    response = client.get("/api/v1/runs/KRUN001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "KRUN001"
    assert payload["artifact"]["artifact_id"] == "KART001"
    assert payload["releases"][0]["release_id"] == "KREL001"


def test_artifacts_endpoint_returns_traceable_artifact(monkeypatch):
    client, module = _build_client()
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: _FakeMongo(), raising=False)

    response = client.get("/api/v1/artifacts", params={"kg_name": "news_kg"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["artifact_id"] == "KART001"


def test_create_release_from_artifact(monkeypatch):
    client, module = _build_client()
    fake_mongo = _FakeMongo()
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: fake_mongo, raising=False)

    response = client.post(
        "/api/v1/releases",
        json={"artifact_id": "KART001", "version": "rel-001", "status": "released"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_id"] == "KART001"
    assert payload["version"] == "rel-001"
    assert fake_mongo.rows["service_releases"][0]["artifact_id"] == "KART001"


def test_activate_release_switches_current_version(monkeypatch):
    client, module = _build_client()
    fake_mongo = _FakeMongo()
    fake_mongo.rows["service_releases"] = [
        {
            "release_id": "KREL_old",
            "artifact_id": "KART000",
            "kg_name": "news_kg",
            "version": "rel-old",
            "status": "active",
        },
        {
            "release_id": "KREL_new",
            "artifact_id": "KART001",
            "kg_name": "news_kg",
            "version": "rel-new",
            "status": "released",
        },
    ]
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: fake_mongo, raising=False)

    response = client.post(
        "/api/v1/releases/KREL_new/activate",
        json={"operator": "alice", "comment": "切换主版本"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["release_id"] == "KREL_new"
    assert payload["status"] == "active"
    old_release = next(item for item in fake_mongo.rows["service_releases"] if item["release_id"] == "KREL_old")
    new_release = next(item for item in fake_mongo.rows["service_releases"] if item["release_id"] == "KREL_new")
    assert old_release["status"] == "superseded"
    assert new_release["status"] == "active"
    assert new_release["state_history"][-1]["operator"] == "alice"


def test_runs_endpoint_bootstraps_traceable_objects_from_latest_build_run(monkeypatch):
    client, module = _build_client()
    fake_mongo = _FakeMongo()
    fake_mongo.rows["knowledge_runs"] = []
    fake_mongo.rows["knowledge_artifacts"] = []
    fake_mongo.rows["service_releases"] = []
    fake_mongo.rows["kg_build_runs"] = [
        {
            "run_id": "KGRUN001",
            "kg_name": "news_kg",
            "status": "completed",
            "started_at": "2026-03-16T10:00:00",
            "finished_at": "2026-03-16T10:01:00",
            "entities_written": 3,
            "statements_written": 2,
            "contexts_written": 2,
            "graph_relations_written": 2,
            "created_at": "2026-03-16T10:01:00",
        }
    ]
    fake_mongo.rows["entity_instances"] = [{"entity_id": "E1", "source_kg": "news_kg"}]
    fake_mongo.rows["inc_statement"] = [{"statement_id": "ST_1", "source_kg": "news_kg"}]
    fake_mongo.rows["inc_context"] = [{"context_id": "CTX_1", "source_kg": "news_kg"}]
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: fake_mongo, raising=False)

    response = client.get("/api/v1/runs", params={"kg_name": "news_kg"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["status"] == "completed"
    assert len(fake_mongo.rows["knowledge_artifacts"]) == 1
    assert len(fake_mongo.rows["service_releases"]) == 1
    assert fake_mongo.rows["service_releases"][0]["status"] == "active"
    assert fake_mongo.rows["entity_instances"][0]["artifact_id"]


def test_submit_review_and_approve_release_updates_status_history(monkeypatch):
    client, module = _build_client()
    fake_mongo = _FakeMongo()
    fake_mongo.rows["service_releases"] = [
        {
            "release_id": "KREL_review",
            "artifact_id": "KART001",
            "kg_name": "news_kg",
            "version": "rel-review",
            "status": "draft",
            "state_history": [],
        }
    ]
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: fake_mongo, raising=False)

    review_res = client.post(
        "/api/v1/releases/KREL_review/submit-review",
        json={"operator": "alice", "comment": "请进入审核"},
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "review_pending"

    approve_res = client.post(
        "/api/v1/releases/KREL_review/approve",
        json={"operator": "bob", "comment": "审核通过"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "released"

    release = fake_mongo.find_one("service_releases", {"release_id": "KREL_review"})
    assert [item["to_status"] for item in release["state_history"]] == ["review_pending", "released"]
    assert release["state_history"][0]["operator"] == "alice"
    assert release["state_history"][0]["comment"] == "请进入审核"
    assert release["state_history"][1]["operator"] == "bob"
    assert release["state_history"][1]["comment"] == "审核通过"


def test_rollback_release_reactivates_target_release(monkeypatch):
    client, module = _build_client()
    fake_mongo = _FakeMongo()
    fake_mongo.rows["service_releases"] = [
        {
            "release_id": "KREL_active",
            "artifact_id": "KART002",
            "kg_name": "news_kg",
            "version": "rel-active",
            "status": "active",
            "state_history": [],
        },
        {
            "release_id": "KREL_prev",
            "artifact_id": "KART001",
            "kg_name": "news_kg",
            "version": "rel-prev",
            "status": "superseded",
            "state_history": [],
        },
    ]
    monkeypatch.setattr(module, "_get_mongo_conn", lambda: fake_mongo, raising=False)

    response = client.post(
        "/api/v1/releases/KREL_active/rollback",
        json={"target_release_id": "KREL_prev", "operator": "admin", "comment": "回滚到上一版本"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current"]["release_id"] == "KREL_prev"
    assert payload["current"]["status"] == "active"
    rolled_back = fake_mongo.find_one("service_releases", {"release_id": "KREL_active"})
    previous = fake_mongo.find_one("service_releases", {"release_id": "KREL_prev"})
    assert rolled_back["status"] == "rolled_back"
    assert previous["status"] == "active"
    assert rolled_back["state_history"][0]["operator"] == "admin"
    assert previous["state_history"][-1]["comment"] == "回滚到上一版本"
