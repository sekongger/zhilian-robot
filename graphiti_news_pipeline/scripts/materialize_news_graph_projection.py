#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.news_graph_projection_service import NewsGraphProjectionService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize browser-friendly projected labels and relationships in the Graphiti news Neo4j graph.",
    )
    parser.add_argument("--group-id", default=None, help="Optional Graphiti group_id/fusion_batch_id scope.")
    parser.add_argument("--limit", type=int, default=5000, help="Max entities and source relationships to project.")
    parser.add_argument("--clear-existing", action="store_true", help="Delete existing projection layer before rebuilding.")
    parser.add_argument("--stats-only", action="store_true", help="Only print projection stats.")
    return parser.parse_args()


async def _run() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv()
    args = _parse_args()

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7689")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password123")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        service = NewsGraphProjectionService(driver)
        if args.stats_only:
            payload = await service.projection_stats(group_id=args.group_id)
        else:
            payload = await service.materialize_projection(
                group_id=args.group_id,
                limit=args.limit,
                clear_existing=args.clear_existing,
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(_run())
