from __future__ import annotations

import argparse
import asyncio
import os

from neo4j import AsyncGraphDatabase


def _env_required(name: str) -> str:
    value = str(os.getenv(name, "")).strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


async def main() -> None:
    uri = _env_required("NEO4J_URI")
    user = _env_required("NEO4J_USER")
    password = _env_required("NEO4J_PASSWORD")
    parser = argparse.ArgumentParser(description="Verify basic v2 schema migration results.")
    parser.add_argument("--sample", type=int, default=20)
    parser.parse_args()

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        query = """
        MATCH (n)
        RETURN labels(n) AS labels, count(*) AS cnt
        ORDER BY cnt DESC
        LIMIT 50
        """
        records, _, _ = await driver.execute_query(query)
        for record in records:
            print(record["labels"], record["cnt"])
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
