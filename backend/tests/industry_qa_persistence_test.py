from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeMongo:
    def __init__(self):
        self.collections = {
            'qa_sessions': [],
            'qa_messages': [],
            'qa_citations': [],
            'qa_traces': [],
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
        payload = dict(update.get('$set') or {})
        target.update(payload)
        return None

    def insert_one(self, collection_name, document):
        self.collections.setdefault(collection_name, []).append(dict(document))
        return None

    def insert_many(self, collection_name, documents):
        for doc in documents:
            self.collections.setdefault(collection_name, []).append(dict(doc))
        return None

    def find_one(self, collection_name, query):
        for row in self.collections.get(collection_name, []):
            if all(row.get(k) == v for k, v in query.items()):
                return dict(row)
        return None

    def find_many(self, collection_name, query=None, limit=0, sort=None):
        query = query or {}
        rows = [dict(row) for row in self.collections.get(collection_name, []) if all(row.get(k) == v for k, v in query.items())]
        if sort:
            for key, direction in reversed(sort):
                reverse = int(direction) < 0
                rows.sort(key=lambda item: str(item.get(key) or ''), reverse=reverse)
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


def test_industry_qa_persists_to_mongo_and_redis(monkeypatch):
    from app.api import industry_qa_routes
    from app.api import open_api_routes

    fake_mongo = _FakeMongo()
    fake_redis = _FakeRedis()

    monkeypatch.setattr(industry_qa_routes, '_get_mongo_conn', lambda: fake_mongo)
    monkeypatch.setattr(industry_qa_routes, '_get_redis_conn', lambda: fake_redis)

    monkeypatch.setattr(
        open_api_routes,
        '_prepare_query_context',
        lambda **kwargs: {
            'query': '测试问题',
            'answer_mode': 'classic',
            'retrieval_compare': {'strategy': 'classic', 'classic': {'hit_count': 1}, 'openspg': {'hit_count': 0}},
            'knowledge_objects': [{'statement_id': 'evt_100'}],
            'entities': ['智链机器人'],
            'evidences': [
                {
                    'doc_id': 'doc_1',
                    'title': '证据一',
                    'snippet': 'snippet',
                    'source_name': 'rss',
                    'source_url': 'https://example.com',
                    'publish_time': '2026-03-04T00:00:00+00:00',
                    'context_id': 'ctx_1',
                    'statement_id': 'evt_100',
                }
            ],
            'trace_id': 'trace_mock_1',
            'trace_payload': {'query_plan': {'query': '测试问题'}},
            'workflow_reference': {},
        },
    )
    monkeypatch.setattr(open_api_routes, '_stream_query_answer', lambda context: iter(['测试回答']))
    monkeypatch.setattr(
        open_api_routes,
        '_build_query_response',
        lambda context, answer: {
            'answer': answer,
            'answer_mode': context.get('answer_mode'),
            'retrieval_compare': context.get('retrieval_compare'),
            'knowledge_objects': context.get('knowledge_objects'),
            'entities': context.get('entities'),
            'evidences': context.get('evidences'),
            'trace_id': context.get('trace_id'),
            'run_id': None,
        },
    )
    monkeypatch.setitem(
        open_api_routes._TRACE_STORE,
        'trace_mock_1',
        {
            'query_plan': {'query': '测试问题'},
            'retrieval_hits': [{'event_id': 'evt_100'}],
            'reasoning_path': ['extraction:kag', 'semantic:openspg'],
            'model_usage': {'mode': 'rule+retrieval'},
        },
    )

    app = FastAPI()
    app.include_router(industry_qa_routes.router, prefix='/api/v1')
    client = TestClient(app)

    create_res = client.post('/api/v1/agent/industry-qa/sessions', json={'title': '持久化测试会话'})
    assert create_res.status_code == 200
    session_id = create_res.json()['session_id']

    chat_res = client.post(
        '/api/v1/agent/industry-qa/chat',
        json={'session_id': session_id, 'question': '测试问题', 'top_k': 5},
    )
    assert chat_res.status_code == 200
    assert chat_res.json()['trace_id'] == 'trace_mock_1'

    # Mongo 持久化
    assert len(fake_mongo.collections['qa_sessions']) >= 1
    assert len(fake_mongo.collections['qa_messages']) >= 2
    assert len(fake_mongo.collections['qa_citations']) >= 1
    assert len(fake_mongo.collections['qa_traces']) >= 1
    assert fake_mongo.collections['qa_citations'][0]['title'] == '证据一'
    assert fake_mongo.collections['qa_citations'][0]['context_id'] == 'ctx_1'

    # Redis 缓存
    assert f'qa:session:{session_id}:context' in fake_redis.store
    assert 'qa:trace:trace_mock_1' in fake_redis.store

    trace_res = client.get('/api/v1/agent/industry-qa/messages/qa_not_exist/trace')
    assert trace_res.status_code == 404


def test_industry_qa_chat_stream_returns_event_stream(monkeypatch):
    from app.api import industry_qa_routes
    from app.api import open_api_routes

    monkeypatch.setattr(industry_qa_routes, '_get_mongo_conn', lambda: None)
    monkeypatch.setattr(industry_qa_routes, '_get_redis_conn', lambda: None)
    monkeypatch.setattr(
        open_api_routes,
        '_prepare_query_context',
        lambda **kwargs: {
            'query': '测试问题',
            'answer_mode': 'classic',
            'retrieval_compare': {'strategy': 'classic', 'classic': {'hit_count': 1}, 'openspg': {'hit_count': 0}},
            'knowledge_objects': [],
            'entities': [],
            'evidences': [],
            'trace_id': 'trace_stream_1',
            'trace_payload': {'query_plan': {'query': '测试问题'}},
            'workflow_reference': {},
        },
    )
    monkeypatch.setattr(open_api_routes, '_stream_query_answer', lambda context: iter(['这是', '一个', '测试回答']))
    monkeypatch.setattr(
        open_api_routes,
        '_build_query_response',
        lambda context, answer: {
            'answer': answer,
            'answer_mode': context.get('answer_mode'),
            'retrieval_compare': context.get('retrieval_compare'),
            'knowledge_objects': [],
            'entities': [],
            'evidences': [],
            'trace_id': context.get('trace_id'),
            'run_id': None,
        },
    )
    monkeypatch.setitem(
        open_api_routes._TRACE_STORE,
        'trace_stream_1',
        {
            'query_plan': {'query': '测试问题'},
            'retrieval_hits': [],
            'reasoning_path': ['semantic:openspg'],
            'model_usage': {'mode': 'rule+retrieval'},
        },
    )

    app = FastAPI()
    app.include_router(industry_qa_routes.router, prefix='/api/v1')
    client = TestClient(app)

    session_res = client.post('/api/v1/agent/industry-qa/sessions', json={'title': '流式会话'})
    assert session_res.status_code == 200
    session_id = session_res.json()['session_id']

    with client.stream(
        'POST',
        '/api/v1/agent/industry-qa/chat/stream',
        json={'session_id': session_id, 'question': '测试问题', 'top_k': 3},
    ) as res:
        body = ''.join(chunk for chunk in res.iter_text())

    assert res.status_code == 200
    assert 'text/event-stream' in res.headers.get('content-type', '')
    assert '"type": "delta"' in body or '"type":"delta"' in body


def test_industry_qa_chat_stream_emits_processing_then_token_deltas(monkeypatch):
    from app.api import industry_qa_routes
    from app.api import open_api_routes

    monkeypatch.setattr(industry_qa_routes, '_get_mongo_conn', lambda: None)
    monkeypatch.setattr(industry_qa_routes, '_get_redis_conn', lambda: None)
    monkeypatch.setattr(
        open_api_routes,
        '_prepare_query_context',
        lambda **kwargs: {
            'trace_id': 'trace_stream_2',
            'answer_mode': 'openspg',
            'retrieval_compare': {'strategy': 'compare', 'openspg': {'hit_count': 1}, 'classic': {'hit_count': 1}},
            'workflow_reference': {'run_id': 'wf_stream_2'},
            'knowledge_objects': [],
            'entities': [],
            'evidences': [],
            'trace_payload': {
                'query_plan': {'query': '测试问题', 'answer_mode': 'openspg'},
                'retrieval_hits': [],
            },
        },
        raising=False,
    )
    monkeypatch.setattr(
        open_api_routes,
        '_stream_query_answer',
        lambda context: iter(['这是', '真正', '流式']),
        raising=False,
    )
    monkeypatch.setattr(
        open_api_routes,
        '_build_query_response',
        lambda context, answer: {
            'answer': answer,
            'answer_mode': context.get('answer_mode'),
            'retrieval_compare': context.get('retrieval_compare'),
            'knowledge_objects': context.get('knowledge_objects') or [],
            'entities': context.get('entities') or [],
            'evidences': context.get('evidences') or [],
            'trace_id': context.get('trace_id'),
            'run_id': 'wf_stream_2',
        },
        raising=False,
    )
    monkeypatch.setitem(
        open_api_routes._TRACE_STORE,
        'trace_stream_2',
        {
            'query_plan': {'query': '测试问题', 'answer_mode': 'openspg'},
            'retrieval_hits': [],
        },
    )

    app = FastAPI()
    app.include_router(industry_qa_routes.router, prefix='/api/v1')
    client = TestClient(app)

    session_res = client.post('/api/v1/agent/industry-qa/sessions', json={'title': '流式会话'})
    assert session_res.status_code == 200
    session_id = session_res.json()['session_id']

    with client.stream(
        'POST',
        '/api/v1/agent/industry-qa/chat/stream',
        json={'session_id': session_id, 'question': '测试问题', 'top_k': 3},
    ) as res:
        body = ''.join(chunk for chunk in res.iter_text())

    assert res.status_code == 200
    assert '"status": "processing"' in body or '"status":"processing"' in body
    assert '"status": "retrieving"' in body or '"status":"retrieving"' in body
    assert '"content": "这是"' in body or '"content":"这是"' in body
    assert '"content": "真正"' in body or '"content":"真正"' in body
    assert '"content": "流式"' in body or '"content":"流式"' in body
    assert '"type": "done"' in body or '"type":"done"' in body
