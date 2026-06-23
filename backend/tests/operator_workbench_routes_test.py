from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakePublishedPipelineRepo:
    def __init__(self):
        self.rows = []

    def ensure_builtin_pipelines(self, templates):
        existing = {row["key"] for row in self.rows}
        for template in templates:
            if template["key"] in existing:
                continue
            edges = [
                {
                    "source": edge.get("source") or edge.get("from"),
                    "target": edge.get("target") or edge.get("to"),
                }
                for edge in template.get("edges", [])
            ]
            self.rows.append(
                {
                    "key": template["key"],
                    "name": template["name"],
                    "description": template.get("description", ""),
                    "source_types": list(template.get("source_types", [])),
                    "nodes": list(template.get("nodes", [])),
                    "edges": edges,
                    "operators": [node["operator"] for node in template.get("nodes", [])],
                    "is_builtin": True,
                    "published_by": "system",
                    "created_at": "2026-04-13T00:00:00Z",
                    "updated_at": "2026-04-13T00:00:00Z",
                }
            )

    def list_pipelines(self):
        return list(self.rows)

    def publish_pipeline(self, request):
        row = {
            "key": f"published-{len(self.rows) + 1}",
            "name": request.name,
            "description": request.description,
            "source_types": list(request.source_types),
            "nodes": [node.model_dump() for node in request.nodes],
            "edges": [
                {"source": request.nodes[index].key, "target": request.nodes[index + 1].key}
                for index in range(len(request.nodes) - 1)
            ],
            "operators": [node.operator for node in request.nodes],
            "is_builtin": False,
            "published_by": request.published_by,
            "created_at": "2026-04-13T00:00:00Z",
            "updated_at": "2026-04-13T00:00:00Z",
        }
        self.rows.append(row)
        return row


def _build_client() -> TestClient:
    from app.api import operator_workbench_routes

    app = FastAPI()
    operator_workbench_routes.published_pipeline_repo = _FakePublishedPipelineRepo()
    app.include_router(operator_workbench_routes.router, prefix="/api/v1")
    return TestClient(app)


def test_operator_workbench_catalog():
    client = _build_client()

    response = client.get("/api/v1/operator-workbench/catalog")
    assert response.status_code == 200

    payload = response.json()
    assert "operators" in payload
    assert "dto_schemas" in payload

    operators = payload["operators"]
    names = {item["name"] for item in operators}
    assert "source_record_map" in names
    assert "graph_import" in names
    assert "pdf_source_ingest" in names
    assert "webpage_source_ingest" in names
    assert "table_extract" in names
    assert "entity_extract" in names
    assert "relation_extract" in names
    assert "event_extract" in names
    assert len(operators) >= 20

    source_map = next(item for item in operators if item["name"] == "source_record_map")
    assert source_map["agent_callable"] is True
    assert source_map["input_type"] == "SourceRecordListDTO"
    assert "properties" in source_map["input_schema"]
    assert "properties" in source_map["output_schema"]
    assert source_map["status"] == "implemented"
    assert source_map["knowledge_category"] == "data_preprocessing_structuring"
    assert source_map["operator_class"] == "general"

    pdf_ingest = next(item for item in operators if item["name"] == "pdf_source_ingest")
    assert pdf_ingest["status"] == "implemented"
    assert pdf_ingest["knowledge_category"] == "data_ingestion_loading"
    assert pdf_ingest["operator_class"] == "general"
    assert pdf_ingest["agent_callable"] is True

    entity_resolve = next(item for item in operators if item["name"] == "entity_resolve")
    assert entity_resolve["knowledge_category"] == "knowledge_alignment_standardization"
    assert entity_resolve["operator_class"] == "business"

    graph_import = next(item for item in operators if item["name"] == "graph_import")
    assert graph_import["knowledge_category"] == "knowledge_fusion_graph_build"
    assert graph_import["operator_class"] == "general"


def test_operator_workbench_overview():
    client = _build_client()

    response = client.get("/api/v1/operator-workbench/overview")
    assert response.status_code == 200

    payload = response.json()
    assert "operators" in payload
    assert "dto_schemas" in payload
    assert "pipelines" in payload
    assert "published_pipelines" in payload
    assert "layers" in payload

    pipelines = payload["pipelines"]
    keys = {item["key"] for item in pipelines}
    assert {
        "news_event_pipeline",
        "report_extraction_pipeline",
        "structured_fusion_pipeline",
        "pdf_report_full_pipeline",
        "web_news_full_pipeline",
    }.issubset(keys)

    news_pipeline = next(item for item in pipelines if item["key"] == "news_event_pipeline")
    assert news_pipeline["nodes"]
    assert news_pipeline["edges"]
    assert news_pipeline["nodes"][0]["operator"] == "source_record_map"

    pdf_pipeline = next(item for item in pipelines if item["key"] == "pdf_report_full_pipeline")
    assert pdf_pipeline["nodes"][0]["operator"] == "pdf_source_ingest"
    assert pdf_pipeline["nodes"][-1]["operator"] == "entity_standardize"

    layers = payload["layers"]
    assert [item["key"] for item in layers] == [
        "data_ingestion_loading",
        "data_preprocessing_structuring",
        "knowledge_extraction",
        "knowledge_alignment_standardization",
        "knowledge_fusion_graph_build",
        "knowledge_retrieval_recall",
        "reasoning_decision_generation",
    ]
    assert all("operator_classes" in item for item in layers)
    assert payload["published_pipelines"]
    assert payload["published_pipelines"][0]["is_builtin"] is True


def test_operator_workbench_templates_only_use_implemented_operators_and_validate():
    client = _build_client()

    overview = client.get("/api/v1/operator-workbench/overview").json()
    operator_map = {item["name"]: item for item in overview["operators"]}

    for pipeline in overview["pipelines"]:
        operator_names = [node["operator"] for node in pipeline["nodes"]]
        assert operator_names, pipeline["key"]
        assert all(operator_map[name]["status"] == "implemented" for name in operator_names), pipeline["key"]

        response = client.post("/api/v1/operator-workbench/validate", json={"operators": operator_names})
        assert response.status_code == 200, pipeline["key"]
        payload = response.json()
        assert payload["valid"] is True, pipeline["key"]
        codes = {item["code"] for item in payload["issues"]}
        assert "TYPE_MISMATCH" not in codes, pipeline["key"]
        assert "INVALID_START_OPERATOR" not in codes, pipeline["key"]


def test_operator_workbench_validate_pipeline_success():
    client = _build_client()

    response = client.post(
        "/api/v1/operator-workbench/validate",
        json={
            "operators": [
                "pdf_source_ingest",
                "pdf_parse",
                "document_clean",
            ]
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["valid"] is True
    assert payload["summary"]["error_count"] == 0
    assert payload["summary"]["warning_count"] >= 1
    assert any(item["code"] == "PIPELINE_NOT_TERMINATED" for item in payload["issues"])


def test_operator_workbench_validate_pipeline_allows_chunk_stream_operators():
    client = _build_client()

    response = client.post(
        "/api/v1/operator-workbench/validate",
        json={
            "operators": [
                "markdown_source_ingest",
                "markdown_normalize",
                "document_clean",
                "chunk_split",
                "entity_extract",
                "event_extract",
            ]
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["valid"] is True
    codes = {item["code"] for item in payload["issues"]}
    assert "TYPE_MISMATCH" not in codes


def test_operator_workbench_execute_preview_runs_markdown_chain():
    client = _build_client()

    response = client.post(
        "/api/v1/operator-workbench/execute-preview",
        json={
            "operators": [
                "markdown_source_ingest",
                "markdown_normalize",
                "document_clean",
                "chunk_split",
                "entity_extract",
                "event_extract",
            ],
            "input_type": "MarkdownSourceDTO",
            "input_payload": {
                "source_id": "md_exec_001",
                "source_type": "markdown",
                "location": "inline://markdown",
                "title": "执行预览样例",
                "source_name": "测试来源",
                "markdown_text": "# 标题\n\n上海某某机器人科技有限公司完成B轮融资，投资方为某产业基金。",
            },
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["valid"] is True
    assert payload["steps"]
    assert payload["steps"][0]["operator"] == "markdown_source_ingest"
    assert payload["steps"][-1]["operator"] == "event_extract"
    assert payload["steps"][3]["output_type"] == "ChunkListDTO"
    assert payload["steps"][4]["summary"]["entity_count"] >= 2
    assert payload["steps"][5]["summary"]["event_count"] >= 1
    assert payload["final_output_type"] == "EventSeedListDTO"


def test_operator_workbench_execute_preview_runs_news_event_template():
    client = _build_client()

    response = client.post(
        "/api/v1/operator-workbench/execute-preview",
        json={
            "operators": [
                "source_record_map",
                "event_enrich",
                "entity_resolve",
                "event_resolve",
                "fusion_graph_build",
                "graph_import",
            ],
            "input_type": "SourceRecordListDTO",
            "input_payload": {
                "records": [
                    {
                        "source_system": "operator-workbench",
                        "source_table": "preview_news",
                        "record_id": "record_001",
                        "record_type": "document",
                        "payload": {
                            "doc_type": "news",
                            "title": "机器人企业融资快讯",
                            "content": "上海某某机器人科技有限公司宣布完成B轮融资，投资方为某产业基金。",
                            "source_name": "工作台样例",
                            "source_type": "news",
                        },
                    }
                ]
            },
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["valid"] is True
    assert payload["final_output_type"] == "GraphImportOutputDTO"
    assert payload["steps"][-1]["operator"] == "graph_import"


def test_operator_workbench_execute_preview_rejects_unimplemented_operator():
    client = _build_client()

    response = client.post(
        "/api/v1/operator-workbench/execute-preview",
        json={
            "operators": [
                "pdf_source_ingest",
                "pdf_parse",
                "outline_extract",
            ],
            "input_type": "PdfSourceDTO",
            "input_payload": {
                "source_id": "pdf_exec_001",
                "source_type": "pdf",
                "location": "/tmp/fake.pdf",
                "title": "执行预览样例",
                "source_name": "测试来源",
                "metadata": {
                    "raw_text": "某公司发布研报。",
                },
            },
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["valid"] is False
    assert any(item["code"] == "UNIMPLEMENTED_OPERATOR" for item in payload["issues"])


def test_operator_workbench_validate_pipeline_detects_contract_issues():
    client = _build_client()

    response = client.post(
        "/api/v1/operator-workbench/validate",
        json={
            "operators": [
                "entity_extract",
                "relation_extract",
                "unknown_operator",
            ]
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["valid"] is False
    assert payload["summary"]["error_count"] >= 2

    codes = {item["code"] for item in payload["issues"]}
    assert "INVALID_START_OPERATOR" in codes
    assert "TYPE_MISMATCH" in codes
    assert "UNKNOWN_OPERATOR" in codes


def test_operator_workbench_publish_and_list_pipelines():
    client = _build_client()

    publish_response = client.post(
        "/api/v1/operator-workbench/publish",
        json={
            "name": "我的测试链路",
            "description": "用于工作台发布测试",
            "published_by": "admin",
            "source_types": ["news"],
            "nodes": [
                {"key": "node-1", "operator": "source_record_map", "title": "源记录映射", "lane": 0},
                {"key": "node-2", "operator": "event_enrich", "title": "事件增强", "lane": 1},
                {"key": "node-3", "operator": "entity_resolve", "title": "实体归一", "lane": 2},
                {"key": "node-4", "operator": "event_resolve", "title": "事件归一", "lane": 3},
                {"key": "node-5", "operator": "fusion_graph_build", "title": "图构建", "lane": 4},
                {"key": "node-6", "operator": "graph_import", "title": "图导入", "lane": 5},
            ],
        },
    )
    assert publish_response.status_code == 200
    published = publish_response.json()
    assert published["name"] == "我的测试链路"
    assert published["is_builtin"] is False
    assert len(published["edges"]) == 5

    list_response = client.get("/api/v1/operator-workbench/published")
    assert list_response.status_code == 200
    rows = list_response.json()
    names = {item["name"] for item in rows}
    assert "我的测试链路" in names


def test_operator_workbench_publish_rejects_invalid_pipeline():
    client = _build_client()

    response = client.post(
        "/api/v1/operator-workbench/publish",
        json={
            "name": "错误链路",
            "nodes": [
                {"key": "node-1", "operator": "entity_extract", "title": "实体抽取", "lane": 0},
                {"key": "node-2", "operator": "graph_import", "title": "图导入", "lane": 1},
            ],
        },
    )
    assert response.status_code == 400
    assert "未通过发布校验" in response.json()["detail"]
