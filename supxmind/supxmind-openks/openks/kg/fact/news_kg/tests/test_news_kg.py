from pathlib import Path
import sys

openks_root = Path(__file__).resolve().parents[5]
if str(openks_root) not in sys.path:
    sys.path.insert(0, str(openks_root))

from openks.kg.fact.news_kg import (
    NewsKgBuilder,
    NewsKgReasoner,
    NewsKgSchema,
    NewsKgSolver,
)


def test_news_kg_scaffold_runtime_contract():
    schema = NewsKgSchema()
    builder = NewsKgBuilder()
    reasoner = NewsKgReasoner()
    solver = NewsKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([])["processed"] == 0
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}


class _FakeMongoAdapter:
    def __init__(self):
        self.entities = []
        self.statements = []
        self.contexts = []
        self.runs = []
        self.knowledge_runs = []
        self.knowledge_artifacts = []

    def upsert_entity(self, payload):
        self.entities.append(dict(payload))
        return payload["entity_id"]

    def upsert_statement(self, payload):
        self.statements.append(dict(payload))
        return payload["statement_id"]

    def upsert_context(self, payload):
        self.contexts.append(dict(payload))
        return payload["context_id"]

    def record_build_run(self, payload):
        self.runs.append(dict(payload))
        return payload["run_id"]

    def record_knowledge_run(self, payload):
        self.knowledge_runs.append(dict(payload))
        return payload["run_id"]

    def update_knowledge_run(self, run_id, fields):
        for item in self.knowledge_runs:
            if item.get("run_id") == run_id:
                item.update(dict(fields))
                return run_id
        raise AssertionError(f"unknown knowledge run: {run_id}")

    def record_knowledge_artifact(self, payload):
        self.knowledge_artifacts.append(dict(payload))
        return payload["artifact_id"]


class _FakeGraphAdapter:
    def __init__(self):
        self.saved = []

    def save_structured_data(self, entities, relations):
        self.saved.append({"entities": list(entities), "relations": list(relations)})
        return {"success": True}


class _FakeCanonicalizer:
    def canonicalize_entity(self, entity_name, entity_type):
        return f"CANONICAL_{entity_type}_{entity_name}"


def test_news_kg_builder_normalizes_queue_records_and_persists_standardized_facts():
    fake_mongo = _FakeMongoAdapter()
    builder = NewsKgBuilder(
        mongo_adapter=fake_mongo,
        graph_adapter=_FakeGraphAdapter(),
        canonicalizer=_FakeCanonicalizer(),
    )

    result = builder.build(
        [
            {
                "queue_id": "KGQ_1",
                "kg_name": "news_kg",
                "doc_id": "doc:news_1",
                "source_news_id": "news_1",
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
                "metadata": {
                    "publish_time": "2026-03-12T08:00:00",
                    "source_name": "rss_36kr",
                    "source_url": "https://example.com/news-1",
                },
            }
        ]
    )

    assert result["processed"] == 1
    assert result["entities_written"] == 3
    assert result["statements_written"] == 2
    assert result["contexts_written"] == 2
    assert result["run_id"].startswith("KRUN")
    assert result["artifact_id"].startswith("KART")
    assert result["artifact_version"].startswith("news_kg:")
    assert len(fake_mongo.knowledge_runs) == 1
    assert len(fake_mongo.knowledge_artifacts) == 1
    assert fake_mongo.knowledge_runs[0]["artifact_ref"] == result["artifact_id"]
    assert fake_mongo.knowledge_artifacts[0]["run_id"] == result["run_id"]
    assert all(item["run_id"] == result["run_id"] for item in fake_mongo.entities)
    assert all(item["artifact_id"] == result["artifact_id"] for item in fake_mongo.entities)
    assert all(item["run_id"] == result["run_id"] for item in fake_mongo.statements)
    assert all(item["artifact_id"] == result["artifact_id"] for item in fake_mongo.statements)
    assert all(item["run_id"] == result["run_id"] for item in fake_mongo.contexts)
    assert all(item["artifact_id"] == result["artifact_id"] for item in fake_mongo.contexts)
