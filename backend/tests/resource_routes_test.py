from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


class _FakeMongo:
    def __init__(self):
        self.collections = {
            'qa_citations': [],
            'source_news': [],
            'crawled_articles': [],
            'inc_document': [],
            'inc_statement': [],
            'inc_context': [],
        }

    def find_many(self, collection_name, query=None, limit=0, sort=None):
        query = query or {}
        rows = []
        for row in self.collections.get(collection_name, []):
            if all(row.get(k) == v for k, v in query.items()):
                rows.append(dict(row))
        if limit and limit > 0:
            rows = rows[:limit]
        return rows

    def find_one(self, collection_name, query):
        for row in self.collections.get(collection_name, []):
            if all(row.get(k) == v for k, v in query.items()):
                return dict(row)
        return None


def _build_client() -> TestClient:
    from app.api.resource_routes import router

    app = FastAPI()
    app.include_router(router, prefix='/api/v1')
    return TestClient(app)


def test_resource_lookup_requires_any_identifier():
    client = _build_client()
    res = client.get('/api/v1/resource/evidence/lookup')
    assert res.status_code == 400


def test_resource_lookup_by_trace_id_returns_evidence(monkeypatch):
    from app.api import resource_routes
    from app.api import open_api_routes
    from app.openspg_demo import routes as demo_routes

    monkeypatch.setattr(resource_routes, '_get_mongo_conn', lambda: None)
    monkeypatch.setattr(
        open_api_routes,
        'get_open_knowledge_trace',
        lambda trace_id: {
            'query_plan': {'query': 'trace query'},
            'retrieval_hits': [{'event_id': 'evt_trace_1'}],
            'reasoning_path': ['semantic:openspg'],
            'model_usage': {'mode': 'rule+retrieval'},
        },
    )
    monkeypatch.setattr(
        demo_routes,
        'get_headline_detail',
        lambda event_id, hours=24, allow_demo_fallback=True: {
            'event_id': event_id,
            'headline_title': '产业事件一',
            'evidence_news': [
                {
                    'news_id': 'doc_trace_1',
                    'title': '证据标题',
                    'snippet': '证据片段',
                    'source_name': 'rss',
                    'url': 'https://example.com/e1',
                    'publish_time': '2026-03-04T00:00:00+00:00',
                }
            ],
        },
    )

    client = _build_client()
    res = client.get('/api/v1/resource/evidence/lookup', params={'trace_id': 'trace_001'})
    assert res.status_code == 200
    payload = res.json()
    assert payload['total'] == 1
    assert payload['trace']['query_plan']['query'] == 'trace query'
    assert payload['items'][0]['statement_id'] == 'evt_trace_1'
    assert payload['items'][0]['doc_id'] == 'doc_trace_1'


def test_resource_lookup_by_statement_and_doc_reads_citation_and_doc(monkeypatch):
    from app.api import resource_routes
    from app.api import open_api_routes
    from app.openspg_demo import routes as demo_routes

    fake_mongo = _FakeMongo()
    fake_mongo.collections['qa_citations'].append(
        {
            'message_id': 'qa_m_1',
            'doc_id': 'doc_100',
            'statement_id': 'evt_100',
            'snippet': '来自 qa 的证据',
            'source_name': 'rss_36kr',
            'source_url': 'https://example.com/doc100',
            'publish_time': '2026-03-04T08:00:00+00:00',
        }
    )
    fake_mongo.collections['source_news'].append(
        {
            'doc_id': 'doc_100',
            'title': '机器人产业动态',
            'source_url': 'https://example.com/doc100',
            'source_name': 'rss_36kr',
            'publish_time': '2026-03-04T08:00:00+00:00',
            'content': '正文内容',
        }
    )

    monkeypatch.setattr(resource_routes, '_get_mongo_conn', lambda: fake_mongo)

    def fake_trace(trace_id):
        raise HTTPException(status_code=404, detail='trace not found')

    monkeypatch.setattr(open_api_routes, 'get_open_knowledge_trace', fake_trace)
    monkeypatch.setattr(demo_routes, 'get_headline_detail', lambda event_id, hours=24, allow_demo_fallback=True: None)

    client = _build_client()
    res = client.get(
        '/api/v1/resource/evidence/lookup',
        params={'statement_id': 'evt_100', 'doc_id': 'doc_100'},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload['total'] == 1
    assert payload['items'][0]['source_collection'] == 'qa_citations'
    assert payload['documents'][0]['source_collection'] == 'source_news'


def test_resource_lookup_supports_sort_and_pagination(monkeypatch):
    from app.api import resource_routes
    from app.api import open_api_routes
    from app.openspg_demo import routes as demo_routes

    monkeypatch.setattr(resource_routes, '_get_mongo_conn', lambda: None)

    monkeypatch.setattr(
        open_api_routes,
        'get_open_knowledge_trace',
        lambda trace_id: {
            'query_plan': {'query': 'sort query'},
            'retrieval_hits': [{'event_id': 'evt_sort_1'}],
            'reasoning_path': ['semantic:openspg'],
            'model_usage': {'mode': 'rule+retrieval'},
        },
    )
    monkeypatch.setattr(
        demo_routes,
        'get_headline_detail',
        lambda event_id, hours=24, allow_demo_fallback=True: {
            'event_id': event_id,
            'headline_title': '排序事件',
            'evidence_news': [
                {
                    'news_id': 'doc_b',
                    'title': 'B 标题',
                    'snippet': 'B 片段',
                    'source_name': 'source_b',
                    'url': 'https://example.com/b',
                    'publish_time': '2026-03-04T11:00:00+00:00',
                },
                {
                    'news_id': 'doc_a',
                    'title': 'A 标题',
                    'snippet': 'A 片段',
                    'source_name': 'source_a',
                    'url': 'https://example.com/a',
                    'publish_time': '2026-03-04T10:00:00+00:00',
                },
            ],
        },
    )

    client = _build_client()
    res = client.get(
        '/api/v1/resource/evidence/lookup',
        params={
            'trace_id': 'trace_sort_1',
            'sort_by': 'source_name',
            'sort_order': 'asc',
            'page': 2,
            'page_size': 1,
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload['total'] == 2
    assert payload['pagination']['page'] == 2
    assert payload['pagination']['page_size'] == 1
    assert payload['items'][0]['doc_id'] == 'doc_b'


def test_resource_lookup_returns_statement_and_context(monkeypatch):
    from app.api import resource_routes
    from app.api import open_api_routes
    from app.openspg_demo import routes as demo_routes

    fake_mongo = _FakeMongo()
    fake_mongo.collections['inc_statement'].append(
        {
            'statement_id': 'evt_struct_1',
            'subject_id': 'company:智链机器人',
            'predicate_id': 'industry_event',
            'object_entity_id': 'event:合作',
            'confidence': 0.92,
            'context_id': 'ctx_100',
            'doc_id': 'doc_200',
            'context_scenario': 'news',
        }
    )
    fake_mongo.collections['inc_context'].append(
        {
            'context_id': 'ctx_100',
            'context_type': 'news_event',
            'doc_id': 'doc_200',
            'begin_time': '2026-03-04T08:00:00+00:00',
            'end_time': '2026-03-04T09:00:00+00:00',
            'context_scenario': 'news',
        }
    )

    monkeypatch.setattr(resource_routes, '_get_mongo_conn', lambda: fake_mongo)

    def fake_trace(trace_id):
        raise HTTPException(status_code=404, detail='trace not found')

    monkeypatch.setattr(open_api_routes, 'get_open_knowledge_trace', fake_trace)
    monkeypatch.setattr(demo_routes, 'get_headline_detail', lambda event_id, hours=24, allow_demo_fallback=True: None)

    client = _build_client()
    res = client.get('/api/v1/resource/evidence/lookup', params={'statement_id': 'evt_struct_1'})
    assert res.status_code == 200
    payload = res.json()
    assert payload['statement']['statement_id'] == 'evt_struct_1'
    assert payload['statement']['subject_id'] == 'company:智链机器人'
    assert payload['contexts'][0]['context_id'] == 'ctx_100'
