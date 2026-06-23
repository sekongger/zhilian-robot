import asyncio
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module(file_name: str, alias: str):
    route_path = Path(__file__).resolve().parents[1] / "app" / "api" / file_name
    spec = spec_from_file_location(alias, route_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_workflow_alias_routes_forward_to_openspg_demo(monkeypatch):
    workflow_routes = _load_module("workflow_routes.py", "workflow_routes_under_test")
    from app.openspg_demo import routes as demo_routes

    async def fake_run_news_workflow(request):
        return {"run_id": "wf_test_1", "status": "success", "request": request.model_dump()}

    monkeypatch.setattr(demo_routes, "run_news_workflow", fake_run_news_workflow)

    request = demo_routes.WorkflowNewsRunRequest(project_id=9, submit_builder=False, headlines_top_n=5)
    payload = asyncio.run(workflow_routes.run_news_workflow(request))

    assert payload["run_id"] == "wf_test_1"
    assert payload["request"]["project_id"] == 9


def test_model_studio_alias_schema_current(monkeypatch):
    model_studio_routes = _load_module("model_studio_routes.py", "model_studio_routes_under_test")
    from app.openspg_demo import routes as demo_routes

    async def fake_schema_current(project_id=1):
        return {
            "project_id": project_id,
            "schema_script": "graph schema {}",
            "schema_model": {"nodes": []},
            "reason_schema": {"rules": []},
        }

    monkeypatch.setattr(demo_routes, "get_model_studio_schema_current", fake_schema_current)

    payload = asyncio.run(model_studio_routes.get_model_studio_schema_current(project_id=3))

    assert payload["project_id"] == 3
    assert "schema_script" in payload


def test_industry_qa_internal_endpoints(monkeypatch):
    industry_qa_routes = _load_module("industry_qa_routes.py", "industry_qa_routes_under_test")
    open_api_routes = industry_qa_routes.open_api_routes

    def fake_prepare_query_context(*, query, query_type, top_k, filters, include_evidence):
        return {
            "query": query,
            "answer_mode": "openspg",
            "retrieval_compare": {
                "strategy": "compare",
                "openspg": {"hit_count": 1, "hits": [{"id": "company:智链机器人", "name": "智链机器人", "label": "zhilian.Company"}]},
                "classic": {"hit_count": 1},
            },
            "knowledge_objects": [
                {
                    "statement_id": "evt_1",
                    "subject": {"id": "company:智链机器人", "type": "Company", "name": "智链机器人"},
                    "predicate": "industry_event",
                    "object": {"id": "evt_1", "type": "IndustryEvent", "name": "测试事件"},
                    "confidence": 0.9,
                }
            ],
            "entities": ["智链机器人"],
            "evidences": [
                {
                    "doc_id": "n1",
                    "title": "测试新闻",
                    "snippet": "测试片段",
                    "source_name": "rss_36kr",
                    "source_url": "https://example.com/n1",
                    "publish_time": "2026-03-04T00:00:00+00:00",
                    "context_id": "evt_1",
                    "statement_id": "evt_1",
                }
            ],
            "trace_id": "trace_test_1",
            "trace_payload": {"query_plan": {"query": query}},
            "workflow_reference": {"run_id": "wf_test_1"},
        }

    monkeypatch.setattr(open_api_routes, "_prepare_query_context", fake_prepare_query_context)
    monkeypatch.setattr(open_api_routes, "_stream_query_answer", lambda context: iter([f"answer:{context['query']}"]))
    monkeypatch.setattr(
        open_api_routes,
        "_build_query_response",
        lambda context, answer: {
            "answer": answer,
            "answer_mode": context.get("answer_mode"),
            "retrieval_compare": context.get("retrieval_compare"),
            "knowledge_objects": context.get("knowledge_objects"),
            "entities": context.get("entities"),
            "evidences": context.get("evidences"),
            "trace_id": context.get("trace_id"),
            "run_id": (context.get("workflow_reference") or {}).get("run_id"),
        },
    )
    monkeypatch.setitem(
        open_api_routes._TRACE_STORE,
        "trace_test_1",
        {
            "query_plan": {"query": "测试问题"},
            "retrieval_hits": [{"event_id": "evt_1"}],
            "reasoning_path": ["extraction:kag", "semantic:openspg"],
            "model_usage": {"mode": "rule+retrieval"},
        },
    )
    monkeypatch.setattr(industry_qa_routes, "_get_mongo_conn", lambda: None)
    monkeypatch.setattr(industry_qa_routes, "_get_redis_conn", lambda: None)

    session = industry_qa_routes.create_session(industry_qa_routes.CreateSessionRequest(title="会话A"))
    session_id = session["session_id"]

    chat_payload = industry_qa_routes.chat(
        industry_qa_routes.IndustryQaChatRequest(session_id=session_id, question="测试问题", top_k=3)
    )
    assert chat_payload["trace_id"] == "trace_test_1"
    assert chat_payload["answer_mode"] == "openspg"
    assert len(chat_payload["citations"]) == 1

    sessions = industry_qa_routes.list_sessions()
    assert sessions["total"] >= 1

    messages_payload = industry_qa_routes.get_session_messages(session_id)
    messages = messages_payload["messages"]
    assert len(messages) >= 2

    assistant_message = [item for item in messages if item["role"] == "assistant"][0]
    trace_payload = industry_qa_routes.get_message_trace(assistant_message["message_id"])
    assert "retrieval_hits" in trace_payload
    assert trace_payload["industry_qa"]["collections_written"] == [
        "qa_messages",
        "qa_citations",
        "qa_traces",
    ]
