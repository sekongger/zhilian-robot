#!/usr/bin/env python3
"""Run the separated Graphiti news graph + common-sense anchor pipeline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.news_graph_pipeline.runner import NewsGraphPipelineRunner


def _default_output_dir() -> str:
    stamp = datetime.now(timezone.utc).strftime("news_graph_%Y%m%d%H%M%S")
    return str(REPO_ROOT / "tmp" / "news_graph_pipeline_runs" / stamp)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _parse_crawler_summary(stdout: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    summaries = []
    for index, char in enumerate(stdout):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(stdout[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("run_id"):
            summaries.append(value)
    if not summaries:
        raise RuntimeError("Graphiti crawler did not print a JSON run summary.")
    return summaries[-1]


def _run_crawler(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.graphiti_project_dir).expanduser().resolve()
    command = [
        *shlex.split(args.crawler_command),
        "-m",
        "crawler.cli",
        "run-once",
        "--since-hours",
        str(args.since_hours),
        "--max-items-per-source",
        str(args.max_items_per_source),
        "--process-limit",
        str(args.process_limit),
    ]
    if args.source:
        command.extend(["--source", args.source])
    if args.ingest:
        command.append("--ingest")
    env = os.environ.copy()
    env["CRAWLER_GRAPHITI_API_BASE"] = str(args.graphiti_api_base).rstrip("/")
    completed = subprocess.run(command, cwd=project_dir, check=True, capture_output=True, text=True, env=env)
    return _parse_crawler_summary(completed.stdout)


def run(args: argparse.Namespace) -> dict[str, Any]:
    crawler_summary = None
    group_id = args.group_id
    if args.run_crawler:
        crawler_summary = _run_crawler(args)
        group_id = group_id or str(crawler_summary.get("graphiti_group_id") or crawler_summary.get("run_id") or "")

    if args.link_entities and not group_id:
        raise RuntimeError("group_id is required for --link-entities unless --run-crawler derives one")

    output_dir = Path(args.output_dir or _default_output_dir()).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = NewsGraphPipelineRunner()
    report = runner.run(
        group_id=group_id,
        sync_anchors=args.sync_anchors,
        link_entities=args.link_entities,
        clear_news_group=args.clear_news_group,
        anchor_limit=args.anchor_limit,
        entity_limit=args.entity_limit,
        output_dir=output_dir,
        crawler_summary=crawler_summary,
        mcp_smoke_test=args.mcp_smoke_test,
    )
    _write_json(output_dir / "run_report.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run separated Graphiti news graph pipeline.")
    parser.add_argument("--graphiti-project-dir", default=str(REPO_ROOT / "graphiti_news_pipeline"))
    parser.add_argument("--run-crawler", action="store_true")
    parser.add_argument("--crawler-command", default=os.getenv("GRAPHITI_NEWS_CRAWLER_COMMAND", sys.executable))
    parser.add_argument("--graphiti-api-base", default=os.getenv("CRAWLER_GRAPHITI_API_BASE", "http://127.0.0.1:8000/api"))
    parser.add_argument("--since-hours", type=int, default=24)
    parser.add_argument("--source", default=None)
    parser.add_argument("--max-items-per-source", type=int, default=20)
    parser.add_argument("--process-limit", type=int, default=300)
    parser.add_argument("--ingest", action="store_true")

    parser.add_argument("--group-id", default=None)
    parser.add_argument("--sync-anchors", action="store_true")
    parser.add_argument("--link-entities", action="store_true")
    parser.add_argument("--mcp-smoke-test", action="store_true")
    parser.add_argument("--clear-news-group", action="store_true")
    parser.add_argument("--anchor-limit", type=int, default=5000)
    parser.add_argument("--entity-limit", type=int, default=1000)
    parser.add_argument("--output-dir", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
