"""OpenSPG 引擎演示快照客户端（失败自动降级 mock）。"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional

import httpx


def _mock_section(name: str, request: Dict[str, Any], message: str) -> Dict[str, Any]:
    return {
        "mode": "mock",
        "request": request,
        "response": {"message": message, "section": name},
    }


async def _request_json(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    req = {"method": method, "path": path, "params": params or {}, "json": json_body or {}}
    try:
        resp = await client.request(method, path, params=params, json=json_body)
        content_type = resp.headers.get("content-type", "")
        payload: Any
        if "application/json" in content_type:
            payload = resp.json()
        else:
            payload = {"text": resp.text[:1000]}
        return {
            "mode": "live" if resp.status_code < 500 else "mock",
            "request": req,
            "http_status": resp.status_code,
            "response": payload,
        }
    except Exception as exc:  # pragma: no cover - 网络不可用时走这里
        return _mock_section(path, req, f"OpenSPG 请求失败，使用演示数据：{exc}")


async def _request_multipart(
    client: httpx.AsyncClient,
    path: str,
    *,
    files: Dict[str, Any],
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    req = {"method": "POST", "path": path, "data": data or {}, "files": list(files.keys())}
    try:
        resp = await client.post(path, files=files, data=data or {})
        content_type = resp.headers.get("content-type", "")
        payload: Any
        if "application/json" in content_type:
            payload = resp.json()
        else:
            payload = {"text": resp.text[:1000]}
        return {
            "mode": "live" if resp.status_code < 500 else "mock",
            "request": req,
            "http_status": resp.status_code,
            "response": payload,
        }
    except Exception as exc:  # pragma: no cover - 网络不可用时走这里
        return _mock_section(path, req, f"OpenSPG 请求失败，使用演示数据：{exc}")


async def get_openspg_capability_snapshot(project_id: int = 1) -> Dict[str, Any]:
    base_url = (os.getenv("OPENSPG_BASE_URL") or "http://127.0.0.1:8887").rstrip("/")
    timeout = float(os.getenv("OPENSPG_TIMEOUT_SECONDS") or "5")

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        builder_demo_request = {
            "projectId": project_id,
            "keyword": "",
            "pageNo": 1,
            "pageSize": 10,
        }

        (
            reason,
            search,
            graph,
            builder_live,
            schema_live,
        ) = await asyncio.gather(
            _request_json(
                client,
                "GET",
                "/public/v1/reason/schema",
                params={"projectId": project_id},
            ),
            _request_json(
                client,
                "POST",
                "/public/v1/search/custom",
                json_body={
                    "projectId": project_id,
                    "customQuery": "MATCH (n) RETURN n AS node, 1.0 AS score LIMIT 5",
                },
            ),
            _request_json(
                client,
                "GET",
                "/public/v1/graph/allLabels",
                params={"projectId": project_id},
            ),
            _request_json(
                client,
                "POST",
                "/public/v1/builder/search",
                json_body=builder_demo_request,
            ),
            _request_json(
                client,
                "GET",
                "/public/v1/schema/queryProjectSchema",
                params={"projectId": project_id},
            ),
        )

    return {
        "schema_live": schema_live,
        "builder_live": builder_live,
        "reason": reason,
        "search": search,
        "graph": graph,
        "meta": {
            "openspg_base_url": base_url,
            "project_id": project_id,
        },
    }


def _build_client() -> tuple[str, float, Dict[str, str]]:
    base_url = (os.getenv("OPENSPG_BASE_URL") or "http://127.0.0.1:8887").rstrip("/")
    timeout = float(os.getenv("OPENSPG_TIMEOUT_SECONDS") or "30")
    user_no = (os.getenv("OPENSPG_USER_NO") or "openspg").strip()
    headers: Dict[str, str] = {}
    if user_no:
        headers["userNo"] = user_no
        headers["userNumber"] = user_no
    return base_url, timeout, headers


def _is_ok(check: Dict[str, Any]) -> bool:
    return bool(check.get("mode") == "live" and int(check.get("http_status") or 0) < 400)


async def get_openspg_health(project_id: int = 1) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        schema_check, graph_check, search_check, builder_check = await asyncio.gather(
            _request_json(
                client,
                "GET",
                "/public/v1/schema/queryProjectSchema",
                params={"projectId": project_id},
            ),
            _request_json(
                client,
                "GET",
                "/public/v1/graph/allLabels",
                params={"projectId": project_id},
            ),
            _request_json(
                client,
                "POST",
                "/public/v1/search/custom",
                json_body={
                    "projectId": project_id,
                    "customQuery": "MATCH (n) RETURN n AS node, 1.0 AS score LIMIT 5",
                },
            ),
            _request_json(
                client,
                "POST",
                "/public/v1/builder/search",
                json_body={"projectId": project_id, "pageNo": 1, "pageSize": 1},
            ),
        )

    checks = {
        "schema": schema_check,
        "graph": graph_check,
        "search": search_check,
        "builder": builder_check,
    }
    ok_count = sum(1 for item in checks.values() if _is_ok(item))
    status = "live" if ok_count >= 3 else ("partial" if ok_count >= 1 else "offline")
    return {
        "openspg_base_url": base_url,
        "project_id": project_id,
        "status": status,
        "ok_count": ok_count,
        "total_checks": len(checks),
        "checks": checks,
    }


async def submit_openspg_builder_job(
    *,
    project_id: int,
    command: str,
    worker_num: int = 1,
    user_number: Optional[str] = None,
    image: Optional[str] = None,
    worker_pool: Optional[str] = None,
    envs: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    body: Dict[str, Any] = {
        "projectId": project_id,
        "command": command,
        "workerNum": worker_num,
    }
    if user_number:
        body["userNumber"] = user_number
    if image:
        body["image"] = image
    if worker_pool:
        body["workerPool"] = worker_pool
    if envs:
        body["envs"] = envs

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(client, "POST", "/public/v1/builder/kag/submit", json_body=body)

    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/public/v1/builder/kag/submit",
        }
    )
    return result


async def apply_openspg_schema_script(
    *,
    project_id: int,
    schema_script: str,
) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    body: Dict[str, Any] = {
        "projectId": project_id,
        "schemaScript": schema_script,
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(client, "POST", "/v1/schemas", json_body=body)

    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/v1/schemas",
        }
    )
    return result


async def get_openspg_schema_script(*, project_id: int) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "GET",
            "/v1/schemas/getSchemaScript",
            params={"projectId": project_id},
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/v1/schemas/getSchemaScript",
        }
    )
    return result


async def get_openspg_schema_graph(*, project_id: int) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "GET",
            f"/v1/schemas/graph/{project_id}",
            params={"projectId": project_id},
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": f"/v1/schemas/graph/{project_id}",
        }
    )
    return result


async def get_openspg_builder_job(*, job_id: int) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "GET",
            "/public/v1/builder/getById",
            params={"id": job_id},
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "job_id": job_id,
            "endpoint": "/public/v1/builder/getById",
        }
    )
    return result


async def get_openspg_project(*, project_id: int) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "GET",
            "/public/v1/project",
            params={"projectId": project_id},
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/public/v1/project",
        }
    )
    return result


async def get_openspg_reason_schema(*, project_id: int) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "GET",
            "/public/v1/reason/schema",
            params={"projectId": project_id},
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/public/v1/reason/schema",
        }
    )
    return result


async def get_openspg_graph_labels(*, project_id: int) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "GET",
            "/public/v1/graph/allLabels",
            params={"projectId": project_id},
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/public/v1/graph/allLabels",
        }
    )
    return result


async def search_openspg_custom(*, project_id: int, custom_query: str) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    body = {
        "projectId": project_id,
        "customQuery": custom_query,
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "POST",
            "/public/v1/search/custom",
            json_body=body,
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/public/v1/search/custom",
            "custom_query": custom_query,
        }
    )
    return result


async def alter_openspg_schema_draft_public(
    *,
    project_id: int,
    schema_draft: Dict[str, Any],
) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    body: Dict[str, Any] = {
        "projectId": project_id,
        "schemaDraft": schema_draft or {},
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "POST",
            "/public/v1/schema/alterSchema",
            json_body=body,
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/public/v1/schema/alterSchema",
        }
    )
    return result


async def search_openspg_scheduler_instances(
    *,
    task_id: int,
    project_id: int,
    page_no: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    body: Dict[str, Any] = {
        "projectId": project_id,
        "jobId": task_id,
        "pageNo": max(page_no, 1),
        "pageSize": max(page_size, 1),
        "sort": "id",
        "order": "desc",
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "POST",
            "/public/v1/scheduler/instance/search",
            json_body=body,
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "task_id": task_id,
            "endpoint": "/public/v1/scheduler/instance/search",
        }
    )
    return result


async def search_openspg_scheduler_tasks(
    *,
    instance_id: int,
    project_id: int,
    page_no: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    body: Dict[str, Any] = {
        "projectId": project_id,
        "instanceId": instance_id,
        "pageNo": max(page_no, 1),
        "pageSize": max(page_size, 1),
        "sort": "id",
        "order": "asc",
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "POST",
            "/public/v1/scheduler/task/search",
            json_body=body,
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "instance_id": instance_id,
            "endpoint": "/public/v1/scheduler/task/search",
        }
    )
    return result


async def get_openspg_builder_sample(*, project_id: int, job_id: int) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(
            client,
            "GET",
            "/public/v1/reasoner/task/builder/query",
            # 兼容不同 OpenSPG 版本：有的读取 `id`，有的读取 `jobId`
            params={"projectId": project_id, "jobId": job_id, "id": job_id},
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "job_id": job_id,
            "endpoint": "/public/v1/reasoner/task/builder/query",
        }
    )
    return result


async def upload_openspg_reasoner_file(
    *,
    filename: str,
    content: bytes,
    content_type: str,
    file_type: str,
) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    files = {"file": (filename, content, content_type)}
    data = {"type": file_type}
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_multipart(
            client,
            "/public/v1/reasoner/dialog/uploadFile",
            files=files,
            data=data,
        )
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "endpoint": "/public/v1/reasoner/dialog/uploadFile",
            "file_name": filename,
            "file_type": file_type,
        }
    )
    return result


async def submit_openspg_builder_legacy_job(
    *,
    project_id: int,
    job_name: str,
    file_url: str,
    extension: Dict[str, Any],
    worker_num: int = 1,
    data_source_type: str = "FILE",
    builder_type: str = "KAG",
    retrievals: Optional[str] = None,
) -> Dict[str, Any]:
    base_url, timeout, headers = _build_client()
    body: Dict[str, Any] = {
        "projectId": project_id,
        "jobName": job_name,
        "type": builder_type,
        "lifeCycle": "ONCE",
        "dataSourceType": data_source_type,
        "fileUrl": file_url,
        "workerNum": max(worker_num, 1),
        "extension": json_dumps(extension),
    }
    if retrievals:
        body["retrievals"] = retrievals
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers) as client:
        result = await _request_json(client, "POST", "/public/v1/builder/job/submit", json_body=body)
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "openspg_base_url": base_url,
            "project_id": project_id,
            "endpoint": "/public/v1/builder/job/submit",
        }
    )
    return result


def json_dumps(payload: Dict[str, Any]) -> str:
    import json

    return json.dumps(payload or {}, ensure_ascii=False)
