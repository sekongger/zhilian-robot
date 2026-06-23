#!/usr/bin/env python3
"""Compatibility entrypoint for the deprecated Graphiti news big-graph fusion path.

New work should use `backend/scripts/run_news_graph_pipeline.py`, which keeps
dynamic news in Graphiti and links it to common-sense anchors instead of merging
news fields back into the stable common graph.
"""

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
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.incore_fusion_pipeline.importers.openspg_importer import OpenSPGImporter
from app.incore_fusion_pipeline.runners.graphiti_news_fusion_runner import GraphitiNewsFusionRunner
from scripts.fusion.import_fusion_batch_to_neo4j import build_import_payload, import_payload


def _default_batch_id() -> str:
    return datetime.now(timezone.utc).strftime("graphiti_news_fusion_%Y%m%d%H%M%S")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _model_dump_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _parse_crawler_summary(stdout: str) -> dict[str, Any]:
    """Extract the final JSON summary printed by graphiti_news_pipeline crawler CLI."""

    decoder = json.JSONDecoder()
    summaries: list[dict[str, Any]] = []
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


def _validate_crawler_summary(summary: dict[str, Any], *, require_ingest: bool) -> None:
    ingest = summary.get("ingest") or summary.get("ingest_retry") or {}
    if not require_ingest:
        return
    total = int(ingest.get("total") or 0)
    ingested = int(ingest.get("ingested") or 0)
    failed = int(ingest.get("failed") or 0)
    if total > 0 and ingested == 0 and failed > 0:
        raise RuntimeError(
            "Graphiti crawler ingest failed for all records; "
            f"run_id={summary.get('run_id')}, total={total}, failed={failed}."
        )


def _request_json(url: str, *, method: str = "GET", timeout_seconds: int = 15) -> dict[str, Any]:
    data = b"" if method.upper() != "GET" else None
    req = urllib_request.Request(url, data=data, method=method.upper())
    try:
        with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Graphiti API request failed: {method} {url} HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Graphiti API is not reachable: {method} {url}; {exc}") from exc
    return json.loads(body) if body else {}


def _ensure_graphiti_api_ready(args: argparse.Namespace) -> dict[str, Any]:
    api_base = str(args.graphiti_api_base).rstrip("/")
    root_base = api_base.removesuffix("/api")
    health = _request_json(f"{root_base}/", timeout_seconds=args.graphiti_api_timeout)
    init_result = _request_json(
        f"{api_base}/initialize-database",
        method="POST",
        timeout_seconds=args.graphiti_api_timeout,
    )
    return {"health": health, "initialize_database": init_result}


def _run_graphiti_crawler(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.graphiti_project_dir).expanduser().resolve()
    if not project_dir.exists():
        raise FileNotFoundError(f"Graphiti news project dir not found: {project_dir}")

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
    if args.graphiti_api_base:
        env["CRAWLER_GRAPHITI_API_BASE"] = str(args.graphiti_api_base).rstrip("/")

    completed = subprocess.run(
        command,
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    summary = _parse_crawler_summary(completed.stdout)
    _validate_crawler_summary(summary, require_ingest=bool(args.ingest))
    return summary


def run(args: argparse.Namespace) -> dict[str, Any]:
    graphiti_preflight: dict[str, Any] | None = None
    crawler_summary: dict[str, Any] | None = None
    if args.run_crawler:
        if not args.skip_graphiti_preflight:
            graphiti_preflight = _ensure_graphiti_api_ready(args)
        crawler_summary = _run_graphiti_crawler(args)
        if args.group_id is None:
            args.group_id = str(
                crawler_summary.get("graphiti_group_id")
                or crawler_summary.get("run_id")
                or ""
            ) or None

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = GraphitiNewsFusionRunner()
    result = runner.run_from_graphiti_neo4j(
        graphiti_neo4j_uri=args.graphiti_neo4j_uri,
        graphiti_neo4j_user=args.graphiti_neo4j_user,
        graphiti_neo4j_password=args.graphiti_neo4j_password,
        graphiti_neo4j_database=args.graphiti_neo4j_database,
        group_id=args.group_id,
        limit=args.limit,
        edge_limit=args.edge_limit,
        wikidata_shard_dir=args.wikidata_shard_dir,
        batch_id=args.batch_id,
        project=args.project,
        namespace=args.namespace,
    )

    batch_payload = _model_dump_jsonable(result.batch)
    node_decisions = [_model_dump_jsonable(item) for item in result.node_decisions]
    relation_decisions = [_model_dump_jsonable(item) for item in result.relation_decisions]
    report = {
        "batch_id": args.batch_id,
        "node_count": result.batch.node_count(),
        "edge_count": result.batch.edge_count(),
        "node_decision_count": len(result.node_decisions),
        "relation_decision_count": len(result.relation_decisions),
        "warnings": result.warnings,
        "output_dir": str(output_dir),
        "graphiti_group_id": args.group_id,
        "graphiti_preflight": graphiti_preflight,
        "crawler_summary": crawler_summary,
    }

    batch_path = output_dir / "fusion_batch.json"
    _write_json(batch_path, batch_payload)
    _write_json(output_dir / "node_decisions.json", node_decisions)
    _write_json(output_dir / "relation_decisions.json", relation_decisions)
    _write_json(output_dir / "fusion_report.json", report)

    if args.openspg_live:
        importer = OpenSPGImporter(base_url=args.openspg_base_url, project_id=args.openspg_project_id)
        import_result = importer.import_batch(result.batch, dry_run=False)
        _write_json(output_dir / "openspg_import_result.json", _model_dump_jsonable(import_result))

    if args.import_neo4j:
        payload = build_import_payload(batch_payload)
        import_payload(
            payload,
            uri=args.target_neo4j_uri,
            user=args.target_neo4j_user,
            password=args.target_neo4j_password,
            database=args.target_neo4j_database,
            clear_batch_id=args.batch_id if args.clear_batch else None,
        )
        report["neo4j_imported"] = True
        _write_json(output_dir / "fusion_report.json", report)

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fuse Graphiti news graph output into the IncCore big graph.")
    parser.add_argument("--graphiti-project-dir", default=str(REPO_ROOT / "graphiti_news_pipeline"))
    parser.add_argument("--run-crawler", action="store_true", help="Run graphiti_news_pipeline crawler before fusion.")
    parser.add_argument("--crawler-command", default=os.getenv("GRAPHITI_NEWS_CRAWLER_COMMAND", sys.executable))
    parser.add_argument("--graphiti-api-base", default=os.getenv("CRAWLER_GRAPHITI_API_BASE", "http://127.0.0.1:8000/api"))
    parser.add_argument("--graphiti-api-timeout", type=int, default=int(os.getenv("GRAPHITI_NEWS_API_TIMEOUT_SECONDS", "60")))
    parser.add_argument("--skip-graphiti-preflight", action="store_true")
    parser.add_argument("--since-hours", type=int, default=24)
    parser.add_argument("--source", default=None)
    parser.add_argument("--max-items-per-source", type=int, default=20)
    parser.add_argument("--process-limit", type=int, default=300)
    parser.add_argument("--ingest", action="store_true", help="Pass --ingest to the Graphiti crawler.")

    parser.add_argument("--graphiti-neo4j-uri", default=os.getenv("GRAPHITI_NEWS_NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--graphiti-neo4j-user", default=os.getenv("GRAPHITI_NEWS_NEO4J_USER", "neo4j"))
    parser.add_argument("--graphiti-neo4j-password", default=os.getenv("GRAPHITI_NEWS_NEO4J_PASSWORD", "password123"))
    parser.add_argument("--graphiti-neo4j-database", default=os.getenv("GRAPHITI_NEWS_NEO4J_DATABASE") or None)
    parser.add_argument("--group-id", default=None)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--edge-limit", type=int, default=None)

    parser.add_argument("--wikidata-shard-dir", required=True)
    parser.add_argument("--batch-id", default=_default_batch_id())
    parser.add_argument("--project", default="IncCore")
    parser.add_argument("--namespace", default="IncCore")
    parser.add_argument("--output-dir", default=None)

    parser.add_argument("--openspg-live", action="store_true", help="Import the fusion batch into OpenSPG.")
    parser.add_argument("--openspg-base-url", default=os.getenv("OPENSPG_BASE_URL"))
    parser.add_argument("--openspg-project-id", type=int, default=os.getenv("OPENSPG_PROJECT_ID"))

    parser.add_argument("--import-neo4j", action="store_true", help="Import the fusion batch into Neo4j for visual inspection.")
    parser.add_argument("--target-neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--target-neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--target-neo4j-password", default=os.getenv("NEO4J_PASSWORD", "password123"))
    parser.add_argument("--target-neo4j-database", default=os.getenv("NEO4J_DATABASE") or None)
    parser.add_argument("--clear-batch", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.output_dir is None:
        args.output_dir = str(REPO_ROOT / "tmp" / "incore_fusion_runs" / args.batch_id)
    report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
