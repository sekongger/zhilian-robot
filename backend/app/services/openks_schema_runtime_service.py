from __future__ import annotations

import os
import sys
import urllib.request
import json
from pathlib import Path
from typing import Any, Dict


OPENKS_NEWS_MODULE_NAME = "news_kg"
OPENKS_NEWS_NAMESPACE = "OpenKSNews"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _openks_source_root() -> Path:
    return _repo_root() / "supxmind" / "supxmind-openks"


def _default_kag_project_dir() -> Path:
    return _repo_root() / "modules" / "kag" / "kag" / "examples" / OPENKS_NEWS_NAMESPACE


def _ensure_openks_import_path() -> None:
    source_root = _openks_source_root()
    if source_root.exists() and str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))


def _resolve_host_addr(host_addr: str | None = None) -> str:
    return str(
        host_addr
        or os.getenv("OPENSPG_BASE_URL")
        or os.getenv("OPENSPG_DEMO_BASE_URL")
        or "http://127.0.0.1:8887"
    ).strip()


def _resolve_project_namespace(project_id: int, host_addr: str) -> str:
    url = f"{host_addr.rstrip('/')}/public/v1/project?projectId={int(project_id)}"
    with urllib.request.urlopen(url, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    rows = []
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = [data]
        else:
            rows = [payload]

    for row in rows:
        if not isinstance(row, dict):
            continue
        namespace = str(row.get("namespace") or "").strip()
        if namespace:
            return namespace
    return OPENKS_NEWS_NAMESPACE


def _load_openks_interop():
    _ensure_openks_import_path()
    from openks.common.interop import compile_module_schema, export_module_schema_to_kag_project

    return compile_module_schema, export_module_schema_to_kag_project


def _activate_openks_model_profile(*, project_id: int, schema_script: str, activate_label: str) -> Dict[str, Any]:
    from app.openspg_demo import routes as demo_routes

    return demo_routes._activate_model_profile(
        project_id=project_id,
        schema_script=schema_script,
        label=activate_label or "openks-news-kg",
        source="openks_module",
    )


def _normalize_export_payload(payload: Dict[str, Any], *, host_addr: str, project_id: int) -> Dict[str, Any]:
    normalized = dict(payload)
    for key in ("project_dir", "schema_path"):
        value = normalized.get(key)
        if value is not None:
            normalized[key] = str(value)
    normalized["host_addr"] = host_addr
    normalized["project_id"] = project_id
    return normalized


def _build_schema_commit_result(export_payload: Dict[str, Any]) -> Dict[str, Any]:
    committed = bool(export_payload.get("committed"))
    return {
        "mode": "openks_sync_schema",
        "http_status": 200,
        "committed": committed,
        "response": {
            "success": True,
            "result": True,
            "message": "OpenKS schema 已提交到 OpenSPG" if committed else "OpenKS schema 已校验并保持现状",
        },
        "meta": {
            "effective_success": True,
            "idempotent": not committed,
            "module_name": export_payload.get("module_name"),
            "namespace": export_payload.get("namespace"),
            "project_dir": export_payload.get("project_dir"),
            "schema_path": export_payload.get("schema_path"),
            "host_addr": export_payload.get("host_addr"),
            "project_id": export_payload.get("project_id"),
        },
    }


async def apply_openks_news_kg_schema(
    *,
    project_id: int,
    activate_label: str = "workflow-step",
    module_name: str = OPENKS_NEWS_MODULE_NAME,
    namespace: str | None = None,
    project_dir: str | Path | None = None,
    host_addr: str | None = None,
) -> Dict[str, Any]:
    compile_module_schema, export_module_schema_to_kag_project = _load_openks_interop()

    resolved_host_addr = _resolve_host_addr(host_addr)
    resolved_namespace = str(namespace or _resolve_project_namespace(project_id, resolved_host_addr)).strip() or OPENKS_NEWS_NAMESPACE
    compiled_schema_script = compile_module_schema(module_name, namespace=resolved_namespace)
    export_payload = _normalize_export_payload(
        export_module_schema_to_kag_project(
            module_name,
            namespace=resolved_namespace,
            project_dir=project_dir or _default_kag_project_dir(),
            commit=True,
            host_addr=resolved_host_addr,
            project_id=project_id,
        ),
        host_addr=resolved_host_addr,
        project_id=project_id,
    )
    schema_commit_result = _build_schema_commit_result(export_payload)
    activate_result = _activate_openks_model_profile(
        project_id=project_id,
        schema_script=compiled_schema_script,
        activate_label=activate_label,
    )

    return {
        "schema_source": "openks_module",
        "module_name": module_name,
        "namespace": resolved_namespace,
        "compiled_schema_script": compiled_schema_script,
        "kag_schema_export": export_payload,
        "schema_commit_result": schema_commit_result,
        "schema_apply_result": schema_commit_result,
        "activate_result": activate_result,
        "active_model_profile": activate_result,
    }
