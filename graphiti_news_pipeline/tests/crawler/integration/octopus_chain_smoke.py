from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests


def _load_dotenv_if_present() -> None:
    root_env = Path(__file__).resolve().parents[3] / ".env"
    if not root_env.exists():
        return
    for line in root_env.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip("'").strip('"')
        os.environ[key] = value


def _request_json(
    method: str,
    url: str,
    *,
    timeout: int,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json_payload,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected payload type: {type(payload)}")
    return payload


def run(group_name: str, sample_size: int, mark_exported: bool) -> int:
    _load_dotenv_if_present()

    base_url = os.getenv("OCTOPUS_API_BASE", "https://openapi.bazhuayu.com").strip().rstrip("/")
    username = os.getenv("OCTOPUS_USERNAME", "").strip()
    password = os.getenv("OCTOPUS_PASSWORD", "").strip()
    timeout = int(os.getenv("CRAWLER_OCTOPUS_HTTP_TIMEOUT_SECONDS", "30"))

    if not username or not password:
        print("ERROR: OCTOPUS_USERNAME/OCTOPUS_PASSWORD 未配置。")
        return 2

    print(f"[1/5] 获取 token: {base_url}/token")
    token_resp = _request_json(
        "POST",
        f"{base_url}/token",
        timeout=timeout,
        json_payload={"username": username, "password": password, "grant_type": "password"},
    )
    access_token = str(((token_resp.get("data") or {}).get("access_token") or "")).strip()
    if not access_token:
        print("ERROR: token 接口返回缺少 access_token。")
        return 3
    token = f"Bearer {access_token}"

    headers = {"Content-Type": "application/json", "Authorization": token}

    print(f"[2/5] 查询任务组: {group_name}")
    group_resp = _request_json("GET", f"{base_url}/taskGroup", timeout=timeout, headers=headers)
    groups = (group_resp.get("data") or []) if isinstance(group_resp.get("data"), list) else []
    matched = [g for g in groups if str(g.get("taskGroupName", "")).strip() == group_name]
    if not matched:
        names = [str(g.get("taskGroupName", "")).strip() for g in groups][:20]
        print("ERROR: 未找到目标任务组。可用任务组(最多20个):")
        print(json.dumps(names, ensure_ascii=False, indent=2))
        return 4
    group_id = matched[0].get("taskGroupId")
    if not group_id:
        print("ERROR: 目标任务组缺少 taskGroupId。")
        return 5

    print(f"[3/5] 查询任务列表: group_id={group_id}")
    task_resp = _request_json(
        "GET",
        f"{base_url}/task/search",
        timeout=timeout,
        headers=headers,
        params={"taskGroupId": group_id},
    )
    tasks = (task_resp.get("data") or []) if isinstance(task_resp.get("data"), list) else []
    if not tasks:
        print("ERROR: 任务组下没有任务。")
        return 6

    print(f"[4/5] 抽样检查未导出数据: 每任务 size={sample_size}")
    summaries: list[dict[str, Any]] = []
    ok_count = 0
    for task in tasks:
        task_id = str(task.get("taskId", "")).strip()
        task_name = str(task.get("taskName", "")).strip()
        if not task_id:
            continue
        try:
            data_resp = _request_json(
                "GET",
                f"{base_url}/data/notexported",
                timeout=timeout,
                headers=headers,
                params={"taskId": task_id, "size": sample_size},
            )
            data_block = data_resp.get("data") or {}
            total = int(data_block.get("total", 0) or 0)
            items = data_block.get("data") or []
            fetched = len(items) if isinstance(items, list) else 0
            status = "ok"
            ok_count += 1
        except Exception as exc:  # noqa: BLE001
            total = -1
            fetched = 0
            status = f"error: {exc}"

        summaries.append(
            {
                "task_id": task_id,
                "task_name": task_name,
                "status": status,
                "not_exported_total": total,
                "sample_fetched": fetched,
            }
        )

        if mark_exported and status == "ok":
            _request_json(
                "POST",
                f"{base_url}/data/markexported",
                timeout=timeout,
                headers=headers,
                json_payload={"taskId": task_id},
            )

    print("[5/5] 测试结果汇总")
    output = {
        "group_name": group_name,
        "group_id": str(group_id),
        "task_count": len(tasks),
        "task_ok_count": ok_count,
        "mark_exported": mark_exported,
        "tasks": summaries,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if ok_count == 0:
        print("ERROR: 所有任务的数据拉取均失败。")
        return 7
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Octopus chain connectivity smoke script.")
    parser.add_argument("--group-name", default="graphiti数据源", help="目标任务组名称")
    parser.add_argument("--sample-size", type=int, default=5, help="每个任务拉取样本条数")
    parser.add_argument(
        "--mark-exported",
        action="store_true",
        help="是否执行 markexported（默认关闭，避免影响线上数据）",
    )
    args = parser.parse_args()
    return run(group_name=args.group_name, sample_size=max(1, args.sample_size), mark_exported=args.mark_exported)


if __name__ == "__main__":
    sys.exit(main())
