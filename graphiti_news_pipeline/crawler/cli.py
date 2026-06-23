from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from crawler.observability.logger import setup_logging


def _build_orchestrator():
    # Lazy imports keep `python -m crawler.cli --help` usable before deps installation.
    from crawler.connectors.source_registry import load_pipeline_config, load_sources
    from crawler.pipeline.context import PipelineContext
    from crawler.pipeline.orchestrator import CrawlerOrchestrator
    from crawler.services.compression_service import LLMCompressor
    from crawler.services.ingest_service import GraphitiIngestClient
    from crawler.storage.mongo_store import MongoStore
    from crawler.storage.repositories import ArticleRepository

    root = Path(__file__).resolve().parent
    sources = load_sources(root / "config" / "sources.yaml")
    config = load_pipeline_config(root / "config" / "pipeline.yaml")
    store = MongoStore()
    repository = ArticleRepository(store)
    context = PipelineContext(
        config=config,
        sources=sources,
        repository=repository,
        compressor=LLMCompressor(),
        ingest_client=GraphitiIngestClient(),
    )
    return CrawlerOrchestrator(context), store


def _persist_run_summary(summary: dict) -> Path:
    run_dir = Path(os.getenv("CRAWLER_RUN_DIR", "var/crawler/runs"))
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = str(summary.get("run_id") or datetime.now(timezone.utc).strftime("crawl_%Y%m%d%H%M%S"))
    output_path = run_dir / f"{run_id}.json"
    summary["run_output_path"] = str(output_path)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    return output_path


def _parse_day_start_utc(value: str) -> datetime:
    parsed = datetime.strptime(value.strip(), "%Y-%m-%d")
    return parsed.replace(tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0)


def _parse_day_end_utc(value: str) -> datetime:
    parsed = datetime.strptime(value.strip(), "%Y-%m-%d")
    return parsed.replace(tzinfo=timezone.utc, hour=23, minute=59, second=59, microsecond=999999)


def parse_args() -> argparse.Namespace:
    default_since_hours = int(os.getenv("CRAWLER_DEFAULT_SINCE_HOURS", "24"))
    parser = argparse.ArgumentParser(description="Robotics crawler CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_once = sub.add_parser("run-once", help="Fetch + process in one run.")
    run_once.add_argument("--since-hours", type=int, default=default_since_hours)
    run_once.add_argument("--source", type=str, default=None)
    run_once.add_argument("--max-items-per-source", type=int, default=50)
    run_once.add_argument("--process-limit", type=int, default=300)
    run_once.add_argument("--ingest", action="store_true")

    crawl = sub.add_parser("crawl", help="Fetch only.")
    crawl.add_argument("--since-hours", type=int, default=default_since_hours)
    crawl.add_argument("--source", type=str, default=None)
    crawl.add_argument("--max-items-per-source", type=int, default=50)

    compress = sub.add_parser("compress", help="Normalize/relevance/dedup/compress only.")
    compress.add_argument("--process-limit", type=int, default=300)

    ingest = sub.add_parser("ingest", help="Ingest compressed records.")
    ingest.add_argument("--process-limit", type=int, default=300)

    retry = sub.add_parser("retry", help="Retry failed compression/ingest records.")
    retry.add_argument(
        "--status",
        type=str,
        default="ALL",
        choices=["ALL", "COMPRESS_FAILED", "INGEST_FAILED"],
    )
    retry.add_argument("--process-limit", type=int, default=300)
    retry.add_argument("--ingest", action="store_true")

    backfill = sub.add_parser("backfill", help="Backfill by date range (UTC day).")
    backfill.add_argument("--from", dest="from_date", required=True, type=str, help="YYYY-MM-DD")
    backfill.add_argument("--to", dest="to_date", required=True, type=str, help="YYYY-MM-DD")
    backfill.add_argument("--source", type=str, default=None)
    backfill.add_argument("--max-items-per-source", type=int, default=100)
    backfill.add_argument("--process-limit", type=int, default=500)
    backfill.add_argument("--ingest", action="store_true")

    return parser.parse_args()


def main() -> int:
    setup_logging()
    args = parse_args()
    orchestrator, store = _build_orchestrator()
    try:
        if args.command == "run-once":
            result = orchestrator.run_once(
                since_hours=args.since_hours,
                source_filter=args.source,
                max_items_per_source=args.max_items_per_source,
                process_limit=args.process_limit,
                enable_ingest=args.ingest,
            )
        elif args.command == "crawl":
            result = orchestrator.run_crawl_only(
                since_hours=args.since_hours,
                source_filter=args.source,
                max_items_per_source=args.max_items_per_source,
            )
        elif args.command == "compress":
            result = orchestrator.run_compress_only(process_limit=args.process_limit)
        elif args.command == "ingest":
            result = orchestrator.run_ingest_only(process_limit=args.process_limit)
        elif args.command == "retry":
            result = orchestrator.run_retry(
                retry_status=args.status,
                process_limit=args.process_limit,
                enable_ingest=args.ingest,
            )
        elif args.command == "backfill":
            from_utc = _parse_day_start_utc(args.from_date)
            to_utc = _parse_day_end_utc(args.to_date)
            if from_utc > to_utc:
                raise ValueError("--from must be <= --to")
            result = orchestrator.run_backfill(
                from_utc=from_utc,
                to_utc=to_utc,
                source_filter=args.source,
                max_items_per_source=args.max_items_per_source,
                process_limit=args.process_limit,
                enable_ingest=args.ingest,
            )
        else:
            raise ValueError(f"Unsupported command: {args.command}")

        _persist_run_summary(result)
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
