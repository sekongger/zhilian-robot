from __future__ import annotations

import logging
import os

from pymongo import ASCENDING, MongoClient

logger = logging.getLogger(__name__)


class MongoStore:
    def __init__(self):
        self.uri = os.getenv("CRAWLER_MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = os.getenv("CRAWLER_MONGODB_DATABASE", "graphiti_crawler")
        self.collection_name = os.getenv("CRAWLER_MONGODB_COLLECTION", "crawler_articles")
        self.run_collection_name = os.getenv("CRAWLER_MONGODB_RUN_COLLECTION", "crawler_runs")
        self._client: MongoClient | None = None
        self._db = None

    def connect(self) -> None:
        if self._db is not None:
            return
        self._client = MongoClient(self.uri)
        self._db = self._client[self.database_name]
        self._client.server_info()
        self.ensure_indexes()
        logger.info("Crawler MongoDB connected: db=%s collection=%s", self.database_name, self.collection_name)

    def ensure_indexes(self) -> None:
        articles = self.get_collection(self.collection_name)
        runs = self.get_collection(self.run_collection_name)
        articles.create_index([("article_id", ASCENDING)], unique=True, name="uk_article_id")
        articles.create_index([("status", ASCENDING)], name="idx_status")
        articles.create_index([("dedup_key", ASCENDING)], name="idx_dedup_key")
        articles.create_index([("title_dedup", ASCENDING), ("publish_day", ASCENDING)], name="idx_title_day")
        articles.create_index(
            [("content_signature", ASCENDING), ("publish_day", ASCENDING)],
            name="idx_content_sig_day",
        )
        articles.create_index([("canonical_url", ASCENDING)], name="idx_canonical_url")
        articles.create_index([("source_id", ASCENDING), ("publish_time_utc", ASCENDING)], name="idx_source_time")
        runs.create_index([("run_id", ASCENDING)], unique=True, name="uk_run_id")
        runs.create_index([("created_at", ASCENDING)], name="idx_run_created")

    def get_collection(self, name: str):
        if self._db is None:
            self.connect()
        return self._db[name]

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
