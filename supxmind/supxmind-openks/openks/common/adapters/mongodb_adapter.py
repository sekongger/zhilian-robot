from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib


class MongoKnowledgeAdapter:
    def __init__(self, mongo: Any | None = None):
        self._mongo = mongo

    def _conn(self):
        if self._mongo is not None:
            return self._mongo
        from app.database.mongodb import mongodb_conn

        return mongodb_conn

    def _normalize_doc(self, payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        result = dict(payload)
        if "_id" in result:
            result["_id"] = str(result["_id"])
        return result

    def _hash(self, parts: List[Any], prefix: str, length: int = 16) -> str:
        raw = "|".join([str(item or "") for item in parts])
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:length]
        return f"{prefix}{digest}"

    def list_queue_records(self, *, kg_name: str = "news_kg", status: Optional[str] = "pending", limit: int = 20) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"kg_name": kg_name}
        if status:
            query["status"] = status
        rows = self._conn().find_many("kg_input_queue", query=query, limit=limit, sort=[("created_at", 1)])
        return [self._normalize_doc(row) or {} for row in rows]

    def update_queue_record(self, queue_id: str, fields: Dict[str, Any]) -> None:
        self._conn().update_one(
            "kg_input_queue",
            {"queue_id": queue_id},
            {"$set": {**fields, "updated_at": datetime.utcnow()}},
            upsert=False,
        )

    def upsert_entity(self, payload: Dict[str, Any]) -> str:
        entity_id = str(payload.get("entity_id") or payload.get("_id") or "")
        document = {
            **payload,
            "_id": entity_id,
            "entity_id": entity_id,
            "updated_at": datetime.utcnow(),
        }
        if not payload.get("created_at"):
            document["created_at"] = datetime.utcnow()
        self._conn().update_one(
            "entity_instances",
            {"_id": entity_id},
            {"$set": document},
            upsert=True,
        )
        return entity_id

    def upsert_statement(self, payload: Dict[str, Any]) -> str:
        statement_id = str(
            payload.get("statement_id")
            or self._hash(
                [
                    payload.get("subject_id"),
                    payload.get("predicate_id"),
                    payload.get("object_entity_id"),
                    payload.get("doc_id"),
                    payload.get("evidence_text"),
                ],
                "ST",
            )
        )
        document = {
            **payload,
            "_id": statement_id,
            "statement_id": statement_id,
            "updated_at": datetime.utcnow(),
        }
        if not payload.get("created_at"):
            document["created_at"] = datetime.utcnow()
        self._conn().update_one(
            "inc_statement",
            {"_id": statement_id},
            {"$set": document},
            upsert=True,
        )
        return statement_id

    def upsert_context(self, payload: Dict[str, Any]) -> str:
        context_id = str(
            payload.get("context_id")
            or self._hash(
                [payload.get("statement_id"), payload.get("doc_id"), payload.get("evidence_text")],
                "CTX",
            )
        )
        document = {
            **payload,
            "_id": context_id,
            "context_id": context_id,
            "updated_at": datetime.utcnow(),
        }
        if not payload.get("created_at"):
            document["created_at"] = datetime.utcnow()
        self._conn().update_one(
            "inc_context",
            {"_id": context_id},
            {"$set": document},
            upsert=True,
        )
        return context_id

    def record_build_run(self, payload: Dict[str, Any]) -> str:
        run_id = str(payload.get("run_id") or self._hash([payload.get("kg_name"), payload.get("started_at")], "KGRUN"))
        document = {
            **payload,
            "_id": run_id,
            "run_id": run_id,
            "updated_at": datetime.utcnow(),
        }
        if not payload.get("created_at"):
            document["created_at"] = datetime.utcnow()
        self._conn().update_one(
            "kg_build_runs",
            {"_id": run_id},
            {"$set": document},
            upsert=True,
        )
        return run_id

    def record_knowledge_run(self, payload: Dict[str, Any]) -> str:
        run_id = str(payload.get("run_id") or self._hash([payload.get("kg_name"), payload.get("started_at")], "KRUN"))
        document = {
            **payload,
            "_id": run_id,
            "run_id": run_id,
            "updated_at": datetime.utcnow(),
        }
        if not payload.get("created_at"):
            document["created_at"] = datetime.utcnow()
        self._conn().update_one(
            "knowledge_runs",
            {"_id": run_id},
            {"$set": document},
            upsert=True,
        )
        return run_id

    def update_knowledge_run(self, run_id: str, fields: Dict[str, Any]) -> None:
        self._conn().update_one(
            "knowledge_runs",
            {"_id": run_id},
            {"$set": {**fields, "updated_at": datetime.utcnow()}},
            upsert=False,
        )

    def record_knowledge_artifact(self, payload: Dict[str, Any]) -> str:
        artifact_id = str(
            payload.get("artifact_id")
            or self._hash(
                [payload.get("kg_name"), payload.get("run_id"), payload.get("version")],
                "KART",
            )
        )
        document = {
            **payload,
            "_id": artifact_id,
            "artifact_id": artifact_id,
            "updated_at": datetime.utcnow(),
        }
        if not payload.get("created_at"):
            document["created_at"] = datetime.utcnow()
        self._conn().update_one(
            "knowledge_artifacts",
            {"_id": artifact_id},
            {"$set": document},
            upsert=True,
        )
        return artifact_id

    def record_service_release(self, payload: Dict[str, Any]) -> str:
        release_id = str(
            payload.get("release_id")
            or self._hash(
                [payload.get("artifact_id"), payload.get("version"), payload.get("released_at")],
                "KREL",
            )
        )
        document = {
            **payload,
            "_id": release_id,
            "release_id": release_id,
            "updated_at": datetime.utcnow(),
        }
        if not payload.get("created_at"):
            document["created_at"] = datetime.utcnow()
        self._conn().update_one(
            "service_releases",
            {"_id": release_id},
            {"$set": document},
            upsert=True,
        )
        return release_id

    def queue_summary(self, *, kg_name: str = "news_kg") -> Dict[str, int]:
        rows = self._conn().find_many("kg_input_queue", query={"kg_name": kg_name}, limit=500)
        summary = {"pending": 0, "running": 0, "failed": 0, "completed": 0}
        for row in rows:
            status = str((row or {}).get("status") or "pending").lower()
            if status in summary:
                summary[status] += 1
        return summary

    def latest_build_run(self, *, kg_name: str = "news_kg") -> Optional[Dict[str, Any]]:
        rows = self._conn().find_many(
            "kg_build_runs",
            query={"kg_name": kg_name},
            limit=1,
            sort=[("created_at", -1)],
        )
        return self._normalize_doc(rows[0]) if rows else None

    def find_many(self, collection_name: str, query: Optional[Dict[str, Any]] = None, *, limit: int = 0, sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        rows = self._conn().find_many(collection_name, query=query or {}, limit=limit, sort=sort)
        return [self._normalize_doc(row) or {} for row in rows]
