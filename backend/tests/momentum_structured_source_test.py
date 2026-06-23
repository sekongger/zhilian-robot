from pathlib import Path
import importlib
import sys


class _FakeMongo:
    def __init__(self):
        self.collections = {
            "inc_statement": [],
            "entity_instances": [],
            "document_instances": [],
            "canonical_entities": [],
        }

    def find_one(self, collection_name, query):
        for row in self.collections.get(collection_name, []):
            matched = True
            for key, value in query.items():
                if row.get(key) != value:
                    matched = False
                    break
            if matched:
                return dict(row)
        return None

    def find_many(self, collection_name, query=None, limit=0, sort=None):
        rows = [dict(item) for item in self.collections.get(collection_name, [])]
        if limit and limit > 0:
            rows = rows[:limit]
        return rows


def test_get_top_momentum_entities_uses_structured_statements_when_available(monkeypatch):
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    mongo_module = importlib.import_module("app.database.mongodb")
    momentum_module = importlib.import_module("app.analytics.momentum")

    fake_mongo = _FakeMongo()
    fake_mongo.collections["entity_instances"] = [
        {
            "_id": "CANONICAL_company_1",
            "entity_id": "CANONICAL_company_1",
            "canonical_name": "智链机器人",
            "entity_type": "company",
            "source_kg": "news_kg",
        },
        {
            "_id": "CANONICAL_technology_1",
            "entity_id": "CANONICAL_technology_1",
            "canonical_name": "机器视觉",
            "entity_type": "technology",
            "source_kg": "news_kg",
        },
    ]
    fake_mongo.collections["inc_statement"] = [
        {
            "_id": "ST_1",
            "statement_id": "ST_1",
            "subject_id": "CANONICAL_company_1",
            "object_entity_id": "CANONICAL_technology_1",
            "context_time_value": "2026-03-12",
            "confidence": 0.95,
            "source_kg": "news_kg",
        },
        {
            "_id": "ST_2",
            "statement_id": "ST_2",
            "subject_id": "CANONICAL_company_1",
            "object_entity_id": "CANONICAL_technology_1",
            "context_time_value": "2026-03-11",
            "confidence": 0.90,
            "source_kg": "news_kg",
        },
    ]

    monkeypatch.setattr(mongo_module, "mongodb_conn", fake_mongo)

    engine = momentum_module.MomentumEngine()
    results = engine.get_top_momentum_entities(limit=5)

    assert results
    assert results[0]["names"][0] == "智链机器人"
    assert results[0]["current_momentum"] > 0
