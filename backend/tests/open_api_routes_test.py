from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeMongo:
    def __init__(self):
        self.collections = {
            'open_api_traces': [],
            'news_pipeline_entity_instances': [],
            'news_pipeline_statements': [],
            'news_pipeline_statement_evidences': [],
        }

    def update_one(self, collection_name, query, update, upsert=False):
        rows = self.collections.setdefault(collection_name, [])
        target = None
        for row in rows:
            if all(row.get(k) == v for k, v in query.items()):
                target = row
                break
        if not target:
            if not upsert:
                return None
            target = dict(query)
            rows.append(target)
        target.update(dict(update.get('$set') or {}))
        return None

    def find_one(self, collection_name, query):
        for row in self.collections.get(collection_name, []):
            if all(row.get(k) == v for k, v in query.items()):
                return dict(row)
        return None

    def find_many(self, collection_name, query=None, limit=0, sort=None):
        query = query or {}
        rows = []
        for row in self.collections.get(collection_name, []):
            if all(row.get(k) == v for k, v in query.items()):
                rows.append(dict(row))
        if sort:
            for field, direction in reversed(sort):
                rows.sort(key=lambda item: str(item.get(field) or ''), reverse=int(direction) < 0)
        if limit and limit > 0:
            rows = rows[:limit]
        return rows


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, expire=None):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)


def _build_client() -> TestClient:
    from app.api.open_api_routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_open_headlines_endpoint_returns_payload(monkeypatch):
    from app.api import open_api_routes

    def fake_query_headlines(hours: int, top_n: int, allow_demo_fallback: bool):
        return {
            "headlines": [
                {
                    "event_id": "evt_1",
                    "headline_title": "测试产业事件",
                    "headline_score": 1.23,
                    "companies": ["智链机器人"],
                    "latest_publish_time": "2026-03-04T00:00:00+00:00",
                }
            ],
            "stats": {"event_count": 1},
            "meta": {"data_source": "demo"},
        }

    monkeypatch.setattr(open_api_routes, "_query_headlines", fake_query_headlines)

    client = _build_client()
    res = client.get("/api/v1/open/applications/headlines", params={"hours": 12, "top_n": 5})

    assert res.status_code == 200
    payload = res.json()
    assert "headlines" in payload
    assert payload["meta"]["access_scope"] == "open"
    assert payload["meta"]["hours"] == 12
    assert payload["meta"]["top_n"] == 5


def test_open_knowledge_query_returns_trace_and_evidence(monkeypatch):
    from app.api import open_api_routes

    def fake_query_headlines(hours: int, top_n: int, allow_demo_fallback: bool):
        return {
            "headlines": [
                {
                    "event_id": "evt_1",
                    "headline_title": "智链机器人合作事件",
                    "headline_score": 1.1,
                    "companies": ["智链机器人", "某车企"],
                    "latest_publish_time": "2026-03-04T00:00:00+00:00",
                }
            ],
            "stats": {"event_count": 1},
            "meta": {"data_source": "demo"},
        }

    def fake_get_event_detail(event_id: str, hours: int, allow_demo_fallback: bool):
        assert event_id == "evt_1"
        return {
            "event_id": event_id,
            "evidence_news": [
                {
                    "news_id": "n1",
                    "title": "智链机器人与车企合作",
                    "source_name": "rss_36kr",
                    "url": "https://example.com/n1",
                    "publish_time": "2026-03-04T00:00:00+00:00",
                    "snippet": "合作推进机器人自动化",
                }
            ],
        }

    monkeypatch.setattr(open_api_routes, "_query_headlines", fake_query_headlines)
    monkeypatch.setattr(open_api_routes, "_get_event_detail", fake_get_event_detail)
    monkeypatch.setattr(open_api_routes, "_get_redis_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_stream_query_answer", lambda context: iter(["测试回答"]))
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "empty",
            "mode": "offline",
            "graph_labels": [],
            "reason_candidates": [],
            "query_plan": [],
            "search_queries": [],
            "search_checks": [],
            "graph_query_count": 0,
            "graph_hit_count": 0,
            "hits": [],
        },
        raising=False,
    )

    client = _build_client()
    res = client.post(
        "/api/v1/open/knowledge/query",
        json={
            "query": "本周机器人产业链重点动态",
            "top_k": 5,
            "filters": {"hours": 24},
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["answer"]
    assert len(payload["knowledge_objects"]) == 1
    assert len(payload["evidences"]) == 1
    assert payload["trace_id"]


def test_open_knowledge_query_filters_structured_statements_by_artifact_id(monkeypatch):
    from app.api import open_api_routes

    fake_mongo = _FakeMongo()
    fake_mongo.collections['entity_instances'] = [
        {
            'entity_id': 'CANONICAL_company_智链机器人',
            'canonical_name': '智链机器人',
            'entity_type': 'company',
            'artifact_id': 'KART_1',
        },
        {
            'entity_id': 'CANONICAL_company_某车企',
            'canonical_name': '某车企',
            'entity_type': 'company',
            'artifact_id': 'KART_1',
        },
    ]
    fake_mongo.collections['inc_statement'] = [
        {
            'statement_id': 'ST_1',
            'subject_id': 'CANONICAL_company_智链机器人',
            'predicate_id': 'rel:collaborates_with',
            'predicate_label': '合作',
            'object_entity_id': 'CANONICAL_company_某车企',
            'doc_id': 'doc_1',
            'source_kg': 'news_kg',
            'artifact_id': 'KART_1',
            'confidence': 0.9,
            'evidence_text': '双方合作推进产线升级',
        },
        {
            'statement_id': 'ST_2',
            'subject_id': 'CANONICAL_company_智链机器人',
            'predicate_id': 'rel:collaborates_with',
            'predicate_label': '合作',
            'object_entity_id': 'CANONICAL_company_某车企',
            'doc_id': 'doc_2',
            'source_kg': 'news_kg',
            'artifact_id': 'KART_2',
            'confidence': 0.9,
            'evidence_text': '另一条不同产物的关系',
        },
    ]
    fake_mongo.collections['inc_context'] = [
        {'statement_id': 'ST_1', 'context_id': 'CTX_1', 'begin_time': '2026-03-16T10:00:00', 'evidence_text': '双方合作推进产线升级', 'source_name': 'rss'},
    ]
    fake_mongo.collections['source_news'] = [
        {'doc_id': 'doc_1', 'title': '智链机器人与车企合作', 'content': '双方合作推进产线升级', 'source_name': 'rss'},
        {'doc_id': 'doc_2', 'title': '无关产物文档', 'content': '另一条不同产物的关系', 'source_name': 'rss'},
    ]

    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: fake_mongo)
    monkeypatch.setattr(open_api_routes, "_get_redis_conn", lambda: None)
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "empty",
            "mode": "offline",
            "graph_labels": [],
            "reason_candidates": [],
            "query_plan": [],
            "search_queries": [],
            "search_checks": [],
            "graph_query_count": 0,
            "graph_hit_count": 0,
            "hits": [],
        },
        raising=False,
    )
    monkeypatch.setattr(open_api_routes, "_stream_query_answer", lambda context: iter(["测试回答"]))

    client = _build_client()
    res = client.post(
        "/api/v1/open/knowledge/query",
        json={
            "query": "智链机器人合作",
            "top_k": 5,
            "filters": {"artifact_id": "KART_1"},
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert len(payload["knowledge_objects"]) == 1
    assert payload["knowledge_objects"][0]["statement_id"] == "ST_1"


def test_open_knowledge_query_trace_includes_release_and_artifact_filters(monkeypatch):
    from app.api import open_api_routes

    fake_mongo = _FakeMongo()
    fake_mongo.collections['service_releases'] = [
        {
            'release_id': 'KREL_1',
            'artifact_id': 'KART_1',
            'version': 'rel-001',
        }
    ]
    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: fake_mongo)

    monkeypatch.setattr(
        open_api_routes,
        "_run_classic_query",
        lambda **kwargs: {
            "headlines": [],
            "data_source": "zhilian-robot-db:inc_statement",
            "knowledge_objects": [],
            "evidences": [],
            "entities": [],
            "hits": [],
            "answer": "",
        },
        raising=False,
    )
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "empty",
            "mode": "offline",
            "graph_labels": [],
            "reason_candidates": [],
            "query_plan": [],
            "search_queries": [],
            "search_checks": [],
            "graph_query_count": 0,
            "graph_hit_count": 0,
            "hits": [],
        },
        raising=False,
    )
    monkeypatch.setattr(open_api_routes, "_stream_query_answer", lambda context: iter(["测试回答"]))

    client = _build_client()
    res = client.post(
        "/api/v1/open/knowledge/query",
        json={
            "query": "测试问题",
            "top_k": 5,
            "filters": {"artifact_id": "KART_1", "release_id": "KREL_1", "release_version": "rel-001"},
        },
    )

    assert res.status_code == 200
    payload = res.json()
    trace = open_api_routes.get_open_knowledge_trace(payload["trace_id"])
    assert trace["query_plan"]["filters"]["artifact_id"] == "KART_1"
    assert trace["query_plan"]["filters"]["release_id"] == "KREL_1"


def test_open_knowledge_query_includes_compare_and_prefers_openspg(monkeypatch):
    from app.api import open_api_routes

    def fake_query_headlines(hours: int, top_n: int, allow_demo_fallback: bool):
        return {
            "headlines": [
                {
                    "event_id": "evt_1",
                    "headline_title": "传统检索命中事件",
                    "headline_score": 1.1,
                    "companies": ["智链机器人"],
                    "latest_publish_time": "2026-03-04T00:00:00+00:00",
                }
            ],
            "stats": {"event_count": 1},
            "meta": {"data_source": "zhilian-robot-db:crawled_articles"},
        }

    def fake_get_event_detail(event_id: str, hours: int, allow_demo_fallback: bool):
        return {
            "event_id": event_id,
            "evidence_news": [
                {
                    "news_id": "n1",
                    "title": "传统证据",
                    "source_name": "rss_36kr",
                    "url": "https://example.com/n1",
                    "publish_time": "2026-03-04T00:00:00+00:00",
                    "snippet": "传统检索证据",
                }
            ],
        }

    monkeypatch.setattr(open_api_routes, "_query_headlines", fake_query_headlines)
    monkeypatch.setattr(open_api_routes, "_get_event_detail", fake_get_event_detail)
    monkeypatch.setattr(open_api_routes, "_get_redis_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_generate_answer_with_llm", lambda **kwargs: "传统回答")
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "live",
            "mode": "openspg",
            "search_queries": ["MATCH (n:`zhilian.Company`) RETURN n LIMIT 3"],
            "graph_labels": ["zhilian.Company", "zhilian.Document"],
            "reason_candidates": [{"name": "Company", "name_zh": "企业", "score": 0.92}],
            "hits": [
                {
                    "id": "company:智链机器人",
                    "name": "智链机器人",
                    "label": "zhilian.Company",
                    "summary": "图谱中的企业节点",
                    "score": 0.92,
                    "source": "search/custom",
                }
            ],
            "answer": "OpenSPG 增强回答",
        },
        raising=False,
    )
    monkeypatch.setattr(
        open_api_routes,
        "_stream_query_answer",
        lambda context: iter(["OpenSPG 增强回答"]),
    )

    client = _build_client()
    res = client.post(
        "/api/v1/open/knowledge/query",
        json={
            "query": "智链机器人最近的合作和布局",
            "top_k": 5,
            "filters": {"hours": 24, "qa_strategy": "compare"},
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["answer_mode"] == "openspg"
    assert payload["answer"] == "OpenSPG 增强回答"
    assert payload["retrieval_compare"]["openspg"]["hit_count"] == 1
    assert payload["retrieval_compare"]["classic"]["hit_count"] == 1


def test_compare_mode_skips_classic_llm_when_openspg_hits_exist(monkeypatch):
    from app.api import open_api_routes

    monkeypatch.setattr(
        open_api_routes,
        "_query_headlines",
        lambda hours, top_n, allow_demo_fallback: {
            "headlines": [
                {
                    "event_id": "evt_1",
                    "headline_title": "传统检索命中事件",
                    "headline_score": 1.1,
                    "companies": ["智链机器人"],
                    "latest_publish_time": "2026-03-04T00:00:00+00:00",
                }
            ],
            "stats": {"event_count": 1},
            "meta": {"data_source": "zhilian-robot-db:crawled_articles"},
        },
    )
    monkeypatch.setattr(open_api_routes, "_get_event_detail", lambda *args, **kwargs: None)
    monkeypatch.setattr(open_api_routes, "_get_redis_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: None)
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "live",
            "mode": "openspg",
            "graph_labels": ["zhilian.Company"],
            "reason_candidates": [{"name": "Company", "name_zh": "公司", "score": 0.9, "label": "zhilian.Company"}],
            "search_queries": ["MATCH (n:`zhilian.Company`) RETURN n LIMIT 1"],
            "search_checks": [{"mode": "live", "http_status": 200}],
            "hits": [{"id": "COM_1", "name": "智链机器人", "label": "zhilian.Company", "summary": "资讯抽取实体", "score": 1.0, "source": "search/custom"}],
        },
        raising=False,
    )
    monkeypatch.setattr(
        open_api_routes,
        "_generate_answer_with_llm",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("classic llm should not be called")),
    )
    monkeypatch.setattr(
        open_api_routes,
        "_stream_query_answer",
        lambda context: iter(["OpenSPG answer only"]),
    )

    client = _build_client()
    res = client.post(
        "/api/v1/open/knowledge/query",
        json={"query": "测试问题", "top_k": 5, "filters": {"qa_strategy": "compare"}},
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["answer_mode"] == "openspg"
    assert payload["answer"] == "OpenSPG answer only"


def test_open_knowledge_trace_endpoint_returns_saved_trace(monkeypatch):
    from app.api import open_api_routes

    def fake_query_headlines(hours: int, top_n: int, allow_demo_fallback: bool):
        return {
            "headlines": [
                {
                    "event_id": "evt_1",
                    "headline_title": "智链机器人合作事件",
                    "headline_score": 1.1,
                    "companies": ["智链机器人", "某车企"],
                    "latest_publish_time": "2026-03-04T00:00:00+00:00",
                }
            ],
            "stats": {"event_count": 1},
            "meta": {"data_source": "demo"},
        }

    monkeypatch.setattr(open_api_routes, "_query_headlines", fake_query_headlines)
    monkeypatch.setattr(open_api_routes, "_get_event_detail", lambda event_id, hours, allow_demo_fallback: None)
    monkeypatch.setattr(open_api_routes, "_get_redis_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_stream_query_answer", lambda context: iter(["测试回答"]))
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "empty",
            "mode": "offline",
            "graph_labels": [],
            "reason_candidates": [],
            "query_plan": [],
            "search_queries": [],
            "search_checks": [],
            "graph_query_count": 0,
            "graph_hit_count": 0,
            "hits": [],
        },
        raising=False,
    )

    client = _build_client()
    query_res = client.post(
        "/api/v1/open/knowledge/query",
        json={"query": "测试查询", "top_k": 3},
    )

    assert query_res.status_code == 200
    trace_id = query_res.json()["trace_id"]

    trace_res = client.get(f"/api/v1/open/knowledge/trace/{trace_id}")
    assert trace_res.status_code == 200
    trace = trace_res.json()
    assert "retrieval_hits" in trace
    assert "reasoning_path" in trace


def test_open_knowledge_trace_contains_table_usage_and_workflow_reference(monkeypatch):
    from app.api import open_api_routes

    def fake_query_headlines(hours: int, top_n: int, allow_demo_fallback: bool):
        return {
            "headlines": [
                {
                    "event_id": "evt_1",
                    "headline_title": "智链机器人合作事件",
                    "headline_score": 1.1,
                    "companies": ["智链机器人"],
                    "latest_publish_time": "2026-03-04T00:00:00+00:00",
                }
            ],
            "stats": {"event_count": 1},
            "meta": {"data_source": "zhilian-robot-db:crawled_articles"},
        }

    def fake_get_event_detail(event_id: str, hours: int, allow_demo_fallback: bool):
        return {
            "event_id": event_id,
            "evidence_news": [
                {
                    "news_id": "n1",
                    "title": "智链机器人与车企合作",
                    "source_name": "rss_36kr",
                    "url": "https://example.com/n1",
                    "publish_time": "2026-03-04T00:00:00+00:00",
                    "snippet": "合作推进机器人自动化",
                }
            ],
        }

    monkeypatch.setattr(open_api_routes, "_query_headlines", fake_query_headlines)
    monkeypatch.setattr(open_api_routes, "_get_event_detail", fake_get_event_detail)
    monkeypatch.setattr(open_api_routes, "_get_redis_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_stream_query_answer", lambda context: iter(["测试回答"]))
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "empty",
            "mode": "offline",
            "graph_labels": [],
            "reason_candidates": [],
            "query_plan": [],
            "search_queries": [],
            "search_checks": [],
            "graph_query_count": 0,
            "graph_hit_count": 0,
            "hits": [],
        },
        raising=False,
    )
    monkeypatch.setattr(
        open_api_routes.demo_routes,
        "_list_workflow_runs",
        lambda project_id=1, limit=20: [
            {
                "run_id": "wf_latest",
                "status": "success",
                "headlines_snapshot": {"top_headline_ids": ["evt_1", "evt_2"]},
            }
        ],
    )

    client = _build_client()
    query_res = client.post(
        "/api/v1/open/knowledge/query",
        json={"query": "测试查询", "top_k": 3},
    )
    assert query_res.status_code == 200
    trace_id = query_res.json()["trace_id"]

    trace_res = client.get(f"/api/v1/open/knowledge/trace/{trace_id}")
    assert trace_res.status_code == 200
    trace = trace_res.json()
    assert trace["tables_used"][0]["table"] == "crawled_articles"
    assert trace["workflow_reference"]["run_id"] == "wf_latest"
    assert trace["workflow_reference"]["matched_event_ids"] == ["evt_1"]


def test_open_knowledge_batch_query_returns_results(monkeypatch):
    from app.api import open_api_routes

    def fake_query_headlines(hours: int, top_n: int, allow_demo_fallback: bool):
        return {
            "headlines": [
                {
                    "event_id": "evt_1",
                    "headline_title": "智链机器人合作事件",
                    "headline_score": 1.1,
                    "companies": ["智链机器人", "某车企"],
                    "latest_publish_time": "2026-03-04T00:00:00+00:00",
                }
            ],
            "stats": {"event_count": 1},
            "meta": {"data_source": "demo"},
        }

    monkeypatch.setattr(open_api_routes, "_query_headlines", fake_query_headlines)
    monkeypatch.setattr(open_api_routes, "_get_event_detail", lambda event_id, hours, allow_demo_fallback: None)
    monkeypatch.setattr(open_api_routes, "_get_redis_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_stream_query_answer", lambda context: iter(["测试回答"]))
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "empty",
            "mode": "offline",
            "graph_labels": [],
            "reason_candidates": [],
            "query_plan": [],
            "search_queries": [],
            "search_checks": [],
            "graph_query_count": 0,
            "graph_hit_count": 0,
            "hits": [],
        },
        raising=False,
    )

    client = _build_client()
    res = client.post(
        "/api/v1/open/knowledge/query/batch",
        json={"queries": ["问题1", "问题2"], "top_k": 2},
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["count"] == 2
    assert len(payload["results"]) == 2
    assert payload["results"][0]["query"] == "问题1"


def test_extract_query_terms_prefers_anchor_entities_over_full_sentence():
    from app.api import open_api_routes

    terms = open_api_routes._extract_query_terms("智链机器人布局了哪些技术")

    assert terms
    assert terms[0] == "智链机器人"
    assert "智链机器人布局了哪些技术" not in terms[:2]


def test_extract_query_terms_keeps_long_company_entity_names():
    from app.api import open_api_routes

    terms = open_api_routes._extract_query_terms("北京智链机器人股份有限公司最近有哪些合作")

    assert "北京智链机器人股份有限公司" in terms


def test_build_openspg_query_plan_prioritizes_multi_hop_queries():
    from app.api import open_api_routes

    plan = open_api_routes._build_openspg_query_plan(
        query="智链机器人布局了哪些技术",
        top_k=5,
        graph_labels=["zhilian.Company", "zhilian.Document", "zhilian.Technology"],
        reason_candidates=[{"label": "zhilian.Company", "name": "Company", "name_zh": "公司", "score": 0.9}],
        seed_terms=["智链机器人"],
    )

    assert plan
    assert plan[0]["kind"] == "graph_multi_hop"
    assert "mentionsCompany" in plan[0]["query"]
    assert "mentionsTech" in plan[0]["query"]
    assert any(item["kind"] == "text_fallback" for item in plan)


def test_build_openspg_query_plan_uses_llm_relation_intent_when_available(monkeypatch):
    from app.api import open_api_routes

    class _FakeLLM:
        client = object()

        def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
            return (
                '{"entities":["北京智链机器人股份有限公司"],'
                '"target_types":["Company"],'
                '"relation_intents":["cooperation"],'
                '"question_focus":"company_partners"}'
            )

    monkeypatch.setattr(open_api_routes, "_get_llm_processor", lambda: _FakeLLM())

    plan = open_api_routes._build_openspg_query_plan(
        query="北京智链机器人股份有限公司最近有哪些合作",
        top_k=5,
        graph_labels=["zhilian.Company", "zhilian.Document", "zhilian.Technology"],
        reason_candidates=[{"label": "zhilian.Company", "name": "Company", "name_zh": "公司", "score": 0.9}],
        seed_terms=[],
    )

    assert plan
    assert plan[0]["tag"] == "company_to_company"
    assert "北京智链机器人股份有限公司" in plan[0]["query"]


def test_rewrite_query_with_llm_returns_structured_intents(monkeypatch):
    from app.api import open_api_routes

    class _FakeLLM:
        client = object()

        def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
            return (
                "```json\n"
                '{"entities":["智链机器人"],'
                '"target_types":["Technology"],'
                '"relation_intents":["technology_layout"],'
                '"question_focus":"technology"}\n'
                "```"
            )

    monkeypatch.setattr(open_api_routes, "_get_llm_processor", lambda: _FakeLLM())

    payload = open_api_routes._rewrite_query_with_llm("智链机器人布局了哪些技术")

    assert payload["entities"] == ["智链机器人"]
    assert payload["target_types"] == ["Technology"]
    assert payload["relation_intents"] == ["technology_layout"]


def test_build_openspg_answer_prompt_includes_multi_hop_path_context():
    from app.api import open_api_routes

    prompt, fallback = open_api_routes._build_openspg_answer_prompt(
        query="智链机器人布局了哪些技术",
        openspg_hits=[
            {
                "id": "TECH_1",
                "name": "具身智能",
                "label": "zhilian.Technology",
                "summary": "来自智链机器人相关资讯",
                "score": 2.0,
                "source": "graph.multi_hop",
                "path_tag": "graph.multi_hop.company_to_technology",
                "anchor_name": "智链机器人",
            }
        ],
        evidences=[],
    )

    assert "graph.multi_hop.company_to_technology" in prompt
    assert "锚点：智链机器人" in prompt
    assert "具身智能" in fallback


def test_run_openspg_query_async_skips_text_fallback_when_multi_hop_hits_exist(monkeypatch):
    from app.api import open_api_routes

    async def fake_reason_schema(*, project_id: int):
        return {"mode": "live", "response": []}

    async def fake_graph_labels(*, project_id: int):
        return {"mode": "live", "response": ["zhilian.Company", "zhilian.Document", "zhilian.Technology"]}

    seen_queries = []

    async def fake_search(*, project_id: int, custom_query: str):
        seen_queries.append(custom_query)
        if "mentionsCompany" in custom_query and "mentionsTech" in custom_query:
            return {
                "mode": "live",
                "http_status": 200,
                "response": [
                    {
                        "node": {"id": "TECH_1", "name": "具身智能", "description": "图谱中的技术节点"},
                        "fields": {
                            "__labels__": ["zhilian.Technology"],
                            "docTitle": "智链机器人布局具身智能",
                            "pathTag": "graph.multi_hop.company_to_technology",
                            "anchorName": "智链机器人",
                        },
                        "score": 2.0,
                    }
                ],
            }
        raise AssertionError("multi-hop 命中后不应继续执行文本 fallback")

    monkeypatch.setattr(open_api_routes, "get_openspg_reason_schema", fake_reason_schema)
    monkeypatch.setattr(open_api_routes, "get_openspg_graph_labels", fake_graph_labels)
    monkeypatch.setattr(open_api_routes, "search_openspg_custom", fake_search)

    result = open_api_routes._run_openspg_query(
        query="智链机器人布局了哪些技术",
        top_k=5,
        filters={},
        seed_terms=["智链机器人"],
    )

    assert result["status"] == "live"
    assert result["hits"][0]["label"] == "zhilian.Technology"
    assert result["hits"][0]["source"] == "graph.multi_hop"
    assert any("mentionsCompany" in item and "mentionsTech" in item for item in seen_queries)


def test_run_openspg_query_async_falls_back_to_text_search_when_multi_hop_is_empty(monkeypatch):
    from app.api import open_api_routes

    async def fake_reason_schema(*, project_id: int):
        return {"mode": "live", "response": []}

    async def fake_graph_labels(*, project_id: int):
        return {"mode": "live", "response": ["zhilian.Company", "zhilian.Document", "zhilian.Technology"]}

    seen_queries = []

    async def fake_search(*, project_id: int, custom_query: str):
        seen_queries.append(custom_query)
        if "MATCH path =" in custom_query:
            return {"mode": "live", "http_status": 200, "response": []}
        return {
            "mode": "live",
            "http_status": 200,
            "response": [
                {
                    "node": {"id": "COM_1", "name": "智链机器人", "description": "图谱中的企业节点"},
                    "fields": {"__labels__": ["zhilian.Company"]},
                    "score": 1.0,
                }
            ],
        }

    monkeypatch.setattr(open_api_routes, "get_openspg_reason_schema", fake_reason_schema)
    monkeypatch.setattr(open_api_routes, "get_openspg_graph_labels", fake_graph_labels)
    monkeypatch.setattr(open_api_routes, "search_openspg_custom", fake_search)

    result = open_api_routes._run_openspg_query(
        query="智链机器人最近有什么动态",
        top_k=5,
        filters={},
        seed_terms=["智链机器人"],
    )

    assert result["status"] == "live"
    assert result["hits"][0]["source"] == "search/custom"
    assert any("MATCH path =" in item for item in seen_queries)
    assert any("MATCH (n:`zhilian.Company`)" in item for item in seen_queries)


def test_extract_openspg_hits_prefers_id_prefix_over_dirty_labels_for_target_type():
    from app.api import open_api_routes

    hits = open_api_routes._extract_openspg_hits(
        {
            "response": [
                {
                    "fields": {
                        "__labels__": ["zhilian.Company"],
                        "id": "TECH_demo_1",
                        "name": "机器视觉",
                    },
                    "score": 2.0,
                }
            ]
        },
        custom_query='MATCH path = (doc:`zhilian.Document`)-[r]->(neighbor) RETURN neighbor AS node LIMIT 5',
        source="graph.multi_hop",
        path_tag="document_anchor_technology",
        expected_target_label="zhilian.Technology",
    )

    assert hits
    assert hits[0]["label"] == "zhilian.Technology"


def test_extract_openspg_hits_exposes_doc_title_for_graph_view():
    from app.api import open_api_routes

    hits = open_api_routes._extract_openspg_hits(
        {
            "response": [
                {
                    "fields": {
                        "__labels__": ["zhilian.Technology"],
                        "id": "TECH_demo_1",
                        "name": "机器视觉",
                        "docTitle": "智链机器人联合宇树科技推进具身智能产线落地",
                        "docDescription": "双方将围绕具身智能、机器视觉和自动化产线协同优化柔性制造。",
                    },
                    "score": 2.0,
                }
            ]
        },
        custom_query='MATCH path = (doc:`zhilian.Document`)-[r]->(neighbor) RETURN neighbor AS node LIMIT 5',
        source="graph.multi_hop",
        path_tag="document_anchor_technology",
        expected_target_label="zhilian.Technology",
    )

    assert hits[0]["doc_title"] == "智链机器人联合宇树科技推进具身智能产线落地"


def test_extract_openspg_hits_prefers_document_business_id_alias():
    from app.api import open_api_routes

    hits = open_api_routes._extract_openspg_hits(
        {
            "response": [
                {
                    "docId": "2971",
                    "fields": {
                        "__labels__": ["zhilian.Technology"],
                        "id": "TECH_demo_1",
                        "name": "机器视觉",
                        "docBizId": "DEMO_DOC_ZLR_PARTNER",
                    },
                    "score": 2.0,
                }
            ]
        },
        custom_query='MATCH path = (doc:`zhilian.Document`)-[r]->(neighbor) RETURN neighbor AS node LIMIT 5',
        source="graph.multi_hop",
        path_tag="document_anchor_technology",
        expected_target_label="zhilian.Technology",
    )

    assert hits[0]["doc_id"] == "DEMO_DOC_ZLR_PARTNER"


def test_build_openspg_query_plan_adds_document_anchor_fallback_for_technology_questions():
    from app.api import open_api_routes

    plan = open_api_routes._build_openspg_query_plan(
        query="智链机器人布局了哪些技术",
        top_k=5,
        graph_labels=["zhilian.Company", "zhilian.Document", "zhilian.Technology"],
        reason_candidates=[{"label": "zhilian.Company", "name": "Company", "name_zh": "公司", "score": 0.9}],
        seed_terms=["智链机器人"],
    )

    assert any(item["kind"] == "graph_document_anchor" and item["tag"] == "document_anchor_technology" for item in plan)


def test_build_openspg_query_plan_prefers_query_anchor_over_classic_seed_terms():
    from app.api import open_api_routes

    plan = open_api_routes._build_openspg_query_plan(
        query="智链机器人布局了哪些技术",
        top_k=5,
        graph_labels=["zhilian.Company", "zhilian.Document", "zhilian.Technology"],
        reason_candidates=[{"label": "zhilian.Company", "name": "Company", "name_zh": "公司", "score": 0.9}],
        seed_terms=["头部人形机器人关节公司", "巨轮智能", "爱磁科技"],
    )

    document_anchor = next(item for item in plan if item["tag"] == "document_anchor_technology")
    assert "智链机器人" in document_anchor["query"]
    assert "头部人形机器人关节公司" not in document_anchor["query"]


def test_prepare_query_context_marks_multi_hop_in_trace(monkeypatch):
    from app.api import open_api_routes

    monkeypatch.setattr(
        open_api_routes.demo_routes,
        "_list_workflow_runs",
        lambda project_id=1, limit=20: [],
    )
    monkeypatch.setattr(open_api_routes, "_get_redis_conn", lambda: None)
    monkeypatch.setattr(open_api_routes, "_get_mongo_conn", lambda: None)
    monkeypatch.setattr(
        open_api_routes,
        "_run_classic_query",
        lambda **kwargs: {
            "headlines": [],
            "data_source": "demo",
            "knowledge_objects": [],
            "evidences": [],
            "entities": ["智链机器人"],
            "hits": [],
        },
    )
    monkeypatch.setattr(
        open_api_routes,
        "_run_openspg_query",
        lambda **kwargs: {
            "status": "live",
            "mode": "openspg",
            "graph_labels": ["zhilian.Company", "zhilian.Document", "zhilian.Technology"],
            "reason_candidates": [{"label": "zhilian.Company", "name": "Company", "name_zh": "公司", "score": 0.9}],
            "query_plan": [{"kind": "graph_multi_hop", "tag": "company_to_technology", "query": "MATCH path = ..."}],
            "search_queries": ["MATCH path = ..."],
            "search_checks": [{"kind": "graph_multi_hop", "mode": "live", "http_status": 200}],
            "graph_query_count": 1,
            "graph_hit_count": 1,
            "hits": [
                {
                    "id": "TECH_1",
                    "name": "具身智能",
                    "label": "zhilian.Technology",
                    "summary": "图谱中的技术节点",
                    "score": 2.0,
                    "source": "graph.multi_hop",
                }
            ],
        },
        raising=False,
    )

    context = open_api_routes._prepare_query_context(
        query="智链机器人布局了哪些技术",
        query_type="semantic",
        top_k=5,
        filters={"qa_strategy": "openspg"},
        include_evidence=True,
    )

    assert context["answer_mode"] == "openspg"
    assert "semantic:openspg.multi_hop" in context["trace_payload"]["reasoning_path"]
    assert context["retrieval_compare"]["openspg"]["graph_hit_count"] == 1


def test_prepare_query_context_builds_statement_backed_graph_path_view(monkeypatch):
    from app.api import open_api_routes

    fake_mongo = _FakeMongo()
    fake_mongo.collections['news_pipeline_entity_instances'].extend([
        {
            '_id': 'EN_COMPANY_ZL',
            'entity_id': 'EN_COMPANY_ZL',
            'canonical_name': '智链机器人',
            'entity_type': 'company',
            'entity_category': 'subject',
        },
        {
            '_id': 'EN_TECH_CV',
            'entity_id': 'EN_TECH_CV',
            'canonical_name': '机器视觉',
            'entity_type': 'technology',
            'entity_category': 'element',
        },
    ])
    fake_mongo.collections['news_pipeline_statements'].append(
        {
            '_id': 'ST_VIS',
            'statement_id': 'ST_VIS',
            'subject_id': 'EN_COMPANY_ZL',
            'predicate_id': 'rel:develops',
            'predicate_label': '研发技术',
            'object_entity_id': 'EN_TECH_CV',
            'doc_id': 'doc_demo_1',
            'evidence_text': '智链机器人持续强化机器视觉能力。',
            'confidence': 0.93,
        }
    )

    monkeypatch.setattr(open_api_routes, '_get_mongo_conn', lambda: fake_mongo)
    monkeypatch.setattr(open_api_routes.demo_routes, '_list_workflow_runs', lambda project_id=1, limit=20: [])
    monkeypatch.setattr(
        open_api_routes,
        '_run_classic_query',
        lambda **kwargs: {
            'headlines': [],
            'data_source': 'demo',
            'knowledge_objects': [],
            'evidences': [
                {
                    'doc_id': 'doc_demo_1',
                    'title': '智链机器人联合宇树科技推进具身智能产线落地',
                    'snippet': '双方将围绕具身智能、机器视觉协同优化柔性制造。',
                    'source_name': 'rss_36kr',
                    'statement_id': 'ST_VIS',
                }
            ],
            'entities': ['智链机器人'],
            'hits': [],
        },
    )
    monkeypatch.setattr(
        open_api_routes,
        '_run_openspg_query',
        lambda **kwargs: {
            'status': 'live',
            'mode': 'openspg',
            'graph_labels': ['zhilian.Company', 'zhilian.Document', 'zhilian.Technology'],
            'reason_candidates': [{'label': 'zhilian.Company', 'name': 'Company', 'name_zh': '公司', 'score': 0.9}],
            'query_plan': [{'kind': 'graph_document_anchor', 'tag': 'document_anchor_technology', 'query': 'MATCH path = ...'}],
            'search_queries': ['MATCH path = ...'],
            'search_checks': [{'kind': 'graph_document_anchor', 'mode': 'live', 'http_status': 200}],
            'graph_query_count': 1,
            'graph_hit_count': 1,
            'hits': [
                {
                    'id': 'TECH_demo_1',
                    'name': '机器视觉',
                    'label': 'zhilian.Technology',
                    'summary': '资讯抽取技术实体',
                    'score': 1.7,
                    'source': 'graph.multi_hop',
                    'path_tag': 'document_anchor_technology',
                    'doc_id': 'doc_demo_1',
                    'doc_title': '智链机器人联合宇树科技推进具身智能产线落地',
                }
            ],
        },
        raising=False,
    )

    context = open_api_routes._prepare_query_context(
        query='智链机器人布局了哪些技术',
        query_type='semantic',
        top_k=5,
        filters={'qa_strategy': 'openspg'},
        include_evidence=True,
    )

    graph_path_view = context['graph_path_view']
    assert graph_path_view['mode'] == 'statement_path'
    labels = [item['label'] for item in graph_path_view['nodes']]
    assert '智链机器人' in labels
    assert '机器视觉' in labels
    assert '研发技术' in labels
    assert any(edge['label'] == '研发技术' for edge in graph_path_view['edges'])


def test_run_classic_query_prefers_structured_statements_over_headlines(monkeypatch):
    from app.api import open_api_routes

    fake_mongo = _FakeMongo()
    fake_mongo.collections['entity_instances'] = [
        {
            '_id': 'CANONICAL_company_1',
            'entity_id': 'CANONICAL_company_1',
            'canonical_name': '智链机器人',
            'entity_type': 'company',
            'source_kg': 'news_kg',
        },
        {
            '_id': 'CANONICAL_technology_1',
            'entity_id': 'CANONICAL_technology_1',
            'canonical_name': '机器视觉',
            'entity_type': 'technology',
            'source_kg': 'news_kg',
        },
    ]
    fake_mongo.collections['inc_statement'] = [
        {
            '_id': 'ST_STRUCT_1',
            'statement_id': 'ST_STRUCT_1',
            'subject_id': 'CANONICAL_company_1',
            'predicate_id': 'rel:develops',
            'predicate_label': '研发技术',
            'object_entity_id': 'CANONICAL_technology_1',
            'doc_id': 'doc_struct_1',
            'evidence_text': '智链机器人持续强化机器视觉能力。',
            'context_time_value': '2026-03-12',
            'confidence': 0.95,
            'source_kg': 'news_kg',
        }
    ]
    fake_mongo.collections['inc_context'] = [
        {
            '_id': 'CTX_1',
            'context_id': 'CTX_1',
            'statement_id': 'ST_STRUCT_1',
            'doc_id': 'doc_struct_1',
            'source_name': 'rss_36kr',
            'source_url': 'https://example.com/news-1',
        }
    ]
    fake_mongo.collections['news_pipeline_source_news'] = [
        {
            '_id': 'news_1',
            'doc_id': 'doc_struct_1',
            'title': '智链机器人升级机器视觉平台',
            'source_name': 'rss_36kr',
            'source_url': 'https://example.com/news-1',
        }
    ]

    monkeypatch.setattr(open_api_routes, '_get_mongo_conn', lambda: fake_mongo)
    monkeypatch.setattr(
        open_api_routes,
        '_query_headlines',
        lambda hours, top_n, allow_demo_fallback: {
            'headlines': [
                {
                    'event_id': 'evt_demo_1',
                    'headline_title': '旧 headlines 结果',
                    'headline_score': 0.3,
                    'companies': ['旧公司'],
                }
            ],
            'meta': {'data_source': 'demo'},
        },
    )
    monkeypatch.setattr(open_api_routes, '_get_event_detail', lambda event_id, hours, allow_demo_fallback: None)

    result = open_api_routes._run_classic_query(
        query='智链机器人布局了哪些技术',
        top_k=5,
        hours=24,
        allow_demo_fallback=True,
        include_evidence=True,
        generate_answer=False,
    )

    assert result['data_source'] == 'zhilian-robot-db:inc_statement'
    assert result['headlines'][0]['event_id'] == 'ST_STRUCT_1'
    assert result['knowledge_objects'][0]['statement_id'] == 'ST_STRUCT_1'
    assert result['evidences'][0]['doc_id'] == 'doc_struct_1'


def test_prepare_query_context_builds_query_graph_path_view_with_doc_id_only(monkeypatch):
    from app.api import open_api_routes

    monkeypatch.setattr(open_api_routes, '_get_mongo_conn', lambda: None)
    monkeypatch.setattr(open_api_routes.demo_routes, '_list_workflow_runs', lambda project_id=1, limit=20: [])
    monkeypatch.setattr(
        open_api_routes,
        '_run_classic_query',
        lambda **kwargs: {
            'headlines': [],
            'data_source': 'demo',
            'knowledge_objects': [],
            'evidences': [],
            'entities': ['智链机器人'],
            'hits': [],
        },
    )
    monkeypatch.setattr(
        open_api_routes,
        '_run_openspg_query',
        lambda **kwargs: {
            'status': 'live',
            'mode': 'openspg',
            'graph_labels': ['zhilian.Company', 'zhilian.Document', 'zhilian.Technology'],
            'reason_candidates': [],
            'query_plan': [{'kind': 'graph_document_anchor', 'tag': 'document_anchor_technology', 'query': 'MATCH path = ...'}],
            'search_queries': ['MATCH path = ...'],
            'search_checks': [{'kind': 'graph_document_anchor', 'mode': 'live', 'http_status': 200}],
            'graph_query_count': 1,
            'graph_hit_count': 1,
            'hits': [
                {
                    'id': 'TECH_demo_1',
                    'name': '机器视觉',
                    'label': 'zhilian.Technology',
                    'summary': '资讯抽取技术实体',
                    'score': 1.7,
                    'source': 'graph.multi_hop',
                    'path_tag': 'document_anchor_technology',
                    'doc_id': '2971',
                }
            ],
        },
        raising=False,
    )

    context = open_api_routes._prepare_query_context(
        query='智链机器人布局了哪些技术',
        query_type='semantic',
        top_k=5,
        filters={'qa_strategy': 'openspg'},
        include_evidence=True,
    )

    graph_path_view = context['graph_path_view']
    assert graph_path_view['mode'] == 'query_path'
    assert any(node['label'] == '文档 #2971' for node in graph_path_view['nodes'])


def test_prepare_query_context_resolves_statement_path_from_source_news_when_hit_only_has_internal_doc_id(monkeypatch):
    from app.api import open_api_routes

    fake_mongo = _FakeMongo()
    fake_mongo.collections['news_pipeline_source_news'] = [
        {
            'doc_id': 'DEMO_DOC_ZLR_PARTNER',
            'title': '智链机器人联合宇树科技推进具身智能产线落地',
            'content': '双方将围绕具身智能、机器视觉协同优化柔性制造。',
        }
    ]
    fake_mongo.collections['news_pipeline_entity_instances'].extend([
        {'_id': 'EN_COMPANY_ZL', 'entity_id': 'EN_COMPANY_ZL', 'canonical_name': '智链机器人', 'entity_type': 'company'},
        {'_id': 'EN_TECH_CV', 'entity_id': 'EN_TECH_CV', 'canonical_name': '机器视觉', 'entity_type': 'technology'},
    ])
    fake_mongo.collections['news_pipeline_statements'].append(
        {
            '_id': 'ST_VIS',
            'statement_id': 'ST_VIS',
            'subject_id': 'EN_COMPANY_ZL',
            'predicate_id': 'rel:develops',
            'predicate_label': '研发技术',
            'object_entity_id': 'EN_TECH_CV',
            'doc_id': 'DEMO_DOC_ZLR_PARTNER',
            'evidence_text': '双方将围绕具身智能、机器视觉协同优化柔性制造。',
            'confidence': 0.93,
        }
    )

    monkeypatch.setattr(open_api_routes, '_get_mongo_conn', lambda: fake_mongo)
    monkeypatch.setattr(open_api_routes.demo_routes, '_list_workflow_runs', lambda project_id=1, limit=20: [])
    monkeypatch.setattr(
        open_api_routes,
        '_run_classic_query',
        lambda **kwargs: {
            'headlines': [],
            'data_source': 'demo',
            'knowledge_objects': [],
            'evidences': [],
            'entities': ['智链机器人'],
            'hits': [],
        },
    )
    monkeypatch.setattr(
        open_api_routes,
        '_run_openspg_query',
        lambda **kwargs: {
            'status': 'live',
            'mode': 'openspg',
            'graph_labels': ['zhilian.Company', 'zhilian.Document', 'zhilian.Technology'],
            'reason_candidates': [],
            'query_plan': [{'kind': 'graph_document_anchor', 'tag': 'document_anchor_technology', 'query': 'MATCH path = ...'}],
            'search_queries': ['MATCH path = ...'],
            'search_checks': [{'kind': 'graph_document_anchor', 'mode': 'live', 'http_status': 200}],
            'graph_query_count': 1,
            'graph_hit_count': 1,
            'hits': [
                {
                    'id': 'TECH_demo_1',
                    'name': '机器视觉',
                    'label': 'zhilian.Technology',
                    'summary': '资讯抽取技术实体',
                    'score': 1.7,
                    'source': 'graph.multi_hop',
                    'path_tag': 'document_anchor_technology',
                    'doc_id': '2971',
                }
            ],
        },
        raising=False,
    )

    context = open_api_routes._prepare_query_context(
        query='智链机器人布局了哪些技术',
        query_type='semantic',
        top_k=5,
        filters={'qa_strategy': 'openspg'},
        include_evidence=True,
    )

    assert context['graph_path_view']['mode'] == 'statement_path'


def test_stable_demo_samples_cover_company_product_and_technology():
    from app.openspg_demo.headlines_service import get_demo_news_samples

    rows = get_demo_news_samples()
    titles = [str(item.get("title") or "") for item in rows]
    contents = [str(item.get("content") or "") for item in rows]
    combined = "\n".join(titles + contents)

    assert any("智链机器人" in title for title in titles)
    assert "宇树科技" in combined
    assert "具身智能" in combined
    assert "FlexArm 协作机械臂" in combined


def test_open_trace_reads_from_redis_and_backfills_memory(monkeypatch):
    from app.api import open_api_routes

    fake_redis = _FakeRedis()
    trace_id = 'trace_from_redis'
    trace_payload = {
        'query_plan': {'query': 'redis trace'},
        'retrieval_hits': [{'event_id': 'evt_redis'}],
        'reasoning_path': ['gateway:open-api'],
        'model_usage': {'mode': 'rule'},
    }
    fake_redis.set(f'open:trace:{trace_id}', trace_payload)

    monkeypatch.setattr(open_api_routes, '_get_redis_conn', lambda: fake_redis)
    monkeypatch.setattr(open_api_routes, '_get_mongo_conn', lambda: None)
    open_api_routes._TRACE_STORE.clear()

    client = _build_client()
    res = client.get(f'/api/v1/open/knowledge/trace/{trace_id}')
    assert res.status_code == 200
    assert res.json()['query_plan']['query'] == 'redis trace'
    assert trace_id in open_api_routes._TRACE_STORE


def test_open_trace_reads_from_mongo_and_backfills_memory(monkeypatch):
    from app.api import open_api_routes

    fake_mongo = _FakeMongo()
    trace_id = 'trace_from_mongo'
    fake_mongo.update_one(
        'open_api_traces',
        {'trace_id': trace_id},
        {
            '$set': {
                'trace_id': trace_id,
                'query_plan': {'query': 'mongo trace'},
                'retrieval_hits': [{'event_id': 'evt_mongo'}],
                'reasoning_path': ['semantic:openspg'],
                'model_usage': {'mode': 'rule+retrieval'},
            }
        },
        upsert=True,
    )

    monkeypatch.setattr(open_api_routes, '_get_redis_conn', lambda: None)
    monkeypatch.setattr(open_api_routes, '_get_mongo_conn', lambda: fake_mongo)
    open_api_routes._TRACE_STORE.clear()

    client = _build_client()
    res = client.get(f'/api/v1/open/knowledge/trace/{trace_id}')
    assert res.status_code == 200
    assert res.json()['query_plan']['query'] == 'mongo trace'
    assert trace_id in open_api_routes._TRACE_STORE
