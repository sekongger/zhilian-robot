from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from neo4j import AsyncGraphDatabase


@dataclass
class MigrationConfig:
    dry_run: bool
    batch_size: int
    limit: int | None


LABEL_MIGRATIONS: list[tuple[str, str]] = [
    ("Company", "Enterprise"),
    ("ProductObject", "Product"),
    ("IndustryNode", "Industry"),
]


PROPERTY_MIGRATIONS: list[tuple[str, str]] = [
    ("foundedDate", "inception"),
    ("website", "officialWebsite"),
    ("eduDgree", "eduDegree"),
]


EVENT_LABEL_MIGRATIONS: list[tuple[str, str]] = [
    ("CompanyFinancingEvent", "EnterpriseEvent"),
    ("CompanyCooperationEvent", "EnterpriseEvent"),
    ("GovernmentPublishPolicyEvent", "OrganizationEvent"),
]


def _env_required(name: str) -> str:
    value = str(os.getenv(name, "")).strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _count_nodes_with_label(driver, label: str) -> int:
    query = f"MATCH (n:{label}) RETURN count(n) AS count"
    records, _, _ = await driver.execute_query(query)
    return int(records[0]["count"] or 0) if records else 0


async def _migrate_label(driver, old_label: str, new_label: str, cfg: MigrationConfig) -> int:
    if cfg.dry_run:
        return await _count_nodes_with_label(driver, old_label)

    query = f"""
    MATCH (n:{old_label})
    {"WITH n LIMIT $limit" if cfg.limit else ""}
    SET n:{new_label}
    REMOVE n:{old_label}
    SET n._schema_migrated_at = $migrated_at
    RETURN count(n) AS migrated
    """
    params = {"migrated_at": _now_iso()}
    if cfg.limit:
        params["limit"] = int(cfg.limit)
    records, _, _ = await driver.execute_query(query, **params)
    return int(records[0]["migrated"] or 0) if records else 0


async def _migrate_property(driver, old_prop: str, new_prop: str, cfg: MigrationConfig) -> int:
    base_match = f"MATCH (n) WHERE n.{old_prop} IS NOT NULL AND n.{new_prop} IS NULL"
    if cfg.dry_run:
        query = f"{base_match} RETURN count(n) AS count"
        records, _, _ = await driver.execute_query(query)
        return int(records[0]["count"] or 0) if records else 0

    query = f"""
    {base_match}
    {"WITH n LIMIT $limit" if cfg.limit else ""}
    SET n.{new_prop} = n.{old_prop}
    SET n._schema_migrated_at = $migrated_at
    RETURN count(n) AS migrated
    """
    params = {"migrated_at": _now_iso()}
    if cfg.limit:
        params["limit"] = int(cfg.limit)
    records, _, _ = await driver.execute_query(query, **params)
    return int(records[0]["migrated"] or 0) if records else 0


async def _mark_legacy_event_kind(driver, old_label: str, cfg: MigrationConfig) -> int:
    if cfg.dry_run:
        return await _count_nodes_with_label(driver, old_label)

    query = f"""
    MATCH (e:{old_label})
    {"WITH e LIMIT $limit" if cfg.limit else ""}
    SET e.legacy_event_kind = $old_label
    SET e._schema_migrated_at = $migrated_at
    RETURN count(e) AS migrated
    """
    params = {"old_label": old_label, "migrated_at": _now_iso()}
    if cfg.limit:
        params["limit"] = int(cfg.limit)
    records, _, _ = await driver.execute_query(query, **params)
    return int(records[0]["migrated"] or 0) if records else 0


async def run_migration(cfg: MigrationConfig) -> None:
    uri = _env_required("NEO4J_URI")
    user = _env_required("NEO4J_USER")
    password = _env_required("NEO4J_PASSWORD")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        print(f"[schema-migrate] start dry_run={cfg.dry_run} batch_size={cfg.batch_size} limit={cfg.limit}")

        for old_label, new_label in LABEL_MIGRATIONS:
            count = await _migrate_label(driver, old_label, new_label, cfg)
            mode = "would_migrate" if cfg.dry_run else "migrated"
            print(f"[label] {old_label} -> {new_label}: {mode}={count}")

        for old_prop, new_prop in PROPERTY_MIGRATIONS:
            count = await _migrate_property(driver, old_prop, new_prop, cfg)
            mode = "would_migrate" if cfg.dry_run else "migrated"
            print(f"[property] {old_prop} -> {new_prop}: {mode}={count}")

        for old_event, new_event in EVENT_LABEL_MIGRATIONS:
            legacy_count = await _mark_legacy_event_kind(driver, old_event, cfg)
            relabeled_count = await _migrate_label(driver, old_event, new_event, cfg)
            mode = "would_migrate" if cfg.dry_run else "migrated"
            print(
                f"[event] {old_event} -> {new_event}: {mode}={relabeled_count}, "
                f"legacy_marked={legacy_count}"
            )

        print("[schema-migrate] done")
    finally:
        await driver.close()


def parse_args() -> MigrationConfig:
    parser = argparse.ArgumentParser(description="Migrate graph schema from v1 to v2 labels/properties.")
    parser.add_argument("--dry-run", action="store_true", help="Only count affected records; do not write.")
    parser.add_argument("--batch-size", type=int, default=1000, help="Reserved for future chunked execution.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max records per migration statement.")
    args = parser.parse_args()
    return MigrationConfig(
        dry_run=bool(args.dry_run),
        batch_size=max(1, int(args.batch_size)),
        limit=args.limit if args.limit is None else max(1, int(args.limit)),
    )


if __name__ == "__main__":
    config = parse_args()
    asyncio.run(run_migration(config))
