from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ReturnDocument

from crawler.domain.enums import ArticleStatus
from crawler.domain.models import ArticleRecord
from crawler.storage.mongo_store import MongoStore


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ACTIVE_DEDUP_STATUSES = {
    ArticleStatus.DEDUP_PASSED.value,
    ArticleStatus.COMPRESSED.value,
    ArticleStatus.INGESTED.value,
}


class ArticleRepository:
    def __init__(self, store: MongoStore):
        self.store = store
        self.collection = store.get_collection(store.collection_name)
        self.run_collection = store.get_collection(store.run_collection_name)

    def upsert_fetched_articles(self, records: list[ArticleRecord]) -> dict[str, int]:
        inserted = 0
        touched = 0
        for record in records:
            now = utcnow()
            result = self.collection.update_one(
                {"article_id": record.article_id},
                {
                    "$setOnInsert": {
                        "article_id": record.article_id,
                        "status": record.status.value,
                        "attempt_count": record.attempt_count,
                        "content_clean": record.content_clean,
                        "relevance_score": record.relevance_score,
                        "matched_keywords": record.matched_keywords,
                        "dedup_key": record.dedup_key,
                        "title_dedup": None,
                        "publish_day": None,
                        "content_signature": None,
                        "compressed_text": None,
                        "compressed_structured": None,
                        "compress_error": record.compress_error,
                        "ingest_error": None,
                        "graphiti_episode_uuid": None,
                        "created_at": now,
                    },
                    "$set": {
                        "title": record.title,
                        "content_raw": record.content_raw,
                        "canonical_url": record.canonical_url,
                        "publish_time_utc": record.publish_time_utc,
                        "source_name": record.source_name,
                        "source_url": record.source_url,
                        "source_id": record.source_id,
                        "crawled_at_utc": record.crawled_at_utc,
                        "updated_at": now,
                    },
                },
                upsert=True,
            )
            touched += 1
            if result.upserted_id is not None:
                inserted += 1
        return {"total": len(records), "inserted": inserted, "touched": touched}

    def list_by_status(self, statuses: list[str], limit: int) -> list[dict[str, Any]]:
        cursor = self.collection.find({"status": {"$in": statuses}}).sort("updated_at", 1).limit(limit)
        return list(cursor)

    def update_article(self, article_id: str, fields: dict[str, Any]) -> None:
        self.collection.update_one(
            {"article_id": article_id},
            {"$set": {**fields, "updated_at": utcnow()}},
            upsert=False,
        )

    def increment_attempt(self, article_id: str) -> int:
        doc = self.collection.find_one_and_update(
            {"article_id": article_id},
            {"$inc": {"attempt_count": 1}, "$set": {"updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        return int((doc or {}).get("attempt_count", 0))

    def has_duplicate(self, dedup_key: str, article_id: str) -> bool:
        query = {
            "dedup_key": dedup_key,
            "article_id": {"$ne": article_id},
            "status": {"$in": list(ACTIVE_DEDUP_STATUSES)},
        }
        return self.collection.find_one(query, {"article_id": 1}) is not None

    def has_duplicate_by_title_day(self, title_dedup: str, publish_day: str, article_id: str) -> bool:
        query = {
            "title_dedup": title_dedup,
            "publish_day": publish_day,
            "article_id": {"$ne": article_id},
            "status": {"$in": list(ACTIVE_DEDUP_STATUSES)},
        }
        return self.collection.find_one(query, {"article_id": 1}) is not None

    def has_duplicate_by_content_signature(
        self,
        content_signature: str,
        publish_day: str,
        article_id: str,
    ) -> bool:
        query = {
            "content_signature": content_signature,
            "publish_day": publish_day,
            "article_id": {"$ne": article_id},
            "status": {"$in": list(ACTIVE_DEDUP_STATUSES)},
        }
        return self.collection.find_one(query, {"article_id": 1}) is not None

    def has_unprocessed_article(self, article_id: str) -> bool:
        query = {
            "article_id": article_id,
            "status": {"$nin": [ArticleStatus.INGESTED.value]},
        }
        return self.collection.find_one(query, {"article_id": 1}) is not None

    def article_exists(self, article_id: str) -> bool:
        return self.collection.find_one({"article_id": article_id}, {"article_id": 1}) is not None

    def count_by_status(self, status: str) -> int:
        return self.collection.count_documents({"status": status})

    def write_run_log(self, run_doc: dict[str, Any]) -> None:
        self.run_collection.update_one(
            {"run_id": run_doc["run_id"]},
            {"$set": run_doc},
            upsert=True,
        )
