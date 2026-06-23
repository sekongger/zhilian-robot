from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeMongo:
    def __init__(self):
        self.collections = {
            "qa_sessions": [],
            "qa_messages": [],
            "qa_citations": [],
            "qa_traces": [],
        }

    def update_one(self, collection_name, query, update, upsert=False):
        rows = self.collections.setdefault(collection_name, [])
        target = None
        for row in rows:
            if all(row.get(k) == v for k, v in query.items()):
                target = row
                break
        if not target and upsert:
            target = dict(query)
            rows.append(target)
        if target is not None:
            target.update(dict(update.get("$set") or {}))

    def insert_one(self, collection_name, document):
        self.collections.setdefault(collection_name, []).append(dict(document))

    def insert_many(self, collection_name, documents):
        for doc in documents:
            self.collections.setdefault(collection_name, []).append(dict(doc))

    def find_one(self, collection_name, query):
        for row in self.collections.get(collection_name, []):
            if all(row.get(k) == v for k, v in query.items()):
                return dict(row)
        return None

    def find_many(self, collection_name, query=None, limit=0, sort=None):
        query = query or {}
        rows = [dict(row) for row in self.collections.get(collection_name, []) if all(row.get(k) == v for k, v in query.items())]
        if limit:
            rows = rows[:limit]
        return rows

    def delete_many(self, collection_name, query):
        kept = []
        removed = 0
        for row in self.collections.get(collection_name, []):
            if all(row.get(k) == v for k, v in query.items()):
                removed += 1
            else:
                kept.append(row)
        self.collections[collection_name] = kept
        return {"deleted_count": removed}


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, expire=None):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)


def test_delete_session_removes_messages_citations_and_trace(monkeypatch):
    from app.api import industry_qa_routes
    from app.api import open_api_routes

    fake_mongo = _FakeMongo()
    fake_redis = _FakeRedis()

    monkeypatch.setattr(industry_qa_routes, "_get_mongo_conn", lambda: fake_mongo)
    monkeypatch.setattr(industry_qa_routes, "_get_redis_conn", lambda: fake_redis)
    monkeypatch.setattr(
        open_api_routes,
        "_run_query",
        lambda **kwargs: {
            "answer": "测试回答",
            "answer_mode": "classic",
            "retrieval_compare": {"strategy": "classic", "classic": {"hit_count": 1}, "openspg": {"hit_count": 0}},
            "knowledge_objects": [],
            "entities": [],
            "evidences": [{"doc_id": "doc_1", "title": "证据", "context_id": "ctx_1", "statement_id": "stmt_1"}],
            "trace_id": "trace_delete_1",
        },
    )
    monkeypatch.setitem(
        open_api_routes._TRACE_STORE,
        "trace_delete_1",
        {"query_plan": {"query": "测试问题"}, "retrieval_hits": []},
    )

    app = FastAPI()
    app.include_router(industry_qa_routes.router, prefix="/api/v1")
    client = TestClient(app)

    create_res = client.post("/api/v1/agent/industry-qa/sessions", json={"title": "待删除会话"})
    session_id = create_res.json()["session_id"]
    chat_res = client.post(
        "/api/v1/agent/industry-qa/chat",
        json={"session_id": session_id, "question": "测试问题", "top_k": 3},
    )
    assert chat_res.status_code == 200

    delete_res = client.delete(f"/api/v1/agent/industry-qa/sessions/{session_id}")
    assert delete_res.status_code == 200
    payload = delete_res.json()
    assert payload["session_id"] == session_id

    list_res = client.get("/api/v1/agent/industry-qa/sessions")
    assert list_res.status_code == 200
    assert all(item["session_id"] != session_id for item in list_res.json()["sessions"])
    assert fake_mongo.collections["qa_messages"] == []
    assert fake_mongo.collections["qa_citations"] == []
    assert fake_mongo.collections["qa_traces"] == []


def test_delete_missing_session_is_idempotent(monkeypatch):
    from app.api import industry_qa_routes

    fake_mongo = _FakeMongo()
    fake_redis = _FakeRedis()

    monkeypatch.setattr(industry_qa_routes, "_get_mongo_conn", lambda: fake_mongo)
    monkeypatch.setattr(industry_qa_routes, "_get_redis_conn", lambda: fake_redis)

    app = FastAPI()
    app.include_router(industry_qa_routes.router, prefix="/api/v1")
    client = TestClient(app)

    delete_res = client.delete("/api/v1/agent/industry-qa/sessions/qa_s_missing")
    assert delete_res.status_code == 200
    payload = delete_res.json()
    assert payload["session_id"] == "qa_s_missing"
    assert payload["deleted"] is False
