"""
将 zhilian-robot 新闻数据导出为 OpenSPG Builder 可消费的 JSONL 批次（演示版）。

示例：
  python scripts/export_openspg_news_batch.py --output /tmp/openspg_news.jsonl --limit 200
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from app.openspg_demo.bridge import export_news_batch_to_jsonl_lines
from app.openspg_demo.headlines_service import get_demo_news_samples


def _load_rows(limit: int) -> List[Dict[str, Any]]:
    try:
        from app.database.mongodb import mongodb_conn

        rows = mongodb_conn.find_many("source_news", limit=limit, sort=[("publish_time", -1)])
        if rows:
            return rows
    except Exception:
        pass

    try:
        from app.database.mongodb import mongodb_conn

        rows = mongodb_conn.find_many("crawled_articles", limit=limit, sort=[("crawled_at", -1)])
        if rows:
            return rows
    except Exception:
        pass

    return get_demo_news_samples()[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 OpenSPG Builder JSONL 批次")
    parser.add_argument("--output", required=True, help="输出 JSONL 文件路径")
    parser.add_argument("--limit", type=int, default=200, help="最多导出条数")
    args = parser.parse_args()

    rows = _load_rows(max(1, args.limit))
    lines = export_news_batch_to_jsonl_lines(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    print(f"exported={len(lines)} file={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

