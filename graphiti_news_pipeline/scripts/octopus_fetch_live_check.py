from __future__ import annotations

import json
from typing import Any

from dotenv import load_dotenv

from crawler.connectors.octopus_connector import OctopusConnector
from crawler.connectors.source_registry import load_sources


def _pick_octopus_source(source_id: str = "octopus_news") -> Any:
    sources = load_sources("crawler/config/sources.yaml")
    for source in sources:
        if source.enabled and source.source_type == "octopus" and source.source_id == source_id:
            return source
    raise RuntimeError(f"enabled octopus source not found: {source_id}")


def main() -> int:
    load_dotenv(".env")
    connector = OctopusConnector()
    source = _pick_octopus_source()

    token = connector._get_token(  # noqa: SLF001
        username=source.options.get("username") or "",
        password=source.options.get("password") or "",
    )
    if not token:
        # fallback to env mode inside connector
        token = connector._get_token(  # noqa: SLF001
            username="",
            password="",
        )
    if not token:
        print(json.dumps({"ok": False, "reason": "token_failed"}, ensure_ascii=False, indent=2))
        return 2

    task_ids = connector._resolve_task_ids(token=token, options=source.options or {})  # noqa: SLF001
    if not task_ids:
        print(json.dumps({"ok": False, "reason": "no_task_ids"}, ensure_ascii=False, indent=2))
        return 3

    task_id = task_ids[0]
    records = connector._fetch_task_records_all(  # noqa: SLF001
        token=token,
        source=source,
        task_id=task_id,
        since_hours=72,
        max_items=50,
        should_keep=None,
    )

    preview = []
    for rec in records[:5]:
        preview.append(
            {
                "title": rec.title,
                "url": rec.canonical_url,
                "publish_time_utc": rec.publish_time_utc.isoformat() if rec.publish_time_utc else None,
            }
        )

    print(
        json.dumps(
            {
                "ok": True,
                "task_id": task_id,
                "fetched_count": len(records),
                "preview": preview,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

