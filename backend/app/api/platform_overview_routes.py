from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.services.knowledge_runtime_service import DEFAULT_RUNTIME_PROFILE

router = APIRouter(prefix="/platform", tags=["platform-overview"])


def _normalize_mongo_doc(document: dict | None) -> dict | None:
    if not isinstance(document, dict):
        return None
    payload = dict(document)
    if "_id" in payload:
        payload["_id"] = str(payload["_id"])
    return payload


def _stats_route(*, doc_type=None, knowledge_scope=None):
    from app.api.document_pipeline_routes import stats
    import asyncio

    return asyncio.run(stats(doc_type=doc_type, knowledge_scope=knowledge_scope))


def _workflow_summary_loader():
    from app.api.workflow_routes import get_latest_news_workflow_run

    return get_latest_news_workflow_run(project_id=1)


def _openks_overview_loader():
    from app.api.openks_routes import get_openks_overview

    return get_openks_overview()


def _openks_news_kg_status_loader():
    from app.api.openks_routes import get_news_kg_build_status

    return get_news_kg_build_status()


def _knowledge_runtime_snapshot_loader():
    from app.database.mongodb import mongodb_conn

    def _latest(collection_name: str):
        rows = mongodb_conn.find_many(
            collection_name,
            query={"kg_name": "news_kg", "runtime_profile": DEFAULT_RUNTIME_PROFILE},
            limit=1,
            sort=[("created_at", -1)],
        )
        return _normalize_mongo_doc(rows[0]) if rows else None

    return {
        "latest_run": _latest("knowledge_runs"),
        "latest_artifact": _latest("knowledge_artifacts"),
        "latest_release": _latest("service_releases"),
    }


def _graph_statistics_loader():
    from app.api.graph_routes import get_graph_statistics
    import asyncio

    return asyncio.run(get_graph_statistics())


def _momentum_top_loader():
    from app.api.graph_routes import get_top_momentum_entities
    import asyncio

    return asyncio.run(get_top_momentum_entities(limit=5))


def _momentum_trend_loader(start_date: str, end_date: str):
    from app.api.graph_routes import get_momentum_trend
    import asyncio

    return asyncio.run(
        get_momentum_trend(
            start_date=start_date,
            end_date=end_date,
            entity_type=None,
        )
    )


def _summarize_workflow_run(run: dict | None) -> dict:
    run = run or {}
    return {
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "updated_at": run.get("updated_at"),
        "step_statuses": run.get("step_statuses") or {},
        "warnings": run.get("warnings") or [],
    }


def _build_data_elements_summary() -> dict:
    news = _stats_route(doc_type="news", knowledge_scope=None)
    report = _stats_route(doc_type="report", knowledge_scope=None)
    return {
        "types": [
            {
                "doc_type": "news",
                "label": "资讯",
                "status": "connected",
                "raw_documents": ((news.get("raw_layer") or {}).get("raw_documents") or 0),
                "resource_documents": ((news.get("resource_layer") or {}).get("inc_document") or 0),
                "entities": ((news.get("knowledge_layer") or {}).get("entities") or 0),
                "statements": ((news.get("knowledge_layer") or {}).get("statements") or 0),
            },
            {
                "doc_type": "report",
                "label": "研报",
                "status": "connected",
                "raw_documents": ((report.get("raw_layer") or {}).get("raw_documents") or 0),
                "resource_documents": ((report.get("resource_layer") or {}).get("inc_document") or 0),
                "entities": ((report.get("knowledge_layer") or {}).get("entities") or 0),
                "statements": ((report.get("knowledge_layer") or {}).get("statements") or 0),
            },
            {"doc_type": "enterprise", "label": "企业", "status": "planned"},
            {"doc_type": "policy", "label": "政策", "status": "planned"},
        ],
    }


def _build_knowledge_computing_summary() -> dict:
    try:
        workflow = _summarize_workflow_run(_workflow_summary_loader())
    except Exception as exc:
        workflow = {
            "run_id": None,
            "status": "unavailable",
            "updated_at": None,
            "step_statuses": {},
            "warnings": [str(exc)],
        }
    try:
        news_kg = _openks_news_kg_status_loader()
    except Exception as exc:
        news_kg = {
            "kg_name": "news_kg",
            "queue": {"pending": 0, "running": 0, "failed": 0, "completed": 0},
            "latest_run": {"run_id": None, "status": "unavailable", "error": str(exc)},
        }
    try:
        traceability = _knowledge_runtime_snapshot_loader()
    except Exception:
        traceability = {"latest_run": None, "latest_artifact": None, "latest_release": None}
    return {
        "workflow": workflow,
        "openks": _openks_overview_loader(),
        "news_kg": news_kg,
        "traceability": traceability,
    }


def _build_chain_analysis_summary() -> dict:
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    try:
        graph_stats = _graph_statistics_loader()
    except Exception:
        graph_stats = {"node_count": 0, "relation_count": 0}
    try:
        momentum_top = _momentum_top_loader()
    except Exception:
        momentum_top = {"entities": []}
    try:
        momentum_trend = _momentum_trend_loader(start_date.isoformat(), end_date.isoformat())
    except Exception:
        momentum_trend = {"trend": []}
    return {
        "graph": graph_stats,
        "momentum_top": (momentum_top or {}).get("entities") or [],
        "momentum_trend": (momentum_trend or {}).get("trend") or [],
    }


def _build_agent_apps_summary() -> dict:
    from app.api.open_api_routes import get_open_headlines

    headlines_payload = get_open_headlines(hours=24, top_n=3, allow_demo_fallback=True)
    return {
        "headlines": headlines_payload.get("headlines") or [],
        "meta": headlines_payload.get("meta") or {},
    }


def _build_full_payload() -> dict:
    return {
        "data_elements": _build_data_elements_summary(),
        "knowledge_computing": _build_knowledge_computing_summary(),
        "chain_analysis": _build_chain_analysis_summary(),
        "agent_apps": _build_agent_apps_summary(),
    }


@router.get("/overview")
def get_platform_overview(stage: str | None = Query(default=None)):
    if stage in {"data-elements", "data-hub"}:
        return {"stage": stage, "data_elements": _build_data_elements_summary()}
    if stage == "knowledge-computing":
        return {"stage": stage, "knowledge_computing": _build_knowledge_computing_summary()}
    if stage == "chain-analysis":
        return {"stage": stage, "chain_analysis": _build_chain_analysis_summary()}
    if stage in {"agent-apps", "intelligent-service"}:
        return {"stage": stage, "agent_apps": _build_agent_apps_summary()}
    return _build_full_payload()
