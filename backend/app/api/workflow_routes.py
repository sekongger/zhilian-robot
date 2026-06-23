"""内部工作流路由（兼容层）。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.openspg_demo import routes as demo_routes
from app.api.openks_routes import build_news_kg, get_news_kg_status
from app.openspg_demo.builder_import_command import (
    build_builder_envs_for_run,
    build_real_import_command,
)
from app.services.knowledge_runtime_service import (
    DEFAULT_RUNTIME_PROFILE,
    get_runtime_binding_summary,
    list_pending_openks_queue_preview,
    normalize_runtime_profile,
    register_workflow_runtime_binding,
)
from app.services.openks_schema_runtime_service import apply_openks_news_kg_schema

router = APIRouter(prefix="/workflow", tags=["Workflow (Internal)"])


class WorkflowCollectRequest(BaseModel):
    max_entries_per_feed: int = Field(5, ge=1, le=50)
    hours_ago: int = Field(24, ge=1, le=168)


class WorkflowProcessRequest(BaseModel):
    limit: int = Field(100, ge=1, le=1000)
    sample_lines: int = Field(5, ge=1, le=50)
    allow_demo_fallback: bool = False


class WorkflowExtractRequest(BaseModel):
    project_id: int = Field(1, ge=1)
    limit: int = Field(200, ge=1, le=5000)
    force_full: bool = True
    use_active_model: bool = True
    worker_num: int = Field(1, ge=1, le=128)
    runtime_profile: str = Field(default=DEFAULT_RUNTIME_PROFILE, min_length=1)


class WorkflowModelRequest(BaseModel):
    project_id: int = Field(1, ge=1)
    schema_script: Optional[str] = None
    activate_label: str = Field(default="workflow-step", min_length=1, max_length=120)


class WorkflowExecuteRequest(BaseModel):
    project_id: int = Field(1, ge=1)
    builder_command: Optional[str] = None
    worker_num: int = Field(1, ge=1, le=128)
    limit: int = Field(20, ge=1, le=5000)
    runtime_profile: str = Field(default=DEFAULT_RUNTIME_PROFILE, min_length=1)
    user_number: Optional[str] = None
    image: Optional[str] = None
    worker_pool: Optional[str] = None


class WorkflowApplyRequest(BaseModel):
    hours: int = Field(24, ge=1, le=168)
    top_n: int = Field(20, ge=1, le=100)
    allow_demo_fallback: bool = False


@router.post("/news/run", status_code=202)
async def run_news_workflow(request: demo_routes.WorkflowNewsRunRequest):
    return await demo_routes.run_news_workflow(request)


@router.get("/news/runs/{run_id}")
def get_news_workflow_run(run_id: str):
    return demo_routes.get_news_workflow_run(run_id)


@router.get("/news/runs/{run_id}/steps/{step_key}")
def get_news_workflow_step_detail(run_id: str, step_key: str):
    return demo_routes.get_news_workflow_step_detail(run_id, step_key)


@router.get("/news/latest")
def get_latest_news_workflow_run(project_id: int = Query(1, ge=1)):
    return demo_routes.get_latest_news_workflow_run(project_id=project_id)


@router.get("/news/history")
def get_news_workflow_history(
    project_id: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    return demo_routes.get_news_workflow_history(project_id=project_id, limit=limit)


@router.post("/news/steps/collect")
def run_news_collect_step(request: WorkflowCollectRequest):
    ingest_request = demo_routes.RSSPullRequest(
        max_entries_per_feed=request.max_entries_per_feed,
        hours_ago=request.hours_ago,
    )
    return demo_routes.ingest_real_rss(ingest_request)


@router.post("/news/steps/process")
def run_news_process_step(request: WorkflowProcessRequest):
    preview = demo_routes.get_bridge_batch_preview(
        limit=request.limit,
        sample_lines=request.sample_lines,
        allow_demo_fallback=request.allow_demo_fallback,
    )
    status = demo_routes.get_bridge_status(allow_demo_fallback=request.allow_demo_fallback)
    return {
        "preview": preview,
        "status": status,
    }


@router.post("/news/steps/extract")
async def run_news_extract_step(request: WorkflowExtractRequest):
    runtime_profile = normalize_runtime_profile(request.runtime_profile)
    if runtime_profile == "openks_direct":
        return {
            "runtime_profile": runtime_profile,
            "preview": list_pending_openks_queue_preview(limit=request.limit),
            "status": get_news_kg_status(),
            "meta": {
                "step": "extract",
                "runtime_profile": runtime_profile,
                "extract_mode": "queue_preview",
            },
        }

    extract_request = demo_routes.BridgeRunRequest(
        project_id=request.project_id,
        limit=request.limit,
        force_full=request.force_full,
        submit_builder=False,
        apply_schema=False,
        materialize_graph=False,
        use_active_model=request.use_active_model,
        worker_num=request.worker_num,
        runtime_profile=runtime_profile,
    )
    result = await demo_routes.run_bridge_batch(extract_request)
    result["meta"] = {
        "step": "extract",
        "submit_builder": False,
        "runtime_profile": runtime_profile,
    }
    return result


@router.post("/news/steps/model")
async def run_news_model_step(request: WorkflowModelRequest):
    return await apply_openks_news_kg_schema(
        project_id=request.project_id,
        activate_label=request.activate_label,
    )


@router.post("/news/steps/execute")
async def run_news_execute_step(request: WorkflowExecuteRequest):
    runtime_profile = normalize_runtime_profile(request.runtime_profile)
    if runtime_profile == "openks_direct":
        build_result = build_news_kg(limit=request.limit)
        return {
            "runtime_profile": runtime_profile,
            "openks_build_result": build_result,
            "runtime_binding": get_runtime_binding_summary(
                kg_name="news_kg",
                runtime_profile=runtime_profile,
            ),
        }

    status = demo_routes.get_bridge_status(allow_demo_fallback=False)
    last_run = status.get("last_run") if isinstance(status, dict) else None
    if not isinstance(last_run, dict):
        raise HTTPException(status_code=400, detail="缺少可执行批次，请先执行抽取步骤")

    try:
        envs = build_builder_envs_for_run(last_run, project_id=request.project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"构建 Builder 环境失败: {exc}") from exc

    submit_request = demo_routes.BuilderSubmitRequest(
        project_id=request.project_id,
        command=str(request.builder_command or "").strip() or build_real_import_command(),
        worker_num=request.worker_num,
        user_number=request.user_number,
        image=request.image,
        worker_pool=request.worker_pool,
        envs=envs,
    )
    builder_submit_result = await demo_routes.submit_engine_builder_job(submit_request)
    if not demo_routes._result_effective_success(builder_submit_result):
        raise HTTPException(
            status_code=502,
            detail=f"Builder 提交失败: {demo_routes._result_effective_error(builder_submit_result)}",
        )
    graph_materialize_result = await materialize_kag_bridge_run(
        bridge_run=last_run,
        project_id=request.project_id,
    )
    runtime_binding = register_workflow_runtime_binding(
        runtime_profile=runtime_profile,
        kg_name="news_kg",
        project_id=request.project_id,
        bridge_run=last_run,
        builder_submit_result=builder_submit_result,
        graph_materialize_result=graph_materialize_result,
    )
    return {
        "runtime_profile": runtime_profile,
        "builder_submit_result": builder_submit_result,
        "graph_materialize_result": graph_materialize_result,
        "runtime_binding": runtime_binding,
        "bridge_last_run": last_run,
        "bridge_status": {
            "cursor": status.get("cursor") if isinstance(status, dict) else None,
            "last_run": last_run,
        },
    }


@router.post("/news/steps/apply")
def run_news_apply_step(request: WorkflowApplyRequest):
    payload = demo_routes.get_headlines(
        hours=request.hours,
        top_n=request.top_n,
        allow_demo_fallback=request.allow_demo_fallback,
    )
    meta = dict(payload.get("meta") or {})
    meta.update(
        {
            "hours": request.hours,
            "top_n": request.top_n,
            "access_scope": "internal",
        }
    )
    payload["meta"] = meta
    return payload


async def materialize_kag_bridge_run(*, bridge_run: dict, project_id: int):
    return await demo_routes._materialize_graph_for_bridge_run(
        bridge_run=bridge_run,
        project_id=project_id,
    )
