"""
API路由模块
"""
from fastapi import APIRouter
from .nlp_routes import router as nlp_router
from .graph_routes import router as graph_router
from .data_routes import router as data_router
from .analytics_routes import router as analytics_router
from .entity_actions_routes import router as entity_actions_router
from .ingestion_routes import router as ingestion_router

# 创建主路由
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(nlp_router)
api_router.include_router(graph_router)
api_router.include_router(data_router)
api_router.include_router(analytics_router)
api_router.include_router(entity_actions_router)
api_router.include_router(ingestion_router)

__all__ = ['api_router']
