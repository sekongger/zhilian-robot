from __future__ import annotations

import argparse
import json
import os
from typing import Any

from crawler.connectors.octopus_connector import OctopusConnector
from crawler.connectors.source_registry import load_sources
from crawler.domain.models import SourceConfig
from crawler.services.canonical_url_service import canonicalize_url
from crawler.utils.text_utils import normalize_text
from crawler.utils.time_utils import is_within_hours, parse_datetime_to_utc


def _pick_source(source_id: str | None) -> SourceConfig:
    sources = load_sources("crawler/config/sources.yaml")
    enabled_octopus = [s for s in sources if s.enabled and s.source_type == "octopus"]
    if not enabled_octopus:
        raise RuntimeError("No enabled octopus source found in crawler/config/sources.yaml")
    if source_id:
        for src in enabled_octopus:
            if src.source_id == source_id:
                return src
        raise RuntimeError(f"Octopus source_id not found or not enabled: {source_id}")
    return enabled_octopus[0]


def _to_payload_preview(items: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for item in items[:max_items]:
        preview.append(
            {
                "title": str(item.get("title", "")).strip(),
                "url": str(item.get("url", "")).strip(),
                "publish_time": item.get("publish_time"),
                "id": item.get("id") or item.get("dataId") or item.get("newsId"),
            }
        )
    return preview


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose octopus connectivity and not-exported backlog.")
    parser.add_argument("--source-id", default=None, help="Source id in crawler/config/sources.yaml")
    parser.add_argument("--preview", type=int, default=5, help="Preview item count per task")
    parser.add_argument(
        "--since-hours",
        type=int,
        default=24,
        help="Filter window used by octopus connector map logic (default 24)",
    )
    parser.add_argument(
        "--scan-pages",
        type=int,
        default=3,
        help="How many notexported pages (size=100) to scan per task for reason stats.",
    )
    parser.add_argument(
        "--dump-raw",
        action="store_true",
        help="Print raw API response summary for task listing.",
    )
    args = parser.parse_args()

    source = _pick_source(args.source_id)
    connector = OctopusConnector()
    options = source.options or {}

    username = str(options.get("username", "")).strip() or os.getenv("OCTOPUS_USERNAME", "").strip()
    password = str(options.get("password", "")).strip() or os.getenv("OCTOPUS_PASSWORD", "").strip()
    if not username or not password:
        print(json.dumps({"ok": False, "reason": "missing_credentials"}, ensure_ascii=False, indent=2))
        return 2

    token = connector._get_token(username=username, password=password)
    if not token:
        print(json.dumps({"ok": False, "reason": "token_failed"}, ensure_ascii=False, indent=2))
        return 3

    task_ids = connector._resolve_task_ids(token=token, options=options)
    if not task_ids:
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "no_task_ids_resolved",
                    "source_id": source.source_id,
                    "task_group_name": options.get("task_group_name"),
                    "env_task_group_name": os.getenv("OCTOPUS_TASK_GROUP_NAME", ""),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 4

    summary: dict[str, Any] = {
        "ok": True,
        "source_id": source.source_id,
        "base_url": connector.base_url,
        "since_hours": args.since_hours,
        "task_count": len(task_ids),
        "tasks": [],
        "notexported_total": 0,
    }

    for task_id in task_ids:
        url = f"{connector.base_url}/data/notexported"
        params = {"taskId": task_id, "size": 100}
        try:
            response = connector._headers(token=token)
            import requests

            resp = requests.get(url, headers=response, params=params, timeout=connector.timeout_seconds)
            resp.raise_for_status()
            body = resp.json() or {}
            data = body.get("data", {}) or {}
            total = int(data.get("total", 0) or 0)
            rows = data.get("data", []) or []
            preview = _to_payload_preview(rows, max_items=max(0, args.preview))
            reason_stats: dict[str, int] = {
                "kept": 0,
                "filtered_missing_title": 0,
                "filtered_publish_time_window": 0,
                "filtered_no_content": 0,
                "filtered_no_url_after_canonicalize": 0,
            }
            publish_stats: dict[str, Any] = {
                "sample_count": 0,
                "latest_publish_time_utc": None,
                "oldest_publish_time_utc": None,
                "within_since_hours_count": 0,
            }

            # Page 1
            pages_to_scan = max(1, args.scan_pages)
            scanned_rows = list(rows)
            for page_no in range(2, pages_to_scan + 1):
                page_params = {"taskId": task_id, "size": 100, "pageNo": page_no}
                page_resp = requests.get(
                    url,
                    headers=response,
                    params=page_params,
                    timeout=connector.timeout_seconds,
                )
                page_resp.raise_for_status()
                page_body = page_resp.json() or {}
                page_data = (page_body.get("data", {}) or {}).get("data", []) or []
                scanned_rows.extend(page_data)

            for item in scanned_rows:
                title = normalize_text(item.get("title", ""))
                if not title:
                    reason_stats["filtered_missing_title"] += 1
                    continue

                raw_url = normalize_text(item.get("url", ""))
                canonical_url = canonicalize_url(raw_url)
                if not canonical_url:
                    canonical_url = canonicalize_url(f"{source.url.rstrip('/')}/{task_id}")
                if not canonical_url:
                    reason_stats["filtered_no_url_after_canonicalize"] += 1
                    continue

                publish_time = parse_datetime_to_utc(item.get("publish_time"))
                if publish_time is not None:
                    ts = publish_time.isoformat()
                    if (
                        publish_stats["latest_publish_time_utc"] is None
                        or ts > publish_stats["latest_publish_time_utc"]
                    ):
                        publish_stats["latest_publish_time_utc"] = ts
                    if (
                        publish_stats["oldest_publish_time_utc"] is None
                        or ts < publish_stats["oldest_publish_time_utc"]
                    ):
                        publish_stats["oldest_publish_time_utc"] = ts
                if not is_within_hours(publish_time, args.since_hours):
                    reason_stats["filtered_publish_time_window"] += 1
                    continue
                if is_within_hours(publish_time, args.since_hours):
                    publish_stats["within_since_hours_count"] += 1

                raw_content = normalize_text(item.get("content", "")) or normalize_text(
                    item.get("abstract", "")
                )
                if not raw_content:
                    raw_content = title
                if not raw_content:
                    reason_stats["filtered_no_content"] += 1
                    continue

                reason_stats["kept"] += 1

            publish_stats["sample_count"] = len(scanned_rows)
            summary["tasks"].append(
                {
                    "task_id": task_id,
                    "notexported_total": total,
                    "page_size": len(rows),
                    "scanned_rows": len(scanned_rows),
                    "reason_stats": reason_stats,
                    "publish_stats": publish_stats,
                    "preview": preview,
                }
            )
            summary["notexported_total"] += total
            if args.dump_raw:
                summary["tasks"][-1]["raw_keys"] = list(body.keys())
        except Exception as exc:
            summary["tasks"].append(
                {
                    "task_id": task_id,
                    "error": str(exc),
                }
            )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
