from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_client() -> TestClient:
    from app.api.workflow_routes import router

    app = FastAPI()
    app.include_router(router, prefix='/api/v1')
    return TestClient(app)


def test_workflow_collect_step(monkeypatch):
    from app.openspg_demo import routes as demo_routes

    def fake_ingest(request):
        return {
            'ok': True,
            'inserted_count': 12,
            'request': request.model_dump(),
        }

    monkeypatch.setattr(demo_routes, 'ingest_real_rss', fake_ingest)

    client = _build_client()
    res = client.post('/api/v1/workflow/news/steps/collect', json={'max_entries_per_feed': 7, 'hours_ago': 48})
    assert res.status_code == 200
    payload = res.json()
    assert payload['inserted_count'] == 12
    assert payload['request']['hours_ago'] == 48


def test_workflow_process_step(monkeypatch):
    from app.openspg_demo import routes as demo_routes

    def fake_preview(limit=100, sample_lines=5, allow_demo_fallback=None):
        return {'meta': {'limit': limit}, 'sample_records': [{'doc_id': 'd1'}]}

    def fake_status(allow_demo_fallback=None):
        return {'cursor': 'abc', 'last_run': {'run_id': 'r1'}}

    monkeypatch.setattr(demo_routes, 'get_bridge_batch_preview', fake_preview)
    monkeypatch.setattr(demo_routes, 'get_bridge_status', fake_status)

    client = _build_client()
    res = client.post('/api/v1/workflow/news/steps/process', json={'limit': 66, 'sample_lines': 3})
    assert res.status_code == 200
    payload = res.json()
    assert payload['preview']['meta']['limit'] == 66
    assert payload['status']['cursor'] == 'abc'


def test_workflow_extract_step(monkeypatch):
    from app.api import workflow_routes
    from app.openspg_demo import routes as demo_routes

    async def fake_extract(request):
        return {
            'run_id': 'extract_1',
            'export_count': 21,
            'request': request.model_dump(),
        }

    monkeypatch.setattr(demo_routes, 'run_bridge_batch', fake_extract)

    client = _build_client()
    res = client.post(
        '/api/v1/workflow/news/steps/extract',
        json={'project_id': 2, 'limit': 66, 'force_full': True},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload['run_id'] == 'extract_1'
    assert payload['request']['project_id'] == 2
    assert payload['request']['submit_builder'] is False
    assert payload['request']['materialize_graph'] is False
    assert payload['request']['runtime_profile'] == workflow_routes.DEFAULT_RUNTIME_PROFILE


def test_workflow_extract_step_supports_openks_direct_preview(monkeypatch):
    from app.api import workflow_routes

    monkeypatch.setattr(
        workflow_routes,
        'list_pending_openks_queue_preview',
        lambda limit=50: {
            'pending_count': 2,
            'rows': [{'queue_id': 'KGQ_1', 'doc_id': 'DOC_1', 'title': '具身智能进展'}],
        },
    )
    monkeypatch.setattr(
        workflow_routes,
        'get_news_kg_status',
        lambda: {'kg_name': 'news_kg', 'queue': {'pending': 2}, 'latest_run': {'run_id': 'KRUN_1'}},
    )

    client = _build_client()
    res = client.post(
        '/api/v1/workflow/news/steps/extract',
        json={'project_id': 1, 'limit': 20, 'runtime_profile': 'openks_direct'},
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload['runtime_profile'] == 'openks_direct'
    assert payload['preview']['pending_count'] == 2
    assert payload['status']['latest_run']['run_id'] == 'KRUN_1'


def test_workflow_model_step_uses_openks_schema_runtime(monkeypatch):
    from app.api import workflow_routes

    async def fake_apply_openks_news_kg_schema(*, project_id, activate_label):
        assert project_id == 2
        assert activate_label == 'workflow-step-test'
        return {
            'schema_source': 'openks_module',
            'compiled_schema_script': 'namespace OpenKSNews\n\nNewsDocument(资讯文档): EntityType\n',
            'kag_schema_export': {
                'namespace': 'OpenKSNews',
                'project_dir': 'modules/kag/kag/examples/OpenKSNews',
                'schema_path': 'modules/kag/kag/examples/OpenKSNews/schema/OpenKSNews.schema',
            },
            'schema_commit_result': {
                'committed': True,
                'host_addr': 'http://127.0.0.1:8887',
                'project_id': 2,
            },
            'activate_result': {
                'project_id': 2,
                'label': 'workflow-step-test',
                'source': 'openks_module',
            },
        }

    monkeypatch.setattr(workflow_routes, 'apply_openks_news_kg_schema', fake_apply_openks_news_kg_schema)

    client = _build_client()
    res = client.post(
        '/api/v1/workflow/news/steps/model',
        json={
            'project_id': 2,
            'activate_label': 'workflow-step-test',
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload['schema_source'] == 'openks_module'
    assert payload['compiled_schema_script'].startswith('namespace OpenKSNews')
    assert payload['kag_schema_export']['namespace'] == 'OpenKSNews'
    assert payload['schema_commit_result']['committed'] is True
    assert payload['activate_result']['label'] == 'workflow-step-test'


def test_workflow_execute_step(monkeypatch):
    from app.api import workflow_routes
    from app.openspg_demo import routes as demo_routes

    def fake_status(allow_demo_fallback=None):
        return {
            'cursor': {'last_seen_time': '2026-03-04T00:00:00+00:00'},
            'last_run': {
                'run_id': 'extract_1',
                'batch_file_path': '/tmp/extract_1.jsonl',
                'batch_file_name': 'extract_1.jsonl',
                'export_count': 9,
            },
        }

    def fake_build_envs(run_result, project_id):
        assert run_result['run_id'] == 'extract_1'
        assert project_id == 3
        return {'OPENSPG_DEMO_BATCH_FILE': '/tmp/extract_1.jsonl'}

    async def fake_submit(request):
        return {
            'mode': 'live',
            'http_status': 200,
            'response': {
                'success': True,
                'result': {'taskId': 1001},
            },
            'request': request.model_dump(),
            'job_id': 1001,
        }

    async def fake_materialize(*, bridge_run, project_id):
        assert bridge_run['run_id'] == 'extract_1'
        assert project_id == 3
        return {
            'status': 'success',
            'records': 9,
            'vertices': 18,
            'edges': 12,
        }

    def fake_register(**kwargs):
        assert kwargs['runtime_profile'] == 'kag_openspg'
        return {
            'run': {'run_id': 'KRUN_KAG_extract_1'},
            'artifact': {'artifact_id': 'KART_KAG_extract_1'},
            'release': None,
        }

    monkeypatch.setattr(demo_routes, 'get_bridge_status', fake_status)
    monkeypatch.setattr(workflow_routes, 'build_builder_envs_for_run', fake_build_envs)
    monkeypatch.setattr(demo_routes, 'submit_engine_builder_job', fake_submit)
    monkeypatch.setattr(workflow_routes, 'materialize_kag_bridge_run', fake_materialize)
    monkeypatch.setattr(workflow_routes, 'register_workflow_runtime_binding', fake_register)

    client = _build_client()
    res = client.post(
        '/api/v1/workflow/news/steps/execute',
        json={'project_id': 3, 'worker_num': 2, 'builder_command': 'python run.py'},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload['builder_submit_result']['job_id'] == 1001
    assert payload['bridge_last_run']['run_id'] == 'extract_1'
    assert payload['builder_submit_result']['request']['project_id'] == 3
    assert payload['graph_materialize_result']['status'] == 'success'
    assert payload['runtime_binding']['artifact']['artifact_id'] == 'KART_KAG_extract_1'


def test_workflow_execute_step_supports_openks_direct(monkeypatch):
    from app.api import workflow_routes

    monkeypatch.setattr(
        workflow_routes,
        'build_news_kg',
        lambda limit=20: {
            'kg_name': 'news_kg',
            'run_id': 'KRUN_OPENKS_1',
            'artifact_id': 'KART_OPENKS_1',
            'artifact_version': 'news_kg:20260317120000',
            'processed': 12,
        },
    )
    monkeypatch.setattr(
        workflow_routes,
        'get_runtime_binding_summary',
        lambda kg_name='news_kg', runtime_profile='openks_direct': {
            'run': {'run_id': 'KRUN_OPENKS_1'},
            'artifact': {'artifact_id': 'KART_OPENKS_1'},
            'release': {'release_id': 'KREL_OPENKS_1'},
        },
    )

    client = _build_client()
    res = client.post(
        '/api/v1/workflow/news/steps/execute',
        json={'project_id': 1, 'runtime_profile': 'openks_direct', 'limit': 12},
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload['runtime_profile'] == 'openks_direct'
    assert payload['openks_build_result']['run_id'] == 'KRUN_OPENKS_1'
    assert payload['runtime_binding']['release']['release_id'] == 'KREL_OPENKS_1'


def test_workflow_execute_step_fails_when_builder_response_is_unsuccessful(monkeypatch):
    from app.api import workflow_routes
    from app.openspg_demo import routes as demo_routes

    def fake_status(allow_demo_fallback=None):
        return {
            'cursor': {'last_seen_time': '2026-03-04T00:00:00+00:00'},
            'last_run': {
                'run_id': 'extract_1',
                'batch_file_path': '/tmp/extract_1.jsonl',
                'batch_file_name': 'extract_1.jsonl',
                'export_count': 9,
            },
        }

    def fake_build_envs(run_result, project_id):
        assert run_result['run_id'] == 'extract_1'
        assert project_id == 3
        return {'OPENSPG_DEMO_BATCH_FILE': '/tmp/extract_1.jsonl'}

    async def fake_submit(request):
        return {
            'mode': 'live',
            'http_status': 200,
            'response': {
                'success': False,
                'errorMsg': 'project is null',
            },
            'request': request.model_dump(),
        }

    monkeypatch.setattr(demo_routes, 'get_bridge_status', fake_status)
    monkeypatch.setattr(workflow_routes, 'build_builder_envs_for_run', fake_build_envs)
    monkeypatch.setattr(demo_routes, 'submit_engine_builder_job', fake_submit)

    client = _build_client()
    res = client.post(
        '/api/v1/workflow/news/steps/execute',
        json={'project_id': 3, 'worker_num': 2, 'builder_command': 'python run.py'},
    )
    assert res.status_code == 502
    assert 'project is null' in res.json()['detail']


def test_workflow_execute_step_requires_extract_first(monkeypatch):
    from app.openspg_demo import routes as demo_routes

    monkeypatch.setattr(demo_routes, 'get_bridge_status', lambda allow_demo_fallback=None: {'cursor': {}, 'last_run': None})

    client = _build_client()
    res = client.post('/api/v1/workflow/news/steps/execute', json={'project_id': 1})
    assert res.status_code == 400
    assert '请先执行抽取步骤' in res.json()['detail']


def test_workflow_apply_step(monkeypatch):
    from app.openspg_demo import routes as demo_routes

    def fake_headlines(hours=24, top_n=20, allow_demo_fallback=None):
        return {'headlines': [{'event_id': 'evt_1'}], 'stats': {'event_count': 1}}

    monkeypatch.setattr(demo_routes, 'get_headlines', fake_headlines)

    client = _build_client()
    res = client.post('/api/v1/workflow/news/steps/apply', json={'hours': 12, 'top_n': 6})
    assert res.status_code == 200
    payload = res.json()
    assert payload['stats']['event_count'] == 1
    assert payload['meta']['hours'] == 12
    assert payload['meta']['top_n'] == 6


def test_workflow_step_detail_route(monkeypatch):
    from app.openspg_demo import routes as demo_routes

    def fake_step_detail(run_id, step_key):
        return {
            'meta': {
                'run_id': run_id,
                'step_key': step_key,
                'status': 'success',
            },
            'input': {'metrics': []},
            'output': {'metrics': []},
            'visualization': {'type': 'none', 'data': {}},
        }

    monkeypatch.setattr(demo_routes, 'get_news_workflow_step_detail', fake_step_detail)

    client = _build_client()
    res = client.get('/api/v1/workflow/news/runs/wf_123/steps/process')
    assert res.status_code == 200
    payload = res.json()
    assert payload['meta']['run_id'] == 'wf_123'
    assert payload['meta']['step_key'] == 'process'
