import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_openspg_demo_headlines_endpoint_returns_payload(monkeypatch):
    from app.openspg_demo.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    res = client.get("/api/v1/openspg-demo/headlines", params={"allow_demo_fallback": False})
    assert res.status_code == 200
    data = res.json()
    assert "headlines" in data
    assert "stats" in data


def test_openspg_demo_engine_snapshot_endpoint_returns_sections(monkeypatch):
    from app.openspg_demo.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    res = client.get("/api/v1/openspg-demo/engine/snapshot")
    assert res.status_code == 200
    data = res.json()
    for key in ["schema", "builder", "reason", "search", "graph"]:
        assert key in data


def test_openspg_demo_bridge_batch_preview_returns_normalized_records():
    from app.openspg_demo.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    res = client.get(
        "/api/v1/openspg-demo/bridge/batch-preview",
        params={"limit": 5, "sample_lines": 2, "allow_demo_fallback": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert "meta" in data
    assert "sample_records" in data
    assert "jsonl_preview" in data
    assert data["meta"]["limit"] == 5
    assert len(data["sample_records"]) >= 1
    assert "doc_id" in data["sample_records"][0]
    assert "doc_hash" in data["sample_records"][0]
    assert len(data["jsonl_preview"]) <= 2


def test_openspg_demo_bridge_export_jsonl_returns_text():
    from app.openspg_demo.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    res = client.get(
        "/api/v1/openspg-demo/bridge/export.jsonl",
        params={"limit": 3, "allow_demo_fallback": True},
    )
    assert res.status_code == 200
    assert "text/plain" in res.headers.get("content-type", "")
    assert "attachment;" in res.headers.get("content-disposition", "")
    lines = [line for line in res.text.splitlines() if line.strip()]
    assert len(lines) >= 1
    assert '"doc_id"' in lines[0]


def test_openspg_demo_bridge_status_and_run_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    status_res = client.get("/api/v1/openspg-demo/bridge/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "last_run" in status_data
    assert "cursor" in status_data

    run_res = client.post(
        "/api/v1/openspg-demo/bridge/run",
        json={"limit": 20, "force_full": True, "submit_builder": False},
    )
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert "run_id" in run_data
    assert "export_count" in run_data
    assert "batch_download_url" in run_data


def test_openspg_demo_engine_health_endpoint_returns_status():
    from app.openspg_demo.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.get("/api/v1/openspg-demo/engine/health", params={"project_id": 1})
    assert res.status_code == 200
    data = res.json()
    assert "openspg_base_url" in data
    assert "status" in data
    assert "checks" in data
    assert "builder_submit_enabled" in data
    assert "builder_submit_hint" in data


def test_openspg_demo_engine_builder_submit_endpoint_supports_mock(monkeypatch):
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    async def fake_submit(**kwargs):
        return {
            "mode": "mock",
            "request": kwargs,
            "response": {"message": "mock builder submit ok"},
        }

    monkeypatch.setattr(demo_routes, "submit_openspg_builder_job", fake_submit)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/engine/builder/submit",
        json={"project_id": 1, "command": "echo hello", "worker_num": 1},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "mock"
    assert "request" in data


def test_bridge_run_skip_builder_when_submit_switch_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT", "0")
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import get_demo_news_samples
    from app.openspg_demo.routes import router

    submit_called = {"n": 0}

    async def fake_apply_schema(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": True},
            "request": kwargs,
        }

    async def fake_submit(**kwargs):
        submit_called["n"] += 1
        return {"mode": "live", "request": kwargs}

    monkeypatch.setattr(demo_routes, "_read_news_rows", lambda limit=200, allow_demo_fallback=False: (get_demo_news_samples(), "demo-fallback"))
    monkeypatch.setattr(demo_routes, "apply_openspg_schema_script", fake_apply_schema)
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_job", fake_submit)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/bridge/run",
        json={"limit": 20, "force_full": True, "submit_builder": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["export_count"] > 0
    assert data["builder_submit_result"]["mode"] == "skip"
    assert "OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT" in data["builder_submit_result"]["reason"]
    assert submit_called["n"] == 0


def test_bridge_run_default_submit_builder_uses_real_ingest_command(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT", raising=False)
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import get_demo_news_samples
    from app.openspg_demo.routes import router

    submit_payload = {}

    async def fake_apply_schema(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": True},
            "request": kwargs,
        }

    async def fake_submit(**kwargs):
        submit_payload.update(kwargs)
        return {"mode": "live", "request": kwargs}

    monkeypatch.setattr(
        demo_routes,
        "_read_news_rows",
        lambda limit=200, allow_demo_fallback=False: (get_demo_news_samples(), "demo-fallback"),
    )
    monkeypatch.setattr(demo_routes, "apply_openspg_schema_script", fake_apply_schema)
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_job", fake_submit)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/bridge/run",
        json={"limit": 20, "force_full": True, "submit_builder": True, "project_id": 1},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["export_count"] > 0
    assert data["builder_submit_result"]["mode"] == "live"
    assert submit_payload["project_id"] == 1
    assert "OPENSPG_DEMO_REAL_IMPORT" in submit_payload["command"]
    assert submit_payload["envs"]["OPENSPG_DEMO_BATCH_GZIP_B64"]
    assert submit_payload["envs"]["OPENSPG_DEMO_PROJECT_ID"] == "1"


def test_real_import_command_handles_existing_vertices_idempotently():
    from app.openspg_demo.builder_import_command import build_real_import_command

    command = build_real_import_command()
    assert "_is_exists_conflict" in command
    assert "ignore_exists=False" in command
    assert "if ignore_exists and _is_exists_conflict(result)" in command
    assert '"upsertAdjacentVertices": False' in command
    assert '"/public/v1/graph/deleteVertex"' in command
    assert '"type": "Entity"' in command
    assert 'document_type = _type_name(namespace, "Document")' in command
    assert 'knowledge_point_type = _type_name(namespace, "KnowledgePoint")' in command
    assert '"label": "mentionsCompany"' in command
    assert '"label": "fromChunk"' in command


def test_real_import_command_groups_records_and_uses_project_namespace():
    from app.openspg_demo.builder_import_command import build_real_import_command

    command = build_real_import_command()
    assert "def _resolve_project_namespace(" in command
    assert "/public/v1/project?projectId=%d" in command
    assert "namespace = _resolve_project_namespace(base_url, project_id)" in command
    assert "def _type_name(namespace, local_name):" in command
    assert "vertex_groups = {}" in command
    assert 'key = (item["srcType"], item["label"], item["dstType"])' in command
    assert "for edge_type, grouped in edge_groups.items():" in command
    assert "cleanup_entity_ids" in command


def test_openspg_demo_pull_rss_endpoint(monkeypatch):
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    def fake_pull(max_entries_per_feed: int, hours_ago: int):
        assert max_entries_per_feed == 2
        assert hours_ago == 6
        return {
            "status": "success",
            "fetched_count": 3,
            "inserted_count": 2,
            "duplicate_count": 1,
            "sample_titles": ["机器人公司发布新品"],
            "hours_ago": hours_ago,
            "max_entries_per_feed": max_entries_per_feed,
        }

    monkeypatch.setattr(demo_routes, "pull_rss_articles_to_mongo", fake_pull)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/ingest/rss",
        json={"max_entries_per_feed": 2, "hours_ago": 6},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["fetched_count"] == 3
    assert data["inserted_count"] == 2


def test_bridge_run_applies_schema_before_builder_submit(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT", raising=False)
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import get_demo_news_samples
    from app.openspg_demo.routes import router

    schema_calls = {"n": 0}

    async def fake_apply_schema(**kwargs):
        schema_calls["n"] += 1
        return {"mode": "live", "request": kwargs}

    async def fake_submit(**kwargs):
        return {"mode": "live", "request": kwargs}

    monkeypatch.setattr(
        demo_routes,
        "_read_news_rows",
        lambda limit=200, allow_demo_fallback=False: (get_demo_news_samples(), "demo-fallback"),
    )
    monkeypatch.setattr(demo_routes, "apply_openspg_schema_script", fake_apply_schema, raising=False)
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_job", fake_submit)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/bridge/run",
        json={"limit": 20, "force_full": True, "submit_builder": True, "project_id": 1},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["export_count"] > 0
    assert schema_calls["n"] == 1
    assert data["schema_apply_result"]["mode"] == "live"


def test_model_studio_schema_apply_endpoint(monkeypatch):
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    async def fake_apply_schema(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": True},
            "request": kwargs,
        }

    async def fake_get_schema_script(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": "namespace Demo\n\nCompany(企业): EntityType\n"},
            "request": kwargs,
        }

    async def fake_get_schema_graph(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": {
                    "entityTypeDTOList": [{"name": "Company"}],
                    "relationTypeDTOList": [],
                },
            },
            "request": kwargs,
        }

    async def fake_get_reason_schema(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"spgTypes": []},
            "request": kwargs,
        }

    monkeypatch.setattr(demo_routes, "apply_openspg_schema_script", fake_apply_schema)
    monkeypatch.setattr(demo_routes, "get_openspg_schema_script", fake_get_schema_script)
    monkeypatch.setattr(demo_routes, "get_openspg_schema_graph", fake_get_schema_graph)
    monkeypatch.setattr(demo_routes, "get_openspg_reason_schema", fake_get_reason_schema, raising=False)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/model-studio/schema/apply",
        json={
            "project_id": 1,
            "schema_script": "namespace Demo\n\nCompany(企业): EntityType",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["schema_apply_result"]["mode"] == "live"
    assert data["schema_model"]["entity_count"] == 1
    assert data["schema_model"]["relation_count"] == 0
    assert "Company" in data["schema_model"]["entity_names"]


def test_model_studio_schema_apply_endpoint_fallback_to_public_alter(monkeypatch):
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    captured: dict = {}

    async def fake_apply_schema(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": False, "errorCode": "LOGIN_0002", "errorMsg": "User not logged in"},
            "request": kwargs,
        }

    async def fake_get_project(*, project_id: int):
        assert project_id == 1
        return {
            "mode": "live",
            "http_status": 200,
            "response": [{"id": 1, "namespace": "zhilian"}],
            "request": {"project_id": project_id},
        }

    async def fake_public_alter(*, project_id: int, schema_draft: dict):
        assert project_id == 1
        captured["schema_draft"] = schema_draft
        return {
            "mode": "live",
            "http_status": 200,
            "response": True,
            "request": {"project_id": project_id},
        }

    async def fake_get_schema_script(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": False, "errorCode": "LOGIN_0002"},
            "request": kwargs,
        }

    async def fake_get_schema_graph(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": False, "errorCode": "LOGIN_0002"},
            "request": kwargs,
        }

    async def fake_get_reason_schema(*, project_id: int):
        assert project_id == 1
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "spgTypes": [
                    {
                        "spgTypeEnum": "ENTITY_TYPE",
                        "basicInfo": {
                            "name": {"namespace": "zhilian", "nameEn": "Company"},
                            "nameZh": "企业",
                        },
                    }
                ]
            },
            "request": {"project_id": project_id},
        }

    monkeypatch.setattr(demo_routes, "apply_openspg_schema_script", fake_apply_schema)
    monkeypatch.setattr(demo_routes, "get_openspg_project", fake_get_project, raising=False)
    monkeypatch.setattr(
        demo_routes, "alter_openspg_schema_draft_public", fake_public_alter, raising=False
    )
    monkeypatch.setattr(demo_routes, "get_openspg_schema_script", fake_get_schema_script)
    monkeypatch.setattr(demo_routes, "get_openspg_schema_graph", fake_get_schema_graph)
    monkeypatch.setattr(demo_routes, "get_openspg_reason_schema", fake_get_reason_schema, raising=False)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/model-studio/schema/apply",
        json={
            "project_id": 1,
            "schema_script": (
                "namespace CompanyModelStudio\n\n"
                "Company(企业): EntityType\n"
                "\tproperties:\n"
                "\t\tname(企业名称): Text\n"
                "\t\t\tdescription(企业描述): Text\n"
            ),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["schema_apply_result"]["mode"] == "live"
    assert data["schema_apply_result"]["meta"]["apply_mode"] == "public_alter_schema_fallback"
    assert data["schema_model"]["entity_count"] == 1
    assert "Company" in data["schema_model"]["entity_names"]

    draft = captured["schema_draft"]
    assert isinstance(draft.get("alterSpgTypes"), list)
    assert draft["alterSpgTypes"][0]["basicInfo"]["name"]["namespace"] == "zhilian"
    assert draft["alterSpgTypes"][0]["basicInfo"]["name"]["nameEn"] == "Company"


def test_model_studio_extraction_flow_endpoints(monkeypatch):
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    async def fake_upload_reasoner_file(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": {
                    "name": kwargs.get("filename", "upload.md"),
                    "fileUrl": "/tmp/openspg_upload/upload.md",
                    "type": kwargs.get("file_type", "md"),
                },
            },
            "request": kwargs,
        }

    async def fake_submit_builder(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": {
                    "id": 9527,
                    "taskId": 2048,
                    "projectId": kwargs.get("project_id", 1),
                    "status": "RUNNING",
                    "jobName": "KAG_BUILDER_TEST",
                },
            },
            "request": kwargs,
        }

    async def fake_get_builder_job(*, job_id: int):
        assert job_id == 9527
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": {
                    "id": 9527,
                    "projectId": 1,
                    "taskId": 2048,
                    "status": "RUNNING",
                    "jobName": "KAG_BUILDER_TEST",
                },
            },
            "request": {"job_id": job_id},
        }

    async def fake_search_instances(*, task_id: int, project_id: int):
        assert task_id == 2048
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": {
                    "results": [
                        {
                            "id": 3001,
                            "jobId": 2048,
                            "projectId": project_id,
                            "status": "RUNNING",
                            "extension": {
                                "llmTokenInfo": {
                                    "prompt_tokens": 321,
                                    "completion_tokens": 123,
                                    "total_tokens": 444,
                                    "prompts": [
                                        {
                                            "model": "Qwen/Qwen2.5-32B-Instruct",
                                            "api_base": "https://api.siliconflow.cn/v1",
                                            "prompt_name": "knowledge_unit_ner",
                                            "prompt": "实际生成的抽取提示词",
                                            "timestamp": "2026-02-28T10:00:00+08:00",
                                        }
                                    ],
                                }
                            },
                        }
                    ],
                    "total": 1,
                },
            },
            "request": {"task_id": task_id, "project_id": project_id},
        }

    async def fake_search_tasks(*, instance_id: int, project_id: int):
        assert instance_id == 3001
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": {
                    "results": [
                        {
                            "id": 4001,
                            "instanceId": instance_id,
                            "projectId": project_id,
                            "type": "Reader",
                            "status": "FINISH",
                            "traceLog": "Reader finished",
                        },
                        {
                            "id": 4002,
                            "instanceId": instance_id,
                            "projectId": project_id,
                            "type": "Extractor",
                            "status": "RUNNING",
                            "traceLog": "Extractor running",
                        },
                    ],
                    "total": 2,
                },
            },
            "request": {"instance_id": instance_id, "project_id": project_id},
        }

    async def fake_get_sample(*, project_id: int, job_id: int):
        assert project_id == 1
        assert job_id == 9527
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": {
                    "resultNodes": [
                        {
                            "id": "entity-1",
                            "label": "Company",
                            "properties": {"name": "智链机器人有限公司", "content": "样例内容"},
                        }
                    ],
                    "resultEdges": [],
                },
            },
            "request": {"project_id": project_id, "job_id": job_id},
        }

    monkeypatch.setattr(demo_routes, "upload_openspg_reasoner_file", fake_upload_reasoner_file)
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_legacy_job", fake_submit_builder)
    monkeypatch.setattr(demo_routes, "get_openspg_builder_job", fake_get_builder_job)
    monkeypatch.setattr(demo_routes, "search_openspg_scheduler_instances", fake_search_instances)
    monkeypatch.setattr(demo_routes, "search_openspg_scheduler_tasks", fake_search_tasks)
    monkeypatch.setattr(demo_routes, "get_openspg_builder_sample", fake_get_sample)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    submit_res = client.post(
        "/api/v1/openspg-demo/model-studio/extraction/submit",
        json={
            "project_id": 1,
            "text_content": "智链机器人有限公司与某车企达成合作。",
            "job_name": "company_extract_demo",
        },
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert submit_data["builder_submit_result"]["mode"] == "live"
    assert submit_data["job"]["id"] == 9527
    assert submit_data["file_suffix"] == "md"
    assert submit_data["upload_result"]["mode"] == "live"
    assert submit_data["builder_extension"]["extractConfig"]["autoSchema"] is False

    status_res = client.get(
        "/api/v1/openspg-demo/model-studio/extraction/status",
        params={"project_id": 1, "job_id": 9527},
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["job"]["id"] == 9527
    assert status_data["instances_total"] == 1
    assert status_data["tasks_total"] == 2
    assert len(status_data["tasks"]) == 2
    assert status_data["llm_trace"]["model"] == "Qwen/Qwen2.5-32B-Instruct"
    assert status_data["llm_trace"]["total_tokens"] == 444
    assert "实际生成的抽取提示词" in status_data["llm_trace"]["prompt"]

    sample_res = client.get(
        "/api/v1/openspg-demo/model-studio/extraction/sample",
        params={"project_id": 1, "job_id": 9527},
    )
    assert sample_res.status_code == 200
    sample_data = sample_res.json()
    assert len(sample_data["result_nodes"]) == 1
    assert sample_data["entities"][0]["name"] == "智链机器人有限公司"
    assert "llm_trace" in sample_data


def test_model_studio_extraction_submit_file_endpoint(monkeypatch):
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    async def fake_upload_reasoner_file(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": {"fileUrl": "/tmp/openspg_upload/new1.md", "type": "md"},
            },
            "request": kwargs,
        }

    async def fake_submit_builder(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": {"id": 9001, "taskId": 7001, "status": "RUNNING"}},
            "request": kwargs,
        }

    monkeypatch.setattr(demo_routes, "upload_openspg_reasoner_file", fake_upload_reasoner_file)
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_legacy_job", fake_submit_builder)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/model-studio/extraction/submit-file",
        files={"file": ("new1.md", b"# test\nhello", "text/markdown")},
        data={
            "project_id": "1",
            "job_name": "upload_job",
            "worker_num": "1",
            "split_length": "500",
            "semantic_split": "false",
            "schema_constrained_extract": "true",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["job"]["id"] == 9001
    assert data["file_suffix"] == "md"


def test_model_studio_extraction_submit_file_endpoint_with_string_upload_result(monkeypatch):
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    async def fake_upload_reasoner_file(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {
                "success": True,
                "result": "http://release-openspg-minio:9000/builder/platform/md/abc/new1.md",
            },
            "request": kwargs,
        }

    async def fake_submit_builder(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": {"id": 9002, "taskId": 7002, "status": "RUNNING"}},
            "request": kwargs,
        }

    monkeypatch.setattr(demo_routes, "upload_openspg_reasoner_file", fake_upload_reasoner_file)
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_legacy_job", fake_submit_builder)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/openspg-demo/model-studio/extraction/submit-file",
        files={"file": ("new1.md", b"# test\nhello", "text/markdown")},
        data={
            "project_id": "1",
            "job_name": "upload_job_string_result",
            "worker_num": "1",
            "split_length": "500",
            "semantic_split": "false",
            "schema_constrained_extract": "true",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["job"]["id"] == 9002
    assert data["file_url"].startswith("http://release-openspg-minio:9000/")


def test_model_studio_schema_activate_and_get_active(monkeypatch):
    from app.openspg_demo.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    activate_res = client.post(
        "/api/v1/openspg-demo/model-studio/schema/activate",
        json={
            "project_id": 1,
            "schema_script": "namespace Demo\n\nCompany(企业): EntityType",
            "label": "model-v1",
        },
    )
    assert activate_res.status_code == 200
    activate_data = activate_res.json()
    assert activate_data["project_id"] == 1
    assert activate_data["label"] == "model-v1"
    assert activate_data["schema_hash"]
    assert activate_data["schema_script"].startswith("namespace Demo")

    active_res = client.get("/api/v1/openspg-demo/model-studio/schema/active", params={"project_id": 1})
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["project_id"] == 1
    assert active_data["model_profile_id"] == activate_data["model_profile_id"]
    assert active_data["schema_hash"] == activate_data["schema_hash"]
    assert active_data["schema_script"].startswith("namespace Demo")


def test_model_studio_schema_current_falls_back_to_cached_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    async def fake_schema_script(**kwargs):
        raise RuntimeError("schema script timeout")

    async def fake_schema_graph(**kwargs):
        raise RuntimeError("schema graph timeout")

    async def fake_reason_schema(**kwargs):
        raise RuntimeError("reason schema timeout")

    monkeypatch.setattr(demo_routes, "get_openspg_schema_script", fake_schema_script)
    monkeypatch.setattr(demo_routes, "get_openspg_schema_graph", fake_schema_graph)
    monkeypatch.setattr(demo_routes, "get_openspg_reason_schema", fake_reason_schema)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    activate_res = client.post(
        "/api/v1/openspg-demo/model-studio/schema/activate",
        json={
            "project_id": 1,
            "schema_script": "namespace Demo\n\nCompany(企业): EntityType",
            "label": "schema-current-cache",
        },
    )
    assert activate_res.status_code == 200

    current_res = client.get(
        "/api/v1/openspg-demo/model-studio/schema/current",
        params={"project_id": 1},
    )
    assert current_res.status_code == 200
    current_data = current_res.json()
    assert current_data["schema_script"].startswith("namespace Demo")
    assert current_data["meta"]["fallback_mode"] == "cached_model_profile"


def test_workflow_news_run_and_status_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import get_demo_news_samples
    from app.openspg_demo.routes import router

    started = {}

    def fake_pull(max_entries_per_feed: int, hours_ago: int):
        return {
            "status": "success",
            "fetched_count": 4,
            "inserted_count": 3,
            "duplicate_count": 1,
            "max_entries_per_feed": max_entries_per_feed,
            "hours_ago": hours_ago,
        }

    async def fake_submit_builder(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": {"taskId": 12345}},
            "request": kwargs,
        }

    def fake_start(run_id, request_payload, active_model_profile):
        started["run_id"] = run_id
        started["request"] = request_payload
        started["active_model_profile"] = active_model_profile

    monkeypatch.setattr(demo_routes, "pull_rss_articles_to_mongo", fake_pull)
    monkeypatch.setattr(
        demo_routes,
        "_read_news_rows",
        lambda limit=200, allow_demo_fallback=False: (get_demo_news_samples(), "demo-fallback"),
    )
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_job", fake_submit_builder)
    monkeypatch.setattr(demo_routes, "_start_workflow_job", fake_start, raising=False)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    run_res = client.post(
        "/api/v1/openspg-demo/workflow/news/run",
        json={
            "project_id": 1,
            "max_entries_per_feed": 2,
            "hours_ago": 6,
            "bridge_limit": 20,
            "force_full": True,
            "submit_builder": True,
        },
    )
    assert run_res.status_code == 202
    run_data = run_res.json()
    assert run_data["run_id"]
    assert run_data["project_id"] == 1
    assert run_data["status"] == "queued"
    assert run_data["active_model_profile"] is None
    assert started["run_id"] == run_data["run_id"]
    assert started["request"]["bridge_limit"] == 20

    status_res = client.get(f"/api/v1/openspg-demo/workflow/news/runs/{run_data['run_id']}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["run_id"] == run_data["run_id"]
    assert status_data["status"] == "queued"
    assert status_data["active_model_profile"] is None


def test_workflow_news_history_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import get_demo_news_samples
    from app.openspg_demo.routes import router

    def fake_pull(max_entries_per_feed: int, hours_ago: int):
        return {
            "status": "success",
            "fetched_count": 4,
            "inserted_count": 3,
            "duplicate_count": 1,
            "max_entries_per_feed": max_entries_per_feed,
            "hours_ago": hours_ago,
        }

    async def fake_apply_schema(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": True},
            "request": kwargs,
        }

    async def fake_submit_builder(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": {"taskId": 12345}},
            "request": kwargs,
        }

    monkeypatch.setattr(demo_routes, "pull_rss_articles_to_mongo", fake_pull)
    monkeypatch.setattr(
        demo_routes,
        "_read_news_rows",
        lambda limit=200, allow_demo_fallback=False: (get_demo_news_samples(), "demo-fallback"),
    )
    monkeypatch.setattr(demo_routes, "_apply_schema_with_public_fallback", fake_apply_schema)
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_job", fake_submit_builder)
    monkeypatch.setattr(demo_routes, "_start_workflow_job", lambda run_id, request_payload, active_model_profile: None, raising=False)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    activate_res = client.post(
        "/api/v1/openspg-demo/model-studio/schema/activate",
        json={
            "project_id": 1,
            "schema_script": "namespace Demo\n\nCompany(企业): EntityType",
            "label": "workflow-active",
        },
    )
    assert activate_res.status_code == 200

    run1_res = client.post(
        "/api/v1/openspg-demo/workflow/news/run",
        json={"project_id": 1, "max_entries_per_feed": 2, "hours_ago": 6, "bridge_limit": 20},
    )
    assert run1_res.status_code == 202
    run1_id = run1_res.json()["run_id"]

    run2_res = client.post(
        "/api/v1/openspg-demo/workflow/news/run",
        json={"project_id": 1, "max_entries_per_feed": 3, "hours_ago": 12, "bridge_limit": 20},
    )
    assert run2_res.status_code == 202
    run2_id = run2_res.json()["run_id"]

    history_res = client.get(
        "/api/v1/openspg-demo/workflow/news/history",
        params={"project_id": 1, "limit": 1},
    )
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["project_id"] == 1
    assert history_data["total"] >= 2
    assert len(history_data["runs"]) == 1
    assert history_data["runs"][0]["run_id"] == run2_id
    assert history_data["runs"][0]["run_id"] != run1_id


def test_execute_workflow_job_fails_when_openks_schema_commit_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import get_demo_news_samples

    def fake_pull(max_entries_per_feed: int, hours_ago: int):
        return {
            "status": "success",
            "fetched_count": 4,
            "inserted_count": 3,
            "duplicate_count": 1,
            "max_entries_per_feed": max_entries_per_feed,
            "hours_ago": hours_ago,
        }

    async def fake_apply_openks_news_kg_schema(**kwargs):
        raise RuntimeError("cannot find project with id=1")

    submit_called = {"count": 0}

    async def fake_submit_builder(**kwargs):
        submit_called["count"] += 1
        return {
            "mode": "live",
            "http_status": 200,
            "response": {"success": True, "result": {"taskId": 12345}},
            "request": kwargs,
        }

    monkeypatch.setattr(demo_routes, "pull_rss_articles_to_mongo", fake_pull)
    monkeypatch.setattr(
        demo_routes,
        "_read_news_rows",
        lambda limit=200, allow_demo_fallback=False: (get_demo_news_samples(), "demo-fallback"),
    )
    monkeypatch.setattr(demo_routes, "apply_openks_news_kg_schema", fake_apply_openks_news_kg_schema)
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_job", fake_submit_builder)

    active_profile = demo_routes._activate_model_profile(
        project_id=1,
        schema_script="namespace Demo\n\nCompany(企业): EntityType",
        label="workflow-active",
        source="test",
    )
    request_payload = demo_routes.WorkflowNewsRunRequest(
        project_id=1,
        max_entries_per_feed=2,
        hours_ago=6,
        bridge_limit=20,
        force_full=True,
        submit_builder=True,
        apply_schema=True,
        worker_num=1,
    ).model_dump()
    run_id = "wf_test_partial"
    demo_routes._save_workflow_run(
        {
            "run_id": run_id,
            "project_id": 1,
            "status": "queued",
            "started_at": demo_routes._utc_now_iso(),
            "active_model_profile": active_profile,
            "request": request_payload,
        }
    )

    asyncio.run(demo_routes._execute_workflow_job(run_id, request_payload, active_profile))

    run_data = demo_routes._get_workflow_run(run_id)
    assert run_data["status"] == "failed"
    assert "cannot find project with id=1" in run_data["error"]
    assert submit_called["count"] == 0


def test_execute_workflow_job_records_runtime_binding_release_for_kag_openspg(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import get_demo_news_samples

    class _FakeBridgeRunner:
        def run_export(self, rows, limit=200, force_full=False):
            return {
                "run_id": "extract_success_1",
                "batch_file_path": "/tmp/extract_success_1.jsonl",
                "batch_file_name": "extract_success_1.jsonl",
                "export_count": 6,
                "run_time": "2026-03-17T12:00:00",
            }

        def get_status(self):
            return {"cursor": {"last_seen_time": "2026-03-17T12:00:00"}, "last_run": {"run_id": "extract_success_1"}}

    def fake_pull(max_entries_per_feed: int, hours_ago: int):
        return {
            "status": "success",
            "fetched_count": 4,
            "inserted_count": 3,
            "duplicate_count": 1,
            "max_entries_per_feed": max_entries_per_feed,
            "hours_ago": hours_ago,
        }

    async def fake_apply_openks_news_kg_schema(**kwargs):
        return {
            "schema_source": "openks_module",
            "compiled_schema_script": "namespace OpenKSNews\n\nNewsDocument(资讯文档): EntityType\n",
            "kag_schema_export": {
                "namespace": "OpenKSNews",
                "project_dir": "modules/kag/kag/examples/OpenKSNews",
                "schema_path": "modules/kag/kag/examples/OpenKSNews/schema/OpenKSNews.schema",
            },
            "schema_commit_result": {
                "mode": "openks_sync_schema",
                "http_status": 200,
                "committed": True,
                "response": {"success": True, "result": True},
                "meta": {"effective_success": True},
            },
            "schema_apply_result": {
                "mode": "openks_sync_schema",
                "http_status": 200,
                "committed": True,
                "response": {"success": True, "result": True},
                "meta": {"effective_success": True},
            },
            "activate_result": {
                "project_id": kwargs["project_id"],
                "label": kwargs["activate_label"],
                "source": "openks_module",
                "model_profile_id": "mp_1",
                "schema_hash": "hash_1",
                "schema_script": "namespace OpenKSNews\n\nNewsDocument(资讯文档): EntityType\n",
            },
            "active_model_profile": {
                "project_id": kwargs["project_id"],
                "label": kwargs["activate_label"],
                "source": "openks_module",
                "model_profile_id": "mp_1",
                "schema_hash": "hash_1",
                "schema_script": "namespace OpenKSNews\n\nNewsDocument(资讯文档): EntityType\n",
            },
        }

    async def fake_submit_builder(**kwargs):
        return {
            "mode": "live",
            "http_status": 200,
            "job_id": 12345,
            "response": {"success": True, "result": {"taskId": 12345}},
            "request": kwargs,
        }

    async def fake_materialize_graph_for_bridge_run(*, bridge_run, project_id):
        return {
            "status": "success",
            "vertices": 12,
            "edges": 8,
            "project_id": project_id,
            "bridge_run_id": bridge_run["run_id"],
        }

    def fake_register_workflow_runtime_binding(**kwargs):
        return {
            "run": {"run_id": "KRUN_KAG_success_1"},
            "artifact": {"artifact_id": "KART_KAG_success_1"},
            "release": {"release_id": "KREL_KAG_success_1", "status": "draft"},
        }

    monkeypatch.setattr(demo_routes, "pull_rss_articles_to_mongo", fake_pull)
    monkeypatch.setattr(
        demo_routes,
        "_read_news_rows",
        lambda limit=200, allow_demo_fallback=False: (get_demo_news_samples(), "demo-fallback"),
    )
    monkeypatch.setattr(demo_routes, "apply_openks_news_kg_schema", fake_apply_openks_news_kg_schema)
    monkeypatch.setattr(demo_routes, "_bridge_runner", lambda: _FakeBridgeRunner())
    monkeypatch.setattr(
        demo_routes,
        "build_builder_envs_for_run",
        lambda run_result, project_id: {"OPENSPG_DEMO_BATCH_FILE": run_result["batch_file_path"], "OPENSPG_DEMO_PROJECT_ID": str(project_id)},
    )
    monkeypatch.setattr(demo_routes, "submit_openspg_builder_job", fake_submit_builder)
    monkeypatch.setattr(demo_routes, "_materialize_graph_for_bridge_run", fake_materialize_graph_for_bridge_run)
    monkeypatch.setattr(demo_routes, "register_workflow_runtime_binding", fake_register_workflow_runtime_binding)

    request_payload = demo_routes.WorkflowNewsRunRequest(
        project_id=1,
        max_entries_per_feed=2,
        hours_ago=6,
        bridge_limit=20,
        force_full=True,
        submit_builder=True,
        apply_schema=True,
        materialize_graph=True,
        worker_num=1,
    ).model_dump()
    run_id = "wf_test_success"
    demo_routes._save_workflow_run(
        {
            "run_id": run_id,
            "project_id": 1,
            "status": "queued",
            "started_at": demo_routes._utc_now_iso(),
            "request": request_payload,
        }
    )

    asyncio.run(demo_routes._execute_workflow_job(run_id, request_payload, None))

    run_data = demo_routes._get_workflow_run(run_id)
    assert run_data["status"] == "success"
    assert run_data["schema_source"] == "openks_module"
    assert run_data["compiled_schema_script"].startswith("namespace OpenKSNews")
    assert run_data["runtime_binding"]["release"]["release_id"] == "KREL_KAG_success_1"
    assert run_data["step_statuses"]["execute"]["status"] == "success"


def test_workflow_step_detail_endpoint_returns_model_graph(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    schema_script = """
namespace Demo

Document(资讯文档): EntityType
    relations:
        mentionsCompany(提及公司): Company
Company(公司): EntityType
""".strip()
    active_profile = demo_routes._activate_model_profile(
        project_id=1,
        schema_script=schema_script,
        label="detail-model",
        source="test",
    )
    run_id = "wf_detail_model"
    demo_routes._save_workflow_run(
        {
            "run_id": run_id,
            "project_id": 1,
            "status": "success",
            "started_at": demo_routes._utc_now_iso(),
            "finished_at": demo_routes._utc_now_iso(),
            "request": {"project_id": 1, "hours_ago": 24, "headlines_top_n": 10},
            "active_model_profile": active_profile,
            "schema_apply_result": {
                "mode": "live",
                "http_status": 200,
                "response": {"success": True},
                "meta": {"effective_success": True},
            },
            "step_statuses": {
                "model": {"status": "success"},
                "collect": {"status": "success"},
                "process": {"status": "success"},
                "extract": {"status": "success"},
                "execute": {"status": "success"},
                "apply": {"status": "success"},
            },
        }
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.get(f"/api/v1/openspg-demo/workflow/news/runs/{run_id}/steps/model")
    assert res.status_code == 200
    data = res.json()
    assert data["meta"]["step_key"] == "model"
    assert data["visualization"]["type"] == "graph"
    assert len(data["visualization"]["data"]["nodes"]) >= 2
    assert len(data["visualization"]["data"]["edges"]) >= 1
    assert data["output"]["table"]["rows"][0]["type_name"]


def test_workflow_step_detail_endpoint_returns_apply_graph(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import build_headlines_from_news, get_demo_news_samples
    from app.openspg_demo.routes import router

    rows = get_demo_news_samples()
    headlines = build_headlines_from_news(rows, top_n=5, hours=24)
    run_id = "wf_detail_apply"
    demo_routes._save_workflow_run(
        {
            "run_id": run_id,
            "project_id": 1,
            "status": "success",
            "started_at": demo_routes._utc_now_iso(),
            "finished_at": demo_routes._utc_now_iso(),
            "request": {"project_id": 1, "hours_ago": 24, "headlines_top_n": 5},
            "headlines_snapshot": {
                "stats": headlines.get("stats") or {},
                "top_headline_ids": [
                    item.get("event_id") for item in (headlines.get("headlines") or [])[:3]
                ],
            },
            "step_statuses": {
                "model": {"status": "success"},
                "collect": {"status": "success"},
                "process": {"status": "success"},
                "extract": {"status": "success"},
                "execute": {"status": "success"},
                "apply": {"status": "success"},
            },
        }
    )
    monkeypatch.setattr(
        demo_routes,
        "_read_news_rows",
        lambda limit=200, allow_demo_fallback=False: (rows, "demo-fallback"),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.get(f"/api/v1/openspg-demo/workflow/news/runs/{run_id}/steps/apply")
    assert res.status_code == 200
    data = res.json()
    assert data["meta"]["step_key"] == "apply"
    assert data["visualization"]["type"] == "graph"
    assert len(data["output"]["table"]["rows"]) >= 1
    assert len(data["visualization"]["data"]["nodes"]) >= 1
    node_ids = {item["id"] for item in data["visualization"]["data"]["nodes"]}
    for edge in data["visualization"]["data"]["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


def test_workflow_step_detail_endpoint_returns_collect_business_rows(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.headlines_service import get_demo_news_samples
    from app.openspg_demo.routes import router

    rows = get_demo_news_samples()[:5]
    run_id = "wf_detail_collect"
    demo_routes._save_workflow_run(
        {
            "run_id": run_id,
            "project_id": 1,
            "status": "success",
            "started_at": demo_routes._utc_now_iso(),
            "finished_at": demo_routes._utc_now_iso(),
            "request": {"project_id": 1, "hours_ago": 24, "max_entries_per_feed": 2},
            "ingest_result": {
                "fetched_count": 5,
                "inserted_count": 2,
                "duplicate_count": 3,
                "pull_mode": "rss_parser",
            },
            "step_statuses": {
                "model": {"status": "success"},
                "collect": {"status": "success"},
                "process": {"status": "success"},
                "extract": {"status": "success"},
                "execute": {"status": "success"},
                "apply": {"status": "success"},
            },
        }
    )
    monkeypatch.setattr(
        demo_routes,
        "_read_news_rows",
        lambda limit=200, allow_demo_fallback=False: (rows, "demo-fallback"),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.get(f"/api/v1/openspg-demo/workflow/news/runs/{run_id}/steps/collect")
    assert res.status_code == 200
    data = res.json()
    assert data["output"]["table"]["rows"][0]["doc_id"]
    assert data["output"]["table"]["rows"][0]["source_name"]
    assert data["output"]["table"]["rows"][0]["publish_time"]


def test_workflow_step_detail_endpoint_returns_execute_business_tables(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    run_id = "wf_detail_execute"
    demo_routes._save_workflow_run(
        {
            "run_id": run_id,
            "project_id": 1,
            "status": "success",
            "started_at": demo_routes._utc_now_iso(),
            "finished_at": demo_routes._utc_now_iso(),
            "request": {"project_id": 1},
            "bridge_run": {
                "batch_file_name": "batch.jsonl",
            },
            "builder_submit_result": {
                "mode": "live",
                "http_status": 200,
                "request": {
                    "json": {
                        "projectId": 1,
                        "workerNum": 1,
                    }
                },
                "response": {
                    "success": True,
                    "traceId": "trace_x",
                },
                "meta": {"effective_success": True},
            },
            "step_statuses": {
                "model": {"status": "success"},
                "collect": {"status": "success"},
                "process": {"status": "success"},
                "extract": {"status": "success"},
                "execute": {"status": "success"},
                "apply": {"status": "success"},
            },
        }
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.get(f"/api/v1/openspg-demo/workflow/news/runs/{run_id}/steps/execute")
    assert res.status_code == 200
    data = res.json()
    assert data["input"]["table"]["rows"][0]["field"] == "projectId"
    assert data["output"]["table"]["rows"][0]["field"]


def test_workflow_step_detail_endpoint_returns_extract_graph_without_orphan_edges(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENSPG_DEMO_DATA_DIR", str(tmp_path))
    from app.openspg_demo import routes as demo_routes
    from app.openspg_demo.routes import router

    rows = [
        {
            "doc_id": f"DOC_{idx}",
            "title": f"头部人形机器人关节公司完成C+轮融资, 单品销量第一, 年营收翻倍 {idx}",
            "content": "头部人形机器人关节公司完成C+轮融资, 单品销量第一, 年营收翻倍",
            "source_name": "crawler_36kr",
        }
        for idx in range(20)
    ]
    run_id = "wf_detail_extract_orphan"
    demo_routes._save_workflow_run(
        {
            "run_id": run_id,
            "project_id": 1,
            "status": "success",
            "started_at": demo_routes._utc_now_iso(),
            "finished_at": demo_routes._utc_now_iso(),
            "bridge_run": {
                "run_id": "extract_run",
                "batch_file_name": "batch.jsonl",
                "export_count": 20,
            },
            "step_statuses": {
                "model": {"status": "success"},
                "collect": {"status": "success"},
                "process": {"status": "success"},
                "extract": {"status": "success"},
                "execute": {"status": "success"},
                "apply": {"status": "success"},
            },
        }
    )
    monkeypatch.setattr(demo_routes, "_load_batch_records_for_run", lambda run_payload, limit=20: rows[:limit])

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.get(f"/api/v1/openspg-demo/workflow/news/runs/{run_id}/steps/extract")
    assert res.status_code == 200
    data = res.json()
    node_ids = {item["id"] for item in data["visualization"]["data"]["nodes"]}
    for edge in data["visualization"]["data"]["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
