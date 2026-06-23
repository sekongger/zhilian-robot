"""
API 路由模块（安全懒加载）。

目的：
- 本地演示时允许缺少部分可选依赖（如 NLP/图数据库驱动）仍能启动 FastAPI
- 已安装依赖的路由会正常注册
"""

from importlib import import_module
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

ROUTE_MODULES = [
    "app.api.nlp_routes",
    "app.api.graph_routes",
    "app.api.data_routes",
    "app.api.analytics_routes",
    "app.api.entity_actions_routes",
    "app.api.ingestion_routes",
    "app.api.ingest_routes",
    "app.api.document_pipeline_routes",
    "app.api.ontology_routes",
    "app.api.report_pipeline_routes",
    "app.api.workflow_routes",
    "app.api.model_studio_routes",
    "app.api.industry_qa_routes",
    "app.api.resource_routes",
    "app.api.resource_hub_routes",
    "app.api.datahub_mock_routes",
    "app.api.knowledge_runtime_routes",
    "app.api.openks_routes",
    "app.api.platform_overview_routes",
    "app.api.open_api_routes",
    "app.api.openspg_demo_routes",
    "app.api.operator_workbench_routes",
    "app.api.news_graph_routes",
]


def _include_router(target: APIRouter, module_path: str, attr: str = "router") -> None:
    try:
        mod = import_module(module_path)
        router = getattr(mod, attr)
        target.include_router(router)
        logger.info("API router loaded: %s", module_path)
    except Exception as exc:  # pragma: no cover - 运行环境缺依赖时触发
        logger.warning("API router skipped: %s (%s)", module_path, exc)


def build_api_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    for module in ROUTE_MODULES:
        _include_router(router, module)
    return router


__all__ = ["build_api_router"]
