"""News pipeline orchestration service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import hashlib
import re
from bson import ObjectId

from .constants import (
    ENTITY_CATEGORY_MAP,
    ENTITY_TYPE_MAP,
    ENTITY_CLASS_MAP,
    PREDICATE_MAP,
    DEFAULT_EXTRACTION_METHOD,
)
from .repository import NewsPipelineRepository
from .extractor import NewsPipelineExtractor

logger = logging.getLogger(__name__)


class NewsPipelineService:
    """Service to process news and persist knowledge."""

    def __init__(self):
        self.repo = NewsPipelineRepository()
        self.extractor = NewsPipelineExtractor()

    def process_news(self, news_id: str) -> Dict[str, Any]:
        news = self.repo.get_source_news(news_id)
        if not news:
            return {"success": False, "error": "news_not_found"}

        if news.get("process_status") == "processing":
            return {"success": False, "error": "already_processing"}

        if not news.get("doc_id"):
            news["doc_id"] = self._generate_doc_id(news)
            self.repo.update_source_news(news_id, {"doc_id": news["doc_id"]})
        if not news.get("doc_hash"):
            doc_hash = self._generate_doc_hash(news)
            self.repo.update_source_news(news_id, {"doc_hash": doc_hash})
            news["doc_hash"] = doc_hash

        self.repo.update_source_news(news_id, {"process_status": "processing"})

        content = self._build_content(news)
        extraction = self.extractor.extract(content)

        document_entity_id = self._create_document_entity(news)
        entity_map = self._create_entities(extraction.get("entities", {}))

        statements = self._create_statements(
            news_id,
            news,
            extraction,
            entity_map,
            document_entity_id,
        )
        self._enqueue_for_kg(
            news_id=news_id,
            news=news,
            extraction=extraction,
            statements=statements,
        )

        process_result = {
            "entities": sum(len(v) for v in extraction.get("entities", {}).values()),
            "relations": len(extraction.get("relations", [])),
            "statements": len(statements),
            "model": extraction.get("model"),
        }

        update_payload = {
            "process_status": "completed",
            "process_result": process_result,
            "processed_at": datetime.utcnow(),
        }
        if not news.get("summary") and extraction.get("summary"):
            update_payload["summary"] = extraction.get("summary")
        self.repo.update_source_news(news_id, update_payload)
        # 同步更新原始文档状态（raw_documents）
        try:
            if news.get("doc_id"):
                self.repo.db.update_one(
                    "raw_documents",
                    {"doc_id": news.get("doc_id")},
                    {"$set": {"process_status": "completed", "updated_at": datetime.utcnow()}},
                )
        except Exception:
            pass

        return {
            "success": True,
            "news_id": news_id,
            "process_result": process_result,
        }

    def get_news_knowledge(self, news_id: str) -> Dict[str, Any]:
        news = self.repo.get_source_news(news_id)
        statements = self.repo.get_statements_by_source_news(news_id)
        if not statements and news and news.get("doc_id"):
            statements = self.repo.get_statements_by_doc_id(news.get("doc_id"))
        entity_ids = self._collect_entity_ids(statements)
        entities = self.repo.get_entities_by_ids(entity_ids)

        return {
            "entities": entities,
            "statements": statements,
            "contexts": [],
        }

    def get_news_provenance(self, news_id: str) -> List[Dict[str, Any]]:
        news = self.repo.get_source_news(news_id)
        statements = self.repo.get_statements_by_source_news(news_id)
        if not statements and news and news.get("doc_id"):
            statements = self.repo.get_statements_by_doc_id(news.get("doc_id"))

        provenance = []
        for stmt in statements:
            context = {
                "source_name": news.get("source_name") if news else None,
                "source_url": stmt.get("source_url"),
                "confidence": stmt.get("confidence"),
                "audit_status": stmt.get("audit_status"),
                "context_time_value": stmt.get("context_time_value"),
                "context_space_value": stmt.get("context_space_value"),
                "context_source_id": stmt.get("context_source_id"),
                "context_version_id": stmt.get("context_version_id"),
                "context_scenario": stmt.get("context_scenario"),
            }
            provenance.append({
                "statement": stmt,
                "context": context,
            })
        return provenance

    def process_pending_news(self, limit: int = 10) -> Dict[str, Any]:
        limit = min(max(limit, 1), 10)
        pending_ids = self.repo.list_pending_news_ids(limit)
        results = []
        success = 0
        failed = 0
        for news_id in pending_ids:
            result = self.process_news(news_id)
            results.append({"news_id": news_id, "result": result})
            if result.get("success"):
                success += 1
            else:
                failed += 1
        return {
            "success": True,
            "processed": success,
            "failed": failed,
            "total": len(pending_ids),
            "details": results,
        }

    def process_crawled_article(self, article_doc: Dict[str, Any], external_id: str | None = None) -> Dict[str, Any]:
        source_news = self.repo.ensure_source_news_from_crawled_article(article_doc, external_id=external_id)
        news_id = str(source_news.get("id") or source_news.get("_id") or "")
        result = self.process_news(news_id)
        if external_id and ObjectId.is_valid(external_id):
            update_payload = {
                "processed": bool(result.get("success")),
                "processed_at": datetime.utcnow(),
                "doc_id": source_news.get("doc_id"),
                "doc_hash": source_news.get("doc_hash"),
                "source_news_id": news_id,
                "process_result": result.get("process_result"),
            }
            self.repo.db.update_one(
                "crawled_articles",
                {"_id": ObjectId(external_id)},
                {"$set": update_payload},
            )
        return result

    def _build_content(self, news: Dict[str, Any]) -> str:
        title = news.get("title") or ""
        content = news.get("content") or ""
        summary = news.get("summary") or ""
        return f"标题：{title}\n摘要：{summary}\n正文：{content}".strip()

    def _create_document_entity(self, news: Dict[str, Any]) -> str:
        doc_id = news.get("doc_id") or self._generate_doc_id(news)
        entity_id = self._generate_entity_id("ont:Document", doc_id)
        entity_doc = {
            "entity_id": entity_id,
            "entity_category": "document",
            "entity_type": "news",
            "class_id": "ont:Document",
            "canonical_name": news.get("title") or "未命名资讯",
            "metadata": {
                "doc_id": doc_id,
                "publish_time": news.get("publish_time"),
                "source_name": news.get("source_name"),
                "source_url": news.get("source_url"),
            },
        }
        return self.repo.upsert_entity(entity_doc)

    def _create_entities(self, entities: Dict[str, List[str]]) -> Dict[str, str]:
        entity_map: Dict[str, str] = {}
        for category, items in entities.items():
            entity_category = ENTITY_CATEGORY_MAP.get(category)
            entity_type = ENTITY_TYPE_MAP.get(category)
            class_id = ENTITY_CLASS_MAP.get(category) or "ont:Entity"
            if not entity_category:
                continue
            for name in items:
                if not name:
                    continue
                entity_id = self._generate_entity_id(class_id, name)
                entity_doc = {
                    "entity_id": entity_id,
                    "entity_category": entity_category,
                    "entity_type": entity_type or category,
                    "class_id": class_id,
                    "canonical_name": name,
                }
                entity_id = self.repo.upsert_entity(entity_doc)
                entity_map[name] = entity_id
        return entity_map

    def _create_statements(
        self,
        news_id: str,
        news: Dict[str, Any],
        extraction: Dict[str, Any],
        entity_map: Dict[str, str],
        document_entity_id: str,
    ) -> List[Dict[str, Any]]:
        relations = extraction.get("relations", [])
        temporal = extraction.get("temporal", {}) or {}
        if not isinstance(temporal, dict):
            temporal = {}
        created: List[Dict[str, Any]] = []

        for relation in relations:
            subject_name = relation.get("subject")
            object_name = relation.get("object")
            subject_id = entity_map.get(subject_name)
            object_id = entity_map.get(object_name)
            if not subject_id or not object_id:
                continue

            predicate_raw = relation.get("relation") or relation.get("predicate") or "related_to"
            predicate_id, predicate_label = self._normalize_predicate(predicate_raw)
            statement_doc = {
                "subject_id": subject_id,
                "subject_category": self._infer_category(subject_id),
                "predicate_id": predicate_id,
                "predicate_label": predicate_label,
                "object_type": "entity_ref",
                "object_entity_id": object_id,
                "object_category": self._infer_category(object_id),
                "doc_id": news.get("doc_id") or news_id,
                "source_news_id": news_id,
                "evidence_type": "extraction",
                "evidence_text": relation.get("evidence"),
                "source_url": news.get("source_url"),
                "extraction_method": DEFAULT_EXTRACTION_METHOD,
                "extraction_model": extraction.get("model"),
                "context_time_value": self._format_time_value(news.get("publish_time")),
                "context_space_value": temporal.get("location") or temporal.get("place"),
                "context_source_id": news.get("source_id") or news.get("ds_id"),
                "context_version_id": extraction.get("ontology_version"),
                "context_scenario": news.get("doc_type") or "news",
                "audit_status": "pending",
                "is_current": True,
                "status": "validated",
                "confidence": relation.get("confidence", 0.8),
                "source_document_id": document_entity_id,
            }
            stmt_id = self.repo.create_statement(statement_doc)
            created.append({**statement_doc, "statement_id": stmt_id})

        return created

    def _enqueue_for_kg(
        self,
        *,
        news_id: str,
        news: Dict[str, Any],
        extraction: Dict[str, Any],
        statements: List[Dict[str, Any]],
    ) -> str:
        queue_doc = {
            "kg_name": "news_kg",
            "source_news_id": news_id,
            "doc_id": news.get("doc_id") or news_id,
            "doc_type": news.get("doc_type") or "news",
            "entities": extraction.get("entities", {}) or {},
            "relations": extraction.get("relations", []) or [],
            "statements": statements,
            "metadata": {
                "title": news.get("title"),
                "summary": extraction.get("summary") or news.get("summary"),
                "publish_time": news.get("publish_time"),
                "source_name": news.get("source_name"),
                "source_url": news.get("source_url"),
                "source_id": news.get("source_id") or news.get("ds_id"),
                "model": extraction.get("model"),
            },
            "status": "pending",
        }
        return self.repo.enqueue_kg_input(queue_doc)

    def _collect_entity_ids(self, statements: List[Dict[str, Any]]) -> List[str]:
        entity_ids = set()
        for stmt in statements:
            if stmt.get("subject_id"):
                entity_ids.add(stmt["subject_id"])
            if stmt.get("object_entity_id"):
                entity_ids.add(stmt["object_entity_id"])
        return list(entity_ids)

    def _infer_category(self, entity_id: str) -> str:
        if not entity_id:
            return "unknown"
        if entity_id.startswith("EN"):
            return "entity"
        return entity_id.split(":", 1)[0]

    def _generate_hash(self, value: str, length: int = 16) -> str:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
        return digest[:length]

    def _generate_entity_id(self, class_id: str, name: str) -> str:
        key = f"{class_id}:{name}".lower().strip()
        return f"EN{self._generate_hash(key, 16)}"

    def _generate_doc_id(self, news: Dict[str, Any]) -> str:
        title = (news.get("title") or "").strip()
        source_url = (news.get("source_url") or "").strip()
        publish_time = news.get("publish_time") or ""
        key = f"{title}|{source_url}|{publish_time}"
        return f"doc:{self._generate_hash(key, 12)}"

    def _format_time_value(self, value: Any) -> Optional[str]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        try:
            return str(value)[:10]
        except Exception:
            return None

    def _generate_doc_hash(self, news: Dict[str, Any]) -> str:
        title = (news.get("title") or "").strip()
        content = (news.get("content") or news.get("summary") or "").strip()
        source_url = (news.get("source_url") or "").strip()
        publish_time = news.get("publish_time") or ""
        key = f"{title}|{content}|{source_url}|{publish_time}"
        return f"sha256:{hashlib.sha256(key.encode('utf-8')).hexdigest()}"

    def _normalize_predicate(self, predicate_raw: Optional[str]) -> tuple[str, Optional[str]]:
        if not predicate_raw:
            return "rel:related_to", None
        if predicate_raw in PREDICATE_MAP:
            return PREDICATE_MAP[predicate_raw], predicate_raw
        if predicate_raw.startswith(("rel:", "prop:")):
            return predicate_raw, None
        slug = re.sub(r"[^a-zA-Z0-9_]+", "_", str(predicate_raw)).strip("_").lower()
        if not slug:
            slug = f"rel_{self._generate_hash(str(predicate_raw), 8)}"
        return f"rel:{slug}", predicate_raw


news_pipeline_service = NewsPipelineService()
