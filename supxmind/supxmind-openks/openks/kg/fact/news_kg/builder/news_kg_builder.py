from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
import hashlib

from openks.common.adapters import MongoKnowledgeAdapter, Neo4jGraphAdapter
from openks.common.base.core import BaseBuilder


RELATION_MAP = {
    "合作": ("rel:collaborates_with", "合作"),
    "战略合作": ("rel:collaborates_with", "战略合作"),
    "collaborates_with": ("rel:collaborates_with", "合作"),
    "研发技术": ("rel:develops", "研发技术"),
    "develops": ("rel:develops", "研发技术"),
    "供应": ("rel:supplies_to", "供应"),
    "supplies_to": ("rel:supplies_to", "供应"),
    "竞争": ("rel:competes_with", "竞争"),
    "competes_with": ("rel:competes_with", "竞争"),
}

ENTITY_TYPE_MAP = {
    "companies": "company",
    "persons": "person",
    "products": "product",
    "technologies": "technology",
    "locations": "location",
    "industries": "industry",
    "events": "event",
}

ENTITY_CATEGORY_MAP = {
    "company": "subject",
    "person": "subject",
    "product": "element",
    "technology": "element",
    "industry": "concept",
    "event": "event",
    "location": "concept",
}


class _IdentityCanonicalizer:
    def canonicalize_entity(self, entity_name: str, entity_type: str) -> str:
        key = f"{entity_type}:{entity_name}".strip().lower()
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        return f"CANONICAL_{entity_type}_{digest}"


class NewsKgBuilder(BaseBuilder):
    def __init__(
        self,
        *,
        mongo_adapter: Optional[Any] = None,
        graph_adapter: Optional[Any] = None,
        canonicalizer: Optional[Any] = None,
    ):
        self.mongo = mongo_adapter or MongoKnowledgeAdapter()
        self.graph = graph_adapter or Neo4jGraphAdapter()
        self.canonicalizer = canonicalizer or self._load_canonicalizer()

    def _load_canonicalizer(self):
        try:
            from app.services.canonicalization_service import canonicalization_service

            return canonicalization_service
        except Exception:
            return _IdentityCanonicalizer()

    def build_pending(self, *, limit: int = 20) -> Dict[str, Any]:
        records = self.mongo.list_queue_records(kg_name="news_kg", status="pending", limit=limit)
        return self.build(records)

    def get_status(self) -> Dict[str, Any]:
        return {
            "kg_name": "news_kg",
            "queue": self.mongo.queue_summary(kg_name="news_kg"),
            "latest_run": self.mongo.latest_build_run(kg_name="news_kg"),
        }

    def build(self, records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        rows = [dict(item) for item in records or [] if isinstance(item, dict)]
        if not rows:
            return {
                "kg_name": "news_kg",
                "processed": 0,
                "entities_written": 0,
                "statements_written": 0,
                "contexts_written": 0,
                "graph_relations_written": 0,
            }

        started_at = datetime.utcnow().isoformat()
        run_id = self._hash(["news_kg", started_at, len(rows)], "KRUN")
        resource_scope = {
            "doc_ids": [str(row.get("doc_id") or "") for row in rows if row.get("doc_id")],
            "queue_ids": [str(row.get("queue_id") or "") for row in rows if row.get("queue_id")],
        }
        if hasattr(self.mongo, "record_knowledge_run"):
            self.mongo.record_knowledge_run(
                {
                    "run_id": run_id,
                    "kg_name": "news_kg",
                    "status": "running",
                    "runtime_profile": "openks_direct",
                    "resource_scope": resource_scope,
                    "started_at": started_at,
                }
            )
        artifact_version = f"news_kg:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        artifact_id = self._hash(["news_kg", run_id, artifact_version], "KART")
        entities_written = 0
        statements_written = 0
        contexts_written = 0
        graph_relations_written = 0

        for row in rows:
            queue_id = str(row.get("queue_id") or "").strip()
            if queue_id and hasattr(self.mongo, "update_queue_record"):
                self.mongo.update_queue_record(queue_id, {"status": "running", "started_at": started_at, "run_id": run_id})
            try:
                result = self._build_single_record(row, run_id=run_id, artifact_id=artifact_id)
                entities_written += result["entities_written"]
                statements_written += result["statements_written"]
                contexts_written += result["contexts_written"]
                graph_relations_written += result["graph_relations_written"]
                if queue_id and hasattr(self.mongo, "update_queue_record"):
                    self.mongo.update_queue_record(
                        queue_id,
                        {
                            "status": "completed",
                            "processed_at": datetime.utcnow().isoformat(),
                            "run_id": run_id,
                            "build_result": result,
                        },
                    )
            except Exception as exc:
                if hasattr(self.mongo, "update_knowledge_run"):
                    self.mongo.update_knowledge_run(
                        run_id,
                        {
                            "status": "failed",
                            "error": str(exc),
                            "finished_at": datetime.utcnow().isoformat(),
                        },
                    )
                if queue_id and hasattr(self.mongo, "update_queue_record"):
                    self.mongo.update_queue_record(
                        queue_id,
                        {
                            "status": "failed",
                            "error": str(exc),
                            "processed_at": datetime.utcnow().isoformat(),
                        },
                    )
                raise

        summary = {
            "kg_name": "news_kg",
            "run_id": run_id,
            "processed": len(rows),
            "entities_written": entities_written,
            "statements_written": statements_written,
            "contexts_written": contexts_written,
            "graph_relations_written": graph_relations_written,
        }
        if hasattr(self.mongo, "record_knowledge_artifact"):
            self.mongo.record_knowledge_artifact(
                {
                    "artifact_id": artifact_id,
                    "kg_name": "news_kg",
                    "run_id": run_id,
                    "runtime_profile": "openks_direct",
                    "version": artifact_version,
                    "status": "ready",
                    "entity_count": entities_written,
                    "statement_count": statements_written,
                    "context_count": contexts_written,
                    "graph_relation_count": graph_relations_written,
                }
            )
        if hasattr(self.mongo, "update_knowledge_run"):
            self.mongo.update_knowledge_run(
                run_id,
                {
                    "status": "completed",
                    "artifact_ref": artifact_id,
                    "finished_at": datetime.utcnow().isoformat(),
                    "processed": len(rows),
                    "entity_count": entities_written,
                    "statement_count": statements_written,
                    "context_count": contexts_written,
                    "graph_relation_count": graph_relations_written,
                },
            )
        if hasattr(self.mongo, "record_build_run"):
            self.mongo.record_build_run(
                {
                    "run_id": self._hash(["news_kg", started_at, len(rows)], "KGRUN"),
                    "kg_name": "news_kg",
                    "status": "completed",
                    "knowledge_run_id": run_id,
                    "artifact_ref": artifact_id,
                    "started_at": started_at,
                    "finished_at": datetime.utcnow().isoformat(),
                    **summary,
                }
            )
        return {
            **summary,
            "artifact_id": artifact_id,
            "artifact_version": artifact_version,
        }

    def _build_single_record(self, row: Dict[str, Any], *, run_id: str, artifact_id: str) -> Dict[str, int]:
        entities_payload = row.get("entities") or {}
        relations = list(row.get("relations") or [])
        doc_id = str(row.get("doc_id") or "")
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}

        named_entities = self._collect_named_entities(entities_payload, relations)

        entity_map: Dict[str, Dict[str, Any]] = {}
        graph_entities: List[Dict[str, Any]] = []
        for name, entity_type in named_entities.items():
            entity_id = self.canonicalizer.canonicalize_entity(name, entity_type)
            entity_doc = {
                "entity_id": entity_id,
                "canonical_name": name,
                "name": name,
                "entity_type": entity_type,
                "entity_category": ENTITY_CATEGORY_MAP.get(entity_type, "entity"),
                "source_kg": "news_kg",
                "doc_id": doc_id,
                "run_id": run_id,
                "artifact_id": artifact_id,
            }
            self.mongo.upsert_entity(entity_doc)
            entity_map[name] = entity_doc
            graph_entities.append(
                {
                    "entity_id": entity_id,
                    "name": name,
                    "type": entity_type,
                    "confidence": 0.9,
                }
            )

        graph_relations: List[Dict[str, Any]] = []
        statements_written = 0
        contexts_written = 0
        for relation in relations:
            subject_name = str(relation.get("subject") or "").strip()
            object_name = str(relation.get("object") or "").strip()
            if subject_name not in entity_map or object_name not in entity_map:
                continue
            predicate_id, predicate_label = self._normalize_relation(
                relation.get("relation") or relation.get("predicate")
            )
            subject_id = entity_map[subject_name]["entity_id"]
            object_id = entity_map[object_name]["entity_id"]
            statement_id = self._hash(
                [
                    doc_id,
                    subject_id,
                    predicate_id,
                    object_id,
                    relation.get("evidence"),
                ],
                "ST",
            )
            statement_doc = {
                "statement_id": statement_id,
                "subject_id": subject_id,
                "predicate_id": predicate_id,
                "predicate_label": predicate_label,
                "object_type": "entity_ref",
                "object_entity_id": object_id,
                "doc_id": doc_id,
                "source_news_id": row.get("source_news_id"),
                "context_scenario": "news",
                "source_kg": "news_kg",
                "run_id": run_id,
                "artifact_id": artifact_id,
                "confidence": float(relation.get("confidence") or 0.8),
                "evidence_text": relation.get("evidence"),
                "source_url": metadata.get("source_url"),
                "context_time_value": self._normalize_time_value(metadata.get("publish_time")),
            }
            self.mongo.upsert_statement(statement_doc)
            statements_written += 1

            context_doc = {
                "context_id": self._hash([statement_id, doc_id], "CTX"),
                "statement_id": statement_id,
                "doc_id": doc_id,
                "context_type": "news_article",
                "context_scenario": "news",
                "begin_time": metadata.get("publish_time"),
                "source_name": metadata.get("source_name"),
                "source_url": metadata.get("source_url"),
                "evidence_text": relation.get("evidence"),
                "source_kg": "news_kg",
                "run_id": run_id,
                "artifact_id": artifact_id,
            }
            self.mongo.upsert_context(context_doc)
            contexts_written += 1

            graph_relations.append(
                {
                    "subject_id": subject_id,
                    "object_id": object_id,
                    "predicate_id": predicate_id,
                    "label": predicate_label,
                    "confidence": float(relation.get("confidence") or 0.8),
                }
            )

        if graph_entities or graph_relations:
            self.graph.save_structured_data(graph_entities, graph_relations)

        return {
            "entities_written": len(entity_map),
            "statements_written": statements_written,
            "contexts_written": contexts_written,
            "graph_relations_written": len(graph_relations),
        }

    def _collect_named_entities(self, entities_payload: Dict[str, Any], relations: List[Dict[str, Any]]) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for category, items in entities_payload.items():
            entity_type = ENTITY_TYPE_MAP.get(str(category), str(category).rstrip("s"))
            for item in items or []:
                name = str(item or "").strip()
                if name:
                    results[name] = entity_type
        for relation in relations:
            subject = str(relation.get("subject") or "").strip()
            obj = str(relation.get("object") or "").strip()
            if subject and subject not in results:
                results[subject] = "company"
            if obj and obj not in results:
                results[obj] = "concept"
        return results

    def _normalize_relation(self, raw_value: Any) -> tuple[str, str]:
        text = str(raw_value or "").strip()
        if not text:
            return "rel:related_to", "相关"
        if text in RELATION_MAP:
            return RELATION_MAP[text]
        slug = text.replace(" ", "_").replace("-", "_").lower()
        return f"rel:{slug}", text

    def _normalize_time_value(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    def _hash(self, parts: List[Any], prefix: str, length: int = 16) -> str:
        raw = "|".join([str(item or "") for item in parts])
        return f"{prefix}{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:length]}"
