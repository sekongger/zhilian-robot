"""OpenSPG/KAG 产业头条演示路由。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import secrets
import socket
import threading
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse, Response

from app.api.openks_routes import build_news_kg
from app.services.knowledge_runtime_service import (
    DEFAULT_RUNTIME_PROFILE,
    get_runtime_binding_summary,
    list_pending_openks_queue_preview,
    normalize_runtime_profile,
    register_workflow_runtime_binding,
)
from app.services.openks_schema_runtime_service import apply_openks_news_kg_schema

from .bridge import export_news_batch_to_jsonl_lines, normalize_news_record
from .bridge_runner import BridgeRunner
from .builder_import_command import build_builder_envs_for_run, build_real_import_command
from .builder_templates import get_robot_chain_mvp_builder_template
from .graph_materializer import async_materialize_bridge_batch, materialize_bridge_batch
from .headlines_service import build_headlines_from_news, get_demo_news_samples, get_event_detail_from_news
from .openspg_client import (
    alter_openspg_schema_draft_public,
    apply_openspg_schema_script,
    get_openspg_capability_snapshot,
    get_openspg_builder_job,
    get_openspg_builder_sample,
    get_openspg_health,
    get_openspg_project,
    get_openspg_reason_schema,
    get_openspg_schema_graph,
    get_openspg_schema_script,
    search_openspg_scheduler_instances,
    search_openspg_scheduler_tasks,
    submit_openspg_builder_legacy_job,
    submit_openspg_builder_job,
    upload_openspg_reasoner_file,
)
from .rss_ingest import pull_rss_articles_to_mongo
from .schema_templates import get_my_news_demo_schema_script, get_robot_chain_mvp_schema_template

router = APIRouter(prefix="/openspg-demo", tags=["OpenSPG KAG Demo"])
_MONGO_FUSE_UNTIL = 0.0
_MONGO_FUSE_SECONDS = 120.0
_MODEL_PROFILE_LOCK = threading.RLock()
_WORKFLOW_STATE_LOCK = threading.RLock()
_WORKFLOW_STEP_KEYS = ("model", "collect", "process", "extract", "execute", "apply")
_WORKFLOW_ACTIVE_STATUSES = {"queued", "running"}
_WORKFLOW_TERMINAL_STATUSES = {"success", "partial_success", "failed"}
_WORKFLOW_STEP_TITLES = {
    "model": "建模",
    "collect": "采集",
    "process": "处理",
    "extract": "抽取",
    "execute": "执行",
    "apply": "应用",
}
_WORKFLOW_STEP_DESCRIPTIONS = {
    "model": "OpenKS schema 适配、导出与提交结果回放",
    "collect": "真实资讯采集输入与入库结果",
    "process": "标准化批次与桥接预处理结果",
    "extract": "KAG bridge 导出与待写入对象预览",
    "execute": "Builder 提交、图物化与运行时绑定结果",
    "apply": "Artifact / Release 消费快照与证据结果",
}


class BridgeRunRequest(BaseModel):
    limit: int = Field(200, ge=1, le=5000)
    force_full: bool = False
    submit_builder: bool = True
    project_id: int = Field(1, ge=1)
    apply_schema: bool = True
    materialize_graph: bool = True
    use_active_model: bool = False
    schema_script: Optional[str] = None
    builder_command: Optional[str] = None
    worker_num: int = Field(1, ge=1, le=128)
    runtime_profile: str = Field(default=DEFAULT_RUNTIME_PROFILE, min_length=1)


class BuilderSubmitRequest(BaseModel):
    project_id: int = Field(1, ge=1)
    command: str = Field(..., min_length=1)
    worker_num: int = Field(1, ge=1, le=128)
    user_number: Optional[str] = None
    image: Optional[str] = None
    worker_pool: Optional[str] = None
    envs: Optional[Dict[str, str]] = None


class RSSPullRequest(BaseModel):
    max_entries_per_feed: int = Field(5, ge=1, le=50)
    hours_ago: int = Field(24, ge=1, le=168)


class ModelStudioSchemaApplyRequest(BaseModel):
    project_id: int = Field(1, ge=1)
    schema_script: str = Field(..., min_length=1)


class ModelStudioSchemaActivateRequest(BaseModel):
    project_id: int = Field(1, ge=1)
    schema_script: Optional[str] = None
    label: Optional[str] = Field(default=None, max_length=120)


class ModelStudioExtractionSubmitRequest(BaseModel):
    project_id: int = Field(1, ge=1)
    text_content: str = Field(..., min_length=1)
    job_name: Optional[str] = Field(default=None, max_length=120)
    worker_num: int = Field(1, ge=1, le=128)
    split_length: int = Field(500, ge=100, le=4000)
    semantic_split: bool = False
    schema_constrained_extract: bool = True


class WorkflowNewsRunRequest(BaseModel):
    project_id: int = Field(1, ge=1)
    max_entries_per_feed: int = Field(5, ge=1, le=50)
    hours_ago: int = Field(24, ge=1, le=168)
    bridge_limit: int = Field(200, ge=1, le=5000)
    force_full: bool = True
    submit_builder: bool = True
    apply_schema: bool = True
    materialize_graph: bool = True
    worker_num: int = Field(1, ge=1, le=128)
    builder_command: Optional[str] = None
    allow_demo_fallback: bool = False
    headlines_top_n: int = Field(20, ge=1, le=100)
    runtime_profile: str = Field(default=DEFAULT_RUNTIME_PROFILE, min_length=1)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _allow_demo_fallback(flag: Optional[bool]) -> bool:
    if flag is not None:
        return bool(flag)
    return _bool_env("OPENSPG_DEMO_ALLOW_FALLBACK", False)


def _builder_submit_enabled() -> bool:
    return _bool_env("OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT", True)


def _builder_submit_hint() -> str:
    return "Builder 自动提交已启用。若需关闭，可设置 OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT=0 并重启后端。"


def _mongo_quick_check() -> bool:
    """快速探测 Mongo 端口，避免无数据库场景下接口长时间阻塞。"""
    global _MONGO_FUSE_UNTIL

    now = time.time()
    if now < _MONGO_FUSE_UNTIL:
        return False

    try:
        from config.settings import settings

        parsed = urlparse(settings.MONGODB_URI)
        host = parsed.hostname or "localhost"
        port = parsed.port or 27017
        # 本地直接启动后端时，常见 docker-compose 主机名可能不可解析。
        try:
            socket.gethostbyname(host)
        except Exception:
            _MONGO_FUSE_UNTIL = now + _MONGO_FUSE_SECONDS
            return False
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except Exception:
        _MONGO_FUSE_UNTIL = now + _MONGO_FUSE_SECONDS
        return False


def _read_news_rows(limit: int = 200, allow_demo_fallback: bool = False) -> tuple[List[Dict[str, Any]], str]:
    """读取真实资讯；可按需回退 demo 样例。"""
    if not _mongo_quick_check():
        if allow_demo_fallback:
            return get_demo_news_samples(), "demo-fallback"
        return [], "empty-real"

    try:
        from app.database.mongodb import mongodb_conn

        rows = mongodb_conn.find_many("source_news", limit=limit, sort=[("publish_time", -1)])
        if rows:
            return rows, "zhilian-robot-db:source_news"
    except Exception:
        pass

    try:
        from app.database.mongodb import mongodb_conn

        rows = mongodb_conn.find_many("crawled_articles", limit=limit, sort=[("crawled_at", -1)])
        if rows:
            return rows, "zhilian-robot-db:crawled_articles"
    except Exception:
        pass

    if allow_demo_fallback:
        return get_demo_news_samples(), "demo-fallback"
    return [], "empty-real"


def _bridge_runner() -> BridgeRunner:
    return BridgeRunner()


def _is_live_success(result: Dict[str, Any]) -> bool:
    if result.get("mode") != "live":
        return False
    http_status = int(result.get("http_status") or 0)
    if http_status >= 400 or http_status <= 0:
        return False
    response = result.get("response")
    if isinstance(response, dict) and response.get("success") is False:
        return False
    return True


def _live_error_message(result: Dict[str, Any]) -> str:
    mode = str(result.get("mode") or "unknown")
    if mode != "live":
        return f"OpenSPG 调用未进入 live 模式（mode={mode}）"
    http_status = int(result.get("http_status") or 0)
    response = result.get("response")
    if http_status >= 400 or http_status <= 0:
        return f"OpenSPG HTTP 调用失败（status={http_status}）"
    if isinstance(response, dict) and response.get("success") is False:
        msg = response.get("errorMsg") or response.get("message") or response.get("msg")
        return str(msg or "OpenSPG 返回 success=false")
    if isinstance(response, dict):
        text = str(response.get("text") or "").strip()
        if text:
            return text
    if isinstance(response, str):
        text = response.strip()
        if text:
            return text
    return "OpenSPG 返回异常"


def _unwrap_http_result_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and "result" in payload:
        return payload.get("result")
    return payload


def _is_schema_already_exists_error(result: Dict[str, Any]) -> bool:
    response = result.get("response")
    if isinstance(response, dict):
        text = str(response.get("text") or "").lower()
    elif isinstance(response, str):
        text = response.lower()
    else:
        return False
    if "exist spg type with name" in text:
        return True
    if "spg type" in text and "already exists" in text:
        return True
    return False


async def _apply_schema_with_public_fallback(
    *,
    project_id: int,
    schema_script: str,
) -> Dict[str, Any]:
    """优先走 /v1/schemas，失败后自动回退到 /public/v1/schema/alterSchema。"""
    script = str(schema_script or "").strip()
    if not script:
        return {
            "mode": "skip",
            "reason": "schema_script is empty",
        }

    schema_apply_result = await apply_openspg_schema_script(
        project_id=project_id,
        schema_script=script,
    )
    legacy_success = _is_live_success(schema_apply_result) or (
        schema_apply_result.get("mode") == "live" and "http_status" not in schema_apply_result
    )
    if legacy_success:
        schema_apply_result.setdefault("meta", {})
        schema_apply_result["meta"]["apply_mode"] = "legacy_v1_schemas"
        return schema_apply_result

    project_result = await get_openspg_project(project_id=project_id)
    project_namespace = _parse_project_namespace(project_result.get("response")) or "zhilian"
    try:
        schema_draft = _parse_schema_dsl_to_public_draft(
            schema_script=script,
            project_namespace=project_namespace,
        )
    except ValueError as exc:
        schema_apply_result.setdefault("meta", {})
        schema_apply_result["meta"].update(
            {
                "apply_mode": "legacy_only_failed",
                "project_namespace": project_namespace,
                "legacy_apply_error": _live_error_message(schema_apply_result),
                "public_fallback_error": str(exc),
            }
        )
        return schema_apply_result

    public_apply_result = await alter_openspg_schema_draft_public(
        project_id=project_id,
        schema_draft=schema_draft,
    )
    public_apply_result.setdefault("meta", {})
    public_apply_result["meta"]["apply_mode"] = "public_alter_schema_fallback"
    public_apply_result["meta"]["project_namespace"] = project_namespace
    public_apply_result["meta"]["legacy_apply_error"] = _live_error_message(schema_apply_result)

    if (not _is_live_success(public_apply_result)) and _is_schema_already_exists_error(
        public_apply_result
    ):
        public_apply_result = {
            "mode": "live",
            "http_status": 200,
            "request": public_apply_result.get("request", {}),
            "response": {
                "success": True,
                "result": True,
                "message": "schema already exists, treat as success",
            },
            "meta": {
                **public_apply_result.get("meta", {}),
                "apply_mode": "public_alter_schema_fallback",
                "project_namespace": project_namespace,
                "legacy_apply_error": _live_error_message(schema_apply_result),
                "idempotent": True,
            },
        }
    return public_apply_result


def _looks_like_uploaded_file_url(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.startswith(("http://", "https://", "minio://", "file://", "/")):
        return True
    if "://" not in text and "/" in text:
        name = text.rsplit("/", 1)[-1]
        if "." in name:
            return True
    return False


def _extract_uploaded_file_url(payload: Any) -> str:
    stack: List[Any] = [payload]
    visited_ids: set[int] = set()
    preferred_keys = (
        "fileUrl",
        "file_url",
        "url",
        "filePath",
        "file_path",
        "path",
        "objectUrl",
        "object_url",
    )
    nested_keys = ("result", "data", "payload", "file", "object")

    while stack:
        current = stack.pop(0)
        current_id = id(current)
        if current_id in visited_ids:
            continue
        visited_ids.add(current_id)

        if isinstance(current, str):
            value = current.strip()
            if _looks_like_uploaded_file_url(value):
                return value
            continue

        if isinstance(current, dict):
            for key in preferred_keys:
                raw = current.get(key)
                if isinstance(raw, str):
                    value = raw.strip()
                    if _looks_like_uploaded_file_url(value):
                        return value

            for key in nested_keys:
                if key in current:
                    stack.append(current.get(key))
            continue

        if isinstance(current, list):
            stack.extend(current)

    return ""


_ALLOWED_UPLOAD_SUFFIX = {"md", "txt", "docx", "pdf"}
_CONTENT_TYPE_BY_SUFFIX = {
    "md": "text/markdown",
    "txt": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}
_MODEL_STUDIO_SCHEMA_SCRIPT_CACHE: Dict[int, str] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _demo_data_dir() -> Path:
    root = os.getenv("OPENSPG_DEMO_DATA_DIR")
    if not root:
        root = str(Path(__file__).resolve().parents[2] / "data" / "openspg_demo")
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _model_profile_state_file() -> Path:
    return _demo_data_dir() / "model_profiles.json"


def _workflow_state_file() -> Path:
    return _demo_data_dir() / "workflow_runs.json"


def _initial_step_statuses() -> Dict[str, Dict[str, Any]]:
    return {key: {"status": "idle"} for key in _WORKFLOW_STEP_KEYS}


def _set_step_status(run_payload: Dict[str, Any], step_key: str, status: str, **extra: Any) -> None:
    step_statuses = run_payload.get("step_statuses")
    if not isinstance(step_statuses, dict):
        step_statuses = _initial_step_statuses()
        run_payload["step_statuses"] = step_statuses
    payload = {"status": status}
    payload.update(extra)
    step_statuses[step_key] = payload


def _mark_run_updated(run_payload: Dict[str, Any]) -> None:
    run_payload["updated_at"] = _utc_now_iso()


def _save_updated_workflow_run(run_payload: Dict[str, Any]) -> None:
    _mark_run_updated(run_payload)
    _save_workflow_run(run_payload)


def _annotate_openspg_result(result: Dict[str, Any], *, action: str) -> Dict[str, Any]:
    payload = dict(result or {})
    meta = dict(payload.get("meta") or {})
    effective_success = _is_live_success(payload)
    meta["action"] = action
    meta["effective_success"] = effective_success
    if not effective_success:
        meta["effective_error"] = _live_error_message(payload)
    payload["meta"] = meta
    return payload


def _result_effective_success(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    meta = result.get("meta")
    if isinstance(meta, dict) and "effective_success" in meta:
        return bool(meta.get("effective_success"))
    return _is_live_success(result)


def _result_effective_error(result: Any) -> str:
    if not isinstance(result, dict):
        return "unknown error"
    meta = result.get("meta")
    if isinstance(meta, dict):
        text = str(meta.get("effective_error") or "").strip()
        if text:
            return text
    return _live_error_message(result)


def _workflow_fallback_run_payload(
    run_id: str,
    request_payload: Dict[str, Any],
    active_model_profile: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    project_id = int(request_payload.get("project_id") or 1)
    runtime_profile = normalize_runtime_profile(request_payload.get("runtime_profile"))
    return {
        "run_id": run_id,
        "project_id": project_id,
        "runtime_profile": runtime_profile,
        "status": "queued",
        "started_at": _utc_now_iso(),
        "active_model_profile": active_model_profile,
        "request": request_payload,
        "step_statuses": _initial_step_statuses(),
    }


def _compute_workflow_final_status(
    *,
    request: WorkflowNewsRunRequest,
    step_statuses: Dict[str, Dict[str, Any]],
    schema_apply_result: Dict[str, Any],
    builder_submit_result: Dict[str, Any],
    graph_materialize_result: Optional[Dict[str, Any]] = None,
) -> tuple[str, List[str]]:
    warnings: List[str] = []
    degraded = False
    runtime_profile = normalize_runtime_profile(request.runtime_profile)

    for step_key in ("collect", "process", "extract", "apply"):
        step_payload = step_statuses.get(step_key) if isinstance(step_statuses, dict) else None
        if isinstance(step_payload, dict) and step_payload.get("status") == "failed":
            return "failed", warnings

    if (
        runtime_profile == "kag_openspg"
        and request.apply_schema
        and not _result_effective_success(schema_apply_result)
    ):
        degraded = True
        warnings.append(f"Schema: {_result_effective_error(schema_apply_result)}")

    if request.submit_builder:
        if not isinstance(builder_submit_result, dict):
            degraded = True
            warnings.append("Builder: 未生成执行结果")
        elif builder_submit_result.get("mode") == "skip":
            degraded = True
            warnings.append(f"Builder: {builder_submit_result.get('reason') or '执行已跳过'}")
        elif not _result_effective_success(builder_submit_result):
            degraded = True
            warnings.append(f"Builder: {_result_effective_error(builder_submit_result)}")

    if runtime_profile == "kag_openspg" and request.materialize_graph:
        if not isinstance(graph_materialize_result, dict):
            degraded = True
            warnings.append("GraphMaterialize: 未生成执行结果")
        elif str(graph_materialize_result.get("status") or "").strip().lower() != "success":
            degraded = True
            warnings.append(
                f"GraphMaterialize: {graph_materialize_result.get('error') or graph_materialize_result.get('status') or 'failed'}"
            )

    return ("partial_success", warnings) if degraded else ("success", warnings)


def _mock_result_for_exception(*, action: str, message: str) -> Dict[str, Any]:
    return {
        "mode": "mock",
        "http_status": 500,
        "response": {"message": message},
        "meta": {
            "action": action,
            "effective_success": False,
            "effective_error": message,
        },
    }


async def _materialize_graph_for_bridge_run(*, bridge_run: Dict[str, Any], project_id: int) -> Dict[str, Any]:
    batch_file_path = str((bridge_run or {}).get("batch_file_path") or "").strip()
    export_count = int((bridge_run or {}).get("export_count") or 0)
    if not batch_file_path or export_count <= 0:
        return {
            "status": "skip",
            "reason": "missing batch file or export_count=0",
        }
    try:
        result = await async_materialize_bridge_batch(
            batch_file_path=batch_file_path,
            project_id=project_id,
        )
        return {
            **result,
            "status": "success",
        }
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "batch_file_path": batch_file_path,
        }


def _detail_metric(label: str, value: Any) -> Dict[str, Any]:
    return {"label": label, "value": value}


def _detail_table(title: str, columns: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"title": title, "columns": columns, "rows": rows}


def _detail_section_table(title: str, columns: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"type": "table", "title": title, "table": _detail_table(title, columns, rows)}


def _detail_section_code(title: str, language: str, content: str) -> Dict[str, Any]:
    return {"type": "code", "title": title, "language": language, "content": content}


def _detail_section_json(title: str, payload: Any) -> Dict[str, Any]:
    return {"type": "json", "title": title, "payload": payload}


def _kv_table(title: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = [{"field": key, "value": value} for key, value in (payload or {}).items()]
    return _detail_table(
        title,
        [
            {"title": "字段", "dataIndex": "field", "key": "field"},
            {"title": "值", "dataIndex": "value", "key": "value"},
        ],
        rows,
    )


def _schema_entity_type_pattern() -> re.Pattern[str]:
    return re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")


def _schema_relation_pattern() -> re.Pattern[str]:
    return re.compile(
        r"^([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*-\s*([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*$"
    )


def _parse_schema_script_details(schema_script: str) -> Dict[str, Any]:
    entities: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    entity_pattern = _schema_entity_type_pattern()
    relation_pattern = _schema_relation_pattern()
    relation_block_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")
    current_entity: Optional[Dict[str, str]] = None
    current_section = ""
    current_entity_indent = 0

    for raw in str(schema_script or "").splitlines():
        line = raw.strip()
        indent = len(raw) - len(raw.lstrip(" \t"))
        if not line or line.startswith("namespace "):
            continue
        relation_match = relation_pattern.match(line)
        if relation_match:
            source_en, source_zh, rel_en, rel_zh, target_en, target_zh = relation_match.groups()
            if source_en not in nodes:
                nodes[source_en] = {"id": source_en, "name": source_zh or source_en, "type": "ENTITY"}
            if target_en not in nodes:
                nodes[target_en] = {"id": target_en, "name": target_zh or target_en, "type": "ENTITY"}
            relations.append(
                {
                    "source_type": source_en,
                    "source_name": source_zh or source_en,
                    "relation_type": rel_en,
                    "relation_name": rel_zh or rel_en,
                    "target_type": target_en,
                    "target_name": target_zh or target_en,
                }
            )
            edges.append(
                {
                    "source": source_en,
                    "target": target_en,
                    "relationship": rel_zh or rel_en,
                }
            )
            continue

        entity_match = entity_pattern.match(line)
        if entity_match:
            type_en, type_zh, type_kind = entity_match.groups()
            if type_kind in {"EntityType", "ConceptType", "IndexType"}:
                current_entity = {
                    "type_name": type_en,
                    "display_name": type_zh or type_en,
                    "type_kind": type_kind,
                }
                current_section = ""
                current_entity_indent = indent
                entities.append(current_entity)
                nodes[type_en] = {
                    "id": type_en,
                    "name": type_zh or type_en,
                    "type": type_kind.replace("Type", "").upper(),
                }
                continue

        if current_entity and indent > current_entity_indent:
            if line == "relations:":
                current_section = "relations"
                continue
            if current_section == "relations":
                block_match = relation_block_pattern.match(line)
                if block_match:
                    rel_en, rel_zh, target_en = block_match.groups()
                    source_en = current_entity["type_name"]
                    source_zh = current_entity["display_name"]
                    nodes.setdefault(target_en, {"id": target_en, "name": target_en, "type": "ENTITY"})
                    relations.append(
                        {
                            "source_type": source_en,
                            "source_name": source_zh,
                            "relation_type": rel_en,
                            "relation_name": rel_zh or rel_en,
                            "target_type": target_en,
                            "target_name": target_en,
                        }
                    )
                    edges.append(
                        {
                            "source": source_en,
                            "target": target_en,
                            "relationship": rel_zh or rel_en,
                        }
                    )
                    continue

    entities.sort(key=lambda item: item["type_name"])
    relations.sort(key=lambda item: (item["source_type"], item["relation_type"], item["target_type"]))
    return {
        "entities": entities,
        "relations": relations,
        "graph": {"nodes": list(nodes.values()), "edges": edges},
    }


def _load_batch_records_for_run(run_payload: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
    bridge_run = run_payload.get("bridge_run")
    if not isinstance(bridge_run, dict):
        return []
    batch_file_path = str(bridge_run.get("batch_file_path") or "").strip()
    if not batch_file_path:
        return []
    batch_file = Path(batch_file_path)
    if not batch_file.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in batch_file.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
            if len(rows) >= limit:
                break
    except Exception:
        return []
    return rows


_PREVIEW_COMPANY_PATTERN = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9·]{2,24}(?:机器人|车企|科技|智能|集团|股份|公司|厂|研究院))"
)
_PREVIEW_TECH_KEYWORDS = [
    "具身智能",
    "机器视觉",
    "伺服",
    "减速器",
    "控制器",
    "SLAM",
    "大模型",
    "工业机器人",
    "协作机器人",
    "人形机器人",
    "自动化产线",
    "路径规划",
]


def _extract_preview_companies(title: str, content: str) -> List[str]:
    text = f"{title} {content}".strip()
    values: List[str] = []
    for match in _PREVIEW_COMPANY_PATTERN.findall(text):
        name = str(match).strip("，。；：、()（）[]【】 ")
        if len(name) < 2 or name in values:
            continue
        values.append(name)
    return values[:6]


def _extract_preview_techs(title: str, content: str) -> List[str]:
    text = f"{title} {content}".strip()
    result: List[str] = []
    for keyword in _PREVIEW_TECH_KEYWORDS:
        if keyword in text and keyword not in result:
            result.append(keyword)
    return result[:6]


def _build_extract_preview(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    for record in records:
        doc_id = str(record.get("doc_id") or "").strip()
        title = str(record.get("title") or "未命名资讯").strip()
        content = str(record.get("content") or record.get("summary") or "").strip()
        if not doc_id:
            continue
        nodes.setdefault(doc_id, {"id": doc_id, "name": title, "type": "DOCUMENT"})

        for company in _extract_preview_companies(title, content):
            company_id = f"company::{company}"
            nodes.setdefault(company_id, {"id": company_id, "name": company, "type": "COMPANY"})
            rows.append({"doc_id": doc_id, "title": title, "object_type": "Company", "object_name": company})
            edges.append({"source": doc_id, "target": company_id, "relationship": "mentionsCompany"})

        for tech in _extract_preview_techs(title, content):
            tech_id = f"tech::{tech}"
            nodes.setdefault(tech_id, {"id": tech_id, "name": tech, "type": "TECHNOLOGY"})
            rows.append({"doc_id": doc_id, "title": title, "object_type": "Technology", "object_name": tech})
            edges.append({"source": doc_id, "target": tech_id, "relationship": "mentionsTech"})

    limited_nodes = list(nodes.values())[:40]
    allowed_ids = {item["id"] for item in limited_nodes}
    limited_edges = [
        item
        for item in edges
        if item.get("source") in allowed_ids and item.get("target") in allowed_ids
    ][:60]
    return {
        "rows": rows[:30],
        "graph": {"nodes": limited_nodes, "edges": limited_edges},
    }


def _build_headline_graph(headline_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    for detail in headline_details:
        event_id = str(detail.get("event_id") or "").strip()
        if not event_id:
            continue
        title = str(detail.get("headline_title") or detail.get("event_type_zh") or event_id).strip()
        nodes.setdefault(event_id, {"id": event_id, "name": title, "type": "EVENT"})

        for company in detail.get("companies") or []:
            company_name = str(company).strip()
            if not company_name:
                continue
            company_id = f"company::{company_name}"
            nodes.setdefault(company_id, {"id": company_id, "name": company_name, "type": "COMPANY"})
            edges.append({"source": event_id, "target": company_id, "relationship": "involves"})

        for evidence in detail.get("evidence_news") or []:
            news_id = str(evidence.get("news_id") or evidence.get("doc_id") or evidence.get("title") or "").strip()
            if not news_id:
                continue
            news_title = str(evidence.get("title") or news_id).strip()
            nodes.setdefault(news_id, {"id": news_id, "name": news_title, "type": "NEWS"})
            edges.append({"source": event_id, "target": news_id, "relationship": "evidence"})
    limited_nodes = list(nodes.values())[:50]
    allowed_ids = {item["id"] for item in limited_nodes}
    limited_edges = [
        item
        for item in edges
        if item.get("source") in allowed_ids and item.get("target") in allowed_ids
    ][:80]
    return {"nodes": limited_nodes, "edges": limited_edges}


def _build_step_detail_meta(run_payload: Dict[str, Any], step_key: str, summary: str = "") -> Dict[str, Any]:
    step_status = ((run_payload.get("step_statuses") or {}).get(step_key) or {}).get("status") or "idle"
    return {
        "run_id": run_payload.get("run_id"),
        "project_id": run_payload.get("project_id"),
        "step_key": step_key,
        "title": _WORKFLOW_STEP_TITLES.get(step_key, step_key),
        "description": _WORKFLOW_STEP_DESCRIPTIONS.get(step_key, ""),
        "status": step_status,
        "summary": summary,
    }


def _build_model_step_detail(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    schema_script = str(
        (run_payload.get("compiled_schema_script"))
        or ((run_payload.get("active_model_profile") or {}).get("schema_script"))
        or ((run_payload.get("request") or {}).get("schema_script"))
        or ""
    ).strip()
    parsed = _parse_schema_script_details(schema_script)
    summary = f"本次建模包含 {len(parsed['entities'])} 个类型、{len(parsed['relations'])} 条关系。"
    return {
        "meta": _build_step_detail_meta(run_payload, "model", summary),
        "input": {
            "metrics": [
                _detail_metric("Schema 长度", len(schema_script.splitlines()) if schema_script else 0),
            ],
            "code": {"title": "Schema DSL", "language": "text", "content": schema_script},
        },
        "output": {
            "metrics": [
                _detail_metric("类型数", len(parsed["entities"])),
                _detail_metric("关系数", len(parsed["relations"])),
            ],
            "table": _detail_table(
                "类型清单",
                [
                    {"title": "英文名", "dataIndex": "type_name", "key": "type_name"},
                    {"title": "展示名", "dataIndex": "display_name", "key": "display_name"},
                    {"title": "类型", "dataIndex": "type_kind", "key": "type_kind"},
                ],
                parsed["entities"],
            ),
            "sections": [
                _detail_section_table(
                    "关系清单",
                    [
                        {"title": "源类型", "dataIndex": "source_name", "key": "source_name"},
                        {"title": "关系", "dataIndex": "relation_name", "key": "relation_name"},
                        {"title": "目标类型", "dataIndex": "target_name", "key": "target_name"},
                    ],
                    parsed["relations"],
                ),
                _detail_section_json("Schema 提交结果", run_payload.get("schema_commit_result") or run_payload.get("schema_apply_result")),
                _detail_section_json("KAG schema 导出", run_payload.get("kag_schema_export")),
                _detail_section_json("激活结果", run_payload.get("activate_result") or run_payload.get("active_model_profile")),
            ],
        },
        "visualization": {
            "type": "graph",
            "title": "Schema 结构图",
            "data": parsed["graph"],
        },
    }


def _build_collect_step_detail(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    request_payload = run_payload.get("request") or {}
    ingest_result = run_payload.get("ingest_result") or {}
    rows, data_source = _read_news_rows(
        limit=max(int(request_payload.get("max_entries_per_feed") or 5) * 5, 10),
        allow_demo_fallback=False,
    )
    sample_rows = [
        {
            "doc_id": str(row.get("doc_id") or row.get("doc_hash") or row.get("_id") or row.get("title") or ""),
            "title": str(row.get("title") or ""),
            "source_name": str(row.get("source_name") or row.get("source") or ""),
            "publish_time": str(row.get("publish_time") or row.get("published_at") or ""),
        }
        for row in rows[:10]
    ]
    summary = f"采集完成，新增 {ingest_result.get('inserted_count') or 0} 条，去重 {ingest_result.get('duplicate_count') or 0} 条。"
    return {
        "meta": _build_step_detail_meta(run_payload, "collect", summary),
        "input": {
            "metrics": [
                _detail_metric("时间窗(h)", request_payload.get("hours_ago")),
                _detail_metric("单源上限", request_payload.get("max_entries_per_feed")),
            ],
            "json": {"payload": request_payload},
        },
        "output": {
            "metrics": [
                _detail_metric("抓取条数", ingest_result.get("fetched_count") or 0),
                _detail_metric("新增条数", ingest_result.get("inserted_count") or 0),
                _detail_metric("重复条数", ingest_result.get("duplicate_count") or 0),
                _detail_metric("拉取模式", ingest_result.get("pull_mode") or "-"),
                _detail_metric("数据源", data_source),
            ],
            "table": _detail_table(
                "采集资讯样例",
                [
                    {"title": "doc_id", "dataIndex": "doc_id", "key": "doc_id"},
                    {"title": "标题", "dataIndex": "title", "key": "title"},
                    {"title": "来源", "dataIndex": "source_name", "key": "source_name"},
                    {"title": "发布时间", "dataIndex": "publish_time", "key": "publish_time"},
                ],
                sample_rows,
            ),
            "sections": [
                _detail_section_json("采集返回", ingest_result),
            ],
        },
        "visualization": {
            "type": "stats",
            "title": "采集概览",
            "data": {
                "items": [
                    {"label": "抓取", "value": ingest_result.get("fetched_count") or 0},
                    {"label": "新增", "value": ingest_result.get("inserted_count") or 0},
                    {"label": "重复", "value": ingest_result.get("duplicate_count") or 0},
                ]
            },
        },
    }


def _build_process_step_detail(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    request_payload = run_payload.get("request") or {}
    preview = run_payload.get("process_preview") or {}
    bridge_status = run_payload.get("bridge_status") or {}
    records = _load_batch_records_for_run(run_payload, limit=10)
    sample_rows = [
        {
            "doc_id": row.get("doc_id"),
            "title": row.get("title"),
            "source_name": row.get("source_name"),
            "publish_time": row.get("publish_time"),
        }
        for row in records
    ]
    summary = f"已生成批次预览，当前数据源 {preview.get('data_source') or '-'}，样例 {len(sample_rows)} 条。"
    return {
        "meta": _build_step_detail_meta(run_payload, "process", summary),
        "input": {
            "metrics": [
                _detail_metric("bridge_limit", request_payload.get("bridge_limit")),
                _detail_metric("force_full", request_payload.get("force_full")),
            ],
            "json": {"payload": preview},
        },
        "output": {
            "metrics": [
                _detail_metric("处理记录数", preview.get("row_count") or 0),
                _detail_metric("批次样例数", len(sample_rows)),
                _detail_metric("cursor", ((bridge_status.get("cursor") or {}).get("last_seen_time")) or "-"),
            ],
            "table": _detail_table(
                "标准化样例",
                [
                    {"title": "doc_id", "dataIndex": "doc_id", "key": "doc_id"},
                    {"title": "标题", "dataIndex": "title", "key": "title"},
                    {"title": "来源", "dataIndex": "source_name", "key": "source_name"},
                    {"title": "发布时间", "dataIndex": "publish_time", "key": "publish_time"},
                ],
                sample_rows,
            ),
            "sections": [
                _detail_section_code(
                    "JSONL 预览",
                    "json",
                    "\n".join(json.dumps(row, ensure_ascii=False) for row in records[:3]),
                ),
            ],
        },
        "visualization": {
            "type": "stats",
            "title": "处理概览",
            "data": {
                "items": [
                    {"label": "记录数", "value": preview.get("row_count") or 0},
                    {"label": "样例", "value": len(sample_rows)},
                ]
            },
        },
    }


def _build_extract_step_detail(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    runtime_profile = normalize_runtime_profile(
        run_payload.get("runtime_profile") or (run_payload.get("request") or {}).get("runtime_profile")
    )
    if runtime_profile == "openks_direct":
        preview = run_payload.get("openks_extract_preview") or {}
        rows = list(preview.get("rows") or [])
        summary = f"OpenKS 直连模式下，当前待构建队列 {preview.get('pending_count') or 0} 条。"
        return {
            "meta": _build_step_detail_meta(run_payload, "extract", summary),
            "input": {
                "metrics": [
                    _detail_metric("runtime_profile", runtime_profile),
                    _detail_metric("pending_count", preview.get("pending_count") or 0),
                ],
                "table": _detail_table(
                    "待构建队列预览",
                    [
                        {"title": "queue_id", "dataIndex": "queue_id", "key": "queue_id"},
                        {"title": "doc_id", "dataIndex": "doc_id", "key": "doc_id"},
                        {"title": "标题", "dataIndex": "title", "key": "title"},
                        {"title": "状态", "dataIndex": "status", "key": "status"},
                    ],
                    rows[:12],
                ),
            },
            "output": {
                "metrics": [
                    _detail_metric("候选对象数", preview.get("pending_count") or 0),
                    _detail_metric("图节点数", 0),
                    _detail_metric("图边数", 0),
                ],
                "table": _detail_table("队列样例", [], []),
                "sections": [
                    _detail_section_json("openks_extract_preview", preview),
                ],
            },
            "visualization": {
                "type": "stats",
                "title": "OpenKS 队列预览",
                "data": {
                    "items": [
                        {"label": "runtime_profile", "value": runtime_profile},
                        {"label": "pending_count", "value": preview.get("pending_count") or 0},
                    ]
                },
            },
        }

    bridge_run = run_payload.get("bridge_run") or {}
    records = _load_batch_records_for_run(run_payload, limit=12)
    preview = _build_extract_preview(records)
    summary = f"已导出 {bridge_run.get('export_count') or 0} 条待写入批次，并生成对象映射预览。"
    return {
        "meta": _build_step_detail_meta(run_payload, "extract", summary),
        "input": {
            "metrics": [
                _detail_metric("批次文件", bridge_run.get("batch_file_name") or "-"),
                _detail_metric("export_count", bridge_run.get("export_count") or 0),
            ],
            "table": _detail_table(
                "批次样例",
                [
                    {"title": "doc_id", "dataIndex": "doc_id", "key": "doc_id"},
                    {"title": "标题", "dataIndex": "title", "key": "title"},
                    {"title": "来源", "dataIndex": "source_name", "key": "source_name"},
                ],
                [
                    {"doc_id": row.get("doc_id"), "title": row.get("title"), "source_name": row.get("source_name")}
                    for row in records
                ],
            ),
        },
        "output": {
            "metrics": [
                _detail_metric("候选对象数", len(preview["rows"])),
                _detail_metric("图节点数", len(preview["graph"]["nodes"])),
                _detail_metric("图边数", len(preview["graph"]["edges"])),
            ],
            "table": _detail_table(
                "待写入对象预览",
                [
                    {"title": "文档", "dataIndex": "title", "key": "title"},
                    {"title": "对象类型", "dataIndex": "object_type", "key": "object_type"},
                    {"title": "对象名称", "dataIndex": "object_name", "key": "object_name"},
                ],
                preview["rows"],
            ),
            "sections": [
                _detail_section_json("bridge_run", bridge_run),
            ],
        },
        "visualization": {
            "type": "graph",
            "title": "文档到对象映射图",
            "data": preview["graph"],
        },
    }


def _build_execute_step_detail(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    runtime_profile = normalize_runtime_profile(
        run_payload.get("runtime_profile") or (run_payload.get("request") or {}).get("runtime_profile")
    )
    if runtime_profile == "openks_direct":
        build_result = run_payload.get("openks_build_result") or {}
        runtime_binding = run_payload.get("runtime_binding") or {}
        summary = f"OpenKS 直连模式处理 {build_result.get('processed') or 0} 条队列。"
        return {
            "meta": _build_step_detail_meta(run_payload, "execute", summary),
            "input": {
                "metrics": [
                    _detail_metric("runtime_profile", runtime_profile),
                    _detail_metric("limit", (run_payload.get("request") or {}).get("bridge_limit") or "-"),
                ],
                "table": _kv_table("OpenKS 执行参数", run_payload.get("request") or {}),
                "sections": [
                    _detail_section_json("openks_build_result", build_result),
                ],
            },
            "output": {
                "metrics": [
                    _detail_metric("run_id", build_result.get("run_id") or "-"),
                    _detail_metric("artifact_id", build_result.get("artifact_id") or "-"),
                    _detail_metric("processed", build_result.get("processed") or 0),
                ],
                "table": _kv_table("运行时绑定", {
                    "runtime_run_id": ((runtime_binding.get("run") or {}).get("run_id") or "-"),
                    "artifact_id": ((runtime_binding.get("artifact") or {}).get("artifact_id") or "-"),
                    "release_id": ((runtime_binding.get("release") or {}).get("release_id") or "-"),
                }),
                "sections": [
                    _detail_section_json("runtime_binding", runtime_binding),
                ],
            },
            "visualization": {
                "type": "timeline",
                "title": "OpenKS 执行时间线",
                "data": {
                    "items": [
                        {"label": "运行模式", "status": "finish", "description": runtime_profile},
                        {"label": "news_kg 构建", "status": "finish", "description": build_result.get("run_id") or "-"},
                        {"label": "Artifact 绑定", "status": "finish", "description": ((runtime_binding.get("artifact") or {}).get("artifact_id") or "-")},
                    ]
                },
            },
        }

    builder_result = run_payload.get("builder_submit_result") or {}
    bridge_run = run_payload.get("bridge_run") or {}
    request_json = ((builder_result.get("request") or {}).get("json") or {}) if isinstance(builder_result, dict) else {}
    response_payload = builder_result.get("response") if isinstance(builder_result, dict) else {}
    response_summary = {
        "mode": builder_result.get("mode") or "-",
        "http_status": builder_result.get("http_status") or "-",
        "effective_success": _result_effective_success(builder_result),
        "trace_id": response_payload.get("traceId") if isinstance(response_payload, dict) else "-",
    }
    runtime_binding = run_payload.get("runtime_binding") or {}
    summary = f"Builder 执行模式 {builder_result.get('mode') or '-'}。"
    return {
        "meta": _build_step_detail_meta(run_payload, "execute", summary),
        "input": {
            "metrics": [
                _detail_metric("project_id", run_payload.get("project_id")),
                _detail_metric("批次文件", bridge_run.get("batch_file_name") or "-"),
            ],
            "table": _kv_table("Builder 关键参数", request_json),
            "sections": [
                _detail_section_json("Builder 请求", builder_result.get("request")),
            ],
        },
        "output": {
            "metrics": [
                _detail_metric("mode", builder_result.get("mode") or "-"),
                _detail_metric("http_status", builder_result.get("http_status") or "-"),
                _detail_metric("effective_success", _result_effective_success(builder_result)),
            ],
            "table": _kv_table("Builder 结果摘要", response_summary),
            "sections": [
                _detail_section_json("Builder 返回", builder_result.get("response")),
                _detail_section_json("运行时绑定", runtime_binding),
            ],
        },
        "visualization": {
            "type": "timeline",
            "title": "执行时间线",
            "data": {
                "items": [
                    {"label": "批次准备", "status": "finish", "description": bridge_run.get("batch_file_name") or "-"},
                    {"label": "Builder 提交", "status": "finish" if _result_effective_success(builder_result) else "error", "description": _result_effective_error(builder_result) if not _result_effective_success(builder_result) else "远端执行已受理"},
                    {"label": "Artifact 绑定", "status": "finish", "description": ((runtime_binding.get("artifact") or {}).get("artifact_id") or "-")},
                    {"label": "Release 生成", "status": "finish", "description": ((runtime_binding.get("release") or {}).get("release_id") or "-")},
                ]
            },
        },
    }


def _build_apply_step_detail(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    request_payload = run_payload.get("request") or {}
    snapshot = run_payload.get("headlines_snapshot") or {}
    top_ids = snapshot.get("top_headline_ids") or []
    rows, data_source = _read_news_rows(
        limit=max(int(request_payload.get("headlines_top_n") or 20) * 10, 100),
        allow_demo_fallback=False,
    )
    headline_details = [
        detail
        for event_id in top_ids
        for detail in [get_event_detail_from_news(rows, event_id=event_id, hours=int(request_payload.get("hours_ago") or 24))]
        if detail
    ]
    table_rows = [
        {
            "event_id": item.get("event_id"),
            "headline_title": item.get("headline_title"),
            "event_type_zh": item.get("event_type_zh"),
            "source_count": item.get("source_count"),
            "headline_score": item.get("headline_score"),
        }
        for item in headline_details
    ]
    summary = f"已生成 {len(table_rows)} 条头条，数据源 {data_source}。"
    runtime_binding = run_payload.get("runtime_binding") or {}
    return {
        "meta": _build_step_detail_meta(run_payload, "apply", summary),
        "input": {
            "metrics": [
                _detail_metric("时间窗(h)", request_payload.get("hours_ago")),
                _detail_metric("top_n", request_payload.get("headlines_top_n")),
                _detail_metric("data_source", data_source),
                _detail_metric("artifact_id", ((runtime_binding.get("artifact") or {}).get("artifact_id") or "-")),
                _detail_metric("release_id", ((runtime_binding.get("release") or {}).get("release_id") or "-")),
            ],
            "json": {"payload": snapshot.get("stats") or {}},
        },
        "output": {
            "metrics": [
                _detail_metric("头条数", len(table_rows)),
                _detail_metric("事件数", (snapshot.get("stats") or {}).get("event_count") or 0),
                _detail_metric("资讯数", (snapshot.get("stats") or {}).get("news_count") or 0),
            ],
            "table": _detail_table(
                "头条列表",
                [
                    {"title": "标题", "dataIndex": "headline_title", "key": "headline_title"},
                    {"title": "事件类型", "dataIndex": "event_type_zh", "key": "event_type_zh"},
                    {"title": "来源数", "dataIndex": "source_count", "key": "source_count"},
                    {"title": "评分", "dataIndex": "headline_score", "key": "headline_score"},
                ],
                table_rows,
            ),
            "sections": [
                _detail_section_json("头条详情", headline_details[:3]),
                _detail_section_json("消费上下文", runtime_binding),
            ],
        },
        "visualization": {
            "type": "graph",
            "title": "头条证据链图",
            "data": _build_headline_graph(headline_details),
        },
    }


def _build_news_workflow_step_detail(run_payload: Dict[str, Any], step_key: str) -> Dict[str, Any]:
    builders = {
        "model": _build_model_step_detail,
        "collect": _build_collect_step_detail,
        "process": _build_process_step_detail,
        "extract": _build_extract_step_detail,
        "execute": _build_execute_step_detail,
        "apply": _build_apply_step_detail,
    }
    builder = builders.get(step_key)
    if builder is None:
        raise HTTPException(status_code=404, detail="workflow step 不存在")
    return builder(run_payload)


def _load_json_state(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    if not isinstance(payload, dict):
        return default
    merged = dict(default)
    merged.update(payload)
    return merged


def _save_json_state(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _schema_hash(schema_script: str) -> str:
    text = str(schema_script or "").strip()
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _load_model_profile_state() -> Dict[str, Any]:
    return _load_json_state(
        _model_profile_state_file(),
        {"active_by_project": {}, "profiles_by_project": {}},
    )


def _save_model_profile_state(state: Dict[str, Any]) -> None:
    _save_json_state(_model_profile_state_file(), state)


def _activate_model_profile(
    *,
    project_id: int,
    schema_script: str,
    label: str,
    source: str,
) -> Dict[str, Any]:
    script = str(schema_script or "").strip()
    if not script:
        raise ValueError("schema_script 不能为空")
    profile = {
        "model_profile_id": f"mp_{int(time.time())}_{secrets.token_hex(4)}",
        "project_id": int(project_id),
        "schema_script": script,
        "schema_hash": _schema_hash(script),
        "label": label or "default",
        "source": source,
        "activated_at": _utc_now_iso(),
    }
    with _MODEL_PROFILE_LOCK:
        state = _load_json_state(
            _model_profile_state_file(),
            {"active_by_project": {}, "profiles_by_project": {}},
        )
        project_key = str(project_id)
        profiles = state.get("profiles_by_project", {})
        if not isinstance(profiles, dict):
            profiles = {}
        project_profiles = profiles.get(project_key)
        if not isinstance(project_profiles, list):
            project_profiles = []
        project_profiles = [profile, *project_profiles][:20]
        profiles[project_key] = project_profiles
        state["profiles_by_project"] = profiles
        active = state.get("active_by_project", {})
        if not isinstance(active, dict):
            active = {}
        active[project_key] = profile
        state["active_by_project"] = active
        _save_json_state(_model_profile_state_file(), state)
    _MODEL_STUDIO_SCHEMA_SCRIPT_CACHE[int(project_id)] = script
    return profile


def _get_active_model_profile(project_id: int) -> Optional[Dict[str, Any]]:
    with _MODEL_PROFILE_LOCK:
        state = _load_json_state(
            _model_profile_state_file(),
            {"active_by_project": {}, "profiles_by_project": {}},
        )
        active = state.get("active_by_project", {})
        if not isinstance(active, dict):
            return None
        profile = active.get(str(project_id))
        return profile if isinstance(profile, dict) else None


def _load_workflow_state() -> Dict[str, Any]:
    with _WORKFLOW_STATE_LOCK:
        return _load_json_state(
            _workflow_state_file(),
            {"runs_by_id": {}, "latest_run_id_by_project": {}},
        )


def _save_workflow_state(state: Dict[str, Any]) -> None:
    with _WORKFLOW_STATE_LOCK:
        _save_json_state(_workflow_state_file(), state)


def _save_workflow_run(run: Dict[str, Any]) -> None:
    run_id = str(run.get("run_id") or "").strip()
    if not run_id:
        return
    project_id = int(run.get("project_id") or 1)
    with _WORKFLOW_STATE_LOCK:
        state = _load_json_state(
            _workflow_state_file(),
            {"runs_by_id": {}, "latest_run_id_by_project": {}},
        )
        runs = state.get("runs_by_id", {})
        if not isinstance(runs, dict):
            runs = {}
        runs[run_id] = run
        if len(runs) > 100:
            run_ids = sorted(
                runs.keys(),
                key=lambda rid: str((runs.get(rid) or {}).get("started_at") or ""),
                reverse=True,
            )
            runs = {rid: runs[rid] for rid in run_ids[:100]}
        state["runs_by_id"] = runs
        latest = state.get("latest_run_id_by_project", {})
        if not isinstance(latest, dict):
            latest = {}
        latest[str(project_id)] = run_id
        state["latest_run_id_by_project"] = latest
        _save_json_state(_workflow_state_file(), state)


def _get_workflow_run(run_id: str) -> Optional[Dict[str, Any]]:
    with _WORKFLOW_STATE_LOCK:
        state = _load_json_state(
            _workflow_state_file(),
            {"runs_by_id": {}, "latest_run_id_by_project": {}},
        )
        runs = state.get("runs_by_id", {})
        if not isinstance(runs, dict):
            return None
        run = runs.get(str(run_id))
        return run if isinstance(run, dict) else None


def _list_workflow_runs(project_id: int, limit: Optional[int] = 20) -> List[Dict[str, Any]]:
    with _WORKFLOW_STATE_LOCK:
        state = _load_json_state(
            _workflow_state_file(),
            {"runs_by_id": {}, "latest_run_id_by_project": {}},
        )
        runs = state.get("runs_by_id", {})
        if not isinstance(runs, dict):
            return []
        project_key = str(project_id)
        items = [
            run
            for run in runs.values()
            if isinstance(run, dict) and str(run.get("project_id") or "") == project_key
        ]
        items.sort(key=lambda item: str(item.get("started_at") or ""), reverse=True)
        if limit is None:
            return items
        max_limit = max(int(limit or 20), 1)
        return items[:max_limit]


def _build_default_llm_config() -> Dict[str, Any]:
    client_type = os.getenv("OPENAI_CLIENT_TYPE", "maas")
    return {
        # KAG 在运行时通过 `type` 选择具体 LLM client，缺失会退化到基类并触发 NotImplementedError
        "type": client_type,
        "client_type": client_type,
        "api_key": os.getenv(
            "OPENAI_API_KEY",
            "sk-REDACTED",
        ),
        "base_url": os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        "model": os.getenv("OPENAI_MODEL", "Qwen/Qwen2.5-32B-Instruct"),
        "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
        "timeout": float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120")),
    }


def _normalize_suffix(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower().strip()


def _check_upload_suffix(filename: str) -> str:
    suffix = _normalize_suffix(filename)
    if suffix not in _ALLOWED_UPLOAD_SUFFIX:
        raise HTTPException(status_code=400, detail="仅支持 md/txt/docx/pdf 文件")
    return suffix


def _build_model_studio_builder_extension(
    *,
    split_length: int,
    semantic_split: bool,
    schema_constrained_extract: bool,
) -> Dict[str, Any]:
    llm_json = json.dumps(_build_default_llm_config(), ensure_ascii=False)
    return {
        "dataSourceConfig": {
            "structure": False,
        },
        "splitConfig": {
            "semanticSplit": bool(semantic_split),
            "splitLength": int(split_length),
        },
        "extractConfig": {
            # autoSchema=true 为 schema-free；用户要求严格按当前 schema 抽取，因此默认 false
            "autoSchema": not bool(schema_constrained_extract),
            # 某些 OpenSPG 版本在 autoWrite 缺失时会触发 NPE，显式给默认值避免提交失败
            "autoWrite": True,
            "llm": llm_json,
        },
    }


def _extract_schema_model(graph_payload: Any) -> Dict[str, Any]:
    data = _unwrap_http_result_payload(graph_payload)
    if not isinstance(data, dict):
        return {
            "entity_count": 0,
            "relation_count": 0,
            "entity_names": [],
            "relation_names": [],
        }

    entities = data.get("entityTypeDTOList")
    relations = data.get("relationTypeDTOList")
    entity_list = entities if isinstance(entities, list) else []
    relation_list = relations if isinstance(relations, list) else []

    entity_names: List[str] = []
    for item in entity_list:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("label") or "").strip()
        if name:
            entity_names.append(name)

    relation_names: List[str] = []
    for item in relation_list:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("label") or "").strip()
        if name:
            relation_names.append(name)

    return {
        "entity_count": len(entity_list),
        "relation_count": len(relation_list),
        "entity_names": entity_names,
        "relation_names": relation_names,
    }


def _extract_schema_model_from_reason_schema(reason_payload: Any) -> Dict[str, Any]:
    data = _unwrap_http_result_payload(reason_payload)
    if isinstance(data, list):
        spg_types = data
    elif isinstance(data, dict):
        raw = data.get("spgTypes")
        spg_types = raw if isinstance(raw, list) else []
    else:
        spg_types = []

    entity_names: List[str] = []
    relation_names: List[str] = []
    for item in spg_types:
        if not isinstance(item, dict):
            continue
        spg_type_enum = str(item.get("spgTypeEnum") or "").strip().upper()
        basic_info = item.get("basicInfo")
        bi = basic_info if isinstance(basic_info, dict) else {}
        raw_name = bi.get("name")
        name_obj = raw_name if isinstance(raw_name, dict) else {}
        namespace = str(name_obj.get("namespace") or "").strip()
        name_en = str(name_obj.get("nameEn") or "").strip()
        if not namespace or not name_en:
            continue
        if spg_type_enum == "ENTITY_TYPE":
            entity_names.append(name_en)
        elif spg_type_enum == "RELATION_TYPE":
            relation_names.append(name_en)

    entity_names = sorted(set(entity_names))
    relation_names = sorted(set(relation_names))
    return {
        "entity_count": len(entity_names),
        "relation_count": len(relation_names),
        "entity_names": entity_names,
        "relation_names": relation_names,
    }


def _parse_project_namespace(project_payload: Any) -> str:
    data = _unwrap_http_result_payload(project_payload)
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = [data]
    else:
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        namespace = str(row.get("namespace") or "").strip()
        if namespace:
            return namespace
    return ""


def _build_entity_type_ref(namespace: str, type_name: str, name_zh: str) -> Dict[str, Any]:
    return {
        "basicInfo": {
            "name": {
                "@type": "SPG_TYPE",
                "namespace": namespace,
                "nameEn": type_name,
                "identityType": "SPG_TYPE",
            },
            "nameZh": name_zh,
            "desc": "",
        },
        "spgTypeEnum": "ENTITY_TYPE",
    }


def _build_text_type_ref() -> Dict[str, Any]:
    return {
        "basicInfo": {
            "name": {
                "@type": "SPG_TYPE",
                "nameEn": "Text",
                "identityType": "SPG_TYPE",
            },
            "nameZh": "文本",
            "desc": "文本",
        },
        "spgTypeEnum": "BASIC_TYPE",
    }


def _map_index_type(index_type: str) -> str:
    text = str(index_type or "").strip().lower()
    if text in {"textandvector", "text_and_vector", "text-and-vector"}:
        return "TEXT_AND_VECTOR"
    if text in {"text"}:
        return "TEXT"
    return ""


def _build_property_draft(
    *,
    namespace: str,
    entity_name: str,
    entity_name_zh: str,
    prop_name: str,
    prop_name_zh: str,
    dsl_type: str,
    index_type: str,
) -> Optional[Dict[str, Any]]:
    if dsl_type not in {"Text", "STD.Text"}:
        return None

    mapped_index = _map_index_type(index_type)
    advanced_config: Dict[str, Any] = {
        "encryptTypeEnum": "NONE",
        "withIndex": bool(mapped_index),
        "subProperties": [],
        "semantics": [],
    }
    if mapped_index:
        advanced_config["indexType"] = mapped_index

    return {
        "subjectTypeRef": _build_entity_type_ref(namespace, entity_name, entity_name_zh),
        "basicInfo": {
            "name": {"@type": "PREDICATE", "name": prop_name, "identityType": "PREDICATE"},
            "nameZh": prop_name_zh,
        },
        "objectTypeRef": _build_text_type_ref(),
        "inherited": False,
        "advancedConfig": advanced_config,
        "extInfo": {},
        "alterOperation": "CREATE",
    }


def _parse_schema_dsl_to_public_draft(
    *,
    schema_script: str,
    project_namespace: str,
) -> Dict[str, Any]:
    lines = [line.rstrip("\n") for line in str(schema_script or "").splitlines()]
    alter_spg_types: List[Dict[str, Any]] = []
    i = 0
    entity_header_pattern = re.compile(
        r"^([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*:\s*EntityType\s*$"
    )
    prop_pattern = re.compile(
        r"^([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*:\s*([A-Za-z_][A-Za-z0-9_.]*)\s*$"
    )
    index_pattern = re.compile(r"^index\s*:\s*([A-Za-z_][A-Za-z0-9_-]*)\s*$", re.IGNORECASE)
    skip_builtin_props = {"id", "name", "description"}

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        i += 1
        if not stripped:
            continue
        entity_match = entity_header_pattern.match(stripped)
        if not entity_match:
            continue

        entity_name = entity_match.group(1).strip()
        entity_name_zh = entity_match.group(2).strip() or entity_name
        entity_indent = len(line) - len(line.lstrip(" \t"))
        properties: List[Dict[str, Any]] = []

        while i < len(lines):
            raw = lines[i]
            text = raw.strip()
            indent = len(raw) - len(raw.lstrip(" \t"))
            if not text:
                i += 1
                continue
            if indent <= entity_indent and entity_header_pattern.match(text):
                break
            if indent <= entity_indent and text.lower().startswith("namespace "):
                break
            if text.lower().startswith("properties:"):
                i += 1
                continue

            prop_match = prop_pattern.match(text)
            if prop_match:
                prop_name = prop_match.group(1).strip()
                prop_name_zh = prop_match.group(2).strip() or prop_name
                dsl_type = prop_match.group(3).strip()
                i += 1
                index_type = ""
                while i < len(lines):
                    sub_raw = lines[i]
                    sub_text = sub_raw.strip()
                    sub_indent = len(sub_raw) - len(sub_raw.lstrip(" \t"))
                    if not sub_text:
                        i += 1
                        continue
                    if sub_indent <= indent:
                        break
                    idx_match = index_pattern.match(sub_text)
                    if idx_match:
                        index_type = idx_match.group(1).strip()
                    i += 1

                if prop_name.lower() in skip_builtin_props:
                    continue
                prop_draft = _build_property_draft(
                    namespace=project_namespace,
                    entity_name=entity_name,
                    entity_name_zh=entity_name_zh,
                    prop_name=prop_name,
                    prop_name_zh=prop_name_zh,
                    dsl_type=dsl_type,
                    index_type=index_type,
                )
                if prop_draft is not None:
                    properties.append(prop_draft)
                continue

            i += 1

        entity_draft = {
            "@type": "ENTITY_TYPE",
            "basicInfo": {
                "name": {
                    "@type": "SPG_TYPE",
                    "namespace": project_namespace,
                    "nameEn": entity_name,
                    "identityType": "SPG_TYPE",
                },
                "nameZh": entity_name_zh,
                "desc": "",
            },
            "parentTypeInfo": {
                "parentTypeIdentifier": {
                    "@type": "SPG_TYPE",
                    "nameEn": "Thing",
                    "identityType": "SPG_TYPE",
                },
                "inheritPath": [],
            },
            "spgTypeEnum": "ENTITY_TYPE",
            "properties": properties,
            "relations": [],
            "advancedConfig": {},
            "extInfo": {},
            "alterOperation": "CREATE",
        }
        alter_spg_types.append(entity_draft)

    if not alter_spg_types:
        raise ValueError("当前仅支持基于 EntityType 的 DSL，未识别到可提交的实体类型定义")
    return {"alterSpgTypes": alter_spg_types}


def _extract_result_entities(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        label = str(node.get("label") or "").strip()
        properties = node.get("properties")
        prop = properties if isinstance(properties, dict) else {}
        name = str(prop.get("name") or prop.get("title") or node.get("id") or "").strip()
        if not name:
            continue
        entities.append(
            {
                "id": str(node.get("id") or f"entity-{idx + 1}"),
                "name": name,
                "label": label or "Unknown",
                "snippet": str(prop.get("content") or prop.get("description") or "").strip(),
                "properties": prop,
            }
        )
    return entities


def _as_json_obj(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _parse_llm_trace_from_instances(instances: List[Dict[str, Any]]) -> Dict[str, Any]:
    for instance in instances:
        ext = _as_json_obj(instance.get("extension"))
        if not ext:
            continue
        raw_info = ext.get("llmTokenInfo")
        info = _as_json_obj(raw_info)
        if not info:
            continue

        raw_prompts = info.get("prompts")
        prompts = raw_prompts if isinstance(raw_prompts, list) else []
        prompt_items: List[Dict[str, Any]] = []
        for idx, item in enumerate(prompts):
            if not isinstance(item, dict):
                continue
            prompt_text = str(item.get("prompt") or "").strip()
            if not prompt_text and item.get("messages") is not None:
                try:
                    prompt_text = json.dumps(item.get("messages"), ensure_ascii=False)
                except Exception:
                    prompt_text = str(item.get("messages"))
            prompt_items.append(
                {
                    "index": idx + 1,
                    "model": str(item.get("model") or "").strip(),
                    "api_base": str(item.get("api_base") or "").strip(),
                    "prompt_name": str(item.get("prompt_name") or "").strip(),
                    "prompt": prompt_text,
                    "timestamp": item.get("timestamp"),
                }
            )

        latest = prompt_items[-1] if prompt_items else {}
        return {
            "invoke_mode": "openspg_kag_runtime",
            "model": latest.get("model") or info.get("model") or "",
            "api_base": latest.get("api_base") or info.get("api_base") or "",
            "prompt": latest.get("prompt") or "",
            "prompt_name": latest.get("prompt_name") or "",
            "prompts": prompt_items,
            "prompt_tokens": info.get("prompt_tokens"),
            "completion_tokens": info.get("completion_tokens"),
            "total_tokens": info.get("total_tokens"),
        }
    return {}


async def _submit_model_studio_file_job(
    *,
    project_id: int,
    filename: str,
    content: bytes,
    content_type: str,
    worker_num: int,
    job_name: Optional[str],
    split_length: int,
    semantic_split: bool,
    schema_constrained_extract: bool,
) -> Dict[str, Any]:
    suffix = _check_upload_suffix(filename)
    upload_result = await upload_openspg_reasoner_file(
        filename=filename,
        content=content,
        content_type=content_type or _CONTENT_TYPE_BY_SUFFIX.get(suffix, "application/octet-stream"),
        file_type=suffix,
    )
    if not _is_live_success(upload_result):
        raise HTTPException(
            status_code=502,
            detail=f"OpenSPG 文件上传失败: mode={upload_result.get('mode')} status={upload_result.get('http_status')}",
        )
    upload_response = upload_result.get("response")
    upload_payload = _unwrap_http_result_payload(upload_response)
    file_url = _extract_uploaded_file_url(upload_payload) or _extract_uploaded_file_url(upload_response)
    if not file_url:
        raise HTTPException(
            status_code=502,
            detail=(
                "OpenSPG 上传成功但未返回可用 fileUrl，"
                f"response={json.dumps(upload_response, ensure_ascii=False)[:800]}"
            ),
        )

    resolved_job_name = job_name or f"model_studio_extract_{time.strftime('%Y%m%d%H%M%S', time.localtime())}"
    extension = _build_model_studio_builder_extension(
        split_length=split_length,
        semantic_split=semantic_split,
        schema_constrained_extract=schema_constrained_extract,
    )
    builder_submit_result = await submit_openspg_builder_legacy_job(
        project_id=project_id,
        job_name=resolved_job_name,
        file_url=file_url,
        extension=extension,
        worker_num=worker_num,
        data_source_type="FILE",
        builder_type="KAG",
        retrievals="[]",
    )
    if not _is_live_success(builder_submit_result):
        raise HTTPException(
            status_code=502,
            detail=(
                "OpenSPG Builder 任务提交失败: "
                f"{_live_error_message(builder_submit_result)}"
            ),
        )
    job_payload = _unwrap_http_result_payload(builder_submit_result.get("response"))
    job = job_payload if isinstance(job_payload, dict) else {}

    return {
        "project_id": project_id,
        "job_name": resolved_job_name,
        "file_name": filename,
        "file_suffix": suffix,
        "file_url": file_url,
        "upload_result": upload_result,
        "builder_extension": extension,
        "builder_submit_result": builder_submit_result,
        "job": job,
    }


@router.get("/headlines")
def get_headlines(
    hours: int = Query(24, ge=1, le=168),
    top_n: int = Query(20, ge=1, le=100),
    allow_demo_fallback: Optional[bool] = Query(None),
):
    rows, data_source = _read_news_rows(
        limit=max(top_n * 10, 100),
        allow_demo_fallback=_allow_demo_fallback(allow_demo_fallback),
    )
    data = build_headlines_from_news(rows, top_n=top_n, hours=hours)
    data["meta"] = {
        "data_source": data_source,
        "top_n": top_n,
        "hours": hours,
        "allow_demo_fallback": _allow_demo_fallback(allow_demo_fallback),
    }
    return data


@router.get("/headlines/{event_id}")
def get_headline_detail(
    event_id: str,
    hours: int = Query(24, ge=1, le=168),
    allow_demo_fallback: Optional[bool] = Query(None),
):
    rows, data_source = _read_news_rows(
        limit=500,
        allow_demo_fallback=_allow_demo_fallback(allow_demo_fallback),
    )
    event = get_event_detail_from_news(rows, event_id=event_id, hours=hours)
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在或不在时间窗口内")
    companies = event.get("companies") or []
    event["meta"] = {
        "data_source": data_source,
        "window_hours": hours,
        "allow_demo_fallback": _allow_demo_fallback(allow_demo_fallback),
    }
    event["openspg_query_hints"] = {
        "graph_all_labels": {"path": "/public/v1/graph/allLabels", "params": {"projectId": 1}},
        "search_custom": {
            "path": "/public/v1/search/custom",
            "body": {"projectId": 1, "customQuery": "MATCH (n) RETURN n LIMIT 5"},
        },
        "schema_reason": {"path": "/public/v1/reason/schema", "params": {"projectId": 1}},
        "entity_keywords": companies[:3],
    }
    return event


@router.get("/bridge/batch-preview")
def get_bridge_batch_preview(
    limit: int = Query(100, ge=1, le=1000),
    sample_lines: int = Query(5, ge=1, le=50),
    allow_demo_fallback: Optional[bool] = Query(None),
):
    rows, data_source = _read_news_rows(
        limit=limit,
        allow_demo_fallback=_allow_demo_fallback(allow_demo_fallback),
    )
    normalized_records = [normalize_news_record(row) for row in rows]
    jsonl_lines = export_news_batch_to_jsonl_lines(rows)

    source_counter: Dict[str, int] = {}
    for record in normalized_records:
        source_name = str(record.get("source_name") or "unknown")
        source_counter[source_name] = source_counter.get(source_name, 0) + 1

    source_distribution = [
        {"source_name": source_name, "count": count}
        for source_name, count in sorted(source_counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    return {
        "meta": {
            "data_source": data_source,
            "limit": limit,
            "row_count": len(rows),
            "jsonl_line_count": len(jsonl_lines),
            "sample_lines": sample_lines,
            "export_path": "/api/v1/openspg-demo/bridge/export.jsonl",
        },
        "stats": {
            "unique_sources": len(source_counter),
            "source_distribution": source_distribution,
        },
        "sample_records": normalized_records[:sample_lines],
        "jsonl_preview": jsonl_lines[:sample_lines],
    }


@router.get("/bridge/export.jsonl")
def export_bridge_batch_jsonl(
    limit: int = Query(200, ge=1, le=5000),
    allow_demo_fallback: Optional[bool] = Query(None),
):
    rows, _ = _read_news_rows(
        limit=limit,
        allow_demo_fallback=_allow_demo_fallback(allow_demo_fallback),
    )
    lines = export_news_batch_to_jsonl_lines(rows)
    payload = "\n".join(lines) + ("\n" if lines else "")
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    filename = f"openspg-news-batch-{timestamp}.jsonl"
    return Response(
        content=payload,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/bridge/status")
def get_bridge_status(allow_demo_fallback: Optional[bool] = Query(None)):
    rows, data_source = _read_news_rows(
        limit=1,
        allow_demo_fallback=_allow_demo_fallback(allow_demo_fallback),
    )
    status = _bridge_runner().get_status()
    status["meta"] = {
        "data_source": data_source,
        "run_endpoint": "/api/v1/openspg-demo/bridge/run",
    }
    return status


@router.get("/bridge/runs/{run_id}/download")
def download_bridge_run_file(run_id: str):
    runner = _bridge_runner()
    batch_file = runner.batches_dir / f"{run_id}.jsonl"
    if not batch_file.exists():
        raise HTTPException(status_code=404, detail="批次文件不存在")
    payload = batch_file.read_text(encoding="utf-8")
    return Response(
        content=payload,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{batch_file.name}"'},
    )


@router.post("/bridge/run")
async def run_bridge_batch(request: BridgeRunRequest):
    runtime_profile = normalize_runtime_profile(request.runtime_profile)
    # 读取更多样本让增量过滤有足够候选空间
    rows, data_source = _read_news_rows(
        limit=max(request.limit * 10, 500),
        allow_demo_fallback=False,
    )
    runner = _bridge_runner()
    run_result = runner.run_export(rows, limit=request.limit, force_full=request.force_full)
    run_result["data_source"] = data_source
    run_result["runtime_profile"] = runtime_profile
    run_result["batch_download_url"] = (
        f"/api/v1/openspg-demo/bridge/runs/{run_result['run_id']}/download"
    )

    active_profile = _get_active_model_profile(request.project_id) if request.use_active_model else None
    run_result["active_model_profile"] = active_profile

    if request.apply_schema:
        selected_schema_script = (
            str(request.schema_script or "").strip()
            or (active_profile or {}).get("schema_script")
            or get_my_news_demo_schema_script()
        )
        run_result["schema_apply_result"] = await _apply_schema_with_public_fallback(
            project_id=request.project_id,
            schema_script=selected_schema_script,
        )
        run_result["schema_source"] = (
            "request.schema_script"
            if str(request.schema_script or "").strip()
            else "active_model_profile"
            if active_profile
            else "default_my_news_demo"
        )
    else:
        run_result["schema_apply_result"] = {
            "mode": "skip",
            "reason": "apply_schema=false",
        }

    schema_ok = (not request.apply_schema) or _is_live_success(run_result["schema_apply_result"])

    builder_submit_enabled = _builder_submit_enabled()
    if request.submit_builder and not schema_ok:
        run_result["builder_submit_result"] = {
            "mode": "skip",
            "reason": "schema apply failed or OpenSPG unreachable",
            "schema_apply_result": run_result["schema_apply_result"],
        }
    elif request.submit_builder and not builder_submit_enabled:
        run_result["builder_submit_result"] = {
            "mode": "skip",
            "reason": "builder submit disabled by OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT",
            "hint": _builder_submit_hint(),
        }
    elif request.submit_builder and run_result.get("export_count", 0) > 0:
        builder_envs = build_builder_envs_for_run(run_result, project_id=request.project_id)
        default_command = (
            request.builder_command
            or os.getenv("OPENSPG_DEMO_BUILDER_COMMAND")
            or build_real_import_command()
        )
        run_result["builder_submit_result"] = await submit_openspg_builder_job(
            project_id=request.project_id,
            command=default_command,
            worker_num=request.worker_num,
            envs=builder_envs,
        )
    else:
        run_result["builder_submit_result"] = {
            "mode": "skip",
            "reason": "submit_builder=false or export_count=0",
        }

    if request.materialize_graph:
        run_result["graph_materialize_result"] = await _materialize_graph_for_bridge_run(
            bridge_run=run_result,
            project_id=request.project_id,
        )
    else:
        run_result["graph_materialize_result"] = {
            "status": "skip",
            "reason": "materialize_graph=false",
        }

    status = runner.get_status()
    run_result["bridge_status"] = {
        "cursor": status.get("cursor"),
        "last_run": status.get("last_run"),
    }
    return run_result


@router.get("/engine/snapshot")
async def get_engine_snapshot(project_id: int = Query(1, ge=1)):
    schema_template = get_robot_chain_mvp_schema_template()
    schema_script = get_my_news_demo_schema_script()
    builder_template = get_robot_chain_mvp_builder_template()
    live = await get_openspg_capability_snapshot(project_id=project_id)

    return {
        "schema": {
            "template": schema_template,
            "my_news_demo_script": schema_script,
            "live_query": live["schema_live"],
        },
        "builder": {
            "template": builder_template,
            "live_query": live["builder_live"],
        },
        "reason": live["reason"],
        "search": live["search"],
        "graph": live["graph"],
        "meta": live["meta"],
    }


@router.get("/engine/health")
async def get_engine_health(project_id: int = Query(1, ge=1)):
    health = await get_openspg_health(project_id=project_id)
    health["builder_submit_enabled"] = _builder_submit_enabled()
    health["builder_submit_hint"] = _builder_submit_hint()
    return health


@router.post("/engine/builder/submit")
async def submit_engine_builder_job(request: BuilderSubmitRequest):
    return await submit_openspg_builder_job(
        project_id=request.project_id,
        command=request.command,
        worker_num=request.worker_num,
        user_number=request.user_number,
        image=request.image,
        worker_pool=request.worker_pool,
        envs=request.envs,
    )


@router.post("/ingest/rss")
def ingest_real_rss(request: RSSPullRequest):
    return pull_rss_articles_to_mongo(
        max_entries_per_feed=request.max_entries_per_feed,
        hours_ago=request.hours_ago,
    )


async def _execute_workflow_job(
    run_id: str,
    request_payload: Dict[str, Any],
    active_model_profile: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    request = WorkflowNewsRunRequest(**request_payload)
    runtime_profile = normalize_runtime_profile(request.runtime_profile)
    run_payload = _get_workflow_run(run_id) or _workflow_fallback_run_payload(
        run_id,
        request_payload,
        active_model_profile,
    )
    run_payload["status"] = "running"
    run_payload["request"] = request.model_dump()
    run_payload["active_model_profile"] = active_model_profile
    run_payload["runtime_profile"] = runtime_profile
    run_payload.setdefault("step_statuses", _initial_step_statuses())
    _save_updated_workflow_run(run_payload)

    try:
        if runtime_profile == "kag_openspg" and request.apply_schema:
            _set_step_status(run_payload, "model", "running")
            _save_updated_workflow_run(run_payload)
            schema_runtime_result = await apply_openks_news_kg_schema(
                project_id=request.project_id,
                activate_label="workflow-step",
            )
            schema_apply_result = dict(schema_runtime_result.get("schema_apply_result") or {})
            run_payload["schema_source"] = schema_runtime_result.get("schema_source") or "openks_module"
            run_payload["compiled_schema_script"] = schema_runtime_result.get("compiled_schema_script")
            run_payload["kag_schema_export"] = schema_runtime_result.get("kag_schema_export")
            run_payload["schema_commit_result"] = schema_runtime_result.get("schema_commit_result")
            run_payload["schema_apply_result"] = schema_apply_result
            run_payload["activate_result"] = schema_runtime_result.get("activate_result")
            run_payload["active_model_profile"] = schema_runtime_result.get("active_model_profile") or active_model_profile
            if _result_effective_success(schema_apply_result):
                _set_step_status(
                    run_payload,
                    "model",
                    "success",
                    mode=(run_payload.get("schema_commit_result") or {}).get("mode") or schema_apply_result.get("mode"),
                    http_status=(run_payload.get("schema_commit_result") or {}).get("http_status") or schema_apply_result.get("http_status"),
                )
            else:
                _set_step_status(
                    run_payload,
                    "model",
                    "failed",
                    error=_result_effective_error(schema_apply_result),
                    mode=schema_apply_result.get("mode"),
                    http_status=schema_apply_result.get("http_status"),
                )
        else:
            schema_apply_result = {
                "mode": "skip",
                "reason": "runtime_profile=openks_direct" if runtime_profile == "openks_direct" else "apply_schema=false",
                "meta": {"effective_success": True, "action": "schema_apply"},
            }
            run_payload["schema_apply_result"] = schema_apply_result
            _set_step_status(
                run_payload,
                "model",
                "skipped",
                reason="runtime_profile=openks_direct" if runtime_profile == "openks_direct" else "apply_schema=false",
            )
        _save_updated_workflow_run(run_payload)

        _set_step_status(run_payload, "collect", "running")
        _save_updated_workflow_run(run_payload)
        ingest_result = pull_rss_articles_to_mongo(
            max_entries_per_feed=request.max_entries_per_feed,
            hours_ago=request.hours_ago,
        )
        run_payload["ingest_result"] = ingest_result
        _set_step_status(
            run_payload,
            "collect",
            "success",
            inserted_count=ingest_result.get("inserted_count"),
            duplicate_count=ingest_result.get("duplicate_count"),
            pull_mode=ingest_result.get("pull_mode"),
        )
        _save_updated_workflow_run(run_payload)

        _set_step_status(run_payload, "process", "running")
        _save_updated_workflow_run(run_payload)
        rows, data_source = _read_news_rows(
            limit=max(request.bridge_limit * 10, 500),
            allow_demo_fallback=request.allow_demo_fallback,
        )
        run_payload["process_preview"] = {
            "data_source": data_source,
            "row_count": len(rows),
        }
        _set_step_status(
            run_payload,
            "process",
            "success",
            data_source=data_source,
            row_count=len(rows),
        )
        _save_updated_workflow_run(run_payload)

        _set_step_status(run_payload, "extract", "running")
        _save_updated_workflow_run(run_payload)
        bridge_runner = _bridge_runner()
        bridge_run: Dict[str, Any] = {}
        if runtime_profile == "openks_direct":
            openks_extract_preview = list_pending_openks_queue_preview(limit=request.bridge_limit)
            run_payload["openks_extract_preview"] = openks_extract_preview
            _set_step_status(
                run_payload,
                "extract",
                "success",
                pending_count=openks_extract_preview.get("pending_count") or 0,
            )
        else:
            bridge_run = bridge_runner.run_export(
                rows,
                limit=request.bridge_limit,
                force_full=request.force_full,
            )
            bridge_run["data_source"] = data_source
            bridge_run["runtime_profile"] = runtime_profile
            bridge_run["batch_download_url"] = (
                f"/api/v1/openspg-demo/bridge/runs/{bridge_run['run_id']}/download"
            )
            run_payload["bridge_run"] = bridge_run
            _set_step_status(
                run_payload,
                "extract",
                "success",
                export_count=bridge_run.get("export_count"),
                run_id=bridge_run.get("run_id"),
            )
        _save_updated_workflow_run(run_payload)

        builder_submit_enabled = _builder_submit_enabled()
        schema_ok = runtime_profile != "kag_openspg" or _result_effective_success(schema_apply_result)
        builder_submit_result: Dict[str, Any]
        graph_materialize_result: Dict[str, Any] = {
            "status": "skip",
            "reason": "runtime not executed",
        }
        if runtime_profile == "openks_direct":
            _set_step_status(run_payload, "execute", "running")
            _save_updated_workflow_run(run_payload)
            openks_build_result = build_news_kg(limit=request.bridge_limit)
            builder_submit_result = {
                "mode": "openks_direct",
                "http_status": 200,
                "response": {"success": True, "result": openks_build_result},
                "meta": {"effective_success": True, "action": "builder_submit"},
            }
            graph_materialize_result = {
                "status": "skip",
                "reason": "runtime_profile=openks_direct",
            }
            run_payload["openks_build_result"] = openks_build_result
            run_payload["runtime_binding"] = get_runtime_binding_summary(
                kg_name="news_kg",
                runtime_profile=runtime_profile,
            )
            _set_step_status(
                run_payload,
                "execute",
                "success",
                mode=builder_submit_result.get("mode"),
                processed=openks_build_result.get("processed"),
                artifact_id=openks_build_result.get("artifact_id"),
            )
        elif not request.submit_builder:
            builder_submit_result = {
                "mode": "skip",
                "reason": "submit_builder=false",
                "meta": {"effective_success": True, "action": "builder_submit"},
            }
            _set_step_status(run_payload, "execute", "skipped", reason="submit_builder=false")
        elif not schema_ok:
            builder_submit_result = {
                "mode": "skip",
                "reason": "schema apply failed or OpenSPG unreachable",
                "schema_apply_result": schema_apply_result,
                "meta": {"effective_success": False, "action": "builder_submit"},
            }
            _set_step_status(
                run_payload,
                "execute",
                "failed",
                error="schema apply failed or OpenSPG unreachable",
            )
        elif not builder_submit_enabled:
            builder_submit_result = {
                "mode": "skip",
                "reason": "builder submit disabled by OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT",
                "hint": _builder_submit_hint(),
                "meta": {"effective_success": False, "action": "builder_submit"},
            }
            _set_step_status(
                run_payload,
                "execute",
                "skipped",
                reason="builder submit disabled by OPENSPG_DEMO_ENABLE_BUILDER_SUBMIT",
            )
        elif bridge_run.get("export_count", 0) <= 0:
            builder_submit_result = {
                "mode": "skip",
                "reason": "export_count=0",
                "meta": {"effective_success": False, "action": "builder_submit"},
            }
            _set_step_status(run_payload, "execute", "skipped", reason="export_count=0")
        else:
            _set_step_status(run_payload, "execute", "running")
            _save_updated_workflow_run(run_payload)
            builder_envs = build_builder_envs_for_run(bridge_run, project_id=request.project_id)
            default_command = (
                request.builder_command
                or os.getenv("OPENSPG_DEMO_BUILDER_COMMAND")
                or build_real_import_command()
            )
            builder_submit_result = _annotate_openspg_result(
                await submit_openspg_builder_job(
                    project_id=request.project_id,
                    command=default_command,
                    worker_num=request.worker_num,
                    envs=builder_envs,
                ),
                action="builder_submit",
            )
            if _result_effective_success(builder_submit_result):
                _set_step_status(
                    run_payload,
                    "execute",
                    "success",
                    mode=builder_submit_result.get("mode"),
                    http_status=builder_submit_result.get("http_status"),
                )
            else:
                _set_step_status(
                    run_payload,
                    "execute",
                    "failed",
                    error=_result_effective_error(builder_submit_result),
                    mode=builder_submit_result.get("mode"),
                    http_status=builder_submit_result.get("http_status"),
                )
            if request.materialize_graph:
                graph_materialize_result = await _materialize_graph_for_bridge_run(
                    bridge_run=bridge_run,
                    project_id=request.project_id,
                )
            else:
                graph_materialize_result = {
                    "status": "skip",
                    "reason": "materialize_graph=false",
                }
            if request.materialize_graph:
                if str(graph_materialize_result.get("status") or "").strip().lower() == "success":
                    run_payload["runtime_binding"] = register_workflow_runtime_binding(
                        runtime_profile=runtime_profile,
                        kg_name="news_kg",
                        project_id=request.project_id,
                        workflow_run_id=run_id,
                        bridge_run=bridge_run,
                        builder_submit_result=builder_submit_result,
                        graph_materialize_result=graph_materialize_result,
                    )
                    execute_status = run_payload.get("step_statuses", {}).get("execute") or {}
                    if isinstance(execute_status, dict) and execute_status.get("status") in {"success", "running"}:
                        _set_step_status(
                            run_payload,
                            "execute",
                            "success",
                            mode=builder_submit_result.get("mode"),
                            http_status=builder_submit_result.get("http_status"),
                            graph_vertices=graph_materialize_result.get("vertices"),
                            graph_edges=graph_materialize_result.get("edges"),
                        )
                elif str(graph_materialize_result.get("status") or "").strip().lower() == "failed":
                    _set_step_status(
                        run_payload,
                        "execute",
                        "failed",
                        error=graph_materialize_result.get("error") or "graph materialize failed",
                        mode=builder_submit_result.get("mode"),
                        http_status=builder_submit_result.get("http_status"),
                    )
        run_payload["builder_submit_result"] = builder_submit_result
        run_payload["graph_materialize_result"] = graph_materialize_result
        _save_updated_workflow_run(run_payload)

        _set_step_status(run_payload, "apply", "running")
        _save_updated_workflow_run(run_payload)
        bridge_status = bridge_runner.get_status()
        headlines_result = build_headlines_from_news(
            rows,
            top_n=request.headlines_top_n,
            hours=request.hours_ago,
        )
        run_payload["bridge_status"] = {
            "cursor": bridge_status.get("cursor"),
            "last_run": bridge_status.get("last_run"),
        }
        run_payload["headlines_snapshot"] = {
            "stats": headlines_result.get("stats") or {},
            "top_headline_ids": [
                item.get("event_id") for item in (headlines_result.get("headlines") or [])[:5]
            ],
        }
        _set_step_status(
            run_payload,
            "apply",
            "success",
            headline_count=len(headlines_result.get("headlines") or []),
        )

        final_status, warnings = _compute_workflow_final_status(
            request=request,
            step_statuses=run_payload.get("step_statuses") or {},
            schema_apply_result=schema_apply_result,
            builder_submit_result=builder_submit_result,
            graph_materialize_result=graph_materialize_result,
        )
        run_payload["status"] = final_status
        run_payload["warnings"] = warnings
        run_payload["status_reason"] = warnings[0] if warnings else ""
        run_payload["finished_at"] = _utc_now_iso()
        _save_updated_workflow_run(run_payload)
        return run_payload
    except Exception as exc:
        run_payload = _get_workflow_run(run_id) or run_payload
        run_payload["status"] = "failed"
        run_payload["error"] = str(exc)
        run_payload["finished_at"] = _utc_now_iso()
        _save_updated_workflow_run(run_payload)
        return run_payload


def _run_workflow_job_thread(
    run_id: str,
    request_payload: Dict[str, Any],
    active_model_profile: Optional[Dict[str, Any]],
) -> None:
    asyncio.run(_execute_workflow_job(run_id, request_payload, active_model_profile))


def _start_workflow_job(
    run_id: str,
    request_payload: Dict[str, Any],
    active_model_profile: Optional[Dict[str, Any]],
) -> None:
    worker = threading.Thread(
        target=_run_workflow_job_thread,
        args=(run_id, request_payload, active_model_profile),
        daemon=True,
        name=f"workflow-job-{run_id}",
    )
    worker.start()


@router.post("/workflow/news/run")
async def run_news_workflow(request: WorkflowNewsRunRequest):
    runtime_profile = normalize_runtime_profile(request.runtime_profile)
    active_model_profile = _get_active_model_profile(request.project_id) if runtime_profile == "kag_openspg" else None
    if runtime_profile == "kag_openspg" and isinstance(active_model_profile, dict):
        if str(active_model_profile.get("source") or "").strip() != "openks_module":
            active_model_profile = None

    run_id = f"wf_{int(time.time())}_{secrets.token_hex(4)}"
    run_payload: Dict[str, Any] = {
        "run_id": run_id,
        "project_id": request.project_id,
        "runtime_profile": runtime_profile,
        "status": "queued",
        "started_at": _utc_now_iso(),
        "active_model_profile": active_model_profile,
        "request": request.model_dump(),
        "step_statuses": _initial_step_statuses(),
        "poll_url": f"/api/v1/openspg-demo/workflow/news/runs/{run_id}",
        "history_url": f"/api/v1/openspg-demo/workflow/news/history?project_id={request.project_id}",
    }
    _save_updated_workflow_run(run_payload)
    _start_workflow_job(run_id, request.model_dump(), active_model_profile)
    return JSONResponse(status_code=202, content=run_payload)


@router.get("/workflow/news/runs/{run_id}")
def get_news_workflow_run(run_id: str):
    run = _get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="workflow run 不存在")
    return run


@router.post("/workflow/news/runs/{run_id}/materialize")
async def materialize_news_workflow_run(run_id: str):
    run = _get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="workflow run 不存在")
    project_id = int(run.get("project_id") or 1)
    bridge_run = run.get("bridge_run") if isinstance(run.get("bridge_run"), dict) else {}
    result = await _materialize_graph_for_bridge_run(
        bridge_run=bridge_run,
        project_id=project_id,
    )
    run["graph_materialize_result"] = result
    _save_updated_workflow_run(run)
    return {
        "run_id": run_id,
        "project_id": project_id,
        "graph_materialize_result": result,
    }


@router.get("/workflow/news/runs/{run_id}/steps/{step_key}")
def get_news_workflow_step_detail(run_id: str, step_key: str):
    run = _get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="workflow run 不存在")
    return _build_news_workflow_step_detail(run, step_key)


@router.get("/workflow/news/latest")
def get_latest_news_workflow_run(project_id: int = Query(1, ge=1)):
    state = _load_workflow_state()
    latest = state.get("latest_run_id_by_project", {})
    if not isinstance(latest, dict):
        latest = {}
    run_id = str(latest.get(str(project_id)) or "").strip()
    if not run_id:
        raise HTTPException(status_code=404, detail="当前项目暂无 workflow 记录")
    run = _get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="workflow run 不存在")
    return run


@router.get("/workflow/news/history")
def get_news_workflow_history(
    project_id: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    runs = _list_workflow_runs(project_id=project_id, limit=limit)
    total = len(_list_workflow_runs(project_id=project_id, limit=None))
    return {
        "project_id": project_id,
        "limit": limit,
        "total": total,
        "runs": runs,
    }


@router.get("/model-studio/schema/active")
def get_model_studio_active_schema(project_id: int = Query(1, ge=1)):
    active = _get_active_model_profile(project_id)
    if not active:
        raise HTTPException(status_code=404, detail="当前项目尚未激活模型")
    return active


@router.post("/model-studio/schema/activate")
def activate_model_studio_schema(request: ModelStudioSchemaActivateRequest):
    script = str(request.schema_script or "").strip()
    if not script:
        script = str(_MODEL_STUDIO_SCHEMA_SCRIPT_CACHE.get(request.project_id) or "").strip()
    if not script:
        raise HTTPException(status_code=400, detail="schema_script 为空，且本地缓存不存在")
    try:
        profile = _activate_model_profile(
            project_id=request.project_id,
            schema_script=script,
            label=(request.label or "manual-activate").strip(),
            source="model_studio_manual",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return profile


@router.get("/model-studio/schema/template")
def get_model_studio_schema_template():
    template = textwrap.dedent(
        """
        namespace CompanyModelStudio

        Company(企业): EntityType
        	properties:
        		name(企业名称): Text
        			index: TextAndVector
        		description(企业描述): Text
        """
    ).strip()
    return {"schema_script": template}


@router.get("/model-studio/schema/current")
async def get_model_studio_schema_current(project_id: int = Query(1, ge=1)):
    timeout_seconds = float(os.getenv("OPENSPG_SCHEMA_CURRENT_TIMEOUT_SECONDS") or "6")
    raw_results = await asyncio.gather(
        asyncio.wait_for(get_openspg_schema_script(project_id=project_id), timeout=timeout_seconds),
        asyncio.wait_for(get_openspg_schema_graph(project_id=project_id), timeout=timeout_seconds),
        asyncio.wait_for(get_openspg_reason_schema(project_id=project_id), timeout=timeout_seconds),
        return_exceptions=True,
    )
    schema_script_result, schema_graph_result, reason_schema_result = [
        item
        if isinstance(item, dict)
        else _mock_result_for_exception(
            action="schema_current",
            message=str(item),
        )
        for item in raw_results
    ]
    script_payload = _unwrap_http_result_payload(schema_script_result.get("response"))
    schema_model = _extract_schema_model(schema_graph_result.get("response"))
    if int(schema_model.get("entity_count") or 0) <= 0:
        schema_model = _extract_schema_model_from_reason_schema(reason_schema_result.get("response"))
    cached_script = _MODEL_STUDIO_SCHEMA_SCRIPT_CACHE.get(project_id, "")
    active_profile = _get_active_model_profile(project_id)
    fallback_script = cached_script or str((active_profile or {}).get("schema_script") or "").strip()
    if isinstance(script_payload, str) and script_payload.strip():
        current_script = script_payload
        fallback_mode = "live"
    else:
        current_script = fallback_script
        fallback_mode = "cached_model_profile" if active_profile else "local_cache" if fallback_script else "empty"
    return {
        "project_id": project_id,
        "schema_script_result": schema_script_result,
        "schema_graph_result": schema_graph_result,
        "reason_schema_result": reason_schema_result,
        "schema_model": schema_model,
        "schema_script": current_script,
        "meta": {
            "fallback_mode": fallback_mode,
            "timeout_seconds": timeout_seconds,
        },
    }


@router.post("/model-studio/schema/apply")
async def apply_model_studio_schema(request: ModelStudioSchemaApplyRequest):
    schema_apply_result = await apply_openspg_schema_script(
        project_id=request.project_id,
        schema_script=request.schema_script,
    )
    if not _is_live_success(schema_apply_result):
        project_result = await get_openspg_project(project_id=request.project_id)
        project_namespace = _parse_project_namespace(project_result.get("response")) or "zhilian"
        try:
            schema_draft = _parse_schema_dsl_to_public_draft(
                schema_script=request.schema_script,
                project_namespace=project_namespace,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Schema 提交失败: "
                    f"{_live_error_message(schema_apply_result)}；"
                    f"且 public 回退解析失败: {exc}"
                ),
            ) from exc

        public_apply_result = await alter_openspg_schema_draft_public(
            project_id=request.project_id,
            schema_draft=schema_draft,
        )
        public_apply_result.setdefault("meta", {})
        public_apply_result["meta"]["apply_mode"] = "public_alter_schema_fallback"
        public_apply_result["meta"]["project_namespace"] = project_namespace
        public_apply_result["meta"]["legacy_apply_error"] = _live_error_message(schema_apply_result)

        if (not _is_live_success(public_apply_result)) and _is_schema_already_exists_error(
            public_apply_result
        ):
            public_apply_result = {
                "mode": "live",
                "http_status": 200,
                "request": public_apply_result.get("request", {}),
                "response": {
                    "success": True,
                    "result": True,
                    "message": "schema already exists, treat as success",
                },
                "meta": {
                    **public_apply_result.get("meta", {}),
                    "apply_mode": "public_alter_schema_fallback",
                    "project_namespace": project_namespace,
                    "legacy_apply_error": _live_error_message(schema_apply_result),
                    "idempotent": True,
                },
            }

        if not _is_live_success(public_apply_result):
            raise HTTPException(
                status_code=502,
                detail=(
                    "Schema 提交失败: "
                    f"legacy={_live_error_message(schema_apply_result)}; "
                    f"public={_live_error_message(public_apply_result)}"
                ),
            )
        schema_apply_result = public_apply_result
    else:
        schema_apply_result.setdefault("meta", {})
        schema_apply_result["meta"]["apply_mode"] = "legacy_v1_schemas"

    _MODEL_STUDIO_SCHEMA_SCRIPT_CACHE[request.project_id] = request.schema_script
    active_model_profile = _activate_model_profile(
        project_id=request.project_id,
        schema_script=request.schema_script,
        label="schema-apply",
        source="model_studio_apply",
    )

    schema_script_result, schema_graph_result, reason_schema_result = await asyncio.gather(
        get_openspg_schema_script(project_id=request.project_id),
        get_openspg_schema_graph(project_id=request.project_id),
        get_openspg_reason_schema(project_id=request.project_id),
    )
    schema_model = _extract_schema_model(schema_graph_result.get("response"))
    if int(schema_model.get("entity_count") or 0) <= 0:
        schema_model = _extract_schema_model_from_reason_schema(reason_schema_result.get("response"))
    script_payload = _unwrap_http_result_payload(schema_script_result.get("response"))
    current_script = (
        script_payload
        if isinstance(script_payload, str) and script_payload.strip()
        else _MODEL_STUDIO_SCHEMA_SCRIPT_CACHE.get(request.project_id, "")
    )
    return {
        "project_id": request.project_id,
        "schema_apply_result": schema_apply_result,
        "schema_script_result": schema_script_result,
        "schema_graph_result": schema_graph_result,
        "reason_schema_result": reason_schema_result,
        "schema_model": schema_model,
        "schema_script": current_script,
        "active_model_profile": active_model_profile,
    }


@router.post("/model-studio/extraction/submit")
async def submit_model_studio_extraction(request: ModelStudioExtractionSubmitRequest):
    text_content = (request.text_content or "").strip()
    if not text_content:
        raise HTTPException(status_code=400, detail="text_content 不能为空")

    filename = f"model_studio_{time.strftime('%Y%m%d%H%M%S', time.localtime())}.md"
    return await _submit_model_studio_file_job(
        project_id=request.project_id,
        filename=filename,
        content=text_content.encode("utf-8"),
        content_type="text/markdown",
        worker_num=request.worker_num,
        job_name=request.job_name,
        split_length=request.split_length,
        semantic_split=request.semantic_split,
        schema_constrained_extract=request.schema_constrained_extract,
    )


@router.post("/model-studio/extraction/submit-file")
async def submit_model_studio_extraction_file(
    file: UploadFile = File(...),
    project_id: int = Form(1),
    job_name: Optional[str] = Form(None),
    worker_num: int = Form(1),
    split_length: int = Form(500),
    semantic_split: bool = Form(False),
    schema_constrained_extract: bool = Form(True),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，当前限制 20MB")
    return await _submit_model_studio_file_job(
        project_id=max(int(project_id), 1),
        filename=file.filename or "model_studio_upload.md",
        content=data,
        content_type=file.content_type or "application/octet-stream",
        worker_num=max(int(worker_num), 1),
        job_name=job_name,
        split_length=max(int(split_length), 100),
        semantic_split=bool(semantic_split),
        schema_constrained_extract=bool(schema_constrained_extract),
    )


@router.get("/model-studio/extraction/status")
async def get_model_studio_extraction_status(
    project_id: int = Query(1, ge=1),
    job_id: int = Query(..., ge=1),
):
    builder_job_result = await get_openspg_builder_job(job_id=job_id)
    job_payload = _unwrap_http_result_payload(builder_job_result.get("response"))
    job = job_payload if isinstance(job_payload, dict) else {}

    task_id = job.get("taskId")
    try:
        task_id_value = int(task_id) if task_id is not None else None
    except Exception:
        task_id_value = None
    instances_result: Optional[Dict[str, Any]] = None
    tasks_result: Optional[Dict[str, Any]] = None
    instances: List[Dict[str, Any]] = []
    tasks: List[Dict[str, Any]] = []
    if task_id_value is not None:
        instances_result = await search_openspg_scheduler_instances(
            task_id=task_id_value,
            project_id=project_id,
        )
        instances_payload = _unwrap_http_result_payload(instances_result.get("response"))
        if isinstance(instances_payload, dict):
            raw_instances = instances_payload.get("results")
            if isinstance(raw_instances, list):
                instances = [x for x in raw_instances if isinstance(x, dict)]

        latest_instance_id = None
        if instances:
            first_instance_id = instances[0].get("id")
            try:
                latest_instance_id = int(first_instance_id) if first_instance_id is not None else None
            except Exception:
                latest_instance_id = None

        if latest_instance_id is not None:
            tasks_result = await search_openspg_scheduler_tasks(
                instance_id=latest_instance_id,
                project_id=project_id,
            )
            tasks_payload = _unwrap_http_result_payload(tasks_result.get("response"))
            if isinstance(tasks_payload, dict):
                raw_tasks = tasks_payload.get("results")
                if isinstance(raw_tasks, list):
                    tasks = [x for x in raw_tasks if isinstance(x, dict)]

    task_status_count: Dict[str, int] = {}
    latest_trace_log = ""
    for task in tasks:
        status = str(task.get("status") or "UNKNOWN")
        task_status_count[status] = task_status_count.get(status, 0) + 1
        trace = str(task.get("traceLog") or "").strip()
        if trace:
            latest_trace_log = trace

    llm_trace = _parse_llm_trace_from_instances(instances)

    return {
        "project_id": project_id,
        "job_id": job_id,
        "job": job,
        "builder_job_result": builder_job_result,
        "instances_result": instances_result,
        "tasks_result": tasks_result,
        "instances": instances,
        "tasks": tasks,
        "instances_total": len(instances),
        "tasks_total": len(tasks),
        "task_status_count": task_status_count,
        "latest_trace_log": latest_trace_log,
        "llm_trace": llm_trace,
    }


@router.get("/model-studio/extraction/sample")
async def get_model_studio_extraction_sample(
    project_id: int = Query(1, ge=1),
    job_id: int = Query(..., ge=1),
):
    builder_job_result = await get_openspg_builder_job(job_id=job_id)
    job_payload = _unwrap_http_result_payload(builder_job_result.get("response"))
    job = job_payload if isinstance(job_payload, dict) else {}
    sample_result = await get_openspg_builder_sample(project_id=project_id, job_id=job_id)
    sample_payload = _unwrap_http_result_payload(sample_result.get("response"))
    if isinstance(sample_payload, dict):
        raw_nodes = sample_payload.get("resultNodes")
        raw_edges = sample_payload.get("resultEdges")
    else:
        raw_nodes = []
        raw_edges = []
    result_nodes = raw_nodes if isinstance(raw_nodes, list) else []
    result_edges = raw_edges if isinstance(raw_edges, list) else []
    entities = _extract_result_entities([x for x in result_nodes if isinstance(x, dict)])

    instances: List[Dict[str, Any]] = []
    task_id = job.get("taskId")
    try:
        task_id_value = int(task_id) if task_id is not None else None
    except Exception:
        task_id_value = None
    if task_id_value is not None:
        instances_result = await search_openspg_scheduler_instances(
            task_id=task_id_value,
            project_id=project_id,
        )
        instances_payload = _unwrap_http_result_payload(instances_result.get("response"))
        if isinstance(instances_payload, dict):
            raw_instances = instances_payload.get("results")
            if isinstance(raw_instances, list):
                instances = [x for x in raw_instances if isinstance(x, dict)]
    llm_trace = _parse_llm_trace_from_instances(instances)

    return {
        "project_id": project_id,
        "job_id": job_id,
        "sample_result": sample_result,
        "builder_job_result": builder_job_result,
        "result_nodes": result_nodes,
        "result_edges": result_edges,
        "entities": entities,
        "llm_trace": llm_trace,
        "counts": {
            "nodes": len(result_nodes),
            "edges": len(result_edges),
            "entities": len(entities),
        },
    }
