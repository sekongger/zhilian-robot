"""Backfill resource-layer fields for historical documents."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

from pymongo import MongoClient
from config.settings import settings
from app.news_pipeline.constants import SOURCE_NEWS_COLLECTION


DS_ID_PATTERN = re.compile(r"^DS_[A-Z]+_(\d{4})_(\d{3,})$")


def _normalize_name(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    return re.sub(r"\s+", "", str(value).strip().lower())


def _now() -> datetime:
    return datetime.utcnow()


def _format_ts(value: Optional[datetime]) -> str:
    if not value:
        value = _now()
    return value.strftime("%Y%m%d%H%M%S")


def _extract_year(value: Optional[datetime]) -> int:
    if not value:
        return _now().year
    return value.year


def _get_db():
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


def _build_existing_ds_index(db) -> Tuple[Dict[str, str], Dict[int, int]]:
    """Return (name->ds_id map, year->max_index map)."""
    name_map: Dict[str, str] = {}
    year_index: Dict[int, int] = {}
    for doc in db["ds_basic_info"].find({}, {"ds_id": 1, "name": 1}):
        ds_id = doc.get("ds_id")
        if ds_id:
            name_map[_normalize_name(doc.get("name"))] = ds_id
            match = DS_ID_PATTERN.match(ds_id)
            if match:
                year = int(match.group(1))
                index = int(match.group(2))
                year_index[year] = max(year_index.get(year, 0), index)
    return name_map, year_index


def _next_ds_id(year_index: Dict[int, int], year: int, ds_type: str) -> str:
    next_index = year_index.get(year, 0) + 1
    year_index[year] = next_index
    return f"DS_{ds_type}_{year}_{next_index:03d}"


def _ensure_ds_basic_info(db, ds_id: str, name: str, ds_type: str, ds_source: Optional[str]) -> None:
    collection = db["ds_basic_info"]
    existing = collection.find_one({"ds_id": ds_id}, {"_id": 1})
    if existing:
        return
    doc = {
        "ds_id": ds_id,
        "name": name or "未知数据源",
        "description": "历史数据回填生成",
        "credibility_score": 80.0,
        "metadata": {},
        "ds_type": ds_type,
        "data_category": "资讯",
        "ds_source": ds_source or "",
        "responsible_person": "系统",
        "create_time": _now(),
        "update_time": _now(),
        "is_valid": True,
    }
    collection.insert_one(doc)


def _resolve_ds_id(
    db,
    name_map: Dict[str, str],
    year_index: Dict[int, int],
    name: Optional[str],
    ds_source: Optional[str],
    year: int,
) -> str:
    key = _normalize_name(name)
    if key in name_map:
        return name_map[key]
    ds_id = _next_ds_id(year_index, year, "INTERNET")
    name_map[key] = ds_id
    _ensure_ds_basic_info(db, ds_id, name or "未知数据源", "INTERNET", ds_source)
    return ds_id


def _backfill_collection(db, collection_name: str, dry_run: bool) -> int:
    collection = db[collection_name]
    name_map, year_index = _build_existing_ds_index(db)
    updated = 0
    cursor = collection.find({"$or": [{"ds_id": {"$exists": False}}, {"status": {"$exists": False}}]})
    for doc in cursor:
        ds_id = doc.get("ds_id")
        source_name = doc.get("source_name") or doc.get("source") or doc.get("author")
        source_url = doc.get("source_url") or doc.get("url")
        time_value = doc.get("publish_time") or doc.get("crawl_time") or doc.get("created_at")
        year = _extract_year(time_value)
        if not ds_id:
            ds_id = _resolve_ds_id(db, name_map, year_index, source_name, source_url, year)
        task_id = doc.get("task_id") or f"TASK_{ds_id}_0001"
        task_runtime_id = doc.get("task_runtime_id") or f"RECORD_{task_id}_{_format_ts(time_value)}"
        status = doc.get("status") or doc.get("process_status") or "pending"

        update_fields = {}
        if not doc.get("ds_id"):
            update_fields["ds_id"] = ds_id
        if not doc.get("task_id"):
            update_fields["task_id"] = task_id
        if not doc.get("task_runtime_id"):
            update_fields["task_runtime_id"] = task_runtime_id
        if not doc.get("status"):
            update_fields["status"] = status

        if update_fields:
            updated += 1
            if not dry_run:
                collection.update_one({"_id": doc.get("_id")}, {"$set": update_fields})
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill ds_id/status for resource-layer collections.")
    parser.add_argument("--dry-run", action="store_true", help="Only report, do not write changes.")
    args = parser.parse_args()

    db = _get_db()
    targets = ["raw_documents", SOURCE_NEWS_COLLECTION, "crawled_articles"]
    total = 0
    for name in targets:
        updated = _backfill_collection(db, name, dry_run=args.dry_run)
        total += updated
        print(f"{name}: updated {updated} docs")
    print(f"total updated: {total}")
    if args.dry_run:
        print("dry-run only, no changes written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
