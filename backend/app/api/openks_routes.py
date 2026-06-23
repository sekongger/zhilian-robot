from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from fastapi import APIRouter, HTTPException, Query

_SOURCE_PROJECT_ROOT = Path(__file__).resolve().parents[3] / "supxmind" / "supxmind-openks"
if _SOURCE_PROJECT_ROOT.exists() and str(_SOURCE_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_PROJECT_ROOT))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_loaded_openks = sys.modules.get("openks")
if _SOURCE_PROJECT_ROOT.exists() and _loaded_openks is not None:
    loaded_file = Path(getattr(_loaded_openks, "__file__", "")).resolve()
    expected_root = (_SOURCE_PROJECT_ROOT / "openks").resolve()
    if expected_root not in loaded_file.parents:
        for module_name in list(sys.modules):
            if module_name == "openks" or module_name.startswith("openks."):
                sys.modules.pop(module_name, None)

from openks.common.registry import SUPPORT_MODULES, get_module_spec, list_kg_modules
from openks.common.base.core import BaseSchema
from openks.entry.api.service import build_news_kg, get_engine_overview, get_news_kg_status, query_news_kg
from app.services.openks_mock_service import (
    get_build_job,
    get_datahub_enterprise,
    get_datahub_headlines,
    list_build_jobs,
    submit_build_job,
)
from app.services.openks_build_job_service import get_build_job_result
from app.services.openks_build_job_service import get_graph_evidence, get_graph_sample, get_graph_summary

router = APIRouter(prefix="/openks", tags=["openks"])
_TRACEABLE_MODULES = {"base_kg", "news_kg", "event_kg", "industry_network"}


def _openks_package_root() -> Path:
    candidate = _SOURCE_PROJECT_ROOT / "openks"
    if candidate.exists():
        return candidate

    import openks

    return Path(openks.__file__).resolve().parent


def _module_root(path: str) -> Path:
    relative = Path(path)
    parts = relative.parts[1:] if relative.parts and relative.parts[0] == "openks" else relative.parts
    return _openks_package_root().joinpath(*parts)


def _module_payload(spec) -> dict:
    root = _module_root(spec.path)
    return {
        "name": spec.name,
        "title": spec.title,
        "stage": spec.stage,
        "owner": spec.owner,
        "path": spec.path,
        "summary": spec.summary,
        "status": getattr(spec, "status", "planned"),
        "dependencies": list(spec.dependencies),
        "has_schema": (root / "schema" / f"{spec.name}_schema.py").exists(),
        "has_builder": (root / "builder" / f"{spec.name}_builder.py").exists(),
        "has_reasoner": (root / "reasoner" / f"{spec.name}_reasoner.py").exists(),
        "has_solver": (root / "solver" / f"{spec.name}_solver.py").exists(),
        "has_tests": (root / "tests" / f"test_{spec.name}.py").exists(),
        "is_traceable": spec.name in _TRACEABLE_MODULES,
    }


def _load_schema_preview(spec) -> dict:
    root = _module_root(spec.path)
    schema_file = root / "schema" / f"{spec.name}_schema.py"
    if not schema_file.exists():
        return {"entities": [], "relations": [], "fields": []}

    loaded_spec = spec_from_file_location(f"openks_schema_preview_{spec.name}", schema_file)
    if not loaded_spec or not loaded_spec.loader:
        return {"entities": [], "relations": [], "fields": []}

    module = module_from_spec(loaded_spec)
    loaded_spec.loader.exec_module(module)

    for value in vars(module).values():
        if isinstance(value, type) and issubclass(value, BaseSchema) and value is not BaseSchema:
            try:
                preview = value().describe()
            except Exception:
                return {"entities": [], "relations": [], "fields": []}
            return {
                "entities": list(preview.get("entities") or []),
                "relations": list(preview.get("relations") or []),
                "fields": list(preview.get("fields") or []),
            }

    return {"entities": [], "relations": [], "fields": []}


def _filter_traceable_specs(specs):
    return [item for item in specs if item.name in _TRACEABLE_MODULES]


def _main_chain_payload() -> dict:
    return {
        "runtime_profile": "kag_openspg",
        "status": "production",
        "delivery_mode": "openspg-first",
        "legacy_profile": "openks_direct",
        "legacy_status": "compatibility_only",
        "description": "当前对外主链已经固定为 kag_openspg，OpenKS 负责 schema 与知识计算，OpenSPG 负责内部主存与图服务。",
    }


def _integration_boundary_payload() -> dict:
    return {
        "datahub": {
            "status": "contract_only",
            "integration_mode": "mock_headlines_first",
            "headlines_endpoint": "/api/v1/datahub/mock/headlines",
            "enterprise_endpoint": "/api/v1/datahub/mock/enterprise",
            "notes": [
                "第一阶段只模拟头条资讯接口，不接真实 DataHub 远程调用。",
                "企业库接口只定义字段规范与占位返回，不进入主链实数构建。",
            ],
        },
        "graphiti": {
            "status": "contract_only",
            "integration_mode": "adapter_snapshot",
            "required_endpoint": "POST /messages",
            "required_fields": ["group_id", "messages[].uuid", "messages[].name", "messages[].content", "messages[].timestamp"],
            "notes": [
                "当前仅使用 GraphitiAdapter 兼容真实契约并生成事件事实包。",
                "真实 Graphiti 服务、时态关系维护与远程 episode 存储留在后续阶段。",
            ],
        },
        "openspg": {
            "status": "production",
            "exposure_mode": "internal_proxy_only",
            "schema_sync_entry": "backend/app/services/openks_schema_runtime_service.py::apply_openks_news_kg_schema",
            "materialize_entry": "backend/app/openspg_demo/graph_materializer.py::materialize_bridge_batch",
            "release_binding_entry": "backend/app/services/knowledge_runtime_service.py::register_workflow_runtime_binding",
        },
    }


def _industry_graph_governance_payload() -> dict:
    return {
        "build_method": [
            "DataHub 标准化资讯批次 -> GraphitiAdapter 事件事实包",
            "event_kg 构造成事件 / 文档 / 来源 / 主体节点与关系",
            "industry_network 聚合事件节点、证据与公司节点形成产业网样例图",
            "OpenSPG 通过 schema sync + upsertVertex/upsertEdge 承接主存",
        ],
        "openspg_capabilities": ["sync_schema", "upsertVertex", "upsertEdge"],
        "audit_checks": [
            "逐条核对 doc_id / source_url / publish_time 是否可回溯到原始资讯",
            "按事件抽样复核主体、事件类型、地域、来源是否抽对",
            "对公司、事件、文档节点数量与关系数量做批次级对账",
            "对高价值边做人工 spot check，确认不是共现误抽或泛化误连",
        ],
        "optimization_backlog": [
            "引入企业主数据和别名归一，减少 company::名称 级别的碎片节点",
            "增加事件去重、跨文档聚合和置信度评分，避免一文一事件的过碎构图",
            "把行业节点、技术节点、产品节点与 IncCore.schema 子类映射做实",
            "补充审核台账、规则回放和坏样本集，形成可持续评测闭环",
        ],
    }


def _production_steps_payload() -> list[dict]:
    return [
        {
            "key": "workflow",
            "title": "Workflow 编排入口",
            "run_api": "POST /api/v1/workflow/news/run",
            "function_entry": "backend/app/api/workflow_routes.py::run_news_workflow",
            "input_fields": ["project_id", "runtime_profile", "max_entries_per_feed", "hours_ago", "limit"],
            "output_fields": ["run_id", "status", "step_statuses", "warnings"],
        },
        {
            "key": "schema_sync",
            "title": "OpenKS Schema Sync",
            "run_api": "POST /api/v1/workflow/news/steps/model",
            "function_entry": "backend/app/services/openks_schema_runtime_service.py::apply_openks_news_kg_schema",
            "input_fields": ["project_id", "activate_label"],
            "output_fields": ["schema_source", "namespace", "compiled_schema_script", "schema_commit_result", "activate_result"],
        },
        {
            "key": "bridge_export",
            "title": "BridgeRunner 导出 JSONL",
            "run_api": "POST /api/v1/workflow/news/steps/extract",
            "function_entry": "backend/app/openspg_demo/bridge_runner.py::BridgeRunner.run_export",
            "input_fields": ["normalized_rows", "project_id", "limit", "force_full", "use_active_model", "worker_num", "runtime_profile"],
            "output_fields": ["run_id", "export_count", "batch_file_path", "batch_relative_path", "cursor_after"],
        },
        {
            "key": "graph_materialize",
            "title": "OpenSPG Upsert",
            "run_api": "POST /api/v1/workflow/news/steps/execute",
            "function_entry": "backend/app/openspg_demo/graph_materializer.py::materialize_bridge_batch",
            "input_fields": ["batch_file_path", "project_id", "openspg_base_url"],
            "output_fields": ["status", "namespace", "records", "vertices", "edges", "vertex_groups", "edge_groups"],
        },
        {
            "key": "runtime_binding",
            "title": "Runtime Binding",
            "run_api": "POST /api/v1/workflow/news/steps/execute",
            "function_entry": "backend/app/services/knowledge_runtime_service.py::register_workflow_runtime_binding",
            "input_fields": ["runtime_profile", "kg_name", "project_id", "workflow_run_id", "bridge_run", "builder_submit_result", "graph_materialize_result"],
            "output_fields": ["run", "artifact", "release"],
        },
    ]


def _openks_page_requirements_payload() -> list[str]:
    return [
        "把 /api/v1/workflow/news/steps/model|extract|execute 的执行入口直接挂到 OpenKS 页面按钮",
        "把 workflow latest 与 runs/artifacts/releases 统一成同一条 production runtime 视图",
        "补每一步的 step detail 输入输出快照，避免页面只显示状态不显示实际载荷",
        "图结果读取应按 artifact_id 走 production runtime，而不是 build-jobs 的样例图接口",
        "补权限、幂等、日志、失败重试与耗时指标，否则页面能跑但不可运维",
    ]


@router.get("/modules")
def get_openks_modules(stage: str | None = Query(default=None), include_hidden: bool = Query(default=False)):
    modules = list_kg_modules(stage)
    if not include_hidden:
        modules = _filter_traceable_specs(modules)
    return {
        "modules": [_module_payload(item) for item in modules],
        "support_modules": SUPPORT_MODULES,
        "total": len(modules),
    }


@router.get("/modules/{name}")
def get_openks_module(name: str):
    spec = get_module_spec(name)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"模块 {name} 不存在")
    return {
        **_module_payload(spec),
        "schema_preview": _load_schema_preview(spec),
    }


@router.get("/overview")
def get_openks_overview():
    payload = get_engine_overview()
    modules = [_module_payload(item) for item in _filter_traceable_specs(list_kg_modules())]
    return {
        **payload,
        "main_chain": _main_chain_payload(),
        "integration_boundary": _integration_boundary_payload(),
        "industry_graph_governance": _industry_graph_governance_payload(),
        "production_steps": _production_steps_payload(),
        "openks_page_requirements": _openks_page_requirements_payload(),
        "modules_by_stage": {
            "fact": len([item for item in modules if item["stage"] == "fact"]),
            "cognition": len([item for item in modules if item["stage"] == "cognition"]),
            "decision": len([item for item in modules if item["stage"] == "decision"]),
        },
    }


@router.post("/news-kg/build")
def trigger_news_kg_build(limit: int = Query(default=20, ge=1, le=200)):
    return build_news_kg(limit=limit)


@router.get("/news-kg/status")
def get_news_kg_build_status():
    return get_news_kg_status()


@router.post("/news-kg/query")
def solve_news_kg(query: dict):
    return query_news_kg(query)


@router.post("/build-jobs")
def submit_openks_build_job(payload: dict):
    return submit_build_job(payload=payload)


@router.get("/build-jobs")
def list_openks_build_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
):
    return list_build_jobs(status=status, limit=limit)


@router.get("/build-jobs/{job_id}")
def get_openks_build_job(job_id: str):
    job = get_build_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"构建任务 {job_id} 不存在")
    return job


@router.get("/build-jobs/{job_id}/result")
def get_openks_build_job_result(job_id: str):
    payload = get_build_job_result(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"构建任务 {job_id} 不存在")
    return payload


@router.get("/datahub/headlines")
def get_datahub_headlines_mock(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=20, ge=1, le=100),
):
    return get_datahub_headlines(hours=hours, limit=limit)


@router.get("/datahub/enterprise")
def get_datahub_enterprise_mock(name: str = Query(default="")):
    return get_datahub_enterprise(name=name)


@router.get("/graph/summary")
def get_openks_graph_summary(
    artifact_id: str = Query(default=""),
    job_id: str = Query(default=""),
):
    payload = get_graph_summary(artifact_id=artifact_id, job_id=job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="图谱结果不存在")
    return payload


@router.get("/graph/sample")
def get_openks_graph_sample(
    artifact_id: str = Query(default=""),
    job_id: str = Query(default=""),
):
    payload = get_graph_sample(artifact_id=artifact_id, job_id=job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="图谱结果不存在")
    return payload


@router.get("/graph/evidence")
def get_openks_graph_evidence(
    artifact_id: str = Query(default=""),
    job_id: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
):
    payload = get_graph_evidence(artifact_id=artifact_id, job_id=job_id, limit=limit)
    if payload is None:
        raise HTTPException(status_code=404, detail="图谱结果不存在")
    return payload
