"""Data access layer for the news pipeline (MongoDB)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId
import hashlib
from app.database.mongodb import mongodb_conn
from .constants import (
    SOURCE_NEWS_COLLECTION,
    ENTITY_COLLECTION,
    STATEMENT_COLLECTION,
    EVIDENCE_COLLECTION,
    KG_INPUT_QUEUE_COLLECTION,
)


class NewsPipelineRepository:
    """Repository wrapping MongoDB access for pipeline collections."""

    def __init__(self):
        self.db = mongodb_conn

    def create_source_news(self, payload: Dict[str, Any]) -> str:
        doc_id = payload.get("doc_id") or self._generate_doc_id(payload)
        doc_hash = payload.get("doc_hash") or self._generate_doc_hash(payload)
        doc_type = payload.get("doc_type") or "news"
        ds_id = payload.get("ds_id") or f"DS_MANUAL_{datetime.utcnow().strftime('%Y%m%d')}"
        task_id = payload.get("task_id") or f"TASK_{ds_id}_0001"
        task_runtime_id = payload.get("task_runtime_id") or f"RECORD_{task_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        status = payload.get("status") or payload.get("process_status") or "pending"
        document = {
            **payload,
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "doc_type": doc_type,
            "ds_id": ds_id,
            "task_id": task_id,
            "task_runtime_id": task_runtime_id,
            "quality_score": payload.get("quality_score", 1.0),
            "process_status": payload.get("process_status", "pending"),
            "fetch_time": payload.get("fetch_time", datetime.utcnow()),
            "created_at": payload.get("created_at", datetime.utcnow()),
            "updated_at": payload.get("updated_at", datetime.utcnow()),
        }
        raw_document = {
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "doc_type": doc_type,
            "title": payload.get("title"),
            "content": payload.get("content"),
            "url": payload.get("source_url"),
            "source_name": payload.get("source_name"),
            "source_url": payload.get("source_url"),
            "ds_id": ds_id,
            "task_id": task_id,
            "task_runtime_id": task_runtime_id,
            "publish_time": payload.get("publish_time"),
            "crawl_time": payload.get("fetch_time", datetime.utcnow()),
            "status": status,
            "process_status": payload.get("process_status", "pending"),
            "created_at": payload.get("created_at", datetime.utcnow()),
            "updated_at": payload.get("updated_at", datetime.utcnow()),
        }
        # 原始文档保真存储（按doc_hash去重）
        self.db.update_one(
            "raw_documents",
            {"doc_hash": doc_hash},
            {"$setOnInsert": raw_document},
            upsert=True,
        )
        result = self.db.insert_one(SOURCE_NEWS_COLLECTION, document)
        return str(result.inserted_id)

    def get_source_news(self, news_id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(news_id):
            return None
        doc = self.db.find_one(SOURCE_NEWS_COLLECTION, {"_id": ObjectId(news_id)})
        if not doc:
            return None
        return self._normalize_doc(doc)

    def list_source_news(self, query: Dict[str, Any], limit: int, offset: int) -> List[Dict[str, Any]]:
        sort = [("publish_time", -1), ("created_at", -1)]
        collection = self.db.get_collection(SOURCE_NEWS_COLLECTION)
        cursor = collection.find(query).sort(sort).skip(offset).limit(limit)
        results = []
        for doc in cursor:
            results.append(self._normalize_doc(doc))
        return results

    def list_pending_news_ids(self, limit: int = 10) -> List[str]:
        collection = self.db.get_collection(SOURCE_NEWS_COLLECTION)
        cursor = collection.find({"process_status": "pending"}).sort([("created_at", 1)]).limit(limit)
        return [str(doc.get("_id")) for doc in cursor]

    def count_source_news(self, query: Dict[str, Any]) -> int:
        collection = self.db.get_collection(SOURCE_NEWS_COLLECTION)
        return collection.count_documents(query)

    def update_source_news(self, news_id: str, update_fields: Dict[str, Any]) -> None:
        if not ObjectId.is_valid(news_id):
            return
        update_doc = {"$set": {**update_fields, "updated_at": datetime.utcnow()}}
        self.db.update_one(SOURCE_NEWS_COLLECTION, {"_id": ObjectId(news_id)}, update_doc)

    def ensure_source_news_from_crawled_article(self, article_doc: Dict[str, Any], external_id: str | None = None) -> Dict[str, Any]:
        doc_hash = article_doc.get("doc_hash") or self._generate_doc_hash(article_doc)
        doc_id = article_doc.get("doc_id") or self._generate_doc_id(article_doc)
        query_parts = [{"doc_hash": doc_hash}]
        if external_id:
            query_parts.append(
                {
                    "external_ref.collection": "crawled_articles",
                    "external_ref.id": external_id,
                }
            )
        existing = self.db.find_one(SOURCE_NEWS_COLLECTION, {"$or": query_parts})
        if existing:
            return self._normalize_doc(existing)

        payload = {
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "doc_type": "news",
            "title": article_doc.get("title") or "未命名资讯",
            "content": article_doc.get("content") or article_doc.get("summary") or "",
            "summary": article_doc.get("summary"),
            "source_name": article_doc.get("source_name") or article_doc.get("source"),
            "source_url": article_doc.get("source_url") or article_doc.get("url"),
            "publish_time": article_doc.get("published_at") or article_doc.get("publish_time"),
            "fetch_time": article_doc.get("crawled_at") or datetime.utcnow(),
            "source_id": article_doc.get("source_id") or f"SRC_{(article_doc.get('source') or 'crawler')}_{doc_id[-6:]}",
            "process_status": "pending",
            "external_ref": {
                "collection": "crawled_articles",
                "id": external_id,
            },
        }
        news_id = self.create_source_news(payload)
        return self.get_source_news(news_id) or {"id": news_id, **payload}

    def import_from_crawled_articles(self, limit: int = 50) -> Dict[str, int]:
        collection = self.db.get_collection("crawled_articles")
        cursor = collection.find({}).sort([("crawled_at", -1)]).limit(limit)

        imported = 0
        skipped = 0
        for doc in cursor:
            external_id = str(doc.get("_id"))
            doc_id = doc.get("doc_id") or self._generate_doc_id(doc)
            doc_hash = doc.get("doc_hash") or self._generate_doc_hash(doc)
            existing = self.db.find_one(
                SOURCE_NEWS_COLLECTION,
                {
                    "$or": [
                        {"external_ref.id": external_id, "external_ref.collection": "crawled_articles"},
                        {"doc_hash": doc_hash},
                    ]
                },
            )
            if existing:
                skipped += 1
                continue

            payload = {
                "doc_id": doc_id,
                "doc_hash": doc_hash,
                "doc_type": "news",
                "title": doc.get("title") or "未命名资讯",
                "content": doc.get("content") or doc.get("summary") or "",
                "summary": doc.get("summary"),
                "source_name": doc.get("source") or doc.get("source_name"),
                "source_url": doc.get("url") or doc.get("source_url"),
                "publish_time": doc.get("publish_time"),
                "source_id": f"SRC_{doc.get('source','crawler')}_{external_id[-6:]}",
                "ds_id": doc.get("ds_id") or f"DS_CRAWLER_{datetime.utcnow().strftime('%Y%m%d')}",
                "task_id": doc.get("task_id") or f"TASK_DS_CRAWLER_{datetime.utcnow().strftime('%Y%m%d')}_0001",
                "task_runtime_id": doc.get("task_runtime_id")
                or f"RECORD_TASK_DS_CRAWLER_{datetime.utcnow().strftime('%Y%m%d')}_0001_{datetime.utcnow().strftime('%H%M%S')}",
                "process_status": "pending",
                "external_ref": {
                    "collection": "crawled_articles",
                    "id": external_id,
                },
            }
            # raw_documents 保真写入（按doc_hash去重）
            raw_document = {
                "doc_id": doc_id,
                "doc_hash": doc_hash,
                "doc_type": "news",
                "title": doc.get("title") or "未命名资讯",
                "content": doc.get("content") or doc.get("summary") or "",
                "url": doc.get("url") or doc.get("source_url"),
                "source_name": doc.get("source") or doc.get("source_name"),
                "source_url": doc.get("url") or doc.get("source_url"),
                "ds_id": payload.get("ds_id"),
                "task_id": payload.get("task_id"),
                "task_runtime_id": payload.get("task_runtime_id"),
                "publish_time": doc.get("publish_time"),
                "crawl_time": doc.get("crawled_at") or doc.get("crawl_time"),
                "status": "pending",
                "process_status": "pending",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            self.db.update_one(
                "raw_documents",
                {"doc_hash": doc_hash},
                {"$setOnInsert": raw_document},
                upsert=True,
            )
            self.create_source_news(payload)
            if not doc.get("doc_id") or not doc.get("doc_hash"):
                collection.update_one(
                    {"_id": doc.get("_id")},
                    {"$set": {"doc_id": doc_id, "doc_hash": doc_hash}},
                )
            imported += 1

        return {"imported": imported, "skipped": skipped}

    def _normalize_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
            doc.pop("_id", None)
        return doc

    def upsert_entity(self, entity_doc: Dict[str, Any]) -> str:
        entity_id = entity_doc.get("entity_id") or entity_doc.get("id")
        if entity_id:
            existing = self.db.find_one(ENTITY_COLLECTION, {"_id": entity_id})
        else:
            query = {
                "canonical_name": entity_doc.get("canonical_name"),
                "entity_category": entity_doc.get("entity_category"),
            }
            existing = self.db.find_one(ENTITY_COLLECTION, query)
        if existing:
            entity_id = existing.get("entity_id") or existing.get("id") or existing.get("_id")
            self.db.update_one(
                ENTITY_COLLECTION,
                {"_id": existing.get("_id")},
                {"$set": {"updated_at": datetime.utcnow()}},
            )
            return str(entity_id)

        entity_id = entity_id or entity_doc.get("id")
        entity_doc = {
            **entity_doc,
            "_id": entity_id,
            "entity_id": entity_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        self.db.insert_one(ENTITY_COLLECTION, entity_doc)
        return str(entity_id)

    def create_statement(self, statement_doc: Dict[str, Any]) -> str:
        statement_hash = statement_doc.get("statement_hash") or self._generate_statement_hash(statement_doc)
        statement_id = f"ST{statement_hash[:16]}"
        now = datetime.utcnow()
        statement_doc = {
            **statement_doc,
            "statement_id": statement_id,
            "statement_hash": statement_hash,
            "created_at": statement_doc.get("created_at") or now,
            "updated_at": now,
        }

        collection = self.db.get_collection(STATEMENT_COLLECTION)
        existing = collection.find_one({"statement_hash": statement_hash}, {"_id": 1, "statement_id": 1})
        if existing:
            existing_id = existing.get("statement_id") or existing.get("_id")
            collection.update_one(
                {"_id": existing.get("_id")},
                {"$set": statement_doc},
            )
            return str(existing_id)

        self.db.update_one(
            STATEMENT_COLLECTION,
            {"_id": statement_id},
            {"$set": statement_doc},
            upsert=True,
        )
        return str(statement_id)

    def create_evidence(self, evidence_doc: Dict[str, Any]) -> str:
        """写入Statement证据记录。"""
        evidence_doc = {
            **evidence_doc,
            "created_at": datetime.utcnow(),
        }
        result = self.db.insert_one(EVIDENCE_COLLECTION, evidence_doc)
        return str(result.inserted_id)

    def enqueue_kg_input(self, queue_doc: Dict[str, Any]) -> str:
        queue_id = queue_doc.get("queue_id") or f"KGQ_{self._generate_doc_hash(queue_doc).split(':', 1)[-1][:16]}"
        payload = {
            **queue_doc,
            "queue_id": queue_id,
            "status": queue_doc.get("status") or "pending",
            "created_at": queue_doc.get("created_at") or datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        self.db.update_one(
            KG_INPUT_QUEUE_COLLECTION,
            {"queue_id": queue_id},
            {"$set": payload},
            upsert=True,
        )
        return queue_id

    def list_kg_input_queue(self, *, kg_name: str = "news_kg", status: str | None = "pending", limit: int = 50) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"kg_name": kg_name}
        if status:
            query["status"] = status
        results = self.db.find_many(
            KG_INPUT_QUEUE_COLLECTION,
            query=query,
            limit=limit,
            sort=[("created_at", 1)],
        )
        return [self._normalize_doc(doc) for doc in results]

    def update_kg_input(self, queue_id: str, update_fields: Dict[str, Any]) -> None:
        self.db.update_one(
            KG_INPUT_QUEUE_COLLECTION,
            {"queue_id": queue_id},
            {"$set": {**update_fields, "updated_at": datetime.utcnow()}},
            upsert=False,
        )

    def get_entities_by_ids(self, entity_ids: List[str]) -> List[Dict[str, Any]]:
        collection = self.db.get_collection(ENTITY_COLLECTION)
        results = list(collection.find({"_id": {"$in": entity_ids}}))
        return [self._normalize_doc(doc) for doc in results]

    def get_statements_by_ids(self, statement_ids: List[str]) -> List[Dict[str, Any]]:
        object_ids = []
        for sid in statement_ids:
            if ObjectId.is_valid(sid):
                object_ids.append(ObjectId(sid))
            else:
                object_ids.append(sid)
        collection = self.db.get_collection(STATEMENT_COLLECTION)
        results = list(collection.find({"_id": {"$in": object_ids}}))
        return [self._normalize_doc(doc) for doc in results]

    def get_statements_by_source_news(self, news_id: str) -> List[Dict[str, Any]]:
        collection = self.db.get_collection(STATEMENT_COLLECTION)
        results = list(collection.find({"source_news_id": news_id}))
        return [self._normalize_doc(doc) for doc in results]

    def get_statements_by_doc_id(self, doc_id: str) -> List[Dict[str, Any]]:
        collection = self.db.get_collection(STATEMENT_COLLECTION)
        results = list(collection.find({"doc_id": doc_id}))
        return [self._normalize_doc(doc) for doc in results]

    def _generate_statement_hash(self, statement_doc: Dict[str, Any]) -> str:
        key_parts = [
            statement_doc.get("subject_id"),
            statement_doc.get("predicate_id"),
            statement_doc.get("object_entity_id") or statement_doc.get("object_value"),
            statement_doc.get("doc_id"),
            statement_doc.get("context_time_value"),
            statement_doc.get("context_space_value"),
            statement_doc.get("context_source_id"),
            statement_doc.get("context_version_id"),
            statement_doc.get("context_scenario"),
        ]
        key = "|".join([str(part or "") for part in key_parts])
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _generate_doc_hash(self, payload: Dict[str, Any]) -> str:
        title = (payload.get("title") or "").strip()
        content = (payload.get("content") or payload.get("summary") or "").strip()
        source_url = (payload.get("source_url") or payload.get("url") or "").strip()
        publish_time = payload.get("publish_time") or ""
        key = f"{title}|{content}|{source_url}|{publish_time}"
        return f"sha256:{hashlib.sha256(key.encode('utf-8')).hexdigest()}"

    def _generate_doc_id(self, payload: Dict[str, Any]) -> str:
        doc_hash = self._generate_doc_hash(payload)
        return f"doc:{doc_hash.split(':', 1)[-1][:12]}"
