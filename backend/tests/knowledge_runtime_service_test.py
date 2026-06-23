from app.services import knowledge_runtime_service


class _FakeMongo:
    def __init__(self):
        self.rows = {
            "knowledge_runs": [],
            "knowledge_artifacts": [],
            "service_releases": [],
        }

    def find_many(self, collection_name, query=None, limit=0, sort=None):
        items = list(self.rows.get(collection_name, []))
        query = query or {}
        for key, value in query.items():
            items = [item for item in items if item.get(key) == value]
        if sort:
            for field, direction in reversed(sort):
                items.sort(key=lambda item: item.get(field) or "", reverse=direction < 0)
        if limit:
            items = items[:limit]
        return items

    def find_one(self, collection_name, query):
        for item in self.rows.get(collection_name, []):
            if all(item.get(key) == value for key, value in query.items()):
                return item
        return None

    def update_one(self, collection_name, query, update, upsert=False):
        payload = dict(update.get("$set", {}))
        existing = self.find_one(collection_name, query)
        if existing:
            existing.update(payload)
            return
        if upsert:
            document = dict(query)
            document.update(payload)
            self.rows.setdefault(collection_name, []).append(document)


def test_register_workflow_runtime_binding_creates_draft_release(monkeypatch):
    fake_mongo = _FakeMongo()
    monkeypatch.setattr(knowledge_runtime_service, "_get_mongo_conn", lambda: fake_mongo)

    payload = knowledge_runtime_service.register_workflow_runtime_binding(
        runtime_profile="kag_openspg",
        kg_name="news_kg",
        project_id=1,
        workflow_run_id="wf_001",
        bridge_run={
            "run_id": "extract_001",
            "run_time": "2026-03-17T12:00:00",
            "export_count": 9,
        },
        builder_submit_result={"job_id": 1001},
        graph_materialize_result={"status": "success", "vertices": 18, "edges": 12},
    )

    assert payload["run"]["runtime_profile"] == "kag_openspg"
    assert payload["artifact"]["status"] == "ready"
    assert payload["release"]["status"] == "draft"
    assert payload["release"]["artifact_id"] == payload["artifact"]["artifact_id"]
    assert payload["release"]["version"] == payload["artifact"]["version"]
    assert payload["release"]["state_history"][0]["action"] == "create"
    assert payload["release"]["state_history"][0]["to_status"] == "draft"
