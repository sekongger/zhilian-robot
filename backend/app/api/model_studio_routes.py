"""内部模型管理路由（兼容层）。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.openspg_demo import routes as demo_routes

router = APIRouter(prefix="/model-studio", tags=["Model Studio (Internal)"])


@router.get("/schema/current")
async def get_model_studio_schema_current(project_id: int = Query(1, ge=1)):
    return await demo_routes.get_model_studio_schema_current(project_id=project_id)


@router.get("/schema/active")
def get_model_studio_active_schema(project_id: int = Query(1, ge=1)):
    return demo_routes.get_model_studio_active_schema(project_id=project_id)


@router.post("/schema/activate")
def activate_model_studio_schema(request: demo_routes.ModelStudioSchemaActivateRequest):
    return demo_routes.activate_model_studio_schema(request)


@router.post("/schema/apply")
async def apply_model_studio_schema(request: demo_routes.ModelStudioSchemaApplyRequest):
    return await demo_routes.apply_model_studio_schema(request)

