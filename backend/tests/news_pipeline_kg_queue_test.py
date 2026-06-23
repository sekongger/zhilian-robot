from pathlib import Path
import importlib
import sys
from types import SimpleNamespace


class _FakeRepo:
    def __init__(self):
        self.news = {
            "_id": "news_1",
            "title": "智链机器人发布机器视觉平台",
            "content": "智链机器人宣布升级机器视觉平台，并与某车企合作。",
            "summary": "机器视觉平台升级",
            "source_name": "rss_36kr",
            "source_url": "https://example.com/news-1",
            "publish_time": "2026-03-12T08:00:00",
            "doc_type": "news",
            "process_status": "pending",
            "source_id": "SRC_NEWS_1",
        }
        self.entities = {}
        self.statements = []
        self.source_updates = []
        self.enqueued = []
        self.db = SimpleNamespace(update_one=lambda *args, **kwargs: None)

    def get_source_news(self, news_id):
        return dict(self.news)

    def update_source_news(self, news_id, payload):
        self.source_updates.append((news_id, dict(payload)))
        self.news.update(dict(payload))

    def upsert_entity(self, entity_doc):
        entity_id = entity_doc["entity_id"]
        self.entities[entity_id] = dict(entity_doc)
        return entity_id

    def create_statement(self, statement_doc):
        statement_id = f"ST_{len(self.statements) + 1}"
        payload = dict(statement_doc)
        payload["statement_id"] = statement_id
        self.statements.append(payload)
        return statement_id

    def enqueue_kg_input(self, queue_doc):
        payload = dict(queue_doc)
        self.enqueued.append(payload)
        return payload.get("queue_id") or "KGQ_1"


class _FakeExtractor:
    def extract(self, content):
        assert "智链机器人" in content
        return {
            "model": "fake-llm",
            "summary": "摘要",
            "entities": {
                "companies": ["智链机器人", "某车企"],
                "technologies": ["机器视觉"],
            },
            "relations": [
                {
                    "subject": "智链机器人",
                    "relation": "合作",
                    "object": "某车企",
                    "confidence": 0.88,
                    "evidence": "双方合作推进产线升级",
                },
                {
                    "subject": "智链机器人",
                    "relation": "研发技术",
                    "object": "机器视觉",
                    "confidence": 0.93,
                    "evidence": "智链机器人升级机器视觉平台",
                },
            ],
        }


class _FakeGraphService:
    def __init__(self):
        self.calls = []

    def save_structured_data(self, entities, relations):
        self.calls.append(("structured", entities, relations))
        return {"success": True}

    def save_analyzed_data(self, entities, relations):
        self.calls.append(("legacy", entities, relations))
        return {"success": True}


def test_process_news_enqueues_kg_input_and_stops_direct_graph_sync(monkeypatch):
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    news_service_module = importlib.import_module("app.news_pipeline.service")

    fake_repo = _FakeRepo()

    svc = news_service_module.NewsPipelineService()
    svc.repo = fake_repo
    svc.extractor = _FakeExtractor()

    result = svc.process_news("news_1")

    assert result["success"] is True
    assert len(fake_repo.enqueued) == 1
    queued = fake_repo.enqueued[0]
    assert queued["kg_name"] == "news_kg"
    assert queued["doc_id"] == fake_repo.news["doc_id"]
    assert queued["source_news_id"] == "news_1"
    assert queued["status"] == "pending"
    assert queued["entities"]["companies"] == ["智链机器人", "某车企"]
    assert len(queued["statements"]) == 2
